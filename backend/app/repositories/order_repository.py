"""
Order Repository - Data Access Layer for Orders

Handles all database queries for orders and returns Order domain models.

Author: TM3
Date: 2025-10-17
"""
from typing import List, Optional, Tuple, Dict, Any
from app.domain.order import Order, OrderItem
from app.core.database import get_db_connection_dict


class OrderRepository:
    """
    Repository for Order data access

    All SQL queries for orders are centralized here.
    Returns Order domain models with related data (customer, channel, items).
    """

    def find_by_id(self, order_id: int) -> Optional[Order]:
        """
        Find order by ID with customer, channel, and items

        Args:
            order_id: Internal order ID

        Returns:
            Order with all related data or None if not found
        """
        conn = get_db_connection_dict()
        cursor = conn.cursor()

        try:
            # Get order with customer and channel info
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

            row = cursor.fetchone()
            if not row:
                return None

            # Get order items with product info
            cursor.execute("""
                SELECT
                    oi.id, oi.order_id, oi.product_id, oi.product_sku, oi.product_name,
                    oi.quantity, oi.unit_price, oi.subtotal, oi.tax_amount, oi.total,
                    p.name as product_name_from_catalog,
                    p.unit, p.category, p.brand,
                    p.units_per_display, p.displays_per_box, p.boxes_per_pallet
                FROM order_items oi
                LEFT JOIN products p ON oi.product_id = p.id
                WHERE oi.order_id = %s
                ORDER BY oi.id
            """, (order_id,))

            items = cursor.fetchall()

            # Build Order object with items
            order_dict = dict(row)
            order_dict['items'] = [OrderItem(**item) for item in items]

            return Order(**order_dict)

        finally:
            cursor.close()
            conn.close()

    def find_all(
        self,
        source: Optional[str] = None,
        status: Optional[str] = None,
        payment_status: Optional[str] = None,
        from_date: Optional[str] = None,
        to_date: Optional[str] = None,
        search: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> Tuple[List[Order], int]:
        """
        Find orders with filters

        Args:
            source: Filter by source (shopify, mercadolibre, etc.)
            status: Filter by order status
            payment_status: Filter by payment status
            from_date: Filter orders from this date
            to_date: Filter orders until this date
            search: Search by order number, customer name, email, or city
            limit: Maximum results to return
            offset: Number of results to skip

        Returns:
            Tuple of (list of orders, total count)
        """
        conn = get_db_connection_dict()
        cursor = conn.cursor()

        try:
            # Build WHERE clause
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

            if search:
                # Search across order_number, external_id, customer name, email, and city
                search_condition = """(
                    o.external_id ILIKE %s OR
                    o.order_number ILIKE %s OR
                    c.name ILIKE %s OR
                    c.email ILIKE %s OR
                    c.city ILIKE %s
                )"""
                conditions.append(search_condition)
                search_param = f"%{search}%"
                params.extend([search_param, search_param, search_param, search_param, search_param])

            where_clause = " AND ".join(conditions) if conditions else "1=1"

            # Get total count
            cursor.execute(f"""
                SELECT COUNT(*) as total
                FROM orders o
                LEFT JOIN customers c ON o.customer_id = c.id
                WHERE {where_clause}
            """, params)
            total = cursor.fetchone()['total']

            # Get orders with customer and channel info
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

            order_rows = cursor.fetchall()

            if not order_rows:
                return [], total

            # Get ALL order items for these orders in ONE QUERY (N+1 fix!)
            order_ids = [order['id'] for order in order_rows]

            cursor.execute("""
                SELECT
                    oi.order_id,
                    oi.id, oi.product_id, oi.product_sku, oi.product_name,
                    oi.quantity, oi.unit_price, oi.subtotal, oi.tax_amount, oi.total,
                    p.name as product_name_from_catalog,
                    p.unit, p.category
                FROM order_items oi
                LEFT JOIN products p ON oi.product_id = p.id
                WHERE oi.order_id = ANY(%s)
                ORDER BY oi.order_id, oi.id
            """, (order_ids,))

            all_items = cursor.fetchall()

            # Group items by order_id
            items_by_order = {}
            for item in all_items:
                order_id = item['order_id']
                if order_id not in items_by_order:
                    items_by_order[order_id] = []

                # Keep order_id - OrderItem needs it as a field
                items_by_order[order_id].append(OrderItem(**dict(item)))

            # Build Order objects with items
            orders = []
            for row in order_rows:
                order_dict = dict(row)
                order_dict['items'] = items_by_order.get(row['id'], [])
                orders.append(Order(**order_dict))

            return orders, total

        finally:
            cursor.close()
            conn.close()

    def find_by_source(self, source: str, limit: int = 50) -> List[Order]:
        """
        Find all orders from a specific source

        Args:
            source: Source platform (shopify, mercadolibre, etc.)
            limit: Maximum results to return

        Returns:
            List of orders
        """
        conn = get_db_connection_dict()
        cursor = conn.cursor()

        try:
            cursor.execute("""
                SELECT
                    o.id, o.external_id, o.order_number, o.source,
                    o.customer_id, o.channel_id,
                    o.subtotal, o.tax_amount, o.shipping_cost, o.discount_amount, o.total,
                    o.status, o.payment_status, o.fulfillment_status,
                    o.order_date, o.customer_notes,
                    o.created_at, o.updated_at,
                    c.name as customer_name
                FROM orders o
                LEFT JOIN customers c ON o.customer_id = c.id
                WHERE o.source = %s
                ORDER BY o.order_date DESC
                LIMIT %s
            """, (source, limit))

            rows = cursor.fetchall()

            # For this endpoint, we don't include items (lightweight response)
            return [Order(**{**dict(row), 'items': []}) for row in rows]

        finally:
            cursor.close()
            conn.close()

    def get_stats(self) -> Dict[str, Any]:
        """
        Get order statistics

        Returns:
            Dict with order stats (totals, by_source, by_status, by_payment_status)
        """
        conn = get_db_connection_dict()
        cursor = conn.cursor()

        try:
            # Total orders and revenue
            # CRITICAL: Exclude cancelled and declined invoices (no revenue)
            cursor.execute("""
                SELECT
                    COUNT(*) as total_orders,
                    COALESCE(SUM(total), 0) as total_revenue,
                    COALESCE(AVG(total), 0) as average_order_value
                FROM orders
                WHERE (invoice_status IN ('accepted', 'accepted_objection') OR invoice_status IS NULL)
            """)
            totals = cursor.fetchone()

            # By source
            cursor.execute("""
                SELECT
                    source,
                    COUNT(*) as count,
                    COALESCE(SUM(total), 0) as revenue
                FROM orders
                WHERE (invoice_status IN ('accepted', 'accepted_objection') OR invoice_status IS NULL)
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

            return {
                'totals': {
                    'total_orders': totals['total_orders'],
                    'total_revenue': float(totals['total_revenue']),
                    'average_order_value': float(totals['average_order_value']),
                    'recent_orders_7d': recent_orders
                },
                'by_source': by_source,
                'by_status': by_status,
                'by_payment_status': by_payment_status
            }

        finally:
            cursor.close()
            conn.close()

    def get_analytics(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        group_by: str = 'month'
    ) -> Dict[str, Any]:
        """
        Get analytics data for charts and visualizations

        Args:
            start_date: Start date filter (YYYY-MM-DD)
            end_date: End date filter (YYYY-MM-DD)
            group_by: Group by period: 'day', 'week', or 'month'

        Returns:
            Dict with analytics data (sales_by_period, source_distribution, top_products, kpis, growth_rates)
        """
        conn = get_db_connection_dict()
        cursor = conn.cursor()

        try:
            # Build date filter
            date_filter = ""
            params = []

            if start_date:
                date_filter += " AND order_date >= %s"
                params.append(start_date)
            else:
                date_filter += " AND order_date >= '2025-01-01'"

            if end_date:
                date_filter += " AND order_date <= %s"
                params.append(end_date)

            # 1. Sales by period and source
            date_format = {
                'day': 'YYYY-MM-DD',
                'week': 'IYYY-IW',
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
                WHERE (invoice_status IN ('accepted', 'accepted_objection') OR invoice_status IS NULL)
                {date_filter}
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

            # 2. Source distribution
            cursor.execute(f"""
                SELECT
                    source,
                    COUNT(*) as order_count,
                    SUM(total) as revenue,
                    AVG(total) as avg_ticket
                FROM orders
                WHERE (invoice_status IN ('accepted', 'accepted_objection') OR invoice_status IS NULL)
                {date_filter}
                GROUP BY source
                ORDER BY revenue DESC
            """, params)

            source_distribution = cursor.fetchall()

            # 3. Top products (using product_sku with fallback to product_id)
            cursor.execute(f"""
                SELECT
                    COALESCE(p.name, oi.product_name) as name,
                    COALESCE(p.sku, oi.product_sku) as sku,
                    COUNT(DISTINCT o.id) as order_count,
                    SUM(oi.quantity) as units_sold,
                    SUM(oi.total) as revenue
                FROM order_items oi
                JOIN orders o ON o.id = oi.order_id
                LEFT JOIN products p ON p.sku = oi.product_sku
                WHERE (o.invoice_status IN ('accepted', 'accepted_objection') OR o.invoice_status IS NULL)
                {date_filter.replace('order_date', 'o.order_date')}
                GROUP BY COALESCE(p.name, oi.product_name), COALESCE(p.sku, oi.product_sku)
                ORDER BY revenue DESC
                LIMIT 10
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
                WHERE (invoice_status IN ('accepted', 'accepted_objection') OR invoice_status IS NULL)
                {date_filter}
            """, params)

            kpis = cursor.fetchone()

            # 5. Growth rates (only for month grouping)
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

            return {
                'sales_by_period': sales_by_period,
                'source_distribution': [
                    {
                        'source': row['source'],
                        'order_count': row['order_count'],
                        'revenue': float(row['revenue']),
                        'avg_ticket': float(row['avg_ticket'])
                    }
                    for row in source_distribution
                ],
                'top_products': [
                    {
                        'name': row['name'],
                        'sku': row['sku'],
                        'order_count': row['order_count'],
                        'units_sold': row['units_sold'],
                        'revenue': float(row['revenue'])
                    }
                    for row in top_products
                ],
                'kpis': {
                    'total_orders': kpis['total_orders'],
                    'total_revenue': float(kpis['total_revenue']),
                    'avg_ticket': float(kpis['avg_ticket']),
                    'first_order': kpis['first_order'].isoformat() if kpis['first_order'] else None,
                    'last_order': kpis['last_order'].isoformat() if kpis['last_order'] else None
                },
                'growth_rates': growth_rates
            }

        finally:
            cursor.close()
            conn.close()

    def count_by_filters(
        self,
        source: Optional[str] = None,
        status: Optional[str] = None,
        payment_status: Optional[str] = None
    ) -> int:
        """
        Count orders matching filters

        Args:
            source: Filter by source
            status: Filter by status
            payment_status: Filter by payment status

        Returns:
            Count of matching orders
        """
        conn = get_db_connection_dict()
        cursor = conn.cursor()

        try:
            conditions = []
            params = []

            if source:
                conditions.append("source = %s")
                params.append(source)

            if status:
                conditions.append("status = %s")
                params.append(status)

            if payment_status:
                conditions.append("payment_status = %s")
                params.append(payment_status)

            where_clause = " AND ".join(conditions) if conditions else "1=1"

            cursor.execute(f"""
                SELECT COUNT(*) as total
                FROM orders
                WHERE {where_clause}
            """, params)

            return cursor.fetchone()['total']

        finally:
            cursor.close()
            conn.close()
