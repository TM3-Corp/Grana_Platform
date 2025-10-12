"""
Orders API Endpoints
Handles order management and queries

Author: TM3
Date: 2025-10-03
"""
from fastapi import APIRouter, HTTPException, Query
from typing import Optional
import os
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime

router = APIRouter()


def get_db_connection():
    """Get database connection"""
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise HTTPException(status_code=500, detail="DATABASE_URL not configured")
    return psycopg2.connect(database_url)


@router.get("/")
async def get_orders(
    source: Optional[str] = Query(None, description="Filter by source (shopify, mercadolibre, etc.)"),
    status: Optional[str] = Query(None, description="Filter by order status"),
    payment_status: Optional[str] = Query(None, description="Filter by payment status"),
    from_date: Optional[str] = Query(None, description="Filter orders from this date (ISO format)"),
    to_date: Optional[str] = Query(None, description="Filter orders until this date (ISO format)"),
    limit: int = Query(50, ge=1, le=5000),  # Aumentado para permitir cargar todas las órdenes 2025
    offset: int = Query(0, ge=0)
):
    """
    Get all orders with optional filters

    Returns orders with customer and item information
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        # Build WHERE clause based on filters
        conditions = []
        params = []

        if source:
            conditions.append("o.source = %s")
            params.append(source)

        if status:
            conditions.append("o.status = %s")
            params.append(status)

        if payment_status:
            conditions.append("o.payment_status = %s")
            params.append(payment_status)

        if from_date:
            conditions.append("o.order_date >= %s")
            params.append(from_date)

        if to_date:
            conditions.append("o.order_date <= %s")
            params.append(to_date)

        where_clause = " AND ".join(conditions) if conditions else "1=1"

        # Get total count
        cursor.execute(f"""
            SELECT COUNT(*) as total
            FROM orders o
            WHERE {where_clause}
        """, params)
        total = cursor.fetchone()['total']

        # Get orders with customer info
        cursor.execute(f"""
            SELECT
                o.id, o.external_id, o.order_number, o.source,
                o.customer_id, o.channel_id,
                o.subtotal, o.tax_amount, o.shipping_cost, o.discount_amount, o.total,
                o.status, o.payment_status, o.fulfillment_status,
                o.order_date, o.customer_notes,
                o.created_at, o.updated_at,
                c.name as customer_name,
                c.email as customer_email,
                c.phone as customer_phone,
                c.city as customer_city,
                ch.name as channel_name,
                ch.code as channel_code
            FROM orders o
            LEFT JOIN customers c ON o.customer_id = c.id
            LEFT JOIN channels ch ON o.channel_id = ch.id
            WHERE {where_clause}
            ORDER BY o.order_date DESC
            LIMIT %s OFFSET %s
        """, params + [limit, offset])

        orders = cursor.fetchall()

        # Get order items for each order
        for order in orders:
            cursor.execute("""
                SELECT
                    oi.id, oi.product_id, oi.product_sku, oi.product_name,
                    oi.quantity, oi.unit_price, oi.subtotal, oi.tax_amount, oi.total,
                    p.name as product_name_from_catalog,
                    p.unit, p.category
                FROM order_items oi
                LEFT JOIN products p ON oi.product_id = p.id
                WHERE oi.order_id = %s
                ORDER BY oi.id
            """, (order['id'],))
            order['items'] = cursor.fetchall()

        cursor.close()
        conn.close()

        return {
            "status": "success",
            "total": total,
            "limit": limit,
            "offset": offset,
            "count": len(orders),
            "data": orders
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
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        # Total orders and revenue
        cursor.execute("""
            SELECT
                COUNT(*) as total_orders,
                COALESCE(SUM(total), 0) as total_revenue,
                COALESCE(AVG(total), 0) as average_order_value
            FROM orders
        """)
        totals = cursor.fetchone()

        # By source
        cursor.execute("""
            SELECT
                source,
                COUNT(*) as count,
                COALESCE(SUM(total), 0) as revenue
            FROM orders
            GROUP BY source
            ORDER BY count DESC
        """)
        by_source = cursor.fetchall()

        # By status
        cursor.execute("""
            SELECT
                status,
                COUNT(*) as count
            FROM orders
            GROUP BY status
            ORDER BY count DESC
        """)
        by_status = cursor.fetchall()

        # By payment status
        cursor.execute("""
            SELECT
                payment_status,
                COUNT(*) as count
            FROM orders
            GROUP BY payment_status
            ORDER BY count DESC
        """)
        by_payment_status = cursor.fetchall()

        # Recent orders (last 7 days)
        cursor.execute("""
            SELECT COUNT(*) as count
            FROM orders
            WHERE order_date >= CURRENT_DATE - INTERVAL '7 days'
        """)
        recent_orders = cursor.fetchone()['count']

        cursor.close()
        conn.close()

        return {
            "status": "success",
            "data": {
                "totals": {
                    "total_orders": totals['total_orders'],
                    "total_revenue": float(totals['total_revenue']),
                    "average_order_value": float(totals['average_order_value']),
                    "recent_orders_7d": recent_orders
                },
                "by_source": by_source,
                "by_status": by_status,
                "by_payment_status": by_payment_status
            }
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
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        # Build date filter
        date_filter = ""
        params = []

        if start_date:
            date_filter += " AND order_date >= %s"
            params.append(start_date)
        else:
            # Default to 2025 if no start date
            date_filter += " AND order_date >= '2025-01-01'"

        if end_date:
            date_filter += " AND order_date <= %s"
            params.append(end_date)

        # 1. Sales by period and source
        date_format = {
            'day': 'YYYY-MM-DD',
            'week': 'IYYY-IW',  # ISO week
            'month': 'YYYY-MM'
        }[group_by]

        cursor.execute(f"""
            SELECT
                TO_CHAR(order_date, %s) as period,
                source,
                COUNT(*) as order_count,
                SUM(total) as revenue,
                AVG(total) as avg_ticket
            FROM orders
            WHERE 1=1 {date_filter}
            GROUP BY period, source
            ORDER BY period, source
        """, [date_format] + params)

        sales_by_period_source = cursor.fetchall()

        # Transform to pivoted structure
        periods = {}
        for row in sales_by_period_source:
            period = row['period']
            if period not in periods:
                periods[period] = {
                    'period': period,
                    'total_revenue': 0,
                    'total_orders': 0
                }

            periods[period][f"{row['source']}_revenue"] = float(row['revenue'])
            periods[period][f"{row['source']}_orders"] = row['order_count']
            periods[period]['total_revenue'] += float(row['revenue'])
            periods[period]['total_orders'] += row['order_count']

        sales_by_period = list(periods.values())

        # 2. Source distribution (total)
        cursor.execute(f"""
            SELECT
                source,
                COUNT(*) as order_count,
                SUM(total) as revenue,
                AVG(total) as avg_ticket
            FROM orders
            WHERE 1=1 {date_filter}
            GROUP BY source
            ORDER BY revenue DESC
        """, params)

        source_distribution = cursor.fetchall()

        # 3. Top products
        cursor.execute(f"""
            SELECT
                p.name,
                p.sku,
                COUNT(DISTINCT o.id) as order_count,
                SUM(oi.quantity) as units_sold,
                SUM(oi.total) as revenue
            FROM order_items oi
            JOIN orders o ON o.id = oi.order_id
            JOIN products p ON p.id = oi.product_id
            WHERE 1=1 {date_filter.replace('order_date', 'o.order_date')}
            GROUP BY p.id, p.name, p.sku
            ORDER BY revenue DESC
            LIMIT 5
        """, params)

        top_products = cursor.fetchall()

        # 4. General KPIs
        cursor.execute(f"""
            SELECT
                COUNT(*) as total_orders,
                SUM(total) as total_revenue,
                AVG(total) as avg_ticket,
                MIN(order_date) as first_order,
                MAX(order_date) as last_order
            FROM orders
            WHERE 1=1 {date_filter}
        """, params)

        kpis = cursor.fetchone()

        # 5. Month-over-month growth (only if group_by='month')
        growth_rates = []
        if group_by == 'month' and len(sales_by_period) > 1:
            for i in range(1, len(sales_by_period)):
                prev = sales_by_period[i-1]['total_revenue']
                curr = sales_by_period[i]['total_revenue']
                growth = ((curr - prev) / prev * 100) if prev > 0 else 0
                growth_rates.append({
                    'period': sales_by_period[i]['period'],
                    'growth_rate': round(growth, 2)
                })

        cursor.close()
        conn.close()

        return {
            "status": "success",
            "data": {
                "sales_by_period": sales_by_period,
                "source_distribution": [
                    {
                        "source": row['source'],
                        "order_count": row['order_count'],
                        "revenue": float(row['revenue']),
                        "avg_ticket": float(row['avg_ticket'])
                    }
                    for row in source_distribution
                ],
                "top_products": [
                    {
                        "name": row['name'],
                        "sku": row['sku'],
                        "order_count": row['order_count'],
                        "units_sold": row['units_sold'],
                        "revenue": float(row['revenue'])
                    }
                    for row in top_products
                ],
                "kpis": {
                    "total_orders": kpis['total_orders'],
                    "total_revenue": float(kpis['total_revenue']),
                    "avg_ticket": float(kpis['avg_ticket']),
                    "first_order": kpis['first_order'].isoformat() if kpis['first_order'] else None,
                    "last_order": kpis['last_order'].isoformat() if kpis['last_order'] else None
                },
                "growth_rates": growth_rates
            }
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
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        cursor.execute("""
            SELECT
                o.id, o.external_id, o.order_number, o.source,
                o.customer_id, o.channel_id,
                o.subtotal, o.tax_amount, o.shipping_cost, o.discount_amount, o.total,
                o.status, o.payment_status, o.fulfillment_status,
                o.order_date, o.customer_notes,
                o.created_at, o.updated_at,
                c.name as customer_name,
                c.email as customer_email,
                c.phone as customer_phone,
                c.address as customer_address,
                c.city as customer_city,
                ch.name as channel_name,
                ch.code as channel_code,
                ch.type as channel_type
            FROM orders o
            LEFT JOIN customers c ON o.customer_id = c.id
            LEFT JOIN channels ch ON o.channel_id = ch.id
            WHERE o.id = %s
        """, (order_id,))

        order = cursor.fetchone()

        if not order:
            cursor.close()
            conn.close()
            raise HTTPException(status_code=404, detail=f"Order {order_id} not found")

        # Get order items
        cursor.execute("""
            SELECT
                oi.id, oi.product_id, oi.product_sku, oi.product_name,
                oi.quantity, oi.unit_price, oi.subtotal, oi.tax_amount, oi.total,
                p.name as product_name_from_catalog,
                p.unit, p.category, p.brand,
                p.units_per_display, p.displays_per_box, p.boxes_per_pallet
            FROM order_items oi
            LEFT JOIN products p ON oi.product_id = p.id
            WHERE oi.order_id = %s
            ORDER BY oi.id
        """, (order_id,))
        order['items'] = cursor.fetchall()

        cursor.close()
        conn.close()

        return {
            "status": "success",
            "data": order
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
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        cursor.execute("""
            SELECT
                o.id, o.external_id, o.order_number,
                o.total, o.status, o.payment_status,
                o.order_date,
                c.name as customer_name
            FROM orders o
            LEFT JOIN customers c ON o.customer_id = c.id
            WHERE o.source = %s
            ORDER BY o.order_date DESC
            LIMIT %s
        """, (source, limit))

        orders = cursor.fetchall()

        cursor.close()
        conn.close()

        return {
            "status": "success",
            "source": source,
            "count": len(orders),
            "data": orders
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching orders: {str(e)}")
