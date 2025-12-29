#!/usr/bin/env python3
"""
Diagnose Dashboard Category Issue

PROBLEM:
- Dashboard uses `products` table for category filtering
- products table has 229 products with NULL category
- When family filter is applied, ~$558M revenue is excluded
- quarterly-breakdown shows this as 'OTROS' category

This script compares:
1. Dashboard query (uses products table) vs
2. sales_facts_mv (uses product_catalog with sku_mappings)
"""

import psycopg2
import psycopg2.extras

# Session Pooler URL (IPv4 compatible for WSL2)
DATABASE_URL = "postgresql://postgres.lypuvibmtxjaxmcmahxr:%24Ilofono1@aws-1-sa-east-1.pooler.supabase.com:6543/postgres"

def diagnose():
    """Run diagnostic queries"""

    print("=" * 80)
    print("DASHBOARD CATEGORY ISSUE DIAGNOSTIC")
    print("=" * 80)

    conn = psycopg2.connect(DATABASE_URL)
    cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

    # 1. Check products table NULL categories
    print("\n1. PRODUCTS TABLE - NULL CATEGORY COUNT")
    print("-" * 60)
    cursor.execute("""
        SELECT
            COUNT(*) as total_products,
            COUNT(*) FILTER (WHERE category IS NULL) as null_category,
            COUNT(*) FILTER (WHERE category IS NOT NULL) as has_category
        FROM products
    """)
    result = cursor.fetchone()
    print(f"   Total products: {result['total_products']}")
    print(f"   NULL category: {result['null_category']}")
    print(f"   Has category: {result['has_category']}")

    # 2. Check impact on 2025 revenue
    print("\n2. 2025 REVENUE IMPACT - DASHBOARD QUERIES")
    print("-" * 60)

    # Query mimicking dashboard executive-kpis
    cursor.execute("""
        WITH dashboard_query AS (
            SELECT
                COALESCE(UPPER(p.category), 'NULL_CATEGORY') as category,
                SUM(oi.subtotal) as revenue,
                COUNT(DISTINCT o.id) as orders
            FROM orders o
            LEFT JOIN order_items oi ON oi.order_id = o.id
            LEFT JOIN products p ON p.sku = oi.product_sku
            WHERE o.source = 'relbase'
            AND o.invoice_status IN ('accepted', 'accepted_objection')
            AND EXTRACT(YEAR FROM o.order_date) = 2025
            GROUP BY COALESCE(UPPER(p.category), 'NULL_CATEGORY')
        )
        SELECT * FROM dashboard_query ORDER BY revenue DESC
    """)
    results = cursor.fetchall()

    print("\n   Dashboard View (products table join):")
    print(f"   {'Category':<20} {'Revenue':>15} {'Orders':>10}")
    print("   " + "-" * 50)
    total_revenue = 0
    null_revenue = 0
    for row in results:
        rev = float(row['revenue']) if row['revenue'] else 0
        total_revenue += rev
        if row['category'] == 'NULL_CATEGORY':
            null_revenue = rev
        print(f"   {row['category']:<20} ${rev:>14,.0f} {row['orders']:>10}")

    print("   " + "-" * 50)
    print(f"   {'TOTAL':<20} ${total_revenue:>14,.0f}")
    print(f"\n   ⚠️  NULL category revenue: ${null_revenue:,.0f} ({null_revenue/total_revenue*100:.1f}% of total)")

    # 3. Compare with sales_facts_mv categories
    print("\n3. SALES_FACTS_MV VIEW - SAME PERIOD")
    print("-" * 60)

    cursor.execute("""
        SELECT
            COALESCE(category, 'UNMAPPED') as category,
            match_type,
            SUM(revenue) as revenue,
            COUNT(DISTINCT order_id) as orders
        FROM sales_facts_mv
        WHERE source = 'relbase'
        AND EXTRACT(YEAR FROM order_date) = 2025
        GROUP BY COALESCE(category, 'UNMAPPED'), match_type
        ORDER BY revenue DESC
    """)
    results = cursor.fetchall()

    print("\n   sales_facts_mv (product_catalog + sku_mappings):")
    print(f"   {'Category':<20} {'Match Type':<25} {'Revenue':>15}")
    print("   " + "-" * 65)
    total_mv_revenue = 0
    for row in results:
        rev = float(row['revenue']) if row['revenue'] else 0
        total_mv_revenue += rev
        print(f"   {row['category']:<20} {row['match_type']:<25} ${rev:>14,.0f}")

    print("   " + "-" * 65)
    print(f"   {'TOTAL':<20} {'':<25} ${total_mv_revenue:>14,.0f}")

    # 4. Identify which SKUs are in order_items but not in products with category
    print("\n4. TOP SKUs WITH NULL CATEGORY (from orders)")
    print("-" * 60)

    cursor.execute("""
        SELECT
            oi.product_sku,
            oi.product_name,
            p.category as products_category,
            pc.category as product_catalog_category,
            sm.target_sku as mapped_to,
            SUM(oi.subtotal) as revenue,
            COUNT(DISTINCT o.id) as orders
        FROM orders o
        JOIN order_items oi ON oi.order_id = o.id
        LEFT JOIN products p ON p.sku = oi.product_sku
        LEFT JOIN product_catalog pc ON pc.sku = UPPER(oi.product_sku) OR pc.sku_master = UPPER(oi.product_sku)
        LEFT JOIN sku_mappings sm ON sm.source_pattern = UPPER(oi.product_sku) AND sm.is_active = TRUE
        WHERE o.source = 'relbase'
        AND o.invoice_status IN ('accepted', 'accepted_objection')
        AND EXTRACT(YEAR FROM o.order_date) = 2025
        AND p.category IS NULL
        GROUP BY oi.product_sku, oi.product_name, p.category, pc.category, sm.target_sku
        ORDER BY revenue DESC
        LIMIT 15
    """)
    results = cursor.fetchall()

    print("\n   SKUs with NULL category in products table:")
    print(f"   {'SKU':<25} {'Prod Cat':<12} {'Mapped To':<15} {'Revenue':>12}")
    print("   " + "-" * 70)
    for row in results:
        pc_cat = row['product_catalog_category'] or 'NULL'
        mapped = row['mapped_to'] or 'N/A'
        rev = float(row['revenue']) if row['revenue'] else 0
        print(f"   {row['product_sku'][:24]:<25} {pc_cat:<12} {mapped[:14]:<15} ${rev:>11,.0f}")

    # 5. Compare category sums: Dashboard vs sales_facts_mv
    print("\n5. CATEGORY COMPARISON: DASHBOARD vs SALES_FACTS_MV")
    print("-" * 60)

    # Dashboard grouped by category (products table)
    cursor.execute("""
        SELECT
            COALESCE(UPPER(p.category), 'OTROS/NULL') as category,
            SUM(oi.subtotal) as revenue
        FROM orders o
        LEFT JOIN order_items oi ON oi.order_id = o.id
        LEFT JOIN products p ON p.sku = oi.product_sku
        WHERE o.source = 'relbase'
        AND o.invoice_status IN ('accepted', 'accepted_objection')
        AND EXTRACT(YEAR FROM o.order_date) = 2025
        GROUP BY COALESCE(UPPER(p.category), 'OTROS/NULL')
        ORDER BY revenue DESC
    """)
    dashboard_results = {row[0]: float(row[1]) if row[1] else 0 for row in cursor.fetchall()}

    # sales_facts_mv grouped by category
    cursor.execute("""
        SELECT
            COALESCE(category, 'UNMAPPED') as category,
            SUM(revenue) as revenue
        FROM sales_facts_mv
        WHERE source = 'relbase'
        AND EXTRACT(YEAR FROM order_date) = 2025
        GROUP BY COALESCE(category, 'UNMAPPED')
        ORDER BY revenue DESC
    """)
    mv_results = {row[0]: float(row[1]) if row[1] else 0 for row in cursor.fetchall()}

    all_categories = set(list(dashboard_results.keys()) + list(mv_results.keys()))

    print(f"\n   {'Category':<20} {'Dashboard':>15} {'sales_facts_mv':>15} {'Difference':>15}")
    print("   " + "-" * 70)
    for cat in sorted(all_categories, key=lambda x: max(dashboard_results.get(x, 0), mv_results.get(x, 0)), reverse=True):
        dash = dashboard_results.get(cat, 0)
        mv = mv_results.get(cat, 0)
        diff = mv - dash
        diff_str = f"+${diff:,.0f}" if diff >= 0 else f"-${abs(diff):,.0f}"
        print(f"   {cat[:19]:<20} ${dash:>14,.0f} ${mv:>14,.0f} {diff_str:>15}")

    # 6. RECOMMENDATION
    print("\n" + "=" * 80)
    print("DIAGNOSIS COMPLETE")
    print("=" * 80)

    print("""
FINDINGS:
1. Dashboard uses 'products' table which has many NULL categories
2. sales_facts_mv uses 'product_catalog' with 'sku_mappings' - better categorization
3. NULL category products show as 'OTROS' in quarterly-breakdown
4. NULL category products are EXCLUDED when filtering by family in executive-kpis

RECOMMENDED FIX:
Update dashboard endpoints to use sales_facts_mv instead of direct products table join.

Files to modify:
1. backend/app/api/orders.py (executive-kpis endpoint)
2. backend/app/api/analytics.py (quarterly-breakdown endpoint)

Both should query from sales_facts_mv for consistent category data.
""")

    cursor.close()
    conn.close()

if __name__ == "__main__":
    diagnose()
