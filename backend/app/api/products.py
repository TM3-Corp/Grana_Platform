"""
Products API Endpoints
Handles product catalog management and queries

Author: TM3
Date: 2025-10-03
"""
from fastapi import APIRouter, HTTPException, Query
from typing import Optional, List
import os
import psycopg2
from psycopg2.extras import RealDictCursor

router = APIRouter()


def get_db_connection():
    """Get database connection"""
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise HTTPException(status_code=500, detail="DATABASE_URL not configured")
    return psycopg2.connect(database_url)


@router.get("/")
async def get_products(
    source: Optional[str] = Query(None, description="Filter by source (shopify, mercadolibre, etc.)"),
    category: Optional[str] = Query(None, description="Filter by category"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    search: Optional[str] = Query(None, description="Search by name or SKU"),
    limit: int = Query(100, ge=1, le=5000),  # Aumentado para permitir cargar todos los productos
    offset: int = Query(0, ge=0)
):
    """
    Get all products with optional filters

    Returns products with conversion information included
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        # Build WHERE clause based on filters
        conditions = []
        params = []

        if source:
            conditions.append("source = %s")
            params.append(source)

        if category:
            conditions.append("category = %s")
            params.append(category)

        if is_active is not None:
            conditions.append("is_active = %s")
            params.append(is_active)

        if search:
            conditions.append("(name ILIKE %s OR sku ILIKE %s)")
            search_term = f"%{search}%"
            params.extend([search_term, search_term])

        where_clause = " AND ".join(conditions) if conditions else "1=1"

        # Get total count
        cursor.execute(f"""
            SELECT COUNT(*) as total
            FROM products
            WHERE {where_clause}
        """, params)
        total = cursor.fetchone()['total']

        # Get products
        cursor.execute(f"""
            SELECT
                id, external_id, source, sku, name, description,
                category, brand, unit,
                units_per_display, displays_per_box, boxes_per_pallet,
                display_name, box_name, pallet_name,
                cost_price, sale_price, current_stock, min_stock,
                is_active, created_at, updated_at
            FROM products
            WHERE {where_clause}
            ORDER BY name
            LIMIT %s OFFSET %s
        """, params + [limit, offset])

        products = cursor.fetchall()

        cursor.close()
        conn.close()

        return {
            "status": "success",
            "total": total,
            "limit": limit,
            "offset": offset,
            "count": len(products),
            "data": products
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching products: {str(e)}")


@router.get("/stats")
async def get_product_stats():
    """
    Get product statistics

    Returns:
    - Total products
    - Products by source
    - Products by category
    - Stock levels
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        # Total products
        cursor.execute("SELECT COUNT(*) as total FROM products WHERE is_active = true")
        total_active = cursor.fetchone()['total']

        cursor.execute("SELECT COUNT(*) as total FROM products")
        total_all = cursor.fetchone()['total']

        # By source
        cursor.execute("""
            SELECT source, COUNT(*) as count
            FROM products
            WHERE is_active = true
            GROUP BY source
            ORDER BY count DESC
        """)
        by_source = cursor.fetchall()

        # By category
        cursor.execute("""
            SELECT category, COUNT(*) as count
            FROM products
            WHERE is_active = true AND category IS NOT NULL
            GROUP BY category
            ORDER BY count DESC
            LIMIT 10
        """)
        by_category = cursor.fetchall()

        # Stock levels
        cursor.execute("""
            SELECT
                COUNT(*) FILTER (WHERE current_stock <= 0) as out_of_stock,
                COUNT(*) FILTER (WHERE current_stock > 0 AND current_stock <= min_stock) as low_stock,
                COUNT(*) FILTER (WHERE current_stock > min_stock) as in_stock
            FROM products
            WHERE is_active = true
        """)
        stock_levels = cursor.fetchone()

        # Products with conversion data
        cursor.execute("""
            SELECT COUNT(*) as count
            FROM products
            WHERE units_per_display IS NOT NULL
                AND displays_per_box IS NOT NULL
                AND boxes_per_pallet IS NOT NULL
        """)
        with_conversions = cursor.fetchone()['count']

        cursor.close()
        conn.close()

        return {
            "status": "success",
            "data": {
                "totals": {
                    "all": total_all,
                    "active": total_active,
                    "with_conversions": with_conversions
                },
                "by_source": by_source,
                "by_category": by_category,
                "stock_levels": stock_levels
            }
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching stats: {str(e)}")


@router.get("/{sku}")
async def get_product(sku: str):
    """
    Get a single product by SKU

    Includes conversion calculations
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        cursor.execute("""
            SELECT
                id, external_id, source, sku, name, description,
                category, brand, unit,
                units_per_display, displays_per_box, boxes_per_pallet,
                display_name, box_name, pallet_name,
                cost_price, sale_price, current_stock, min_stock,
                is_active, created_at, updated_at
            FROM products
            WHERE sku = %s
        """, (sku,))

        product = cursor.fetchone()

        if not product:
            cursor.close()
            conn.close()
            raise HTTPException(status_code=404, detail=f"Product {sku} not found")

        # Calculate conversion metrics if available
        if product['units_per_display'] and product['displays_per_box']:
            units_per_box = product['units_per_display'] * product['displays_per_box']
            product['units_per_box'] = units_per_box

            if product['boxes_per_pallet']:
                units_per_pallet = units_per_box * product['boxes_per_pallet']
                product['units_per_pallet'] = units_per_pallet

        cursor.close()
        conn.close()

        return {
            "status": "success",
            "data": product
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching product: {str(e)}")


@router.get("/source/{source}")
async def get_products_by_source(source: str):
    """
    Get all products from a specific source

    Args:
        source: shopify, mercadolibre, walmart, cencosud, etc.
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        cursor.execute("""
            SELECT
                id, external_id, source, sku, name, description,
                category, brand, unit,
                units_per_display, displays_per_box, boxes_per_pallet,
                display_name, box_name, pallet_name,
                sale_price, current_stock, min_stock,
                is_active, created_at, updated_at
            FROM products
            WHERE source = %s
            ORDER BY name
        """, (source,))

        products = cursor.fetchall()

        cursor.close()
        conn.close()

        return {
            "status": "success",
            "source": source,
            "count": len(products),
            "data": products
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching products: {str(e)}")


@router.get("/low-stock/alert")
async def get_low_stock_products(threshold: Optional[int] = Query(None, description="Custom threshold")):
    """
    Get products with low stock levels

    Returns products where current_stock <= min_stock
    Or optionally use custom threshold
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        if threshold is not None:
            cursor.execute("""
                SELECT
                    id, sku, name, category, source,
                    current_stock, min_stock,
                    sale_price
                FROM products
                WHERE is_active = true
                    AND current_stock <= %s
                ORDER BY current_stock ASC
            """, (threshold,))
        else:
            cursor.execute("""
                SELECT
                    id, sku, name, category, source,
                    current_stock, min_stock,
                    sale_price
                FROM products
                WHERE is_active = true
                    AND current_stock <= min_stock
                ORDER BY current_stock ASC
            """)

        products = cursor.fetchall()

        cursor.close()
        conn.close()

        return {
            "status": "success",
            "count": len(products),
            "threshold": threshold or "min_stock",
            "data": products
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching low stock products: {str(e)}")
