"""
MercadoLibre API Endpoints
Handles MercadoLibre integration and syncing

Author: TM3
Date: 2025-10-04
"""
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
import os

from app.connectors.mercadolibre_connector import MercadoLibreConnector
from app.services.mercadolibre_sync_service import MercadoLibreSyncService

router = APIRouter()


# Pydantic models
class SyncRequest(BaseModel):
    days: int = 30  # Days to look back for orders


class SyncResponse(BaseModel):
    status: str
    synced: int
    failed: int
    message: str


# Dependency: Get services
def get_ml_connector() -> MercadoLibreConnector:
    return MercadoLibreConnector()


def get_ml_sync_service() -> MercadoLibreSyncService:
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise HTTPException(status_code=500, detail="DATABASE_URL not configured")
    return MercadoLibreSyncService(database_url)


@router.get("/test-connection")
async def test_ml_connection():
    """Test connection to MercadoLibre API"""
    try:
        connector = get_ml_connector()
        seller_info = await connector.get_seller_info()

        if seller_info:
            return {
                "status": "success",
                "message": f"✅ Connected to MercadoLibre as {seller_info.get('nickname')}",
                "data": {
                    "seller_id": seller_info.get('id'),
                    "nickname": seller_info.get('nickname'),
                    "country": seller_info.get('country_id'),
                    "reputation": seller_info.get('seller_reputation', {})
                }
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to connect to MercadoLibre")

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sync/products")
async def sync_products(background_tasks: BackgroundTasks):
    """
    Sync products from MercadoLibre to database

    This will:
    1. Fetch active listings from MercadoLibre
    2. Create/update in database
    3. Return sync results
    """
    try:
        service = get_ml_sync_service()
        result = await service.sync_products()

        return {
            "status": "success" if result['success'] else "error",
            "products_synced": result.get('products_synced', 0),
            "products_failed": result.get('products_failed', 0),
            "message": result.get('message', ''),
            "error": result.get('error')
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sync/orders")
async def sync_orders(request: SyncRequest = SyncRequest(), background_tasks: BackgroundTasks = None):
    """
    Sync orders from MercadoLibre to database

    This will:
    1. Fetch recent orders from MercadoLibre
    2. Transform to normalized format
    3. Create/update customers
    4. Create orders and items in database
    5. Log sync results
    """
    try:
        service = get_ml_sync_service()
        result = await service.sync_orders(days=request.days)

        return {
            "status": "success" if result['success'] else "error",
            "orders_synced": result.get('orders_synced', 0),
            "orders_failed": result.get('orders_failed', 0),
            "total_orders": result.get('total_orders', 0),
            "message": result.get('message', ''),
            "errors": result.get('errors'),
            "error": result.get('error')
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sync/all")
async def sync_all(request: SyncRequest = SyncRequest(), background_tasks: BackgroundTasks = None):
    """
    Sync both products and orders from MercadoLibre

    This is a convenience endpoint that syncs everything.
    """
    try:
        service = get_ml_sync_service()

        # Sync products first
        products_result = await service.sync_products()

        # Then sync orders
        orders_result = await service.sync_orders(days=request.days)

        return {
            "status": "success",
            "products": {
                "synced": products_result.get('products_synced', 0),
                "failed": products_result.get('products_failed', 0)
            },
            "orders": {
                "synced": orders_result.get('orders_synced', 0),
                "failed": orders_result.get('orders_failed', 0),
                "total": orders_result.get('total_orders', 0)
            },
            "message": "MercadoLibre sync completed"
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/products")
async def get_ml_products(limit: int = 50):
    """Get products directly from MercadoLibre API (without syncing)"""
    try:
        connector = get_ml_connector()
        listings = await connector.get_active_listings()

        # Limit results
        listings = listings[:limit]

        return {
            "status": "success",
            "count": len(listings),
            "data": listings
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/orders")
async def get_ml_orders(days: int = 30):
    """Get orders directly from MercadoLibre API (without syncing)"""
    try:
        connector = get_ml_connector()
        orders = await connector.get_recent_orders(days=days)

        # Simplify order data for response
        simplified_orders = []
        for order in orders:
            simplified_orders.append({
                'id': order.get('id'),
                'date_created': order.get('date_created'),
                'status': order.get('status'),
                'total_amount': order.get('total_amount'),
                'currency': order.get('currency_id'),
                'buyer': order.get('buyer', {}).get('nickname') if order.get('buyer') else None,
                'items_count': len(order.get('order_items', []))
            })

        return {
            "status": "success",
            "count": len(simplified_orders),
            "data": simplified_orders
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sales-summary")
async def get_sales_summary(days: int = 30):
    """Get sales summary from MercadoLibre"""
    try:
        connector = get_ml_connector()
        summary = await connector.get_sales_summary(days=days)

        return {
            "status": "success",
            "data": summary
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats")
async def get_ml_stats():
    """Get sync statistics from database"""
    try:
        database_url = os.getenv("DATABASE_URL")
        if not database_url:
            raise HTTPException(status_code=500, detail="DATABASE_URL not configured")

        service = get_ml_sync_service()
        stats = await service.get_sync_stats()

        return {
            "status": "success",
            "data": stats
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
