"""
Populate product_variants table from official catalog

This script creates product variant mappings based on the official catalog.
It identifies packaging variants (1un, 5un, 16un, etc.) of the same base product
and creates relationships in the product_variants table.

Usage:
    python3 populate_product_variants.py [--dry-run]

Author: TM3
Date: 2025-10-17
"""
import os
import sys
from typing import Dict, List, Tuple, Optional

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from app.core.database import get_db_connection
from app.domain import catalog


def get_product_id_by_sku(cursor, sku: str) -> Optional[int]:
    """Get product ID from database by SKU"""
    cursor.execute("SELECT id FROM products WHERE sku = %s AND is_active = true", (sku,))
    result = cursor.fetchone()
    return result[0] if result else None


def get_existing_variants(cursor) -> set:
    """Get existing variant mappings to avoid duplicates"""
    cursor.execute("""
        SELECT base_product_id, variant_product_id
        FROM product_variants
        WHERE is_active = true
    """)
    return {(row[0], row[1]) for row in cursor.fetchall()}


def determine_packaging_type(units_per_display: int) -> str:
    """Determine packaging type based on units per display"""
    if units_per_display == 1:
        return 'individual'
    elif units_per_display == 5:
        return 'display_5'
    elif units_per_display == 16:
        return 'display_16'
    elif units_per_display == 18:
        return 'display_18'
    elif units_per_display == 4:
        return 'display_4'
    elif units_per_display == 7:
        return 'display_7'
    elif units_per_display == 12:
        return 'display_12'
    else:
        return f'display_{units_per_display}'


def find_variant_pairs(cursor) -> List[Dict]:
    """
    Find all packaging variant pairs from the official catalog

    A variant pair is:
    - Base product (1 unit, base SKU)
    - Variant product (5 units, 16 units, etc. - same base code)

    Example: BAKC_U04010 (1 unit) → BAKC_U20010 (5 units)
    """
    variant_pairs = []

    # Group products by base_code
    products_by_base = {}
    for product in catalog.get_all_products():
        base_code = product.base_code
        if base_code not in products_by_base:
            products_by_base[base_code] = []
        products_by_base[base_code].append(product)

    # For each base code, find the base product (1 unit) and its variants
    for base_code, products in products_by_base.items():
        # Sort by units_per_display to ensure we get the base product first
        products = sorted(products, key=lambda p: p.units_per_display)

        # Find base product (1 unit)
        base_products = [p for p in products if p.units_per_display == 1]

        if not base_products:
            # No base product (1 unit), skip this base code
            continue

        # Use first base product as the base
        base_product = base_products[0]
        base_id = get_product_id_by_sku(cursor, base_product.sku)

        if not base_id:
            print(f"⚠️  WARNING: Base product {base_product.sku} not found in database, skipping base code {base_code}")
            continue

        # Find all variant products (more than 1 unit)
        for variant_product in products:
            if variant_product.units_per_display == 1:
                continue  # Skip base products

            variant_id = get_product_id_by_sku(cursor, variant_product.sku)

            if not variant_id:
                print(f"⚠️  WARNING: Variant product {variant_product.sku} not found in database, skipping")
                continue

            variant_pairs.append({
                'base_product_id': base_id,
                'base_sku': base_product.sku,
                'base_name': base_product.product_name,
                'variant_product_id': variant_id,
                'variant_sku': variant_product.sku,
                'variant_name': variant_product.product_name,
                'quantity_multiplier': variant_product.units_per_display,
                'packaging_type': determine_packaging_type(variant_product.units_per_display)
            })

    return variant_pairs


def populate_variants(dry_run: bool = False):
    """Populate product_variants table"""
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        print("🔍 Finding variant pairs from official catalog...")
        variant_pairs = find_variant_pairs(cursor)

        print(f"📦 Found {len(variant_pairs)} variant pairs")

        # Get existing variants
        existing = get_existing_variants(cursor)
        print(f"📋 {len(existing)} variant mappings already exist in database")

        # Filter out existing variants
        new_variants = [
            v for v in variant_pairs
            if (v['base_product_id'], v['variant_product_id']) not in existing
        ]

        print(f"✨ {len(new_variants)} new variants to insert")

        if dry_run:
            print("\n🔍 DRY RUN MODE - No changes will be made to database\n")

        # Display and insert new variants
        inserted = 0
        for variant in new_variants:
            print(f"\n{'[DRY RUN] ' if dry_run else ''}Creating variant mapping:")
            print(f"  Base: {variant['base_sku']} - {variant['base_name']}")
            print(f"  Variant: {variant['variant_sku']} - {variant['variant_name']}")
            print(f"  Multiplier: {variant['quantity_multiplier']}x")
            print(f"  Type: {variant['packaging_type']}")

            if not dry_run:
                cursor.execute("""
                    INSERT INTO product_variants (
                        base_product_id,
                        variant_product_id,
                        quantity_multiplier,
                        packaging_type,
                        is_active
                    )
                    VALUES (%s, %s, %s, %s, true)
                """, (
                    variant['base_product_id'],
                    variant['variant_product_id'],
                    variant['quantity_multiplier'],
                    variant['packaging_type']
                ))
                inserted += 1

        if not dry_run:
            conn.commit()
            print(f"\n✅ Successfully inserted {inserted} product variant mappings")
        else:
            print(f"\n✅ Dry run complete. Would have inserted {len(new_variants)} variant mappings")

        # Show summary
        if not dry_run:
            cursor.execute("SELECT COUNT(*) FROM product_variants WHERE is_active = true")
            total = cursor.fetchone()[0]
            print(f"📊 Total active product variants in database: {total}")

    except Exception as e:
        conn.rollback()
        print(f"\n❌ ERROR: {str(e)}")
        raise

    finally:
        cursor.close()
        conn.close()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='Populate product_variants table')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be inserted without making changes')
    args = parser.parse_args()

    print("=" * 80)
    print("POPULATE PRODUCT VARIANTS")
    print("=" * 80)

    populate_variants(dry_run=args.dry_run)

    print("\n" + "=" * 80)
    print("DONE")
    print("=" * 80)
