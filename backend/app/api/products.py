"""
Products API Endpoints
Handles product catalog management and queries

Author: TM3
Date: 2025-10-03
Updated: 2025-10-17 (refactor: use ProductRepository for data access)
Updated: 2025-11-24 (add minimum stock calculation based on sales history)
"""
from fastapi import APIRouter, HTTPException, Query, Body
from typing import Optional, List
from pydantic import BaseModel

from app.repositories.product_repository import ProductRepository
from app.core.database import get_db_connection_dict_with_retry

router = APIRouter()


# Request models
class MinStockUpdate(BaseModel):
    min_stock: int


@router.get("/")
async def get_products(
    source: Optional[str] = Query(None, description="Filter by source (shopify, mercadolibre, etc.)"),
    category: Optional[str] = Query(None, description="Filter by category"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    search: Optional[str] = Query(None, description="Search by name or SKU"),
    limit: int = Query(100, ge=1, le=5000),
    offset: int = Query(0, ge=0)
):
    """
    Get all products with optional filters

    Returns products with conversion information included
    """
    try:
        repo = ProductRepository()

        # Get products using repository
        products, total = repo.find_all(
            source=source,
            category=category,
            is_active=is_active,
            search=search,
            limit=limit,
            offset=offset
        )

        # Convert Product models to dicts
        products_data = [product.to_dict() for product in products]

        return {
            "status": "success",
            "total": total,
            "limit": limit,
            "offset": offset,
            "count": len(products),
            "data": products_data
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
        repo = ProductRepository()

        # Get all stats from repository
        stats = repo.get_stats()

        return {
            "status": "success",
            "data": stats
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching stats: {str(e)}")


@router.get("/minimum-stock-suggestions")
async def get_minimum_stock_suggestions():
    """
    Calculate suggested minimum stock levels based on average sales from last 4 months

    Logic:
    - Analyzes sales from last 4 months (current month excluded)
    - Calculates average monthly sales per SKU
    - If less than 4 months of data, uses average of available months
    - If no sales data, suggests 0

    Returns:
        Dictionary mapping SKU -> suggested minimum stock
    """
    try:
        conn = get_db_connection_dict_with_retry()
        cursor = conn.cursor()

        # Calculate average monthly sales for last 4 months
        # November 2025 is current, so we look at: Oct, Sep, Aug, July (2025-07-01 to 2025-10-31)
        query = """
        WITH monthly_sales AS (
            SELECT
                oi.product_sku,
                DATE_TRUNC('month', o.order_date) as month,
                SUM(oi.quantity) as total_quantity
            FROM order_items oi
            JOIN orders o ON o.id = oi.order_id
            WHERE o.order_date >= '2025-07-01'
              AND o.order_date < '2025-11-01'
              AND o.source = 'relbase'
            GROUP BY oi.product_sku, DATE_TRUNC('month', o.order_date)
        )
        SELECT
            product_sku,
            COALESCE(ROUND(AVG(total_quantity)), 0)::INTEGER as suggested_min_stock,
            COUNT(DISTINCT month)::INTEGER as months_with_data
        FROM monthly_sales
        GROUP BY product_sku
        ORDER BY product_sku;
        """

        cursor.execute(query)
        results = cursor.fetchall()

        cursor.close()
        conn.close()

        # Convert to dictionary for easy lookup
        suggestions = {
            row['product_sku']: {
                'suggested_min_stock': row['suggested_min_stock'],
                'months_with_data': row['months_with_data']
            }
            for row in results
        }

        return {
            "status": "success",
            "calculation_period": "2025-07-01 to 2025-10-31 (4 months)",
            "total_skus_analyzed": len(suggestions),
            "data": suggestions
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error calculating minimum stock suggestions: {str(e)}")


@router.get("/{sku}")
async def get_product(sku: str):
    """
    Get a single product by SKU

    Includes conversion calculations
    """
    try:
        repo = ProductRepository()
        product = repo.find_by_sku(sku)

        if not product:
            raise HTTPException(status_code=404, detail=f"Product {sku} not found")

        return {
            "status": "success",
            "data": product.to_dict()
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
        repo = ProductRepository()
        products = repo.find_by_source(source)

        products_data = [product.to_dict() for product in products]

        return {
            "status": "success",
            "source": source,
            "count": len(products),
            "data": products_data
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
        repo = ProductRepository()
        products = repo.find_low_stock(threshold)

        products_data = [product.to_dict() for product in products]

        return {
            "status": "success",
            "count": len(products),
            "threshold": threshold or "min_stock",
            "data": products_data
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching low stock products: {str(e)}")


@router.put("/{sku}/min-stock")
async def update_product_min_stock(sku: str, update: MinStockUpdate):
    """
    Update the minimum stock level for a specific product

    Args:
        sku: Product SKU
        update: MinStockUpdate model with min_stock value

    Returns:
        Updated product information
    """
    try:
        conn = get_db_connection_dict_with_retry()
        cursor = conn.cursor()

        # Update min_stock for the product
        cursor.execute(
            """
            UPDATE products
            SET min_stock = %s,
                updated_at = NOW()
            WHERE sku = %s
            RETURNING sku, min_stock, updated_at
            """,
            (update.min_stock, sku)
        )

        result = cursor.fetchone()

        if not result:
            cursor.close()
            conn.close()
            raise HTTPException(status_code=404, detail=f"Product with SKU '{sku}' not found")

        conn.commit()
        cursor.close()
        conn.close()

        return {
            "status": "success",
            "message": f"Minimum stock updated for {sku}",
            "data": result
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error updating minimum stock: {str(e)}")
