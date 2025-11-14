#!/usr/bin/env python3
"""
MercadoLibre Stock Sync - Production Script v2
Links ML stock to existing products by SELLER_SKU

This version properly maps ML items to existing products using SELLER_SKU
instead of creating duplicate product records.

Author: TM3
Date: 2025-11-14
"""
import os
import sys
import httpx
import psycopg2
from dotenv import load_dotenv
from datetime import datetime
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Configuration
DATABASE_URL = os.getenv('DATABASE_URL')
ML_ACCESS_TOKEN = os.getenv('ML_ACCESS_TOKEN')
ML_SELLER_ID = os.getenv('ML_SELLER_ID')

# Validate environment
if not all([DATABASE_URL, ML_ACCESS_TOKEN, ML_SELLER_ID]):
    logger.error("Missing required environment variables!")
    sys.exit(1)


def make_ml_request(endpoint, params=None):
    """Make authenticated request to ML API"""
    url = f"https://api.mercadolibre.com{endpoint}"
    headers = {
        'Authorization': f'Bearer {ML_ACCESS_TOKEN}',
        'Accept': 'application/json'
    }

    try:
        response = httpx.get(url, headers=headers, params=params, timeout=30.0)
        response.raise_for_status()
        return response.json()
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 401:
            logger.error("ML API authentication failed - token may be expired")
        raise
    except Exception as e:
        logger.error(f"ML API request failed: {e}")
        raise


def extract_seller_sku(item_data):
    """Extract SELLER_SKU from item attributes"""
    attributes = item_data.get('attributes', [])
    for attr in attributes:
        if attr.get('id') == 'SELLER_SKU':
            return attr.get('value_name')
    return None


def get_all_active_items():
    """Get all active item IDs"""
    logger.info("Fetching active items from MercadoLibre...")

    items_response = make_ml_request(
        f"/users/{ML_SELLER_ID}/items/search",
        {'status': 'active', 'limit': 50}
    )

    if not items_response:
        return []

    item_ids = items_response.get('results', [])
    total = items_response.get('paging', {}).get('total', 0)

    logger.info(f"Found {total} active items")
    return item_ids


def get_stock_for_user_product(user_product_id):
    """Get stock information for a User Product"""
    return make_ml_request(f"/user-products/{user_product_id}/stock")


def get_warehouse_id(conn, warehouse_code='mercadolibre'):
    """Get warehouse ID, create if doesn't exist"""
    cur = conn.cursor()

    cur.execute("SELECT id FROM warehouses WHERE code = %s", (warehouse_code,))
    result = cur.fetchone()

    if result:
        warehouse_id = result[0]
        logger.info(f"Using warehouse '{warehouse_code}' (ID: {warehouse_id})")
    else:
        cur.execute("""
            INSERT INTO warehouses (code, name, location, update_method, is_active)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING id
        """, (warehouse_code, 'Mercado Libre', 'MercadoLibre Fulfillment', 'api', True))

        warehouse_id = cur.fetchone()[0]
        conn.commit()
        logger.info(f"Created warehouse '{warehouse_code}' (ID: {warehouse_id})")

    cur.close()
    return warehouse_id


def find_product_by_seller_sku(conn, seller_sku):
    """Find product in database by SELLER_SKU"""
    cur = conn.cursor()

    cur.execute("""
        SELECT id, sku, name, source
        FROM products
        WHERE sku = %s
        AND is_active = true
        LIMIT 1
    """, (seller_sku,))

    result = cur.fetchone()
    cur.close()

    if result:
        return {'id': result[0], 'sku': result[1], 'name': result[2], 'source': result[3]}
    return None


def update_warehouse_stock(conn, product_id, warehouse_id, quantity):
    """Update stock for a product in a warehouse"""
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO warehouse_stock (product_id, warehouse_id, quantity, last_updated, updated_by)
        VALUES (%s, %s, %s, NOW(), 'mercadolibre_api')
        ON CONFLICT (product_id, warehouse_id)
        DO UPDATE SET
            quantity = EXCLUDED.quantity,
            last_updated = NOW(),
            updated_by = 'mercadolibre_api'
    """, (product_id, warehouse_id, quantity))

    conn.commit()
    cur.close()


def sync_ml_stock():
    """Main sync function"""
    start_time = datetime.now()
    logger.info("="* 80)
    logger.info("MERCADOLIBRE STOCK SYNC - START (v2)")
    logger.info("=" * 80)
    logger.info(f"Timestamp: {start_time}")
    logger.info(f"Seller ID: {ML_SELLER_ID}")

    try:
        # Connect to database
        logger.info("Connecting to database...")
        conn = psycopg2.connect(DATABASE_URL)
        logger.info("Database connected")

        try:
            # Get warehouse ID
            warehouse_id = get_warehouse_id(conn)

            # Get all active items
            item_ids = get_all_active_items()

            if not item_ids:
                logger.warning("No active items found")
                return

            logger.info(f"Processing {len(item_ids)} items...")

            # Track statistics
            stats = {
                'items_processed': 0,
                'stock_updated': 0,
                'products_not_found': 0,
                'no_seller_sku': 0,
                'user_products_seen': set(),
                'errors': 0
            }

            for i, item_id in enumerate(item_ids, 1):
                try:
                    # Get item details
                    item_details = make_ml_request(f"/items/{item_id}")
                    if not item_details:
                        stats['errors'] += 1
                        continue

                    title = item_details.get('title', 'Unknown')
                    user_product_id = item_details.get('user_product_id')

                    # Extract SELLER_SKU
                    seller_sku = extract_seller_sku(item_details)

                    if not user_product_id:
                        logger.warning(f"Item {item_id}: No user_product_id")
                        stats['errors'] += 1
                        continue

                    # Skip duplicates
                    if user_product_id in stats['user_products_seen']:
                        logger.debug(f"Item {item_id}: Already processed {user_product_id}")
                        continue

                    stats['user_products_seen'].add(user_product_id)

                    # Get stock
                    stock_data = get_stock_for_user_product(user_product_id)
                    if not stock_data:
                        stats['errors'] += 1
                        continue

                    # Calculate total stock
                    total_stock = sum(loc.get('quantity', 0) for loc in stock_data.get('locations', []))

                    logger.info(f"[{i}/{len(item_ids)}] {item_id}: {total_stock} units")

                    # If no SELLER_SKU, skip
                    if not seller_sku:
                        logger.warning(f"  No SELLER_SKU found")
                        stats['no_seller_sku'] += 1
                        continue

                    logger.info(f"  SELLER_SKU: {seller_sku}")

                    # Find product by SELLER_SKU
                    product = find_product_by_seller_sku(conn, seller_sku)

                    if product:
                        logger.info(f"  ✅ Found: {product['sku']} ({product['source']})")
                        update_warehouse_stock(conn, product['id'], warehouse_id, total_stock)
                        stats['stock_updated'] += 1
                    else:
                        logger.warning(f"  ⚠️  Product not found for SKU: {seller_sku}")
                        stats['products_not_found'] += 1

                    stats['items_processed'] += 1

                except Exception as e:
                    logger.error(f"Error processing {item_id}: {e}")
                    stats['errors'] += 1

            # Print summary
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()

            logger.info("=" * 80)
            logger.info("SYNC SUMMARY")
            logger.info("=" * 80)
            logger.info(f"Items processed: {stats['items_processed']}")
            logger.info(f"Unique user products: {len(stats['user_products_seen'])}")
            logger.info(f"Stock updated in DB: {stats['stock_updated']}")
            logger.info(f"Products not found: {stats['products_not_found']}")
            logger.info(f"No SELLER_SKU: {stats['no_seller_sku']}")
            logger.info(f"Errors: {stats['errors']}")
            logger.info(f"Duration: {duration:.2f} seconds")
            logger.info("=" * 80)

            # Exit with error if too many failures
            if stats['errors'] > stats['items_processed'] / 2:
                logger.error("More than 50% of items failed - exiting with error")
                sys.exit(1)

        finally:
            conn.close()
            logger.info("Database connection closed")

    except Exception as e:
        logger.error(f"Fatal error: {e}")
        raise


if __name__ == '__main__':
    try:
        sync_ml_stock()
        logger.info("✅ Sync completed successfully")
    except Exception as e:
        logger.error(f"❌ Sync failed: {e}")
        sys.exit(1)
