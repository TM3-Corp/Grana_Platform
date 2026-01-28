"""
Sync API - Scheduled data synchronization endpoints
Designed to be called by cron-job.org or similar services

Endpoints:
- GET  /api/v1/sync/status     - Get last sync status (public)
- GET  /api/v1/sync/health     - Health check (public)
- POST /api/v1/sync/sales      - Sync orders from RelBase (requires API key)
- POST /api/v1/sync/inventory  - Sync inventory from RelBase + ML (requires API key)
- POST /api/v1/sync/all        - Run all syncs (requires API key)

Security:
- POST endpoints require X-Sync-Key header with valid SYNC_API_KEY
- GET endpoints are public (read-only, no sensitive data)

Author: Claude Code
Date: 2025-11-28
Updated: 2025-12-01 - Added API key authentication
"""
from fastapi import APIRouter, HTTPException, Query, BackgroundTasks, Header, Depends
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
import logging
import os

from app.services.sync_service import SyncService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/sync", tags=["Sync"])

# Initialize sync service
sync_service = SyncService()

# API Key for sync endpoints (set in environment variables)
SYNC_API_KEY = os.getenv("SYNC_API_KEY")


# ============================================================================
# Security - API Key Verification
# ============================================================================

async def verify_sync_key(x_sync_key: str = Header(None, alias="X-Sync-Key")):
    """
    Verify the sync API key from X-Sync-Key header.

    If SYNC_API_KEY is not configured, allows all requests (backward compatibility).
    If configured, requires matching key.
    """
    if not SYNC_API_KEY:
        # No key configured - log warning but allow (for development/backward compatibility)
        logger.warning("SYNC_API_KEY not configured - sync endpoints are unprotected!")
        return

    if not x_sync_key:
        logger.warning("Sync request without X-Sync-Key header")
        raise HTTPException(
            status_code=401,
            detail="Missing X-Sync-Key header. Authentication required."
        )

    if x_sync_key != SYNC_API_KEY:
        logger.warning(f"Invalid sync key attempt")
        raise HTTPException(
            status_code=401,
            detail="Invalid API key"
        )


# ============================================================================
# Response Models
# ============================================================================

class SyncStatusResponse(BaseModel):
    """Response model for sync status"""
    last_sales_sync: Optional[datetime]
    last_inventory_sync: Optional[datetime]
    orders_count: int
    last_order_date: Optional[datetime]
    warehouses_count: int
    products_with_stock: int


class SalesSyncResponse(BaseModel):
    """Response model for sales sync"""
    success: bool
    message: str
    orders_created: int
    orders_updated: int
    order_items_created: int
    errors: List[str]
    date_range: Dict[str, str]
    duration_seconds: float
    customers_fixed: int = 0  # Cleanup: customers linked to orders
    channels_fixed: int = 0   # Cleanup: channels fixed for orders


class InventorySyncResponse(BaseModel):
    """Response model for inventory sync"""
    success: bool
    message: str
    relbase_warehouses_synced: int
    relbase_products_updated: int
    mercadolibre_products_updated: int
    klog_products_updated: int = 0  # KLOG direct API sync
    errors: List[str]
    duration_seconds: float


class FullSyncResponse(BaseModel):
    """Response model for full sync"""
    success: bool
    message: str
    sales_sync: Optional[SalesSyncResponse]
    inventory_sync: Optional[InventorySyncResponse]
    total_duration_seconds: float
    timestamp: datetime


# ============================================================================
# Endpoints
# ============================================================================

@router.get("/status", response_model=SyncStatusResponse)
async def get_sync_status():
    """
    Get current sync status and statistics

    Returns information about:
    - Last sync timestamps
    - Total orders in database
    - Last order date
    - Warehouse and stock counts
    """
    try:
        status = await sync_service.get_sync_status()
        return status
    except Exception as e:
        logger.error(f"Error getting sync status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sales", response_model=SalesSyncResponse, dependencies=[Depends(verify_sync_key)])
async def sync_sales(
    days_back: int = Query(default=7, ge=1, le=365, description="Days to look back for missing data"),
    force_full: bool = Query(default=False, description="Force full sync instead of incremental"),
    date_from: Optional[str] = Query(default=None, description="Override start date (YYYY-MM-DD format)"),
    date_to: Optional[str] = Query(default=None, description="Override end date (YYYY-MM-DD format)")
):
    """
    Sync sales orders from RelBase

    Logic:
    1. Get last order date in database
    2. Fetch all DTEs from RelBase since that date
    3. Create/update orders and order_items
    4. Fill any gaps in data

    Args:
        days_back: How many days to look back (default 7)
        force_full: If True, sync all data regardless of last date
        date_from: Override start date (YYYY-MM-DD) for manual backfills
        date_to: Override end date (YYYY-MM-DD) for manual backfills
    """
    try:
        logger.info(f"Starting sales sync (days_back={days_back}, force_full={force_full}, date_from={date_from}, date_to={date_to})")
        result = await sync_service.sync_sales_from_relbase(
            days_back=days_back,
            force_full=force_full,
            date_from_override=date_from,
            date_to_override=date_to
        )
        # Convert dataclass to Pydantic model
        return SalesSyncResponse(
            success=result.success,
            message=result.message,
            orders_created=result.orders_created,
            orders_updated=result.orders_updated,
            order_items_created=result.order_items_created,
            errors=result.errors,
            date_range=result.date_range,
            duration_seconds=result.duration_seconds,
            customers_fixed=result.customers_fixed,
            channels_fixed=result.channels_fixed
        )
    except Exception as e:
        logger.error(f"Error syncing sales: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/inventory", response_model=InventorySyncResponse, dependencies=[Depends(verify_sync_key)])
async def sync_inventory():
    """
    Sync inventory from RelBase and MercadoLibre

    Logic:
    1. Fetch warehouse stock from RelBase (all warehouses)
    2. Fetch active listings from MercadoLibre
    3. Update warehouse_stock table
    """
    try:
        logger.info("Starting inventory sync")
        result = await sync_service.sync_inventory()
        # Convert dataclass to Pydantic model
        return InventorySyncResponse(
            success=result.success,
            message=result.message,
            relbase_warehouses_synced=result.relbase_warehouses_synced,
            relbase_products_updated=result.relbase_products_updated,
            mercadolibre_products_updated=result.mercadolibre_products_updated,
            errors=result.errors,
            duration_seconds=result.duration_seconds
        )
    except Exception as e:
        logger.error(f"Error syncing inventory: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/all", response_model=FullSyncResponse, dependencies=[Depends(verify_sync_key)])
async def sync_all(
    background_tasks: BackgroundTasks,
    days_back: int = Query(default=3, ge=1, le=30, description="Days to look back for sales"),
    run_in_background: bool = Query(default=False, description="Run sync in background")
):
    """
    Run full sync (sales + inventory)

    This is the endpoint for UptimeRobot to call.
    Keeps the service warm AND syncs data.

    Args:
        days_back: How many days to look back for sales
        run_in_background: If True, start sync and return immediately
    """
    start_time = datetime.now()

    if run_in_background:
        # Queue sync for background execution
        background_tasks.add_task(sync_service.run_full_sync, days_back)
        return FullSyncResponse(
            success=True,
            message="Sync started in background",
            sales_sync=None,
            inventory_sync=None,
            total_duration_seconds=0,
            timestamp=start_time
        )

    try:
        logger.info(f"Starting full sync (days_back={days_back})")

        # Run sales sync
        sales_result = await sync_service.sync_sales_from_relbase(days_back=days_back)

        # Run inventory sync
        inventory_result = await sync_service.sync_inventory()

        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()

        # Determine overall success
        overall_success = sales_result.success and inventory_result.success

        # Convert dataclass results to Pydantic models
        sales_response = SalesSyncResponse(
            success=sales_result.success,
            message=sales_result.message,
            orders_created=sales_result.orders_created,
            orders_updated=sales_result.orders_updated,
            order_items_created=sales_result.order_items_created,
            errors=sales_result.errors,
            date_range=sales_result.date_range,
            duration_seconds=sales_result.duration_seconds,
            customers_fixed=sales_result.customers_fixed,
            channels_fixed=sales_result.channels_fixed
        )

        inventory_response = InventorySyncResponse(
            success=inventory_result.success,
            message=inventory_result.message,
            relbase_warehouses_synced=inventory_result.relbase_warehouses_synced,
            relbase_products_updated=inventory_result.relbase_products_updated,
            mercadolibre_products_updated=inventory_result.mercadolibre_products_updated,
            errors=inventory_result.errors,
            duration_seconds=inventory_result.duration_seconds
        )

        return FullSyncResponse(
            success=overall_success,
            message="Full sync completed" if overall_success else "Sync completed with errors",
            sales_sync=sales_response,
            inventory_sync=inventory_response,
            total_duration_seconds=duration,
            timestamp=end_time
        )

    except Exception as e:
        logger.error(f"Error in full sync: {e}")
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()

        return FullSyncResponse(
            success=False,
            message=f"Sync failed: {str(e)}",
            sales_sync=None,
            inventory_sync=None,
            total_duration_seconds=duration,
            timestamp=end_time
        )


@router.get("/health")
async def sync_health():
    """
    Simple health check for the sync service
    Returns quickly - useful for keep-alive pings
    """
    return {
        "status": "healthy",
        "service": "sync",
        "timestamp": datetime.now().isoformat()
    }


@router.get("/debug-relbase")
async def debug_relbase_connectivity():
    """
    Debug endpoint to test RelBase API connectivity.
    Helps diagnose if Railway can reach RelBase.
    """
    import requests
    import time

    results = {
        "timestamp": datetime.now().isoformat(),
        "relbase_company_token": bool(os.getenv('RELBASE_COMPANY_TOKEN')),
        "relbase_user_token": bool(os.getenv('RELBASE_USER_TOKEN')),
        "tests": []
    }

    base_url = "https://api.relbase.cl"
    headers = {
        'company': os.getenv('RELBASE_COMPANY_TOKEN', ''),
        'authorization': os.getenv('RELBASE_USER_TOKEN', ''),
        'Content-Type': 'application/json'
    }

    # Test 1: Simple API connectivity (channels endpoint)
    try:
        start = time.time()
        response = requests.get(
            f"{base_url}/api/v1/canal_ventas",
            headers=headers,
            timeout=30
        )
        elapsed = round(time.time() - start, 2)
        results["tests"].append({
            "test": "channels_endpoint",
            "status_code": response.status_code,
            "elapsed_seconds": elapsed,
            "success": response.status_code == 200,
            "data_preview": str(response.json())[:200] if response.status_code == 200 else response.text[:200]
        })
    except Exception as e:
        results["tests"].append({
            "test": "channels_endpoint",
            "success": False,
            "error": str(e)
        })

    # Test 2: DTEs endpoint - check RECENT data (last 7 days dynamically)
    today = datetime.now().date()
    week_ago = today - timedelta(days=7)
    try:
        start = time.time()
        response = requests.get(
            f"{base_url}/api/v1/dtes",
            headers=headers,
            params={
                'type_document': 33,
                'start_date': week_ago.isoformat(),
                'end_date': today.isoformat(),
                'page': 1,
                'per_page': 50
            },
            timeout=60
        )
        elapsed = round(time.time() - start, 2)
        data = response.json() if response.status_code == 200 else {}
        dtes = data.get('data', {}).get('dtes', [])
        dtes_count = len(dtes)

        # Group DTEs by date
        dates_summary = {}
        for dte in dtes:
            created = dte.get('created_at', '')[:10] if dte.get('created_at') else 'unknown'
            dates_summary[created] = dates_summary.get(created, 0) + 1

        results["tests"].append({
            "test": "dtes_endpoint_recent",
            "status_code": response.status_code,
            "elapsed_seconds": elapsed,
            "success": response.status_code == 200,
            "date_range": f"{week_ago} to {today}",
            "dtes_returned": dtes_count,
            "dtes_by_date": dates_summary
        })
    except Exception as e:
        results["tests"].append({
            "test": "dtes_endpoint_recent",
            "success": False,
            "error": str(e)
        })

    # Overall status
    results["overall_success"] = all(t.get("success", False) for t in results["tests"])

    return results
