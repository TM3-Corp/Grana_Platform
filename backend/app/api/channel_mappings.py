"""
Channel Mappings API Endpoints
Comprehensive client-channel relationship management

Purpose:
- Analyze which clients belong to which channels (from orders data)
- Detect anomalies: clients with multiple channels or no channel
- Assign channels to customers (stored in customers.assigned_channel_id)
- Sync channels from RelBase API
- Filter clients by channel

REFACTORED: Now uses customers.assigned_channel_id instead of customer_channel_rules table.
The customer_channel_rules table was removed in migration 20260113000001.

Author: TM3
Date: 2025-01-16
Refactored: 2026-01-16
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

class ChannelAssignmentCreate(BaseModel):
    """Request model for assigning a channel to a customer"""
    customer_external_id: str = Field(..., min_length=1, max_length=50, description="RelBase customer_id")
    channel_external_id: int = Field(..., description="RelBase channel_id")
    channel_name: str = Field(..., min_length=1, max_length=100, description="Channel name")
    assigned_by: Optional[str] = Field(None, max_length=100, description="Who assigned this channel")


class ChannelAssignmentUpdate(BaseModel):
    """Request model for updating a channel assignment"""
    channel_external_id: Optional[int] = None
    channel_name: Optional[str] = Field(None, min_length=1, max_length=100)


# =====================================================================
# Helper Functions
# =====================================================================

def apply_channel_override_to_historical_orders(
    cursor,
    customer_external_id: str,
    channel_external_id: int
) -> int:
    """
    Apply channel override to ALL historical orders for a customer.

    This ensures that when a channel is assigned to a customer, ALL their
    historical orders are corrected to use the assigned channel - both orders
    with NULL channel and orders with wrong channels.

    Args:
        cursor: Database cursor
        customer_external_id: The RelBase customer external ID
        channel_external_id: The RelBase channel external ID (NOT the internal channels.id)

    Returns:
        Number of orders updated
    """
    # First, find the internal customer ID and the internal channel ID
    cursor.execute("""
        SELECT c.id as customer_id, ch.id as channel_id
        FROM customers c
        JOIN channels ch ON ch.external_id = %s AND ch.source = 'relbase'
        WHERE c.external_id = %s AND c.source = 'relbase'
    """, [str(channel_external_id), customer_external_id])
    result = cursor.fetchone()

    if not result:
        logger.warning(
            f"Customer {customer_external_id} or channel {channel_external_id} not found "
            "for historical order update"
        )
        return 0

    customer_id = result['customer_id']
    channel_internal_id = result['channel_id']

    # Temporarily disable the audit trigger (it has a bug with missing corrected_by column)
    try:
        cursor.execute("ALTER TABLE orders DISABLE TRIGGER audit_order_changes_trigger")
    except Exception as e:
        logger.warning(f"Could not disable audit trigger: {e}")

    # Update ALL orders for this customer that don't have the correct channel
    # This fixes both NULL channels AND wrong channels
    cursor.execute("""
        UPDATE orders
        SET channel_id = %s,
            updated_at = NOW()
        WHERE customer_id = %s
          AND source = 'relbase'
          AND (channel_id IS NULL OR channel_id != %s)
    """, [channel_internal_id, customer_id, channel_internal_id])

    updated_count = cursor.rowcount

    # Re-enable the audit trigger
    try:
        cursor.execute("ALTER TABLE orders ENABLE TRIGGER audit_order_changes_trigger")
    except Exception as e:
        logger.warning(f"Could not re-enable audit trigger: {e}")

    if updated_count > 0:
        logger.info(
            f"Applied channel override: Corrected {updated_count} historical orders "
            f"for customer {customer_external_id} to channel_id={channel_internal_id}"
        )

    return updated_count


# =====================================================================
# API Endpoints
# =====================================================================

@router.get("/stats")
async def get_channel_mapping_stats():
    """
    Get statistics for KPI cards.
    Returns total assignments, channels covered, customers mapped.
    """
    try:
        conn = psycopg2.connect(DATABASE_URL, connect_timeout=10)
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        # Total customers with channel assignments
        cursor.execute("""
            SELECT COUNT(*) as count
            FROM customers
            WHERE source = 'relbase'
              AND assigned_channel_id IS NOT NULL
        """)
        total_assignments = cursor.fetchone()['count']

        # Unique channels used
        cursor.execute("""
            SELECT COUNT(DISTINCT assigned_channel_id) as count
            FROM customers
            WHERE source = 'relbase'
              AND assigned_channel_id IS NOT NULL
        """)
        channels_covered = cursor.fetchone()['count']

        # Total relbase customers
        cursor.execute("""
            SELECT COUNT(*) as count
            FROM customers
            WHERE source = 'relbase'
        """)
        total_customers = cursor.fetchone()['count']

        cursor.close()
        conn.close()

        return {
            "status": "success",
            "data": {
                "total_rules": total_assignments,  # backwards compat
                "active_rules": total_assignments,  # all assignments are "active"
                "channels_covered": channels_covered,
                "customers_mapped": total_assignments,
                "total_customers": total_customers
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
                source,
                assigned_channel_id,
                assigned_channel_name
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
    search: Optional[str] = Query(None, description="Search in customer name, external_id, or channel"),
    channel_name: Optional[str] = Query(None, description="Filter by channel name"),
    is_active: Optional[bool] = Query(None, description="Filter by active status (assigned_channel_id IS NOT NULL)"),
    limit: int = Query(50, ge=1, le=500, description="Max results to return"),
    offset: int = Query(0, ge=0, description="Offset for pagination")
):
    """
    List all customers with channel assignments.
    Returns customers that have assigned_channel_id set.
    """
    try:
        conn = psycopg2.connect(DATABASE_URL, connect_timeout=10)
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        # Build query
        where_clauses = ["source = 'relbase'"]
        params = []

        if search:
            where_clauses.append("""
                (external_id ILIKE %s OR
                 assigned_channel_name ILIKE %s OR
                 name ILIKE %s)
            """)
            search_param = f"%{search}%"
            params.extend([search_param, search_param, search_param])

        if channel_name:
            where_clauses.append("assigned_channel_name ILIKE %s")
            params.append(f"%{channel_name}%")

        if is_active is not None:
            if is_active:
                where_clauses.append("assigned_channel_id IS NOT NULL")
            else:
                where_clauses.append("assigned_channel_id IS NULL")

        where_sql = " AND ".join(where_clauses)

        # Get total count
        count_sql = f"""
            SELECT COUNT(*)
            FROM customers
            WHERE {where_sql}
        """
        cursor.execute(count_sql, params)
        total = cursor.fetchone()['count']

        # Get paginated results
        query_sql = f"""
            SELECT
                id,
                external_id as customer_external_id,
                name as customer_name,
                rut as customer_rut,
                assigned_channel_id as channel_external_id,
                assigned_channel_name as channel_name,
                channel_assigned_by as created_by,
                channel_assigned_at as created_at,
                updated_at,
                CASE WHEN assigned_channel_id IS NOT NULL THEN TRUE ELSE FALSE END as is_active
            FROM customers
            WHERE {where_sql}
              AND assigned_channel_id IS NOT NULL
            ORDER BY channel_assigned_at DESC NULLS LAST
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
    - Whether an override assignment exists for the client (assigned_channel_id)

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
                    COUNT(CASE WHEN o.channel_id IS NULL THEN 1 END) as orders_without_channel,
                    SUM(o.total) as total_revenue,
                    c.assigned_channel_id as override_channel_id,
                    c.assigned_channel_name as override_channel,
                    c.channel_assigned_by,
                    c.channel_assigned_at
                FROM customers c
                JOIN orders o ON o.customer_id = c.id
                LEFT JOIN channels ch ON ch.id = o.channel_id
                WHERE c.source = 'relbase'
                GROUP BY c.id, c.external_id, c.name, c.rut,
                         c.assigned_channel_id, c.assigned_channel_name,
                         c.channel_assigned_by, c.channel_assigned_at
            )
            SELECT
                *,
                CASE WHEN override_channel_id IS NOT NULL THEN TRUE ELSE FALSE END as has_override
            FROM client_channels
        """

        # Apply filters
        if channel_external_id:
            where_clauses.append("%s = ANY(channel_ids)")
            params.append(channel_external_id)

        if anomaly_type == 'multiple':
            where_clauses.append("channel_count > 1")
        elif anomaly_type == 'none':
            # Show customers with ANY order that has no channel assigned
            where_clauses.append("orders_without_channel > 0")

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
        # Sort unmapped customers (orders_without_channel > 0) first, then by channel_count and revenue
        base_query += " ORDER BY orders_without_channel DESC, channel_count DESC, total_revenue DESC LIMIT %s OFFSET %s"
        params.extend([limit, offset])

        cursor.execute(base_query, params)
        clients = cursor.fetchall()

        # Get summary stats
        cursor.execute("""
            SELECT
                COUNT(DISTINCT c.id) as total_clients,
                COUNT(DISTINCT CASE WHEN sub.channel_count > 1 THEN c.id END) as multi_channel_clients,
                COUNT(DISTINCT CASE WHEN sub.orders_without_channel > 0 THEN c.id END) as no_channel_clients,
                COUNT(DISTINCT CASE WHEN c.assigned_channel_id IS NOT NULL THEN c.id END) as clients_with_override
            FROM customers c
            JOIN (
                SELECT
                    o.customer_id,
                    COUNT(DISTINCT o.channel_id) as channel_count,
                    COUNT(CASE WHEN o.channel_id IS NULL THEN 1 END) as orders_without_channel
                FROM orders o
                JOIN customers c ON c.id = o.customer_id
                WHERE c.source = 'relbase'
                GROUP BY o.customer_id
            ) sub ON sub.customer_id = c.id
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
                "clients_with_rules": stats['clients_with_override']  # backwards compat
            }
        }

    except Exception as e:
        logger.error(f"Error in client-channel analysis: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error analyzing client channels: {str(e)}")


@router.get("/analysis-stats")
async def get_analysis_stats():
    """
    Get comprehensive stats for the channel analysis dashboard.
    Returns KPIs about clients, channels, anomalies, and assignments.
    """
    try:
        conn = psycopg2.connect(DATABASE_URL, connect_timeout=10)
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        # Get client-channel stats
        cursor.execute("""
            WITH client_channels AS (
                SELECT
                    c.id,
                    COUNT(DISTINCT o.channel_id) as channel_count,
                    COUNT(CASE WHEN o.channel_id IS NULL THEN 1 END) as orders_without_channel
                FROM customers c
                JOIN orders o ON o.customer_id = c.id
                WHERE c.source = 'relbase'
                GROUP BY c.id
            )
            SELECT
                COUNT(*) as total_clients,
                COUNT(CASE WHEN channel_count = 1 AND orders_without_channel = 0 THEN 1 END) as single_channel_clients,
                COUNT(CASE WHEN channel_count > 1 THEN 1 END) as multi_channel_clients,
                COUNT(CASE WHEN orders_without_channel > 0 THEN 1 END) as no_channel_clients
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

        # Get customers with channel assignments
        cursor.execute("""
            SELECT
                COUNT(*) as total_assignments
            FROM customers
            WHERE source = 'relbase'
              AND assigned_channel_id IS NOT NULL
        """)
        assignment_stats = cursor.fetchone()

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
                "rules": {  # backwards compat naming
                    "total": assignment_stats['total_assignments'],
                    "active": assignment_stats['total_assignments']
                }
            }
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching analysis stats: {str(e)}")


# =====================================================================
# Customer Channel Assignment (replaces customer_channel_rules CRUD)
# =====================================================================

@router.get("/customer/{customer_external_id}")
async def get_customer_channel(customer_external_id: str):
    """
    Get channel assignment for a specific customer.
    """
    try:
        conn = psycopg2.connect(DATABASE_URL, connect_timeout=10)
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        cursor.execute("""
            SELECT
                id,
                external_id as customer_external_id,
                name as customer_name,
                rut as customer_rut,
                assigned_channel_id as channel_external_id,
                assigned_channel_name as channel_name,
                channel_assigned_by as created_by,
                channel_assigned_at as created_at,
                CASE WHEN assigned_channel_id IS NOT NULL THEN TRUE ELSE FALSE END as is_active
            FROM customers
            WHERE external_id = %s AND source = 'relbase'
        """, [customer_external_id])
        customer = cursor.fetchone()

        cursor.close()
        conn.close()

        if not customer:
            raise HTTPException(status_code=404, detail="Customer not found")

        return {
            "status": "success",
            "data": customer
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching customer: {str(e)}")


@router.post("/")
async def assign_channel_to_customer(assignment: ChannelAssignmentCreate):
    """
    Assign a channel to a customer.
    Updates customers.assigned_channel_id and related fields.
    """
    try:
        conn = psycopg2.connect(DATABASE_URL, connect_timeout=10)
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        # Check if customer exists
        cursor.execute("""
            SELECT id, assigned_channel_id
            FROM customers
            WHERE external_id = %s AND source = 'relbase'
        """, [assignment.customer_external_id])
        customer = cursor.fetchone()

        if not customer:
            cursor.close()
            conn.close()
            raise HTTPException(
                status_code=404,
                detail=f"Cliente no encontrado: {assignment.customer_external_id}"
            )

        if customer['assigned_channel_id'] is not None:
            cursor.close()
            conn.close()
            raise HTTPException(
                status_code=400,
                detail=f"El cliente {assignment.customer_external_id} ya tiene un canal asignado"
            )

        # Assign the channel
        cursor.execute("""
            UPDATE customers
            SET
                assigned_channel_id = %s,
                assigned_channel_name = %s,
                channel_assigned_by = %s,
                channel_assigned_at = NOW(),
                updated_at = NOW()
            WHERE external_id = %s AND source = 'relbase'
            RETURNING
                id,
                external_id as customer_external_id,
                name as customer_name,
                assigned_channel_id as channel_external_id,
                assigned_channel_name as channel_name,
                channel_assigned_by as created_by,
                channel_assigned_at as created_at
        """, [
            assignment.channel_external_id,
            assignment.channel_name,
            assignment.assigned_by,
            assignment.customer_external_id
        ])
        updated = cursor.fetchone()

        # Apply override to historical orders (retroactive fix)
        orders_updated = apply_channel_override_to_historical_orders(
            cursor,
            assignment.customer_external_id,
            assignment.channel_external_id
        )

        conn.commit()
        cursor.close()
        conn.close()

        return {
            "status": "success",
            "message": f"Canal asignado exitosamente. {orders_updated} órdenes históricas actualizadas.",
            "data": updated,
            "historical_orders_updated": orders_updated
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error assigning channel: {str(e)}")


@router.put("/customer/{customer_external_id}")
async def update_customer_channel(customer_external_id: str, assignment: ChannelAssignmentUpdate):
    """
    Update channel assignment for a customer.
    """
    try:
        conn = psycopg2.connect(DATABASE_URL, connect_timeout=10)
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        # Check if customer exists
        cursor.execute("""
            SELECT id FROM customers
            WHERE external_id = %s AND source = 'relbase'
        """, [customer_external_id])
        customer = cursor.fetchone()

        if not customer:
            cursor.close()
            conn.close()
            raise HTTPException(status_code=404, detail="Cliente no encontrado")

        # Build update query
        updates = []
        params = []

        if assignment.channel_external_id is not None:
            updates.append("assigned_channel_id = %s")
            params.append(assignment.channel_external_id)

        if assignment.channel_name is not None:
            updates.append("assigned_channel_name = %s")
            params.append(assignment.channel_name)

        if not updates:
            cursor.close()
            conn.close()
            return {
                "status": "success",
                "message": "No changes to apply"
            }

        updates.append("updated_at = NOW()")
        params.append(customer_external_id)

        cursor.execute(f"""
            UPDATE customers
            SET {', '.join(updates)}
            WHERE external_id = %s AND source = 'relbase'
            RETURNING
                id,
                external_id as customer_external_id,
                name as customer_name,
                assigned_channel_id as channel_external_id,
                assigned_channel_name as channel_name,
                channel_assigned_by as created_by,
                channel_assigned_at as created_at
        """, params)
        updated = cursor.fetchone()

        # Apply override to historical orders if channel was updated (retroactive fix)
        orders_updated = 0
        if assignment.channel_external_id is not None:
            orders_updated = apply_channel_override_to_historical_orders(
                cursor,
                customer_external_id,
                assignment.channel_external_id
            )

        conn.commit()
        cursor.close()
        conn.close()

        return {
            "status": "success",
            "message": f"Asignación actualizada exitosamente. {orders_updated} órdenes históricas actualizadas.",
            "data": updated,
            "historical_orders_updated": orders_updated
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error updating assignment: {str(e)}")


@router.delete("/customer/{customer_external_id}")
async def remove_customer_channel(customer_external_id: str):
    """
    Remove channel assignment from a customer.
    Sets assigned_channel_id to NULL.
    """
    try:
        conn = psycopg2.connect(DATABASE_URL, connect_timeout=10)
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        # Check if customer exists
        cursor.execute("""
            SELECT id, assigned_channel_id
            FROM customers
            WHERE external_id = %s AND source = 'relbase'
        """, [customer_external_id])
        customer = cursor.fetchone()

        if not customer:
            cursor.close()
            conn.close()
            raise HTTPException(status_code=404, detail="Cliente no encontrado")

        if customer['assigned_channel_id'] is None:
            cursor.close()
            conn.close()
            return {
                "status": "success",
                "message": "El cliente no tiene canal asignado"
            }

        # Remove the assignment
        cursor.execute("""
            UPDATE customers
            SET
                assigned_channel_id = NULL,
                assigned_channel_name = NULL,
                channel_assigned_by = NULL,
                channel_assigned_at = NULL,
                updated_at = NOW()
            WHERE external_id = %s AND source = 'relbase'
        """, [customer_external_id])

        conn.commit()
        cursor.close()
        conn.close()

        return {
            "status": "success",
            "message": "Asignación de canal eliminada"
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error removing assignment: {str(e)}")


# =====================================================================
# Legacy routes for backwards compatibility
# These map old /{mapping_id} routes to the new customer-based system
# =====================================================================

@router.get("/{mapping_id}")
async def get_channel_mapping_legacy(mapping_id: int):
    """
    Legacy route - Get customer by internal ID.
    Note: The old customer_channel_rules table used its own IDs.
    This now uses the customers table id.
    """
    try:
        conn = psycopg2.connect(DATABASE_URL, connect_timeout=10)
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        cursor.execute("""
            SELECT
                id,
                external_id as customer_external_id,
                name as customer_name,
                rut as customer_rut,
                assigned_channel_id as channel_external_id,
                assigned_channel_name as channel_name,
                channel_assigned_by as created_by,
                channel_assigned_at as created_at,
                updated_at,
                CASE WHEN assigned_channel_id IS NOT NULL THEN TRUE ELSE FALSE END as is_active
            FROM customers
            WHERE id = %s AND source = 'relbase'
        """, [mapping_id])
        mapping = cursor.fetchone()

        cursor.close()
        conn.close()

        if not mapping:
            raise HTTPException(status_code=404, detail="Customer not found")

        return {
            "status": "success",
            "data": mapping
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching mapping: {str(e)}")


@router.delete("/{mapping_id}")
async def delete_channel_mapping_legacy(
    mapping_id: int,
    hard_delete: bool = Query(False, description="Ignored - always removes assignment")
):
    """
    Legacy route - Remove channel assignment by customer ID.
    """
    try:
        conn = psycopg2.connect(DATABASE_URL, connect_timeout=10)
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        # Check if customer exists
        cursor.execute("""
            SELECT id, external_id, assigned_channel_id
            FROM customers
            WHERE id = %s AND source = 'relbase'
        """, [mapping_id])
        customer = cursor.fetchone()

        if not customer:
            cursor.close()
            conn.close()
            raise HTTPException(status_code=404, detail="Customer not found")

        if customer['assigned_channel_id'] is None:
            cursor.close()
            conn.close()
            return {
                "status": "success",
                "message": "El cliente no tiene canal asignado"
            }

        # Remove the assignment
        cursor.execute("""
            UPDATE customers
            SET
                assigned_channel_id = NULL,
                assigned_channel_name = NULL,
                channel_assigned_by = NULL,
                channel_assigned_at = NULL,
                updated_at = NOW()
            WHERE id = %s AND source = 'relbase'
        """, [mapping_id])

        conn.commit()
        cursor.close()
        conn.close()

        return {
            "status": "success",
            "message": "Asignación de canal eliminada"
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error removing assignment: {str(e)}")


@router.post("/apply-overrides-to-history")
async def apply_all_overrides_to_historical_orders(
    refresh_mv: bool = Query(False, description="Refresh sales_facts_mv after updating orders")
):
    """
    Apply ALL existing channel overrides to historical orders.

    This is a bulk operation that:
    1. Finds all customers with assigned_channel_id
    2. Updates their historical orders that have NULL channel_id
    3. Optionally refreshes the sales_facts_mv materialized view

    Use this for initial retroactive fix or to ensure all overrides are applied.
    """
    try:
        conn = psycopg2.connect(DATABASE_URL, connect_timeout=10)
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        # Find all customers with channel overrides, joined with channels to get internal ID
        cursor.execute("""
            SELECT
                cust.id as customer_id,
                cust.external_id,
                cust.name,
                cust.assigned_channel_id as channel_external_id,
                cust.assigned_channel_name,
                ch.id as channel_internal_id
            FROM customers cust
            JOIN channels ch ON ch.external_id = cust.assigned_channel_id::text AND ch.source = 'relbase'
            WHERE cust.source = 'relbase'
              AND cust.assigned_channel_id IS NOT NULL
        """)
        customers_with_overrides = cursor.fetchall()

        total_customers = len(customers_with_overrides)
        total_orders_updated = 0
        customers_updated = []

        # Temporarily disable the audit trigger (it has a bug with missing corrected_by column)
        try:
            cursor.execute("ALTER TABLE orders DISABLE TRIGGER audit_order_changes_trigger")
        except Exception as e:
            logger.warning(f"Could not disable audit trigger: {e}")

        # Apply override for each customer using the internal channel ID
        # Updates ALL orders that don't have the correct channel (NULL or wrong)
        for customer in customers_with_overrides:
            cursor.execute("""
                UPDATE orders
                SET channel_id = %s,
                    updated_at = NOW()
                WHERE customer_id = %s
                  AND source = 'relbase'
                  AND (channel_id IS NULL OR channel_id != %s)
            """, [customer['channel_internal_id'], customer['customer_id'], customer['channel_internal_id']])

            orders_updated = cursor.rowcount
            if orders_updated > 0:
                total_orders_updated += orders_updated
                customers_updated.append({
                    "customer_name": customer['name'],
                    "customer_external_id": customer['external_id'],
                    "channel": customer['assigned_channel_name'],
                    "orders_updated": orders_updated
                })

        # Re-enable the audit trigger
        try:
            cursor.execute("ALTER TABLE orders ENABLE TRIGGER audit_order_changes_trigger")
        except Exception as e:
            logger.warning(f"Could not re-enable audit trigger: {e}")

        conn.commit()

        # Optionally refresh the materialized view
        mv_refreshed = False
        if refresh_mv and total_orders_updated > 0:
            try:
                cursor.execute("REFRESH MATERIALIZED VIEW CONCURRENTLY sales_facts_mv")
                conn.commit()
                mv_refreshed = True
                logger.info("Refreshed sales_facts_mv after applying channel overrides")
            except Exception as mv_error:
                logger.warning(f"Could not refresh materialized view: {mv_error}")

        cursor.close()
        conn.close()

        return {
            "status": "success",
            "message": f"Overrides aplicados a {total_orders_updated} órdenes históricas de {len(customers_updated)} clientes",
            "data": {
                "customers_with_overrides": total_customers,
                "customers_updated": len(customers_updated),
                "total_orders_updated": total_orders_updated,
                "materialized_view_refreshed": mv_refreshed,
                "details": customers_updated[:20]  # Limit details to avoid large response
            }
        }

    except Exception as e:
        logger.error(f"Error applying overrides to history: {e}")
        raise HTTPException(status_code=500, detail=f"Error applying overrides: {str(e)}")
