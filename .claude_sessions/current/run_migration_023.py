#!/usr/bin/env python3
"""
Run Migration 023: Add quantity_multiplier support to sales_facts_mv
"""

import psycopg2

# Use Session Pooler URL (IPv4 compatible for WSL2)
DATABASE_URL = "postgresql://postgres.lypuvibmtxjaxmcmahxr:%24Ilofono1@aws-1-sa-east-1.pooler.supabase.com:6543/postgres"

def run_migration():
    """Execute migration 023"""

    migration_path = "/home/paul/projects/Grana/Grana_Platform/backend/migrations/023_add_quantity_multiplier_to_sales_mv.sql"

    print("=" * 60)
    print("Migration 023: Add quantity_multiplier to sales_facts_mv")
    print("=" * 60)

    try:
        # Read migration SQL
        with open(migration_path, 'r') as f:
            sql = f.read()

        # Connect to database
        conn = psycopg2.connect(DATABASE_URL)
        conn.autocommit = True
        cursor = conn.cursor()

        print("\n1. Dropping existing sales_facts_mv...")
        cursor.execute("DROP MATERIALIZED VIEW IF EXISTS sales_facts_mv CASCADE;")
        print("   Done!")

        print("\n2. Creating new sales_facts_mv with quantity_multiplier...")
        # Execute the full migration
        cursor.execute(sql)
        print("   Done!")

        print("\n3. Verifying PACK products mapping...")
        cursor.execute("""
            SELECT
                original_sku,
                catalog_sku,
                quantity_multiplier,
                original_units_sold,
                units_sold,
                match_type
            FROM sales_facts_mv
            WHERE original_sku LIKE 'PACK%'
            LIMIT 10;
        """)
        pack_results = cursor.fetchall()

        if pack_results:
            print(f"\n   Found {len(pack_results)} PACK products:")
            for row in pack_results:
                print(f"   {row[0]} → {row[1]} (×{row[2]}): {row[3]} raw → {row[4]} adjusted [{row[5]}]")
        else:
            print("   No PACK products found in current orders")

        print("\n4. Category totals with adjusted units (2025)...")
        cursor.execute("""
            SELECT
                COALESCE(category, 'UNMAPPED') as category,
                COUNT(*) as items,
                SUM(original_units_sold) as raw_units,
                SUM(units_sold) as adjusted_units,
                ROUND(SUM(revenue)::numeric, 0) as total_revenue
            FROM sales_facts_mv
            WHERE source = 'relbase'
              AND EXTRACT(YEAR FROM order_date) = 2025
            GROUP BY category
            ORDER BY total_revenue DESC;
        """)
        category_results = cursor.fetchall()

        print(f"\n   {'Category':<20} {'Items':>10} {'Raw Units':>12} {'Adj Units':>12} {'Revenue':>15}")
        print("   " + "-" * 75)
        for row in category_results:
            print(f"   {row[0]:<20} {row[1]:>10} {row[2]:>12} {row[3]:>12} ${row[4]:>14,.0f}")

        cursor.close()
        conn.close()

        print("\n" + "=" * 60)
        print("Migration 023 completed successfully!")
        print("=" * 60)

    except Exception as e:
        print(f"\nERROR: {e}")
        raise

if __name__ == "__main__":
    run_migration()
