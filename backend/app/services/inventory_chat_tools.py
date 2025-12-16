"""
Inventory Chat Tools for Claude AI Integration

This module provides 10 tools for querying Grana's inventory and sales data:
1. get_inventory_summary - Overall stats
2. get_product_stock - Stock by SKU/name
3. get_expiring_products - Expiration alerts
4. get_warehouse_inventory - Per-warehouse view
5. get_low_stock_products - Below min_stock
6. get_sales_by_product - Top sellers
7. get_sales_by_channel - Channel breakdown
8. compare_stock_vs_sales - Days of stock projection
9. get_sales_forecast - Explicit year filtering + forecast methodology (NEW)
10. get_chart_data - Structured chart data for visualizations (NEW)

Author: TM3
Date: 2025-11-24
Updated: 2025-11-28 - Added forecast and chart tools
"""
import json
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta

from app.core.database import get_db_connection_dict_with_retry


# ============================================================================
# TOOL 1: get_inventory_summary
# ============================================================================

def get_inventory_summary(
    warehouse: Optional[str] = None,
    category: Optional[str] = None
) -> str:
    """
    Get overall inventory statistics including total stock, products, warehouses, expiration alerts.

    Args:
        warehouse: Optional warehouse code filter (e.g., 'packner', 'amplifica_centro')
        category: Optional product category filter (GRANOLAS, BARRAS, CRACKERS, KEEPERS)

    Returns:
        JSON string with inventory summary
    """
    conn = None
    cursor = None
    try:
        conn = get_db_connection_dict_with_retry()
        cursor = conn.cursor()

        # Build WHERE conditions
        product_conditions = ["p.is_active = true"]
        warehouse_conditions = ["w.is_active = true", "w.source = 'relbase'", "w.external_id IS NOT NULL"]
        params = []

        if category:
            product_conditions.append("p.category = %s")
            params.append(category)

        if warehouse:
            warehouse_conditions.append("w.code = %s")
            params.append(warehouse)

        product_where = " AND ".join(product_conditions)
        warehouse_where = " AND ".join(warehouse_conditions)

        # Main query
        cursor.execute(f"""
            SELECT
                COUNT(DISTINCT p.id) as total_products,
                COALESCE(SUM(ws.quantity), 0) as total_stock,
                COUNT(DISTINCT CASE WHEN ws.quantity > 0 THEN p.id END) as products_with_stock,
                COUNT(DISTINCT w.id) as active_warehouses
            FROM products p
            LEFT JOIN warehouse_stock ws ON ws.product_id = p.id
            LEFT JOIN warehouses w ON w.id = ws.warehouse_id AND {warehouse_where}
            WHERE {product_where}
        """, params)

        summary = cursor.fetchone()

        # Get expiration stats
        exp_params = []
        exp_warehouse_where = "1=1"
        if warehouse:
            exp_warehouse_where = "warehouse_code = %s"
            exp_params.append(warehouse)

        cursor.execute(f"""
            SELECT
                COUNT(CASE WHEN expiration_status = 'Expired' THEN 1 END) as expired_lots,
                COALESCE(SUM(CASE WHEN expiration_status = 'Expired' THEN quantity ELSE 0 END), 0) as expired_units,
                COUNT(CASE WHEN expiration_status = 'Expiring Soon' THEN 1 END) as expiring_soon_lots,
                COALESCE(SUM(CASE WHEN expiration_status = 'Expiring Soon' THEN quantity ELSE 0 END), 0) as expiring_soon_units,
                COUNT(CASE WHEN expiration_status = 'Valid' THEN 1 END) as valid_lots,
                COALESCE(SUM(CASE WHEN expiration_status = 'Valid' THEN quantity ELSE 0 END), 0) as valid_units
            FROM warehouse_stock_by_lot
            WHERE {exp_warehouse_where}
        """, exp_params if exp_params else None)

        expiration = cursor.fetchone()

        # Get by warehouse breakdown
        cursor.execute(f"""
            SELECT
                w.name as warehouse_name,
                w.code as warehouse_code,
                COALESCE(SUM(ws.quantity), 0) as stock
            FROM warehouses w
            LEFT JOIN warehouse_stock ws ON ws.warehouse_id = w.id
            WHERE {warehouse_where}
            GROUP BY w.id, w.name, w.code
            ORDER BY stock DESC
        """, params[1:] if warehouse else [])

        by_warehouse = cursor.fetchall()

        result = {
            "total_products": summary['total_products'],
            "total_stock": int(summary['total_stock']),
            "products_with_stock": summary['products_with_stock'],
            "active_warehouses": summary['active_warehouses'],
            "expiration": {
                "expired_lots": expiration['expired_lots'],
                "expired_units": int(expiration['expired_units']),
                "expiring_soon_lots": expiration['expiring_soon_lots'],
                "expiring_soon_units": int(expiration['expiring_soon_units']),
                "valid_lots": expiration['valid_lots'],
                "valid_units": int(expiration['valid_units'])
            },
            "by_warehouse": [
                {"name": w['warehouse_name'], "code": w['warehouse_code'], "stock": int(w['stock'])}
                for w in by_warehouse
            ]
        }

        return json.dumps(result, ensure_ascii=False)

    except Exception as e:
        return json.dumps({"error": str(e)}, ensure_ascii=False)
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


# ============================================================================
# TOOL 2: get_product_stock
# ============================================================================

def get_product_stock(query: str) -> str:
    """
    Get detailed stock information for a specific product by SKU or name search.

    Args:
        query: Product SKU (e.g., 'BAMC_U04010') or partial name to search

    Returns:
        JSON string with product stock details across warehouses
    """
    conn = None
    cursor = None
    try:
        conn = get_db_connection_dict_with_retry()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT
                p.sku,
                p.name,
                p.category,
                p.subfamily,
                w.code as warehouse_code,
                w.name as warehouse_name,
                SUM(ws.quantity) as stock,
                json_agg(
                    json_build_object(
                        'lot_number', ws.lot_number,
                        'quantity', ws.quantity,
                        'expiration_date', ws.expiration_date,
                        'days_to_expiration', ws.expiration_date - CURRENT_DATE
                    )
                    ORDER BY ws.expiration_date NULLS LAST
                ) FILTER (WHERE ws.lot_number IS NOT NULL) as lots
            FROM products p
            JOIN warehouse_stock ws ON ws.product_id = p.id
            JOIN warehouses w ON w.id = ws.warehouse_id
                AND w.is_active = true
                AND w.source = 'relbase'
            WHERE p.is_active = true
              AND (p.sku ILIKE %s OR p.name ILIKE %s)
            GROUP BY p.sku, p.name, p.category, p.subfamily, w.code, w.name
            ORDER BY w.name, p.name
        """, (f"%{query}%", f"%{query}%"))

        results = cursor.fetchall()

        if not results:
            return json.dumps({"message": f"No se encontraron productos con '{query}'"}, ensure_ascii=False)

        # Group by product
        products = {}
        for row in results:
            sku = row['sku']
            if sku not in products:
                products[sku] = {
                    "sku": sku,
                    "name": row['name'],
                    "category": row['category'],
                    "subfamily": row['subfamily'],
                    "total_stock": 0,
                    "warehouses": []
                }

            stock = int(row['stock'])
            products[sku]['total_stock'] += stock
            products[sku]['warehouses'].append({
                "warehouse_code": row['warehouse_code'],
                "warehouse_name": row['warehouse_name'],
                "stock": stock,
                "lots": row['lots'] or []
            })

        return json.dumps(list(products.values()), ensure_ascii=False)

    except Exception as e:
        return json.dumps({"error": str(e)}, ensure_ascii=False)
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


# ============================================================================
# TOOL 3: get_expiring_products
# ============================================================================

def get_expiring_products(
    status: str = "all",
    warehouse: Optional[str] = None,
    days_threshold: int = 30
) -> str:
    """
    Get list of products that are expired or expiring soon.

    Args:
        status: 'expired', 'expiring_soon', or 'all' (default)
        warehouse: Optional warehouse code filter
        days_threshold: Days threshold for expiring soon (default: 30)

    Returns:
        JSON string with expiring products
    """
    conn = None
    cursor = None
    try:
        conn = get_db_connection_dict_with_retry()
        cursor = conn.cursor()

        # Build WHERE conditions
        conditions = ["quantity > 0"]
        params = []

        if status == "expired":
            conditions.append("expiration_status = 'Expired'")
        elif status == "expiring_soon":
            conditions.append("expiration_status = 'Expiring Soon'")
        else:  # all
            conditions.append("expiration_status IN ('Expired', 'Expiring Soon')")

        if warehouse:
            conditions.append("warehouse_code = %s")
            params.append(warehouse)

        where_clause = " AND ".join(conditions)

        cursor.execute(f"""
            SELECT
                sku,
                product_name,
                category,
                warehouse_code,
                warehouse_name,
                lot_number,
                quantity,
                expiration_date,
                days_to_expiration,
                expiration_status
            FROM warehouse_stock_by_lot
            WHERE {where_clause}
            ORDER BY expiration_date ASC NULLS LAST, quantity DESC
            LIMIT 50
        """, params if params else None)

        results = cursor.fetchall()

        if not results:
            return json.dumps({"message": "No hay productos vencidos o por vencer"}, ensure_ascii=False)

        # Format results
        items = []
        for row in results:
            items.append({
                "sku": row['sku'],
                "name": row['product_name'],
                "category": row['category'],
                "warehouse": row['warehouse_name'],
                "lot": row['lot_number'],
                "quantity": int(row['quantity']),
                "expiration_date": row['expiration_date'].isoformat() if row['expiration_date'] else None,
                "days_to_expiration": row['days_to_expiration'],
                "status": row['expiration_status']
            })

        return json.dumps({
            "total_items": len(items),
            "items": items
        }, ensure_ascii=False)

    except Exception as e:
        return json.dumps({"error": str(e)}, ensure_ascii=False)
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


# ============================================================================
# TOOL 4: get_warehouse_inventory
# ============================================================================

def get_warehouse_inventory(
    warehouse_code: str,
    category: Optional[str] = None,
    only_with_stock: bool = True
) -> str:
    """
    Get complete inventory for a specific warehouse with product breakdown.

    Args:
        warehouse_code: Warehouse code (e.g., 'packner', 'amplifica_centro')
        category: Optional product category filter
        only_with_stock: Only show products with stock > 0 (default: True)

    Returns:
        JSON string with warehouse inventory
    """
    conn = None
    cursor = None
    try:
        conn = get_db_connection_dict_with_retry()
        cursor = conn.cursor()

        # Verify warehouse exists
        cursor.execute("""
            SELECT code, name FROM warehouses
            WHERE code = %s AND is_active = true AND source = 'relbase'
        """, (warehouse_code,))

        warehouse = cursor.fetchone()
        if not warehouse:
            return json.dumps({"error": f"Bodega '{warehouse_code}' no encontrada"}, ensure_ascii=False)

        # Build WHERE conditions
        conditions = ["warehouse_code = %s"]
        params = [warehouse_code]

        if category:
            conditions.append("category = %s")
            params.append(category)

        if only_with_stock:
            conditions.append("quantity > 0")

        where_clause = " AND ".join(conditions)

        cursor.execute(f"""
            SELECT
                sku,
                product_name as name,
                category,
                SUM(quantity) as stock,
                COUNT(lot_number) as lot_count
            FROM warehouse_stock_by_lot
            WHERE {where_clause}
            GROUP BY sku, product_name, category
            ORDER BY category, product_name
        """, params)

        products = cursor.fetchall()

        # Get summary
        cursor.execute("""
            SELECT
                COUNT(DISTINCT sku) as total_products,
                COALESCE(SUM(quantity), 0) as total_stock
            FROM warehouse_stock_by_lot
            WHERE warehouse_code = %s
        """, (warehouse_code,))

        summary = cursor.fetchone()

        result = {
            "warehouse": {
                "code": warehouse['code'],
                "name": warehouse['name']
            },
            "summary": {
                "total_products": summary['total_products'],
                "total_stock": int(summary['total_stock'])
            },
            "products": [
                {
                    "sku": p['sku'],
                    "name": p['name'],
                    "category": p['category'],
                    "stock": int(p['stock']),
                    "lots": p['lot_count']
                }
                for p in products
            ]
        }

        return json.dumps(result, ensure_ascii=False)

    except Exception as e:
        return json.dumps({"error": str(e)}, ensure_ascii=False)
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


# ============================================================================
# TOOL 5: get_low_stock_products
# ============================================================================

def get_low_stock_products(
    threshold: Optional[int] = None,
    category: Optional[str] = None
) -> str:
    """
    Get products with low or zero stock that may need restocking.

    Args:
        threshold: Optional minimum stock threshold (default: uses min_stock from products table)
        category: Optional product category filter

    Returns:
        JSON string with low stock products
    """
    conn = None
    cursor = None
    try:
        conn = get_db_connection_dict_with_retry()
        cursor = conn.cursor()

        # Build WHERE conditions
        conditions = ["p.is_active = true"]
        params = []

        if category:
            conditions.append("p.category = %s")
            params.append(category)

        where_clause = " AND ".join(conditions)

        # Use threshold or min_stock
        if threshold:
            having_clause = f"COALESCE(SUM(ws.quantity), 0) < {int(threshold)}"
        else:
            having_clause = "COALESCE(SUM(ws.quantity), 0) < COALESCE(p.min_stock, 10)"

        cursor.execute(f"""
            SELECT
                p.sku,
                p.name,
                p.category,
                COALESCE(p.min_stock, 10) as min_stock,
                COALESCE(SUM(ws.quantity), 0) as current_stock,
                COALESCE(p.min_stock, 10) - COALESCE(SUM(ws.quantity), 0) as units_needed,
                CASE
                    WHEN COALESCE(SUM(ws.quantity), 0) = 0 THEN 'SIN_STOCK'
                    WHEN COALESCE(SUM(ws.quantity), 0) < COALESCE(p.min_stock, 10) THEN 'CRITICO'
                    WHEN COALESCE(SUM(ws.quantity), 0) < COALESCE(p.min_stock, 10) * 2 THEN 'ADVERTENCIA'
                    ELSE 'OK'
                END as status
            FROM products p
            LEFT JOIN warehouse_stock ws ON ws.product_id = p.id
            LEFT JOIN warehouses w ON w.id = ws.warehouse_id AND w.is_active = true
            WHERE {where_clause}
            GROUP BY p.id, p.sku, p.name, p.category, p.min_stock
            HAVING {having_clause}
            ORDER BY
                CASE WHEN COALESCE(SUM(ws.quantity), 0) = 0 THEN 1 ELSE 2 END,
                (COALESCE(p.min_stock, 10) - COALESCE(SUM(ws.quantity), 0)) DESC
            LIMIT 50
        """, params if params else None)

        results = cursor.fetchall()

        if not results:
            return json.dumps({"message": "No hay productos con stock bajo"}, ensure_ascii=False)

        items = []
        for row in results:
            items.append({
                "sku": row['sku'],
                "name": row['name'],
                "category": row['category'],
                "min_stock": int(row['min_stock']),
                "current_stock": int(row['current_stock']),
                "units_needed": int(row['units_needed']),
                "status": row['status']
            })

        # Count by status
        sin_stock = sum(1 for i in items if i['status'] == 'SIN_STOCK')
        critico = sum(1 for i in items if i['status'] == 'CRITICO')

        return json.dumps({
            "summary": {
                "sin_stock": sin_stock,
                "critico": critico,
                "total": len(items)
            },
            "products": items
        }, ensure_ascii=False)

    except Exception as e:
        return json.dumps({"error": str(e)}, ensure_ascii=False)
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


# ============================================================================
# TOOL 6: get_sales_by_product
# ============================================================================

def get_sales_by_product(
    query: Optional[str] = None,
    category: Optional[str] = None,
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
    top_limit: int = 10
) -> str:
    """
    Get sales analytics for products including revenue, units sold, and trends.

    Args:
        query: Optional product SKU or name to filter
        category: Optional product category filter
        from_date: Start date (YYYY-MM-DD format, default: 30 days ago)
        to_date: End date (YYYY-MM-DD format, default: today)
        top_limit: Number of top products to return (default: 10)

    Returns:
        JSON string with sales by product
    """
    conn = None
    cursor = None
    try:
        conn = get_db_connection_dict_with_retry()
        cursor = conn.cursor()

        # Build WHERE conditions
        # IMPORTANT: Only include accepted invoices to match Desglose Pedidos
        conditions = [
            "o.source = 'relbase'",
            "o.invoice_status IN ('accepted', 'accepted_objection')"
        ]
        params = []

        # Date range
        if from_date:
            conditions.append("o.order_date >= %s")
            params.append(from_date)
        else:
            conditions.append("o.order_date >= CURRENT_DATE - INTERVAL '30 days'")

        if to_date:
            conditions.append("o.order_date <= %s")
            params.append(to_date)

        if query:
            conditions.append("(oi.product_sku ILIKE %s OR oi.product_name ILIKE %s)")
            params.extend([f"%{query}%", f"%{query}%"])

        if category:
            conditions.append("p.category = %s")
            params.append(category)

        where_clause = " AND ".join(conditions)

        cursor.execute(f"""
            SELECT
                oi.product_sku as sku,
                oi.product_name as name,
                p.category,
                COALESCE(SUM(oi.subtotal), 0) as total_revenue,
                COALESCE(SUM(oi.quantity), 0) as total_units,
                COUNT(DISTINCT o.id) as total_orders
            FROM orders o
            JOIN order_items oi ON oi.order_id = o.id
            LEFT JOIN products p ON p.sku = oi.product_sku
            WHERE {where_clause}
            GROUP BY oi.product_sku, oi.product_name, p.category
            ORDER BY total_revenue DESC
            LIMIT %s
        """, params + [top_limit])

        results = cursor.fetchall()

        if not results:
            return json.dumps({"message": "No se encontraron ventas en el periodo"}, ensure_ascii=False)

        # Calculate totals
        total_revenue = sum(float(r['total_revenue']) for r in results)
        total_units = sum(int(r['total_units']) for r in results)

        items = []
        for row in results:
            revenue = float(row['total_revenue'])
            items.append({
                "sku": row['sku'],
                "name": row['name'],
                "category": row['category'],
                "revenue": int(revenue),
                "units": int(row['total_units']),
                "orders": row['total_orders'],
                "percentage": round((revenue / total_revenue * 100) if total_revenue > 0 else 0, 1)
            })

        return json.dumps({
            "period": {
                "from": from_date or "ultimos 30 dias",
                "to": to_date or "hoy"
            },
            "totals": {
                "revenue": int(total_revenue),
                "units": total_units,
                "products": len(items)
            },
            "top_products": items
        }, ensure_ascii=False)

    except Exception as e:
        return json.dumps({"error": str(e)}, ensure_ascii=False)
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


# ============================================================================
# TOOL 7: get_sales_by_channel
# ============================================================================

def get_sales_by_channel(
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
    category: Optional[str] = None
) -> str:
    """
    Get sales breakdown by sales channel (ECOMMERCE, RETAIL, CORPORATIVO, DISTRIBUIDOR).

    Args:
        from_date: Start date (YYYY-MM-DD format, default: 30 days ago)
        to_date: End date (YYYY-MM-DD format, default: today)
        category: Optional product category filter

    Returns:
        JSON string with sales by channel
    """
    conn = None
    cursor = None
    try:
        conn = get_db_connection_dict_with_retry()
        cursor = conn.cursor()

        # Build WHERE conditions
        # IMPORTANT: Only include accepted invoices to match Desglose Pedidos
        conditions = [
            "o.source = 'relbase'",
            "o.invoice_status IN ('accepted', 'accepted_objection')"
        ]
        params = []

        # Date range
        if from_date:
            conditions.append("o.order_date >= %s")
            params.append(from_date)
        else:
            conditions.append("o.order_date >= CURRENT_DATE - INTERVAL '30 days'")

        if to_date:
            conditions.append("o.order_date <= %s")
            params.append(to_date)

        if category:
            conditions.append("p.category = %s")
            params.append(category)

        where_clause = " AND ".join(conditions)

        cursor.execute(f"""
            SELECT
                COALESCE(ch.name, 'SIN CANAL') as channel_name,
                COALESCE(SUM(oi.subtotal), 0) as total_revenue,
                COALESCE(SUM(oi.quantity), 0) as total_units,
                COUNT(DISTINCT o.id) as total_orders,
                COUNT(DISTINCT o.customer_id) as unique_customers
            FROM orders o
            JOIN order_items oi ON oi.order_id = o.id
            LEFT JOIN channels ch ON ch.id = o.channel_id
            LEFT JOIN products p ON p.sku = oi.product_sku
            WHERE {where_clause}
            GROUP BY ch.name
            ORDER BY total_revenue DESC
        """, params if params else None)

        results = cursor.fetchall()

        if not results:
            return json.dumps({"message": "No se encontraron ventas en el periodo"}, ensure_ascii=False)

        # Calculate totals
        total_revenue = sum(float(r['total_revenue']) for r in results)
        total_units = sum(int(r['total_units']) for r in results)
        total_orders = sum(r['total_orders'] for r in results)

        channels = []
        for row in results:
            revenue = float(row['total_revenue'])
            channels.append({
                "channel": row['channel_name'],
                "revenue": int(revenue),
                "units": int(row['total_units']),
                "orders": row['total_orders'],
                "customers": row['unique_customers'],
                "percentage": round((revenue / total_revenue * 100) if total_revenue > 0 else 0, 1)
            })

        return json.dumps({
            "period": {
                "from": from_date or "ultimos 30 dias",
                "to": to_date or "hoy"
            },
            "totals": {
                "revenue": int(total_revenue),
                "units": total_units,
                "orders": total_orders
            },
            "channels": channels
        }, ensure_ascii=False)

    except Exception as e:
        return json.dumps({"error": str(e)}, ensure_ascii=False)
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


# ============================================================================
# TOOL 8: compare_stock_vs_sales
# ============================================================================

def compare_stock_vs_sales(
    days_lookback: int = 30,
    category: Optional[str] = None
) -> str:
    """
    Compare current inventory levels against recent sales velocity to identify potential stockouts.

    Args:
        days_lookback: Days of sales history to analyze (default: 30)
        category: Optional product category filter

    Returns:
        JSON string with stock vs sales comparison
    """
    conn = None
    cursor = None
    try:
        conn = get_db_connection_dict_with_retry()
        cursor = conn.cursor()

        # Build category filter
        category_filter = ""
        params = [days_lookback, days_lookback]
        if category:
            category_filter = "AND cs.category = %s"
            params.append(category)

        # IMPORTANT: Only include accepted invoices to match Desglose Pedidos
        cursor.execute(f"""
            WITH sales_velocity AS (
                SELECT
                    oi.product_sku as sku,
                    SUM(oi.quantity) as units_sold_period,
                    ROUND(SUM(oi.quantity)::numeric / %s, 2) as daily_velocity
                FROM orders o
                JOIN order_items oi ON oi.order_id = o.id
                WHERE o.source = 'relbase'
                  AND o.invoice_status IN ('accepted', 'accepted_objection')
                  AND o.order_date >= CURRENT_DATE - INTERVAL '%s days'
                GROUP BY oi.product_sku
            ),
            current_stock AS (
                SELECT
                    p.sku,
                    p.name,
                    p.category,
                    COALESCE(SUM(ws.quantity), 0) as stock
                FROM products p
                LEFT JOIN warehouse_stock ws ON ws.product_id = p.id
                LEFT JOIN warehouses w ON w.id = ws.warehouse_id
                    AND w.is_active = true
                    AND w.source = 'relbase'
                WHERE p.is_active = true
                GROUP BY p.sku, p.name, p.category
            )
            SELECT
                cs.sku,
                cs.name,
                cs.category,
                cs.stock as current_stock,
                COALESCE(sv.units_sold_period, 0) as units_sold,
                COALESCE(sv.daily_velocity, 0) as daily_sales_rate,
                CASE
                    WHEN COALESCE(sv.daily_velocity, 0) = 0 THEN NULL
                    ELSE ROUND(cs.stock / sv.daily_velocity, 0)
                END as days_of_stock,
                CASE
                    WHEN cs.stock = 0 THEN 'SIN_STOCK'
                    WHEN COALESCE(sv.daily_velocity, 0) = 0 THEN 'SIN_VENTAS'
                    WHEN cs.stock / sv.daily_velocity < 7 THEN 'CRITICO'
                    WHEN cs.stock / sv.daily_velocity < 30 THEN 'ADVERTENCIA'
                    ELSE 'SALUDABLE'
                END as health_status
            FROM current_stock cs
            LEFT JOIN sales_velocity sv ON sv.sku = cs.sku
            WHERE (cs.stock > 0 OR COALESCE(sv.units_sold_period, 0) > 0)
              {category_filter}
            ORDER BY
                CASE
                    WHEN cs.stock = 0 THEN 1
                    WHEN COALESCE(sv.daily_velocity, 0) > 0 AND cs.stock / sv.daily_velocity < 7 THEN 2
                    WHEN COALESCE(sv.daily_velocity, 0) > 0 AND cs.stock / sv.daily_velocity < 30 THEN 3
                    ELSE 4
                END,
                COALESCE(sv.units_sold_period, 0) DESC
            LIMIT 50
        """, params)

        results = cursor.fetchall()

        if not results:
            return json.dumps({"message": "No hay datos de stock o ventas"}, ensure_ascii=False)

        items = []
        for row in results:
            items.append({
                "sku": row['sku'],
                "name": row['name'],
                "category": row['category'],
                "current_stock": int(row['current_stock']),
                "units_sold_30d": int(row['units_sold']),
                "daily_sales_rate": float(row['daily_sales_rate']),
                "days_of_stock": int(row['days_of_stock']) if row['days_of_stock'] else None,
                "status": row['health_status']
            })

        # Count by status
        sin_stock = sum(1 for i in items if i['status'] == 'SIN_STOCK')
        critico = sum(1 for i in items if i['status'] == 'CRITICO')
        advertencia = sum(1 for i in items if i['status'] == 'ADVERTENCIA')
        saludable = sum(1 for i in items if i['status'] == 'SALUDABLE')

        return json.dumps({
            "analysis_period": f"ultimos {days_lookback} dias",
            "summary": {
                "sin_stock": sin_stock,
                "critico": critico,
                "advertencia": advertencia,
                "saludable": saludable,
                "total": len(items)
            },
            "products": items
        }, ensure_ascii=False)

    except Exception as e:
        return json.dumps({"error": str(e)}, ensure_ascii=False)
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


# ============================================================================
# TOOL 9: get_sales_forecast
# ============================================================================

def get_sales_forecast(
    year: int,
    group_by: str = "month",
    channel: Optional[str] = None,
    category: Optional[str] = None,
    forecast_months: int = 12
) -> str:
    """
    Get historical sales data for a specific year with optional sales forecast.

    EXPLICIT YEAR FILTERING: Uses EXTRACT(YEAR FROM order_date) = year
    to guarantee only data from the specified year is included.

    INCOMPLETE MONTH FILTERING: Automatically excludes the current month
    and any future months when analyzing the current year, since they have
    incomplete data that would skew the forecast negatively.

    METHODOLOGY:
    - Historical Analysis: Monthly revenue/units aggregation (complete months only)
    - Trend Detection: Linear regression on monthly data
    - Seasonality: Monthly index based on historical patterns
    - Forecast: (Base + Trend) * Seasonality Factor

    Args:
        year: The year to analyze (e.g., 2025). REQUIRED.
        group_by: Grouping period - 'month' (default) or 'quarter'
        channel: Optional channel filter (ECOMMERCE, RETAIL, CORPORATIVO, DISTRIBUIDOR)
        category: Optional product category filter
        forecast_months: Number of months to forecast (default: 12 for next year)

    Returns:
        JSON with historical data, trend analysis, and forecasts
    """
    conn = None
    cursor = None
    try:
        conn = get_db_connection_dict_with_retry()
        cursor = conn.cursor()

        # Determine which months are complete
        # Current month and future months have incomplete data
        from datetime import datetime
        today = datetime.now()
        current_year = today.year
        current_month = today.month

        # Calculate last complete month for the requested year
        if year < current_year:
            # Past years: all 12 months are complete
            last_complete_month = 12
            excluded_months = []
        elif year == current_year:
            # Current year: exclude current month and future (they have incomplete data)
            last_complete_month = current_month - 1
            excluded_months = list(range(current_month, 13))
        else:
            # Future year: no complete months yet
            last_complete_month = 0
            excluded_months = list(range(1, 13))

        # Build WHERE conditions with EXPLICIT year filter
        conditions = [
            "o.source = 'relbase'",
            "o.invoice_status IN ('accepted', 'accepted_objection')",
            "EXTRACT(YEAR FROM o.order_date) = %s"  # EXPLICIT year filtering
        ]
        params = [year]

        # Add filter to exclude incomplete months (for current year)
        if year == current_year and last_complete_month < 12:
            conditions.append("EXTRACT(MONTH FROM o.order_date) <= %s")
            params.append(last_complete_month)

        if channel:
            conditions.append("ch.name = %s")
            params.append(channel.upper())

        if category:
            conditions.append("p.category = %s")
            params.append(category.upper())

        where_clause = " AND ".join(conditions)

        # Choose grouping
        if group_by == "quarter":
            period_expr = "EXTRACT(QUARTER FROM o.order_date)"
            period_format = "'Q' || EXTRACT(QUARTER FROM o.order_date)::int"
        else:
            period_expr = "EXTRACT(MONTH FROM o.order_date)"
            period_format = "TO_CHAR(o.order_date, 'YYYY-MM')"

        # Get monthly/quarterly aggregated data
        cursor.execute(f"""
            SELECT
                {period_format} as period,
                {period_expr} as period_num,
                COUNT(DISTINCT o.id) as orders,
                COALESCE(SUM(oi.quantity), 0) as units,
                COALESCE(SUM(oi.subtotal), 0) as revenue
            FROM orders o
            JOIN order_items oi ON oi.order_id = o.id
            LEFT JOIN products p ON p.sku = oi.product_sku
            LEFT JOIN channels ch ON ch.id = o.channel_id
            WHERE {where_clause}
            GROUP BY {period_expr}, {period_format}
            ORDER BY {period_expr}
        """, params)

        historical = cursor.fetchall()

        if not historical:
            return json.dumps({
                "error": f"No data found for year {year}",
                "filters_applied": {
                    "year": year,
                    "channel": channel,
                    "category": category
                }
            }, ensure_ascii=False)

        # Convert to list of dicts
        periods = []
        revenues = []
        units_list = []
        for row in historical:
            periods.append({
                "period": row['period'],
                "period_num": int(row['period_num']),
                "orders": row['orders'],
                "units": int(row['units']),
                "revenue": int(row['revenue'])
            })
            revenues.append(float(row['revenue']))
            units_list.append(float(row['units']))

        # Calculate statistics
        total_revenue = sum(revenues)
        total_units = sum(units_list)
        avg_revenue = total_revenue / len(revenues) if revenues else 0
        avg_units = total_units / len(units_list) if units_list else 0

        # Simple linear trend calculation (slope)
        n = len(revenues)
        if n >= 2:
            x_mean = (n + 1) / 2
            y_mean = sum(revenues) / n
            numerator = sum((i + 1 - x_mean) * (revenues[i] - y_mean) for i in range(n))
            denominator = sum((i + 1 - x_mean) ** 2 for i in range(n))
            slope = numerator / denominator if denominator != 0 else 0
            trend_direction = "creciente" if slope > 0 else "decreciente" if slope < 0 else "estable"
            monthly_change_pct = (slope / avg_revenue * 100) if avg_revenue > 0 else 0
        else:
            slope = 0
            trend_direction = "insuficientes datos"
            monthly_change_pct = 0

        # Calculate seasonality indices (each period's deviation from average)
        seasonality = {}
        for p in periods:
            idx = p['revenue'] / avg_revenue if avg_revenue > 0 else 1.0
            seasonality[p['period_num']] = round(idx, 2)

        # Generate forecast for next year
        forecast = []
        if forecast_months > 0:
            base_forecast = avg_revenue
            for m in range(1, min(forecast_months + 1, 13)):
                # Forecast = (base + trend * month_offset) * seasonality
                month_offset = n + m
                trend_component = slope * month_offset
                seasonality_factor = seasonality.get(m, 1.0)
                projected = (base_forecast + trend_component) * seasonality_factor

                forecast.append({
                    "month": m,
                    "month_name": ["", "Ene", "Feb", "Mar", "Abr", "May", "Jun",
                                   "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"][m],
                    "projected_revenue": max(0, int(projected)),
                    "seasonality_factor": seasonality_factor,
                    "confidence": "medium" if n >= 6 else "low"
                })

        # Total projected for next year
        total_forecast = sum(f['projected_revenue'] for f in forecast) if forecast else 0
        growth_vs_current = ((total_forecast - total_revenue) / total_revenue * 100) if total_revenue > 0 else 0

        # Map month numbers to names for excluded months info
        month_names = ["", "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
                       "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
        excluded_month_names = [month_names[m] for m in excluded_months if m <= 12]

        # Build the forecast_chart object that matches ForecastData interface exactly
        # This is what the frontend ChatChart component expects for rendering
        forecast_chart = {
            "year": year,
            "historical_data": {
                "monthly": [
                    {
                        "month": p['period_num'],
                        "month_name": month_names[p['period_num']] if p['period_num'] <= 12 else "",
                        "revenue": p['revenue'],
                        "units": p['units'],
                        "orders": p['orders']
                    }
                    for p in periods
                ],
                "summary": {
                    "total_revenue": int(total_revenue),
                    "total_units": int(total_units),
                    "total_orders": sum(p['orders'] for p in periods),
                    "months_with_data": len(periods)
                }
            },
            "forecast": {
                "methodology": "Linear Trend + Seasonality Adjustment",
                "base_monthly_revenue": int(avg_revenue),
                "trend_per_month": int(slope),
                "projected_year": year + 1,
                "monthly_forecast": [
                    {
                        "month": f['month'],
                        "month_name": month_names[f['month']] if f['month'] <= 12 else "",
                        "projected_revenue": f['projected_revenue'],
                        "seasonality_factor": f['seasonality_factor']
                    }
                    for f in forecast
                ],
                "summary": {
                    "projected_annual_revenue": int(total_forecast),
                    "average_monthly": int(total_forecast / 12) if total_forecast > 0 else 0,
                    "growth_vs_base": round(growth_vs_current, 1),
                    "confidence_level": "medium" if len(periods) >= 6 else "low"
                }
            }
        }

        return json.dumps({
            "query_info": {
                "year": year,
                "filters": {
                    "channel": channel,
                    "category": category
                },
                "date_range": {
                    "from": f"{year}-01-01",
                    "to": f"{year}-{last_complete_month:02d}-31" if last_complete_month > 0 else f"{year}-01-01",
                    "explicit_filter": f"EXTRACT(YEAR FROM order_date) = {year}",
                    "complete_months_only": True if excluded_months else False,
                    "last_complete_month": last_complete_month,
                    "excluded_months": excluded_month_names,
                    "exclusion_reason": f"Meses {', '.join(excluded_month_names)} excluidos por tener datos incompletos (mes actual o futuro)" if excluded_months else None
                }
            },
            "historical_data": {
                "periods": periods,
                "totals": {
                    "revenue": int(total_revenue),
                    "units": int(total_units),
                    "periods_count": len(periods)
                }
            },
            "analysis": {
                "trend": {
                    "direction": trend_direction,
                    "slope_per_month": int(slope),
                    "monthly_change_percent": round(monthly_change_pct, 1)
                },
                "seasonality": seasonality,
                "average_monthly_revenue": int(avg_revenue),
                "average_monthly_units": int(avg_units)
            },
            "forecast": {
                "methodology": "Linear Trend + Seasonality Adjustment (Complete Months Only)",
                "description": f"Proyección basada en {len(periods)} meses completos (Ene-{month_names[last_complete_month] if last_complete_month > 0 else 'N/A'}). Meses incompletos excluidos para evitar sesgo negativo.",
                "months_used_for_calculation": len(periods),
                "next_year_projection": forecast,
                "total_projected": int(total_forecast),
                "growth_vs_current_year": round(growth_vs_current, 1)
            },
            # This is the chart-ready format that the frontend can render directly
            "forecast_chart": forecast_chart
        }, ensure_ascii=False)

    except Exception as e:
        return json.dumps({"error": str(e)}, ensure_ascii=False)
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


# ============================================================================
# TOOL 10: get_chart_data
# ============================================================================

def get_chart_data(
    chart_type: str,
    metric: str = "revenue",
    year: Optional[int] = None,
    group_by: str = "month",
    channel: Optional[str] = None,
    category: Optional[str] = None,
    top_n: int = 10
) -> str:
    """
    Generate structured chart data for visualizations in the frontend.

    Supports multiple chart types optimized for different analyses:
    - line: Time series (monthly/quarterly trends)
    - bar: Comparisons (by channel, category, product)
    - pie: Distribution (market share, composition)
    - stacked_bar: Multi-dimensional comparison

    Args:
        chart_type: 'line', 'bar', 'pie', or 'stacked_bar'
        metric: 'revenue', 'units', or 'orders'
        year: Optional year filter (uses explicit EXTRACT)
        group_by: 'month', 'quarter', 'channel', 'category', or 'product'
        channel: Optional channel filter
        category: Optional category filter
        top_n: For product charts, limit to top N (default: 10)

    Returns:
        JSON with chart-ready data structure for frontend rendering
    """
    conn = None
    cursor = None
    try:
        conn = get_db_connection_dict_with_retry()
        cursor = conn.cursor()

        # Build base conditions
        conditions = [
            "o.source = 'relbase'",
            "o.invoice_status IN ('accepted', 'accepted_objection')"
        ]
        params = []

        # EXPLICIT year filter if provided
        year_filter_sql = None
        if year:
            conditions.append("EXTRACT(YEAR FROM o.order_date) = %s")
            params.append(year)
            year_filter_sql = f"EXTRACT(YEAR FROM order_date) = {year}"

        if channel:
            conditions.append("ch.name = %s")
            params.append(channel.upper())

        if category:
            conditions.append("p.category = %s")
            params.append(category.upper())

        where_clause = " AND ".join(conditions)

        # Select metric column
        metric_expr = {
            "revenue": "COALESCE(SUM(oi.subtotal), 0)",
            "units": "COALESCE(SUM(oi.quantity), 0)",
            "orders": "COUNT(DISTINCT o.id)"
        }.get(metric, "COALESCE(SUM(oi.subtotal), 0)")

        metric_label = {
            "revenue": "Ingresos ($)",
            "units": "Unidades",
            "orders": "Órdenes"
        }.get(metric, "Valor")

        # Build query based on group_by
        if group_by in ("month", "quarter"):
            if group_by == "quarter":
                group_expr = "EXTRACT(QUARTER FROM o.order_date)"
                label_expr = "'Q' || EXTRACT(QUARTER FROM o.order_date)::int"
            else:
                group_expr = "EXTRACT(MONTH FROM o.order_date)"
                label_expr = "TO_CHAR(o.order_date, 'YYYY-MM')"

            cursor.execute(f"""
                SELECT
                    {label_expr} as label,
                    {group_expr} as sort_order,
                    {metric_expr} as value
                FROM orders o
                JOIN order_items oi ON oi.order_id = o.id
                LEFT JOIN products p ON p.sku = oi.product_sku
                LEFT JOIN channels ch ON ch.id = o.channel_id
                WHERE {where_clause}
                GROUP BY {group_expr}, {label_expr}
                ORDER BY {group_expr}
            """, params)

        elif group_by == "channel":
            cursor.execute(f"""
                SELECT
                    COALESCE(ch.name, 'SIN CANAL') as label,
                    {metric_expr} as value
                FROM orders o
                JOIN order_items oi ON oi.order_id = o.id
                LEFT JOIN products p ON p.sku = oi.product_sku
                LEFT JOIN channels ch ON ch.id = o.channel_id
                WHERE {where_clause}
                GROUP BY ch.name
                ORDER BY value DESC
            """, params)

        elif group_by == "category":
            cursor.execute(f"""
                SELECT
                    COALESCE(p.category, 'SIN CATEGORIA') as label,
                    {metric_expr} as value
                FROM orders o
                JOIN order_items oi ON oi.order_id = o.id
                LEFT JOIN products p ON p.sku = oi.product_sku
                LEFT JOIN channels ch ON ch.id = o.channel_id
                WHERE {where_clause}
                GROUP BY p.category
                ORDER BY value DESC
            """, params)

        elif group_by == "product":
            params.append(top_n)
            cursor.execute(f"""
                SELECT
                    oi.product_sku || ' - ' || SUBSTRING(oi.product_name, 1, 30) as label,
                    {metric_expr} as value
                FROM orders o
                JOIN order_items oi ON oi.order_id = o.id
                LEFT JOIN products p ON p.sku = oi.product_sku
                LEFT JOIN channels ch ON ch.id = o.channel_id
                WHERE {where_clause}
                GROUP BY oi.product_sku, oi.product_name
                ORDER BY value DESC
                LIMIT %s
            """, params)
        else:
            return json.dumps({"error": f"Invalid group_by: {group_by}"}, ensure_ascii=False)

        results = cursor.fetchall()

        if not results:
            return json.dumps({
                "error": "No data found",
                "filters": {"year": year, "channel": channel, "category": category}
            }, ensure_ascii=False)

        # Build chart data structure
        labels = [row['label'] for row in results]
        values = [int(row['value']) for row in results]
        total = sum(values)

        # For pie charts, also calculate percentages
        percentages = [round(v / total * 100, 1) if total > 0 else 0 for v in values]

        # Determine suggested chart type based on data
        suggested_type = chart_type
        if chart_type == "auto":
            if group_by in ("month", "quarter"):
                suggested_type = "line"
            elif group_by in ("channel", "category"):
                suggested_type = "bar" if len(labels) > 5 else "pie"
            else:
                suggested_type = "bar"

        # Color palette for charts
        colors = [
            "#4F46E5",  # Indigo
            "#10B981",  # Emerald
            "#F59E0B",  # Amber
            "#EF4444",  # Red
            "#8B5CF6",  # Violet
            "#06B6D4",  # Cyan
            "#EC4899",  # Pink
            "#84CC16",  # Lime
            "#F97316",  # Orange
            "#6366F1",  # Indigo-lighter
        ]

        return json.dumps({
            "chart_type": suggested_type,
            "title": f"{metric_label} por {group_by.replace('_', ' ').title()}",
            "subtitle": f"Año {year}" if year else "Todos los períodos",
            "query_info": {
                "year": year,
                "year_filter_sql": year_filter_sql,
                "group_by": group_by,
                "metric": metric,
                "filters": {
                    "channel": channel,
                    "category": category
                }
            },
            "data": {
                "labels": labels,
                "datasets": [
                    {
                        "label": metric_label,
                        "data": values,
                        "backgroundColor": colors[:len(values)],
                        "borderColor": colors[:len(values)]
                    }
                ]
            },
            "summary": {
                "total": total,
                "count": len(values),
                "average": int(total / len(values)) if values else 0,
                "max": max(values) if values else 0,
                "min": min(values) if values else 0,
                "percentages": dict(zip(labels, percentages))
            },
            "render_hint": {
                "type": suggested_type,
                "show_legend": len(labels) <= 10,
                "show_data_labels": chart_type == "pie" or len(labels) <= 5,
                "x_axis_label": group_by.replace('_', ' ').title() if suggested_type != "pie" else None,
                "y_axis_label": metric_label if suggested_type != "pie" else None
            }
        }, ensure_ascii=False)

    except Exception as e:
        return json.dumps({"error": str(e)}, ensure_ascii=False)
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


# ============================================================================
# TOOL REGISTRY
# ============================================================================

TOOL_FUNCTIONS = {
    "get_inventory_summary": get_inventory_summary,
    "get_product_stock": get_product_stock,
    "get_expiring_products": get_expiring_products,
    "get_warehouse_inventory": get_warehouse_inventory,
    "get_low_stock_products": get_low_stock_products,
    "get_sales_by_product": get_sales_by_product,
    "get_sales_by_channel": get_sales_by_channel,
    "compare_stock_vs_sales": compare_stock_vs_sales,
    "get_sales_forecast": get_sales_forecast,
    "get_chart_data": get_chart_data,
}


def execute_tool(tool_name: str, tool_input: Dict[str, Any]) -> str:
    """
    Execute a tool by name with given input parameters.

    Args:
        tool_name: Name of the tool to execute
        tool_input: Dictionary of input parameters

    Returns:
        JSON string result from the tool
    """
    if tool_name not in TOOL_FUNCTIONS:
        return json.dumps({"error": f"Tool '{tool_name}' not found"}, ensure_ascii=False)

    try:
        return TOOL_FUNCTIONS[tool_name](**tool_input)
    except TypeError as e:
        return json.dumps({"error": f"Invalid parameters for {tool_name}: {str(e)}"}, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": f"Error executing {tool_name}: {str(e)}"}, ensure_ascii=False)
