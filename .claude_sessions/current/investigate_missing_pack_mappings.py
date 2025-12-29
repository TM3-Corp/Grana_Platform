#!/usr/bin/env python3
"""
Investigate Missing PACK Mappings

Identify the target SKUs and multipliers for:
- PACKDIECIOCHO
- PACKCRSURTIDO
- PACKGRSURTIDA
- PACKNAVIDAD
"""

import psycopg2
import psycopg2.extras

DATABASE_URL = "postgresql://postgres.lypuvibmtxjaxmcmahxr:%24Ilofono1@aws-1-sa-east-1.pooler.supabase.com:6543/postgres"

def investigate():
    conn = psycopg2.connect(DATABASE_URL)
    cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

    missing_skus = ['PACKDIECIOCHO', 'PACKCRSURTIDO', 'PACKGRSURTIDA', 'PACKNAVIDAD']

    print("=" * 80)
    print("INVESTIGATING MISSING PACK MAPPINGS")
    print("=" * 80)

    for sku in missing_skus:
        print(f"\n--- {sku} ---")

        # Get order item details
        cursor.execute("""
            SELECT
                oi.product_sku,
                oi.product_name,
                COUNT(DISTINCT o.id) as order_count,
                SUM(oi.quantity) as total_qty,
                SUM(oi.subtotal) as total_revenue
            FROM orders o
            JOIN order_items oi ON oi.order_id = o.id
            WHERE o.source = 'relbase'
            AND UPPER(oi.product_sku) = %s
            AND EXTRACT(YEAR FROM o.order_date) = 2025
            GROUP BY oi.product_sku, oi.product_name
        """, (sku,))

        result = cursor.fetchone()
        if result:
            print(f"  Name: {result['product_name']}")
            print(f"  Orders: {result['order_count']}")
            print(f"  Total Qty: {result['total_qty']}")
            print(f"  Revenue: ${float(result['total_revenue']):,.0f}")
        else:
            print("  No orders found in 2025")

        # Check if there's a non-PACK version in product_catalog
        base_sku = sku.replace('PACK', '')
        cursor.execute("""
            SELECT sku, product_name, category
            FROM product_catalog
            WHERE sku LIKE %s
            OR product_name ILIKE %s
            LIMIT 5
        """, (f'%{base_sku}%', f'%{base_sku}%'))

        matches = cursor.fetchall()
        if matches:
            print(f"\n  Potential catalog matches:")
            for m in matches:
                print(f"    - {m['sku']}: {m['product_name']} [{m['category']}]")

    # Now let's see what products table says about these
    print("\n" + "=" * 80)
    print("PRODUCTS TABLE INFO")
    print("=" * 80)

    cursor.execute("""
        SELECT sku, name, category
        FROM products
        WHERE sku IN ('PACKDIECIOCHO', 'PACKCRSURTIDO', 'PACKGRSURTIDA', 'PACKNAVIDAD')
    """)

    for row in cursor.fetchall():
        print(f"  {row['sku']}: {row['name']} [{row['category']}]")

    # Check existing PACK mappings for pattern
    print("\n" + "=" * 80)
    print("EXISTING PACK MAPPINGS (for pattern reference)")
    print("=" * 80)

    cursor.execute("""
        SELECT source_pattern, target_sku, quantity_multiplier, notes
        FROM sku_mappings
        WHERE source_pattern LIKE 'PACK%'
        AND is_active = TRUE
        ORDER BY source_pattern
    """)

    for row in cursor.fetchall():
        print(f"  {row['source_pattern']} → {row['target_sku']} (×{row['quantity_multiplier']}) | {row['notes']}")

    cursor.close()
    conn.close()


if __name__ == "__main__":
    investigate()
