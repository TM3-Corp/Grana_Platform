#!/usr/bin/env python3
"""
Sync Warehouse Inventory from Relbase API

This script fetches warehouse inventory data from Relbase and populates:
1. warehouses table (with external_id from Relbase)
2. warehouse_stock table (with lot tracking)

Strategy:
- Fetch all warehouses from Relbase
- Fetch all products with external_id (Relbase products only)
- For each warehouse × product combination:
  - Fetch lot/serial numbers from Relbase
  - Store in warehouse_stock with lot_number and expiration_date

Usage:
    python3 sync_warehouse_inventory_from_relbase.py [--dry-run] [--verbose]

Author: Claude Code
Date: 2025-11-18
"""
import os
import sys
import json
import time
import argparse
from typing import Dict, List, Optional
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))

# Load environment variables from .env file (override system vars)
from dotenv import load_dotenv
load_dotenv(override=True)

import requests
from app.core.database import get_db_connection_dict

# ============================================================================
# Configuration
# ============================================================================

RELBASE_BASE_URL = "https://api.relbase.cl"
RELBASE_COMPANY_TOKEN = os.getenv('RELBASE_COMPANY_TOKEN')
RELBASE_USER_TOKEN = os.getenv('RELBASE_USER_TOKEN')

# Rate limiting: ~6 requests/second
RATE_LIMIT_DELAY = 0.17

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


def fetch_warehouses() -> List[Dict]:
    """Fetch all warehouses from Relbase API"""
    url = f"{RELBASE_BASE_URL}/api/v1/bodegas"
    headers = get_relbase_headers()

    print("📦 Fetching warehouses from Relbase...")
    response = requests.get(url, headers=headers, timeout=30)
    response.raise_for_status()

    data = response.json()
    warehouses = data.get('data', {}).get('warehouses', [])

    print(f"✅ Fetched {len(warehouses)} warehouses")
    return warehouses


def fetch_products() -> List[Dict]:
    """Fetch all products from Relbase API"""
    url = f"{RELBASE_BASE_URL}/api/v1/productos"
    headers = get_relbase_headers()

    print("📦 Fetching products from Relbase...")
    response = requests.get(url, headers=headers, timeout=30)
    response.raise_for_status()

    data = response.json()
    products = data.get('data', {}).get('products', [])

    print(f"✅ Fetched {len(products)} products")
    return products


def fetch_lot_serial_numbers(product_id: int, warehouse_id: int, verbose: bool = False) -> List[Dict]:
    """
    Fetch lot/serial numbers for a specific product in a specific warehouse

    Args:
        product_id: Relbase product ID
        warehouse_id: Relbase warehouse ID
        verbose: Print detailed progress

    Returns:
        List of lot/serial number records
    """
    url = f"{RELBASE_BASE_URL}/api/v1/productos/{product_id}/lotes_series/{warehouse_id}"
    headers = get_relbase_headers()

    try:
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()

        data = response.json()
        lots = data.get('data', {}).get('lot_serial_numbers', [])

        if verbose and lots:
            print(f"   └─ Product {product_id} @ Warehouse {warehouse_id}: {len(lots)} lots")

        return lots

    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 404:
            # No lots found for this combination (common, not an error)
            return []
        else:
            raise


# ============================================================================
# Database Sync Functions
# ============================================================================

def sync_warehouses(cursor, warehouses_from_api: List[Dict], dry_run: bool = False) -> Dict:
    """
    Sync warehouses from Relbase API to database

    Args:
        cursor: Database cursor
        warehouses_from_api: List of warehouses from Relbase API
        dry_run: If True, don't execute updates

    Returns:
        Statistics dictionary
    """
    print("\n" + "=" * 80)
    print("📍 PHASE 1: Sync Warehouses")
    print("=" * 80)

    stats = {'created': 0, 'updated': 0, 'skipped': 0}

    for wh in warehouses_from_api:
        warehouse_id = wh['id']
        name = wh['name']
        address = wh.get('address', '')
        enabled = wh.get('enabled', True)

        # Generate code from name (normalize)
        code = name.lower().replace(' ', '_').replace('-', '_')

        # Check if warehouse exists by external_id
        cursor.execute("""
            SELECT id, code, name FROM warehouses
            WHERE external_id = %s AND source = 'relbase'
        """, (str(warehouse_id),))

        existing = cursor.fetchone()

        if existing:
            # Update existing
            if not dry_run:
                cursor.execute("""
                    UPDATE warehouses
                    SET name = %s,
                        location = %s,
                        is_active = %s,
                        update_method = 'api',
                        updated_at = NOW()
                    WHERE external_id = %s AND source = 'relbase'
                """, (name, address, enabled, str(warehouse_id)))

            print(f"   ✓ Updated: {name} (external_id: {warehouse_id})")
            stats['updated'] += 1

        else:
            # Create new
            if not dry_run:
                cursor.execute("""
                    INSERT INTO warehouses (code, name, location, external_id, source, update_method, is_active)
                    VALUES (%s, %s, %s, %s, 'relbase', 'api', %s)
                    ON CONFLICT (code) DO UPDATE
                    SET external_id = EXCLUDED.external_id,
                        name = EXCLUDED.name,
                        location = EXCLUDED.location,
                        is_active = EXCLUDED.is_active,
                        updated_at = NOW()
                """, (code, name, address, str(warehouse_id), enabled))

            print(f"   + Created: {name} (code: {code}, external_id: {warehouse_id})")
            stats['created'] += 1

    print(f"\n📊 Warehouses: {stats['created']} created, {stats['updated']} updated")
    return stats


def get_products_with_external_id(cursor) -> List[Dict]:
    """Get all products that have external_id from Relbase"""
    cursor.execute("""
        SELECT id, external_id, sku, name
        FROM products
        WHERE external_id IS NOT NULL
        AND source = 'relbase'
        AND is_active = true
        ORDER BY id
    """)

    return cursor.fetchall()


def get_warehouses_from_db(cursor) -> List[Dict]:
    """Get all warehouses from database"""
    cursor.execute("""
        SELECT id, external_id, code, name
        FROM warehouses
        WHERE source = 'relbase'
        AND is_active = true
        ORDER BY id
    """)

    return cursor.fetchall()


def sync_warehouse_stock(
    cursor,
    products: List[Dict],
    warehouses: List[Dict],
    dry_run: bool = False,
    verbose: bool = False
) -> Dict:
    """
    Sync warehouse stock with lot tracking from Relbase API

    Args:
        cursor: Database cursor
        products: List of products with external_id
        warehouses: List of warehouses with external_id
        dry_run: If True, don't execute updates
        verbose: Print detailed progress

    Returns:
        Statistics dictionary
    """
    print("\n" + "=" * 80)
    print("📦 PHASE 2: Sync Warehouse Stock with Lot Tracking")
    print("=" * 80)

    stats = {
        'combinations_checked': 0,
        'lots_found': 0,
        'lots_inserted': 0,
        'errors': 0,
        'start_time': time.time()
    }

    total_combinations = len(products) * len(warehouses)
    print(f"\n🔍 Checking {total_combinations} combinations ({len(products)} products × {len(warehouses)} warehouses)")
    print(f"⏱️  Estimated time: ~{(total_combinations * RATE_LIMIT_DELAY) / 60:.1f} minutes\n")

    # Save results to JSON for inspection
    all_lots = []

    for i, product in enumerate(products, 1):
        product_id_db = product['id']
        product_external_id = product['external_id']
        product_sku = product['sku']

        print(f"\n[{i}/{len(products)}] Product: {product_sku} (external_id: {product_external_id})")

        for warehouse in warehouses:
            warehouse_id_db = warehouse['id']
            warehouse_external_id = warehouse['external_id']
            warehouse_name = warehouse['name']

            stats['combinations_checked'] += 1

            try:
                # Fetch lots from Relbase API
                lots = fetch_lot_serial_numbers(
                    product_id=int(product_external_id),
                    warehouse_id=int(warehouse_external_id),
                    verbose=verbose
                )

                if lots:
                    stats['lots_found'] += len(lots)

                    for lot in lots:
                        lot_data = {
                            'product_id_db': product_id_db,
                            'product_external_id': product_external_id,
                            'product_sku': product_sku,
                            'warehouse_id_db': warehouse_id_db,
                            'warehouse_external_id': warehouse_external_id,
                            'warehouse_name': warehouse_name,
                            'lot_id': lot['id'],
                            'lot_number': lot['lot_serial_number'],
                            'stock': lot['stock'],
                            'expiration_date': lot.get('expiration_date')
                        }

                        all_lots.append(lot_data)

                        if not dry_run:
                            # Insert/update warehouse_stock
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
                                VALUES (%s, %s, %s, %s, %s, NOW(), 'relbase_api')
                                ON CONFLICT (product_id, warehouse_id, lot_number)
                                DO UPDATE SET
                                    quantity = EXCLUDED.quantity,
                                    expiration_date = EXCLUDED.expiration_date,
                                    last_updated = NOW(),
                                    updated_by = 'relbase_api'
                            """, (
                                product_id_db,
                                warehouse_id_db,
                                lot['stock'],
                                lot['lot_serial_number'],
                                lot.get('expiration_date')
                            ))

                            stats['lots_inserted'] += 1

                # Rate limiting
                time.sleep(RATE_LIMIT_DELAY)

            except Exception as e:
                stats['errors'] += 1
                print(f"   ⚠️  Error fetching product {product_external_id} @ warehouse {warehouse_external_id}: {e}")

        # Progress update every 10 products
        if i % 10 == 0:
            elapsed = time.time() - stats['start_time']
            rate = stats['combinations_checked'] / elapsed
            remaining = (total_combinations - stats['combinations_checked']) / rate
            print(f"\n⏱️  Progress: {i}/{len(products)} products | {stats['combinations_checked']}/{total_combinations} combinations")
            print(f"   Lots found: {stats['lots_found']} | ETA: {remaining/60:.1f} min")

    # Save all lots to JSON file
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    json_file = f'/tmp/warehouse_stock_sync_{timestamp}.json'

    with open(json_file, 'w') as f:
        json.dump(all_lots, f, indent=2, default=str)

    print(f"\n💾 Saved {len(all_lots)} lot records to: {json_file}")

    elapsed_time = time.time() - stats['start_time']
    print(f"\n📊 Sync Stats:")
    print(f"   Combinations checked: {stats['combinations_checked']}")
    print(f"   Lots found: {stats['lots_found']}")
    print(f"   Lots inserted: {stats['lots_inserted']}")
    print(f"   Errors: {stats['errors']}")
    print(f"   Time elapsed: {elapsed_time/60:.1f} minutes")

    return stats


# ============================================================================
# Main Execution
# ============================================================================

def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description='Sync warehouse inventory from Relbase API'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be done without executing updates'
    )
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Show detailed progress'
    )

    args = parser.parse_args()

    print("=" * 80)
    print("🔄 RELBASE WAREHOUSE INVENTORY SYNC")
    print("=" * 80)

    if args.dry_run:
        print("\n⚠️  DRY RUN MODE - No changes will be made to database\n")

    try:
        # Connect to database
        conn = get_db_connection_dict()
        cursor = conn.cursor()

        # PHASE 1: Sync Warehouses
        warehouses_api = fetch_warehouses()
        warehouse_stats = sync_warehouses(cursor, warehouses_api, dry_run=args.dry_run)

        if not args.dry_run:
            conn.commit()

        # Get warehouses from DB (with external_id populated)
        warehouses_db = get_warehouses_from_db(cursor)
        print(f"\n✅ {len(warehouses_db)} warehouses ready in database")

        # Get products with external_id
        products_db = get_products_with_external_id(cursor)
        print(f"✅ {len(products_db)} products with external_id ready")

        # PHASE 2: Sync Stock with Lots
        stock_stats = sync_warehouse_stock(
            cursor,
            products_db,
            warehouses_db,
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

    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
