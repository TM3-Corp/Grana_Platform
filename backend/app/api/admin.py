"""
Admin API - OLAP Management Endpoints
Provides administrative operations for data warehouse maintenance

Author: Claude Code
Date: 2025-11-12
"""
from fastapi import APIRouter, HTTPException, BackgroundTasks
from typing import Dict, Any
import psycopg2
import os
from datetime import datetime

router = APIRouter()

# Database connection
DATABASE_URL = os.getenv("DATABASE_URL")

@router.post("/refresh-analytics")
async def refresh_analytics(background_tasks: BackgroundTasks) -> Dict[str, Any]:
    """
    Refresh sales_facts_mv materialized view

    This endpoint triggers a refresh of the OLAP materialized view.
    Should be called:
    - After RelBase data sync completes
    - After Shopify order sync
    - Before generating executive reports

    Uses CONCURRENTLY to avoid blocking read queries during refresh.
    Unique index added in migration 20260116000001.
    Refresh time: ~3-4 seconds for current data size.

    Returns:
        success: Boolean indicating if refresh was successful
        message: Human-readable status message
        refresh_time: Time taken to refresh (in seconds)
        timestamp: ISO timestamp of when refresh occurred
    """
    try:
        start_time = datetime.now()

        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()

        # Refresh materialized view CONCURRENTLY (no read locks)
        # Requires unique index on MV (migration 20260116000001)
        cur.execute("REFRESH MATERIALIZED VIEW CONCURRENTLY sales_facts_mv")
        conn.commit()

        # Get MV statistics
        cur.execute("""
            SELECT
                COUNT(*) as row_count,
                pg_size_pretty(pg_total_relation_size('sales_facts_mv')) as size
            FROM sales_facts_mv
        """)
        row_count, size = cur.fetchone()

        # Get materialized view metadata
        cur.execute("""
            SELECT ispopulated
            FROM pg_matviews
            WHERE matviewname = 'sales_facts_mv'
        """)
        is_populated = cur.fetchone()[0]

        cur.close()
        conn.close()

        end_time = datetime.now()
        refresh_time = (end_time - start_time).total_seconds()

        return {
            "success": True,
            "message": "Materialized view refreshed successfully (CONCURRENTLY, no read locks)",
            "refresh_time_seconds": round(refresh_time, 2),
            "timestamp": end_time.isoformat(),
            "statistics": {
                "row_count": row_count,
                "size": size,
                "is_populated": is_populated
            }
        }

    except psycopg2.OperationalError as e:
        raise HTTPException(
            status_code=503,
            detail=f"Database connection error: {str(e)}"
        )
    except psycopg2.Error as e:
        raise HTTPException(
            status_code=500,
            detail=f"Database error during refresh: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Unexpected error: {str(e)}"
        )


@router.get("/analytics-status")
async def get_analytics_status() -> Dict[str, Any]:
    """
    Get current status of analytics materialized view

    Returns metadata about the sales_facts_mv without refreshing it.
    Useful for monitoring and health checks.

    Returns:
        exists: Boolean indicating if MV exists
        row_count: Number of rows in MV
        size: Human-readable size of MV
        is_populated: Boolean indicating if MV has data
        indexes: Number of indexes on MV
    """
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()

        # Check if MV exists
        cur.execute("""
            SELECT EXISTS (
                SELECT 1
                FROM pg_matviews
                WHERE matviewname = 'sales_facts_mv'
            )
        """)
        mv_exists = cur.fetchone()[0]

        if not mv_exists:
            return {
                "success": True,
                "exists": False,
                "message": "Materialized view does not exist"
            }

        # Get MV statistics
        cur.execute("""
            SELECT
                COUNT(*) as row_count,
                pg_size_pretty(pg_total_relation_size('sales_facts_mv')) as size,
                MIN(order_date) as earliest_date,
                MAX(order_date) as latest_date,
                COUNT(DISTINCT source) as sources,
                COUNT(DISTINCT order_id) as unique_orders
            FROM sales_facts_mv
        """)
        stats = cur.fetchone()

        # Get materialized view info
        cur.execute("""
            SELECT
                schemaname,
                matviewname,
                ispopulated
            FROM pg_matviews
            WHERE matviewname = 'sales_facts_mv'
        """)
        mv_info = cur.fetchone()

        # Get index count
        cur.execute("""
            SELECT COUNT(*)
            FROM pg_indexes
            WHERE tablename = 'sales_facts_mv'
        """)
        index_count = cur.fetchone()[0]

        cur.close()
        conn.close()

        return {
            "success": True,
            "exists": True,
            "schema": mv_info[0],
            "name": mv_info[1],
            "is_populated": mv_info[2],
            "statistics": {
                "row_count": stats[0],
                "size": stats[1],
                "earliest_date": stats[2].isoformat() if stats[2] else None,
                "latest_date": stats[3].isoformat() if stats[3] else None,
                "sources": stats[4],
                "unique_orders": stats[5],
                "indexes": index_count
            }
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error fetching analytics status: {str(e)}"
        )
