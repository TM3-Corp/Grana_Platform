#!/usr/bin/env python3
"""
Investigate GRBE unit calculation discrepancy

Problem: 8 master boxes showing 16,000 units (implies 2,000 units per box)
Expected: 8 × 10 = 80 units (based on product_catalog UI showing items_per_master_box=10)
"""

import psycopg2
from psycopg2.extras import RealDictCursor

# Session Pooler URL (IPv4 - works in WSL2)
DATABASE_URL = "postgresql://postgres.lypuvibmtxjaxmcmahxr:%24Ilofono1@aws-1-sa-east-1.pooler.supabase.com:6543/postgres"

def main():
    conn = psycopg2.connect(DATABASE_URL)
    cursor = conn.cursor(cursor_factory=RealDictCursor)

    print("=" * 80)
    print("INVESTIGATING GRBE UNIT CALCULATION DISCREPANCY")
    print("=" * 80)

    # 1. Check product_catalog for GRBE products
    print("\n1. PRODUCT_CATALOG TABLE - GRBE products:")
    print("-" * 80)
    cursor.execute("""
        SELECT
            sku,
            sku_master,
            product_name,
            category,
            units_per_display,
            units_per_master_box,
            items_per_master_box,
            is_master_sku,
            sku_primario
        FROM product_catalog
        WHERE sku LIKE 'GRBE%' OR sku_master LIKE 'GRBE%'
        ORDER BY sku
    """)
    rows = cursor.fetchall()
    for row in rows:
        print(f"\nSKU: {row['sku']}")
        print(f"  sku_master: {row['sku_master']}")
        print(f"  product_name: {row['product_name']}")
        print(f"  units_per_display: {row['units_per_display']}")
        print(f"  units_per_master_box: {row['units_per_master_box']}")
        print(f"  items_per_master_box: {row['items_per_master_box']}")
        print(f"  is_master_sku: {row['is_master_sku']}")
        print(f"  sku_primario: {row['sku_primario']}")

    # 2. Check sku_mappings for any GRBE mappings
    print("\n\n2. SKU_MAPPINGS TABLE - GRBE entries:")
    print("-" * 80)
    cursor.execute("""
        SELECT
            source_sku,
            target_sku,
            quantity_multiplier,
            source,
            description,
            is_active
        FROM sku_mappings
        WHERE source_sku LIKE '%GRBE%' OR target_sku LIKE '%GRBE%'
        ORDER BY source_sku
    """)
    rows = cursor.fetchall()
    if rows:
        for row in rows:
            print(f"\nSource: {row['source_sku']} → Target: {row['target_sku']}")
            print(f"  quantity_multiplier: {row['quantity_multiplier']}")
            print(f"  source: {row['source']}")
            print(f"  description: {row['description']}")
            print(f"  is_active: {row['is_active']}")
    else:
        print("No sku_mappings found for GRBE")

    # 3. Check the specific order item (external_id: 34489448)
    print("\n\n3. ORDER DATA - external_id 34489448:")
    print("-" * 80)
    cursor.execute("""
        SELECT
            o.external_id,
            o.order_date,
            o.source as order_source,
            oi.product_sku,
            oi.product_name,
            oi.quantity,
            oi.unit_price,
            oi.subtotal
        FROM orders o
        JOIN order_items oi ON oi.order_id = o.id
        WHERE o.external_id = '34489448'
    """)
    rows = cursor.fetchall()
    for row in rows:
        print(f"\nOrder: {row['external_id']} ({row['order_date']})")
        print(f"  product_sku: {row['product_sku']}")
        print(f"  product_name: {row['product_name']}")
        print(f"  quantity: {row['quantity']}")
        print(f"  unit_price: {row['unit_price']}")
        print(f"  subtotal: {row['subtotal']}")
        print(f"  order_source: {row['order_source']}")

    # 4. Check if GRBE_C02010 is in product_catalog as master SKU
    print("\n\n4. CHECKING GRBE_C02010 SPECIFICALLY:")
    print("-" * 80)
    cursor.execute("""
        SELECT
            sku,
            sku_master,
            product_name,
            units_per_display,
            units_per_master_box,
            items_per_master_box,
            is_master_sku
        FROM product_catalog
        WHERE sku = 'GRBE_C02010' OR sku_master = 'GRBE_C02010'
    """)
    rows = cursor.fetchall()
    if rows:
        for row in rows:
            print(f"Found GRBE_C02010:")
            print(f"  As SKU: {row['sku']}")
            print(f"  sku_master: {row['sku_master']}")
            print(f"  is_master_sku: {row['is_master_sku']}")
            print(f"  units_per_display: {row['units_per_display']}")
            print(f"  items_per_master_box: {row['items_per_master_box']}")
    else:
        print("GRBE_C02010 NOT FOUND in product_catalog")
        print("\nThis means the master SKU lookup will use items_per_master_box from the")
        print("product that has sku_master = 'GRBE_C02010'")

    # 5. Check the actual master SKU lookup path
    print("\n\n5. MASTER SKU LOOKUP PATH:")
    print("-" * 80)
    cursor.execute("""
        SELECT
            sku,
            sku_master,
            units_per_display,
            items_per_master_box,
            is_master_sku,
            product_name
        FROM product_catalog
        WHERE sku_master = 'GRBE_C02010'
    """)
    rows = cursor.fetchall()
    if rows:
        for row in rows:
            print(f"\nProduct with sku_master='GRBE_C02010':")
            print(f"  SKU: {row['sku']}")
            print(f"  product_name: {row['product_name']}")
            print(f"  units_per_display: {row['units_per_display']}")
            print(f"  items_per_master_box: {row['items_per_master_box']} ← THIS IS USED FOR CONVERSION")
    else:
        print("No product has sku_master='GRBE_C02010'")

    # 6. Check COLUMN STRUCTURE of product_catalog
    print("\n\n6. PRODUCT_CATALOG COLUMNS:")
    print("-" * 80)
    cursor.execute("""
        SELECT column_name, data_type
        FROM information_schema.columns
        WHERE table_name = 'product_catalog'
        ORDER BY ordinal_position
    """)
    for row in cursor.fetchall():
        print(f"  {row['column_name']}: {row['data_type']}")

    cursor.close()
    conn.close()

if __name__ == "__main__":
    main()
