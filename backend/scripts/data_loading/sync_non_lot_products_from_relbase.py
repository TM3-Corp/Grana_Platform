#!/usr/bin/env python3
"""
Sync Non-Lot-Tracked Products from Relbase API

This script fetches inventory data for products that don't use lot tracking
from Relbase and populates the warehouse_stock table.

Key Difference from sync_warehouse_inventory_from_relbase.py:
- Uses /api/v1/productos/{id} endpoint to get inventories array
- NOT /api/v1/productos/{id}/lotes_series/{warehouse_id} (which returns empty for non-lot products)

How it works:
1. Query products WHERE external_id IS NOT NULL (optionally filter by category)
2. For each product: GET /api/v1/productos/{external_id}
3. Extract inventories array: [{ware_house_id: 5232, stock: 8100}, ...]
4. Map ware_house_id to our warehouse.id via external_id
5. Insert into warehouse_stock with lot_number = 'NO_LOT_TRACKING'

Usage:
    python3 sync_non_lot_products_from_relbase.py [--dry-run] [--verbose]
    python3 sync_non_lot_products_from_relbase.py --category ENVASES
    python3 sync_non_lot_products_from_relbase.py --category "CAJA MASTER"
    python3 sync_non_lot_products_from_relbase.py --all-categories

Author: Claude Code
Date: 2025-11-28
"""
import os
import sys
import json
import time
import argparse
from typing import Dict, List, Optional
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

# Load environment variables from .env file (override system vars)
from dotenv import load_dotenv
load_dotenv(override=True)

import requests
from app.core.database import get_db_connection_dict_with_retry

# ============================================================================
# Configuration
# ============================================================================

RELBASE_BASE_URL = "https://api.relbase.cl"
RELBASE_COMPANY_TOKEN = os.getenv('RELBASE_COMPANY_TOKEN')
RELBASE_USER_TOKEN = os.getenv('RELBASE_USER_TOKEN')

# Rate limiting: ~6 requests/second
RATE_LIMIT_DELAY = 0.17

# Special marker for products without lot tracking
NO_LOT_TRACKING = 'NO_LOT_TRACKING'

# ============================================================================
# Relbase API Functions
# ============================================================================

def get_relbase_headers() -> Dict[str, str]:
    """Get authentication headers for Relbase API"""
    return {
        'company': RELBASE_COMPANY_TOKEN,
        'authorization': RELBASE_USER_TOKEN,
        'Content-Type': 'application/json'
    }


def fetch_product_details(product_id: int, verbose: bool = False) -> Optional[Dict]:
    """
    Fetch complete product details from Relbase API

    This endpoint returns the 'inventories' array with stock per warehouse,
    which is the only way to get stock for non-lot-tracked products.

    Args:
        product_id: Relbase product ID (external_id in our database)
        verbose: Print detailed progress

    Returns:
        Product data dict or None if not found
    """
    url = f"{RELBASE_BASE_URL}/api/v1/productos/{product_id}"
    headers = get_relbase_headers()

    try:
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()

        data = response.json()
        product_data = data.get('data', {})

        if verbose:
            inventories = product_data.get('inventories', [])
            if inventories:
                total_stock = sum(inv.get('stock', 0) for inv in inventories)
                print(f"   ✓ {product_data.get('code', 'N/A')}: {len(inventories)} warehouses, {total_stock} total units")

        return product_data

    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 404:
            return None
        else:
            raise
    except requests.exceptions.RequestException as e:
        print(f"   ⚠️  API Error for product {product_id}: {e}")
        return None


# ============================================================================
# Database Functions
# ============================================================================

def get_products_for_sync(cursor, category: str = None, all_categories: bool = False) -> List[Dict]:
    """
    Get products that have external_id from Relbase for inventory sync.

    Args:
        cursor: Database cursor
        category: Specific category to filter (e.g., 'ENVASES', 'CAJA MASTER')
        all_categories: If True, get ALL products with external_id

    Returns:
        List of products to sync
    """
    if all_categories:
        # Get ALL products with external_id
        cursor.execute("""
            SELECT id, external_id, sku, name, category
            FROM products
            WHERE external_id IS NOT NULL
            AND source = 'relbase'
            AND is_active = true
            ORDER BY category, id
        """)
    elif category:
        # Filter by specific category
        cursor.execute("""
            SELECT id, external_id, sku, name, category
            FROM products
            WHERE external_id IS NOT NULL
            AND source = 'relbase'
            AND is_active = true
            AND UPPER(category) = UPPER(%s)
            ORDER BY id
        """, (category,))
    else:
        # Default: ENVASES only (backward compatible)
        cursor.execute("""
            SELECT id, external_id, sku, name, category
            FROM products
            WHERE external_id IS NOT NULL
            AND source = 'relbase'
            AND is_active = true
            AND UPPER(category) = 'ENVASES'
            ORDER BY id
        """)

    return cursor.fetchall()


def get_warehouse_mapping(cursor) -> Dict[str, int]:
    """
    Get mapping from Relbase warehouse_id (external_id) to our database warehouse.id

    Returns:
        Dict mapping external_id string -> database id
    """
    cursor.execute("""
        SELECT id, external_id, name
        FROM warehouses
        WHERE external_id IS NOT NULL
        AND source = 'relbase'
        AND is_active = true
    """)

    warehouses = cursor.fetchall()
    mapping = {}

    print("\n📍 Warehouse ID Mapping:")
    for wh in warehouses:
        mapping[str(wh['external_id'])] = wh['id']
        print(f"   {wh['external_id']} ({wh['name']}) → DB id {wh['id']}")

    return mapping


def clear_existing_no_lot_stock(cursor, product_ids: List[int], dry_run: bool = False) -> int:
    """
    Clear existing NO_LOT_TRACKING entries for products we're about to sync

    This ensures we don't have stale data from previous syncs.

    Args:
        cursor: Database cursor
        product_ids: List of product database IDs to clear
        dry_run: If True, don't execute

    Returns:
        Number of rows deleted
    """
    if not product_ids:
        return 0

    if not dry_run:
        cursor.execute("""
            DELETE FROM warehouse_stock
            WHERE product_id = ANY(%s)
            AND lot_number = %s
        """, (product_ids, NO_LOT_TRACKING))

        deleted = cursor.rowcount
    else:
        cursor.execute("""
            SELECT COUNT(*) as count
            FROM warehouse_stock
            WHERE product_id = ANY(%s)
            AND lot_number = %s
        """, (product_ids, NO_LOT_TRACKING))

        deleted = cursor.fetchone()['count']

    return deleted


def sync_inventories(
    cursor,
    products: List[Dict],
    warehouse_mapping: Dict[str, int],
    dry_run: bool = False,
    verbose: bool = False
) -> Dict:
    """
    Sync inventory from Relbase product details to warehouse_stock

    Args:
        cursor: Database cursor
        products: List of ENVASES products with external_id
        warehouse_mapping: Dict mapping Relbase warehouse_id -> DB warehouse.id
        dry_run: If True, don't execute updates
        verbose: Print detailed progress

    Returns:
        Statistics dictionary
    """
    print("\n" + "=" * 80)
    print("📦 SYNCING INVENTORY FROM RELBASE (Non-Lot-Tracked Products)")
    print("=" * 80)

    stats = {
        'products_processed': 0,
        'products_with_stock': 0,
        'stock_entries_inserted': 0,
        'warehouses_skipped': 0,
        'api_errors': 0,
        'start_time': time.time()
    }

    print(f"\n🔍 Processing {len(products)} ENVASES products")
    print(f"⏱️  Estimated time: ~{(len(products) * RATE_LIMIT_DELAY) / 60:.1f} minutes\n")

    # Collect all inventory data for JSON export
    all_inventory = []

    for i, product in enumerate(products, 1):
        product_id_db = product['id']
        product_external_id = product['external_id']
        product_sku = product['sku']
        product_name = product['name']

        if verbose:
            print(f"\n[{i}/{len(products)}] {product_sku}: {product_name}")

        stats['products_processed'] += 1

        # Fetch product details from Relbase API
        product_data = fetch_product_details(int(product_external_id), verbose=verbose)

        if not product_data:
            stats['api_errors'] += 1
            continue

        # Extract inventories array
        inventories = product_data.get('inventories', [])

        if not inventories:
            if verbose:
                print(f"   └─ No inventory data")
            continue

        stats['products_with_stock'] += 1

        for inv in inventories:
            ware_house_id = str(inv.get('ware_house_id'))
            stock = inv.get('stock', 0)

            # Skip zero stock
            if stock <= 0:
                continue

            # Map Relbase warehouse_id to our database id
            warehouse_id_db = warehouse_mapping.get(ware_house_id)

            if not warehouse_id_db:
                if verbose:
                    print(f"   ⚠️  Unknown warehouse {ware_house_id} (not in mapping)")
                stats['warehouses_skipped'] += 1
                continue

            # Record for JSON export
            inventory_record = {
                'product_id_db': product_id_db,
                'product_external_id': product_external_id,
                'product_sku': product_sku,
                'product_name': product_name,
                'warehouse_id_db': warehouse_id_db,
                'warehouse_external_id': ware_house_id,
                'quantity': stock,
                'lot_number': NO_LOT_TRACKING,
                'expiration_date': None
            }
            all_inventory.append(inventory_record)

            if not dry_run:
                cursor.execute("""
                    INSERT INTO warehouse_stock (
                        product_id,
                        warehouse_id,
                        quantity,
                        lot_number,
                        expiration_date,
                        last_updated,
                        updated_by
                    )
                    VALUES (%s, %s, %s, %s, NULL, NOW(), 'relbase_api_inventories')
                    ON CONFLICT (product_id, warehouse_id, lot_number)
                    DO UPDATE SET
                        quantity = EXCLUDED.quantity,
                        last_updated = NOW(),
                        updated_by = 'relbase_api_inventories'
                """, (
                    product_id_db,
                    warehouse_id_db,
                    stock,
                    NO_LOT_TRACKING
                ))

            stats['stock_entries_inserted'] += 1

            if verbose:
                print(f"   └─ Warehouse {ware_house_id}: {stock} units")

        # Rate limiting
        time.sleep(RATE_LIMIT_DELAY)

        # Progress update every 10 products
        if i % 10 == 0:
            elapsed = time.time() - stats['start_time']
            rate = stats['products_processed'] / elapsed if elapsed > 0 else 0
            remaining = (len(products) - i) / rate if rate > 0 else 0
            print(f"\n⏱️  Progress: {i}/{len(products)} products | Stock entries: {stats['stock_entries_inserted']} | ETA: {remaining/60:.1f} min")

    # Save all inventory to JSON file
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    json_file = f'/tmp/relbase_inventory_sync_{timestamp}.json'

    with open(json_file, 'w') as f:
        json.dump(all_inventory, f, indent=2, default=str)

    print(f"\n💾 Saved {len(all_inventory)} inventory records to: {json_file}")

    elapsed_time = time.time() - stats['start_time']
    print(f"\n📊 Sync Stats:")
    print(f"   Products processed: {stats['products_processed']}")
    print(f"   Products with stock: {stats['products_with_stock']}")
    print(f"   Stock entries inserted: {stats['stock_entries_inserted']}")
    print(f"   Warehouses skipped (not mapped): {stats['warehouses_skipped']}")
    print(f"   API errors: {stats['api_errors']}")
    print(f"   Time elapsed: {elapsed_time:.1f} seconds")

    return stats


# ============================================================================
# Main Execution
# ============================================================================

def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description='Sync non-lot-tracked products inventory from Relbase API'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be done without executing updates'
    )
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Show detailed progress'
    )
    parser.add_argument(
        '--category', '-c',
        type=str,
        help='Specific category to sync (e.g., ENVASES, "CAJA MASTER", GRANOLAS)'
    )
    parser.add_argument(
        '--all-categories',
        action='store_true',
        help='Sync ALL products with external_id (ignores --category)'
    )

    args = parser.parse_args()

    # Determine sync scope
    if args.all_categories:
        scope = "ALL CATEGORIES"
    elif args.category:
        scope = f"Category: {args.category.upper()}"
    else:
        scope = "Category: ENVASES (default)"

    print("=" * 80)
    print("🔄 RELBASE INVENTORY SYNC (Non-Lot-Tracked Products)")
    print(f"   Scope: {scope}")
    print("=" * 80)

    if args.dry_run:
        print("\n⚠️  DRY RUN MODE - No changes will be made to database\n")

    # Validate API credentials
    if not RELBASE_COMPANY_TOKEN or not RELBASE_USER_TOKEN:
        print("❌ ERROR: Missing Relbase API credentials")
        print("   Set RELBASE_COMPANY_TOKEN and RELBASE_USER_TOKEN in .env")
        sys.exit(1)

    try:
        # Connect to database
        print("\n📡 Connecting to database...")
        conn = get_db_connection_dict_with_retry()
        cursor = conn.cursor()
        print("✅ Connected")

        # Get warehouse mapping
        warehouse_mapping = get_warehouse_mapping(cursor)

        if not warehouse_mapping:
            print("\n❌ ERROR: No warehouses found with external_id")
            print("   Run sync_warehouse_inventory_from_relbase.py first to populate warehouses")
            sys.exit(1)

        # Get products based on category filter
        print(f"\n🔍 Finding products for sync ({scope})...")
        products = get_products_for_sync(
            cursor,
            category=args.category,
            all_categories=args.all_categories
        )
        print(f"✅ Found {len(products)} products with external_id")

        if not products:
            print("\n⚠️  No products found with external_id")
            print("   Ensure products have source='relbase' and external_id populated")
            sys.exit(0)

        # Clear existing NO_LOT_TRACKING entries
        product_ids = [p['id'] for p in products]
        deleted = clear_existing_no_lot_stock(cursor, product_ids, dry_run=args.dry_run)
        print(f"\n🧹 {'Would delete' if args.dry_run else 'Deleted'} {deleted} existing NO_LOT_TRACKING entries")

        if not args.dry_run:
            conn.commit()

        # Sync inventories
        stats = sync_inventories(
            cursor,
            products,
            warehouse_mapping,
            dry_run=args.dry_run,
            verbose=args.verbose
        )

        if not args.dry_run:
            conn.commit()
            print("\n✅ Changes committed to database")

        cursor.close()
        conn.close()

        print("\n" + "=" * 80)
        print("✅ SYNC COMPLETE")
        print("=" * 80)

        # Summary
        if stats['stock_entries_inserted'] > 0:
            print(f"\n📍 Inventory is now available in warehouse views!")
            print(f"   Check: /dashboard/warehouse-inventory/by-warehouse → MI BODEGA")

    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
