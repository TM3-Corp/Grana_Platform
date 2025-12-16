#!/usr/bin/env python3
"""
Categorize NULL Category Products from product_catalog Table

This script assigns categories to products with NULL category by matching
against the product_catalog table using SKU patterns.

Matching Strategy (in order):
1. Direct match: product.sku → product_catalog.sku
2. Master box match: product.sku → product_catalog.sku_master
3. _EM suffix extraction: XXXX_U04010_EM → XXXX_U04010 → product_catalog.sku
4. _NR suffix extraction: XXXX_U04010_NR → XXXX_U04010 → product_catalog.sku
5. ANU- prefix extraction: ANU-BACM_U04010 → BACM_U04010 → product_catalog.sku

NO CSV dependencies - uses product_catalog table only.

Usage:
    python3 categorize_null_products.py [--dry-run] [--verbose]

Author: Claude Code
Date: 2025-12-01
"""
import os
import sys
import re
import argparse
from typing import Dict, List, Optional, Tuple
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

# Load environment variables from .env file (override system vars)
from dotenv import load_dotenv
load_dotenv(override=True)

from app.core.database import get_db_connection_dict_with_retry

# ============================================================================
# SKU Pattern Extraction Functions
# ============================================================================

def extract_base_sku(sku: str) -> List[str]:
    """
    Extract possible base SKUs from a given SKU.

    Returns a list of potential base SKUs to try matching, in order of preference.

    Examples:
        BACM_U04010_EM → ['BACM_U04010_EM', 'BACM_U04010']
        BACM_U04010_NR → ['BACM_U04010_NR', 'BACM_U04010']
        ANU-BACM_U04010 → ['ANU-BACM_U04010', 'BACM_U04010']
        ANU-3322808180 → ['ANU-3322808180'] (no extraction possible)
        BACM_U04010 → ['BACM_U04010']
    """
    candidates = [sku]  # Always try the original first

    # Pattern 1: Remove _EM suffix (Spanish/special variant)
    if sku.endswith('_EM'):
        base = sku[:-3]
        if base not in candidates:
            candidates.append(base)

    # Pattern 2: Remove _NR suffix (another variant)
    if sku.endswith('_NR'):
        base = sku[:-3]
        if base not in candidates:
            candidates.append(base)

    # Pattern 3: Remove ANU- prefix (legacy/anulado code)
    if sku.startswith('ANU-'):
        base = sku[4:]  # Remove 'ANU-'
        if base not in candidates:
            candidates.append(base)

        # Also try removing suffixes from ANU- codes
        if base.endswith('_EM'):
            base2 = base[:-3]
            if base2 not in candidates:
                candidates.append(base2)
        if base.endswith('_NR'):
            base2 = base[:-3]
            if base2 not in candidates:
                candidates.append(base2)

    return candidates


def is_valid_sku_pattern(sku: str) -> bool:
    """
    Check if SKU follows Grana's standard pattern: XXXX_UYYYYY or XXXX_CYYYYY

    Valid patterns:
        BACM_U04010 (4-letter base + underscore + type + digits)
        GRCA_C02010 (master box)

    Invalid patterns:
        ANU-3322808180 (just numbers after ANU-)
        ALIANZA (no underscore/structure)
    """
    # Standard pattern: 4 letters + underscore + U/C + digits
    pattern = r'^[A-Z]{4}_[UC]\d{5}$'
    return bool(re.match(pattern, sku))


# ============================================================================
# Database Functions
# ============================================================================

def get_null_category_products(cursor) -> List[Dict]:
    """Get all products with NULL category that are active"""
    cursor.execute("""
        SELECT id, sku, name, source, external_id, is_active
        FROM products
        WHERE (category IS NULL OR category = '')
        AND is_active = true
        ORDER BY source, sku
    """)
    return cursor.fetchall()


def get_product_catalog_lookup(cursor) -> Tuple[Dict[str, Dict], Dict[str, Dict]]:
    """
    Build lookup dictionaries from product_catalog table.

    Returns:
        (sku_lookup, sku_master_lookup)
        - sku_lookup: {sku: {category, brand, base_code, product_name}}
        - sku_master_lookup: {sku_master: {category, brand, base_code, product_name}}
    """
    cursor.execute("""
        SELECT sku, sku_master, category, brand, base_code, product_name
        FROM product_catalog
        WHERE is_active = true
    """)

    sku_lookup = {}
    sku_master_lookup = {}

    for row in cursor.fetchall():
        catalog_data = {
            'category': row['category'],
            'brand': row['brand'],
            'base_code': row['base_code'],
            'product_name': row['product_name']
        }

        if row['sku']:
            sku_lookup[row['sku']] = catalog_data

        if row['sku_master']:
            sku_master_lookup[row['sku_master']] = catalog_data

    return sku_lookup, sku_master_lookup


def find_category_match(
    product_sku: str,
    sku_lookup: Dict[str, Dict],
    sku_master_lookup: Dict[str, Dict]
) -> Optional[Tuple[str, str, str]]:
    """
    Find category match for a product SKU.

    Args:
        product_sku: The product SKU to match
        sku_lookup: Dictionary of SKU → catalog data
        sku_master_lookup: Dictionary of sku_master → catalog data

    Returns:
        Tuple of (category, match_type, matched_sku) or None if no match
    """
    candidates = extract_base_sku(product_sku)

    for candidate in candidates:
        # Try direct SKU match
        if candidate in sku_lookup:
            return (
                sku_lookup[candidate]['category'],
                'direct_sku',
                candidate
            )

        # Try master box SKU match
        if candidate in sku_master_lookup:
            return (
                sku_master_lookup[candidate]['category'],
                'master_sku',
                candidate
            )

    return None


# ============================================================================
# Main Categorization Logic
# ============================================================================

def categorize_products(
    cursor,
    products: List[Dict],
    sku_lookup: Dict[str, Dict],
    sku_master_lookup: Dict[str, Dict],
    dry_run: bool = False,
    verbose: bool = False
) -> Dict:
    """
    Categorize products by matching against product_catalog.

    Returns statistics dictionary.
    """
    stats = {
        'total': len(products),
        'matched': 0,
        'unmatched': 0,
        'by_match_type': {
            'direct_sku': 0,
            'master_sku': 0
        },
        'by_source': {},
        'unmatched_products': []
    }

    print("\n" + "=" * 80)
    print("📦 CATEGORIZING NULL CATEGORY PRODUCTS")
    print("=" * 80)
    print(f"\n🔍 Processing {len(products)} products with NULL category\n")

    for i, product in enumerate(products, 1):
        product_id = product['id']
        product_sku = product['sku']
        product_name = product['name']
        source = product['source']

        # Track by source
        if source not in stats['by_source']:
            stats['by_source'][source] = {'matched': 0, 'unmatched': 0}

        # Try to find match
        match = find_category_match(product_sku, sku_lookup, sku_master_lookup)

        if match:
            category, match_type, matched_sku = match
            stats['matched'] += 1
            stats['by_match_type'][match_type] += 1
            stats['by_source'][source]['matched'] += 1

            if verbose:
                print(f"  ✓ [{i}/{len(products)}] {product_sku} → {category} (via {match_type}: {matched_sku})")

            # Update the product
            if not dry_run:
                cursor.execute("""
                    UPDATE products
                    SET category = %s, updated_at = NOW()
                    WHERE id = %s
                """, (category, product_id))
        else:
            stats['unmatched'] += 1
            stats['by_source'][source]['unmatched'] += 1
            stats['unmatched_products'].append({
                'id': product_id,
                'sku': product_sku,
                'name': product_name,
                'source': source
            })

            if verbose:
                print(f"  ✗ [{i}/{len(products)}] {product_sku} → NO MATCH")

        # Progress every 50 products
        if i % 50 == 0 and not verbose:
            print(f"  Progress: {i}/{len(products)} ({stats['matched']} matched, {stats['unmatched']} unmatched)")

    return stats


def print_report(stats: Dict, dry_run: bool):
    """Print detailed categorization report"""
    print("\n" + "=" * 80)
    print("📊 CATEGORIZATION REPORT")
    print("=" * 80)

    print(f"\n{'DRY RUN - ' if dry_run else ''}Summary:")
    print(f"  Total products processed: {stats['total']}")
    print(f"  ✓ Matched (category assigned): {stats['matched']} ({stats['matched']/stats['total']*100:.1f}%)")
    print(f"  ✗ Unmatched (needs review): {stats['unmatched']} ({stats['unmatched']/stats['total']*100:.1f}%)")

    print(f"\nBy Match Type:")
    for match_type, count in stats['by_match_type'].items():
        print(f"  {match_type}: {count}")

    print(f"\nBy Source:")
    for source, counts in stats['by_source'].items():
        print(f"  {source}: {counts['matched']} matched, {counts['unmatched']} unmatched")

    if stats['unmatched_products']:
        print(f"\n⚠️  UNMATCHED PRODUCTS (need manual review):")
        print("-" * 80)

        # Group by source
        by_source = {}
        for p in stats['unmatched_products']:
            src = p['source']
            if src not in by_source:
                by_source[src] = []
            by_source[src].append(p)

        for source, products in by_source.items():
            print(f"\n  [{source.upper()}] ({len(products)} products)")
            for p in products[:20]:  # Show first 20 per source
                name = (p['name'] or '')[:40]
                print(f"    {p['sku']:<30} {name}")
            if len(products) > 20:
                print(f"    ... and {len(products) - 20} more")


# ============================================================================
# Main Execution
# ============================================================================

def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description='Categorize products with NULL category using product_catalog table'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be done without executing updates'
    )
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Show detailed progress for each product'
    )

    args = parser.parse_args()

    print("=" * 80)
    print("🔄 CATEGORIZE NULL CATEGORY PRODUCTS")
    print("   Using product_catalog table (NO CSV)")
    print("=" * 80)

    if args.dry_run:
        print("\n⚠️  DRY RUN MODE - No changes will be made to database\n")

    try:
        # Connect to database
        print("📡 Connecting to database...")
        conn = get_db_connection_dict_with_retry()
        cursor = conn.cursor()
        print("✅ Connected")

        # Load product_catalog lookups
        print("\n📚 Loading product_catalog...")
        sku_lookup, sku_master_lookup = get_product_catalog_lookup(cursor)
        print(f"✅ Loaded {len(sku_lookup)} SKUs and {len(sku_master_lookup)} master SKUs")

        # Get NULL category products
        print("\n🔍 Finding products with NULL category...")
        products = get_null_category_products(cursor)
        print(f"✅ Found {len(products)} products to categorize")

        if not products:
            print("\n✅ No products with NULL category found!")
            return

        # Run categorization
        stats = categorize_products(
            cursor,
            products,
            sku_lookup,
            sku_master_lookup,
            dry_run=args.dry_run,
            verbose=args.verbose
        )

        # Commit changes
        if not args.dry_run:
            conn.commit()
            print("\n✅ Changes committed to database")

        # Print report
        print_report(stats, args.dry_run)

        cursor.close()
        conn.close()

        print("\n" + "=" * 80)
        print("✅ CATEGORIZATION COMPLETE")
        print("=" * 80)

    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
