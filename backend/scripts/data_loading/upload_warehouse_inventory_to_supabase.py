#!/usr/bin/env python3
"""
Upload Warehouse Inventory to Supabase from JSON Data Lake

This script reads JSON files downloaded from Relbase and populates Supabase:
1. warehouses table (with external_id)
2. warehouse_stock table (with lot tracking)

Usage:
    python3 upload_warehouse_inventory_to_supabase.py [--data-dir /path/to/dir] [--dry-run] [--verbose]

Author: Claude Code
Date: 2025-11-18
"""
import os
import sys
import json
import argparse
from typing import Dict, List
from pathlib import Path
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

# Load environment variables from .env file (override system vars)
from dotenv import load_dotenv
load_dotenv(override=True)

from app.core.database import get_db_connection_dict

# ============================================================================
# Configuration
# ============================================================================

DEFAULT_DATA_DIR = '/tmp/relbase_data_lake'

# ============================================================================
# Upload Functions
# ============================================================================

def load_json_file(file_path: Path) -> Dict:
    """Load JSON file and return data"""
    print(f"📖 Loading: {file_path}")

    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    print(f"✅ Loaded {file_path.name}")
    return data


def upload_warehouses(cursor, warehouses_data: Dict, dry_run: bool = False, verbose: bool = False) -> Dict:
    """
    Upload warehouses from JSON to Supabase

    Args:
        cursor: Database cursor
        warehouses_data: Dictionary from warehouses.json
        dry_run: If True, don't execute updates
        verbose: Print detailed progress

    Returns:
        Statistics dictionary
    """
    print("\n" + "=" * 80)
    print("📍 PHASE 1: Upload Warehouses")
    print("=" * 80)

    warehouses = warehouses_data['warehouses']
    stats = {'created': 0, 'updated': 0, 'skipped': 0}

    for wh in warehouses:
        warehouse_id = str(wh['id'])
        name = wh['name']
        address = wh.get('address', '')
        enabled = wh.get('enabled', True)

        # Generate code from name (normalize, remove accents, remove numbers)
        import unicodedata
        import re
        # Remove accents
        name_normalized = ''.join(
            c for c in unicodedata.normalize('NFD', name)
            if unicodedata.category(c) != 'Mn'
        )
        # Convert to lowercase, replace spaces/hyphens with underscores
        code = name_normalized.lower().replace(' ', '_').replace('-', '_')
        # Remove numbers (constraint only allows [a-z_])
        code = re.sub(r'\d+', '', code)
        # Remove multiple consecutive underscores
        code = re.sub(r'_+', '_', code)
        # Remove leading/trailing underscores
        code = code.strip('_')

        # Check if warehouse exists by external_id
        cursor.execute("""
            SELECT id, code, name FROM warehouses
            WHERE external_id = %s AND source = 'relbase'
        """, (warehouse_id,))

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
                """, (name, address, enabled, warehouse_id))

            if verbose:
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
                        source = EXCLUDED.source,
                        updated_at = NOW()
                """, (code, name, address, warehouse_id, enabled))

            if verbose:
                print(f"   + Created: {name} (code: {code}, external_id: {warehouse_id})")
            stats['created'] += 1

    print(f"\n📊 Warehouses: {stats['created']} created, {stats['updated']} updated")
    return stats


def upload_warehouse_stock(cursor, stock_data: Dict, dry_run: bool = False, verbose: bool = False) -> Dict:
    """
    Upload warehouse stock with lots from JSON to Supabase

    Args:
        cursor: Database cursor
        stock_data: Dictionary from warehouse_stock_lots.json
        dry_run: If True, don't execute updates
        verbose: Print detailed progress

    Returns:
        Statistics dictionary
    """
    print("\n" + "=" * 80)
    print("📦 PHASE 2: Upload Warehouse Stock with Lots")
    print("=" * 80)

    stock_records = stock_data['stock_records']

    stats = {
        'lots_inserted': 0,
        'lots_updated': 0,
        'errors': 0
    }

    print(f"\n🔄 Processing {len(stock_records)} stock records...")

    for i, record in enumerate(stock_records, 1):
        product_external_id = str(record['product_id'])
        warehouse_external_id = str(record['warehouse_id'])
        product_sku = record.get('product_sku', 'Unknown')
        lots = record['lots']

        if verbose:
            print(f"\n[{i}/{len(stock_records)}] {product_sku} @ {record.get('warehouse_name', 'Unknown')}: {len(lots)} lots")

        # Get product_id from database
        cursor.execute("""
            SELECT id FROM products
            WHERE external_id = %s AND source = 'relbase'
        """, (product_external_id,))

        product_row = cursor.fetchone()
        if not product_row:
            if verbose:
                print(f"   ⚠️  Product not found in DB: external_id={product_external_id}")
            stats['errors'] += 1
            continue

        product_id_db = product_row['id']

        # Get warehouse_id from database
        cursor.execute("""
            SELECT id FROM warehouses
            WHERE external_id = %s AND source = 'relbase'
        """, (warehouse_external_id,))

        warehouse_row = cursor.fetchone()
        if not warehouse_row:
            if verbose:
                print(f"   ⚠️  Warehouse not found in DB: external_id={warehouse_external_id}")
            stats['errors'] += 1
            continue

        warehouse_id_db = warehouse_row['id']

        # Insert each lot
        for lot in lots:
            try:
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

                    if cursor.rowcount == 1:
                        stats['lots_inserted'] += 1
                    else:
                        stats['lots_updated'] += 1
                else:
                    # Dry run
                    stats['lots_inserted'] += 1

                if verbose:
                    print(f"   ✓ Lot {lot['lot_serial_number']}: {lot['stock']} units (exp: {lot.get('expiration_date', 'N/A')})")

            except Exception as e:
                stats['errors'] += 1
                print(f"   ❌ Error inserting lot {lot.get('lot_serial_number', 'unknown')}: {e}")

        # Progress update
        if i % 20 == 0:
            print(f"\n⏱️  Progress: {i}/{len(stock_records)} records | Lots: {stats['lots_inserted']} inserted, {stats['lots_updated']} updated")

    print(f"\n📊 Stock: {stats['lots_inserted']} lots inserted, {stats['lots_updated']} lots updated, {stats['errors']} errors")
    return stats


# ============================================================================
# Main Execution
# ============================================================================

def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description='Upload warehouse inventory to Supabase from JSON data lake'
    )
    parser.add_argument(
        '--data-dir',
        type=str,
        default=DEFAULT_DATA_DIR,
        help=f'Directory with JSON files (default: {DEFAULT_DATA_DIR})'
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

    # Get data directory
    data_dir = Path(args.data_dir)

    if not data_dir.exists():
        print(f"❌ ERROR: Data directory not found: {data_dir}")
        print(f"\n💡 First run: python3 download_warehouse_inventory_from_relbase.py")
        sys.exit(1)

    print("=" * 80)
    print("⬆️  UPLOAD WAREHOUSE INVENTORY TO SUPABASE")
    print("=" * 80)
    print(f"\n📁 Data directory: {data_dir}")

    if args.dry_run:
        print("\n⚠️  DRY RUN MODE - No changes will be made to database\n")

    try:
        # Load JSON files
        warehouses_file = data_dir / 'warehouses.json'
        stock_file = data_dir / 'warehouse_stock_lots.json'

        warehouses_data = load_json_file(warehouses_file)
        stock_data = load_json_file(stock_file)

        print(f"\n📊 Data loaded:")
        print(f"   • Warehouses: {warehouses_data['count']}")
        print(f"   • Stock records: {len(stock_data['stock_records'])}")
        print(f"   • Total lots: {stock_data['statistics']['total_lots']}")

        # Connect to database (using Session Pooler port 5432 for persistent connections)
        import psycopg2
        import psycopg2.extras

        DATABASE_URL = "postgresql://postgres.lypuvibmtxjaxmcmahxr:%24Ilofono1@aws-1-sa-east-1.pooler.supabase.com:5432/postgres"
        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

        # PHASE 1: Upload Warehouses
        warehouse_stats = upload_warehouses(cursor, warehouses_data, dry_run=args.dry_run, verbose=args.verbose)

        if not args.dry_run:
            conn.commit()
            print("✅ Warehouses committed to database")

        # PHASE 2: Upload Stock
        stock_stats = upload_warehouse_stock(cursor, stock_data, dry_run=args.dry_run, verbose=args.verbose)

        if not args.dry_run:
            conn.commit()
            print("✅ Warehouse stock committed to database")

        cursor.close()
        conn.close()

        # Create upload summary
        summary_file = data_dir / 'upload_summary.json'
        summary = {
            'upload_completed_at': datetime.now().isoformat(),
            'dry_run': args.dry_run,
            'statistics': {
                'warehouses': warehouse_stats,
                'stock': stock_stats
            }
        }

        with open(summary_file, 'w', encoding='utf-8') as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)

        print("\n" + "=" * 80)
        print("✅ UPLOAD COMPLETE" if not args.dry_run else "✅ DRY RUN COMPLETE")
        print("=" * 80)

        print(f"\n📊 Summary:")
        print(f"\n   Warehouses:")
        print(f"      • Created: {warehouse_stats['created']}")
        print(f"      • Updated: {warehouse_stats['updated']}")
        print(f"\n   Stock:")
        print(f"      • Lots inserted: {stock_stats['lots_inserted']}")
        print(f"      • Lots updated: {stock_stats['lots_updated']}")
        print(f"      • Errors: {stock_stats['errors']}")

        if args.dry_run:
            print(f"\n💡 To execute real upload, run without --dry-run flag")

    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
