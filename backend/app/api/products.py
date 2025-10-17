"""
Products API Endpoints
Handles product catalog management and queries

Author: TM3
Date: 2025-10-03
Updated: 2025-10-17 (refactor: use ProductRepository for data access)
"""
from fastapi import APIRouter, HTTPException, Query
from typing import Optional, List

from app.repositories.product_repository import ProductRepository

router = APIRouter()


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
