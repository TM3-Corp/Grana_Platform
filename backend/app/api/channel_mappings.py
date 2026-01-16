"""
Channel Mappings API Endpoints
Comprehensive client-channel relationship management

Purpose:
- Analyze which clients belong to which channels (from orders data)
- Detect anomalies: clients with multiple channels or no channel
- Create override rules that take precedence over RelBase data
- Sync channels from RelBase API
- Filter clients by channel

These rules correct customer channel assignments when RelBase has errors or omissions.

Author: TM3
Date: 2025-01-16
"""
from fastapi import APIRouter, HTTPException, Query
from typing import Optional, List
from pydantic import BaseModel, Field
import os
import psycopg2
from psycopg2.extras import RealDictCursor
import requests
import logging

logger = logging.getLogger(__name__)

# RelBase API credentials
RELBASE_COMPANY_TOKEN = os.getenv("RELBASE_COMPANY_TOKEN", "8iNGjKSPBJQ7R2su4ZtftBsP")
RELBASE_USER_TOKEN = os.getenv("RELBASE_USER_TOKEN", "3dk4TybsDQwiCH39AvnSHiEi")

router = APIRouter()

# Database connection
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    # Fallback for local development
    DATABASE_URL = "postgresql://postgres.lypuvibmtxjaxmcmahxr:%24Ilofono1@aws-1-sa-east-1.pooler.supabase.com:6543/postgres"


# =====================================================================
# Pydantic Models
# =====================================================================

class ChannelMappingCreate(BaseModel):
    """Request model for creating a new channel mapping"""
    customer_external_id: str = Field(..., min_length=1, max_length=50, description="RelBase customer_id")
    channel_external_id: int = Field(..., description="RelBase channel_id")
    channel_name: str = Field(..., min_length=1, max_length=100, description="Channel name")
    rule_reason: str = Field(..., min_length=1, description="Business reason for this mapping")
    priority: int = Field(default=1, ge=1, le=10, description="Priority (1-10, higher = higher priority)")
    created_by: Optional[str] = Field(None, max_length=100, description="Who created this rule")


class ChannelMappingUpdate(BaseModel):
    """Request model for updating an existing channel mapping"""
    customer_external_id: Optional[str] = Field(None, min_length=1, max_length=50)
    channel_external_id: Optional[int] = None
    channel_name: Optional[str] = Field(None, min_length=1, max_length=100)
    rule_reason: Optional[str] = Field(None, min_length=1)
    priority: Optional[int] = Field(None, ge=1, le=10)
    is_active: Optional[bool] = None


# =====================================================================
# API Endpoints
# =====================================================================

@router.get("/stats")
async def get_channel_mapping_stats():
    """
    Get statistics for KPI cards.
    Returns total rules, active rules, channels covered, customers mapped.
    """
    try:
        conn = psycopg2.connect(DATABASE_URL, connect_timeout=10)
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        # Total rules
        cursor.execute("SELECT COUNT(*) as count FROM customer_channel_rules")
        total_rules = cursor.fetchone()['count']

        # Active rules
        cursor.execute("SELECT COUNT(*) as count FROM customer_channel_rules WHERE is_active = TRUE")
        active_rules = cursor.fetchone()['count']

        # Unique channels used
        cursor.execute("""
            SELECT COUNT(DISTINCT channel_external_id) as count
            FROM customer_channel_rules
            WHERE is_active = TRUE
        """)
        channels_covered = cursor.fetchone()['count']

        # Unique customers mapped
        cursor.execute("""
            SELECT COUNT(DISTINCT customer_external_id) as count
            FROM customer_channel_rules
            WHERE is_active = TRUE
        """)
        customers_mapped = cursor.fetchone()['count']

        cursor.close()
        conn.close()

        return {
            "status": "success",
            "data": {
                "total_rules": total_rules,
                "active_rules": active_rules,
                "channels_covered": channels_covered,
                "customers_mapped": customers_mapped
            }
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching stats: {str(e)}")


@router.get("/channels")
async def get_available_channels():
    """
    Get list of available channels for dropdown.
    Returns channels from the channels table.
    """
    try:
        conn = psycopg2.connect(DATABASE_URL, connect_timeout=10)
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        cursor.execute("""
            SELECT id, name, external_id
            FROM channels
            WHERE is_active = TRUE
            ORDER BY name
        """)
        channels = cursor.fetchall()

        cursor.close()
        conn.close()

        return {
            "status": "success",
            "data": channels
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching channels: {str(e)}")


@router.get("/customers/search")
async def search_customers(
    q: str = Query(..., min_length=1, description="Search query"),
    limit: int = Query(20, ge=1, le=100, description="Max results")
):
    """
    Search customers by name, RUT, or external_id.
    Returns matching customers for dropdown.
    """
    try:
        conn = psycopg2.connect(DATABASE_URL, connect_timeout=10)
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        search_param = f"%{q}%"
        cursor.execute("""
            SELECT
                id,
                external_id,
                name,
                rut,
                source
            FROM customers
            WHERE source = 'relbase'
              AND (
                  name ILIKE %s OR
                  rut ILIKE %s OR
                  external_id ILIKE %s
              )
            ORDER BY name
            LIMIT %s
        """, [search_param, search_param, search_param, limit])
        customers = cursor.fetchall()

        cursor.close()
        conn.close()

        return {
            "status": "success",
            "data": customers
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error searching customers: {str(e)}")


@router.get("/")
async def list_channel_mappings(
    search: Optional[str] = Query(None, description="Search in customer_external_id, channel_name, or rule_reason"),
    channel_name: Optional[str] = Query(None, description="Filter by channel name"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    limit: int = Query(50, ge=1, le=500, description="Max results to return"),
    offset: int = Query(0, ge=0, description="Offset for pagination")
):
    """
    List all channel mapping rules with filters and pagination.
    Returns mappings with customer details joined.
    """
    try:
        conn = psycopg2.connect(DATABASE_URL, connect_timeout=10)
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        # Build query
        where_clauses = []
        params = []

        if search:
            where_clauses.append("""
                (ccr.customer_external_id ILIKE %s OR
                 ccr.channel_name ILIKE %s OR
                 ccr.rule_reason ILIKE %s OR
                 c.name ILIKE %s)
            """)
            search_param = f"%{search}%"
            params.extend([search_param, search_param, search_param, search_param])

        if channel_name:
            where_clauses.append("ccr.channel_name ILIKE %s")
            params.append(f"%{channel_name}%")

        if is_active is not None:
            where_clauses.append("ccr.is_active = %s")
            params.append(is_active)

        where_sql = " AND ".join(where_clauses) if where_clauses else "TRUE"

        # Get total count
        count_sql = f"""
            SELECT COUNT(*)
            FROM customer_channel_rules ccr
            LEFT JOIN customers c ON c.external_id = ccr.customer_external_id AND c.source = 'relbase'
            WHERE {where_sql}
        """
        cursor.execute(count_sql, params)
        total = cursor.fetchone()['count']

        # Get paginated results with customer details
        query_sql = f"""
            SELECT
                ccr.id,
                ccr.customer_external_id,
                ccr.channel_external_id,
                ccr.channel_name,
                ccr.rule_reason,
                ccr.priority,
                ccr.is_active,
                ccr.created_by,
                ccr.created_at,
                ccr.updated_at,
                c.name as customer_name,
                c.rut as customer_rut
            FROM customer_channel_rules ccr
            LEFT JOIN customers c ON c.external_id = ccr.customer_external_id AND c.source = 'relbase'
            WHERE {where_sql}
            ORDER BY ccr.priority DESC, ccr.created_at DESC
            LIMIT %s OFFSET %s
        """
        cursor.execute(query_sql, params + [limit, offset])
        mappings = cursor.fetchall()

        cursor.close()
        conn.close()

        return {
            "status": "success",
            "data": mappings,
            "total": total,
            "limit": limit,
            "offset": offset
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error listing mappings: {str(e)}")


# =====================================================================
# RelBase Channel Sync & Client-Channel Analysis
# These routes MUST come before /{mapping_id} to avoid route conflicts
# =====================================================================

@router.get("/relbase-channels")
async def get_relbase_channels(active_only: bool = Query(True, description="Only show active RelBase channels")):
    """
    Get channels synced from RelBase.
    These are the official channels from the RelBase API (canal_ventas).
    """
    try:
        conn = psycopg2.connect(DATABASE_URL, connect_timeout=10)
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        if active_only:
            cursor.execute("""
                SELECT id, name, external_id, is_active_relbase
                FROM channels
                WHERE source = 'relbase' AND is_active_relbase = TRUE
                ORDER BY name
            """)
        else:
            cursor.execute("""
                SELECT id, name, external_id, is_active_relbase
                FROM channels
                WHERE source = 'relbase'
                ORDER BY is_active_relbase DESC, name
            """)

        channels = cursor.fetchall()
        cursor.close()
        conn.close()

        return {
            "status": "success",
            "data": channels,
            "count": len(channels)
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching RelBase channels: {str(e)}")


@router.post("/sync-relbase-channels")
async def sync_relbase_channels():
    """
    Sync channels from RelBase API (canal_ventas).
    Updates the channels table with current RelBase channel data.
    """
    try:
        # Fetch from RelBase API
        headers = {
            'accept': 'application/json',
            'Authorization': RELBASE_USER_TOKEN,
            'Company': RELBASE_COMPANY_TOKEN
        }

        response = requests.get(
            'https://api.relbase.cl/api/v1/canal_ventas',
            headers=headers,
            timeout=30
        )
        response.raise_for_status()
        data = response.json()

        relbase_channels = data.get('data', {}).get('channels', [])

        if not relbase_channels:
            return {
                "status": "warning",
                "message": "No channels returned from RelBase API"
            }

        conn = psycopg2.connect(DATABASE_URL, connect_timeout=10)
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        synced = 0
        inserted = 0

        for ch in relbase_channels:
            ch_id = str(ch['id'])
            ch_name = ch['name']
            ch_active = ch.get('active', True)

            # Try to update existing
            cursor.execute("""
                UPDATE channels
                SET name = %s, is_active_relbase = %s, updated_at = NOW()
                WHERE external_id = %s AND source = 'relbase'
            """, (ch_name, ch_active, ch_id))

            if cursor.rowcount == 0:
                # Insert new
                code = ch_name.lower().replace(' ', '_').replace('/', '_')
                cursor.execute("""
                    INSERT INTO channels (code, name, external_id, source, is_active, is_active_relbase)
                    VALUES (%s, %s, %s, 'relbase', %s, %s)
                    ON CONFLICT DO NOTHING
                """, (code, ch_name, ch_id, ch_active, ch_active))
                inserted += 1
            else:
                synced += 1

        conn.commit()
        cursor.close()
        conn.close()

        return {
            "status": "success",
            "message": f"Synced {synced} channels, inserted {inserted} new channels",
            "total_from_api": len(relbase_channels)
        }

    except requests.RequestException as e:
        raise HTTPException(status_code=502, detail=f"Error connecting to RelBase API: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error syncing channels: {str(e)}")


@router.get("/client-channel-analysis")
async def get_client_channel_analysis(
    channel_external_id: Optional[str] = Query(None, description="Filter by RelBase channel ID"),
    anomaly_type: Optional[str] = Query(None, description="Filter by anomaly: 'multiple' (>1 channel), 'none' (no channel)"),
    search: Optional[str] = Query(None, description="Search by customer name or RUT"),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0)
):
    """
    Analyze which clients belong to which channels based on their orders.

    This endpoint shows:
    - All clients and their channel distribution (from orders)
    - Clients with multiple channels (data quality issue)
    - Clients with no channel assigned
    - Whether an override rule exists for the client

    Use this to identify and fix channel assignment issues.
    """
    try:
        conn = psycopg2.connect(DATABASE_URL, connect_timeout=10)
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        # Build the query for client-channel analysis
        where_clauses = []
        params = []

        base_query = """
            WITH client_channels AS (
                SELECT
                    c.id as customer_id,
                    c.external_id as customer_external_id,
                    c.name as customer_name,
                    c.rut as customer_rut,
                    COUNT(DISTINCT o.channel_id) as channel_count,
                    ARRAY_AGG(DISTINCT ch.name) FILTER (WHERE ch.name IS NOT NULL) as channels,
                    ARRAY_AGG(DISTINCT ch.external_id) FILTER (WHERE ch.external_id IS NOT NULL) as channel_ids,
                    COUNT(o.id) as order_count,
                    SUM(o.total) as total_revenue
                FROM customers c
                JOIN orders o ON o.customer_id = c.id
                LEFT JOIN channels ch ON ch.id = o.channel_id
                WHERE c.source = 'relbase'
                GROUP BY c.id, c.external_id, c.name, c.rut
            ),
            with_rules AS (
                SELECT
                    cc.*,
                    ccr.id as rule_id,
                    ccr.channel_name as override_channel,
                    ccr.channel_external_id as override_channel_id,
                    ccr.rule_reason,
                    ccr.is_active as rule_active
                FROM client_channels cc
                LEFT JOIN customer_channel_rules ccr
                    ON ccr.customer_external_id = cc.customer_external_id
                    AND ccr.is_active = TRUE
            )
            SELECT * FROM with_rules
        """

        # Apply filters
        if channel_external_id:
            where_clauses.append("%s = ANY(channel_ids)")
            params.append(channel_external_id)

        if anomaly_type == 'multiple':
            where_clauses.append("channel_count > 1")
        elif anomaly_type == 'none':
            where_clauses.append("channel_count = 0 OR channels IS NULL")

        if search:
            where_clauses.append("(customer_name ILIKE %s OR customer_rut ILIKE %s)")
            search_param = f"%{search}%"
            params.extend([search_param, search_param])

        if where_clauses:
            base_query += " WHERE " + " AND ".join(where_clauses)

        # Get total count
        count_query = f"SELECT COUNT(*) FROM ({base_query}) sub"
        cursor.execute(count_query, params)
        total = cursor.fetchone()['count']

        # Get paginated results
        base_query += " ORDER BY channel_count DESC, total_revenue DESC LIMIT %s OFFSET %s"
        params.extend([limit, offset])

        cursor.execute(base_query, params)
        clients = cursor.fetchall()

        # Get summary stats
        cursor.execute("""
            SELECT
                COUNT(DISTINCT c.id) as total_clients,
                COUNT(DISTINCT CASE WHEN sub.channel_count > 1 THEN c.id END) as multi_channel_clients,
                COUNT(DISTINCT CASE WHEN sub.channel_count = 0 OR sub.channel_count IS NULL THEN c.id END) as no_channel_clients,
                COUNT(DISTINCT ccr.customer_external_id) as clients_with_rules
            FROM customers c
            JOIN (
                SELECT
                    customer_id,
                    COUNT(DISTINCT o.channel_id) as channel_count
                FROM orders o
                JOIN customers c ON c.id = o.customer_id
                WHERE c.source = 'relbase'
                GROUP BY customer_id
            ) sub ON sub.customer_id = c.id
            LEFT JOIN customer_channel_rules ccr
                ON ccr.customer_external_id = c.external_id
                AND ccr.is_active = TRUE
            WHERE c.source = 'relbase'
        """)
        stats = cursor.fetchone()

        cursor.close()
        conn.close()

        return {
            "status": "success",
            "data": clients,
            "total": total,
            "limit": limit,
            "offset": offset,
            "stats": {
                "total_clients": stats['total_clients'],
                "multi_channel_clients": stats['multi_channel_clients'],
                "no_channel_clients": stats['no_channel_clients'],
                "clients_with_rules": stats['clients_with_rules']
            }
        }

    except Exception as e:
        logger.error(f"Error in client-channel analysis: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error analyzing client channels: {str(e)}")


@router.get("/analysis-stats")
async def get_analysis_stats():
    """
    Get comprehensive stats for the channel analysis dashboard.
    Returns KPIs about clients, channels, anomalies, and rules.
    """
    try:
        conn = psycopg2.connect(DATABASE_URL, connect_timeout=10)
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        # Get client-channel stats
        cursor.execute("""
            WITH client_channels AS (
                SELECT
                    c.id,
                    COUNT(DISTINCT o.channel_id) as channel_count
                FROM customers c
                JOIN orders o ON o.customer_id = c.id
                WHERE c.source = 'relbase'
                GROUP BY c.id
            )
            SELECT
                COUNT(*) as total_clients,
                COUNT(CASE WHEN channel_count = 1 THEN 1 END) as single_channel_clients,
                COUNT(CASE WHEN channel_count > 1 THEN 1 END) as multi_channel_clients,
                COUNT(CASE WHEN channel_count = 0 THEN 1 END) as no_channel_clients
            FROM client_channels
        """)
        client_stats = cursor.fetchone()

        # Get RelBase channels count
        cursor.execute("""
            SELECT
                COUNT(*) FILTER (WHERE is_active_relbase = TRUE) as active_channels,
                COUNT(*) as total_channels
            FROM channels
            WHERE source = 'relbase'
        """)
        channel_stats = cursor.fetchone()

        # Get override rules count
        cursor.execute("""
            SELECT
                COUNT(*) as total_rules,
                COUNT(*) FILTER (WHERE is_active = TRUE) as active_rules
            FROM customer_channel_rules
        """)
        rule_stats = cursor.fetchone()

        cursor.close()
        conn.close()

        return {
            "status": "success",
            "data": {
                "clients": {
                    "total": client_stats['total_clients'],
                    "single_channel": client_stats['single_channel_clients'],
                    "multi_channel": client_stats['multi_channel_clients'],
                    "no_channel": client_stats['no_channel_clients']
                },
                "channels": {
                    "active_relbase": channel_stats['active_channels'],
                    "total_relbase": channel_stats['total_channels']
                },
                "rules": {
                    "total": rule_stats['total_rules'],
                    "active": rule_stats['active_rules']
                }
            }
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching analysis stats: {str(e)}")


# =====================================================================
# Single Mapping CRUD (these routes must come AFTER specific routes)
# =====================================================================

@router.get("/{mapping_id}")
async def get_channel_mapping(mapping_id: int):
    """
    Get a single channel mapping by ID.
    """
    try:
        conn = psycopg2.connect(DATABASE_URL, connect_timeout=10)
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        cursor.execute("""
            SELECT
                ccr.*,
                c.name as customer_name,
                c.rut as customer_rut
            FROM customer_channel_rules ccr
            LEFT JOIN customers c ON c.external_id = ccr.customer_external_id AND c.source = 'relbase'
            WHERE ccr.id = %s
        """, [mapping_id])
        mapping = cursor.fetchone()

        cursor.close()
        conn.close()

        if not mapping:
            raise HTTPException(status_code=404, detail="Mapping not found")

        return {
            "status": "success",
            "data": mapping
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching mapping: {str(e)}")


@router.post("/")
async def create_channel_mapping(mapping: ChannelMappingCreate):
    """
    Create a new channel mapping rule.
    """
    try:
        conn = psycopg2.connect(DATABASE_URL, connect_timeout=10)
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        # Check for existing active mapping for this customer
        cursor.execute("""
            SELECT id FROM customer_channel_rules
            WHERE customer_external_id = %s AND is_active = TRUE
        """, [mapping.customer_external_id])
        existing = cursor.fetchone()

        if existing:
            cursor.close()
            conn.close()
            raise HTTPException(
                status_code=400,
                detail=f"Ya existe un mapeo activo para el cliente {mapping.customer_external_id}"
            )

        # Insert new mapping
        cursor.execute("""
            INSERT INTO customer_channel_rules
                (customer_external_id, channel_external_id, channel_name, rule_reason, priority, created_by)
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING *
        """, [
            mapping.customer_external_id,
            mapping.channel_external_id,
            mapping.channel_name,
            mapping.rule_reason,
            mapping.priority,
            mapping.created_by
        ])
        new_mapping = cursor.fetchone()

        conn.commit()
        cursor.close()
        conn.close()

        return {
            "status": "success",
            "message": "Mapeo creado exitosamente",
            "data": new_mapping
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating mapping: {str(e)}")


@router.put("/{mapping_id}")
async def update_channel_mapping(mapping_id: int, mapping: ChannelMappingUpdate):
    """
    Update an existing channel mapping.
    """
    try:
        conn = psycopg2.connect(DATABASE_URL, connect_timeout=10)
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        # Check if mapping exists
        cursor.execute("SELECT * FROM customer_channel_rules WHERE id = %s", [mapping_id])
        existing = cursor.fetchone()

        if not existing:
            cursor.close()
            conn.close()
            raise HTTPException(status_code=404, detail="Mapping not found")

        # Build update query dynamically
        updates = []
        params = []

        if mapping.customer_external_id is not None:
            updates.append("customer_external_id = %s")
            params.append(mapping.customer_external_id)

        if mapping.channel_external_id is not None:
            updates.append("channel_external_id = %s")
            params.append(mapping.channel_external_id)

        if mapping.channel_name is not None:
            updates.append("channel_name = %s")
            params.append(mapping.channel_name)

        if mapping.rule_reason is not None:
            updates.append("rule_reason = %s")
            params.append(mapping.rule_reason)

        if mapping.priority is not None:
            updates.append("priority = %s")
            params.append(mapping.priority)

        if mapping.is_active is not None:
            updates.append("is_active = %s")
            params.append(mapping.is_active)

        if not updates:
            cursor.close()
            conn.close()
            return {
                "status": "success",
                "message": "No changes to apply",
                "data": existing
            }

        updates.append("updated_at = NOW()")
        params.append(mapping_id)

        cursor.execute(f"""
            UPDATE customer_channel_rules
            SET {', '.join(updates)}
            WHERE id = %s
            RETURNING *
        """, params)
        updated = cursor.fetchone()

        conn.commit()
        cursor.close()
        conn.close()

        return {
            "status": "success",
            "message": "Mapeo actualizado exitosamente",
            "data": updated
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error updating mapping: {str(e)}")


@router.delete("/{mapping_id}")
async def delete_channel_mapping(
    mapping_id: int,
    hard_delete: bool = Query(False, description="If true, permanently delete. Otherwise soft delete.")
):
    """
    Delete a channel mapping.
    By default, performs soft delete (sets is_active=false).
    """
    try:
        conn = psycopg2.connect(DATABASE_URL, connect_timeout=10)
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        # Check if mapping exists
        cursor.execute("SELECT * FROM customer_channel_rules WHERE id = %s", [mapping_id])
        existing = cursor.fetchone()

        if not existing:
            cursor.close()
            conn.close()
            raise HTTPException(status_code=404, detail="Mapping not found")

        if hard_delete:
            cursor.execute("DELETE FROM customer_channel_rules WHERE id = %s", [mapping_id])
            message = "Mapeo eliminado permanentemente"
        else:
            cursor.execute("""
                UPDATE customer_channel_rules
                SET is_active = FALSE, updated_at = NOW()
                WHERE id = %s
            """, [mapping_id])
            message = "Mapeo desactivado"

        conn.commit()
        cursor.close()
        conn.close()

        return {
            "status": "success",
            "message": message
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error deleting mapping: {str(e)}")
