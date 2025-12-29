#!/usr/bin/env python3
"""Check if variety packs exist in product_catalog"""

import psycopg2
import psycopg2.extras

DATABASE_URL = "postgresql://postgres.lypuvibmtxjaxmcmahxr:%24Ilofono1@aws-1-sa-east-1.pooler.supabase.com:6543/postgres"

def check():
    conn = psycopg2.connect(DATABASE_URL)
    cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

    skus = ['PACKDIECIOCHO', 'PACKCRSURTIDO', 'PACKGRSURTIDA', 'PACKNAVIDAD']

    print("=" * 80)
    print("CHECKING VARIETY PACKS IN PRODUCT_CATALOG")
    print("=" * 80)

    for sku in skus:
        cursor.execute("""
            SELECT sku, product_name, category, is_active
            FROM product_catalog
            WHERE sku = %s OR sku_master = %s
        """, (sku, sku))

        result = cursor.fetchone()
        if result:
            print(f"\n✅ {sku} found in product_catalog:")
            print(f"   SKU: {result['sku']}")
            print(f"   Name: {result['product_name']}")
            print(f"   Category: {result['category']}")
            print(f"   Active: {result['is_active']}")
        else:
            print(f"\n❌ {sku} NOT in product_catalog")

    # Check what category these would need
    print("\n" + "=" * 80)
    print("CATEGORY RECOMMENDATION")
    print("=" * 80)
    print("""
Based on product names:
- PACKDIECIOCHO: "Pack Dieciochero: 6 Productos" → PACK SURTIDO or PROMOCIONES
- PACKCRSURTIDO: "Pack 4 Crackers Keto Surtidos" → CRACKERS
- PACKGRSURTIDA: "Pack 4 Granolas Surtidas" → GRANOLAS
- PACKNAVIDAD: "Pack Navidad: 6 Productos" → PACK SURTIDO or PROMOCIONES

Recommendation:
1. Add these to product_catalog with category 'OTROS' (catch-all for variety packs)
2. Create sku_mappings entries pointing to themselves with multiplier=1
3. This ensures they're recognized by sales_facts_mv as mapped products
""")

    cursor.close()
    conn.close()


if __name__ == "__main__":
    check()
