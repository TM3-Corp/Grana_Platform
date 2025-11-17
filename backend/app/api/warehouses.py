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
    try:
        conn = get_db_connection_dict()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT id, code, name, location, update_method, is_active
            FROM warehouses
            WHERE is_active = true
            ORDER BY
                CASE
                    WHEN code LIKE 'amplifica%' THEN 1
                    WHEN code = 'packner' THEN 2
                    WHEN code = 'orinoco' THEN 3
                    WHEN code = 'mercadolibre' THEN 4
                    ELSE 5
                END,
                name
        """)

        warehouses = cursor.fetchall()
        cursor.close()
        conn.close()

        return {
            "status": "success",
            "data": warehouses
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching warehouses: {str(e)}")


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
    Get consolidated inventory view with stock by warehouse

    Query Parameters:
        - search: Filter by SKU or product name (optional)
        - category: Filter by category (optional)
        - only_with_stock: Show only products with stock (optional)

    Returns:
        {
            "status": "success",
            "data": [
                {
                    "sku": "BAMC_U04010",
                    "name": "Barra Low Carb Manzana Canela x 1",
                    "category": "BARRAS",
                    "subfamily": "Barra Low Carb Manzana Canela",
                    "stock_amplifica_centro": 44,
                    "stock_amplifica_lareina": 37,
                    "stock_amplifica_lobarnechea": 0,
                    "stock_amplifica_quilicura": 135,
                    "stock_packner": 198,
                    "stock_orinoco": 0,
                    "stock_mercadolibre": 0,
                    "stock_total": 414,
                    "last_updated": "2025-11-13T10:30:00Z"
                },
                ...
            ],
            "summary": {
                "total_products": 187,
                "total_stock": 3537,
                "products_with_stock": 187,
                "products_without_stock": 0
            }
        }
    """
    try:
        conn = get_db_connection_dict()
        cursor = conn.cursor()

        # Build WHERE clause
        where_conditions = []
        params = []

        if search:
            where_conditions.append("(sku ILIKE %s OR name ILIKE %s)")
            params.extend([f"%{search}%", f"%{search}%"])

        if category:
            where_conditions.append("category = %s")
            params.append(category)

        if only_with_stock:
            if warehouse_group == 'amplifica':
                # Filter by Amplifica warehouses only
                where_conditions.append(
                    "(stock_amplifica_centro > 0 OR stock_amplifica_lareina > 0 OR "
                    "stock_amplifica_lobarnechea > 0 OR stock_amplifica_quilicura > 0)"
                )
            else:
                # Default: filter by total stock
                where_conditions.append("stock_total > 0")

        where_clause = " AND ".join(where_conditions) if where_conditions else "1=1"

        # Main query
        query = f"""
            SELECT
                sku,
                name,
                category,
                subfamily,
                stock_amplifica_centro,
                stock_amplifica_lareina,
                stock_amplifica_lobarnechea,
                stock_amplifica_quilicura,
                stock_packner,
                stock_orinoco,
                stock_mercadolibre,
                stock_total,
                last_updated
            FROM inventory_general
            WHERE {where_clause}
            ORDER BY category, name
        """

        cursor.execute(query, params)
        products = cursor.fetchall()

        # Get summary stats
        cursor.execute(f"""
            SELECT
                COUNT(*) as total_products,
                COALESCE(SUM(stock_total), 0) as total_stock,
                COUNT(*) FILTER (WHERE stock_total > 0) as products_with_stock,
                COUNT(*) FILTER (WHERE stock_total = 0) as products_without_stock
            FROM inventory_general
            WHERE {where_clause}
        """, params)

        summary = cursor.fetchone()

        cursor.close()
        conn.close()

        return {
            "status": "success",
            "data": products,
            "summary": summary
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching inventory: {str(e)}")


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
    try:
        conn = get_db_connection_dict()
        cursor = conn.cursor()

        # Verify warehouse exists
        cursor.execute("""
            SELECT code, name, update_method
            FROM warehouses
            WHERE code = %s AND is_active = true
        """, (warehouse_code,))

        warehouse = cursor.fetchone()

        if not warehouse:
            raise HTTPException(status_code=404, detail=f"Warehouse '{warehouse_code}' not found")

        # Build WHERE clause
        where_conditions = ["1=1"]
        params = [warehouse_code]

        if search:
            where_conditions.append("(p.sku ILIKE %s OR p.name ILIKE %s)")
            params.extend([f"%{search}%", f"%{search}%"])

        if only_with_stock:
            where_conditions.append("ws.quantity > 0")

        where_clause = " AND ".join(where_conditions)

        # Get inventory for this warehouse
        cursor.execute(f"""
            SELECT
                p.sku,
                p.name,
                p.category,
                ws.quantity as stock,
                CASE
                    WHEN (SELECT SUM(quantity) FROM warehouse_stock WHERE product_id = p.id) > 0
                    THEN ROUND((ws.quantity::numeric / (SELECT SUM(quantity) FROM warehouse_stock WHERE product_id = p.id)) * 100, 1)
                    ELSE 0
                END as percentage_of_total
            FROM warehouse_stock ws
            JOIN products p ON p.id = ws.product_id
            JOIN warehouses w ON w.id = ws.warehouse_id
            WHERE w.code = %s AND p.is_active = true AND {where_clause}
            ORDER BY p.category, p.name
        """, params)

        products = cursor.fetchall()

        # Get summary
        cursor.execute("""
            SELECT
                COUNT(*) as total_products,
                COALESCE(SUM(ws.quantity), 0) as total_stock,
                MAX(ws.last_updated) as last_updated
            FROM warehouse_stock ws
            JOIN warehouses w ON w.id = ws.warehouse_id
            WHERE w.code = %s
        """, (warehouse_code,))

        summary = cursor.fetchone()

        cursor.close()
        conn.close()

        return {
            "status": "success",
            "warehouse": warehouse,
            "data": products,
            "summary": summary
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching warehouse inventory: {str(e)}")


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

        cursor.close()
        conn.close()

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
            cursor.close()
            conn.close()
            raise HTTPException(status_code=404, detail=f"Warehouse '{warehouse_code}' not found")

        warehouse_id = warehouse['id']

        # 2. Read Excel file
        contents = await file.read()

        try:
            df = pd.read_excel(io.BytesIO(contents))
        except Exception as e:
            cursor.close()
            conn.close()
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
                cursor.close()
                conn.close()
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

                    # Update or insert warehouse_stock
                    cursor.execute("""
                        INSERT INTO warehouse_stock (product_id, warehouse_id, quantity, last_updated, updated_by)
                        VALUES (%s, %s, %s, NOW(), 'manual_upload')
                        ON CONFLICT (product_id, warehouse_id)
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
                cursor.close()
                conn.close()
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

                    # Update or insert warehouse_stock
                    cursor.execute("""
                        INSERT INTO warehouse_stock (product_id, warehouse_id, quantity, last_updated, updated_by)
                        VALUES (%s, %s, %s, NOW(), 'manual_upload')
                        ON CONFLICT (product_id, warehouse_id)
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
            cursor.close()
            conn.close()
            raise HTTPException(
                status_code=400,
                detail=f"Upload not supported for warehouse '{warehouse_code}'. Only Amplifica and Packner warehouses support manual upload."
            )

        # Commit changes
        conn.commit()
        cursor.close()
        conn.close()

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
        try:
            conn.rollback()
            cursor.close()
            conn.close()
        except:
            pass
        raise HTTPException(status_code=500, detail=f"Error uploading inventory: {str(e)}")
