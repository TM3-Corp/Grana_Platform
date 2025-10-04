"""
Shopify API Endpoints
Handles Shopify integration and syncing

Author: TM3
Date: 2025-10-03
"""
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
import os

from app.connectors.shopify_connector import ShopifyConnector
from app.services.order_processing_service import OrderProcessingService

router = APIRouter()


# Pydantic models
class SyncRequest(BaseModel):
    limit: int = 50
    created_after: Optional[str] = None  # ISO datetime string


class SyncResponse(BaseModel):
    status: str
    synced: int
    failed: int
    details: List[dict]


# Dependency: Get services
def get_shopify_connector() -> ShopifyConnector:
    return ShopifyConnector()


def get_order_processor() -> OrderProcessingService:
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise HTTPException(status_code=500, detail="DATABASE_URL not configured")
    return OrderProcessingService(database_url)


@router.get("/test-connection")
async def test_shopify_connection():
    """Test connection to Shopify"""
    try:
        connector = get_shopify_connector()
        result = await connector.test_connection()

        if result['success']:
            return {
                "status": "success",
                "message": "✅ Connected to Shopify",
                "data": result
            }
        else:
            raise HTTPException(status_code=500, detail=result.get('error'))

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sync/products")
async def sync_products(request: SyncRequest = SyncRequest(limit=50)):
    """
    Sync products from Shopify to database

    This will:
    1. Fetch products from Shopify
    2. Normalize data
    3. Create/update in database
    """
    try:
        connector = get_shopify_connector()
        processor = get_order_processor()

        # Fetch products from Shopify
        products_data = await connector.get_products(limit=request.limit)
        products = products_data.get('products', {}).get('edges', [])

        synced = 0
        failed = 0
        details = []

        for edge in products:
            product_node = edge['node']
            normalized_products = connector.normalize_product(product_node)

            for product in normalized_products:
                try:
                    result = processor.sync_product_from_external(product)
                    synced += 1
                    details.append({
                        'sku': product['sku'],
                        'name': product['name'],
                        'status': result['status']
                    })
                except Exception as e:
                    failed += 1
                    details.append({
                        'sku': product['sku'],
                        'name': product['name'],
                        'status': 'failed',
                        'error': str(e)
                    })

        return {
            "status": "success",
            "synced": synced,
            "failed": failed,
            "total": synced + failed,
            "details": details
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Sync failed: {str(e)}")


@router.post("/sync/orders")
async def sync_orders(request: SyncRequest = SyncRequest(limit=50)):
    """
    Sync orders from Shopify to database

    This will:
    1. Fetch orders from Shopify
    2. Normalize data
    3. Create customers if needed
    4. Create orders in database
    """
    try:
        connector = get_shopify_connector()
        processor = get_order_processor()

        # Parse created_after if provided
        created_after = None
        if request.created_after:
            created_after = datetime.fromisoformat(request.created_after.replace('Z', '+00:00'))

        # Fetch orders from Shopify
        orders_data = await connector.get_orders(
            limit=request.limit,
            created_after=created_after
        )
        orders = orders_data.get('orders', {}).get('edges', [])

        synced = 0
        failed = 0
        details = []

        for edge in orders:
            order_node = edge['node']
            normalized_order = connector.normalize_order(order_node)

            try:
                result = processor.process_order(normalized_order)

                if result['success']:
                    synced += 1
                    details.append({
                        'order_number': normalized_order['order_number'],
                        'status': result['status'],
                        'order_id': result.get('order_id'),
                        'warnings': result.get('warnings')
                    })
                else:
                    failed += 1
                    details.append({
                        'order_number': normalized_order['order_number'],
                        'status': 'failed',
                        'error': result.get('message')
                    })

            except Exception as e:
                failed += 1
                details.append({
                    'order_number': normalized_order['order_number'],
                    'status': 'failed',
                    'error': str(e)
                })

        return {
            "status": "success",
            "synced": synced,
            "failed": failed,
            "total": synced + failed,
            "details": details
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Sync failed: {str(e)}")


@router.get("/products")
async def get_shopify_products(limit: int = 50):
    """Get products directly from Shopify (without syncing)"""
    try:
        connector = get_shopify_connector()
        products_data = await connector.get_products(limit=limit)

        products = []
        for edge in products_data.get('products', {}).get('edges', []):
            product = edge['node']
            products.append({
                'id': product['id'],
                'title': product['title'],
                'status': product['status'],
                'vendor': product.get('vendor'),
                'productType': product.get('productType'),
                'variantCount': len(product.get('variants', {}).get('edges', []))
            })

        return {
            "status": "success",
            "count": len(products),
            "data": products
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/orders")
async def get_shopify_orders(limit: int = 50):
    """Get orders directly from Shopify (without syncing)"""
    try:
        connector = get_shopify_connector()
        orders_data = await connector.get_orders(limit=limit)

        orders = []
        for edge in orders_data.get('orders', {}).get('edges', []):
            order = edge['node']
            orders.append({
                'id': order['id'],
                'name': order['name'],
                'createdAt': order['createdAt'],
                'total': order['totalPriceSet']['shopMoney']['amount'],
                'currency': order['totalPriceSet']['shopMoney']['currencyCode'],
                'financialStatus': order['displayFinancialStatus'],
                'fulfillmentStatus': order['displayFulfillmentStatus']
            })

        return {
            "status": "success",
            "count": len(orders),
            "data": orders
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats")
async def get_shopify_stats():
    """Get sync statistics from database"""
    try:
        database_url = os.getenv("DATABASE_URL")
        if not database_url:
            raise HTTPException(status_code=500, detail="DATABASE_URL not configured")

        import psycopg2
        from psycopg2.extras import RealDictCursor

        conn = psycopg2.connect(database_url)
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        # Count products from Shopify
        cursor.execute("""
            SELECT COUNT(*) as count FROM products
            WHERE source = 'shopify'
        """)
        products_count = cursor.fetchone()['count']

        # Count orders from Shopify
        cursor.execute("""
            SELECT COUNT(*) as count FROM orders
            WHERE source = 'shopify'
        """)
        orders_count = cursor.fetchone()['count']

        # Get last sync
        cursor.execute("""
            SELECT sync_type, status, completed_at, records_processed, records_failed
            FROM sync_logs
            WHERE source = 'shopify'
            ORDER BY completed_at DESC
            LIMIT 10
        """)
        recent_syncs = cursor.fetchall()

        cursor.close()
        conn.close()

        return {
            "status": "success",
            "data": {
                "products_synced": products_count,
                "orders_synced": orders_count,
                "recent_syncs": recent_syncs
            }
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
async def shopify_health():
    """Health check for Shopify integration"""
    try:
        connector = get_shopify_connector()
        result = await connector.test_connection()

        return {
            "status": "healthy" if result['success'] else "unhealthy",
            "service": "shopify",
            "connected": result['success'],
            "shop": result.get('shop_name') if result['success'] else None
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "service": "shopify",
            "connected": False,
            "error": str(e)
        }
