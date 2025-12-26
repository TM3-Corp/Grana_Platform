"""
Orders API Endpoints
Handles order management and queries

Author: TM3
Date: 2025-10-03
Updated: 2025-10-17 (refactor: use OrderRepository for data access)
Updated: 2025-11-14 (add executive dashboard endpoint with projections)
"""
from fastapi import APIRouter, HTTPException, Query
from typing import Optional
from datetime import datetime, timedelta
import statistics

from app.repositories.order_repository import OrderRepository

router = APIRouter()


@router.get("/")
async def get_orders(
    source: Optional[str] = Query(None, description="Filter by source (shopify, mercadolibre, etc.)"),
    status: Optional[str] = Query(None, description="Filter by order status"),
    payment_status: Optional[str] = Query(None, description="Filter by payment status"),
    from_date: Optional[str] = Query(None, description="Filter orders from this date (ISO format)"),
    to_date: Optional[str] = Query(None, description="Filter orders until this date (ISO format)"),
    search: Optional[str] = Query(None, description="Search by order number, customer name, email, or city"),
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
            search=search,
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


@router.get("/dashboard/executive-kpis")
async def get_executive_kpis(
    product_family: Optional[str] = Query(None, description="Filter by product family (BARRAS, CRACKERS, GRANOLAS, KEEPERS)")
):
    """
    Get executive dashboard KPIs with sales projections

    Returns:
    - Monthly data for 2024 (all 12 months)
    - Monthly data for 2025 (up to current month)
    - Projected data for remaining 2025 months
    - KPIs with YoY comparisons
    - Supports product family filtering

    Uses exponential smoothing with seasonal adjustment for projections.

    NOTE: Uses sales_facts_mv for consistent category data aligned with
    Desglose Pedidos and Sales Analytics pages.
    """
    conn = None
    cursor = None
    try:
        from app.core.database import get_db_connection_dict_with_retry

        conn = get_db_connection_dict_with_retry()
        cursor = conn.cursor()

        # Build WHERE clause for product family filter
        # Uses sales_facts_mv which has proper category from product_catalog + sku_mappings
        family_filter = ""
        params_2024 = []
        params_2025 = []

        if product_family and product_family.upper() != "TODAS":
            family_filter = "AND category = %s"
            params_2024 = [product_family.upper()]
            params_2025 = [product_family.upper()]

        # Get 2024 monthly data from sales_facts_mv
        query_2024 = f"""
            SELECT
                DATE_TRUNC('month', order_date)::date as month,
                COUNT(DISTINCT order_id) as total_orders,
                COALESCE(SUM(revenue), 0) as total_revenue
            FROM sales_facts_mv
            WHERE EXTRACT(YEAR FROM order_date) = 2024
            AND source = 'relbase'
            {family_filter}
            GROUP BY DATE_TRUNC('month', order_date)
            ORDER BY month
        """

        cursor.execute(query_2024, params_2024)
        data_2024 = cursor.fetchall()

        # Get 2025 monthly data from sales_facts_mv
        query_2025 = f"""
            SELECT
                DATE_TRUNC('month', order_date)::date as month,
                COUNT(DISTINCT order_id) as total_orders,
                COALESCE(SUM(revenue), 0) as total_revenue
            FROM sales_facts_mv
            WHERE EXTRACT(YEAR FROM order_date) = 2025
            AND source = 'relbase'
            {family_filter}
            GROUP BY DATE_TRUNC('month', order_date)
            ORDER BY month
        """

        cursor.execute(query_2025, params_2025)
        data_2025 = cursor.fetchall()

        # Process data
        current_date = datetime.now()
        current_month = current_date.month
        current_day = current_date.day
        current_year = current_date.year

        # Create lookup dictionaries
        monthly_2024 = {row['month'].month: row for row in data_2024}
        monthly_2025 = {row['month'].month: row for row in data_2025}

        # FAIR COMPARISON FIX: For the current month, get 2024 data only up to the same day
        # This ensures we compare Dec 1-17, 2024 with Dec 1-17, 2025 (not full Dec 2024 vs partial Dec 2025)
        monthly_2024_mtd = {}  # Month-to-date adjusted data for current month
        if current_month in monthly_2024:
            # Query 2024 current month with same date range (day 1 to current_day) from sales_facts_mv
            query_2024_mtd = f"""
                SELECT
                    COUNT(DISTINCT order_id) as total_orders,
                    COALESCE(SUM(revenue), 0) as total_revenue
                FROM sales_facts_mv
                WHERE EXTRACT(YEAR FROM order_date) = 2024
                AND EXTRACT(MONTH FROM order_date) = %s
                AND EXTRACT(DAY FROM order_date) <= %s
                AND source = 'relbase'
                {family_filter}
            """
            mtd_params = [current_month, current_day] + params_2024
            cursor.execute(query_2024_mtd, mtd_params)
            mtd_result = cursor.fetchone()
            if mtd_result:
                monthly_2024_mtd[current_month] = {
                    'total_orders': mtd_result['total_orders'],
                    'total_revenue': mtd_result['total_revenue']
                }

        # Calculate YoY growth rates for months we have in both years
        # Use MTD-adjusted data for the current month to ensure fair comparison
        growth_rates = []
        for month in range(1, min(current_month + 1, 13)):
            if month in monthly_2024 and month in monthly_2025:
                # For current month, use MTD-adjusted 2024 data for fair comparison
                if month == current_month and month in monthly_2024_mtd:
                    rev_2024 = float(monthly_2024_mtd[month]['total_revenue'])
                else:
                    rev_2024 = float(monthly_2024[month]['total_revenue'])
                rev_2025 = float(monthly_2025[month]['total_revenue'])
                if rev_2024 > 0:
                    growth_rate = ((rev_2025 - rev_2024) / rev_2024) * 100
                    growth_rates.append(growth_rate)

        # Calculate average growth rate and std dev for projections
        avg_growth_rate = statistics.mean(growth_rates) if growth_rates else 0
        std_dev = statistics.stdev(growth_rates) if len(growth_rates) > 1 else 10

        # Build response data
        sales_by_month_2024 = []
        sales_by_month_2025 = []
        projections_2025 = []

        # 2024 data (all 12 months)
        # FAIR COMPARISON: For current month, use MTD value as primary (chart shows this directly)
        for month in range(1, 13):
            month_name = datetime(2024, month, 1).strftime('%b')
            is_current_month = (month == current_month)

            if month in monthly_2024:
                # For current month, use MTD-adjusted value as primary so chart shows fair comparison
                if is_current_month and month in monthly_2024_mtd:
                    entry = {
                        'month': month,
                        'month_name': month_name,
                        'year': 2024,
                        'total_orders': monthly_2024_mtd[month]['total_orders'],
                        'total_revenue': float(monthly_2024_mtd[month]['total_revenue']),  # MTD value as primary
                        'total_revenue_full_month': float(monthly_2024[month]['total_revenue']),  # Keep full month for reference
                        'total_orders_full_month': monthly_2024[month]['total_orders'],
                        'is_mtd': True,
                        'mtd_day': current_day,
                    }
                else:
                    entry = {
                        'month': month,
                        'month_name': month_name,
                        'year': 2024,
                        'total_orders': monthly_2024[month]['total_orders'],
                        'total_revenue': float(monthly_2024[month]['total_revenue']),
                    }
                sales_by_month_2024.append(entry)
            else:
                sales_by_month_2024.append({
                    'month': month,
                    'month_name': month_name,
                    'year': 2024,
                    'total_orders': 0,
                    'total_revenue': 0,
                })

        # 2025 actual data (up to current month)
        for month in range(1, current_month + 1):
            month_name = datetime(2025, month, 1).strftime('%b')
            is_current_month = (month == current_month)

            if month in monthly_2025:
                entry = {
                    'month': month,
                    'month_name': month_name,
                    'year': 2025,
                    'total_orders': monthly_2025[month]['total_orders'],
                    'total_revenue': float(monthly_2025[month]['total_revenue']),
                    'is_actual': True,
                    'is_mtd': is_current_month,  # Mark current month as month-to-date
                }
                if is_current_month:
                    entry['mtd_day'] = current_day
                    # For incomplete month, estimate full month based on 2024 pattern
                    if month in monthly_2024 and month in monthly_2024_mtd:
                        mtd_2024 = float(monthly_2024_mtd[month]['total_revenue'])
                        full_2024 = float(monthly_2024[month]['total_revenue'])
                        if mtd_2024 > 0:
                            mtd_ratio = mtd_2024 / full_2024
                            entry['estimated_full_month'] = float(monthly_2025[month]['total_revenue']) / mtd_ratio
                sales_by_month_2025.append(entry)
            else:
                sales_by_month_2025.append({
                    'month': month,
                    'month_name': month_name,
                    'year': 2025,
                    'total_orders': 0,
                    'total_revenue': 0,
                    'is_actual': True,
                    'is_mtd': is_current_month,
                })

        # 2025 projected data for ALL 12 months (based on 2024 + growth rate)
        # This allows comparison of actual vs projected for past months too
        for month in range(1, 13):
            month_name = datetime(2025, month, 1).strftime('%b')
            is_future_month = month > current_month if current_year == 2025 else False

            # Use same month from 2024 as baseline
            if month in monthly_2024:
                baseline_revenue = float(monthly_2024[month]['total_revenue'])
                baseline_orders = monthly_2024[month]['total_orders']

                # Apply growth rate
                projected_revenue = baseline_revenue * (1 + avg_growth_rate / 100)
                projected_orders = int(baseline_orders * (1 + avg_growth_rate / 100))

                # Calculate confidence interval (±1 std dev)
                confidence_lower = projected_revenue * (1 - std_dev / 100)
                confidence_upper = projected_revenue * (1 + std_dev / 100)

                projections_2025.append({
                    'month': month,
                    'month_name': month_name,
                    'year': 2025,
                    'total_orders': projected_orders,
                    'total_revenue': projected_revenue,
                    'is_actual': False,
                    'is_projection': True,
                    'is_future': is_future_month,
                    'confidence_lower': confidence_lower,
                    'confidence_upper': confidence_upper,
                    'growth_rate_applied': avg_growth_rate
                })
            else:
                # No baseline data, use average from 2025 so far
                if monthly_2025:
                    avg_revenue = statistics.mean([float(row['total_revenue']) for row in monthly_2025.values()])
                    avg_orders = int(statistics.mean([row['total_orders'] for row in monthly_2025.values()]))
                else:
                    avg_revenue = 0
                    avg_orders = 0

                projections_2025.append({
                    'month': month,
                    'month_name': month_name,
                    'year': 2025,
                    'total_orders': avg_orders,
                    'total_revenue': float(avg_revenue),
                    'is_actual': False,
                    'is_projection': True,
                    'is_future': is_future_month,
                    'confidence_lower': float(avg_revenue * 0.8),
                    'confidence_upper': float(avg_revenue * 1.2),
                    'growth_rate_applied': 0
                })

        # 2026 projected data (NEXT YEAR projections based on 2025 actual + growth rate)
        # Calculate 2025 vs 2024 growth rate for next year projection
        # Use MTD-adjusted data for current month to ensure fair comparison
        growth_rates_2025 = []
        for month in range(1, 13):
            if month in monthly_2024 and month in monthly_2025:
                # For current month, use MTD-adjusted 2024 data for fair comparison
                if month == current_month and month in monthly_2024_mtd:
                    rev_2024 = float(monthly_2024_mtd[month]['total_revenue'])
                else:
                    rev_2024 = float(monthly_2024[month]['total_revenue'])
                rev_2025 = float(monthly_2025[month]['total_revenue'])
                if rev_2024 > 0:
                    growth_rate = ((rev_2025 - rev_2024) / rev_2024) * 100
                    growth_rates_2025.append(growth_rate)

        avg_growth_rate_2026 = statistics.mean(growth_rates_2025) if growth_rates_2025 else avg_growth_rate
        std_dev_2026 = statistics.stdev(growth_rates_2025) if len(growth_rates_2025) > 1 else std_dev

        projections_2026 = []
        for month in range(1, 13):
            month_name = datetime(2026, month, 1).strftime('%b')

            # Use same month from 2025 as baseline for 2026 projections
            if month in monthly_2025:
                # For the current incomplete month, estimate full month based on 2024 pattern
                # This answers: "How am I doing until this date vs last year?" and projects the full month
                is_incomplete_month = (month == current_month and current_year == 2025)

                if is_incomplete_month and month in monthly_2024 and month in monthly_2024_mtd:
                    # Calculate MTD ratio from 2024: what % of the month is days 1-current_day?
                    mtd_2024 = float(monthly_2024_mtd[month]['total_revenue'])
                    full_2024 = float(monthly_2024[month]['total_revenue'])

                    if mtd_2024 > 0:
                        # mtd_ratio = portion of month represented by days 1-current_day
                        mtd_ratio = mtd_2024 / full_2024

                        # Estimate 2025 full month: current_mtd / ratio
                        mtd_2025 = float(monthly_2025[month]['total_revenue'])
                        estimated_full_2025 = mtd_2025 / mtd_ratio

                        baseline_revenue = estimated_full_2025
                        baseline_orders = int(monthly_2025[month]['total_orders'] / mtd_ratio)
                    else:
                        baseline_revenue = float(monthly_2025[month]['total_revenue'])
                        baseline_orders = monthly_2025[month]['total_orders']
                else:
                    # Complete month - use actual value
                    baseline_revenue = float(monthly_2025[month]['total_revenue'])
                    baseline_orders = monthly_2025[month]['total_orders']

                # Apply growth rate
                projected_revenue = baseline_revenue * (1 + avg_growth_rate_2026 / 100)
                projected_orders = int(baseline_orders * (1 + avg_growth_rate_2026 / 100))

                # Calculate confidence interval (±1 std dev)
                confidence_lower = projected_revenue * (1 - std_dev_2026 / 100)
                confidence_upper = projected_revenue * (1 + std_dev_2026 / 100)

                projection_entry = {
                    'month': month,
                    'month_name': month_name,
                    'year': 2026,
                    'total_orders': projected_orders,
                    'total_revenue': projected_revenue,
                    'is_actual': False,
                    'is_projection': True,
                    'is_future': True,
                    'confidence_lower': confidence_lower,
                    'confidence_upper': confidence_upper,
                    'growth_rate_applied': avg_growth_rate_2026
                }

                # Add metadata for incomplete month estimation
                if is_incomplete_month and month in monthly_2024 and month in monthly_2024_mtd:
                    projection_entry['is_estimated_from_mtd'] = True
                    projection_entry['estimated_2025_full_month'] = baseline_revenue
                    projection_entry['mtd_ratio_used'] = mtd_ratio if mtd_2024 > 0 else None

                projections_2026.append(projection_entry)
            else:
                # No 2025 baseline, use average from 2025
                if monthly_2025:
                    avg_revenue = statistics.mean([float(row['total_revenue']) for row in monthly_2025.values()])
                    avg_orders = int(statistics.mean([row['total_orders'] for row in monthly_2025.values()]))
                    projected_revenue = avg_revenue * (1 + avg_growth_rate_2026 / 100)
                    projected_orders = int(avg_orders * (1 + avg_growth_rate_2026 / 100))
                else:
                    projected_revenue = 0
                    projected_orders = 0

                projections_2026.append({
                    'month': month,
                    'month_name': month_name,
                    'year': 2026,
                    'total_orders': projected_orders,
                    'total_revenue': float(projected_revenue),
                    'is_actual': False,
                    'is_projection': True,
                    'is_future': True,
                    'confidence_lower': float(projected_revenue * 0.8),
                    'confidence_upper': float(projected_revenue * 1.2),
                    'growth_rate_applied': avg_growth_rate_2026
                })

        # Calculate KPIs
        total_revenue_2024 = sum([m['total_revenue'] for m in sales_by_month_2024])
        total_orders_2024 = sum([m['total_orders'] for m in sales_by_month_2024])
        avg_ticket_2024 = total_revenue_2024 / total_orders_2024 if total_orders_2024 > 0 else 0

        total_revenue_2025_actual = sum([m['total_revenue'] for m in sales_by_month_2025])
        total_orders_2025_actual = sum([m['total_orders'] for m in sales_by_month_2025])
        avg_ticket_2025 = total_revenue_2025_actual / total_orders_2025_actual if total_orders_2025_actual > 0 else 0

        # Calculate YoY changes (comparing same period)
        # FAIR COMPARISON: For current month, use MTD-adjusted 2024 data
        # This compares Dec 1-17, 2024 with Dec 1-17, 2025 instead of full Dec 2024 vs partial Dec 2025
        total_revenue_2024_ytd = 0
        total_orders_2024_ytd = 0
        for m in range(1, current_month + 1):
            if m == current_month and m in monthly_2024_mtd:
                # Use MTD-adjusted data for current month (fair comparison)
                total_revenue_2024_ytd += float(monthly_2024_mtd[m]['total_revenue'])
                total_orders_2024_ytd += monthly_2024_mtd[m]['total_orders']
            elif m in monthly_2024:
                # Use full month data for completed months
                total_revenue_2024_ytd += float(monthly_2024[m]['total_revenue'])
                total_orders_2024_ytd += monthly_2024[m]['total_orders']

        revenue_yoy_change = ((total_revenue_2025_actual - total_revenue_2024_ytd) / total_revenue_2024_ytd * 100) if total_revenue_2024_ytd > 0 else 0
        orders_yoy_change = ((total_orders_2025_actual - total_orders_2024_ytd) / total_orders_2024_ytd * 100) if total_orders_2024_ytd > 0 else 0
        ticket_yoy_change = ((avg_ticket_2025 - avg_ticket_2024) / avg_ticket_2024 * 100) if avg_ticket_2024 > 0 else 0

        # Calculate 2026 projected totals
        total_revenue_2026_projected = sum([m['total_revenue'] for m in projections_2026])
        total_orders_2026_projected = sum([m['total_orders'] for m in projections_2026])

        return {
            "status": "success",
            "data": {
                "sales_2024": sales_by_month_2024,
                "sales_2025_actual": sales_by_month_2025,
                "sales_2025_projected": projections_2025,
                "sales_2026_projected": projections_2026,
                "kpis": {
                    "total_revenue_2024": total_revenue_2024,
                    "total_revenue_2025_actual": total_revenue_2025_actual,
                    "total_revenue_2026_projected": total_revenue_2026_projected,
                    "total_orders_2024": total_orders_2024,
                    "total_orders_2025_actual": total_orders_2025_actual,
                    "total_orders_2026_projected": total_orders_2026_projected,
                    "avg_ticket_2024": avg_ticket_2024,
                    "avg_ticket_2025": avg_ticket_2025,
                    "revenue_yoy_change": revenue_yoy_change,
                    "orders_yoy_change": orders_yoy_change,
                    "ticket_yoy_change": ticket_yoy_change,
                },
                "projection_metadata": {
                    "avg_growth_rate": avg_growth_rate,
                    "avg_growth_rate_2026": avg_growth_rate_2026,
                    "std_dev": std_dev,
                    "std_dev_2026": std_dev_2026,
                    "months_projected": len(projections_2025),
                    "current_month": current_month,
                    "current_year": current_year,
                    "mtd_day": current_day,
                    "is_mtd_comparison": current_month in monthly_2024_mtd,
                    "mtd_comparison_info": f"Diciembre: comparando días 1-{current_day} de 2024 vs 2025" if current_month in monthly_2024_mtd else None,
                    # Incomplete month estimation for 2026 projections
                    "incomplete_month_estimation": {
                        "month": current_month,
                        "mtd_ratio": float(monthly_2024_mtd[current_month]['total_revenue']) / float(monthly_2024[current_month]['total_revenue']) if current_month in monthly_2024_mtd and current_month in monthly_2024 else None,
                        "estimated_2025_full_month": float(monthly_2025[current_month]['total_revenue']) / (float(monthly_2024_mtd[current_month]['total_revenue']) / float(monthly_2024[current_month]['total_revenue'])) if current_month in monthly_2025 and current_month in monthly_2024_mtd and current_month in monthly_2024 else None
                    } if current_month in monthly_2024_mtd else None
                }
            }
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching executive KPIs: {str(e)}")
    finally:
        # Always close cursor and connection to prevent leaks
        if cursor:
            cursor.close()
        if conn:
            conn.close()


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
