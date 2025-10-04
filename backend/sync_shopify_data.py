#!/usr/bin/env python3
"""
Sync Shopify Data - Import products and orders from Shopify

Author: TM3
Date: 2025-10-03
"""
import os
import sys
import asyncio
from pathlib import Path
from dotenv import load_dotenv

# Load environment
env_path = Path(__file__).parent / '.env'
load_dotenv(env_path)

from app.connectors.shopify_connector import ShopifyConnector
from app.services.order_processing_service import OrderProcessingService


async def sync_all():
    """Sync products and orders from Shopify"""
    print("\n" + "="*60)
    print("🛍️  SYNCING SHOPIFY DATA TO DATABASE")
    print("="*60)

    try:
        # Initialize services
        connector = ShopifyConnector()
        database_url = os.getenv('DATABASE_URL')
        processor = OrderProcessingService(database_url)

        # Test connection first
        print("\n🔄 Testing Shopify connection...")
        test_result = await connector.test_connection()
        if not test_result['success']:
            print(f"❌ Connection failed: {test_result.get('error')}")
            return False

        print(f"✅ Connected to {test_result['shop_name']}")

        # Sync Products
        print("\n" + "="*60)
        print("📦 SYNCING PRODUCTS")
        print("="*60)

        products_data = await connector.get_products(limit=50)
        products = products_data.get('products', {}).get('edges', [])

        print(f"\n📥 Found {len(products)} products in Shopify")

        synced_products = 0
        failed_products = 0

        for edge in products:
            product_node = edge['node']
            normalized_products = connector.normalize_product(product_node)

            for product in normalized_products:
                try:
                    result = processor.sync_product_from_external(product)
                    synced_products += 1
                    print(f"  ✅ {result['status']:8} | {product['sku']:20} | {product['name'][:40]}")
                except Exception as e:
                    failed_products += 1
                    print(f"  ❌ failed   | {product['sku']:20} | Error: {str(e)[:40]}")

        print(f"\n📊 Products: {synced_products} synced, {failed_products} failed")

        # Sync Orders
        print("\n" + "="*60)
        print("🛒 SYNCING ORDERS")
        print("="*60)

        orders_data = await connector.get_orders(limit=10)  # Reduced batch size to avoid timeout
        orders = orders_data.get('orders', {}).get('edges', [])

        print(f"\n📥 Found {len(orders)} orders in Shopify")

        synced_orders = 0
        failed_orders = 0
        skipped_orders = 0

        for edge in orders:
            order_node = edge['node']
            normalized_order = connector.normalize_order(order_node)

            try:
                result = processor.process_order(normalized_order)

                if result['success']:
                    if result['status'] == 'already_exists':
                        skipped_orders += 1
                        print(f"  ⏭️  skip     | {normalized_order['order_number']:10} | Already synced")
                    else:
                        synced_orders += 1
                        customer_name = normalized_order.get('customer', {}).get('name', 'Guest') if normalized_order.get('customer') else 'Guest'
                        print(f"  ✅ created  | {normalized_order['order_number']:10} | {customer_name[:25]:25} | ${normalized_order['total']}")

                        if result.get('warnings'):
                            print(f"     ⚠️  Unmapped SKUs: {', '.join(result['warnings'][:3])}")
                else:
                    failed_orders += 1
                    print(f"  ❌ failed   | {normalized_order['order_number']:10} | {result.get('message', 'Unknown error')}")

            except Exception as e:
                failed_orders += 1
                print(f"  ❌ failed   | {normalized_order['order_number']:10} | Error: {str(e)[:40]}")

        print(f"\n📊 Orders: {synced_orders} synced, {skipped_orders} skipped, {failed_orders} failed")

        # Summary
        print("\n" + "="*60)
        print("✅ SYNC COMPLETE!")
        print("="*60)
        print(f"\n📦 Products:")
        print(f"   • Synced: {synced_products}")
        print(f"   • Failed: {failed_products}")
        print(f"\n🛒 Orders:")
        print(f"   • Synced: {synced_orders}")
        print(f"   • Skipped (already exists): {skipped_orders}")
        print(f"   • Failed: {failed_orders}")

        # Show database stats
        print("\n" + "="*60)
        print("📊 DATABASE STATS")
        print("="*60)

        import psycopg2
        from psycopg2.extras import RealDictCursor

        conn = psycopg2.connect(database_url)
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        # Count total products
        cursor.execute("SELECT COUNT(*) as count FROM products WHERE source = 'shopify'")
        total_products = cursor.fetchone()['count']

        # Count total orders
        cursor.execute("SELECT COUNT(*) as count FROM orders WHERE source = 'shopify'")
        total_orders = cursor.fetchone()['count']

        # Count total customers
        cursor.execute("SELECT COUNT(*) as count FROM customers WHERE source = 'shopify'")
        total_customers = cursor.fetchone()['count']

        # Get recent orders
        cursor.execute("""
            SELECT order_number, total, order_date
            FROM orders
            WHERE source = 'shopify'
            ORDER BY order_date DESC
            LIMIT 5
        """)
        recent_orders = cursor.fetchall()

        cursor.close()
        conn.close()

        print(f"\n📦 Total Shopify Products in DB: {total_products}")
        print(f"🛒 Total Shopify Orders in DB: {total_orders}")
        print(f"👥 Total Shopify Customers in DB: {total_customers}")

        if recent_orders:
            print(f"\n📋 Recent Orders:")
            for order in recent_orders:
                print(f"   • {order['order_number']:10} | ${order['total']:10,.2f} | {order['order_date']}")

        print("\n🎉 Success! Shopify data is now in your database!")
        print("👉 You can now view this data in your dashboard")

        return True

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(sync_all())
    sys.exit(0 if success else 1)
