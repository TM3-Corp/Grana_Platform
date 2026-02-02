"""
API endpoints for warehouse inventory management.

This module provides endpoints for the new warehouse-based inventory system:
- GET /api/v1/warehouses - List all warehouses
- GET /api/v1/warehouse-inventory/general - Consolidated inventory view (all warehouses)
- GET /api/v1/warehouse-inventory/warehouse/{code} - Specific warehouse inventory
- GET /api/v1/warehouse-inventory/summary - Inventory summary statistics
- POST /api/v1/warehouse-inventory/upload - Upload Excel file to update inventory

Author: TM3
Date: 2025-11-13
"""
from fastapi import APIRouter, HTTPException, Path, Query, UploadFile, File
from typing import Dict, List, Optional
from pydantic import BaseModel
import pandas as pd
import io
from datetime import datetime

from app.core.database import get_db_connection_dict_with_retry


# ============================================================================
# ROUTERS
# ============================================================================

# Router for warehouse operations
warehouses_router = APIRouter(prefix="/api/v1/warehouses", tags=["warehouses"])

# Router for warehouse inventory operations (distinct from old inventory module)
inventory_router = APIRouter(prefix="/api/v1/warehouse-inventory", tags=["warehouse-inventory"])


# ============================================================================
# RESPONSE MODELS
# ============================================================================

class WarehouseModel(BaseModel):
    """Warehouse response model"""
    id: int
    code: str
    name: str
    location: Optional[str]
    update_method: str  # 'manual_upload' or 'api'
    is_active: bool

    class Config:
        from_attributes = True


class InventoryGeneralItem(BaseModel):
    """Item in general inventory view"""
    sku: str
    name: str
    category: Optional[str]
    subfamily: Optional[str]
    stock_amplifica_centro: int
    stock_amplifica_lareina: int
    stock_amplifica_lobarnechea: int
    stock_amplifica_quilicura: int
    stock_packner: int
    stock_orinoco: int
    stock_mercadolibre: int
    stock_total: int
    last_updated: Optional[str]


class WarehouseInventoryItem(BaseModel):
    """Item in warehouse-specific inventory"""
    sku: str
    name: str
    category: Optional[str]
    stock: int
    percentage_of_total: float


# ============================================================================
# ENDPOINT: GET /api/v1/warehouses
# ============================================================================

@warehouses_router.get("", response_model=Dict)
async def get_warehouses():
    """
    Get list of all warehouses

    Returns:
        {
            "status": "success",
            "data": [
                {
                    "id": 1,
                    "code": "amplifica_centro",
                    "name": "Amplifica - Centro",
                    "location": "Santiago Centro",
                    "update_method": "manual_upload",
                    "is_active": true
                },
                ...
            ]
        }
    """
    conn = None
    cursor = None
    try:
        conn = get_db_connection_dict_with_retry()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT id, code, name, location, update_method, is_active, external_id, source
            FROM warehouses
            WHERE is_active = true
              AND source = 'relbase'
              AND external_id IS NOT NULL
            ORDER BY
                CASE
                    WHEN code LIKE 'amplifica%' THEN 1
                    WHEN code ILIKE '%klog%' THEN 2
                    WHEN code = 'packner' THEN 3
                    WHEN code = 'orinoco' THEN 4
                    WHEN code LIKE 'mercado%' THEN 5
                    WHEN code = 'mi_bodega' THEN 6
                    WHEN code LIKE 'produccion%' THEN 7
                    ELSE 8
                END,
                name
        """)

        warehouses = cursor.fetchall()

        return {
            "status": "success",
            "data": warehouses
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching warehouses: {str(e)}")
    finally:
        # Always close cursor and connection to prevent leaks
        if cursor:
            cursor.close()
        if conn:
            conn.close()


# ============================================================================
# ENDPOINT: GET /api/v1/inventory/general
# ============================================================================

@inventory_router.get("/general", response_model=Dict)
async def get_inventory_general(
    search: Optional[str] = Query(None, description="Search by SKU or product name"),
    category: Optional[str] = Query(None, description="Filter by category"),
    only_with_stock: bool = Query(False, description="Show only products with stock > 0"),
    warehouse_group: Optional[str] = Query(None, description="Filter by warehouse group (e.g., 'amplifica')"),
    show_unmapped: bool = Query(True, description="Show products not in product_catalog")
):
    """
    Get consolidated inventory view with SKU mapping and dynamic warehouse columns.

    This endpoint applies the same SKU mapping logic as Desglose Pedidos:
    1. Maps raw SKUs (e.g., PACKGRCA_U26010) to canonical product_catalog SKUs (GRCA_U26010)
    2. Applies quantity multipliers for PACK products (e.g., 1× PACK = 4× base units)
    3. Consolidates stock under the mapped SKU
    4. Returns in_catalog flag for warning indicator

    Query Parameters:
        - search: Filter by SKU or product name (optional)
        - category: Filter by category (optional)
        - only_with_stock: Show only products with stock (optional)
        - warehouse_group: Filter by warehouse group (optional)
        - show_unmapped: Show products not in product_catalog (default: true)

    Returns:
        {
            "status": "success",
            "data": [
                {
                    "sku": "GRCA_U26010",
                    "original_skus": ["GRCA_U26010", "PACKGRCA_U26010"],
                    "name": "Granola Low Carb Cacao 260 Grs",
                    "category": "GRANOLAS",
                    "warehouses": {"mi_bodega": 90, ...},
                    "stock_total": 90,
                    "in_catalog": true,
                    ...
                },
                ...
            ]
        }
    """
    conn = None
    cursor = None
    try:
        conn = get_db_connection_dict_with_retry()
        cursor = conn.cursor()

        # Build filter conditions
        filter_conditions = []
        params = []

        if search:
            filter_conditions.append("""
                (final.sku ILIKE %s OR final.name ILIKE %s OR
                 EXISTS (SELECT 1 FROM unnest(final.original_skus) os WHERE os ILIKE %s))
            """)
            params.extend([f"%{search}%", f"%{search}%", f"%{search}%"])

        if category:
            filter_conditions.append("final.category = %s")
            params.append(category)

        if only_with_stock:
            filter_conditions.append("final.stock_total > 0")

        if not show_unmapped:
            filter_conditions.append("final.in_catalog = true")

        filter_clause = " AND ".join(filter_conditions) if filter_conditions else "1=1"

        # Main query with SKU mapping and consolidation
        # Flow: raw inventory → apply sku_mappings → aggregate by mapped SKU → join product_catalog
        query = f"""
            WITH raw_inventory AS (
                -- Step 1: Get raw inventory per product-warehouse with SKU from products table
                SELECT
                    p.sku as original_sku,
                    p.name as original_name,
                    w.code as warehouse_code,
                    SUM(ws.quantity) as raw_quantity,
                    COUNT(ws.id) as lot_count,
                    MAX(ws.last_updated) as last_updated
                FROM warehouse_stock ws
                JOIN products p ON p.id = ws.product_id
                JOIN warehouses w ON w.id = ws.warehouse_id
                WHERE w.is_active = true
                  AND w.source = 'relbase'
                  AND w.external_id IS NOT NULL
                  AND p.is_active = true
                GROUP BY p.sku, p.name, w.code
            ),
            mapped_inventory AS (
                -- Step 2: Apply SKU mapping to get canonical SKU + multiplier
                SELECT
                    ri.original_sku,
                    ri.original_name,
                    ri.warehouse_code,
                    ri.raw_quantity,
                    ri.lot_count,
                    ri.last_updated,
                    COALESCE(sm.target_sku, ri.original_sku) as mapped_sku,
                    COALESCE(sm.quantity_multiplier, 1) as multiplier,
                    sm.rule_name as mapping_rule
                FROM raw_inventory ri
                LEFT JOIN sku_mappings sm
                    ON sm.source_pattern = UPPER(ri.original_sku)
                    AND sm.pattern_type = 'exact'
                    AND sm.is_active = TRUE
            ),
            aggregated_per_warehouse AS (
                -- Step 3: Aggregate by mapped SKU and warehouse (apply multiplier)
                SELECT
                    mapped_sku as sku,
                    warehouse_code,
                    SUM(raw_quantity * multiplier) as adjusted_quantity,
                    SUM(lot_count) as lot_count,
                    MAX(last_updated) as last_updated,
                    array_agg(DISTINCT original_sku ORDER BY original_sku) as original_skus
                FROM mapped_inventory
                GROUP BY mapped_sku, warehouse_code
            ),
            -- Step 3b: Aggregate SKU mapping details (total across all warehouses)
            sku_mapping_details AS (
                SELECT
                    mapped_sku as sku,
                    original_sku,
                    MAX(original_name) as original_name,
                    bool_or(mapping_rule IS NOT NULL) as is_mapped,
                    MAX(CASE WHEN mapping_rule IS NOT NULL THEN mapped_sku ELSE NULL END) as target_sku,
                    MAX(CASE WHEN mapping_rule IS NOT NULL THEN multiplier ELSE NULL END) as multiplier,
                    MAX(mapping_rule) as rule_name,
                    SUM(raw_quantity) as raw_quantity,
                    SUM(raw_quantity * multiplier) as adjusted_quantity
                FROM mapped_inventory
                GROUP BY mapped_sku, original_sku
            ),
            aggregated_total AS (
                -- Step 4: Aggregate warehouse stocks into JSON per mapped SKU
                SELECT
                    sku,
                    json_object_agg(warehouse_code, adjusted_quantity) as warehouses,
                    SUM(adjusted_quantity) as stock_total,
                    SUM(lot_count) as lot_count,
                    MAX(last_updated) as last_updated,
                    -- Flatten and deduplicate original_skus across warehouses
                    (SELECT array_agg(DISTINCT os ORDER BY os)
                     FROM aggregated_per_warehouse apw2,
                          unnest(apw2.original_skus) as os
                     WHERE apw2.sku = aggregated_per_warehouse.sku) as original_skus,
                    -- Get aggregated SKU mapping details
                    (SELECT json_agg(
                        json_build_object(
                            'sku', smd.original_sku,
                            'name', smd.original_name,
                            'is_mapped', smd.is_mapped,
                            'target_sku', smd.target_sku,
                            'multiplier', smd.multiplier,
                            'rule_name', smd.rule_name,
                            'raw_quantity', smd.raw_quantity,
                            'adjusted_quantity', smd.adjusted_quantity
                        ) ORDER BY smd.original_sku
                     )
                     FROM sku_mapping_details smd
                     WHERE smd.sku = aggregated_per_warehouse.sku) as original_skus_detail
                FROM aggregated_per_warehouse
                GROUP BY sku
            ),
            final AS (
                -- Step 5: Join with product_catalog for enrichment + inventory planning data
                SELECT
                    at.sku,
                    at.original_skus,
                    at.original_skus_detail,
                    COALESCE(
                        pc.product_name,
                        pc_master.master_box_name,
                        (SELECT name FROM products WHERE sku = at.sku LIMIT 1),
                        at.sku
                    ) as name,
                    COALESCE(
                        pc.category,
                        CASE WHEN pc_master.sku IS NOT NULL THEN 'CAJA MASTER' END,
                        (SELECT category FROM products WHERE sku = at.sku LIMIT 1)
                    ) as category,
                    NULL as subfamily,  -- product_catalog doesn't have subfamily column
                    COALESCE(at.warehouses, '{{}}'::json) as warehouses,
                    COALESCE(at.stock_total, 0) as stock_total,
                    COALESCE(at.lot_count, 0) as lot_count,
                    at.last_updated,
                    COALESCE(pc.sku_value, pc_master.sku_value, 0) as sku_value,
                    COALESCE(at.stock_total, 0) * COALESCE(pc.sku_value, pc_master.sku_value, 0) as valor,
                    -- Get min_stock from products table (user-editable value)
                    COALESCE(
                        (SELECT min_stock FROM products WHERE sku = at.sku AND is_active = true LIMIT 1),
                        0
                    ) as min_stock,
                    -- Get per-product estimation period (1, 3, or 6 months - default 6)
                    COALESCE(pis.estimation_months, 6) as estimation_months,
                    -- Get recommended_min_stock based on configurable monthly sales average
                    -- Uses per-product estimation_months from product_inventory_settings
                    COALESCE(
                        (SELECT ROUND(SUM(sfm.units_sold)::NUMERIC / COALESCE(pis.estimation_months, 6))::INTEGER
                         FROM sales_facts_mv sfm
                         WHERE sfm.original_sku = at.sku
                           AND sfm.order_date >= CURRENT_DATE - MAKE_INTERVAL(months => COALESCE(pis.estimation_months, 6))),
                        0
                    ) as recommended_min_stock,
                    -- Expiration-aware stock from inventory_planning_facts view
                    COALESCE(ipf.stock_usable, at.stock_total, 0) as stock_usable,
                    COALESCE(ipf.stock_expiring_30d, 0) as stock_expiring_30d,
                    COALESCE(ipf.stock_expired, 0) as stock_expired,
                    ipf.earliest_expiration,
                    ipf.days_to_earliest_expiration,
                    -- Days of coverage: how many days will stock_usable last at current sales rate
                    -- Formula: stock_usable / (recommended_min_stock / 30) = stock_usable * 30 / avg_monthly_sales
                    CASE
                        WHEN COALESCE(
                            (SELECT ROUND(SUM(sfm.units_sold)::NUMERIC / COALESCE(pis.estimation_months, 6))::INTEGER
                             FROM sales_facts_mv sfm
                             WHERE sfm.original_sku = at.sku
                               AND sfm.order_date >= CURRENT_DATE - MAKE_INTERVAL(months => COALESCE(pis.estimation_months, 6))),
                            0
                        ) > 0 THEN
                            ROUND(COALESCE(ipf.stock_usable, at.stock_total, 0)::NUMERIC * 30 /
                                  (SELECT ROUND(SUM(sfm.units_sold)::NUMERIC / COALESCE(pis.estimation_months, 6))::INTEGER
                                   FROM sales_facts_mv sfm
                                   WHERE sfm.original_sku = at.sku
                                     AND sfm.order_date >= CURRENT_DATE - MAKE_INTERVAL(months => COALESCE(pis.estimation_months, 6))))::INTEGER
                        ELSE 999  -- No sales = infinite coverage
                    END as days_of_coverage,
                    -- Production needed: target_stock (with 20%% safety buffer) - stock_usable
                    -- Formula: max(0, recommended_min_stock * 1.2 - stock_usable)
                    GREATEST(0,
                        ROUND(COALESCE(
                            (SELECT ROUND(SUM(sfm.units_sold)::NUMERIC / COALESCE(pis.estimation_months, 6))::INTEGER
                             FROM sales_facts_mv sfm
                             WHERE sfm.original_sku = at.sku
                               AND sfm.order_date >= CURRENT_DATE - MAKE_INTERVAL(months => COALESCE(pis.estimation_months, 6))),
                            0
                        ) * 1.2 - COALESCE(ipf.stock_usable, at.stock_total, 0))::INTEGER
                    ) as production_needed,
                    -- in_catalog: TRUE if SKU found in product_catalog (sku or sku_master)
                    CASE WHEN pc.sku IS NOT NULL OR pc_master.sku IS NOT NULL THEN true ELSE false END as in_catalog,
                    -- is_inventory_active: NULL means active (default), FALSE means hidden
                    COALESCE(pc.is_inventory_active, pc_master.is_inventory_active, true) as is_inventory_active
                FROM aggregated_total at
                -- Direct match on product_catalog.sku
                LEFT JOIN product_catalog pc
                    ON pc.sku = at.sku
                    AND pc.is_active = TRUE
                -- Match on product_catalog.sku_master (for CAJA MASTER)
                LEFT JOIN product_catalog pc_master
                    ON pc_master.sku_master = at.sku
                    AND pc_master.is_active = TRUE
                    AND pc.sku IS NULL
                -- Join inventory planning settings (per-product estimation period)
                LEFT JOIN product_inventory_settings pis
                    ON pis.sku = at.sku
                -- Join inventory planning facts (expiration-aware stock)
                LEFT JOIN inventory_planning_facts ipf
                    ON ipf.sku = at.sku
            )
            SELECT *
            FROM final
            WHERE is_inventory_active = true
              AND {filter_clause}
            ORDER BY category NULLS LAST, name
        """

        # Only pass params if there are any, to avoid psycopg2 parsing % in comments
        if params:
            cursor.execute(query, params)
        else:
            cursor.execute(query)
        products = cursor.fetchall()

        # Get summary stats with the new mapping logic
        cursor.execute("""
            WITH mapped_stock AS (
                SELECT
                    COALESCE(sm.target_sku, p.sku) as mapped_sku,
                    ws.quantity * COALESCE(sm.quantity_multiplier, 1) as adjusted_qty,
                    pc.sku_value
                FROM warehouse_stock ws
                JOIN products p ON p.id = ws.product_id
                JOIN warehouses w ON w.id = ws.warehouse_id
                LEFT JOIN sku_mappings sm ON sm.source_pattern = UPPER(p.sku)
                    AND sm.pattern_type = 'exact' AND sm.is_active = TRUE
                LEFT JOIN product_catalog pc ON pc.sku = COALESCE(sm.target_sku, p.sku)
                    AND pc.is_active = TRUE
                WHERE w.is_active = true AND w.source = 'relbase' AND p.is_active = true
            )
            SELECT
                COUNT(DISTINCT mapped_sku) as total_products,
                COALESCE(SUM(adjusted_qty), 0) as total_stock,
                COUNT(DISTINCT CASE WHEN adjusted_qty > 0 THEN mapped_sku END) as products_with_stock,
                (SELECT COUNT(DISTINCT id) FROM warehouses WHERE is_active = true AND source = 'relbase') as active_warehouses,
                COALESCE(SUM(adjusted_qty * COALESCE(sku_value, 0)), 0) as total_valor
            FROM mapped_stock
        """)

        summary = cursor.fetchone()

        # Get expiration stats from materialized view
        cursor.execute("""
            SELECT
                -- Expired lots
                COUNT(CASE WHEN expiration_status = 'Expired' THEN 1 END) as expired_lots,
                COALESCE(SUM(CASE WHEN expiration_status = 'Expired' THEN quantity ELSE 0 END), 0) as expired_units,

                -- Expiring soon (30 days)
                COUNT(CASE WHEN expiration_status = 'Expiring Soon' THEN 1 END) as expiring_soon_lots,
                COALESCE(SUM(CASE WHEN expiration_status = 'Expiring Soon' THEN quantity ELSE 0 END), 0) as expiring_soon_units,

                -- Valid lots (> 30 days)
                COUNT(CASE WHEN expiration_status = 'Valid' THEN 1 END) as valid_lots,
                COALESCE(SUM(CASE WHEN expiration_status = 'Valid' THEN quantity ELSE 0 END), 0) as valid_units,

                -- No date
                COUNT(CASE WHEN expiration_status = 'No Date' THEN 1 END) as no_date_lots,
                COALESCE(SUM(CASE WHEN expiration_status = 'No Date' THEN quantity ELSE 0 END), 0) as no_date_units
            FROM warehouse_stock_by_lot
            WHERE warehouse_code IN (
                SELECT code FROM warehouses
                WHERE is_active = true
                  AND source = 'relbase'
                  AND external_id IS NOT NULL
            )
        """)

        expiration_stats = cursor.fetchone()

        return {
            "status": "success",
            "data": products,
            "summary": {
                **summary,
                "expiration": expiration_stats
            }
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching inventory: {str(e)}")
    finally:
        # Always close cursor and connection to prevent leaks
        if cursor:
            cursor.close()
        if conn:
            conn.close()


# ============================================================================
# ENDPOINT: GET /api/v1/inventory/warehouse/{code}
# ============================================================================

@inventory_router.get("/warehouse/{warehouse_code}", response_model=Dict)
async def get_warehouse_inventory(
    warehouse_code: str = Path(..., description="Warehouse code (e.g., amplifica_centro)"),
    search: Optional[str] = Query(None, description="Search by SKU or product name"),
    only_with_stock: bool = Query(False, description="Show only products with stock > 0")
):
    """
    Get inventory for a specific warehouse

    Path Parameters:
        - warehouse_code: Warehouse code (e.g., 'amplifica_centro', 'packner')

    Query Parameters:
        - search: Filter by SKU or product name (optional)
        - only_with_stock: Show only products with stock (optional)

    Returns:
        {
            "status": "success",
            "warehouse": {
                "code": "amplifica_centro",
                "name": "Amplifica - Centro",
                "update_method": "manual_upload"
            },
            "data": [
                {
                    "sku": "BAMC_U04010",
                    "name": "Barra Low Carb Manzana Canela x 1",
                    "category": "BARRAS",
                    "stock": 44,
                    "percentage_of_total": 10.6
                },
                ...
            ],
            "summary": {
                "total_products": 44,
                "total_stock": 637,
                "last_updated": "2025-11-13T10:30:00Z"
            }
        }
    """
    conn = None
    cursor = None
    try:
        conn = get_db_connection_dict_with_retry()
        cursor = conn.cursor()

        # Verify warehouse exists (Relbase only)
        cursor.execute("""
            SELECT code, name, update_method, external_id, source
            FROM warehouses
            WHERE code = %s
              AND is_active = true
              AND source = 'relbase'
              AND external_id IS NOT NULL
        """, (warehouse_code,))

        warehouse = cursor.fetchone()

        if not warehouse:
            raise HTTPException(status_code=404, detail=f"Relbase warehouse '{warehouse_code}' not found or inactive")

        # Build WHERE clause (using view column names)
        where_conditions = ["1=1"]
        # First param for CTE, second for main query
        params = [warehouse_code, warehouse_code]

        if search:
            where_conditions.append("(v.sku ILIKE %s OR v.product_name ILIKE %s)")
            params.extend([f"%{search}%", f"%{search}%"])

        if only_with_stock:
            where_conditions.append("v.quantity > 0")

        where_clause = " AND ".join(where_conditions)

        # Get inventory for this warehouse with lot details from view
        # Now includes sku_value from product_catalog for valuation
        cursor.execute(f"""
            WITH warehouse_total AS (
                SELECT SUM(quantity) as total
                FROM warehouse_stock_by_lot
                WHERE warehouse_code = %s
            )
            SELECT
                v.sku,
                v.product_name as name,
                v.category,
                SUM(v.quantity) as stock,
                json_agg(
                    json_build_object(
                        'lot_number', v.lot_number,
                        'quantity', v.quantity,
                        'expiration_date', v.expiration_date,
                        'last_updated', v.last_updated,
                        'days_to_expiration', v.days_to_expiration,
                        'expiration_status', v.expiration_status
                    )
                    ORDER BY v.expiration_date NULLS LAST, v.lot_number
                ) as lots,
                -- %% of this warehouse's total inventory
                CASE
                    WHEN (SELECT total FROM warehouse_total) > 0
                    THEN ROUND((SUM(v.quantity)::numeric / (SELECT total FROM warehouse_total)) * 100, 1)
                    ELSE 0
                END as percentage_of_warehouse,
                -- %% of this product's total inventory across all warehouses
                CASE
                    WHEN (SELECT SUM(quantity) FROM warehouse_stock_by_lot WHERE sku = v.sku) > 0
                    THEN ROUND((SUM(v.quantity)::numeric / (SELECT SUM(quantity) FROM warehouse_stock_by_lot WHERE sku = v.sku)) * 100, 1)
                    ELSE 0
                END as percentage_of_product,
                -- Valuation fields
                COALESCE(pc.sku_value, 0) as sku_value,
                SUM(v.quantity) * COALESCE(pc.sku_value, 0) as valor
            FROM warehouse_stock_by_lot v
            LEFT JOIN product_catalog pc ON pc.sku = v.sku AND pc.is_active = true
            WHERE v.warehouse_code = %s
              AND {where_clause}
            GROUP BY v.sku, v.product_name, v.category, pc.sku_value
            ORDER BY v.category, v.product_name
        """, params)

        products = cursor.fetchall()

        # Get summary including total valuation
        cursor.execute("""
            SELECT
                COUNT(DISTINCT ws.product_id) as total_products,
                COALESCE(SUM(ws.quantity), 0) as total_stock,
                COUNT(ws.id) as total_lots,
                MAX(ws.last_updated) as last_updated,
                COALESCE(SUM(ws.quantity * COALESCE(pc.sku_value, 0)), 0) as total_valor
            FROM warehouse_stock ws
            JOIN warehouses w ON w.id = ws.warehouse_id
            JOIN products p ON p.id = ws.product_id
            LEFT JOIN product_catalog pc ON pc.sku = p.sku AND pc.is_active = true
            WHERE w.code = %s
              AND w.source = 'relbase'
        """, (warehouse_code,))

        summary = cursor.fetchone()

        # Get expiration stats for this warehouse from view
        cursor.execute("""
            SELECT
                -- Expired lots
                COUNT(CASE WHEN expiration_status = 'Expired' THEN 1 END) as expired_lots,
                COALESCE(SUM(CASE WHEN expiration_status = 'Expired' THEN quantity ELSE 0 END), 0) as expired_units,

                -- Expiring soon (30 days)
                COUNT(CASE WHEN expiration_status = 'Expiring Soon' THEN 1 END) as expiring_soon_lots,
                COALESCE(SUM(CASE WHEN expiration_status = 'Expiring Soon' THEN quantity ELSE 0 END), 0) as expiring_soon_units,

                -- Valid lots (> 30 days)
                COUNT(CASE WHEN expiration_status = 'Valid' THEN 1 END) as valid_lots,
                COALESCE(SUM(CASE WHEN expiration_status = 'Valid' THEN quantity ELSE 0 END), 0) as valid_units,

                -- No date
                COUNT(CASE WHEN expiration_status = 'No Date' THEN 1 END) as no_date_lots,
                COALESCE(SUM(CASE WHEN expiration_status = 'No Date' THEN quantity ELSE 0 END), 0) as no_date_units
            FROM warehouse_stock_by_lot
            WHERE warehouse_code = %s
        """, (warehouse_code,))

        expiration_stats = cursor.fetchone()

        return {
            "status": "success",
            "warehouse": warehouse,
            "data": products,
            "summary": {
                **summary,
                "expiration": expiration_stats
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching warehouse inventory: {str(e)}")
    finally:
        # Always close cursor and connection to prevent leaks
        if cursor:
            cursor.close()
        if conn:
            conn.close()


# ============================================================================
# ENDPOINT: GET /api/v1/inventory/summary
# ============================================================================

@inventory_router.get("/summary", response_model=Dict)
async def get_inventory_summary():
    """
    Get summary statistics for entire inventory

    Returns:
        {
            "status": "success",
            "data": {
                "total_products": 187,
                "total_stock": 3537,
                "warehouses": [
                    {
                        "name": "Amplifica - Centro",
                        "product_count": 44,
                        "total_stock": 637
                    },
                    ...
                ],
                "by_category": [
                    {
                        "category": "BARRAS",
                        "product_count": 120,
                        "total_stock": 2500
                    },
                    ...
                ]
            }
        }
    """
    conn = None
    cursor = None
    try:
        conn = get_db_connection_dict_with_retry()
        cursor = conn.cursor()

        # Overall stats
        cursor.execute("""
            SELECT
                COUNT(DISTINCT p.id) as total_products,
                COALESCE(SUM(ws.quantity), 0) as total_stock
            FROM warehouse_stock ws
            JOIN products p ON p.id = ws.product_id
        """)
        overall = cursor.fetchone()

        # By warehouse
        cursor.execute("""
            SELECT
                w.name,
                COUNT(DISTINCT ws.product_id) as product_count,
                COALESCE(SUM(ws.quantity), 0) as total_stock
            FROM warehouse_stock ws
            JOIN warehouses w ON w.id = ws.warehouse_id
            WHERE w.is_active = true
            GROUP BY w.name
            ORDER BY w.name
        """)
        by_warehouse = cursor.fetchall()

        # By category
        cursor.execute("""
            SELECT
                p.category,
                COUNT(DISTINCT p.id) as product_count,
                COALESCE(SUM(ws.quantity), 0) as total_stock
            FROM warehouse_stock ws
            JOIN products p ON p.id = ws.product_id
            WHERE p.category IS NOT NULL
            GROUP BY p.category
            ORDER BY total_stock DESC
        """)
        by_category = cursor.fetchall()

        return {
            "status": "success",
            "data": {
                **overall,
                "warehouses": by_warehouse,
                "by_category": by_category
            }
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching summary: {str(e)}")
    finally:
        # Always close cursor and connection to prevent leaks
        if cursor:
            cursor.close()
        if conn:
            conn.close()


# ============================================================================
# ENDPOINT: GET /api/v1/warehouse-inventory/expiration-summary
# ============================================================================

@inventory_router.get("/expiration-summary", response_model=Dict)
async def get_warehouse_expiration_summary():
    """
    Get expiration summary for all warehouses.

    Returns expiration stats per warehouse for display in warehouse cards:
    - Expired lots count and units
    - Expiring soon (30 days) lots count and units
    - Earliest expiration date

    Returns:
        {
            "status": "success",
            "data": {
                "mi_bodega": {
                    "expired_lots": 0,
                    "expired_units": 0,
                    "expiring_soon_lots": 2,
                    "expiring_soon_units": 500,
                    "valid_lots": 7,
                    "valid_units": 134911,
                    "earliest_expiration": "2026-11-13",
                    "days_to_earliest": 319
                },
                ...
            }
        }
    """
    conn = None
    cursor = None
    try:
        conn = get_db_connection_dict_with_retry()
        cursor = conn.cursor()

        # Get expiration stats per warehouse from the view
        cursor.execute("""
            SELECT
                warehouse_code,
                -- Expired lots
                COUNT(CASE WHEN expiration_status = 'Expired' THEN 1 END) as expired_lots,
                COALESCE(SUM(CASE WHEN expiration_status = 'Expired' THEN quantity ELSE 0 END), 0) as expired_units,

                -- Expiring soon (30 days)
                COUNT(CASE WHEN expiration_status = 'Expiring Soon' THEN 1 END) as expiring_soon_lots,
                COALESCE(SUM(CASE WHEN expiration_status = 'Expiring Soon' THEN quantity ELSE 0 END), 0) as expiring_soon_units,

                -- Valid lots (> 30 days)
                COUNT(CASE WHEN expiration_status = 'Valid' THEN 1 END) as valid_lots,
                COALESCE(SUM(CASE WHEN expiration_status = 'Valid' THEN quantity ELSE 0 END), 0) as valid_units,

                -- No date
                COUNT(CASE WHEN expiration_status = 'No Date' THEN 1 END) as no_date_lots,
                COALESCE(SUM(CASE WHEN expiration_status = 'No Date' THEN quantity ELSE 0 END), 0) as no_date_units,

                -- Earliest expiration
                MIN(expiration_date) as earliest_expiration,
                MIN(days_to_expiration) FILTER (WHERE days_to_expiration IS NOT NULL) as days_to_earliest

            FROM warehouse_stock_by_lot
            WHERE warehouse_code IN (
                SELECT code FROM warehouses
                WHERE is_active = true
                  AND source = 'relbase'
                  AND external_id IS NOT NULL
            )
            GROUP BY warehouse_code
            ORDER BY warehouse_code
        """)

        rows = cursor.fetchall()

        # Convert to dictionary keyed by warehouse_code
        result = {}
        for row in rows:
            result[row['warehouse_code']] = {
                'expired_lots': row['expired_lots'],
                'expired_units': int(row['expired_units']),
                'expiring_soon_lots': row['expiring_soon_lots'],
                'expiring_soon_units': int(row['expiring_soon_units']),
                'valid_lots': row['valid_lots'],
                'valid_units': int(row['valid_units']),
                'no_date_lots': row['no_date_lots'],
                'no_date_units': int(row['no_date_units']),
                'earliest_expiration': str(row['earliest_expiration']) if row['earliest_expiration'] else None,
                'days_to_earliest': row['days_to_earliest']
            }

        return {
            "status": "success",
            "data": result
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching expiration summary: {str(e)}")
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


# ============================================================================
# ENDPOINT: POST /api/v1/warehouse-inventory/upload
# ============================================================================

@inventory_router.post("/upload", response_model=Dict)
async def upload_warehouse_inventory(
    warehouse_code: str = Query(..., description="Warehouse code (e.g., amplifica_centro, packner)"),
    file: UploadFile = File(..., description="Excel file with inventory data")
):
    """
    Upload Excel file to update warehouse inventory

    Supports two formats:
    1. **Amplifica warehouses**: Excel with columns [SKU, Nombre, Stock Disponible]
    2. **Packner**: Excel with columns [Articulo, Descripción, Cantidad, Sub Empresa]

    Query Parameters:
        - warehouse_code: Code of the warehouse to update

    File:
        - file: Excel file (.xlsx or .xls)

    Returns:
        {
            "status": "success",
            "warehouse_code": "amplifica_centro",
            "products_updated": 42,
            "products_not_found": 7,
            "details": [...],
            "timestamp": "2025-11-14T10:30:00Z"
        }
    """
    conn = None
    cursor = None
    try:
        conn = get_db_connection_dict_with_retry()
        cursor = conn.cursor()

        # 1. Verify warehouse exists
        cursor.execute("""
            SELECT id, code, name, update_method
            FROM warehouses
            WHERE code = %s AND is_active = true
        """, (warehouse_code,))

        warehouse = cursor.fetchone()

        if not warehouse:
            raise HTTPException(status_code=404, detail=f"Warehouse '{warehouse_code}' not found")

        warehouse_id = warehouse['id']

        # 2. Read Excel file
        contents = await file.read()

        try:
            df = pd.read_excel(io.BytesIO(contents))
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Error reading Excel file: {str(e)}")

        # 3. Parse based on warehouse type
        stats = {
            'products_updated': 0,
            'products_not_found': 0,
            'products_created': 0,
            'details': []
        }

        if warehouse_code.startswith('amplifica'):
            # Amplifica format: [SKU, Nombre, Stock Disponible]
            if 'SKU' not in df.columns or 'Stock Disponible' not in df.columns:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid Amplifica format. Expected columns: SKU, Nombre, Stock Disponible. Got: {list(df.columns)}"
                )

            for _, row in df.iterrows():
                sku = str(row['SKU']).strip()
                stock = row['Stock Disponible']

                # Skip if stock is NaN or None
                if pd.isna(stock):
                    continue

                # Handle non-numeric values (e.g., "≤7" or " ≤7")
                try:
                    stock_str = str(stock).strip()
                    # Remove non-numeric characters like ≤, >, <, etc.
                    stock_str = ''.join(c for c in stock_str if c.isdigit())
                    if not stock_str:
                        continue
                    stock = int(stock_str)
                except (ValueError, TypeError):
                    continue

                # Find product by SKU (check both sku and master_box_sku fields)
                cursor.execute("""
                    SELECT id FROM products
                    WHERE (sku = %s OR master_box_sku = %s)
                    AND is_active = true
                    LIMIT 1
                """, (sku, sku))
                product = cursor.fetchone()

                if product:
                    product_id = product['id']

                    # Update or insert warehouse_stock (use default lot number for manual uploads)
                    cursor.execute("""
                        INSERT INTO warehouse_stock (product_id, warehouse_id, lot_number, quantity, last_updated, updated_by)
                        VALUES (%s, %s, 'MANUAL-UPLOAD', %s, NOW(), 'manual_upload')
                        ON CONFLICT (product_id, warehouse_id, lot_number)
                        DO UPDATE SET
                            quantity = EXCLUDED.quantity,
                            last_updated = NOW(),
                            updated_by = 'manual_upload'
                    """, (product_id, warehouse_id, stock))

                    stats['products_updated'] += 1
                    stats['details'].append({
                        'sku': sku,
                        'stock': stock,
                        'status': 'updated'
                    })
                else:
                    stats['products_not_found'] += 1
                    stats['details'].append({
                        'sku': sku,
                        'stock': stock,
                        'status': 'not_found'
                    })

        elif warehouse_code == 'packner':
            # Packner format: [Articulo, Descripción, Cantidad, Sub Empresa]
            # First row contains headers, actual data starts from row 1

            if len(df) < 2:
                raise HTTPException(status_code=400, detail="Packner file must have at least 2 rows (header + data)")

            # Skip first row (header) and use actual column names
            df = df.iloc[1:].reset_index(drop=True)
            df.columns = ['Articulo', 'Descripción', 'Cantidad', 'Sub Empresa']

            for _, row in df.iterrows():
                sku = str(row['Articulo']).strip()
                stock = row['Cantidad']

                # Skip if stock is NaN or None
                if pd.isna(stock):
                    continue

                # Handle non-numeric values
                try:
                    stock_str = str(stock).strip()
                    # Remove non-numeric characters
                    stock_str = ''.join(c for c in stock_str if c.isdigit())
                    if not stock_str:
                        continue
                    stock = int(stock_str)
                except (ValueError, TypeError):
                    continue

                # Find product by SKU (check both sku and master_box_sku fields)
                cursor.execute("""
                    SELECT id FROM products
                    WHERE (sku = %s OR master_box_sku = %s)
                    AND is_active = true
                    LIMIT 1
                """, (sku, sku))
                product = cursor.fetchone()

                if product:
                    product_id = product['id']

                    # Update or insert warehouse_stock (use default lot number for manual uploads)
                    cursor.execute("""
                        INSERT INTO warehouse_stock (product_id, warehouse_id, lot_number, quantity, last_updated, updated_by)
                        VALUES (%s, %s, 'MANUAL-UPLOAD', %s, NOW(), 'manual_upload')
                        ON CONFLICT (product_id, warehouse_id, lot_number)
                        DO UPDATE SET
                            quantity = EXCLUDED.quantity,
                            last_updated = NOW(),
                            updated_by = 'manual_upload'
                    """, (product_id, warehouse_id, stock))

                    stats['products_updated'] += 1
                    stats['details'].append({
                        'sku': sku,
                        'stock': stock,
                        'status': 'updated'
                    })
                else:
                    stats['products_not_found'] += 1
                    stats['details'].append({
                        'sku': sku,
                        'stock': stock,
                        'status': 'not_found'
                    })

        else:
            raise HTTPException(
                status_code=400,
                detail=f"Upload not supported for warehouse '{warehouse_code}'. Only Amplifica and Packner warehouses support manual upload."
            )

        # Commit changes
        conn.commit()

        return {
            "status": "success",
            "warehouse_code": warehouse_code,
            "warehouse_name": warehouse['name'],
            "products_updated": stats['products_updated'],
            "products_not_found": stats['products_not_found'],
            "details": stats['details'],
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }

    except HTTPException:
        raise
    except Exception as e:
        if conn:
            try:
                conn.rollback()
            except:
                pass
        raise HTTPException(status_code=500, detail=f"Error uploading inventory: {str(e)}")
    finally:
        # Always close cursor and connection to prevent leaks
        if cursor:
            cursor.close()
        if conn:
            conn.close()
