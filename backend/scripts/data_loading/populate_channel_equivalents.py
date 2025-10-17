"""
Populate channel_equivalents table from MercadoLibre mappings

This script creates cross-channel equivalent mappings between Shopify and
MercadoLibre products based on the ML_TO_CATALOG_MAPPING from the frontend.

Usage:
    python3 populate_channel_equivalents.py [--dry-run]

Author: TM3
Date: 2025-10-17
"""
import os
import sys
from typing import Dict, Optional, List

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from app.core.database import get_db_connection


# MercadoLibre to Shopify SKU mappings (from frontend product-mapping-ml.ts)
ML_TO_SHOPIFY_MAPPING = {
    # Barras Low Carb Cacao Maní
    'ML-MLC1630349929': 'BACM_U64010',
    'ML-MLC2978631042': 'BACM_U20010',
    'ML-MLC1630414337': 'BACM_U20010',

    # Barras Keto Nuez
    'ML-MLC2929973548': 'BAKC_U64010',
    'ML-MLC2930199094': 'BAKC_U20010',

    # Barras Manzana Canela
    'ML-MLC1630337053': 'BAMC_U64010',
    'ML-MLC2938290826': 'BAMC_U20010',
    'ML-MLC1630416135': 'BAMC_U20010',

    # Crackers Sal de Mar
    'ML-MLC2930215860': 'CRSM_U13510',

    # Crackers Romero
    'ML-MLC2930238714': 'CRRO_U13510',
    'ML-MLC2933751572': 'CRRO_U13510',

    # Crackers Ajo Albahaca
    'ML-MLC2930200766': 'CRAA_U13510',

    # Crackers Pimienta
    'ML-MLC1630369169': 'CRPM_U13510',

    # Granola Low Carb Almendras
    'ML-MLC2967399930': 'GRAL_U26010',
    'ML-MLC3029455396': 'GRAL_U26010',

    # Granola Low Carb Berries
    'ML-MLC2978641268': 'GRBE_U26010',
    'ML-MLC2966323128': 'GRBE_U26010',
}


def get_product_by_sku(cursor, sku: str) -> Optional[Dict]:
    """Get product from database by SKU"""
    cursor.execute("""
        SELECT id, sku, name, source
        FROM products
        WHERE sku = %s AND is_active = true
    """, (sku,))
    result = cursor.fetchone()
    if result:
        return {
            'id': result[0],
            'sku': result[1],
            'name': result[2],
            'source': result[3]
        }
    return None


def get_existing_equivalents(cursor) -> set:
    """Get existing channel equivalents to avoid duplicates"""
    cursor.execute("""
        SELECT shopify_product_id, mercadolibre_product_id
        FROM channel_equivalents
    """)
    return {(row[0], row[1]) for row in cursor.fetchall()}


def populate_equivalents(dry_run: bool = False):
    """Populate channel_equivalents table"""
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        print("🔍 Processing MercadoLibre → Shopify mappings...")

        # Get existing equivalents
        existing = get_existing_equivalents(cursor)
        print(f"📋 {len(existing)} channel equivalents already exist in database")

        equivalent_pairs = []
        warnings = []

        # Process each mapping
        for ml_sku, shopify_sku in ML_TO_SHOPIFY_MAPPING.items():
            # Get MercadoLibre product
            ml_product = get_product_by_sku(cursor, ml_sku)
            if not ml_product:
                warnings.append(f"⚠️  MercadoLibre product not found in DB: {ml_sku}")
                continue

            if ml_product['source'] != 'mercadolibre':
                warnings.append(f"⚠️  Product {ml_sku} is not a MercadoLibre product (source: {ml_product['source']})")
                continue

            # Get Shopify product
            shopify_product = get_product_by_sku(cursor, shopify_sku)
            if not shopify_product:
                warnings.append(f"⚠️  Shopify product not found in DB: {shopify_sku}")
                continue

            if shopify_product['source'] != 'shopify':
                warnings.append(f"⚠️  Product {shopify_sku} is not a Shopify product (source: {shopify_product['source']})")
                continue

            # Skip if already exists
            if (shopify_product['id'], ml_product['id']) in existing:
                continue

            # Add to list
            equivalent_pairs.append({
                'shopify_product_id': shopify_product['id'],
                'shopify_sku': shopify_product['sku'],
                'shopify_name': shopify_product['name'],
                'mercadolibre_product_id': ml_product['id'],
                'mercadolibre_sku': ml_product['sku'],
                'mercadolibre_name': ml_product['name'],
                'confidence': 1.0,  # Manual mapping, high confidence
                'verified': True     # These are manually verified
            })

        print(f"✨ {len(equivalent_pairs)} new equivalents to insert")

        # Display warnings
        if warnings:
            print(f"\n⚠️  {len(warnings)} warnings:")
            for warning in warnings[:10]:  # Show first 10
                print(f"  {warning}")
            if len(warnings) > 10:
                print(f"  ... and {len(warnings) - 10} more")

        if dry_run:
            print("\n🔍 DRY RUN MODE - No changes will be made to database\n")

        # Display and insert new equivalents
        inserted = 0
        for equiv in equivalent_pairs:
            print(f"\n{'[DRY RUN] ' if dry_run else ''}Creating channel equivalent:")
            print(f"  Shopify: {equiv['shopify_sku']} - {equiv['shopify_name']}")
            print(f"  MercadoLibre: {equiv['mercadolibre_sku']} - {equiv['mercadolibre_name']}")
            print(f"  Confidence: {equiv['confidence']:.2f}, Verified: {equiv['verified']}")

            if not dry_run:
                cursor.execute("""
                    INSERT INTO channel_equivalents (
                        shopify_product_id,
                        mercadolibre_product_id,
                        equivalence_confidence,
                        verified,
                        notes
                    )
                    VALUES (%s, %s, %s, %s, %s)
                """, (
                    equiv['shopify_product_id'],
                    equiv['mercadolibre_product_id'],
                    equiv['confidence'],
                    equiv['verified'],
                    'Migrated from frontend product-mapping-ml.ts'
                ))
                inserted += 1

        if not dry_run:
            conn.commit()
            print(f"\n✅ Successfully inserted {inserted} channel equivalent mappings")
        else:
            print(f"\n✅ Dry run complete. Would have inserted {len(equivalent_pairs)} channel equivalents")

        # Show summary
        if not dry_run:
            cursor.execute("SELECT COUNT(*) FROM channel_equivalents")
            total = cursor.fetchone()[0]
            print(f"📊 Total channel equivalents in database: {total}")

    except Exception as e:
        conn.rollback()
        print(f"\n❌ ERROR: {str(e)}")
        raise

    finally:
        cursor.close()
        conn.close()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='Populate channel_equivalents table')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be inserted without making changes')
    args = parser.parse_args()

    print("=" * 80)
    print("POPULATE CHANNEL EQUIVALENTS")
    print("=" * 80)

    populate_equivalents(dry_run=args.dry_run)

    print("\n" + "=" * 80)
    print("DONE")
    print("=" * 80)
