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
  - Fetch lot/serial numbers from Relbase (with retry on failure)
  - Store in warehouse_stock with lot_number and expiration_date

Features:
- Retry logic with exponential backoff for failed requests
- Periodic DB commits to prevent connection timeout
- Failed request tracking with retry at end
- Pagination handling for API responses

Usage:
    python3 sync_warehouse_inventory_from_relbase.py [--dry-run] [--verbose]

Author: Claude Code
Date: 2025-11-18
Updated: 2025-12-28 (added retry logic)
"""
import os
import sys
import json
import time
import argparse
from typing import Dict, List, Optional, Tuple
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

# Load environment variables from .env file (override system vars)
from dotenv import load_dotenv
load_dotenv(override=True)

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from app.core.database import get_db_connection_dict

# ============================================================================
# Configuration
# ============================================================================

RELBASE_BASE_URL = "https://api.relbase.cl"
RELBASE_COMPANY_TOKEN = os.getenv('RELBASE_COMPANY_TOKEN')
RELBASE_USER_TOKEN = os.getenv('RELBASE_USER_TOKEN')

# Rate limiting: ~4 requests/second (slightly slower for reliability)
RATE_LIMIT_DELAY = 0.25

# Retry configuration
MAX_RETRIES = 5
RETRY_BACKOFF_FACTOR = 2  # Exponential backoff: 1s, 2s, 4s, 8s, 16s
INITIAL_RETRY_DELAY = 1.0

# DB commit frequency (every N products)
COMMIT_FREQUENCY = 20

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


def fetch_lot_serial_numbers_with_retry(
    product_id: int,
    warehouse_id: int,
    verbose: bool = False,
    max_retries: int = MAX_RETRIES
) -> Tuple[List[Dict], bool]:
    """
    Fetch lot/serial numbers for a specific product in a specific warehouse
    WITH retry logic and exponential backoff.

    Args:
        product_id: Relbase product ID
        warehouse_id: Relbase warehouse ID
        verbose: Print detailed progress
        max_retries: Maximum number of retry attempts

    Returns:
        Tuple of (list of lot/serial number records, success boolean)
    """
    url = f"{RELBASE_BASE_URL}/api/v1/productos/{product_id}/lotes_series/{warehouse_id}"
    headers = get_relbase_headers()

    last_error = None

    for attempt in range(max_retries + 1):
        try:
            # Increase timeout with each retry
            timeout = 30 + (attempt * 10)  # 30s, 40s, 50s, 60s, 70s, 80s

            response = requests.get(url, headers=headers, timeout=timeout)
            response.raise_for_status()

            data = response.json()
            lots = data.get('data', {}).get('lot_serial_numbers', [])

            # Check for pagination (in case API paginates results)
            pagination = data.get('data', {}).get('pagination', {})
            if pagination:
                total_pages = pagination.get('total_pages', 1)
                current_page = pagination.get('current_page', 1)
                if total_pages > 1:
                    print(f"   ⚠️  Pagination detected: page {current_page}/{total_pages}")
                    # Fetch remaining pages
                    all_lots = lots.copy()
                    for page in range(2, total_pages + 1):
                        page_url = f"{url}?page={page}"
                        page_response = requests.get(page_url, headers=headers, timeout=timeout)
                        page_response.raise_for_status()
                        page_data = page_response.json()
                        page_lots = page_data.get('data', {}).get('lot_serial_numbers', [])
                        all_lots.extend(page_lots)
                        time.sleep(RATE_LIMIT_DELAY)
                    lots = all_lots

            if verbose and lots:
                print(f"   └─ Product {product_id} @ Warehouse {warehouse_id}: {len(lots)} lots")

            return lots, True

        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                # No lots found for this combination (common, not an error)
                return [], True
            else:
                last_error = e

        except (requests.exceptions.ConnectionError,
                requests.exceptions.Timeout,
                requests.exceptions.RequestException) as e:
            last_error = e

            if attempt < max_retries:
                # Exponential backoff
                delay = INITIAL_RETRY_DELAY * (RETRY_BACKOFF_FACTOR ** attempt)
                if verbose or attempt >= 2:
                    print(f"   🔄 Retry {attempt + 1}/{max_retries} in {delay:.1f}s... ({type(e).__name__})")
                time.sleep(delay)
            else:
                # All retries exhausted
                return [], False

    # Should not reach here, but just in case
    return [], False


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
    conn,
    cursor,
    products: List[Dict],
    warehouses: List[Dict],
    dry_run: bool = False,
    verbose: bool = False
) -> Dict:
    """
    Sync warehouse stock with lot tracking from Relbase API
    WITH retry logic and periodic commits.

    Args:
        conn: Database connection (for commits)
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
    print(f"🔄 Retry config: {MAX_RETRIES} retries with exponential backoff")
    print(f"💾 DB commit every {COMMIT_FREQUENCY} products")

    stats = {
        'combinations_checked': 0,
        'lots_found': 0,
        'lots_inserted': 0,
        'retries_succeeded': 0,
        'permanent_failures': 0,
        'start_time': time.time()
    }

    # Track failed combinations for final retry pass
    failed_combinations = []

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

            # Fetch lots from Relbase API WITH RETRY
            lots, success = fetch_lot_serial_numbers_with_retry(
                product_id=int(product_external_id),
                warehouse_id=int(warehouse_external_id),
                verbose=verbose
            )

            if not success:
                # Track for later retry
                failed_combinations.append({
                    'product': product,
                    'warehouse': warehouse
                })
                print(f"   ❌ Failed after {MAX_RETRIES} retries: {product_sku} @ {warehouse_name}")
                continue

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

        # Periodic commit to prevent connection timeout
        if i % COMMIT_FREQUENCY == 0 and not dry_run:
            conn.commit()
            print(f"   💾 Committed changes (checkpoint at product {i})")

        # Progress update every 10 products
        if i % 10 == 0:
            elapsed = time.time() - stats['start_time']
            rate = stats['combinations_checked'] / elapsed if elapsed > 0 else 1
            remaining = (total_combinations - stats['combinations_checked']) / rate if rate > 0 else 0
            print(f"\n⏱️  Progress: {i}/{len(products)} products | {stats['combinations_checked']}/{total_combinations} combinations")
            print(f"   Lots found: {stats['lots_found']} | Failed: {len(failed_combinations)} | ETA: {remaining/60:.1f} min")

    # Final commit before retry phase
    if not dry_run:
        conn.commit()
        print("\n💾 Committed all changes before retry phase")

    # =========================================================================
    # RETRY PHASE: Re-attempt failed combinations with extended timeouts
    # =========================================================================
    if failed_combinations:
        print("\n" + "=" * 80)
        print(f"🔄 PHASE 2b: Retrying {len(failed_combinations)} failed combinations")
        print("=" * 80)
        print("   (Using extended timeouts and longer delays)")

        # Wait a bit before retry phase to let API recover
        print("   ⏳ Waiting 30 seconds before retry phase...")
        time.sleep(30)

        still_failed = []

        for idx, combo in enumerate(failed_combinations, 1):
            product = combo['product']
            warehouse = combo['warehouse']

            product_id_db = product['id']
            product_external_id = product['external_id']
            product_sku = product['sku']
            warehouse_id_db = warehouse['id']
            warehouse_external_id = warehouse['external_id']
            warehouse_name = warehouse['name']

            print(f"\n   [{idx}/{len(failed_combinations)}] Retrying: {product_sku} @ {warehouse_name}")

            # Retry with more attempts and longer delays
            lots, success = fetch_lot_serial_numbers_with_retry(
                product_id=int(product_external_id),
                warehouse_id=int(warehouse_external_id),
                verbose=True,
                max_retries=MAX_RETRIES + 3  # Extra retries for failed ones
            )

            if success:
                stats['retries_succeeded'] += 1
                print(f"   ✅ Retry succeeded!")

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
            else:
                still_failed.append(combo)
                stats['permanent_failures'] += 1
                print(f"   ❌ Permanently failed")

            # Longer delay between retries
            time.sleep(RATE_LIMIT_DELAY * 2)

        # Final commit after retries
        if not dry_run:
            conn.commit()

        # Report on permanent failures
        if still_failed:
            print(f"\n⚠️  {len(still_failed)} combinations permanently failed:")
            for combo in still_failed[:10]:  # Show first 10
                print(f"   - {combo['product']['sku']} @ {combo['warehouse']['name']}")
            if len(still_failed) > 10:
                print(f"   ... and {len(still_failed) - 10} more")

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
    print(f"   Lots inserted/updated: {stats['lots_inserted']}")
    print(f"   Retries succeeded: {stats['retries_succeeded']}")
    print(f"   Permanent failures: {stats['permanent_failures']}")
    print(f"   Success rate: {((stats['combinations_checked'] - stats['permanent_failures']) / stats['combinations_checked'] * 100):.1f}%")
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

        # PHASE 2: Sync Stock with Lots (with retry logic)
        stock_stats = sync_warehouse_stock(
            conn,  # Pass connection for periodic commits
            cursor,
            products_db,
            warehouses_db,
            dry_run=args.dry_run,
            verbose=args.verbose
        )

        # Final commit handled inside sync_warehouse_stock
        print("\n✅ All changes committed to database")

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
