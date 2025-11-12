"""
Sales Analytics API - Dynamic sales visualization with filters and grouping
Only uses RelBase data to avoid duplicates
"""
from fastapi import APIRouter, Query, HTTPException
from typing import List, Optional, Dict, Any
import psycopg2
import os
from datetime import datetime, timedelta

router = APIRouter()

# Database connection
DATABASE_URL = os.getenv("DATABASE_URL")

@router.get("")
async def get_sales_analytics(
    # Date filters
    from_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    to_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
    time_period: str = Query('auto', description="Time grouping: day, month, year, or auto (auto-detect based on date range)"),

    # Multi-select filters
    sources: Optional[List[str]] = Query(['relbase'], description="Data sources - DEFAULT: relbase only"),
    channels: Optional[List[str]] = Query(None, description="Channel names (multi-select)"),
    customers: Optional[List[str]] = Query(None, description="Customer names (multi-select)"),
    categories: Optional[List[str]] = Query(None, description="Product categories (multi-select)"),
    formats: Optional[List[str]] = Query(None, description="Product formats (multi-select)"),

    # Grouping and limits
    group_by: Optional[str] = Query(None, description="Group by: category, channel, customer, format, sku_primario"),
    stack_by: Optional[str] = Query(None, description="Stack by: channel, customer, format (creates grouped stacked bars)"),
    top_limit: int = Query(10, ge=5, le=30, description="Top N items to show"),

    # Pagination
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=10, le=500, description="Items per page")
):
    """
    Dynamic Sales Analytics endpoint

    Features:
    - Multi-dimensional filtering (dates, channels, customers, categories, formats)
    - Dynamic grouping (by category, channel, customer, format, SKU)
    - Timeline analysis (month-by-month breakdown)
    - Top N items (configurable limit)
    - Only RelBase data (no duplicates)

    Returns:
    - Summary metrics (total revenue, units, orders, avg ticket, growth)
    - Timeline data (month-by-month with optional grouping)
    - Top items (ranked by revenue)
    - Grouped data table (for display)
    - Pagination info
    """

    try:
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()

        # Build base filters
        where_clauses = ["o.source = ANY(%s)"]  # Always filter by source
        params = [sources]  # Default ['relbase']

        # CRITICAL: Exclude cancelled and declined invoices (no revenue)
        # Relbase invoices can have status: accepted, accepted_objection, cancel, declined
        # Only 'accepted' and 'accepted_objection' generate revenue
        # Other sources (shopify, lokal, etc.) don't have invoice_status, so we allow NULL
        where_clauses.append("(o.invoice_status IN ('accepted', 'accepted_objection') OR o.invoice_status IS NULL)")

        # Date filters
        if from_date and to_date:
            where_clauses.append("o.order_date >= %s AND o.order_date <= %s")
            params.extend([from_date, to_date])
        elif from_date:
            where_clauses.append("o.order_date >= %s")
            params.append(from_date)
        elif to_date:
            where_clauses.append("o.order_date <= %s")
            params.append(to_date)
        else:
            # Default to 2025 for backward compatibility
            where_clauses.append("EXTRACT(YEAR FROM o.order_date) = 2025")

        # Multi-select filters
        if channels:
            channel_conditions = ' OR '.join(['ch.name ILIKE %s'] * len(channels))
            where_clauses.append(f"({channel_conditions})")
            for ch in channels:
                params.append(f"%{ch}%")

        if customers:
            customer_conditions = ' OR '.join(['cust.name ILIKE %s'] * len(customers))
            where_clauses.append(f"({customer_conditions})")
            for cust in customers:
                params.append(f"%{cust}%")

        if categories:
            placeholders = ','.join(['%s'] * len(categories))
            where_clauses.append(f"p.category IN ({placeholders})")
            params.extend(categories)

        if formats:
            placeholders = ','.join(['%s'] * len(formats))
            where_clauses.append(f"p.format IN ({placeholders})")
            params.extend(formats)

        where_clause = " AND ".join(where_clauses)

        # === AUTO-DETECT TIME PERIOD ===
        if time_period == 'auto':
            if from_date and to_date:
                # Calculate days between dates
                from_dt = datetime.strptime(from_date, '%Y-%m-%d')
                to_dt = datetime.strptime(to_date, '%Y-%m-%d')
                days_diff = (to_dt - from_dt).days

                if days_diff <= 31:
                    time_period = 'day'
                elif days_diff <= 365:
                    time_period = 'month'
                else:
                    time_period = 'year'
            else:
                # Default to month if no date range specified
                time_period = 'month'

        # Build period expression based on time_period
        period_expr_map = {
            'day': "TO_CHAR(o.order_date, 'YYYY-MM-DD')",
            'week': "TO_CHAR(DATE_TRUNC('week', o.order_date), 'YYYY-\"W\"IW')",  # ISO week format: 2025-W45
            'month': "TO_CHAR(DATE_TRUNC('month', o.order_date), 'YYYY-MM')",
            'quarter': "TO_CHAR(DATE_TRUNC('quarter', o.order_date), 'YYYY-\"Q\"Q')",  # Quarter format: 2025-Q4
            'year': "EXTRACT(YEAR FROM o.order_date)::text"
        }
        period_expr = period_expr_map.get(time_period, period_expr_map['month'])

        # Determine group field based on group_by parameter
        group_field_map = {
            'category': 'p.category',
            'channel': 'ch.name',
            'customer': 'cust.name',
            'format': 'p.format',
            'sku_primario': 'oi.product_sku'  # Simplified - using SKU directly
        }
        group_field = group_field_map.get(group_by, 'p.category')  # Default to category

        # Determine stack field if stack_by is provided
        stack_field = None
        if stack_by:
            stack_field = group_field_map.get(stack_by)

        # === 1. SUMMARY METRICS ===
        summary_query = f"""
            SELECT
                SUM(oi.total) as total_revenue,
                SUM(oi.quantity) as total_units,
                COUNT(DISTINCT o.id) as total_orders,
                CASE
                    WHEN COUNT(DISTINCT o.id) > 0 THEN SUM(oi.total) / COUNT(DISTINCT o.id)
                    ELSE 0
                END as avg_ticket
            FROM orders o
            JOIN order_items oi ON o.id = oi.order_id
            LEFT JOIN channels ch ON o.channel_id = ch.id
            LEFT JOIN customers cust ON o.customer_id = cust.id
            LEFT JOIN products p ON oi.product_id = p.id
            WHERE {where_clause}
        """

        cur.execute(summary_query, params)
        summary_row = cur.fetchone()

        summary = {
            "total_revenue": float(summary_row[0] or 0),
            "total_units": int(summary_row[1] or 0),
            "total_orders": int(summary_row[2] or 0),
            "avg_ticket": float(summary_row[3] or 0),
            "growth_rate": 0  # TODO: Calculate growth vs previous period
        }

        # === 2. TIMELINE DATA ===
        # Timeline breakdown with dynamic time grouping (day/month/year)
        if group_by and stack_by and stack_field:
            # DOUBLE GROUPING: period + group + stack
            timeline_query = f"""
                SELECT
                    {period_expr} as period,
                    {group_field} as group_value,
                    {stack_field} as stack_value,
                    SUM(oi.total) as revenue,
                    SUM(oi.quantity) as units,
                    COUNT(DISTINCT o.id) as orders
                FROM orders o
                JOIN order_items oi ON o.id = oi.order_id
                LEFT JOIN channels ch ON o.channel_id = ch.id
                LEFT JOIN customers cust ON o.customer_id = cust.id
                LEFT JOIN products p ON oi.product_id = p.id
                WHERE {where_clause}
                GROUP BY period, group_value, stack_value
                ORDER BY period, group_value, revenue DESC
            """
        elif group_by:
            # SINGLE GROUPING: period + group
            timeline_query = f"""
                SELECT
                    {period_expr} as period,
                    {group_field} as group_value,
                    SUM(oi.total) as revenue,
                    SUM(oi.quantity) as units,
                    COUNT(DISTINCT o.id) as orders
                FROM orders o
                JOIN order_items oi ON o.id = oi.order_id
                LEFT JOIN channels ch ON o.channel_id = ch.id
                LEFT JOIN customers cust ON o.customer_id = cust.id
                LEFT JOIN products p ON oi.product_id = p.id
                WHERE {where_clause}
                GROUP BY period, group_value
                ORDER BY period, revenue DESC
            """
        else:
            # NO GROUPING: period only
            timeline_query = f"""
                SELECT
                    {period_expr} as period,
                    SUM(oi.total) as revenue,
                    SUM(oi.quantity) as units,
                    COUNT(DISTINCT o.id) as orders
                FROM orders o
                JOIN order_items oi ON o.id = oi.order_id
                LEFT JOIN channels ch ON o.channel_id = ch.id
                LEFT JOIN customers cust ON o.customer_id = cust.id
                LEFT JOIN products p ON oi.product_id = p.id
                WHERE {where_clause}
                GROUP BY period
                ORDER BY period
            """

        cur.execute(timeline_query, params)
        timeline_rows = cur.fetchall()

        # Process timeline data
        timeline_dict = {}

        if group_by and stack_by and stack_field:
            # DOUBLE GROUPING: period → group → stack
            # First pass: build nested structure
            for row in timeline_rows:
                period, group_value, stack_value, revenue, units, orders = row

                # Initialize period
                if period not in timeline_dict:
                    timeline_dict[period] = {
                        "period": period,
                        "total_revenue": 0,
                        "total_units": 0,
                        "total_orders": 0,
                        "by_group": {}
                    }

                # Initialize group within period
                if group_value not in timeline_dict[period]["by_group"]:
                    timeline_dict[period]["by_group"][group_value] = {
                        "group_value": group_value,
                        "revenue": 0,
                        "units": 0,
                        "orders": 0,
                        "by_stack": []
                    }

                # Add stack data
                timeline_dict[period]["by_group"][group_value]["revenue"] += float(revenue or 0)
                timeline_dict[period]["by_group"][group_value]["units"] += int(units or 0)
                timeline_dict[period]["by_group"][group_value]["orders"] += int(orders or 0)
                timeline_dict[period]["by_group"][group_value]["by_stack"].append({
                    "stack_value": stack_value,
                    "revenue": float(revenue or 0),
                    "units": int(units or 0),
                    "orders": int(orders or 0)
                })

                # Update period totals
                timeline_dict[period]["total_revenue"] += float(revenue or 0)
                timeline_dict[period]["total_units"] += int(units or 0)
                timeline_dict[period]["total_orders"] += int(orders or 0)

            # Convert group dict to list
            for period_data in timeline_dict.values():
                period_data["by_group"] = list(period_data["by_group"].values())

            timeline = list(timeline_dict.values())

        elif group_by:
            # SINGLE GROUPING: period → group
            for row in timeline_rows:
                period, group_value, revenue, units, orders = row
                if period not in timeline_dict:
                    timeline_dict[period] = {
                        "period": period,
                        "total_revenue": 0,
                        "total_units": 0,
                        "total_orders": 0,
                        "by_group": []
                    }
                timeline_dict[period]["total_revenue"] += float(revenue or 0)
                timeline_dict[period]["total_units"] += int(units or 0)
                timeline_dict[period]["total_orders"] += int(orders or 0)
                timeline_dict[period]["by_group"].append({
                    "group_value": group_value,
                    "revenue": float(revenue or 0),
                    "units": int(units or 0),
                    "orders": int(orders or 0)
                })

            timeline = list(timeline_dict.values())

        else:
            # NO GROUPING: period only
            for row in timeline_rows:
                period, revenue, units, orders = row
                timeline_dict[period] = {
                    "period": period,
                    "total_revenue": float(revenue or 0),
                    "total_units": int(units or 0),
                    "total_orders": int(orders or 0)
                }

            timeline = list(timeline_dict.values())

        # === 3. TOP ITEMS ===
        top_query = f"""
            SELECT
                {group_field} as group_value,
                SUM(oi.total) as revenue,
                SUM(oi.quantity) as units,
                COUNT(DISTINCT o.id) as orders
            FROM orders o
            JOIN order_items oi ON o.id = oi.order_id
            LEFT JOIN channels ch ON o.channel_id = ch.id
            LEFT JOIN customers cust ON o.customer_id = cust.id
            LEFT JOIN products p ON oi.product_id = p.id
            WHERE {where_clause}
            GROUP BY {group_field}
            HAVING {group_field} IS NOT NULL
            ORDER BY revenue DESC
            LIMIT %s
        """

        cur.execute(top_query, params + [top_limit])
        top_rows = cur.fetchall()

        top_items = []
        for row in top_rows:
            group_value, revenue, units, orders = row
            percentage = (float(revenue) / summary["total_revenue"] * 100) if summary["total_revenue"] > 0 else 0
            top_items.append({
                "group_value": group_value,
                "revenue": float(revenue or 0),
                "units": int(units or 0),
                "orders": int(orders or 0),
                "percentage": round(percentage, 2)
            })

        # === 4. GROUPED DATA TABLE ===
        offset = (page - 1) * page_size

        grouped_query = f"""
            SELECT
                {group_field} as group_value,
                SUM(oi.total) as revenue,
                SUM(oi.quantity) as units,
                COUNT(DISTINCT o.id) as orders,
                CASE
                    WHEN COUNT(DISTINCT o.id) > 0 THEN SUM(oi.total) / COUNT(DISTINCT o.id)
                    ELSE 0
                END as avg_ticket
            FROM orders o
            JOIN order_items oi ON o.id = oi.order_id
            LEFT JOIN channels ch ON o.channel_id = ch.id
            LEFT JOIN customers cust ON o.customer_id = cust.id
            LEFT JOIN products p ON oi.product_id = p.id
            WHERE {where_clause}
            GROUP BY {group_field}
            HAVING {group_field} IS NOT NULL
            ORDER BY revenue DESC
            LIMIT %s OFFSET %s
        """

        cur.execute(grouped_query, params + [page_size, offset])
        grouped_rows = cur.fetchall()

        grouped_data = []
        for row in grouped_rows:
            group_value, revenue, units, orders, avg_ticket = row
            grouped_data.append({
                "group_value": group_value,
                "revenue": float(revenue or 0),
                "units": int(units or 0),
                "orders": int(orders or 0),
                "avg_ticket": float(avg_ticket or 0)
            })

        # Count total items for pagination
        count_query = f"""
            SELECT COUNT(DISTINCT {group_field})
            FROM orders o
            JOIN order_items oi ON o.id = oi.order_id
            LEFT JOIN channels ch ON o.channel_id = ch.id
            LEFT JOIN customers cust ON o.customer_id = cust.id
            LEFT JOIN products p ON oi.product_id = p.id
            WHERE {where_clause} AND {group_field} IS NOT NULL
        """

        cur.execute(count_query, params)
        total_items = cur.fetchone()[0]
        total_pages = (total_items + page_size - 1) // page_size

        cur.close()
        conn.close()

        return {
            "success": True,
            "data": {
                "summary": summary,
                "timeline": timeline,
                "top_items": top_items,
                "grouped_data": grouped_data,
                "pagination": {
                    "current_page": page,
                    "total_pages": total_pages,
                    "total_items": total_items,
                    "page_size": page_size
                },
                "filters": {
                    "from_date": from_date,
                    "to_date": to_date,
                    "time_period": time_period,
                    "sources": sources,
                    "channels": channels,
                    "customers": customers,
                    "categories": categories,
                    "formats": formats,
                    "group_by": group_by,
                    "stack_by": stack_by,
                    "top_limit": top_limit
                }
            }
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching sales analytics: {str(e)}")
