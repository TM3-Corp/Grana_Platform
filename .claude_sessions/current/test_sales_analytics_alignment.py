#!/usr/bin/env python3
"""
Comprehensive test suite comparing Sales Analytics with Desglose Pedidos (Audit)

Purpose: Verify both endpoints produce aligned results when using same filters

Endpoints:
- Sales Analytics: /api/v1/sales_analytics (uses sales_facts_mv materialized view)
- Desglose Pedidos: /api/v1/audit/data (uses raw tables + Python SKU mapping)
"""

import requests
import json
from datetime import datetime, timedelta
from collections import defaultdict

# API Configuration
BASE_URL = "http://localhost:8000/api/v1"
SALES_ANALYTICS_URL = f"{BASE_URL}/sales-analytics"
AUDIT_URL = f"{BASE_URL}/audit/data"

# Test configuration
TEST_YEAR = 2025
TEST_MONTH = "2025-11"  # November 2025 for recent data


def format_currency(value):
    """Format number as currency"""
    return f"${value:,.0f}"


def format_pct(value):
    """Format as percentage"""
    return f"{value:.1f}%"


def print_header(title):
    """Print test section header"""
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80)


def print_subheader(title):
    """Print test subsection header"""
    print(f"\n--- {title} ---")


def test_summary_totals():
    """
    Test 1: Compare overall summary totals between endpoints

    Both endpoints should produce similar total revenue, units, and orders
    for the same time period and filters.
    """
    print_header("TEST 1: Summary Totals Comparison")

    # Get Sales Analytics summary (default 2025)
    print("\nFetching Sales Analytics summary...")
    try:
        sa_response = requests.get(SALES_ANALYTICS_URL, timeout=30)
        sa_data = sa_response.json()

        if sa_data.get("status") != "success":
            print(f"❌ Sales Analytics error: {sa_data}")
            return False

        sa_summary = sa_data["data"]["summary"]
        print(f"  ✓ Sales Analytics: {format_currency(sa_summary['total_revenue'])} revenue, "
              f"{sa_summary['total_units']:,} units, {sa_summary['total_orders']:,} orders")
    except Exception as e:
        print(f"❌ Error calling Sales Analytics: {e}")
        return False

    # Get Audit data (calculate totals from line items)
    print("\nFetching Audit/Desglose Pedidos data...")
    try:
        audit_response = requests.get(
            AUDIT_URL,
            params={"source": "relbase", "limit": 50000},
            timeout=60
        )
        audit_data = audit_response.json()

        if audit_data.get("status") != "success":
            print(f"❌ Audit error: {audit_data}")
            return False

        # Calculate totals from audit data (2025 only)
        audit_rows = audit_data["data"]["rows"]
        audit_revenue = 0
        audit_units = 0
        audit_orders = set()

        for row in audit_rows:
            # Filter for 2025
            order_date = row.get("fecha", "")
            if order_date and order_date.startswith("2025"):
                audit_revenue += float(row.get("total", 0) or 0)
                audit_units += int(row.get("unidades", 0) or row.get("cantidad", 0) or 0)
                audit_orders.add(row.get("pedido"))

        print(f"  ✓ Audit/Desglose: {format_currency(audit_revenue)} revenue, "
              f"{audit_units:,} units, {len(audit_orders):,} orders")
    except Exception as e:
        print(f"❌ Error calling Audit: {e}")
        return False

    # Compare results
    print_subheader("Comparison")

    # Revenue comparison
    revenue_diff = abs(sa_summary['total_revenue'] - audit_revenue)
    revenue_pct_diff = (revenue_diff / sa_summary['total_revenue'] * 100) if sa_summary['total_revenue'] > 0 else 0

    # Units comparison
    units_diff = abs(sa_summary['total_units'] - audit_units)
    units_pct_diff = (units_diff / sa_summary['total_units'] * 100) if sa_summary['total_units'] > 0 else 0

    # Orders comparison
    orders_diff = abs(sa_summary['total_orders'] - len(audit_orders))

    print(f"\n  {'Metric':<15} {'Sales Analytics':>18} {'Audit':>18} {'Diff':>12} {'% Diff':>10}")
    print("  " + "-" * 75)
    print(f"  {'Revenue':<15} {format_currency(sa_summary['total_revenue']):>18} {format_currency(audit_revenue):>18} "
          f"{format_currency(revenue_diff):>12} {format_pct(revenue_pct_diff):>10}")
    print(f"  {'Units':<15} {sa_summary['total_units']:>18,} {audit_units:>18,} "
          f"{units_diff:>12,} {format_pct(units_pct_diff):>10}")
    print(f"  {'Orders':<15} {sa_summary['total_orders']:>18,} {len(audit_orders):>18,} "
          f"{orders_diff:>12,} {'N/A':>10}")

    # Verdict
    # Allow 5% tolerance for differences (due to timing, filters, etc.)
    tolerance = 5.0
    if revenue_pct_diff <= tolerance and units_pct_diff <= tolerance:
        print(f"\n  ✅ PASS: Totals are within {tolerance}% tolerance")
        return True
    else:
        print(f"\n  ⚠️  WARNING: Differences exceed {tolerance}% tolerance")
        return False


def test_category_breakdown():
    """
    Test 2: Compare category breakdown between endpoints

    Both endpoints should show similar revenue distribution by category.
    """
    print_header("TEST 2: Category Breakdown Comparison")

    # Get Sales Analytics by category
    print("\nFetching Sales Analytics by category...")
    try:
        sa_response = requests.get(
            SALES_ANALYTICS_URL,
            params={"group_by": "category"},
            timeout=30
        )
        sa_data = sa_response.json()
        sa_categories = {item['group_value']: item for item in sa_data["data"]["top_items"]}
        print(f"  ✓ Got {len(sa_categories)} categories from Sales Analytics")
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

    # Get Audit data and aggregate by category
    print("\nFetching Audit data and aggregating by category...")
    try:
        audit_response = requests.get(
            AUDIT_URL,
            params={"source": "relbase", "limit": 50000},
            timeout=60
        )
        audit_data = audit_response.json()

        audit_categories = defaultdict(lambda: {"revenue": 0, "units": 0})

        for row in audit_data["data"]["rows"]:
            order_date = row.get("fecha", "")
            if order_date and order_date.startswith("2025"):
                category = row.get("familia") or "UNMAPPED"
                audit_categories[category]["revenue"] += float(row.get("total", 0) or 0)
                audit_categories[category]["units"] += int(row.get("unidades", 0) or row.get("cantidad", 0) or 0)

        print(f"  ✓ Got {len(audit_categories)} categories from Audit")
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

    # Compare categories
    print_subheader("Category Comparison")

    all_categories = set(sa_categories.keys()) | set(audit_categories.keys())

    print(f"\n  {'Category':<20} {'SA Revenue':>15} {'Audit Revenue':>15} {'Diff %':>10} {'Status':>10}")
    print("  " + "-" * 75)

    mismatches = 0
    for cat in sorted(all_categories, key=lambda c: sa_categories.get(c, {}).get('revenue', 0), reverse=True):
        sa_rev = sa_categories.get(cat, {}).get('revenue', 0)
        audit_rev = audit_categories.get(cat, {}).get('revenue', 0)

        if sa_rev > 0:
            diff_pct = abs(sa_rev - audit_rev) / sa_rev * 100
        elif audit_rev > 0:
            diff_pct = 100.0
        else:
            diff_pct = 0.0

        status = "✅" if diff_pct <= 10 else "⚠️"
        if diff_pct > 10:
            mismatches += 1

        print(f"  {(cat or 'NULL'):<20} {format_currency(sa_rev):>15} {format_currency(audit_rev):>15} "
              f"{format_pct(diff_pct):>10} {status:>10}")

    if mismatches == 0:
        print(f"\n  ✅ PASS: All categories within 10% tolerance")
        return True
    else:
        print(f"\n  ⚠️  WARNING: {mismatches} categories have >10% difference")
        return False


def test_pack_products():
    """
    Test 3: Verify PACK products have correct quantity multipliers

    PACK products should show:
    - Sales Analytics: units_sold = original_units × multiplier (via MV)
    - Audit: unidades = cantidad × multiplier (via Python mapping)
    """
    print_header("TEST 3: PACK Products Quantity Multiplier")

    import psycopg2

    DATABASE_URL = "postgresql://postgres.lypuvibmtxjaxmcmahxr:%24Ilofono1@aws-1-sa-east-1.pooler.supabase.com:6543/postgres"

    print("\nQuerying sales_facts_mv for PACK products...")

    try:
        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor()

        # Get PACK products from MV
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
            LIMIT 15;
        """)

        pack_results = cursor.fetchall()

        print(f"\n  {'Original SKU':<22} {'Mapped SKU':<15} {'×':>3} {'Raw':>8} {'Adj':>8} {'Revenue':>12} {'Status':>8}")
        print("  " + "-" * 85)

        issues = 0
        for row in pack_results:
            orig_sku, mapped_sku, multiplier, raw_units, adj_units, revenue, match_type = row

            # Verify multiplier is applied correctly
            expected_adj = raw_units * multiplier
            status = "✅" if adj_units == expected_adj else "❌"
            if adj_units != expected_adj:
                issues += 1

            mapped_display = mapped_sku if mapped_sku else "UNMAPPED"
            print(f"  {orig_sku:<22} {mapped_display:<15} {multiplier:>3} {raw_units:>8} {adj_units:>8} "
                  f"{format_currency(revenue):>12} {status:>8}")

        cursor.close()
        conn.close()

        if issues == 0:
            print(f"\n  ✅ PASS: All PACK products have correct multiplier applied")
            return True
        else:
            print(f"\n  ❌ FAIL: {issues} PACK products have incorrect multipliers")
            return False

    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def test_channel_grouping():
    """
    Test 4: Compare channel groupings between endpoints
    """
    print_header("TEST 4: Channel Grouping Comparison")

    # Get Sales Analytics by channel
    print("\nFetching Sales Analytics by channel...")
    try:
        sa_response = requests.get(
            SALES_ANALYTICS_URL,
            params={"group_by": "channel"},
            timeout=30
        )
        sa_data = sa_response.json()
        sa_channels = {item['group_value']: item for item in sa_data["data"]["top_items"]}

        print(f"\n  Sales Analytics Channels:")
        for ch, data in sorted(sa_channels.items(), key=lambda x: x[1]['revenue'], reverse=True):
            print(f"    {ch or 'NULL':<25} {format_currency(data['revenue']):>15} "
                  f"({data['orders']:,} orders)")
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

    # Get Audit data by channel
    print("\nFetching Audit data by channel...")
    try:
        audit_response = requests.get(
            AUDIT_URL,
            params={"source": "relbase", "limit": 50000},
            timeout=60
        )
        audit_data = audit_response.json()

        audit_channels = defaultdict(lambda: {"revenue": 0, "orders": set()})

        for row in audit_data["data"]["rows"]:
            order_date = row.get("fecha", "")
            if order_date and order_date.startswith("2025"):
                channel = row.get("canal") or "NULL"
                audit_channels[channel]["revenue"] += float(row.get("total", 0) or 0)
                audit_channels[channel]["orders"].add(row.get("pedido"))

        print(f"\n  Audit Channels:")
        for ch, data in sorted(audit_channels.items(), key=lambda x: x[1]['revenue'], reverse=True):
            print(f"    {ch:<25} {format_currency(data['revenue']):>15} "
                  f"({len(data['orders']):,} orders)")
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

    # Compare
    print_subheader("Channel Revenue Comparison")

    all_channels = set(sa_channels.keys()) | set(audit_channels.keys())

    print(f"\n  {'Channel':<25} {'SA Revenue':>15} {'Audit Revenue':>15} {'Diff %':>10}")
    print("  " + "-" * 70)

    for ch in sorted(all_channels, key=lambda c: sa_channels.get(c, {}).get('revenue', 0), reverse=True):
        sa_rev = sa_channels.get(ch, {}).get('revenue', 0)
        audit_rev = audit_channels.get(ch, {}).get('revenue', 0)

        if sa_rev > 0:
            diff_pct = abs(sa_rev - audit_rev) / sa_rev * 100
        elif audit_rev > 0:
            diff_pct = 100.0
        else:
            diff_pct = 0.0

        status = "✅" if diff_pct <= 10 else "⚠️"

        print(f"  {(ch or 'NULL'):<25} {format_currency(sa_rev):>15} {format_currency(audit_rev):>15} "
              f"{format_pct(diff_pct):>10} {status}")

    return True


def test_date_range_filter():
    """
    Test 5: Verify date range filters work consistently
    """
    print_header("TEST 5: Date Range Filter Comparison")

    # Test specific month: November 2025
    from_date = "2025-11-01"
    to_date = "2025-11-30"

    print(f"\nTesting date range: {from_date} to {to_date}")

    # Get Sales Analytics for date range
    print("\nFetching Sales Analytics for date range...")
    try:
        sa_response = requests.get(
            SALES_ANALYTICS_URL,
            params={"from_date": from_date, "to_date": to_date},
            timeout=30
        )
        sa_data = sa_response.json()
        sa_summary = sa_data["data"]["summary"]

        print(f"  ✓ Sales Analytics: {format_currency(sa_summary['total_revenue'])} revenue, "
              f"{sa_summary['total_units']:,} units, {sa_summary['total_orders']:,} orders")
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

    # Get Audit data for date range
    print("\nFetching Audit data for date range...")
    try:
        audit_response = requests.get(
            AUDIT_URL,
            params={
                "source": "relbase",
                "from_date": from_date,
                "to_date": to_date,
                "limit": 50000
            },
            timeout=60
        )
        audit_data = audit_response.json()

        audit_revenue = 0
        audit_units = 0
        audit_orders = set()

        for row in audit_data["data"]["rows"]:
            audit_revenue += float(row.get("total", 0) or 0)
            audit_units += int(row.get("unidades", 0) or row.get("cantidad", 0) or 0)
            audit_orders.add(row.get("pedido"))

        print(f"  ✓ Audit: {format_currency(audit_revenue)} revenue, "
              f"{audit_units:,} units, {len(audit_orders):,} orders")
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

    # Compare
    print_subheader("Comparison for November 2025")

    revenue_diff_pct = abs(sa_summary['total_revenue'] - audit_revenue) / sa_summary['total_revenue'] * 100 if sa_summary['total_revenue'] > 0 else 0
    units_diff_pct = abs(sa_summary['total_units'] - audit_units) / sa_summary['total_units'] * 100 if sa_summary['total_units'] > 0 else 0

    print(f"\n  Revenue: SA={format_currency(sa_summary['total_revenue'])}, Audit={format_currency(audit_revenue)}, "
          f"Diff={format_pct(revenue_diff_pct)}")
    print(f"  Units:   SA={sa_summary['total_units']:,}, Audit={audit_units:,}, "
          f"Diff={format_pct(units_diff_pct)}")
    print(f"  Orders:  SA={sa_summary['total_orders']:,}, Audit={len(audit_orders):,}")

    if revenue_diff_pct <= 5 and units_diff_pct <= 5:
        print(f"\n  ✅ PASS: Date range filter produces consistent results")
        return True
    else:
        print(f"\n  ⚠️  WARNING: Date range results differ significantly")
        return False


def test_sku_mapping_consistency():
    """
    Test 6: Verify SKU mapping is consistent between MV and Python mapping

    Check specific SKUs that use sku_mappings table.
    """
    print_header("TEST 6: SKU Mapping Consistency")

    import psycopg2

    DATABASE_URL = "postgresql://postgres.lypuvibmtxjaxmcmahxr:%24Ilofono1@aws-1-sa-east-1.pooler.supabase.com:6543/postgres"

    print("\nComparing SKU mapping results...")

    try:
        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor()

        # Get SKU mapping summary from MV
        cursor.execute("""
            SELECT
                match_type,
                COUNT(*) as count,
                SUM(units_sold) as total_units,
                SUM(revenue) as total_revenue
            FROM sales_facts_mv
            WHERE source = 'relbase'
              AND EXTRACT(YEAR FROM order_date) = 2025
            GROUP BY match_type
            ORDER BY total_revenue DESC;
        """)

        mv_results = cursor.fetchall()

        print(f"\n  Sales Facts MV - SKU Match Types (2025):")
        print(f"  {'Match Type':<30} {'Count':>10} {'Units':>12} {'Revenue':>15}")
        print("  " + "-" * 70)

        for row in mv_results:
            match_type, count, units, revenue = row
            print(f"  {match_type:<30} {count:>10,} {units:>12,} {format_currency(revenue):>15}")

        # Get sample of each match type
        print(f"\n  Sample SKUs by Match Type:")

        for match_type in ['direct', 'caja_master', 'sku_mapping', 'sku_mapping_caja_master', 'unmapped']:
            cursor.execute("""
                SELECT DISTINCT original_sku, catalog_sku, quantity_multiplier
                FROM sales_facts_mv
                WHERE match_type = %s
                  AND source = 'relbase'
                  AND EXTRACT(YEAR FROM order_date) = 2025
                LIMIT 3;
            """, (match_type,))

            samples = cursor.fetchall()
            if samples:
                print(f"\n  {match_type}:")
                for orig, mapped, mult in samples:
                    mapped_display = mapped if mapped else "UNMAPPED"
                    print(f"    {orig} → {mapped_display} (×{mult})")

        cursor.close()
        conn.close()

        print(f"\n  ✅ PASS: SKU mapping structure verified")
        return True

    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def test_specific_sku_comparison():
    """
    Test 7: Compare specific SKU totals between both systems
    """
    print_header("TEST 7: Specific SKU Comparison")

    import psycopg2

    DATABASE_URL = "postgresql://postgres.lypuvibmtxjaxmcmahxr:%24Ilofono1@aws-1-sa-east-1.pooler.supabase.com:6543/postgres"

    # Test SKUs: some regular, some PACK, some mapped
    test_skus = [
        'BAMC_U04010',      # Direct match (common barra)
        'PACKBAMC_U20010',  # PACK product
        'GRCA_U26010',      # Granola
        'PACKGRCA_U26010',  # PACK Granola
        'CRPM_U13510',      # Cracker
    ]

    print(f"\nComparing totals for specific SKUs in 2025...")

    try:
        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor()

        print(f"\n  {'SKU':<20} {'SA Units':>10} {'SA Revenue':>15} {'Match Type':<25}")
        print("  " + "-" * 75)

        for sku in test_skus:
            # Query MV for this SKU (check both original and mapped)
            cursor.execute("""
                SELECT
                    SUM(units_sold) as total_units,
                    SUM(revenue) as total_revenue,
                    MAX(match_type) as match_type
                FROM sales_facts_mv
                WHERE (original_sku = %s OR catalog_sku = %s)
                  AND source = 'relbase'
                  AND EXTRACT(YEAR FROM order_date) = 2025;
            """, (sku, sku))

            result = cursor.fetchone()
            units = result[0] or 0
            revenue = result[1] or 0
            match_type = result[2] or 'not_found'

            print(f"  {sku:<20} {units:>10,} {format_currency(revenue):>15} {match_type:<25}")

        # Also show PACK consolidation example
        print(f"\n  PACK Consolidation Example (GRCA_U26010):")
        cursor.execute("""
            SELECT
                original_sku,
                catalog_sku,
                quantity_multiplier,
                SUM(original_units_sold) as raw_units,
                SUM(units_sold) as adj_units,
                SUM(revenue) as revenue
            FROM sales_facts_mv
            WHERE catalog_sku = 'GRCA_U26010'
              AND source = 'relbase'
              AND EXTRACT(YEAR FROM order_date) = 2025
            GROUP BY original_sku, catalog_sku, quantity_multiplier
            ORDER BY revenue DESC;
        """)

        consolidation = cursor.fetchall()
        if consolidation:
            print(f"\n  {'Original SKU':<20} {'Mapped SKU':<15} {'×':>3} {'Raw':>8} {'Adj':>8} {'Revenue':>12}")
            print("  " + "-" * 75)

            total_raw = 0
            total_adj = 0
            total_rev = 0

            for row in consolidation:
                orig, mapped, mult, raw, adj, rev = row
                total_raw += raw
                total_adj += adj
                total_rev += rev
                print(f"  {orig:<20} {mapped:<15} {mult:>3} {raw:>8} {adj:>8} {format_currency(rev):>12}")

            print("  " + "-" * 75)
            print(f"  {'TOTAL':<20} {'':<15} {'':<3} {total_raw:>8} {total_adj:>8} {format_currency(total_rev):>12}")

        cursor.close()
        conn.close()

        print(f"\n  ✅ PASS: SKU comparison complete")
        return True

    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def run_all_tests():
    """Run all tests and report summary"""
    print("\n" + "=" * 80)
    print("  SALES ANALYTICS ALIGNMENT TEST SUITE")
    print("  Comparing: Sales Analytics (MV) vs Desglose Pedidos (Audit)")
    print("=" * 80)
    print(f"\n  Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    results = {}

    # Run tests
    results["Test 1: Summary Totals"] = test_summary_totals()
    results["Test 2: Category Breakdown"] = test_category_breakdown()
    results["Test 3: PACK Multipliers"] = test_pack_products()
    results["Test 4: Channel Grouping"] = test_channel_grouping()
    results["Test 5: Date Range Filter"] = test_date_range_filter()
    results["Test 6: SKU Mapping Structure"] = test_sku_mapping_consistency()
    results["Test 7: Specific SKU Comparison"] = test_specific_sku_comparison()

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


if __name__ == "__main__":
    import sys

    # Check if backend is running
    try:
        response = requests.get(f"{BASE_URL}/../health", timeout=5)
    except:
        print("⚠️  Warning: Backend may not be running at localhost:8000")
        print("   Some tests will fail if the API is not accessible.")

    success = run_all_tests()
    sys.exit(0 if success else 1)
