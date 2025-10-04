#!/usr/bin/env python3
"""
Test Products API directly to see detailed errors
"""
import os
from dotenv import load_dotenv
import psycopg2
from psycopg2.extras import RealDictCursor

load_dotenv()

def test_products_query():
    """Test the products query directly"""
    database_url = os.getenv("DATABASE_URL")

    try:
        conn = psycopg2.connect(database_url)
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        # Test simple count
        print("Testing simple count...")
        cursor.execute("SELECT COUNT(*) as total FROM products")
        result = cursor.fetchone()
        print(f"✅ Total products: {result['total']}")

        # Test with filters
        print("\nTesting filtered query...")
        conditions = []
        params = []
        where_clause = " AND ".join(conditions) if conditions else "1=1"

        cursor.execute(f"""
            SELECT COUNT(*) as total
            FROM products
            WHERE {where_clause}
        """, params)
        total = cursor.fetchone()['total']
        print(f"✅ Filtered count: {total}")

        # Test full query
        print("\nTesting full query...")
        cursor.execute(f"""
            SELECT
                id, external_id, source, sku, name, description,
                category, brand, unit,
                units_per_display, displays_per_box, boxes_per_pallet,
                display_name, box_name, pallet_name,
                cost_price, sale_price, current_stock, min_stock,
                is_active, created_at, updated_at
            FROM products
            WHERE {where_clause}
            ORDER BY name
            LIMIT 5 OFFSET 0
        """, params)

        products = cursor.fetchall()
        print(f"✅ Got {len(products)} products")

        for product in products:
            print(f"  - {product['sku']}: {product['name']}")

        cursor.close()
        conn.close()

        print("\n✅ All tests passed!")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_products_query()
