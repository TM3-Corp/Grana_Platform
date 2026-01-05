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
    - Monthly data for previous year (all 12 months) - "baseline year"
    - Monthly data for current year (up to current month) - "comparison year"
    - Projected data for next year
    - KPIs with YoY comparisons
    - Supports product family filtering

    DYNAMIC YEARS: Automatically adjusts based on current date
    - If current year is 2026: compares 2025 vs 2026, projects 2027
    - If current year is 2025: compares 2024 vs 2025, projects 2026

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

        # Process data - DYNAMIC YEAR CALCULATION
        current_date = datetime.now()
        current_month = current_date.month
        current_day = current_date.day
        current_year = current_date.year

        # Dynamic year assignments
        previous_year = current_year - 1  # e.g., 2025 when current is 2026
        next_year = current_year + 1      # e.g., 2027 when current is 2026

        # Build WHERE clause for product family filter
        # Uses sales_facts_mv which has proper category from product_catalog + sku_mappings
        family_filter = ""
        params_prev = []
        params_curr = []

        if product_family and product_family.upper() != "TODAS":
            family_filter = "AND category = %s"
            params_prev = [product_family.upper()]
            params_curr = [product_family.upper()]

        # Get PREVIOUS YEAR monthly data from sales_facts_mv (e.g., 2025)
        query_prev_year = f"""
            SELECT
                DATE_TRUNC('month', order_date)::date as month,
                COUNT(DISTINCT order_id) as total_orders,
                COALESCE(SUM(revenue), 0) as total_revenue
            FROM sales_facts_mv
            WHERE EXTRACT(YEAR FROM order_date) = %s
            AND source = 'relbase'
            {family_filter}
            GROUP BY DATE_TRUNC('month', order_date)
            ORDER BY month
        """

        cursor.execute(query_prev_year, [previous_year] + params_prev)
        data_prev_year = cursor.fetchall()

        # Get CURRENT YEAR monthly data from sales_facts_mv (e.g., 2026)
        query_curr_year = f"""
            SELECT
                DATE_TRUNC('month', order_date)::date as month,
                COUNT(DISTINCT order_id) as total_orders,
                COALESCE(SUM(revenue), 0) as total_revenue
            FROM sales_facts_mv
            WHERE EXTRACT(YEAR FROM order_date) = %s
            AND source = 'relbase'
            {family_filter}
            GROUP BY DATE_TRUNC('month', order_date)
            ORDER BY month
        """

        cursor.execute(query_curr_year, [current_year] + params_curr)
        data_curr_year = cursor.fetchall()

        # Get YEAR BEFORE PREVIOUS (e.g., 2024) for historical growth calculation
        # This is needed when current year has no data (beginning of year edge case)
        year_before_previous = previous_year - 1
        query_ybp = f"""
            SELECT
                DATE_TRUNC('month', order_date)::date as month,
                COUNT(DISTINCT order_id) as total_orders,
                COALESCE(SUM(revenue), 0) as total_revenue
            FROM sales_facts_mv
            WHERE EXTRACT(YEAR FROM order_date) = %s
            AND source = 'relbase'
            {family_filter}
            GROUP BY DATE_TRUNC('month', order_date)
            ORDER BY month
        """
        cursor.execute(query_ybp, [year_before_previous] + params_prev)
        data_ybp = cursor.fetchall()
        monthly_ybp = {row['month'].month: row for row in data_ybp}

        # Create lookup dictionaries
        monthly_prev = {row['month'].month: row for row in data_prev_year}
        monthly_curr = {row['month'].month: row for row in data_curr_year}

        # FAIR COMPARISON FIX: For the current month, get previous year data only up to the same day
        # This ensures we compare Jan 1-3, 2025 with Jan 1-3, 2026 (not full Jan 2025 vs partial Jan 2026)
        monthly_prev_mtd = {}  # Month-to-date adjusted data for current month
        if current_month in monthly_prev:
            # Query previous year current month with same date range (day 1 to current_day) from sales_facts_mv
            query_prev_mtd = f"""
                SELECT
                    COUNT(DISTINCT order_id) as total_orders,
                    COALESCE(SUM(revenue), 0) as total_revenue
                FROM sales_facts_mv
                WHERE EXTRACT(YEAR FROM order_date) = %s
                AND EXTRACT(MONTH FROM order_date) = %s
                AND EXTRACT(DAY FROM order_date) <= %s
                AND source = 'relbase'
                {family_filter}
            """
            mtd_params = [previous_year, current_month, current_day] + params_prev
            cursor.execute(query_prev_mtd, mtd_params)
            mtd_result = cursor.fetchone()
            if mtd_result:
                monthly_prev_mtd[current_month] = {
                    'total_orders': mtd_result['total_orders'],
                    'total_revenue': mtd_result['total_revenue']
                }

        # Calculate YoY growth rates for months we have in both years
        # Use MTD-adjusted data for the current month to ensure fair comparison
        growth_rates = []
        for month in range(1, min(current_month + 1, 13)):
            if month in monthly_prev and month in monthly_curr:
                # For current month, use MTD-adjusted previous year data for fair comparison
                if month == current_month and month in monthly_prev_mtd:
                    rev_prev = float(monthly_prev_mtd[month]['total_revenue'])
                else:
                    rev_prev = float(monthly_prev[month]['total_revenue'])
                rev_curr = float(monthly_curr[month]['total_revenue'])
                if rev_prev > 0:
                    growth_rate = ((rev_curr - rev_prev) / rev_prev) * 100
                    growth_rates.append(growth_rate)

        # Check if current year has meaningful data
        current_year_total = sum([float(row['total_revenue']) for row in monthly_curr.values()])

        # FALLBACK: If current year has no meaningful data (start of year edge case),
        # calculate historical growth from year_before_previous to previous_year (e.g., 2024→2025)
        historical_growth_rates = []
        if current_year_total < 1000:  # Less than $1000 = essentially no data
            for month in range(1, 13):
                if month in monthly_ybp and month in monthly_prev:
                    rev_ybp = float(monthly_ybp[month]['total_revenue'])
                    rev_prev = float(monthly_prev[month]['total_revenue'])
                    if rev_ybp > 0:
                        growth_rate = ((rev_prev - rev_ybp) / rev_ybp) * 100
                        historical_growth_rates.append(growth_rate)

        # Calculate average growth rate and std dev for projections
        # Use historical growth rates when current year has no data
        if historical_growth_rates and not growth_rates:
            avg_growth_rate = statistics.mean(historical_growth_rates)
            std_dev = statistics.stdev(historical_growth_rates) if len(historical_growth_rates) > 1 else 10
        else:
            avg_growth_rate = statistics.mean(growth_rates) if growth_rates else 0
            std_dev = statistics.stdev(growth_rates) if len(growth_rates) > 1 else 10

        # Build response data
        sales_by_month_prev = []
        sales_by_month_curr = []
        projections_curr = []

        # PREVIOUS YEAR data (all 12 months) - e.g., 2025 when current year is 2026
        # FAIR COMPARISON: For current month, use MTD value as primary (chart shows this directly)
        for month in range(1, 13):
            month_name = datetime(previous_year, month, 1).strftime('%b')
            is_current_month = (month == current_month)

            if month in monthly_prev:
                # For current month, use MTD-adjusted value as primary so chart shows fair comparison
                if is_current_month and month in monthly_prev_mtd:
                    entry = {
                        'month': month,
                        'month_name': month_name,
                        'year': previous_year,
                        'total_orders': monthly_prev_mtd[month]['total_orders'],
                        'total_revenue': float(monthly_prev_mtd[month]['total_revenue']),  # MTD value as primary
                        'total_revenue_full_month': float(monthly_prev[month]['total_revenue']),  # Keep full month for reference
                        'total_orders_full_month': monthly_prev[month]['total_orders'],
                        'is_mtd': True,
                        'mtd_day': current_day,
                    }
                else:
                    entry = {
                        'month': month,
                        'month_name': month_name,
                        'year': previous_year,
                        'total_orders': monthly_prev[month]['total_orders'],
                        'total_revenue': float(monthly_prev[month]['total_revenue']),
                    }
                sales_by_month_prev.append(entry)
            else:
                sales_by_month_prev.append({
                    'month': month,
                    'month_name': month_name,
                    'year': previous_year,
                    'total_orders': 0,
                    'total_revenue': 0,
                })

        # CURRENT YEAR actual data (up to current month) - e.g., 2026
        for month in range(1, current_month + 1):
            month_name = datetime(current_year, month, 1).strftime('%b')
            is_current_month_flag = (month == current_month)

            if month in monthly_curr:
                entry = {
                    'month': month,
                    'month_name': month_name,
                    'year': current_year,
                    'total_orders': monthly_curr[month]['total_orders'],
                    'total_revenue': float(monthly_curr[month]['total_revenue']),
                    'is_actual': True,
                    'is_mtd': is_current_month_flag,  # Mark current month as month-to-date
                }
                if is_current_month_flag:
                    entry['mtd_day'] = current_day
                    # For incomplete month, estimate full month based on previous year pattern
                    if month in monthly_prev and month in monthly_prev_mtd:
                        mtd_prev = float(monthly_prev_mtd[month]['total_revenue'])
                        full_prev = float(monthly_prev[month]['total_revenue'])
                        if mtd_prev > 0:
                            mtd_ratio = mtd_prev / full_prev
                            entry['estimated_full_month'] = float(monthly_curr[month]['total_revenue']) / mtd_ratio
                sales_by_month_curr.append(entry)
            else:
                sales_by_month_curr.append({
                    'month': month,
                    'month_name': month_name,
                    'year': current_year,
                    'total_orders': 0,
                    'total_revenue': 0,
                    'is_actual': True,
                    'is_mtd': is_current_month_flag,
                })

        # CURRENT YEAR projected data for ALL 12 months (based on previous year + growth rate)
        # This allows comparison of actual vs projected for past months too
        for month in range(1, 13):
            month_name = datetime(current_year, month, 1).strftime('%b')
            is_future_month = month > current_month

            # Use same month from previous year as baseline
            if month in monthly_prev:
                baseline_revenue = float(monthly_prev[month]['total_revenue'])
                baseline_orders = monthly_prev[month]['total_orders']

                # Apply growth rate
                projected_revenue = baseline_revenue * (1 + avg_growth_rate / 100)
                projected_orders = int(baseline_orders * (1 + avg_growth_rate / 100))

                # Calculate confidence interval (±1 std dev)
                confidence_lower = projected_revenue * (1 - std_dev / 100)
                confidence_upper = projected_revenue * (1 + std_dev / 100)

                projections_curr.append({
                    'month': month,
                    'month_name': month_name,
                    'year': current_year,
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
                # No baseline data, use average from current year so far
                if monthly_curr:
                    avg_revenue = statistics.mean([float(row['total_revenue']) for row in monthly_curr.values()])
                    avg_orders = int(statistics.mean([row['total_orders'] for row in monthly_curr.values()]))
                else:
                    avg_revenue = 0
                    avg_orders = 0

                projections_curr.append({
                    'month': month,
                    'month_name': month_name,
                    'year': current_year,
                    'total_orders': avg_orders,
                    'total_revenue': float(avg_revenue),
                    'is_actual': False,
                    'is_projection': True,
                    'is_future': is_future_month,
                    'confidence_lower': float(avg_revenue * 0.8),
                    'confidence_upper': float(avg_revenue * 1.2),
                    'growth_rate_applied': 0
                })

        # NEXT YEAR projected data (projections based on current year actual + growth rate)
        # Calculate MONTH-SPECIFIC growth rates (current vs previous year) for more accurate projections
        # Each month uses its own YoY growth rate instead of a uniform average
        growth_rates_by_month = {}  # {month: growth_rate}
        growth_rates_list = []  # For calculating average fallback
        for month in range(1, 13):
            if month in monthly_prev and month in monthly_curr:
                # For current month, use MTD-adjusted previous year data for fair comparison
                if month == current_month and month in monthly_prev_mtd:
                    rev_prev = float(monthly_prev_mtd[month]['total_revenue'])
                else:
                    rev_prev = float(monthly_prev[month]['total_revenue'])
                rev_curr = float(monthly_curr[month]['total_revenue'])
                if rev_prev > 0:
                    growth_rate = ((rev_curr - rev_prev) / rev_prev) * 100
                    growth_rates_by_month[month] = growth_rate
                    growth_rates_list.append(growth_rate)

        # Calculate average as fallback for months without specific data
        avg_growth_rate_next = statistics.mean(growth_rates_list) if growth_rates_list else avg_growth_rate
        std_dev_next = statistics.stdev(growth_rates_list) if len(growth_rates_list) > 1 else std_dev

        # Check if current year has meaningful data - if not, use previous year as baseline
        current_year_total_revenue = sum([float(row['total_revenue']) for row in monthly_curr.values()])
        use_previous_year_as_baseline = current_year_total_revenue < 1000  # Less than $1000 = essentially no data

        projections_next = []
        for month in range(1, 13):
            month_name = datetime(next_year, month, 1).strftime('%b')

            # EDGE CASE: Beginning of new year with no current year data
            # Use previous year as baseline with historical growth rate
            if use_previous_year_as_baseline and month in monthly_prev:
                prev_revenue = float(monthly_prev[month]['total_revenue'])
                prev_orders = monthly_prev[month]['total_orders']

                # Apply historical growth rate to project from previous year to next year (2 years forward)
                # If avg_growth_rate is 10%, then 2 years = (1.10)^2 - 1 = 21%
                two_year_growth = ((1 + avg_growth_rate / 100) ** 2 - 1) * 100

                projected_revenue = prev_revenue * (1 + two_year_growth / 100)
                projected_orders = int(prev_orders * (1 + two_year_growth / 100))

                confidence_lower = projected_revenue * (1 - std_dev_next / 100)
                confidence_upper = projected_revenue * (1 + std_dev_next / 100)

                projections_next.append({
                    'month': month,
                    'month_name': month_name,
                    'year': next_year,
                    'total_orders': projected_orders,
                    'total_revenue': projected_revenue,
                    'is_actual': False,
                    'is_projection': True,
                    'is_future': True,
                    'confidence_lower': confidence_lower,
                    'confidence_upper': confidence_upper,
                    'growth_rate_applied': two_year_growth,
                    'baseline_year': previous_year,
                    'baseline_note': f'Projected from {previous_year} (no {current_year} data yet)'
                })
                continue

            # Use same month from current year as baseline for next year projections
            if month in monthly_curr:
                # For the current incomplete month, estimate full month based on previous year pattern
                # This answers: "How am I doing until this date vs last year?" and projects the full month
                is_incomplete_month = (month == current_month)

                if is_incomplete_month and month in monthly_prev and month in monthly_prev_mtd:
                    # Calculate MTD ratio from previous year: what % of the month is days 1-current_day?
                    mtd_prev = float(monthly_prev_mtd[month]['total_revenue'])
                    full_prev = float(monthly_prev[month]['total_revenue'])

                    if mtd_prev > 0:
                        # mtd_ratio = portion of month represented by days 1-current_day
                        mtd_ratio = mtd_prev / full_prev

                        # Estimate current year full month: current_mtd / ratio
                        mtd_curr = float(monthly_curr[month]['total_revenue'])
                        estimated_full_curr = mtd_curr / mtd_ratio

                        baseline_revenue = estimated_full_curr
                        baseline_orders = int(monthly_curr[month]['total_orders'] / mtd_ratio)
                    else:
                        baseline_revenue = float(monthly_curr[month]['total_revenue'])
                        baseline_orders = monthly_curr[month]['total_orders']
                else:
                    # Complete month - use actual value
                    baseline_revenue = float(monthly_curr[month]['total_revenue'])
                    baseline_orders = monthly_curr[month]['total_orders']

                # Apply MONTH-SPECIFIC growth rate (fall back to average if not available)
                month_growth_rate = growth_rates_by_month.get(month, avg_growth_rate_next)
                projected_revenue = baseline_revenue * (1 + month_growth_rate / 100)
                projected_orders = int(baseline_orders * (1 + month_growth_rate / 100))

                # Calculate confidence interval (±1 std dev)
                confidence_lower = projected_revenue * (1 - std_dev_next / 100)
                confidence_upper = projected_revenue * (1 + std_dev_next / 100)

                projection_entry = {
                    'month': month,
                    'month_name': month_name,
                    'year': next_year,
                    'total_orders': projected_orders,
                    'total_revenue': projected_revenue,
                    'is_actual': False,
                    'is_projection': True,
                    'is_future': True,
                    'confidence_lower': confidence_lower,
                    'confidence_upper': confidence_upper,
                    'growth_rate_applied': month_growth_rate  # Now shows month-specific rate
                }

                # Add metadata for incomplete month estimation
                if is_incomplete_month and month in monthly_prev and month in monthly_prev_mtd:
                    projection_entry['is_estimated_from_mtd'] = True
                    projection_entry['estimated_curr_full_month'] = baseline_revenue
                    projection_entry['mtd_ratio_used'] = mtd_ratio if mtd_prev > 0 else None

                projections_next.append(projection_entry)
            else:
                # No current year ACTUAL data for this month
                # Try to use current year PROJECTION as baseline (from projections_curr)
                curr_year_projection = next(
                    (p for p in projections_curr if p['month'] == month),
                    None
                )

                if curr_year_projection and curr_year_projection['total_revenue'] > 0:
                    # Use 2026 projection as baseline for 2027
                    baseline_revenue = curr_year_projection['total_revenue']
                    baseline_orders = curr_year_projection['total_orders']
                    projected_revenue = baseline_revenue * (1 + avg_growth_rate_next / 100)
                    projected_orders = int(baseline_orders * (1 + avg_growth_rate_next / 100))
                    baseline_note = f'Based on {current_year} projection'
                elif month in monthly_prev:
                    # Fall back to previous year with 2-year growth
                    prev_revenue = float(monthly_prev[month]['total_revenue'])
                    prev_orders = monthly_prev[month]['total_orders']
                    two_year_growth = ((1 + avg_growth_rate_next / 100) ** 2 - 1) * 100
                    projected_revenue = prev_revenue * (1 + two_year_growth / 100)
                    projected_orders = int(prev_orders * (1 + two_year_growth / 100))
                    baseline_note = f'Based on {previous_year} with 2-year growth'
                else:
                    projected_revenue = 0
                    projected_orders = 0
                    baseline_note = 'No baseline data'

                projections_next.append({
                    'month': month,
                    'month_name': month_name,
                    'year': next_year,
                    'total_orders': projected_orders,
                    'total_revenue': float(projected_revenue),
                    'is_actual': False,
                    'is_projection': True,
                    'is_future': True,
                    'confidence_lower': float(projected_revenue * 0.8),
                    'confidence_upper': float(projected_revenue * 1.2),
                    'growth_rate_applied': avg_growth_rate_next,
                    'baseline_note': baseline_note
                })

        # Calculate KPIs using dynamic year variables
        total_revenue_prev = sum([m['total_revenue'] for m in sales_by_month_prev])
        total_orders_prev = sum([m['total_orders'] for m in sales_by_month_prev])
        avg_ticket_prev = total_revenue_prev / total_orders_prev if total_orders_prev > 0 else 0

        total_revenue_curr = sum([m['total_revenue'] for m in sales_by_month_curr])
        total_orders_curr = sum([m['total_orders'] for m in sales_by_month_curr])
        avg_ticket_curr = total_revenue_curr / total_orders_curr if total_orders_curr > 0 else 0

        # Calculate YoY changes (comparing same period)
        # FAIR COMPARISON: For current month, use MTD-adjusted previous year data
        total_revenue_prev_ytd = 0
        total_orders_prev_ytd = 0
        for m in range(1, current_month + 1):
            if m == current_month and m in monthly_prev_mtd:
                # Use MTD-adjusted data for current month (fair comparison)
                total_revenue_prev_ytd += float(monthly_prev_mtd[m]['total_revenue'])
                total_orders_prev_ytd += monthly_prev_mtd[m]['total_orders']
            elif m in monthly_prev:
                # Use full month data for completed months
                total_revenue_prev_ytd += float(monthly_prev[m]['total_revenue'])
                total_orders_prev_ytd += monthly_prev[m]['total_orders']

        revenue_yoy_change = ((total_revenue_curr - total_revenue_prev_ytd) / total_revenue_prev_ytd * 100) if total_revenue_prev_ytd > 0 else 0
        orders_yoy_change = ((total_orders_curr - total_orders_prev_ytd) / total_orders_prev_ytd * 100) if total_orders_prev_ytd > 0 else 0
        # Calculate YTD-adjusted average ticket for fair comparison
        avg_ticket_prev_ytd = total_revenue_prev_ytd / total_orders_prev_ytd if total_orders_prev_ytd > 0 else 0
        ticket_yoy_change = ((avg_ticket_curr - avg_ticket_prev_ytd) / avg_ticket_prev_ytd * 100) if avg_ticket_prev_ytd > 0 else 0

        # Calculate next year projected totals
        total_revenue_next_projected = sum([m['total_revenue'] for m in projections_next])
        total_orders_next_projected = sum([m['total_orders'] for m in projections_next])

        # Get current month name for dynamic message
        current_month_name = datetime(current_year, current_month, 1).strftime('%B')

        return {
            "status": "success",
            "data": {
                # Use generic keys but include actual years in the data
                "sales_previous_year": sales_by_month_prev,
                "sales_current_year": sales_by_month_curr,
                "sales_current_year_projected": projections_curr,
                "sales_next_year_projected": projections_next,
                "kpis": {
                    "total_revenue_previous_year": total_revenue_prev,
                    "total_revenue_current_year": total_revenue_curr,
                    "total_revenue_next_year_projected": total_revenue_next_projected,
                    "total_orders_previous_year": total_orders_prev,
                    "total_orders_current_year": total_orders_curr,
                    "total_orders_next_year_projected": total_orders_next_projected,
                    "avg_ticket_previous_year": avg_ticket_prev,
                    "avg_ticket_current_year": avg_ticket_curr,
                    "revenue_yoy_change": revenue_yoy_change,
                    "orders_yoy_change": orders_yoy_change,
                    "ticket_yoy_change": ticket_yoy_change,
                    # YTD-adjusted values for fair comparison display (same period as current year)
                    "total_revenue_previous_year_ytd": total_revenue_prev_ytd,
                    "total_orders_previous_year_ytd": total_orders_prev_ytd,
                    "avg_ticket_previous_year_ytd": avg_ticket_prev_ytd,
                },
                "projection_metadata": {
                    "avg_growth_rate": avg_growth_rate,
                    "avg_growth_rate_next_year": avg_growth_rate_next,
                    "growth_rates_by_month": growth_rates_by_month,
                    "projection_method": "month_specific",
                    "std_dev": std_dev,
                    "std_dev_next_year": std_dev_next,
                    "months_projected": len(projections_curr),
                    "current_month": current_month,
                    "current_month_name": current_month_name,
                    "current_year": current_year,
                    "previous_year": previous_year,
                    "next_year": next_year,
                    "mtd_day": current_day,
                    "is_mtd_comparison": current_month in monthly_prev_mtd,
                    "mtd_comparison_info": f"{current_month_name}: comparando días 1-{current_day} de {previous_year} vs {current_year}" if current_month in monthly_prev_mtd else None,
                    # Incomplete month estimation for next year projections
                    "incomplete_month_estimation": {
                        "month": current_month,
                        "mtd_ratio": float(monthly_prev_mtd[current_month]['total_revenue']) / float(monthly_prev[current_month]['total_revenue']) if current_month in monthly_prev_mtd and current_month in monthly_prev else None,
                        "estimated_curr_full_month": float(monthly_curr[current_month]['total_revenue']) / (float(monthly_prev_mtd[current_month]['total_revenue']) / float(monthly_prev[current_month]['total_revenue'])) if current_month in monthly_curr and current_month in monthly_prev_mtd and current_month in monthly_prev else None
                    } if current_month in monthly_prev_mtd else None
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
