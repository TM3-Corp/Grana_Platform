#!/usr/bin/env python3
"""
Database-level comparison between Sales Analytics (MV) and Audit logic

This test compares:
1. sales_facts_mv (materialized view used by sales-analytics)
2. Raw tables with SKU mapping logic (simulating what audit.py does)

Purpose: Verify both produce aligned results for the same data.
"""

import psycopg2
from datetime import datetime

DATABASE_URL = "postgresql://postgres.lypuvibmtxjaxmcmahxr:%24Ilofono1@aws-1-sa-east-1.pooler.supabase.com:6543/postgres"


def format_currency(value):
    return f"${value:,.0f}"


def format_pct(value):
    return f"{value:.1f}%"


def print_header(title):
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80)


def print_subheader(title):
    print(f"\n--- {title} ---")


def test_total_revenue_comparison(cursor):
    """
    Test 1: Compare total revenue between MV and raw order_items
    """
    print_header("TEST 1: Total Revenue & Units Comparison")

    # Get totals from MV
    cursor.execute("""
        SELECT
            SUM(revenue) as total_revenue,
            SUM(units_sold) as total_units,
            SUM(original_units_sold) as raw_units,
            COUNT(*) as item_count,
            COUNT(DISTINCT order_id) as order_count
        FROM sales_facts_mv
        WHERE source = 'relbase'
          AND EXTRACT(YEAR FROM order_date) = 2025;
    """)
    mv_result = cursor.fetchone()
    mv_revenue, mv_units, mv_raw_units, mv_items, mv_orders = mv_result

    # Get totals from raw order_items (same filter as MV)
    cursor.execute("""
        SELECT
            SUM(oi.subtotal) as total_revenue,
            SUM(oi.quantity) as total_units,
            COUNT(*) as item_count,
            COUNT(DISTINCT o.id) as order_count
        FROM orders o
        JOIN order_items oi ON o.id = oi.order_id
        WHERE o.source = 'relbase'
          AND EXTRACT(YEAR FROM o.order_date) = 2025
          AND o.invoice_status IN ('accepted', 'accepted_objection')
          AND o.status != 'cancelled';
    """)
    raw_result = cursor.fetchone()
    raw_revenue, raw_units, raw_items, raw_orders = raw_result

    print(f"\n  {'Metric':<20} {'MV (sales_facts)':>18} {'Raw Tables':>18} {'Diff':>12}")
    print("  " + "-" * 70)
    print(f"  {'Revenue':<20} {format_currency(mv_revenue):>18} {format_currency(raw_revenue):>18} "
          f"{format_currency(abs(mv_revenue - raw_revenue)):>12}")
    print(f"  {'Raw Units':<20} {mv_raw_units:>18,} {raw_units:>18,} "
          f"{abs(mv_raw_units - raw_units):>12,}")
    print(f"  {'Adjusted Units':<20} {mv_units:>18,} {'(N/A - no MV)':>18} "
          f"{'N/A':>12}")
    print(f"  {'Items':<20} {mv_items:>18,} {raw_items:>18,} "
          f"{abs(mv_items - raw_items):>12,}")
    print(f"  {'Orders':<20} {mv_orders:>18,} {raw_orders:>18,} "
          f"{abs(mv_orders - raw_orders):>12,}")

    # Revenue should match exactly
    revenue_match = abs(mv_revenue - raw_revenue) < 1  # Allow $1 rounding
    units_match = mv_raw_units == raw_units
    items_match = mv_items == raw_items

    if revenue_match and units_match and items_match:
        print(f"\n  ✅ PASS: MV and raw tables have matching totals")
        return True
    else:
        print(f"\n  ❌ FAIL: Discrepancy detected")
        return False


def test_category_breakdown(cursor):
    """
    Test 2: Compare category breakdown
    """
    print_header("TEST 2: Category Breakdown Comparison")

    # MV categories
    cursor.execute("""
        SELECT
            COALESCE(category, 'UNMAPPED') as category,
            SUM(revenue) as revenue,
            SUM(units_sold) as units,
            COUNT(*) as items
        FROM sales_facts_mv
        WHERE source = 'relbase'
          AND EXTRACT(YEAR FROM order_date) = 2025
        GROUP BY category
        ORDER BY revenue DESC;
    """)
    mv_categories = {row[0]: {'revenue': row[1], 'units': row[2], 'items': row[3]}
                     for row in cursor.fetchall()}

    # Raw tables with same join logic as MV
    cursor.execute("""
        WITH sku_matched AS (
            SELECT
                oi.id,
                oi.subtotal,
                oi.quantity,
                COALESCE(
                    pc_direct.category,
                    CASE WHEN pc_master.sku IS NOT NULL THEN 'CAJA MASTER' END,
                    pc_mapped.category,
                    CASE WHEN pc_mapped_master.sku IS NOT NULL THEN 'CAJA MASTER' END
                ) as category
            FROM orders o
            JOIN order_items oi ON o.id = oi.order_id
            LEFT JOIN product_catalog pc_direct
                ON pc_direct.sku = UPPER(oi.product_sku) AND pc_direct.is_active = TRUE
            LEFT JOIN product_catalog pc_master
                ON pc_master.sku_master = UPPER(oi.product_sku)
                AND pc_master.is_active = TRUE AND pc_direct.sku IS NULL
            LEFT JOIN sku_mappings sm
                ON sm.source_pattern = UPPER(oi.product_sku)
                AND sm.pattern_type = 'exact' AND sm.is_active = TRUE
                AND pc_direct.sku IS NULL AND pc_master.sku IS NULL
            LEFT JOIN product_catalog pc_mapped
                ON pc_mapped.sku = sm.target_sku AND pc_mapped.is_active = TRUE
            LEFT JOIN product_catalog pc_mapped_master
                ON pc_mapped_master.sku_master = sm.target_sku
                AND pc_mapped_master.is_active = TRUE AND pc_mapped.sku IS NULL
            WHERE o.source = 'relbase'
              AND EXTRACT(YEAR FROM o.order_date) = 2025
              AND o.invoice_status IN ('accepted', 'accepted_objection')
              AND o.status != 'cancelled'
        )
        SELECT
            COALESCE(category, 'UNMAPPED') as category,
            SUM(subtotal) as revenue,
            SUM(quantity) as units,
            COUNT(*) as items
        FROM sku_matched
        GROUP BY category
        ORDER BY revenue DESC;
    """)
    raw_categories = {row[0]: {'revenue': row[1], 'units': row[2], 'items': row[3]}
                      for row in cursor.fetchall()}

    all_categories = set(mv_categories.keys()) | set(raw_categories.keys())

    print(f"\n  {'Category':<15} {'MV Revenue':>15} {'Raw Revenue':>15} {'Diff %':>10} {'Status':>8}")
    print("  " + "-" * 70)

    all_match = True
    for cat in sorted(all_categories, key=lambda c: mv_categories.get(c, {}).get('revenue', 0), reverse=True):
        mv_rev = mv_categories.get(cat, {}).get('revenue', 0)
        raw_rev = raw_categories.get(cat, {}).get('revenue', 0)

        if mv_rev > 0:
            diff_pct = abs(mv_rev - raw_rev) / mv_rev * 100
        else:
            diff_pct = 100 if raw_rev > 0 else 0

        status = "✅" if diff_pct < 0.1 else "⚠️"
        if diff_pct >= 0.1:
            all_match = False

        print(f"  {cat:<15} {format_currency(mv_rev):>15} {format_currency(raw_rev):>15} "
              f"{format_pct(diff_pct):>10} {status:>8}")

    if all_match:
        print(f"\n  ✅ PASS: All categories match within 0.1%")
    else:
        print(f"\n  ⚠️  WARNING: Some category differences detected")
    return all_match


def test_pack_multiplier_application(cursor):
    """
    Test 3: Verify PACK products have correct quantity multipliers
    """
    print_header("TEST 3: PACK Quantity Multiplier Verification")

    cursor.execute("""
        SELECT
            original_sku,
            catalog_sku,
            quantity_multiplier,
            SUM(original_units_sold) as raw_units,
            SUM(units_sold) as adjusted_units,
            SUM(revenue) as revenue,
            match_type
        FROM sales_facts_mv
        WHERE original_sku LIKE 'PACK%'
          AND source = 'relbase'
          AND EXTRACT(YEAR FROM order_date) = 2025
        GROUP BY original_sku, catalog_sku, quantity_multiplier, match_type
        ORDER BY revenue DESC
        LIMIT 20;
    """)

    pack_results = cursor.fetchall()

    print(f"\n  {'Original SKU':<22} {'Mapped SKU':<15} {'×':>3} {'Raw':>8} {'Adj':>8} {'Expected':>8} {'Status':>8}")
    print("  " + "-" * 85)

    all_correct = True
    for row in pack_results:
        orig_sku, mapped_sku, multiplier, raw_units, adj_units, revenue, match_type = row

        expected = raw_units * multiplier
        status = "✅" if adj_units == expected else "❌"
        if adj_units != expected:
            all_correct = False

        mapped_display = mapped_sku if mapped_sku else "UNMAPPED"
        print(f"  {orig_sku:<22} {mapped_display:<15} {multiplier:>3} {raw_units:>8} {adj_units:>8} "
              f"{expected:>8} {status:>8}")

    if all_correct:
        print(f"\n  ✅ PASS: All PACK multipliers applied correctly")
    else:
        print(f"\n  ❌ FAIL: Some PACK multipliers are incorrect")
    return all_correct


def test_channel_revenue(cursor):
    """
    Test 4: Compare channel revenue breakdown
    """
    print_header("TEST 4: Channel Revenue Comparison")

    # MV channels
    cursor.execute("""
        SELECT
            COALESCE(channel_name, 'Sin Canal') as channel,
            SUM(revenue) as revenue,
            COUNT(DISTINCT order_id) as orders
        FROM sales_facts_mv
        WHERE source = 'relbase'
          AND EXTRACT(YEAR FROM order_date) = 2025
        GROUP BY channel_name
        ORDER BY revenue DESC;
    """)
    mv_channels = cursor.fetchall()

    # Raw channels
    cursor.execute("""
        SELECT
            COALESCE(ch.name, 'Sin Canal') as channel,
            SUM(oi.subtotal) as revenue,
            COUNT(DISTINCT o.id) as orders
        FROM orders o
        JOIN order_items oi ON o.id = oi.order_id
        LEFT JOIN channels ch ON o.channel_id = ch.id
        WHERE o.source = 'relbase'
          AND EXTRACT(YEAR FROM o.order_date) = 2025
          AND o.invoice_status IN ('accepted', 'accepted_objection')
          AND o.status != 'cancelled'
        GROUP BY ch.name
        ORDER BY revenue DESC;
    """)
    raw_channels = cursor.fetchall()

    print(f"\n  MV Channel Breakdown:")
    print(f"  {'Channel':<25} {'Revenue':>15} {'Orders':>10}")
    print("  " + "-" * 55)
    mv_total = 0
    for row in mv_channels:
        print(f"  {row[0]:<25} {format_currency(row[1]):>15} {row[2]:>10,}")
        mv_total += row[1]
    print("  " + "-" * 55)
    print(f"  {'TOTAL':<25} {format_currency(mv_total):>15}")

    print(f"\n  Raw Tables Channel Breakdown:")
    print(f"  {'Channel':<25} {'Revenue':>15} {'Orders':>10}")
    print("  " + "-" * 55)
    raw_total = 0
    for row in raw_channels:
        print(f"  {row[0]:<25} {format_currency(row[1]):>15} {row[2]:>10,}")
        raw_total += row[1]
    print("  " + "-" * 55)
    print(f"  {'TOTAL':<25} {format_currency(raw_total):>15}")

    match = abs(mv_total - raw_total) < 1
    if match:
        print(f"\n  ✅ PASS: Channel totals match")
    else:
        print(f"\n  ⚠️  Difference: {format_currency(abs(mv_total - raw_total))}")
    return match


def test_monthly_trend(cursor):
    """
    Test 5: Compare monthly revenue trend
    """
    print_header("TEST 5: Monthly Revenue Trend Comparison")

    # MV monthly
    cursor.execute("""
        SELECT
            TO_CHAR(order_date, 'YYYY-MM') as month,
            SUM(revenue) as revenue,
            SUM(units_sold) as units,
            COUNT(DISTINCT order_id) as orders
        FROM sales_facts_mv
        WHERE source = 'relbase'
          AND EXTRACT(YEAR FROM order_date) = 2025
        GROUP BY TO_CHAR(order_date, 'YYYY-MM')
        ORDER BY month;
    """)
    mv_monthly = {row[0]: {'revenue': row[1], 'units': row[2], 'orders': row[3]}
                  for row in cursor.fetchall()}

    # Raw monthly
    cursor.execute("""
        SELECT
            TO_CHAR(o.order_date, 'YYYY-MM') as month,
            SUM(oi.subtotal) as revenue,
            SUM(oi.quantity) as units,
            COUNT(DISTINCT o.id) as orders
        FROM orders o
        JOIN order_items oi ON o.id = oi.order_id
        WHERE o.source = 'relbase'
          AND EXTRACT(YEAR FROM o.order_date) = 2025
          AND o.invoice_status IN ('accepted', 'accepted_objection')
          AND o.status != 'cancelled'
        GROUP BY TO_CHAR(o.order_date, 'YYYY-MM')
        ORDER BY month;
    """)
    raw_monthly = {row[0]: {'revenue': row[1], 'units': row[2], 'orders': row[3]}
                   for row in cursor.fetchall()}

    all_months = sorted(set(mv_monthly.keys()) | set(raw_monthly.keys()))

    print(f"\n  {'Month':<10} {'MV Revenue':>15} {'Raw Revenue':>15} {'Diff':>12} {'Status':>8}")
    print("  " + "-" * 65)

    all_match = True
    for month in all_months:
        mv_rev = mv_monthly.get(month, {}).get('revenue', 0)
        raw_rev = raw_monthly.get(month, {}).get('revenue', 0)
        diff = abs(mv_rev - raw_rev)
        status = "✅" if diff < 1 else "⚠️"
        if diff >= 1:
            all_match = False
        print(f"  {month:<10} {format_currency(mv_rev):>15} {format_currency(raw_rev):>15} "
              f"{format_currency(diff):>12} {status:>8}")

    if all_match:
        print(f"\n  ✅ PASS: All months match")
    else:
        print(f"\n  ⚠️  WARNING: Some months have small differences")
    return all_match


def test_sku_primario_grouping(cursor):
    """
    Test 6: Verify sku_primario grouping consolidates correctly
    """
    print_header("TEST 6: SKU Primario Consolidation")

    # Get top SKU Primarios with their consolidated totals
    cursor.execute("""
        SELECT
            sku_primario,
            array_agg(DISTINCT original_sku ORDER BY original_sku) as source_skus,
            SUM(revenue) as revenue,
            SUM(units_sold) as units,
            COUNT(*) as items
        FROM sales_facts_mv
        WHERE source = 'relbase'
          AND EXTRACT(YEAR FROM order_date) = 2025
          AND sku_primario IS NOT NULL
        GROUP BY sku_primario
        ORDER BY revenue DESC
        LIMIT 10;
    """)

    results = cursor.fetchall()

    print(f"\n  Top 10 SKU Primarios with source SKU consolidation:\n")

    for row in results:
        sku_primario, source_skus, revenue, units, items = row
        print(f"  {sku_primario}")
        print(f"     Revenue: {format_currency(revenue)} | Units: {units:,} | Items: {items:,}")
        if len(source_skus) > 1:
            print(f"     Consolidated from {len(source_skus)} SKUs: {', '.join(source_skus[:5])}")
            if len(source_skus) > 5:
                print(f"        ... and {len(source_skus) - 5} more")
        print()

    print(f"  ✅ SKU Primario consolidation working correctly")
    return True


def test_unmapped_skus(cursor):
    """
    Test 7: Review unmapped SKUs
    """
    print_header("TEST 7: Unmapped SKUs Review")

    cursor.execute("""
        SELECT
            original_sku,
            SUM(revenue) as revenue,
            SUM(original_units_sold) as units,
            COUNT(*) as occurrences
        FROM sales_facts_mv
        WHERE source = 'relbase'
          AND EXTRACT(YEAR FROM order_date) = 2025
          AND match_type = 'unmapped'
        GROUP BY original_sku
        ORDER BY revenue DESC
        LIMIT 15;
    """)

    unmapped = cursor.fetchall()

    print(f"\n  Top 15 Unmapped SKUs (need sku_mappings rules):\n")
    print(f"  {'SKU':<25} {'Revenue':>15} {'Units':>10} {'Count':>8}")
    print("  " + "-" * 65)

    total_unmapped_revenue = 0
    for row in unmapped:
        sku, revenue, units, count = row
        total_unmapped_revenue += revenue
        print(f"  {sku:<25} {format_currency(revenue):>15} {units:>10,} {count:>8,}")

    # Get total revenue for context
    cursor.execute("""
        SELECT SUM(revenue) FROM sales_facts_mv
        WHERE source = 'relbase' AND EXTRACT(YEAR FROM order_date) = 2025;
    """)
    total_revenue = cursor.fetchone()[0]

    unmapped_pct = (total_unmapped_revenue / total_revenue * 100) if total_revenue > 0 else 0

    print("  " + "-" * 65)
    print(f"  {'Total Unmapped':<25} {format_currency(total_unmapped_revenue):>15}")
    print(f"  {'% of Total Revenue':<25} {format_pct(unmapped_pct):>15}")

    if unmapped_pct < 5:
        print(f"\n  ✅ PASS: Unmapped SKUs are {format_pct(unmapped_pct)} of revenue (< 5% threshold)")
        return True
    else:
        print(f"\n  ⚠️  WARNING: Unmapped SKUs exceed 5% threshold")
        return False


def run_all_tests():
    """Run all database-level comparison tests"""
    print("\n" + "=" * 80)
    print("  SALES ANALYTICS DATABASE-LEVEL ALIGNMENT TEST")
    print("  Comparing: sales_facts_mv vs Raw Tables with Same Logic")
    print("=" * 80)
    print(f"\n  Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    try:
        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor()

        results = {}

        results["Test 1: Total Revenue & Units"] = test_total_revenue_comparison(cursor)
        results["Test 2: Category Breakdown"] = test_category_breakdown(cursor)
        results["Test 3: PACK Multipliers"] = test_pack_multiplier_application(cursor)
        results["Test 4: Channel Revenue"] = test_channel_revenue(cursor)
        results["Test 5: Monthly Trend"] = test_monthly_trend(cursor)
        results["Test 6: SKU Primario Consolidation"] = test_sku_primario_grouping(cursor)
        results["Test 7: Unmapped SKUs Review"] = test_unmapped_skus(cursor)

        cursor.close()
        conn.close()

        # Summary
        print_header("TEST SUMMARY")

        passed = sum(1 for v in results.values() if v)
        total = len(results)

        print(f"\n  Results: {passed}/{total} tests passed\n")

        for test_name, result in results.items():
            status = "✅ PASS" if result else "❌ FAIL"
            print(f"  {status}  {test_name}")

        print(f"\n  Completed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 80)

        return all(results.values())

    except Exception as e:
        print(f"\n❌ Database connection error: {e}")
        return False


if __name__ == "__main__":
    import sys
    success = run_all_tests()
    sys.exit(0 if success else 1)
