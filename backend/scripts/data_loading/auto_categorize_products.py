"""
Auto-categorize uncategorized products using product_catalog + keyword matching

This script identifies products without category assignment and automatically
categorizes them using a 3-step approach:
1. Exact match in product_catalog table
2. Match without ANU- prefix in product_catalog
3. Keyword-based auto-categorization

Designed to run as part of data loading pipeline or GitHub Actions workflow.

Usage:
    python3 auto_categorize_products.py [--dry-run] [--verbose]

Options:
    --dry-run   : Show what would be done without executing updates
    --verbose   : Show detailed progress and categorization details

Author: Claude Code
Date: 2025-11-18
"""
import os
import sys
from typing import Dict, List, Tuple, Optional

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

# Load environment variables from .env file (override system vars)
from dotenv import load_dotenv
load_dotenv(override=True)

from app.core.database import get_db_connection_dict


def get_uncategorized_skus(cursor) -> List[Dict]:
    """Get all SKUs without category from order_items"""
    query = """
        SELECT DISTINCT
            oi.product_sku,
            oi.product_name
        FROM orders o
        LEFT JOIN order_items oi ON oi.order_id = o.id
        LEFT JOIN products p ON p.sku = oi.product_sku
        WHERE o.source = 'relbase'
        AND o.invoice_status IN ('accepted', 'accepted_objection')
        AND EXTRACT(YEAR FROM o.order_date) = 2025
        AND (p.category IS NULL OR p.category = '')
        AND oi.product_sku IS NOT NULL
        ORDER BY oi.product_sku
    """

    cursor.execute(query)
    return cursor.fetchall()


def get_product_catalog(cursor) -> Dict[str, Dict]:
    """Get all products from product_catalog table"""
    # Check if product_catalog table exists
    cursor.execute("""
        SELECT EXISTS (
            SELECT FROM information_schema.tables
            WHERE table_name = 'product_catalog'
        )
    """)

    table_exists = cursor.fetchone()['exists']

    if not table_exists:
        print("⚠️  Warning: product_catalog table does not exist")
        return {}

    # Get all products from catalog
    cursor.execute("""
        SELECT
            sku,
            category,
            product_name
        FROM product_catalog
        WHERE category IS NOT NULL AND category != ''
    """)

    results = cursor.fetchall()

    # Create dictionary: sku -> {category, product_name}
    catalog = {}
    for row in results:
        catalog[row['sku']] = {
            'category': row['category'],
            'product_name': row['product_name']
        }

    return catalog


def remove_anu_prefix(sku: str) -> str:
    """Remove ANU- prefix from legacy SKU codes"""
    if sku.startswith('ANU-'):
        return sku[4:]  # Remove first 4 characters
    return sku


def auto_categorize_by_keywords(product_name: str) -> Optional[str]:
    """
    Auto-categorize based on keywords in product name

    Returns category or None if no match found
    """
    name_lower = product_name.lower()

    # Priority order matters - check most specific first
    if 'keeper' in name_lower:
        return 'KEEPERS'
    elif 'barra' in name_lower or 'barrita' in name_lower:
        return 'BARRAS'
    elif 'cracker' in name_lower:
        return 'CRACKERS'
    elif 'granola' in name_lower:
        return 'GRANOLAS'
    elif 'caja master' in name_lower:
        return 'CAJA MASTER'
    elif 'despacho' in name_lower:
        return 'DESPACHOS'
    elif 'pack' in name_lower:
        return 'OTROS'
    # Special cases for edge cases
    elif 'refacturacion' in name_lower or 'refacturación' in name_lower:
        return 'OTROS'
    elif 'productos varios' in name_lower or 'general' in name_lower:
        return 'OTROS'
    else:
        return None  # Needs manual review


def categorize_sku(sku: str, product_name: str, catalog: Dict) -> Tuple[Optional[str], str, str]:
    """
    Categorize a single SKU using the 3-step approach

    Returns: (category, method, confidence)
    """

    # Step 1: Try exact match in product_catalog
    if sku in catalog:
        return (catalog[sku]['category'], 'product_catalog_exact', 'HIGH')

    # Step 2: Try match without ANU- prefix
    sku_without_prefix = remove_anu_prefix(sku)
    if sku_without_prefix != sku and sku_without_prefix in catalog:
        return (catalog[sku_without_prefix]['category'], 'product_catalog_no_prefix', 'HIGH')

    # Step 3: Auto-categorize by keywords
    keyword_category = auto_categorize_by_keywords(product_name)
    if keyword_category:
        return (keyword_category, 'keyword_matching', 'MEDIUM')

    # Needs manual review
    return (None, 'manual_review_needed', 'LOW')


def execute_categorization(dry_run: bool = True, verbose: bool = False) -> Dict:
    """
    Main categorization function

    Args:
        dry_run: If True, only show what would be done
        verbose: If True, show detailed progress

    Returns:
        Dictionary with execution statistics
    """

    print("=" * 80)
    print("🔧 AUTO-CATEGORIZATION OF UNCATEGORIZED PRODUCTS")
    print("=" * 80)

    # Get database connection
    conn = get_db_connection_dict()
    cursor = conn.cursor()

    # Get uncategorized SKUs
    if verbose:
        print("\n📊 Fetching uncategorized SKUs...")
    uncategorized = get_uncategorized_skus(cursor)
    print(f"✅ Found {len(uncategorized)} uncategorized SKUs")

    if len(uncategorized) == 0:
        print("\n✅ All products are already categorized!")
        cursor.close()
        conn.close()
        return {
            'total_skus': 0,
            'categorized': 0,
            'manual_review_needed': 0
        }

    # Get product catalog
    if verbose:
        print("\n📚 Loading product_catalog...")
    catalog = get_product_catalog(cursor)
    print(f"✅ Loaded {len(catalog)} products from catalog")

    # Categorize each SKU
    if verbose:
        print("\n🔍 Categorizing SKUs...")
        print("-" * 80)

    categorization_plan = []

    for item in uncategorized:
        sku = item['product_sku']
        name = item['product_name']

        category, method, confidence = categorize_sku(sku, name, catalog)

        categorization_plan.append({
            'sku': sku,
            'name': name,
            'category': category,
            'method': method,
            'confidence': confidence
        })

    # Generate statistics
    by_method = {
        'product_catalog_exact': [],
        'product_catalog_no_prefix': [],
        'keyword_matching': [],
        'manual_review_needed': []
    }

    for item in categorization_plan:
        by_method[item['method']].append(item)

    # Print report
    print("\n📋 CATEGORIZATION REPORT")
    print("=" * 80)
    print(f"\n✅ Method 1 - Catalog (exact match):        {len(by_method['product_catalog_exact'])} SKUs")
    print(f"✅ Method 2 - Catalog (without ANU- prefix): {len(by_method['product_catalog_no_prefix'])} SKUs")
    print(f"⚠️  Method 3 - Keyword matching:             {len(by_method['keyword_matching'])} SKUs")
    print(f"❌ Manual review needed:                    {len(by_method['manual_review_needed'])} SKUs")

    total_automated = len(by_method['product_catalog_exact']) + \
                     len(by_method['product_catalog_no_prefix']) + \
                     len(by_method['keyword_matching'])

    print(f"\n📊 Total automated: {total_automated}/{len(uncategorized)} ({total_automated/len(uncategorized)*100:.1f}%)")

    # Show manual review cases if any
    if by_method['manual_review_needed'] and verbose:
        print("\n❌ SKUs requiring manual review:")
        print("-" * 80)
        for item in by_method['manual_review_needed']:
            print(f"  {item['sku']:30s} | {item['name'][:45]}")

    # Execute updates if not dry run
    updates_executed = 0

    if not dry_run:
        print("\n" + "=" * 80)
        print("🚀 EXECUTING DATABASE UPDATES")
        print("=" * 80)

        for item in categorization_plan:
            if item['category']:  # Only update if we have a category
                try:
                    # Check if SKU exists in products table
                    cursor.execute("""
                        SELECT id FROM products WHERE sku = %s
                    """, (item['sku'],))

                    product_exists = cursor.fetchone()

                    if product_exists:
                        # Update existing product
                        cursor.execute("""
                            UPDATE products
                            SET category = %s, updated_at = NOW()
                            WHERE sku = %s
                            AND (category IS NULL OR category = '')
                        """, (item['category'], item['sku']))

                        if cursor.rowcount > 0:
                            updates_executed += 1
                            if verbose:
                                print(f"✅ Updated: {item['sku']} → {item['category']}")
                    else:
                        if verbose:
                            print(f"⚠️  Skipped: {item['sku']} (does not exist in products table)")

                except Exception as e:
                    print(f"❌ Error updating {item['sku']}: {e}")

        # Commit changes
        conn.commit()
        print(f"\n✅ Updates completed: {updates_executed} products categorized")

    else:
        print("\n" + "=" * 80)
        print("ℹ️  DRY RUN - No changes were made to the database")
        print("   To execute real changes, run: python3 auto_categorize_products.py")
        print("=" * 80)

    cursor.close()
    conn.close()

    return {
        'total_skus': len(uncategorized),
        'categorized': total_automated,
        'manual_review_needed': len(by_method['manual_review_needed']),
        'updates_executed': updates_executed if not dry_run else 0
    }


def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(
        description='Auto-categorize uncategorized products'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be done without executing updates'
    )
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Show detailed progress and categorization details'
    )

    args = parser.parse_args()

    # Execute categorization
    stats = execute_categorization(
        dry_run=args.dry_run,
        verbose=args.verbose
    )

    # Exit with appropriate code
    if stats['manual_review_needed'] > 0:
        print(f"\n⚠️  Warning: {stats['manual_review_needed']} SKUs need manual review")
        sys.exit(1)
    else:
        print("\n✅ All SKUs categorized successfully!")
        sys.exit(0)


if __name__ == "__main__":
    main()
