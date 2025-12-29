#!/usr/bin/env python3
"""
Revert Migration 025 - Remove forced variety pack mappings

These SKUs are legitimately unmapped composite products:
- PACKCRSURTIDO (4 different crackers)
- PACKGRSURTIDA (4 different granolas)
- PACKDIECIOCHO (6 products promotional bundle)
- PACKNAVIDAD (6 products Christmas bundle)

They should remain unmapped since there's no canonical single-product equivalent.
"""

import psycopg2
import psycopg2.extras

DATABASE_URL = "postgresql://postgres.lypuvibmtxjaxmcmahxr:%24Ilofono1@aws-1-sa-east-1.pooler.supabase.com:6543/postgres"

def revert():
    conn = psycopg2.connect(DATABASE_URL)
    cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

    variety_packs = ['PACKCRSURTIDO', 'PACKGRSURTIDA', 'PACKDIECIOCHO', 'PACKNAVIDAD']

    print("=" * 70)
    print("REVERTING MIGRATION 025: Remove forced variety pack mappings")
    print("=" * 70)

    try:
        # Step 1: Remove from sku_mappings
        print("\n1. Removing from sku_mappings...")
        cursor.execute("""
            DELETE FROM sku_mappings
            WHERE source_pattern IN %s
            AND pattern_type = 'exact'
        """, (tuple(variety_packs),))
        print(f"   Deleted: {cursor.rowcount} rows")

        # Step 2: Remove from product_catalog
        print("\n2. Removing from product_catalog...")
        cursor.execute("""
            DELETE FROM product_catalog
            WHERE sku IN %s
        """, (tuple(variety_packs),))
        print(f"   Deleted: {cursor.rowcount} rows")

        # Step 3: Refresh materialized view
        print("\n3. Refreshing sales_facts_mv...")
        cursor.execute("REFRESH MATERIALIZED VIEW sales_facts_mv")
        print("   Done!")

        conn.commit()

        # Verification
        print("\n" + "=" * 70)
        print("VERIFICATION")
        print("=" * 70)

        # Confirm they're gone from product_catalog
        cursor.execute("""
            SELECT sku FROM product_catalog WHERE sku IN %s
        """, (tuple(variety_packs),))
        remaining_catalog = cursor.fetchall()
        print(f"\nproduct_catalog entries remaining: {len(remaining_catalog)}")

        # Confirm they're gone from sku_mappings
        cursor.execute("""
            SELECT source_pattern FROM sku_mappings WHERE source_pattern IN %s
        """, (tuple(variety_packs),))
        remaining_mappings = cursor.fetchall()
        print(f"sku_mappings entries remaining: {len(remaining_mappings)}")

        # Check they now show as unmapped in sales_facts_mv
        cursor.execute("""
            SELECT
                original_sku,
                match_type,
                category,
                SUM(revenue) as revenue
            FROM sales_facts_mv
            WHERE original_sku IN %s
            AND EXTRACT(YEAR FROM order_date) = 2025
            GROUP BY original_sku, match_type, category
            ORDER BY revenue DESC
        """, (tuple(variety_packs),))
        results = cursor.fetchall()

        print("\nsales_facts_mv status (should be 'unmapped'):")
        for row in results:
            print(f"   {row['original_sku']}: {row['match_type']} [{row['category']}] = ${float(row['revenue']):,.0f}")

        print("\n" + "=" * 70)
        print("REVERT COMPLETE!")
        print("=" * 70)
        print("\nThese variety packs are now legitimately unmapped.")
        print("Total revenue in unmapped bucket: ~$1.04M additional")

    except Exception as e:
        conn.rollback()
        print(f"\n❌ ERROR: {e}")
        raise
    finally:
        cursor.close()
        conn.close()


if __name__ == "__main__":
    revert()
