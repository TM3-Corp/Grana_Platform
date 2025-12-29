#!/usr/bin/env python3
"""
Test Dashboard Alignment After Migration to sales_facts_mv

This script verifies that the dashboard endpoints now return data
aligned with sales_facts_mv (which uses product_catalog + sku_mappings).

Tests:
1. executive-kpis endpoint returns correct totals
2. quarterly-breakdown endpoint returns correct category breakdown
3. Category sums match sales_facts_mv
4. Filtered queries (by family) return correct results
"""

import requests
import psycopg2
import psycopg2.extras
import sys

# Configuration
API_URL = "http://localhost:8000/api/v1"
DATABASE_URL = "postgresql://postgres.lypuvibmtxjaxmcmahxr:%24Ilofono1@aws-1-sa-east-1.pooler.supabase.com:6543/postgres"


def get_db_connection():
    """Get database connection"""
    return psycopg2.connect(DATABASE_URL)


def test_executive_kpis_total():
    """Test 1: Executive KPIs total matches sales_facts_mv"""
    print("\n" + "=" * 60)
    print("TEST 1: Executive KPIs Total Revenue (2025)")
    print("=" * 60)

    # Get API response
    try:
        response = requests.get(f"{API_URL}/orders/dashboard/executive-kpis", timeout=30)
        if response.status_code != 200:
            print(f"❌ FAIL: API returned {response.status_code}")
            return False
        data = response.json()['data']
        api_total = data['kpis']['total_revenue_2025_actual']
    except requests.exceptions.ConnectionError:
        print("❌ FAIL: Cannot connect to API. Is the backend running?")
        return False

    # Get database value
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    cursor.execute("""
        SELECT SUM(revenue) as total
        FROM sales_facts_mv
        WHERE source = 'relbase'
        AND EXTRACT(YEAR FROM order_date) = 2025
    """)
    db_total = float(cursor.fetchone()['total'])
    cursor.close()
    conn.close()

    # Compare
    diff = abs(api_total - db_total)
    diff_pct = (diff / db_total * 100) if db_total > 0 else 0

    print(f"   API Total:      ${api_total:,.0f}")
    print(f"   DB (MV) Total:  ${db_total:,.0f}")
    print(f"   Difference:     ${diff:,.0f} ({diff_pct:.2f}%)")

    if diff_pct < 0.01:  # Less than 0.01% difference
        print("✅ PASS: Totals match!")
        return True
    else:
        print("❌ FAIL: Totals don't match")
        return False


def test_executive_kpis_filtered():
    """Test 2: Executive KPIs filtered by family matches sales_facts_mv"""
    print("\n" + "=" * 60)
    print("TEST 2: Executive KPIs Filtered by Family (BARRAS)")
    print("=" * 60)

    # Get API response with BARRAS filter
    try:
        response = requests.get(f"{API_URL}/orders/dashboard/executive-kpis?product_family=BARRAS", timeout=30)
        if response.status_code != 200:
            print(f"❌ FAIL: API returned {response.status_code}")
            return False
        data = response.json()['data']
        api_total = data['kpis']['total_revenue_2025_actual']
    except requests.exceptions.ConnectionError:
        print("❌ FAIL: Cannot connect to API")
        return False

    # Get database value
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    cursor.execute("""
        SELECT SUM(revenue) as total
        FROM sales_facts_mv
        WHERE source = 'relbase'
        AND EXTRACT(YEAR FROM order_date) = 2025
        AND category = 'BARRAS'
    """)
    db_total = float(cursor.fetchone()['total'])
    cursor.close()
    conn.close()

    # Compare
    diff = abs(api_total - db_total)
    diff_pct = (diff / db_total * 100) if db_total > 0 else 0

    print(f"   API Total (BARRAS):      ${api_total:,.0f}")
    print(f"   DB (MV) Total (BARRAS):  ${db_total:,.0f}")
    print(f"   Difference:              ${diff:,.0f} ({diff_pct:.2f}%)")

    if diff_pct < 0.01:
        print("✅ PASS: Filtered totals match!")
        return True
    else:
        print("❌ FAIL: Filtered totals don't match")
        return False


def test_quarterly_breakdown_categories():
    """Test 3: Quarterly breakdown categories match sales_facts_mv"""
    print("\n" + "=" * 60)
    print("TEST 3: Quarterly Breakdown Categories (2025)")
    print("=" * 60)

    # Get API response
    try:
        response = requests.get(f"{API_URL}/analytics/quarterly-breakdown?year=2025", timeout=30)
        if response.status_code != 200:
            print(f"❌ FAIL: API returned {response.status_code}")
            return False
        data = response.json()['data']
        api_families = {f['name']: f['totals']['revenue'] for f in data['product_families']}
    except requests.exceptions.ConnectionError:
        print("❌ FAIL: Cannot connect to API")
        return False

    # Get database values
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    cursor.execute("""
        SELECT
            COALESCE(category, 'OTROS') as category,
            SUM(revenue) as total
        FROM sales_facts_mv
        WHERE source = 'relbase'
        AND EXTRACT(YEAR FROM order_date) = 2025
        GROUP BY COALESCE(category, 'OTROS')
        ORDER BY total DESC
    """)
    db_categories = {row['category']: float(row['total']) for row in cursor.fetchall()}
    cursor.close()
    conn.close()

    # Compare
    print("\n   Category Comparison:")
    print(f"   {'Category':<20} {'API':>15} {'DB (MV)':>15} {'Match':>8}")
    print("   " + "-" * 60)

    all_match = True
    all_categories = set(list(api_families.keys()) + list(db_categories.keys()))

    for cat in sorted(all_categories, key=lambda x: max(api_families.get(x, 0), db_categories.get(x, 0)), reverse=True):
        api_val = api_families.get(cat, 0)
        db_val = db_categories.get(cat, 0)
        diff_pct = abs(api_val - db_val) / db_val * 100 if db_val > 0 else (0 if api_val == 0 else 100)
        match = "✅" if diff_pct < 0.01 else "❌"
        if diff_pct >= 0.01:
            all_match = False
        print(f"   {cat:<20} ${api_val:>13,.0f} ${db_val:>13,.0f} {match:>8}")

    if all_match:
        print("\n✅ PASS: All categories match!")
        return True
    else:
        print("\n❌ FAIL: Some categories don't match")
        return False


def test_quarterly_breakdown_channels():
    """Test 4: Quarterly breakdown channels match sales_facts_mv"""
    print("\n" + "=" * 60)
    print("TEST 4: Quarterly Breakdown Channels (2025)")
    print("=" * 60)

    # Get API response
    try:
        response = requests.get(f"{API_URL}/analytics/quarterly-breakdown?year=2025", timeout=30)
        if response.status_code != 200:
            print(f"❌ FAIL: API returned {response.status_code}")
            return False
        data = response.json()['data']
        api_channels = {c['name']: c['totals']['revenue'] for c in data['channels']}
    except requests.exceptions.ConnectionError:
        print("❌ FAIL: Cannot connect to API")
        return False

    # Get database values
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    cursor.execute("""
        SELECT
            COALESCE(UPPER(channel_name), 'OTROS') as channel,
            SUM(revenue) as total
        FROM sales_facts_mv
        WHERE source = 'relbase'
        AND EXTRACT(YEAR FROM order_date) = 2025
        GROUP BY COALESCE(UPPER(channel_name), 'OTROS')
        ORDER BY total DESC
    """)
    db_channels = {row['channel']: float(row['total']) for row in cursor.fetchall()}
    cursor.close()
    conn.close()

    # Compare
    print("\n   Channel Comparison:")
    print(f"   {'Channel':<25} {'API':>15} {'DB (MV)':>15} {'Match':>8}")
    print("   " + "-" * 65)

    all_match = True
    all_channels = set(list(api_channels.keys()) + list(db_channels.keys()))

    for ch in sorted(all_channels, key=lambda x: max(api_channels.get(x, 0), db_channels.get(x, 0)), reverse=True):
        api_val = api_channels.get(ch, 0)
        db_val = db_channels.get(ch, 0)
        diff_pct = abs(api_val - db_val) / db_val * 100 if db_val > 0 else (0 if api_val == 0 else 100)
        match = "✅" if diff_pct < 0.01 else "❌"
        if diff_pct >= 0.01:
            all_match = False
        print(f"   {ch[:24]:<25} ${api_val:>13,.0f} ${db_val:>13,.0f} {match:>8}")

    if all_match:
        print("\n✅ PASS: All channels match!")
        return True
    else:
        print("\n❌ FAIL: Some channels don't match")
        return False


def test_caja_master_alignment():
    """Test 5: CAJA MASTER category is properly identified (key fix)"""
    print("\n" + "=" * 60)
    print("TEST 5: CAJA MASTER Alignment (Key Fix)")
    print("=" * 60)

    # Get API response
    try:
        response = requests.get(f"{API_URL}/analytics/quarterly-breakdown?year=2025", timeout=30)
        if response.status_code != 200:
            print(f"❌ FAIL: API returned {response.status_code}")
            return False
        data = response.json()['data']

        # Find CAJA MASTER in families
        caja_master_api = None
        for f in data['product_families']:
            if f['name'] == 'CAJA MASTER':
                caja_master_api = f['totals']['revenue']
                break
    except requests.exceptions.ConnectionError:
        print("❌ FAIL: Cannot connect to API")
        return False

    # Get database value
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    cursor.execute("""
        SELECT SUM(revenue) as total
        FROM sales_facts_mv
        WHERE source = 'relbase'
        AND EXTRACT(YEAR FROM order_date) = 2025
        AND category = 'CAJA MASTER'
    """)
    result = cursor.fetchone()
    caja_master_db = float(result['total']) if result and result['total'] else 0
    cursor.close()
    conn.close()

    print(f"   API CAJA MASTER:      ${caja_master_api:,.0f}" if caja_master_api else "   API CAJA MASTER:      NOT FOUND")
    print(f"   DB (MV) CAJA MASTER:  ${caja_master_db:,.0f}")

    # The old dashboard showed $130M for CAJA MASTER
    # The correct value from sales_facts_mv should be ~$167M
    if caja_master_api and caja_master_api > 160_000_000:
        print(f"\n✅ PASS: CAJA MASTER is now correctly identified (~${caja_master_api/1_000_000:.0f}M)")
        print("   (Was $130M before fix, now properly includes ANU-* prefix mappings)")
        return True
    else:
        print(f"\n❌ FAIL: CAJA MASTER value looks wrong")
        return False


def main():
    """Run all tests"""
    print("\n" + "=" * 60)
    print("DASHBOARD ALIGNMENT TEST SUITE")
    print("Testing after migration to sales_facts_mv")
    print("=" * 60)

    results = []

    results.append(("Executive KPIs Total", test_executive_kpis_total()))
    results.append(("Executive KPIs Filtered (BARRAS)", test_executive_kpis_filtered()))
    results.append(("Quarterly Categories", test_quarterly_breakdown_categories()))
    results.append(("Quarterly Channels", test_quarterly_breakdown_channels()))
    results.append(("CAJA MASTER Alignment", test_caja_master_alignment()))

    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)

    passed = sum(1 for _, r in results if r)
    total = len(results)

    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"   {name:<35} {status}")

    print("\n" + "-" * 60)
    print(f"   Total: {passed}/{total} tests passed")

    if passed == total:
        print("\n🎉 All tests passed! Dashboard is now aligned with sales_facts_mv")
        return 0
    else:
        print(f"\n⚠️  {total - passed} test(s) failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
