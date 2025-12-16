"""
SKU Mappings API Endpoints
CRUD operations for managing SKU mapping rules

Purpose:
- List, create, update, delete SKU mapping rules
- Test SKU against active rules
- Get catalog SKUs for dropdown

Author: TM3
Date: 2025-12-10
"""
from fastapi import APIRouter, HTTPException, Query
from typing import Optional, List, Literal
from pydantic import BaseModel, Field
import os
import psycopg2
from psycopg2.extras import RealDictCursor

from app.services.sku_mapping_service import get_sku_mapping_service

router = APIRouter()

# Database connection
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    # Fallback for local development
    DATABASE_URL = "postgresql://postgres.lypuvibmtxjaxmcmahxr:%24Ilofono1@aws-1-sa-east-1.pooler.supabase.com:6543/postgres"


# =====================================================================
# Pydantic Models
# =====================================================================

class SKUMappingCreate(BaseModel):
    """Request model for creating a new SKU mapping"""
    source_pattern: str = Field(..., min_length=1, max_length=255, description="Raw SKU pattern to match")
    pattern_type: Literal['exact', 'prefix', 'suffix', 'regex', 'contains'] = Field(..., description="How to match the pattern")
    target_sku: str = Field(..., min_length=1, max_length=100, description="Target SKU from product_catalog")
    source_filter: Optional[str] = Field(None, max_length=50, description="Optional source filter (relbase, mercadolibre, etc.)")
    quantity_multiplier: int = Field(default=1, ge=1, description="Quantity multiplier for pack rules")
    rule_name: Optional[str] = Field(None, max_length=100, description="Human-readable rule name")
    confidence: int = Field(default=100, ge=0, le=100, description="Confidence score (0-100)")
    priority: int = Field(default=50, ge=0, le=100, description="Priority (higher = checked first)")
    notes: Optional[str] = Field(None, description="Notes about why this mapping exists")


class SKUMappingUpdate(BaseModel):
    """Request model for updating an existing SKU mapping"""
    source_pattern: Optional[str] = Field(None, min_length=1, max_length=255)
    pattern_type: Optional[Literal['exact', 'prefix', 'suffix', 'regex', 'contains']] = None
    target_sku: Optional[str] = Field(None, min_length=1, max_length=100)
    source_filter: Optional[str] = Field(None, max_length=50)
    quantity_multiplier: Optional[int] = Field(None, ge=1)
    rule_name: Optional[str] = Field(None, max_length=100)
    confidence: Optional[int] = Field(None, ge=0, le=100)
    priority: Optional[int] = Field(None, ge=0, le=100)
    is_active: Optional[bool] = None
    notes: Optional[str] = None


class SKUTestRequest(BaseModel):
    """Request model for testing a SKU"""
    sku: str = Field(..., min_length=1, description="SKU to test")
    source: Optional[str] = Field(None, description="Optional source filter")


# =====================================================================
# API Endpoints
# =====================================================================

@router.get("/")
async def list_mappings(
    pattern_type: Optional[str] = Query(None, description="Filter by pattern type"),
    source_filter: Optional[str] = Query(None, description="Filter by source"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    search: Optional[str] = Query(None, description="Search in source_pattern, target_sku, or rule_name"),
    limit: int = Query(50, ge=1, le=500, description="Max results to return"),
    offset: int = Query(0, ge=0, description="Offset for pagination")
):
    """
    List all SKU mappings with filters and pagination.

    Returns mappings ordered by priority DESC.
    """
    try:
        conn = psycopg2.connect(DATABASE_URL, connect_timeout=10)
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        # Build query
        where_clauses = []
        params = []

        if pattern_type:
            where_clauses.append("pattern_type = %s")
            params.append(pattern_type)

        if source_filter:
            where_clauses.append("source_filter = %s")
            params.append(source_filter)

        if is_active is not None:
            where_clauses.append("is_active = %s")
            params.append(is_active)

        if search:
            where_clauses.append("""
                (source_pattern ILIKE %s OR target_sku ILIKE %s OR rule_name ILIKE %s)
            """)
            search_param = f"%{search}%"
            params.extend([search_param, search_param, search_param])

        where_sql = " AND ".join(where_clauses) if where_clauses else "TRUE"

        # Get total count
        count_sql = f"SELECT COUNT(*) FROM sku_mappings WHERE {where_sql}"
        cursor.execute(count_sql, params)
        total = cursor.fetchone()['count']

        # Get paginated results
        query_sql = f"""
            SELECT
                id,
                source_pattern,
                pattern_type,
                source_filter,
                target_sku,
                quantity_multiplier,
                rule_name,
                confidence,
                priority,
                is_active,
                created_at,
                updated_at,
                created_by,
                notes
            FROM sku_mappings
            WHERE {where_sql}
            ORDER BY priority DESC, id ASC
            LIMIT %s OFFSET %s
        """
        cursor.execute(query_sql, params + [limit, offset])
        mappings = cursor.fetchall()

        cursor.close()
        conn.close()

        return {
            "status": "success",
            "total": total,
            "limit": limit,
            "offset": offset,
            "count": len(mappings),
            "data": [dict(m) for m in mappings]
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching mappings: {str(e)}")


@router.get("/stats")
async def get_mapping_stats():
    """
    Get statistics about SKU mappings.

    Returns counts by type, source, and active status.
    """
    try:
        service = get_sku_mapping_service()
        stats = service.get_mapping_stats()

        # Get additional stats from database
        conn = psycopg2.connect(DATABASE_URL, connect_timeout=10)
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        # Count inactive mappings
        cursor.execute("SELECT COUNT(*) FROM sku_mappings WHERE is_active = FALSE")
        inactive = cursor.fetchone()['count']

        cursor.close()
        conn.close()

        return {
            "status": "success",
            "data": {
                "total_active": stats['total'],
                "total_inactive": inactive,
                "by_type": stats['by_type'],
                "by_source": stats['by_source'],
                "cache_valid": stats['cache_valid']
            }
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching stats: {str(e)}")


@router.get("/catalog-skus")
async def get_catalog_skus(
    search: Optional[str] = Query(None, description="Search by SKU or product name"),
    category: Optional[str] = Query(None, description="Filter by category"),
    limit: int = Query(100, ge=1, le=500)
):
    """
    Get list of valid target SKUs from product_catalog.

    Used for the target SKU dropdown in the UI.
    """
    try:
        conn = psycopg2.connect(DATABASE_URL, connect_timeout=10)
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        where_clauses = ["is_active = TRUE"]
        params = []

        if search:
            where_clauses.append("(sku ILIKE %s OR product_name ILIKE %s)")
            search_param = f"%{search}%"
            params.extend([search_param, search_param])

        if category:
            where_clauses.append("category = %s")
            params.append(category)

        where_sql = " AND ".join(where_clauses)

        cursor.execute(f"""
            SELECT
                sku,
                product_name,
                category,
                units_per_display
            FROM product_catalog
            WHERE {where_sql}
            ORDER BY sku
            LIMIT %s
        """, params + [limit])

        skus = cursor.fetchall()

        cursor.close()
        conn.close()

        return {
            "status": "success",
            "count": len(skus),
            "data": [dict(s) for s in skus]
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching catalog SKUs: {str(e)}")


@router.get("/{mapping_id}")
async def get_mapping(mapping_id: int):
    """
    Get a single SKU mapping by ID.
    """
    try:
        conn = psycopg2.connect(DATABASE_URL, connect_timeout=10)
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        cursor.execute("""
            SELECT
                id,
                source_pattern,
                pattern_type,
                source_filter,
                target_sku,
                quantity_multiplier,
                rule_name,
                confidence,
                priority,
                is_active,
                created_at,
                updated_at,
                created_by,
                notes
            FROM sku_mappings
            WHERE id = %s
        """, (mapping_id,))

        mapping = cursor.fetchone()

        cursor.close()
        conn.close()

        if not mapping:
            raise HTTPException(status_code=404, detail=f"Mapping with id {mapping_id} not found")

        return {
            "status": "success",
            "data": dict(mapping)
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching mapping: {str(e)}")


@router.post("/")
async def create_mapping(mapping: SKUMappingCreate):
    """
    Create a new SKU mapping.

    Validates that target_sku exists in product_catalog.
    """
    try:
        conn = psycopg2.connect(DATABASE_URL, connect_timeout=10)
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        # Validate target_sku exists in product_catalog
        cursor.execute("""
            SELECT sku FROM product_catalog WHERE sku = %s AND is_active = TRUE
        """, (mapping.target_sku,))

        if not cursor.fetchone():
            cursor.close()
            conn.close()
            raise HTTPException(
                status_code=400,
                detail=f"Target SKU '{mapping.target_sku}' does not exist in product_catalog"
            )

        # Check for duplicate exact mapping (same source_pattern + target_sku combination)
        # Allow multiple target_skus for the same source_pattern (e.g., pack with multiple products)
        if mapping.pattern_type == 'exact':
            cursor.execute("""
                SELECT id FROM sku_mappings
                WHERE source_pattern = %s
                AND target_sku = %s
                AND (source_filter = %s OR (source_filter IS NULL AND %s IS NULL))
                AND is_active = TRUE
            """, (mapping.source_pattern, mapping.target_sku, mapping.source_filter, mapping.source_filter))

            if cursor.fetchone():
                cursor.close()
                conn.close()
                raise HTTPException(
                    status_code=400,
                    detail=f"An active mapping for '{mapping.source_pattern}' → '{mapping.target_sku}' already exists"
                )

        # Insert new mapping
        cursor.execute("""
            INSERT INTO sku_mappings (
                source_pattern,
                pattern_type,
                source_filter,
                target_sku,
                quantity_multiplier,
                rule_name,
                confidence,
                priority,
                notes
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id, created_at
        """, (
            mapping.source_pattern,
            mapping.pattern_type,
            mapping.source_filter,
            mapping.target_sku,
            mapping.quantity_multiplier,
            mapping.rule_name,
            mapping.confidence,
            mapping.priority,
            mapping.notes
        ))

        result = cursor.fetchone()
        conn.commit()

        cursor.close()
        conn.close()

        # Invalidate cache
        service = get_sku_mapping_service()
        service.invalidate_cache()

        return {
            "status": "success",
            "message": "Mapping created successfully",
            "data": {
                "id": result['id'],
                "created_at": result['created_at']
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating mapping: {str(e)}")


@router.put("/{mapping_id}")
async def update_mapping(mapping_id: int, mapping: SKUMappingUpdate):
    """
    Update an existing SKU mapping.

    Only provided fields are updated.
    """
    try:
        conn = psycopg2.connect(DATABASE_URL, connect_timeout=10)
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        # Check mapping exists
        cursor.execute("SELECT id FROM sku_mappings WHERE id = %s", (mapping_id,))
        if not cursor.fetchone():
            cursor.close()
            conn.close()
            raise HTTPException(status_code=404, detail=f"Mapping with id {mapping_id} not found")

        # Validate target_sku if provided
        if mapping.target_sku:
            cursor.execute("""
                SELECT sku FROM product_catalog WHERE sku = %s AND is_active = TRUE
            """, (mapping.target_sku,))

            if not cursor.fetchone():
                cursor.close()
                conn.close()
                raise HTTPException(
                    status_code=400,
                    detail=f"Target SKU '{mapping.target_sku}' does not exist in product_catalog"
                )

        # Build update query
        update_fields = []
        params = []

        update_dict = mapping.dict(exclude_unset=True)
        for field, value in update_dict.items():
            update_fields.append(f"{field} = %s")
            params.append(value)

        if not update_fields:
            cursor.close()
            conn.close()
            raise HTTPException(status_code=400, detail="No fields to update")

        params.append(mapping_id)

        cursor.execute(f"""
            UPDATE sku_mappings
            SET {', '.join(update_fields)}, updated_at = NOW()
            WHERE id = %s
            RETURNING id, updated_at
        """, params)

        result = cursor.fetchone()
        conn.commit()

        cursor.close()
        conn.close()

        # Invalidate cache
        service = get_sku_mapping_service()
        service.invalidate_cache()

        return {
            "status": "success",
            "message": "Mapping updated successfully",
            "data": {
                "id": result['id'],
                "updated_at": result['updated_at']
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error updating mapping: {str(e)}")


@router.delete("/{mapping_id}")
async def delete_mapping(mapping_id: int, hard_delete: bool = Query(False, description="Permanently delete instead of soft delete")):
    """
    Delete a SKU mapping.

    By default, performs soft delete (sets is_active=FALSE).
    Use hard_delete=true for permanent deletion.
    """
    try:
        conn = psycopg2.connect(DATABASE_URL, connect_timeout=10)
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        # Check mapping exists
        cursor.execute("SELECT id, source_pattern FROM sku_mappings WHERE id = %s", (mapping_id,))
        mapping = cursor.fetchone()

        if not mapping:
            cursor.close()
            conn.close()
            raise HTTPException(status_code=404, detail=f"Mapping with id {mapping_id} not found")

        if hard_delete:
            cursor.execute("DELETE FROM sku_mappings WHERE id = %s", (mapping_id,))
            action = "permanently deleted"
        else:
            cursor.execute("""
                UPDATE sku_mappings
                SET is_active = FALSE, updated_at = NOW()
                WHERE id = %s
            """, (mapping_id,))
            action = "deactivated"

        conn.commit()

        cursor.close()
        conn.close()

        # Invalidate cache
        service = get_sku_mapping_service()
        service.invalidate_cache()

        return {
            "status": "success",
            "message": f"Mapping '{mapping['source_pattern']}' {action}",
            "data": {"id": mapping_id}
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error deleting mapping: {str(e)}")


@router.post("/test")
async def test_mapping(request: SKUTestRequest):
    """
    Test a SKU against all active mapping rules.

    Returns which rule (if any) would match, without actually mapping.
    Useful for previewing mappings in the UI.
    """
    try:
        service = get_sku_mapping_service()
        result = service.test_sku(request.sku, request.source)

        return {
            "status": "success",
            "data": result
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error testing SKU: {str(e)}")


@router.post("/reload-cache")
async def reload_cache():
    """
    Force reload the mappings cache from database.

    Useful after bulk updates or for debugging.
    """
    try:
        service = get_sku_mapping_service()
        service.reload_mappings()

        return {
            "status": "success",
            "message": "Cache reloaded successfully",
            "data": service.get_mapping_stats()
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reloading cache: {str(e)}")


@router.get("/order-skus/unmapped")
async def get_unmapped_order_skus(
    search: Optional[str] = Query(None, description="Search in SKU"),
    limit: int = Query(100, ge=1, le=1000, description="Max results to return"),
    offset: int = Query(0, ge=0, description="Offset for pagination")
):
    """
    Get all unique SKUs from order_items that don't have a mapping.

    These are SKUs that:
    1. Exist in order_items.product_sku
    2. Don't have an active mapping in sku_mappings.source_pattern
    3. Don't exist directly in product_catalog.sku

    Returns SKUs with order count and total revenue to help prioritize.
    """
    try:
        conn = psycopg2.connect(DATABASE_URL, connect_timeout=10)
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        # Build search clause
        search_clause = ""
        params = []
        if search:
            search_clause = "AND oi.product_sku ILIKE %s"
            params.append(f"%{search}%")

        # Query to find unmapped SKUs with aggregated info
        # Only include orders from 2025 (active/current SKUs)
        # Check both product_catalog.sku AND product_catalog.sku_master (caja master codes)
        query = f"""
            WITH order_skus AS (
                SELECT
                    oi.product_sku as sku,
                    MAX(oi.product_name) as product_name,
                    COUNT(DISTINCT oi.order_id) as order_count,
                    SUM(oi.quantity) as total_quantity,
                    SUM(oi.subtotal) as total_revenue,
                    MAX(o.order_date) as last_order_date
                FROM order_items oi
                JOIN orders o ON o.id = oi.order_id
                WHERE oi.product_sku IS NOT NULL
                AND oi.product_sku != ''
                AND EXTRACT(YEAR FROM o.order_date) = 2025
                {search_clause}
                GROUP BY oi.product_sku
            )
            SELECT
                os.sku,
                os.product_name,
                os.order_count,
                os.total_quantity,
                os.total_revenue,
                os.last_order_date
            FROM order_skus os
            WHERE NOT EXISTS (
                SELECT 1 FROM sku_mappings sm
                WHERE sm.source_pattern = os.sku
                AND sm.is_active = TRUE
            )
            AND NOT EXISTS (
                SELECT 1 FROM product_catalog pc
                WHERE pc.sku = os.sku
                AND pc.is_active = TRUE
            )
            AND NOT EXISTS (
                SELECT 1 FROM product_catalog pc
                WHERE pc.sku_master = os.sku
                AND pc.is_active = TRUE
            )
            ORDER BY os.total_revenue DESC NULLS LAST, os.order_count DESC
        """

        # Get total count first (only 2025 orders, check both sku and sku_master)
        count_query = f"""
            WITH order_skus AS (
                SELECT DISTINCT oi.product_sku as sku
                FROM order_items oi
                JOIN orders o ON o.id = oi.order_id
                WHERE oi.product_sku IS NOT NULL
                AND oi.product_sku != ''
                AND EXTRACT(YEAR FROM o.order_date) = 2025
                {search_clause}
            )
            SELECT COUNT(*)
            FROM order_skus os
            WHERE NOT EXISTS (
                SELECT 1 FROM sku_mappings sm
                WHERE sm.source_pattern = os.sku
                AND sm.is_active = TRUE
            )
            AND NOT EXISTS (
                SELECT 1 FROM product_catalog pc
                WHERE pc.sku = os.sku
                AND pc.is_active = TRUE
            )
            AND NOT EXISTS (
                SELECT 1 FROM product_catalog pc
                WHERE pc.sku_master = os.sku
                AND pc.is_active = TRUE
            )
        """
        cursor.execute(count_query, params)
        total = cursor.fetchone()['count']

        # Get paginated results
        paginated_query = query + " LIMIT %s OFFSET %s"
        cursor.execute(paginated_query, params + [limit, offset])
        unmapped_skus = cursor.fetchall()

        cursor.close()
        conn.close()

        return {
            "status": "success",
            "total": total,
            "limit": limit,
            "offset": offset,
            "count": len(unmapped_skus),
            "data": [dict(s) for s in unmapped_skus]
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching unmapped SKUs: {str(e)}")


@router.get("/order-skus/all")
async def get_all_order_skus(
    search: Optional[str] = Query(None, description="Search in SKU"),
    mapped_only: bool = Query(False, description="Only show mapped SKUs"),
    unmapped_only: bool = Query(False, description="Only show unmapped SKUs"),
    limit: int = Query(100, ge=1, le=1000, description="Max results to return"),
    offset: int = Query(0, ge=0, description="Offset for pagination")
):
    """
    Get all unique SKUs from order_items with their mapping status.

    Shows whether each SKU:
    - Has a mapping in sku_mappings
    - Exists directly in product_catalog
    - Has no mapping (needs attention)
    """
    try:
        conn = psycopg2.connect(DATABASE_URL, connect_timeout=10)
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        # Build search clause
        search_clause = ""
        params = []
        if search:
            search_clause = "AND oi.product_sku ILIKE %s"
            params.append(f"%{search}%")

        # Base query with mapping status (only 2025 orders)
        # Check both product_catalog.sku AND product_catalog.sku_master (caja master codes)
        # Aggregate multiple mapping components into JSON array for pack products
        base_query = f"""
            WITH order_skus AS (
                SELECT
                    oi.product_sku as sku,
                    MAX(oi.product_name) as product_name,
                    COUNT(DISTINCT oi.order_id) as order_count,
                    SUM(oi.quantity) as total_quantity,
                    SUM(oi.subtotal) as total_revenue,
                    MAX(o.order_date) as last_order_date
                FROM order_items oi
                JOIN orders o ON o.id = oi.order_id
                WHERE oi.product_sku IS NOT NULL
                AND oi.product_sku != ''
                AND EXTRACT(YEAR FROM o.order_date) = 2025
                {search_clause}
                GROUP BY oi.product_sku
            ),
            mapping_components AS (
                SELECT
                    source_pattern,
                    json_agg(json_build_object(
                        'id', id,
                        'target_sku', target_sku,
                        'quantity_multiplier', quantity_multiplier,
                        'rule_name', rule_name
                    ) ORDER BY id) as components,
                    COUNT(*) as component_count
                FROM sku_mappings
                WHERE is_active = TRUE
                GROUP BY source_pattern
            )
            SELECT
                os.sku,
                -- Use canonical product name from product_catalog when available
                COALESCE(
                    pc_direct.product_name,      -- SKU matches product_catalog.sku
                    pc_master.master_box_name,   -- SKU matches product_catalog.sku_master (caja master)
                    os.product_name              -- Fallback to order_items name for unmapped
                ) as product_name,
                os.order_count,
                os.total_quantity,
                os.total_revenue,
                os.last_order_date,
                CASE
                    WHEN mc.source_pattern IS NOT NULL THEN 'mapped'
                    WHEN pc_direct.sku IS NOT NULL THEN 'in_catalog'
                    WHEN pc_master.sku IS NOT NULL THEN 'in_catalog'
                    ELSE 'unmapped'
                END as mapping_status,
                COALESCE(
                    (mc.components->0->>'target_sku'),
                    pc_master.sku
                ) as mapped_to,
                COALESCE(
                    (mc.components->0->>'quantity_multiplier')::int,
                    pc_master.items_per_master_box
                ) as quantity_multiplier,
                COALESCE(
                    (mc.components->0->>'rule_name'),
                    CASE WHEN pc_master.sku IS NOT NULL THEN 'Caja Master' ELSE NULL END
                ) as rule_name,
                mc.components as mapping_components,
                COALESCE(mc.component_count, 0) as component_count
            FROM order_skus os
            LEFT JOIN mapping_components mc ON mc.source_pattern = os.sku
            LEFT JOIN product_catalog pc_direct ON pc_direct.sku = os.sku AND pc_direct.is_active = TRUE
            LEFT JOIN product_catalog pc_master ON pc_master.sku_master = os.sku AND pc_master.is_active = TRUE
        """

        # Add filter for mapped/unmapped (check both sku and sku_master)
        filter_clause = ""
        if mapped_only:
            filter_clause = "WHERE mc.source_pattern IS NOT NULL OR pc_direct.sku IS NOT NULL OR pc_master.sku IS NOT NULL"
        elif unmapped_only:
            filter_clause = "WHERE mc.source_pattern IS NULL AND pc_direct.sku IS NULL AND pc_master.sku IS NULL"

        # Count query (only 2025 orders, check both sku and sku_master)
        count_query = f"""
            WITH order_skus AS (
                SELECT DISTINCT oi.product_sku as sku
                FROM order_items oi
                JOIN orders o ON o.id = oi.order_id
                WHERE oi.product_sku IS NOT NULL
                AND oi.product_sku != ''
                AND EXTRACT(YEAR FROM o.order_date) = 2025
                {search_clause}
            ),
            mapping_sources AS (
                SELECT DISTINCT source_pattern
                FROM sku_mappings
                WHERE is_active = TRUE
            )
            SELECT COUNT(*)
            FROM order_skus os
            LEFT JOIN mapping_sources mc ON mc.source_pattern = os.sku
            LEFT JOIN product_catalog pc_direct ON pc_direct.sku = os.sku AND pc_direct.is_active = TRUE
            LEFT JOIN product_catalog pc_master ON pc_master.sku_master = os.sku AND pc_master.is_active = TRUE
            {filter_clause}
        """
        cursor.execute(count_query, params)
        total = cursor.fetchone()['count']

        # Full query with pagination
        full_query = f"""
            {base_query}
            {filter_clause}
            ORDER BY
                CASE WHEN mc.source_pattern IS NULL AND pc_direct.sku IS NULL AND pc_master.sku IS NULL THEN 0 ELSE 1 END,
                os.total_revenue DESC NULLS LAST,
                os.order_count DESC
            LIMIT %s OFFSET %s
        """
        cursor.execute(full_query, params + [limit, offset])
        skus = cursor.fetchall()

        cursor.close()
        conn.close()

        return {
            "status": "success",
            "total": total,
            "limit": limit,
            "offset": offset,
            "count": len(skus),
            "data": [dict(s) for s in skus]
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching order SKUs: {str(e)}")


@router.get("/order-skus/stats")
async def get_order_skus_stats():
    """
    Get statistics about order SKUs and their mapping status.

    Critical KPI: Shows how many SKUs from orders are unmapped.
    """
    try:
        conn = psycopg2.connect(DATABASE_URL, connect_timeout=10)
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        # Only include orders from 2025 (active/current SKUs)
        # Check both product_catalog.sku AND product_catalog.sku_master (caja master codes)
        cursor.execute("""
            WITH order_skus AS (
                SELECT DISTINCT oi.product_sku as sku
                FROM order_items oi
                JOIN orders o ON o.id = oi.order_id
                WHERE oi.product_sku IS NOT NULL
                AND oi.product_sku != ''
                AND EXTRACT(YEAR FROM o.order_date) = 2025
            ),
            sku_status AS (
                SELECT
                    os.sku,
                    CASE
                        WHEN sm.id IS NOT NULL THEN 'mapped'
                        WHEN pc_direct.sku IS NOT NULL THEN 'in_catalog'
                        WHEN pc_master.sku IS NOT NULL THEN 'in_catalog'
                        ELSE 'unmapped'
                    END as status
                FROM order_skus os
                LEFT JOIN sku_mappings sm ON sm.source_pattern = os.sku AND sm.is_active = TRUE
                LEFT JOIN product_catalog pc_direct ON pc_direct.sku = os.sku AND pc_direct.is_active = TRUE
                LEFT JOIN product_catalog pc_master ON pc_master.sku_master = os.sku AND pc_master.is_active = TRUE
            )
            SELECT
                COUNT(*) as total_skus,
                COUNT(*) FILTER (WHERE status = 'mapped') as mapped_count,
                COUNT(*) FILTER (WHERE status = 'in_catalog') as in_catalog_count,
                COUNT(*) FILTER (WHERE status = 'unmapped') as unmapped_count
            FROM sku_status
        """)

        stats = cursor.fetchone()

        # Get total revenue from unmapped SKUs (only 2025 orders)
        # Check both product_catalog.sku AND product_catalog.sku_master (caja master codes)
        cursor.execute("""
            WITH order_skus AS (
                SELECT
                    oi.product_sku as sku,
                    SUM(oi.subtotal) as revenue
                FROM order_items oi
                JOIN orders o ON o.id = oi.order_id
                WHERE oi.product_sku IS NOT NULL
                AND oi.product_sku != ''
                AND EXTRACT(YEAR FROM o.order_date) = 2025
                GROUP BY oi.product_sku
            )
            SELECT COALESCE(SUM(os.revenue), 0) as unmapped_revenue
            FROM order_skus os
            WHERE NOT EXISTS (
                SELECT 1 FROM sku_mappings sm
                WHERE sm.source_pattern = os.sku
                AND sm.is_active = TRUE
            )
            AND NOT EXISTS (
                SELECT 1 FROM product_catalog pc
                WHERE pc.sku = os.sku
                AND pc.is_active = TRUE
            )
            AND NOT EXISTS (
                SELECT 1 FROM product_catalog pc
                WHERE pc.sku_master = os.sku
                AND pc.is_active = TRUE
            )
        """)

        unmapped_revenue = cursor.fetchone()['unmapped_revenue']

        cursor.close()
        conn.close()

        return {
            "status": "success",
            "data": {
                "total_order_skus": stats['total_skus'],
                "mapped_count": stats['mapped_count'],
                "in_catalog_count": stats['in_catalog_count'],
                "unmapped_count": stats['unmapped_count'],
                "unmapped_revenue": float(unmapped_revenue) if unmapped_revenue else 0,
                "coverage_percent": round(
                    (stats['mapped_count'] + stats['in_catalog_count']) / stats['total_skus'] * 100, 1
                ) if stats['total_skus'] > 0 else 0
            }
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching order SKU stats: {str(e)}")
