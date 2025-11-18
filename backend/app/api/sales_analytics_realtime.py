"""
Sales Analytics API - Real-Time Version
Uses orders + order_items tables directly (same as Audit endpoint)
Ensures perfect alignment with Desglose Pedidos data

Author: Claude Code
Date: 2025-11-14
"""
from fastapi import APIRouter, Query, HTTPException
from typing import List, Optional
from app.core.database import get_db_connection_dict

router = APIRouter()

@router.get("")
async def get_sales_analytics_realtime(
    # Date filters
    from_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD) - INCLUSIVE"),
    to_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD) - INCLUSIVE"),
    time_period: str = Query('auto', description="Time grouping: day, week, month, quarter, year, or auto"),

    # Multi-select filters
    sources: Optional[List[str]] = Query(['relbase'], description="Data sources - DEFAULT: relbase only"),
    channels: Optional[List[str]] = Query(None, description="Channel names (multi-select)"),
    customers: Optional[List[str]] = Query(None, description="Customer names (multi-select)"),
    categories: Optional[List[str]] = Query(None, description="Product categories (multi-select)"),
    formats: Optional[List[str]] = Query(None, description="Product formats (multi-select)"),

    # Grouping and limits
    group_by: Optional[str] = Query(None, description="Group by: category, channel, customer, format, sku_primario"),
    stack_by: Optional[str] = Query(None, description="Stack by: channel, customer, format"),
    top_limit: int = Query(10, ge=5, le=30, description="Top N items to show"),

    # Pagination
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=10, le=500, description="Items per page")
):
    """
    Real-Time Sales Analytics endpoint

    Uses orders + order_items tables directly (same as Audit endpoint)
    for perfect data alignment
    """

    try:
        conn = get_db_connection_dict()
        cursor = conn.cursor()

        # Build base WHERE clauses
        where_clauses = []
        params = []

        # Source filter
        if sources:
            placeholders = ','.join(['%s'] * len(sources))
            where_clauses.append(f"o.source IN ({placeholders})")
            params.extend(sources)

        # Invoice status filter (only for relbase orders)
        # Only show accepted and accepted_objection invoices (exclude cancelled, declined, NULL)
        if sources and 'relbase' in sources:
            where_clauses.append("o.invoice_status IN ('accepted', 'accepted_objection')")

        # Date filters (INCLUSIVE on both ends, matching Audit endpoint)
        if from_date and to_date:
            where_clauses.append("o.order_date >= %s AND o.order_date <= %s")
            params.extend([from_date, to_date])
        elif from_date:
            where_clauses.append("o.order_date >= %s")
            params.append(from_date)
        elif to_date:
            where_clauses.append("o.order_date <= %s")
            params.append(to_date)
        # No else clause - require explicit date filter from frontend (Option C)

        # Multi-select filters
        if channels:
            channel_conditions = ' OR '.join(['ch.name ILIKE %s'] * len(channels))
            where_clauses.append(f"({channel_conditions})")
            for ch in channels:
                params.append(f"%{ch}%")

        if customers:
            # Support both direct customer match and channel-based mapping (same as Audit)
            customer_conditions = ' OR '.join([
                'cust_direct.name ILIKE %s',
                'cust_channel.name ILIKE %s'
            ] * len(customers))
            where_clauses.append(f"({customer_conditions})")
            for cust in customers:
                params.append(f"%{cust}%")
                params.append(f"%{cust}%")

        if categories:
            placeholders = ','.join(['%s'] * len(categories))
            where_clauses.append(f"p.category IN ({placeholders})")
            params.extend(categories)

        if formats:
            format_conditions = ' OR '.join(['p.format ILIKE %s'] * len(formats))
            where_clauses.append(f"({format_conditions})")
            for fmt in formats:
                params.append(f"%{fmt}%")

        where_clause = " AND ".join(where_clauses) if where_clauses else "1=1"

        # Determine time period for timeline
        if time_period == 'auto':
            # Auto-detect based on date range
            if from_date and to_date:
                cursor.execute("SELECT %s::date - %s::date as days", (to_date, from_date))
                days = cursor.fetchone()['days']
                if days <= 31:
                    time_period = 'day'
                elif days <= 90:
                    time_period = 'week'
                elif days <= 365:
                    time_period = 'month'
                else:
                    time_period = 'quarter'
            else:
                time_period = 'month'

        # Map time period to SQL
        period_formats = {
            'day': "TO_CHAR(o.order_date, 'YYYY-MM-DD')",
            'week': "TO_CHAR(DATE_TRUNC('week', o.order_date), 'YYYY-MM-DD')",
            'month': "TO_CHAR(o.order_date, 'YYYY-MM')",
            'quarter': "TO_CHAR(o.order_date, 'YYYY-\"Q\"Q')",
            'year': "TO_CHAR(o.order_date, 'YYYY')"
        }
        period_sql = period_formats[time_period]

        # Build GROUP BY field
        group_fields = {
            'category': 'p.category',
            'channel': 'ch.name',
            'customer': 'COALESCE(cust_direct.name, cust_channel.name)',
            'format': 'p.format',
            'sku_primario': 'oi.product_sku'  # Using original SKU for now
        }
        group_field = group_fields.get(group_by, 'p.category')

        # Query 1: Summary KPIs
        # Build customer JOINs only if customer filter is active (to avoid row duplication)
        if customers:
            customer_joins = """
                LEFT JOIN customers cust_direct
                    ON cust_direct.id = o.customer_id
                    AND cust_direct.source = o.source
                LEFT JOIN LATERAL (
                    SELECT customer_external_id
                    FROM customer_channel_rules ccr
                    WHERE ccr.channel_external_id::text = (
                        o.customer_notes::json->>'channel_id_relbase'
                    )
                    AND ccr.is_active = TRUE
                ) ccr_match ON true
                LEFT JOIN customers cust_channel
                    ON cust_channel.external_id = ccr_match.customer_external_id
                    AND cust_channel.source = 'relbase'
            """
        else:
            customer_joins = ""

        summary_query = f"""
            SELECT
                COALESCE(SUM(oi.subtotal), 0) as total_revenue,
                COALESCE(SUM(oi.quantity), 0) as total_units,
                COUNT(DISTINCT o.id) as total_orders,
                CASE
                    WHEN COUNT(DISTINCT o.id) > 0
                    THEN COALESCE(SUM(oi.subtotal), 0) / COUNT(DISTINCT o.id)
                    ELSE 0
                END as avg_ticket
            FROM orders o
            LEFT JOIN order_items oi ON oi.order_id = o.id
            LEFT JOIN products p ON p.sku = oi.product_sku
            LEFT JOIN channels ch ON ch.id = o.channel_id
            {customer_joins}
            WHERE {where_clause}
        """

        cursor.execute(summary_query, params)
        summary = cursor.fetchone()

        # Query 2: Timeline
        timeline_query = f"""
            SELECT
                {period_sql} as period,
                COALESCE(SUM(oi.subtotal), 0) as total_revenue,
                COALESCE(SUM(oi.quantity), 0) as total_units,
                COUNT(DISTINCT o.id) as total_orders
            FROM orders o
            LEFT JOIN order_items oi ON oi.order_id = o.id
            LEFT JOIN products p ON p.sku = oi.product_sku
            LEFT JOIN channels ch ON ch.id = o.channel_id
            LEFT JOIN customers cust_direct
                ON cust_direct.id = o.customer_id
                AND cust_direct.source = o.source
            LEFT JOIN LATERAL (
                SELECT customer_external_id
                FROM customer_channel_rules ccr
                WHERE ccr.channel_external_id::text = (
                    o.customer_notes::json->>'channel_id_relbase'
                )
                AND ccr.is_active = TRUE
            ) ccr_match ON true
            LEFT JOIN customers cust_channel
                ON cust_channel.external_id = ccr_match.customer_external_id
                AND cust_channel.source = 'relbase'
            WHERE {where_clause}
            GROUP BY {period_sql}
            ORDER BY {period_sql}
        """

        cursor.execute(timeline_query, params)
        timeline = cursor.fetchall()

        # Query 3: Top Items
        top_items_query = f"""
            SELECT
                {group_field} as group_value,
                COALESCE(SUM(oi.subtotal), 0) as revenue,
                COALESCE(SUM(oi.quantity), 0) as units,
                COUNT(DISTINCT o.id) as orders
            FROM orders o
            LEFT JOIN order_items oi ON oi.order_id = o.id
            LEFT JOIN products p ON p.sku = oi.product_sku
            LEFT JOIN channels ch ON ch.id = o.channel_id
            LEFT JOIN customers cust_direct
                ON cust_direct.id = o.customer_id
                AND cust_direct.source = o.source
            LEFT JOIN LATERAL (
                SELECT customer_external_id
                FROM customer_channel_rules ccr
                WHERE ccr.channel_external_id::text = (
                    o.customer_notes::json->>'channel_id_relbase'
                )
                AND ccr.is_active = TRUE
            ) ccr_match ON true
            LEFT JOIN customers cust_channel
                ON cust_channel.external_id = ccr_match.customer_external_id
                AND cust_channel.source = 'relbase'
            WHERE {where_clause} AND {group_field} IS NOT NULL
            GROUP BY {group_field}
            ORDER BY revenue DESC
            LIMIT %s
        """

        cursor.execute(top_items_query, params + [top_limit])
        top_items = cursor.fetchall()

        # Calculate percentages
        total_revenue = summary['total_revenue']
        for item in top_items:
            item['percentage'] = (item['revenue'] / total_revenue * 100) if total_revenue > 0 else 0

        # Query 4: Grouped Data (for table)
        offset = (page - 1) * page_size
        grouped_query = f"""
            SELECT
                {group_field} as group_value,
                COALESCE(SUM(oi.subtotal), 0) as revenue,
                COALESCE(SUM(oi.quantity), 0) as units,
                COUNT(DISTINCT o.id) as orders,
                CASE
                    WHEN COUNT(DISTINCT o.id) > 0
                    THEN COALESCE(SUM(oi.subtotal), 0) / COUNT(DISTINCT o.id)
                    ELSE 0
                END as avg_ticket
            FROM orders o
            LEFT JOIN order_items oi ON oi.order_id = o.id
            LEFT JOIN products p ON p.sku = oi.product_sku
            LEFT JOIN channels ch ON ch.id = o.channel_id
            LEFT JOIN customers cust_direct
                ON cust_direct.id = o.customer_id
                AND cust_direct.source = o.source
            LEFT JOIN LATERAL (
                SELECT customer_external_id
                FROM customer_channel_rules ccr
                WHERE ccr.channel_external_id::text = (
                    o.customer_notes::json->>'channel_id_relbase'
                )
                AND ccr.is_active = TRUE
            ) ccr_match ON true
            LEFT JOIN customers cust_channel
                ON cust_channel.external_id = ccr_match.customer_external_id
                AND cust_channel.source = 'relbase'
            WHERE {where_clause} AND {group_field} IS NOT NULL
            GROUP BY {group_field}
            ORDER BY revenue DESC
            LIMIT %s OFFSET %s
        """

        cursor.execute(grouped_query, params + [page_size, offset])
        grouped_data = cursor.fetchall()

        # Get total count for pagination
        count_query = f"""
            SELECT COUNT(DISTINCT {group_field}) as count
            FROM orders o
            LEFT JOIN order_items oi ON oi.order_id = o.id
            LEFT JOIN products p ON p.sku = oi.product_sku
            LEFT JOIN channels ch ON ch.id = o.channel_id
            LEFT JOIN customers cust_direct
                ON cust_direct.id = o.customer_id
                AND cust_direct.source = o.source
            LEFT JOIN LATERAL (
                SELECT customer_external_id
                FROM customer_channel_rules ccr
                WHERE ccr.channel_external_id::text = (
                    o.customer_notes::json->>'channel_id_relbase'
                )
                AND ccr.is_active = TRUE
            ) ccr_match ON true
            LEFT JOIN customers cust_channel
                ON cust_channel.external_id = ccr_match.customer_external_id
                AND cust_channel.source = 'relbase'
            WHERE {where_clause} AND {group_field} IS NOT NULL
        """

        cursor.execute(count_query, params)
        total_items = cursor.fetchone()['count']

        cursor.close()
        conn.close()

        return {
            "status": "success",
            "data": {
                "summary": {
                    "total_revenue": float(summary['total_revenue']),
                    "total_units": int(summary['total_units']),
                    "total_orders": int(summary['total_orders']),
                    "avg_ticket": float(summary['avg_ticket']),
                    "growth_rate": 0  # Can be calculated if we have comparison period
                },
                "timeline": timeline,
                "top_items": top_items,
                "grouped_data": grouped_data,
                "pagination": {
                    "current_page": page,
                    "total_pages": (total_items + page_size - 1) // page_size,
                    "total_items": total_items,
                    "page_size": page_size
                },
                "filters": {
                    "from_date": from_date,
                    "to_date": to_date,
                    "sources": sources,
                    "channels": channels,
                    "customers": customers,
                    "categories": categories,
                    "formats": formats,
                    "group_by": group_by,
                    "top_limit": top_limit
                },
                "metadata": {
                    "data_source": "orders + order_items (real-time)",
                    "aligned_with": "Desglose Pedidos (Audit)",
                    "time_period": time_period
                }
            }
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching sales analytics: {str(e)}")
