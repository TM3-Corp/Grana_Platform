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

from app.core.database import get_db_connection_dict


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
        conn = get_db_connection_dict()
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
                    WHEN code = 'packner' THEN 2
                    WHEN code = 'orinoco' THEN 3
                    WHEN code LIKE 'mercado%' THEN 4
                    WHEN code = 'mi_bodega' THEN 5
                    WHEN code LIKE 'produccion%' THEN 6
                    ELSE 7
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
    warehouse_group: Optional[str] = Query(None, description="Filter by warehouse group (e.g., 'amplifica')")
):
    """
    Get consolidated inventory view with dynamic warehouse columns (Relbase only)

    Query Parameters:
        - search: Filter by SKU or product name (optional)
        - category: Filter by category (optional)
        - only_with_stock: Show only products with stock (optional)
        - warehouse_group: Filter by warehouse group (optional)

    Returns:
        {
            "status": "success",
            "data": [
                {
                    "sku": "BAMC_U04010",
                    "name": "Barra Low Carb Manzana Canela x 1",
                    "category": "BARRAS",
                    "subfamily": "Barra Low Carb Manzana Canela",
                    "warehouses": {
                        "mi_bodega": 7218,
                        "casa_maca": 12,
                        ...
                    },
                    "stock_total": 7230,
                    "lot_count": 3,
                    "last_updated": "2025-11-20T17:58:21Z"
                },
                ...
            ],
            "summary": {
                "total_products": 9,
                "total_stock": 45648,
                "products_with_stock": 9,
                "products_without_stock": 0,
                "active_warehouses": 10
            }
        }
    """
    conn = None
    cursor = None
    try:
        conn = get_db_connection_dict()
        cursor = conn.cursor()

        # Build WHERE clause for products
        product_where_conditions = ["p.is_active = true"]
        params = []

        if search:
            product_where_conditions.append("(p.sku ILIKE %s OR p.name ILIKE %s)")
            params.extend([f"%{search}%", f"%{search}%"])

        if category:
            product_where_conditions.append("p.category = %s")
            params.append(category)

        product_where_clause = " AND ".join(product_where_conditions)

        # Dynamic query with JSON aggregation for warehouses
        # Two-step aggregation to avoid nested aggregate functions
        query = f"""
            WITH warehouse_stock_per_product_warehouse AS (
                -- Step 1: Sum quantities per product-warehouse combination
                SELECT
                    ws.product_id,
                    w.code as warehouse_code,
                    SUM(ws.quantity) as warehouse_total,
                    COUNT(ws.id) as warehouse_lots,
                    MAX(ws.last_updated) as last_updated
                FROM warehouse_stock ws
                JOIN warehouses w ON w.id = ws.warehouse_id
                WHERE w.is_active = true
                  AND w.source = 'relbase'
                  AND w.external_id IS NOT NULL
                GROUP BY ws.product_id, w.code
            ),
            warehouse_stock_agg AS (
                -- Step 2: Aggregate into JSON object per product
                SELECT
                    product_id,
                    json_object_agg(warehouse_code, warehouse_total) as warehouse_stocks,
                    SUM(warehouse_total) as stock_total,
                    SUM(warehouse_lots) as lot_count,
                    MAX(last_updated) as last_updated
                FROM warehouse_stock_per_product_warehouse
                GROUP BY product_id
            )
            SELECT
                p.sku,
                p.name,
                p.category,
                p.subfamily,
                COALESCE(wsa.warehouse_stocks, '{{}}'::json) as warehouses,
                COALESCE(wsa.stock_total, 0) as stock_total,
                COALESCE(wsa.lot_count, 0) as lot_count,
                wsa.last_updated
            FROM products p
            LEFT JOIN warehouse_stock_agg wsa ON wsa.product_id = p.id
            WHERE {product_where_clause}
              {f"AND wsa.stock_total > 0" if only_with_stock else ""}
            ORDER BY p.category, p.name
        """

        cursor.execute(query, params)
        products = cursor.fetchall()

        # Get summary stats
        cursor.execute("""
            SELECT
                COUNT(DISTINCT p.id) as total_products,
                COALESCE(SUM(ws.quantity), 0) as total_stock,
                COUNT(DISTINCT CASE WHEN ws.quantity > 0 THEN p.id END) as products_with_stock,
                COUNT(DISTINCT CASE WHEN ws.quantity IS NULL OR ws.quantity = 0 THEN p.id END) as products_without_stock,
                COUNT(DISTINCT w.id) as active_warehouses
            FROM products p
            LEFT JOIN warehouse_stock ws ON ws.product_id = p.id
            LEFT JOIN warehouses w ON w.id = ws.warehouse_id AND w.is_active = true AND w.source = 'relbase'
            WHERE p.is_active = true
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
        conn = get_db_connection_dict()
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
                END as percentage_of_product
            FROM warehouse_stock_by_lot v
            WHERE v.warehouse_code = %s
              AND {where_clause}
            GROUP BY v.sku, v.product_name, v.category
            ORDER BY v.category, v.product_name
        """, params)

        products = cursor.fetchall()

        # Get summary
        cursor.execute("""
            SELECT
                COUNT(DISTINCT ws.product_id) as total_products,
                COALESCE(SUM(ws.quantity), 0) as total_stock,
                COUNT(ws.id) as total_lots,
                MAX(ws.last_updated) as last_updated
            FROM warehouse_stock ws
            JOIN warehouses w ON w.id = ws.warehouse_id
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
        conn = get_db_connection_dict()
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
        conn = get_db_connection_dict()
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
