#!/usr/bin/env python3
"""
Test Shopify Connection
Verify we can connect to Shopify and fetch data

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


async def test_connection():
    """Test Shopify connection"""
    print("="*60)
    print("🛍️  TESTING SHOPIFY CONNECTION")
    print("="*60)

    try:
        connector = ShopifyConnector()
        print(f"\n📝 Store: {connector.shop_name}")
        print(f"🔗 API URL: {connector.api_url}")

        # Test connection
        print("\n🔄 Testing connection...")
        result = await connector.test_connection()

        if result['success']:
            print(f"✅ Connection successful!")
            print(f"\nShop Info:")
            print(f"  • Name: {result['shop_name']}")
            print(f"  • Email: {result['email']}")
            print(f"  • Currency: {result['currency']}")
            print(f"  • URL: {result['url']}")
        else:
            print(f"❌ Connection failed: {result['error']}")
            return False

        # Fetch sample products
        print("\n🔄 Fetching products...")
        products_data = await connector.get_products(limit=5)
        products = products_data.get('products', {}).get('edges', [])

        print(f"✅ Found {len(products)} products")
        for edge in products[:3]:
            product = edge['node']
            print(f"\n  📦 {product['title']}")
            print(f"     Status: {product['status']}")
            variants = product.get('variants', {}).get('edges', [])
            print(f"     Variants: {len(variants)}")
            if variants:
                variant = variants[0]['node']
                print(f"     SKU: {variant.get('sku', 'No SKU')}")
                print(f"     Price: ${variant.get('price', 0)}")
                print(f"     Stock: {variant.get('inventoryQuantity', 0)} units")

        # Fetch sample orders
        print("\n🔄 Fetching recent orders...")
        orders_data = await connector.get_orders(limit=5)
        orders = orders_data.get('orders', {}).get('edges', [])

        print(f"✅ Found {len(orders)} recent orders")
        for edge in orders[:3]:
            order = edge['node']
            print(f"\n  🛒 Order {order['name']}")
            print(f"     Date: {order['createdAt']}")
            print(f"     Total: ${order['totalPriceSet']['shopMoney']['amount']} {order['totalPriceSet']['shopMoney']['currencyCode']}")
            print(f"     Status: {order['displayFinancialStatus']} / {order['displayFulfillmentStatus']}")

        # Test normalization
        if orders:
            print("\n🔄 Testing order normalization...")
            sample_order = orders[0]
            normalized = connector.normalize_order(sample_order)

            print(f"✅ Normalized order #{normalized['order_number']}")
            print(f"   Customer: {normalized['customer']['name'] if normalized['customer'] else 'Guest'}")
            print(f"   Total: ${normalized['total']}")
            print(f"   Items: {len(normalized['items'])}")
            for item in normalized['items'][:3]:
                print(f"     • {item['product_name']}: {item['quantity']} x ${item['unit_price']}")

        print("\n"+"="*60)
        print("✅ ALL SHOPIFY TESTS PASSED!")
        print("="*60)
        print("\n🎉 Shopify connector is ready for integration!")

        return True

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(test_connection())
    sys.exit(0 if success else 1)
