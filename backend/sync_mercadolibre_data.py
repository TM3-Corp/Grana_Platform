#!/usr/bin/env python3
"""
Sync MercadoLibre Data - Import products and orders from MercadoLibre

Author: TM3
Date: 2025-10-04
"""
import os
import sys
import asyncio
from pathlib import Path
from dotenv import load_dotenv

# Load environment
env_path = Path(__file__).parent / '.env'
load_dotenv(env_path)

from app.connectors.mercadolibre_connector import MercadoLibreConnector
from app.services.mercadolibre_sync_service import MercadoLibreSyncService


async def sync_all(days: int = 30):
    """Sync products and orders from MercadoLibre"""
    print("\n" + "="*60)
    print("🛒 SYNCING MERCADOLIBRE DATA TO DATABASE")
    print("="*60)

    try:
        # Initialize services
        connector = MercadoLibreConnector()
        database_url = os.getenv('DATABASE_URL')
        service = MercadoLibreSyncService(database_url)

        # Test connection first
        print("\n🔄 Testing MercadoLibre connection...")
        seller_info = await connector.get_seller_info()
        if not seller_info:
            print("❌ Connection failed")
            return False

        print(f"✅ Connected as {seller_info.get('nickname')} (ID: {seller_info.get('id')})")
        print(f"   Country: {seller_info.get('country_id')}")

        # Sync Products
        print("\n" + "="*60)
        print("📦 SYNCING PRODUCTS")
        print("="*60)

        products_result = await service.sync_products()

        print(f"\n📥 MercadoLibre Product Sync:")
        print(f"  ✅ Synced: {products_result.get('products_synced', 0)}")
        print(f"  ❌ Failed: {products_result.get('products_failed', 0)}")

        # Sync Orders
        print("\n" + "="*60)
        print(f"🛒 SYNCING ORDERS (Last {days} days)")
        print("="*60)

        orders_result = await service.sync_orders(days=days)

        print(f"\n📥 MercadoLibre Order Sync:")
        print(f"  ✅ Synced: {orders_result.get('orders_synced', 0)}")
        print(f"  📦 Total found: {orders_result.get('total_orders', 0)}")
        print(f"  ❌ Failed: {orders_result.get('orders_failed', 0)}")

        if orders_result.get('errors'):
            print(f"\n⚠️  Errors:")
            for error in orders_result['errors'][:5]:  # Show first 5 errors
                print(f"     Order {error.get('order')}: {error.get('error')}")

        # Summary
        print("\n" + "="*60)
        print("✅ SYNC COMPLETE!")
        print("="*60)

        # Show database stats
        print("\n" + "="*60)
        print("📊 DATABASE STATS")
        print("="*60)

        import psycopg2
        from psycopg2.extras import RealDictCursor

        conn = psycopg2.connect(database_url)
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        # Count total products
        cursor.execute("SELECT COUNT(*) as count FROM products WHERE source = 'mercadolibre'")
        total_products = cursor.fetchone()['count']

        # Count total orders
        cursor.execute("SELECT COUNT(*) as count FROM orders WHERE source = 'mercadolibre'")
        total_orders = cursor.fetchone()['count']

        # Count total customers
        cursor.execute("SELECT COUNT(*) as count FROM customers WHERE source = 'mercadolibre'")
        total_customers = cursor.fetchone()['count']

        # Get total revenue
        cursor.execute("""
            SELECT SUM(total) as revenue
            FROM orders
            WHERE source = 'mercadolibre'
        """)
        total_revenue = cursor.fetchone()['revenue'] or 0

        # Get recent orders
        cursor.execute("""
            SELECT order_number, total, order_date
            FROM orders
            WHERE source = 'mercadolibre'
            ORDER BY order_date DESC
            LIMIT 5
        """)
        recent_orders = cursor.fetchall()

        cursor.close()
        conn.close()

        print(f"\n📦 Total MercadoLibre Products in DB: {total_products}")
        print(f"🛒 Total MercadoLibre Orders in DB: {total_orders}")
        print(f"👥 Total MercadoLibre Customers in DB: {total_customers}")
        print(f"💰 Total Revenue: ${total_revenue:,.2f} CLP")

        if recent_orders:
            print(f"\n📋 Recent Orders:")
            for order in recent_orders:
                print(f"   • {order['order_number']:15} | ${order['total']:10,.2f} | {order['order_date']}")

        print("\n🎉 Success! MercadoLibre data is now in your database!")
        print("👉 You can now view this data in your dashboard at:")
        print("   • Products: http://localhost:3000/dashboard/products")
        print("   • Orders: http://localhost:3000/dashboard/orders")

        # Show multi-channel summary
        print("\n" + "="*60)
        print("🌟 MULTI-CHANNEL SUMMARY")
        print("="*60)

        conn = psycopg2.connect(database_url)
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        cursor.execute("""
            SELECT source, COUNT(*) as count
            FROM orders
            GROUP BY source
            ORDER BY count DESC
        """)
        orders_by_source = cursor.fetchall()

        cursor.execute("""
            SELECT source, SUM(total) as revenue
            FROM orders
            GROUP BY source
            ORDER BY revenue DESC
        """)
        revenue_by_source = cursor.fetchall()

        cursor.close()
        conn.close()

        if orders_by_source:
            print("\n📊 Orders by Platform:")
            for row in orders_by_source:
                print(f"   • {row['source']:15} : {row['count']:3} orders")

        if revenue_by_source:
            print("\n💰 Revenue by Platform:")
            for row in revenue_by_source:
                print(f"   • {row['source']:15} : ${row['revenue']:,.2f} CLP")

        return True

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Sync MercadoLibre data to database")
    parser.add_argument('--days', type=int, default=30, help='Number of days to sync orders (default: 30)')
    args = parser.parse_args()

    success = asyncio.run(sync_all(days=args.days))
    sys.exit(0 if success else 1)
