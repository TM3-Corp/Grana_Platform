#!/usr/bin/env python3
"""Run migration 025 - Add Variety Pack Mappings"""

import psycopg2
import psycopg2.extras

DATABASE_URL = "postgresql://postgres.lypuvibmtxjaxmcmahxr:%24Ilofono1@aws-1-sa-east-1.pooler.supabase.com:6543/postgres"

def run_migration():
    conn = psycopg2.connect(DATABASE_URL)
    cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

    print("=" * 70)
    print("MIGRATION 025: Add Variety Pack Mappings")
    print("=" * 70)

    try:
        # Step 1: Add to product_catalog
        print("\n1. Adding variety packs to product_catalog...")
        cursor.execute("""
            INSERT INTO product_catalog (sku, product_name, category, is_active, created_at)
            VALUES
                ('PACKCRSURTIDO', 'Pack 4 Crackers Keto Surtidos', 'CRACKERS', TRUE, NOW()),
                ('PACKGRSURTIDA', 'Pack 4 Granolas Surtidas', 'GRANOLAS', TRUE, NOW()),
                ('PACKDIECIOCHO', 'Pack Dieciochero: 6 Productos + Despacho Gratis', 'OTROS', TRUE, NOW()),
                ('PACKNAVIDAD', 'Pack Navidad: 6 Productos', 'OTROS', TRUE, NOW())
            ON CONFLICT (sku) DO UPDATE SET
                product_name = EXCLUDED.product_name,
                category = EXCLUDED.category,
                is_active = TRUE,
                updated_at = NOW()
        """)
        print(f"   Affected rows: {cursor.rowcount}")

        # Step 2: Add identity mappings to sku_mappings
        print("\n2. Adding identity mappings to sku_mappings...")

        variety_packs = [
            ('PACKCRSURTIDO', 'exact', 'PACKCRSURTIDO', 1, 'Variety pack identity', 95, 90,
             'Pack 4 Crackers Surtidos - variety pack, maps to self'),
            ('PACKGRSURTIDA', 'exact', 'PACKGRSURTIDA', 1, 'Variety pack identity', 95, 90,
             'Pack 4 Granolas Surtidas - variety pack, maps to self'),
            ('PACKDIECIOCHO', 'exact', 'PACKDIECIOCHO', 1, 'Promotional pack identity', 95, 90,
             'Pack Dieciochero 6 productos - promotional bundle, maps to self'),
            ('PACKNAVIDAD', 'exact', 'PACKNAVIDAD', 1, 'Promotional pack identity', 95, 90,
             'Pack Navidad 6 productos - seasonal bundle, maps to self'),
        ]

        inserted = 0
        updated = 0
        for pack in variety_packs:
            source_pattern, pattern_type, target_sku, multiplier, rule_name, conf, prio, notes = pack

            # Check if exists
            cursor.execute("""
                SELECT id FROM sku_mappings
                WHERE source_pattern = %s AND pattern_type = 'exact'
            """, (source_pattern,))

            existing = cursor.fetchone()
            if existing:
                # Update existing
                cursor.execute("""
                    UPDATE sku_mappings
                    SET target_sku = %s, quantity_multiplier = %s, notes = %s,
                        is_active = TRUE, updated_at = NOW()
                    WHERE source_pattern = %s AND pattern_type = 'exact'
                """, (target_sku, multiplier, notes, source_pattern))
                updated += 1
            else:
                # Insert new
                cursor.execute("""
                    INSERT INTO sku_mappings
                    (source_pattern, pattern_type, target_sku, quantity_multiplier,
                     rule_name, confidence, priority, notes, is_active)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, TRUE)
                """, (source_pattern, pattern_type, target_sku, multiplier,
                      rule_name, conf, prio, notes))
                inserted += 1

        print(f"   Inserted: {inserted}, Updated: {updated}")

        # Step 3: Refresh materialized view
        print("\n3. Refreshing sales_facts_mv...")
        cursor.execute("REFRESH MATERIALIZED VIEW sales_facts_mv")
        print("   Done!")

        conn.commit()

        # Verification
        print("\n" + "=" * 70)
        print("VERIFICATION")
        print("=" * 70)

        print("\nproduct_catalog entries:")
        cursor.execute("""
            SELECT sku, product_name, category
            FROM product_catalog
            WHERE sku IN ('PACKCRSURTIDO', 'PACKGRSURTIDA', 'PACKDIECIOCHO', 'PACKNAVIDAD')
        """)
        for row in cursor.fetchall():
            print(f"   {row['sku']}: {row['product_name']} [{row['category']}]")

        print("\nsku_mappings entries:")
        cursor.execute("""
            SELECT source_pattern, target_sku, quantity_multiplier
            FROM sku_mappings
            WHERE source_pattern IN ('PACKCRSURTIDO', 'PACKGRSURTIDA', 'PACKDIECIOCHO', 'PACKNAVIDAD')
        """)
        for row in cursor.fetchall():
            print(f"   {row['source_pattern']} -> {row['target_sku']} (x{row['quantity_multiplier']})")

        # Check if now mapped in sales_facts_mv
        print("\nsales_facts_mv verification (2025 revenue):")
        cursor.execute("""
            SELECT
                original_sku,
                catalog_sku,
                category,
                match_type,
                SUM(revenue) as revenue
            FROM sales_facts_mv
            WHERE original_sku IN ('PACKCRSURTIDO', 'PACKGRSURTIDA', 'PACKDIECIOCHO', 'PACKNAVIDAD')
            AND EXTRACT(YEAR FROM order_date) = 2025
            GROUP BY original_sku, catalog_sku, category, match_type
            ORDER BY revenue DESC
        """)
        results = cursor.fetchall()
        if results:
            for row in results:
                print(f"   {row['original_sku']} -> {row['catalog_sku']} [{row['category']}] "
                      f"({row['match_type']}) = ${float(row['revenue']):,.0f}")
        else:
            print("   ⚠️ No data found yet - may need MV refresh")

        print("\n" + "=" * 70)
        print("MIGRATION 025 COMPLETE!")
        print("=" * 70)

    except Exception as e:
        conn.rollback()
        print(f"\n❌ ERROR: {e}")
        raise
    finally:
        cursor.close()
        conn.close()


if __name__ == "__main__":
    run_migration()
