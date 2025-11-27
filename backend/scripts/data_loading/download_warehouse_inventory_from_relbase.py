#!/usr/bin/env python3
"""
Download Warehouse Inventory from Relbase API (Data Lake Strategy)

This script ONLY downloads data from Relbase and saves as JSON files.
No database modifications are made.

Strategy:
1. Download all warehouses → save JSON
2. Download all products → save JSON (optional, we already have them)
3. For each warehouse × product combination:
   - Download lot/serial numbers → save to master JSON
4. Create comprehensive data lake with all raw Relbase data

Later, a separate script will upload this data to Supabase.

Usage:
    python3 download_warehouse_inventory_from_relbase.py [--output-dir /path/to/dir] [--verbose]

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
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

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

# Default output directory
DEFAULT_OUTPUT_DIR = '/tmp/relbase_data_lake'

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


def fetch_products_from_relbase_api() -> List[Dict]:
    """Fetch all products from Relbase API"""
    url = f"{RELBASE_BASE_URL}/api/v1/productos"
    headers = get_relbase_headers()

    print("📦 Fetching products from Relbase API...")
    response = requests.get(url, headers=headers, timeout=30)
    response.raise_for_status()

    data = response.json()
    products = data.get('data', {}).get('products', [])

    print(f"✅ Fetched {len(products)} products from API")
    return products


def fetch_lot_serial_numbers(product_id: int, warehouse_id: int, verbose: bool = False) -> Optional[Dict]:
    """
    Fetch lot/serial numbers for a specific product in a specific warehouse

    Args:
        product_id: Relbase product ID
        warehouse_id: Relbase warehouse ID
        verbose: Print detailed progress

    Returns:
        Dictionary with response data or None if not found
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

        return {
            'product_id': product_id,
            'warehouse_id': warehouse_id,
            'lots': lots,
            'fetched_at': datetime.now().isoformat()
        }

    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 404:
            # No lots found for this combination (common, not an error)
            if verbose:
                print(f"   └─ Product {product_id} @ Warehouse {warehouse_id}: No lots")
            return None
        else:
            raise


def get_products_with_external_id_from_db(cursor) -> List[Dict]:
    """Get all products that have external_id from Relbase (from our DB)"""
    cursor.execute("""
        SELECT id, external_id, sku, name
        FROM products
        WHERE external_id IS NOT NULL
        AND source = 'relbase'
        AND is_active = true
        ORDER BY id
    """)

    return cursor.fetchall()


# ============================================================================
# Download Functions
# ============================================================================

def download_warehouses(output_dir: Path) -> Dict:
    """
    Download all warehouses from Relbase and save as JSON

    Returns:
        Dictionary with warehouse data and metadata
    """
    print("\n" + "=" * 80)
    print("📍 PHASE 1: Download Warehouses")
    print("=" * 80)

    warehouses = fetch_warehouses()

    # Save to JSON
    output_file = output_dir / 'warehouses.json'

    data = {
        'source': 'relbase',
        'endpoint': '/api/v1/bodegas',
        'fetched_at': datetime.now().isoformat(),
        'count': len(warehouses),
        'warehouses': warehouses
    }

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print(f"💾 Saved {len(warehouses)} warehouses to: {output_file}")

    return data


def download_products_from_api(output_dir: Path) -> Dict:
    """
    Download all products from Relbase API and save as JSON

    Returns:
        Dictionary with product data and metadata
    """
    print("\n" + "=" * 80)
    print("📦 PHASE 2: Download Products from Relbase API")
    print("=" * 80)

    products = fetch_products_from_relbase_api()

    # Save to JSON
    output_file = output_dir / 'products_from_api.json'

    data = {
        'source': 'relbase',
        'endpoint': '/api/v1/productos',
        'fetched_at': datetime.now().isoformat(),
        'count': len(products),
        'products': products
    }

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print(f"💾 Saved {len(products)} products to: {output_file}")

    return data


def download_warehouse_stock_lots(
    output_dir: Path,
    warehouses: List[Dict],
    products_db: List[Dict],
    verbose: bool = False
) -> Dict:
    """
    Download lot/serial numbers for all warehouse × product combinations

    Args:
        output_dir: Directory to save JSON files
        warehouses: List of warehouses from Relbase
        products_db: List of products from our database (with external_id)
        verbose: Print detailed progress

    Returns:
        Dictionary with download statistics
    """
    print("\n" + "=" * 80)
    print("🔍 PHASE 3: Download Warehouse Stock with Lots")
    print("=" * 80)

    stats = {
        'combinations_checked': 0,
        'combinations_with_lots': 0,
        'total_lots': 0,
        'errors': 0,
        'start_time': time.time()
    }

    total_combinations = len(products_db) * len(warehouses)
    print(f"\n🔍 Downloading {total_combinations} combinations ({len(products_db)} products × {len(warehouses)} warehouses)")
    print(f"⏱️  Estimated time: ~{(total_combinations * RATE_LIMIT_DELAY) / 60:.1f} minutes\n")

    # Master list of all stock records
    all_stock_records = []

    for i, product in enumerate(products_db, 1):
        product_external_id = product['external_id']
        product_sku = product['sku']
        product_name = product['name']

        print(f"\n[{i}/{len(products_db)}] Product: {product_sku} (external_id: {product_external_id})")

        for warehouse in warehouses:
            warehouse_id = warehouse['id']
            warehouse_name = warehouse['name']

            stats['combinations_checked'] += 1

            try:
                # Fetch lots from Relbase API
                result = fetch_lot_serial_numbers(
                    product_id=int(product_external_id),
                    warehouse_id=warehouse_id,
                    verbose=verbose
                )

                if result and result['lots']:
                    stats['combinations_with_lots'] += 1
                    stats['total_lots'] += len(result['lots'])

                    # Add metadata
                    result['product_sku'] = product_sku
                    result['product_name'] = product_name
                    result['warehouse_name'] = warehouse_name

                    all_stock_records.append(result)

                # Rate limiting
                time.sleep(RATE_LIMIT_DELAY)

            except Exception as e:
                stats['errors'] += 1
                print(f"   ⚠️  Error: {e}")

        # Progress update every 10 products
        if i % 10 == 0:
            elapsed = time.time() - stats['start_time']
            rate = stats['combinations_checked'] / elapsed if elapsed > 0 else 0
            remaining = (total_combinations - stats['combinations_checked']) / rate if rate > 0 else 0

            print(f"\n⏱️  Progress: {i}/{len(products_db)} products | {stats['combinations_checked']}/{total_combinations} combinations")
            print(f"   Found: {stats['combinations_with_lots']} with stock | {stats['total_lots']} total lots | ETA: {remaining/60:.1f} min")

    # Save master stock file
    output_file = output_dir / 'warehouse_stock_lots.json'

    master_data = {
        'source': 'relbase',
        'endpoint': '/api/v1/productos/{product_id}/lotes_series/{warehouse_id}',
        'fetched_at': datetime.now().isoformat(),
        'statistics': {
            'combinations_checked': stats['combinations_checked'],
            'combinations_with_lots': stats['combinations_with_lots'],
            'total_lots': stats['total_lots'],
            'errors': stats['errors'],
            'elapsed_minutes': (time.time() - stats['start_time']) / 60
        },
        'stock_records': all_stock_records
    }

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(master_data, f, indent=2, ensure_ascii=False, default=str)

    print(f"\n💾 Saved {len(all_stock_records)} stock records ({stats['total_lots']} lots) to: {output_file}")

    return stats


# ============================================================================
# Main Execution
# ============================================================================

def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description='Download warehouse inventory from Relbase API as JSON data lake'
    )
    parser.add_argument(
        '--output-dir',
        type=str,
        default=DEFAULT_OUTPUT_DIR,
        help=f'Directory to save JSON files (default: {DEFAULT_OUTPUT_DIR})'
    )
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Show detailed progress'
    )
    parser.add_argument(
        '--skip-products',
        action='store_true',
        help='Skip downloading products from API (we already have them in DB)'
    )

    args = parser.parse_args()

    # Create output directory
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 80)
    print("🌊 RELBASE DATA LAKE DOWNLOAD")
    print("=" * 80)
    print(f"\n📁 Output directory: {output_dir}")

    try:
        # Connect to database (only to get products with external_id)
        conn = get_db_connection_dict()
        cursor = conn.cursor()

        # PHASE 1: Download Warehouses
        warehouses_data = download_warehouses(output_dir)
        warehouses = warehouses_data['warehouses']

        # PHASE 2: Download Products (optional)
        if not args.skip_products:
            products_api_data = download_products_from_api(output_dir)

        # Get products from our database (those with external_id)
        print("\n📊 Getting products from database (with external_id)...")
        products_db = get_products_with_external_id_from_db(cursor)
        print(f"✅ Found {len(products_db)} products in DB with Relbase external_id")

        # PHASE 3: Download Warehouse Stock with Lots
        stock_stats = download_warehouse_stock_lots(
            output_dir,
            warehouses,
            products_db,
            verbose=args.verbose
        )

        cursor.close()
        conn.close()

        # Create summary
        summary_file = output_dir / 'download_summary.json'
        summary = {
            'download_completed_at': datetime.now().isoformat(),
            'files_created': [
                'warehouses.json',
                'products_from_api.json' if not args.skip_products else None,
                'warehouse_stock_lots.json'
            ],
            'statistics': {
                'warehouses_count': len(warehouses),
                'products_in_db': len(products_db),
                'combinations_checked': stock_stats['combinations_checked'],
                'combinations_with_lots': stock_stats['combinations_with_lots'],
                'total_lots_found': stock_stats['total_lots'],
                'errors': stock_stats['errors']
            }
        }

        with open(summary_file, 'w', encoding='utf-8') as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)

        print("\n" + "=" * 80)
        print("✅ DOWNLOAD COMPLETE - DATA LAKE READY")
        print("=" * 80)
        print(f"\n📁 All files saved to: {output_dir}")
        print("\n📊 Summary:")
        print(f"   • Warehouses: {len(warehouses)}")
        print(f"   • Products (in DB): {len(products_db)}")
        print(f"   • Combinations checked: {stock_stats['combinations_checked']}")
        print(f"   • Combinations with stock: {stock_stats['combinations_with_lots']}")
        print(f"   • Total lots: {stock_stats['total_lots']}")
        print(f"\n💡 Next step: Run upload script to populate Supabase from these JSON files")

    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
