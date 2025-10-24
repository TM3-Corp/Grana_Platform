"""
Orders API Endpoints
Handles order management and queries

Author: TM3
Date: 2025-10-03
Updated: 2025-10-17 (refactor: use OrderRepository for data access)
"""
from fastapi import APIRouter, HTTPException, Query
from typing import Optional

from app.repositories.order_repository import OrderRepository

router = APIRouter()


@router.get("/")
async def get_orders(
    source: Optional[str] = Query(None, description="Filter by source (shopify, mercadolibre, etc.)"),
    status: Optional[str] = Query(None, description="Filter by order status"),
    payment_status: Optional[str] = Query(None, description="Filter by payment status"),
    from_date: Optional[str] = Query(None, description="Filter orders from this date (ISO format)"),
    to_date: Optional[str] = Query(None, description="Filter orders until this date (ISO format)"),
    limit: int = Query(50, ge=1, le=10000),
    offset: int = Query(0, ge=0)
):
    """
    Get all orders with optional filters

    Returns orders with customer and item information
    """
    try:
        repo = OrderRepository()

        # Get orders using repository (N+1 optimization included!)
        orders, total = repo.find_all(
            source=source,
            status=status,
            payment_status=payment_status,
            from_date=from_date,
            to_date=to_date,
            limit=limit,
            offset=offset
        )

        # Convert Order models to dicts with computed fields
        orders_data = [order.to_dict() for order in orders]

        return {
            "status": "success",
            "total": total,
            "limit": limit,
            "offset": offset,
            "count": len(orders),
            "data": orders_data
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching orders: {str(e)}")


@router.get("/stats")
async def get_order_stats():
    """
    Get order statistics

    Returns:
    - Total orders
    - Orders by source
    - Orders by status
    - Revenue metrics
    """
    try:
        repo = OrderRepository()
        stats = repo.get_stats()

        return {
            "status": "success",
            "data": stats
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching stats: {str(e)}")


@router.get("/analytics")
async def get_analytics(
    start_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
    group_by: str = Query('month', description="Group by: day, week, or month")
):
    """
    Get analytics data for charts and visualizations

    Returns:
    - Sales by period and source
    - Source distribution
    - Top products
    - KPIs
    - Growth rates
    """
    if group_by not in ['day', 'week', 'month']:
        raise HTTPException(status_code=400, detail="group_by must be 'day', 'week', or 'month'")

    try:
        repo = OrderRepository()
        analytics = repo.get_analytics(
            start_date=start_date,
            end_date=end_date,
            group_by=group_by
        )

        return {
            "status": "success",
            "data": analytics
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching analytics: {str(e)}")


@router.get("/{order_id}")
async def get_order(order_id: int):
    """
    Get a single order by ID

    Includes customer info and all order items
    """
    try:
        repo = OrderRepository()
        order = repo.find_by_id(order_id)

        if not order:
            raise HTTPException(status_code=404, detail=f"Order {order_id} not found")

        return {
            "status": "success",
            "data": order.to_dict()
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching order: {str(e)}")


@router.get("/source/{source}")
async def get_orders_by_source(source: str, limit: int = Query(50, ge=1, le=500)):
    """
    Get all orders from a specific source

    Args:
        source: shopify, mercadolibre, walmart, cencosud, etc.
    """
    try:
        repo = OrderRepository()
        orders = repo.find_by_source(source, limit=limit)

        orders_data = [order.to_dict() for order in orders]

        return {
            "status": "success",
            "source": source,
            "count": len(orders),
            "data": orders_data
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching orders: {str(e)}")
