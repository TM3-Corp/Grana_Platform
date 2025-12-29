#!/usr/bin/env python3
"""
Verify Ventas por Línea de Productos alignment

Compares:
1. API response from /api/v1/analytics/quarterly-breakdown
2. Direct query to sales_facts_mv

Checks:
- Product family totals match
- Quarter definitions are correct (Q1=Jan-Mar, Q2=Apr-Jun, etc.)
- Units are calculated with quantity_multiplier
"""

import requests
import psycopg2
import psycopg2.extras

API_URL = "http://localhost:8000/api/v1"
DATABASE_URL = "postgresql://postgres.lypuvibmtxjaxmcmahxr:%24Ilofono1@aws-1-sa-east-1.pooler.supabase.com:6543/postgres"

def main():
    print("=" * 80)
    print("VENTAS POR LÍNEA DE PRODUCTOS - ALIGNMENT CHECK")
    print("=" * 80)

    # 1. Get API response
    print("\n1. Fetching API response...")
    try:
        response = requests.get(f"{API_URL}/analytics/quarterly-breakdown?year=2025", timeout=30)
        api_data = response.json()['data']
        print(f"   ✅ API returned {len(api_data['product_families'])} product families")
    except Exception as e:
        print(f"   ❌ API error: {e}")
        return

    # 2. Get database totals
    print("\n2. Querying sales_facts_mv directly...")
    conn = psycopg2.connect(DATABASE_URL)
    cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

    cursor.execute("""
        SELECT
            COALESCE(category, 'OTROS') as category,
            EXTRACT(QUARTER FROM order_date)::int as quarter,
            SUM(revenue) as revenue,
            SUM(units_sold) as units,
            COUNT(DISTINCT order_id) as orders
        FROM sales_facts_mv
        WHERE source = 'relbase'
        AND EXTRACT(YEAR FROM order_date) = 2025
        GROUP BY COALESCE(category, 'OTROS'), EXTRACT(QUARTER FROM order_date)
        ORDER BY category, quarter
    """)
    db_data = cursor.fetchall()
    print(f"   ✅ Database returned {len(db_data)} category-quarter combinations")

    # 3. Compare Product Family totals
    print("\n3. PRODUCT FAMILY COMPARISON (2025)")
    print("=" * 80)

    # Build DB totals by category
    db_by_category = {}
    for row in db_data:
        cat = row['category']
        if cat not in db_by_category:
            db_by_category[cat] = {'revenue': 0, 'units': 0, 'orders': 0, 'quarters': {}}
        db_by_category[cat]['revenue'] += float(row['revenue'])
        db_by_category[cat]['units'] += int(row['units'])
        db_by_category[cat]['orders'] += int(row['orders'])
        db_by_category[cat]['quarters'][f"Q{row['quarter']}"] = {
            'revenue': float(row['revenue']),
            'units': int(row['units']),
            'orders': int(row['orders'])
        }

    # Compare
    print(f"\n{'Category':<15} {'API Revenue':>15} {'DB Revenue':>15} {'Match':>8}")
    print("-" * 58)

    all_match = True
    for family in api_data['product_families']:
        name = family['name']
        api_revenue = family['totals']['revenue']
        db_revenue = db_by_category.get(name, {}).get('revenue', 0)

        match = abs(api_revenue - db_revenue) < 1  # Allow $1 rounding
        if not match:
            all_match = False

        status = "✅" if match else "❌"
        print(f"{name:<15} ${api_revenue:>13,.0f} ${db_revenue:>13,.0f} {status:>8}")

    # 4. Check quarter definitions
    print("\n4. QUARTER DEFINITIONS CHECK")
    print("=" * 80)

    cursor.execute("""
        SELECT
            EXTRACT(MONTH FROM order_date)::int as month,
            EXTRACT(QUARTER FROM order_date)::int as quarter,
            COUNT(*) as count
        FROM sales_facts_mv
        WHERE source = 'relbase'
        AND EXTRACT(YEAR FROM order_date) = 2025
        GROUP BY EXTRACT(MONTH FROM order_date), EXTRACT(QUARTER FROM order_date)
        ORDER BY month
    """)
    month_quarter_map = cursor.fetchall()

    print(f"\n{'Month':<10} {'Quarter':>10} {'Orders':>10}")
    print("-" * 35)

    expected_quarters = {
        1: 1, 2: 1, 3: 1,      # Q1: Jan-Mar
        4: 2, 5: 2, 6: 2,      # Q2: Apr-Jun
        7: 3, 8: 3, 9: 3,      # Q3: Jul-Sep
        10: 4, 11: 4, 12: 4    # Q4: Oct-Dec
    }

    quarters_correct = True
    for row in month_quarter_map:
        month = row['month']
        quarter = row['quarter']
        expected = expected_quarters[month]
        status = "✅" if quarter == expected else "❌"
        if quarter != expected:
            quarters_correct = False
        print(f"{month:<10} Q{quarter:>9} {row['count']:>10,} {status}")

    # 5. Check PACK multiplier is applied
    print("\n5. PACK QUANTITY MULTIPLIER CHECK")
    print("=" * 80)

    cursor.execute("""
        SELECT
            original_sku,
            catalog_sku,
            quantity_multiplier,
            SUM(original_units_sold) as raw_units,
            SUM(units_sold) as adjusted_units,
            SUM(revenue) as revenue
        FROM sales_facts_mv
        WHERE source = 'relbase'
        AND EXTRACT(YEAR FROM order_date) = 2025
        AND original_sku LIKE 'PACK%'
        AND quantity_multiplier > 1
        GROUP BY original_sku, catalog_sku, quantity_multiplier
        ORDER BY revenue DESC
        LIMIT 10
    """)
    pack_data = cursor.fetchall()

    print(f"\n{'Original SKU':<20} {'Mult':>5} {'Raw':>10} {'Adjusted':>10} {'Correct':>8}")
    print("-" * 63)

    packs_correct = True
    for row in pack_data:
        mult = row['quantity_multiplier']
        raw = row['raw_units']
        adj = row['adjusted_units']
        expected_adj = raw * mult
        correct = adj == expected_adj
        if not correct:
            packs_correct = False
        status = "✅" if correct else "❌"
        print(f"{row['original_sku']:<20} {mult:>5}x {raw:>10,} {adj:>10,} {status:>8}")

    cursor.close()
    conn.close()

    # Summary
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"   Product Family Alignment: {'✅ PASS' if all_match else '❌ FAIL'}")
    print(f"   Quarter Definitions:      {'✅ PASS' if quarters_correct else '❌ FAIL'}")
    print(f"   PACK Multipliers:         {'✅ PASS' if packs_correct else '❌ FAIL'}")

    if all_match and quarters_correct and packs_correct:
        print("\n🎉 All checks passed! Ventas por Línea de Productos is correctly aligned.")
    else:
        print("\n⚠️  Some checks failed - review issues above.")


if __name__ == "__main__":
    main()
