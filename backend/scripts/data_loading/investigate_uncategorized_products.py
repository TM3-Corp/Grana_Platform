"""
Investigate and analyze uncategorized products

This script provides detailed analysis of products without category assignment,
showing revenue impact, distribution by category, and identifying data quality issues.

Useful for:
- Understanding which products need categorization
- Analyzing revenue impact of uncategorized data
- Diagnosing data quality issues
- Generating reports before running auto-categorization

Usage:
    python3 investigate_uncategorized_products.py [--output-format {text|json}]

Options:
    --output-format : Output format (text or json), default: text

Author: Claude Code
Date: 2025-11-18
"""
import os
import sys
import json
from typing import Dict, List

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

# Load environment variables from .env file (override system vars)
from dotenv import load_dotenv
load_dotenv(override=True)

from app.core.database import get_db_connection_dict


def get_total_stats(cursor) -> Dict:
    """Get total statistics without category filter"""
    cursor.execute("""
        SELECT
            COUNT(DISTINCT o.id) as total_orders,
            COALESCE(SUM(oi.subtotal), 0) as total_revenue,
            COALESCE(SUM(oi.quantity), 0) as total_units
        FROM orders o
        LEFT JOIN order_items oi ON oi.order_id = o.id
        WHERE o.source = 'relbase'
        AND o.invoice_status IN ('accepted', 'accepted_objection')
        AND EXTRACT(YEAR FROM o.order_date) = 2025
    """)
    return cursor.fetchone()


def get_stats_with_products_join(cursor) -> Dict:
    """Get statistics with products JOIN (may lose data if products missing)"""
    cursor.execute("""
        SELECT
            COUNT(DISTINCT o.id) as total_orders,
            COALESCE(SUM(oi.subtotal), 0) as total_revenue,
            COALESCE(SUM(oi.quantity), 0) as total_units
        FROM orders o
        LEFT JOIN order_items oi ON oi.order_id = o.id
        LEFT JOIN products p ON p.sku = oi.product_sku
        WHERE o.source = 'relbase'
        AND o.invoice_status IN ('accepted', 'accepted_objection')
        AND EXTRACT(YEAR FROM o.order_date) = 2025
    """)
    return cursor.fetchone()


def get_skus_without_match(cursor) -> Dict:
    """Get SKUs that exist in order_items but not in products table"""
    cursor.execute("""
        SELECT
            COUNT(DISTINCT oi.product_sku) as skus_without_match,
            COALESCE(SUM(oi.subtotal), 0) as revenue_lost
        FROM orders o
        LEFT JOIN order_items oi ON oi.order_id = o.id
        LEFT JOIN products p ON p.sku = oi.product_sku
        WHERE o.source = 'relbase'
        AND o.invoice_status IN ('accepted', 'accepted_objection')
        AND EXTRACT(YEAR FROM o.order_date) = 2025
        AND p.id IS NULL  -- No match in products
        AND oi.product_sku IS NOT NULL
    """)
    return cursor.fetchone()


def get_products_with_null_category(cursor) -> Dict:
    """Get products with category NULL or empty"""
    cursor.execute("""
        SELECT
            COUNT(DISTINCT oi.product_sku) as skus_with_null_category,
            COALESCE(SUM(oi.subtotal), 0) as revenue_uncategorized
        FROM orders o
        LEFT JOIN order_items oi ON oi.order_id = o.id
        LEFT JOIN products p ON p.sku = oi.product_sku
        WHERE o.source = 'relbase'
        AND o.invoice_status IN ('accepted', 'accepted_objection')
        AND EXTRACT(YEAR FROM o.order_date) = 2025
        AND (p.category IS NULL OR p.category = '')
    """)
    return cursor.fetchone()


def get_category_distribution(cursor) -> List[Dict]:
    """Get revenue distribution by category"""
    cursor.execute("""
        SELECT
            COALESCE(p.category, '(NO CATEGORY)') as category,
            COUNT(DISTINCT o.id) as orders,
            COALESCE(SUM(oi.subtotal), 0) as revenue,
            COALESCE(SUM(oi.quantity), 0) as units
        FROM orders o
        LEFT JOIN order_items oi ON oi.order_id = o.id
        LEFT JOIN products p ON p.sku = oi.product_sku
        WHERE o.source = 'relbase'
        AND o.invoice_status IN ('accepted', 'accepted_objection')
        AND EXTRACT(YEAR FROM o.order_date) = 2025
        GROUP BY p.category
        ORDER BY revenue DESC
    """)
    return cursor.fetchall()


def get_uncategorized_skus_detail(cursor, limit: int = 20) -> List[Dict]:
    """Get detailed list of uncategorized SKUs with revenue impact"""
    cursor.execute("""
        SELECT
            oi.product_sku,
            oi.product_name,
            COALESCE(SUM(oi.subtotal), 0) as total_revenue,
            COALESCE(SUM(oi.quantity), 0) as total_units,
            COUNT(DISTINCT o.id) as total_orders
        FROM orders o
        LEFT JOIN order_items oi ON oi.order_id = o.id
        LEFT JOIN products p ON p.sku = oi.product_sku
        WHERE o.source = 'relbase'
        AND o.invoice_status IN ('accepted', 'accepted_objection')
        AND EXTRACT(YEAR FROM o.order_date) = 2025
        AND (p.category IS NULL OR p.category = '')
        AND oi.product_sku IS NOT NULL
        GROUP BY oi.product_sku, oi.product_name
        ORDER BY total_revenue DESC
        LIMIT %s
    """, (limit,))
    return cursor.fetchall()


def format_text_report(data: Dict) -> str:
    """Format investigation results as text report"""

    report = []
    report.append("=" * 80)
    report.append("📊 UNCATEGORIZED PRODUCTS INVESTIGATION")
    report.append("=" * 80)

    # Section 1: Totals
    total_stats = data['total_stats']
    report.append("\n1. TOTALS (without category filter):")
    report.append(f"   Orders:  {total_stats['total_orders']:,}")
    report.append(f"   Revenue: ${total_stats['total_revenue']:,.0f}")
    report.append(f"   Units:   {total_stats['total_units']:,}")

    # Section 2: With products JOIN
    join_stats = data['stats_with_join']
    report.append("\n2. WITH products JOIN (may lose data):")
    report.append(f"   Orders:  {join_stats['total_orders']:,}")
    report.append(f"   Revenue: ${join_stats['total_revenue']:,.0f}")
    report.append(f"   Units:   {join_stats['total_units']:,}")

    # Section 3: SKUs without match
    no_match = data['skus_without_match']
    report.append("\n3. SKUs without match in products table:")
    report.append(f"   Unique SKUs without match: {no_match['skus_without_match']}")
    report.append(f"   Revenue lost: ${no_match['revenue_lost']:,.0f}")

    # Section 4: Products with NULL category
    null_cat = data['products_with_null_category']
    report.append("\n4. Products with category NULL or empty:")
    report.append(f"   SKUs: {null_cat['skus_with_null_category']}")
    report.append(f"   Revenue: ${null_cat['revenue_uncategorized']:,.0f}")

    # Section 5: Category distribution
    distribution = data['category_distribution']
    report.append("\n5. DISTRIBUTION BY CATEGORY:")
    report.append("-" * 80)

    total_cat_revenue = 0
    for cat in distribution:
        total_cat_revenue += cat['revenue']
        percentage = (cat['revenue'] / total_stats['total_revenue'] * 100) if total_stats['total_revenue'] > 0 else 0
        report.append(
            f"   {cat['category']:20s}: ${cat['revenue']:>12,.0f} ({percentage:>5.1f}%) "
            f"- {cat['units']:>8,} units - {cat['orders']:>5,} orders"
        )

    report.append("-" * 80)
    report.append(f"   {'TOTAL':20s}: ${total_cat_revenue:>12,.0f}")

    # Section 6: Top uncategorized SKUs
    if data['uncategorized_skus_detail']:
        report.append("\n6. TOP UNCATEGORIZED SKUs (by revenue):")
        report.append("-" * 80)
        for idx, sku in enumerate(data['uncategorized_skus_detail'], 1):
            report.append(
                f"   {idx:2d}. {sku['product_sku']:30s} ${sku['total_revenue']:>12,.0f} "
                f"({sku['total_units']:>6,} units, {sku['total_orders']:>3,} orders)"
            )
            report.append(f"       {sku['product_name'][:70]}")

    # Summary
    report.append("\n" + "=" * 80)
    report.append("📋 SUMMARY")
    report.append("=" * 80)

    if null_cat['skus_with_null_category'] > 0:
        impact_pct = (null_cat['revenue_uncategorized'] / total_stats['total_revenue'] * 100)
        report.append(f"\n⚠️  DATA QUALITY ISSUE DETECTED:")
        report.append(f"   • {null_cat['skus_with_null_category']} SKUs without category")
        report.append(f"   • ${null_cat['revenue_uncategorized']:,.0f} in uncategorized revenue ({impact_pct:.1f}% of total)")
        report.append(f"\n💡 Recommendation: Run auto_categorize_products.py to fix")
    else:
        report.append("\n✅ All products are properly categorized!")

    return "\n".join(report)


def format_json_report(data: Dict) -> str:
    """Format investigation results as JSON"""
    return json.dumps(data, indent=2, default=str)


def execute_investigation(output_format: str = 'text') -> Dict:
    """
    Execute investigation and return results

    Args:
        output_format: Output format ('text' or 'json')

    Returns:
        Dictionary with investigation data
    """

    # Get database connection
    conn = get_db_connection_dict()
    cursor = conn.cursor()

    # Collect all data
    data = {
        'total_stats': get_total_stats(cursor),
        'stats_with_join': get_stats_with_products_join(cursor),
        'skus_without_match': get_skus_without_match(cursor),
        'products_with_null_category': get_products_with_null_category(cursor),
        'category_distribution': get_category_distribution(cursor),
        'uncategorized_skus_detail': get_uncategorized_skus_detail(cursor, limit=20)
    }

    cursor.close()
    conn.close()

    # Format output
    if output_format == 'json':
        print(format_json_report(data))
    else:
        print(format_text_report(data))

    return data


def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(
        description='Investigate and analyze uncategorized products'
    )
    parser.add_argument(
        '--output-format',
        choices=['text', 'json'],
        default='text',
        help='Output format (default: text)'
    )

    args = parser.parse_args()

    # Execute investigation
    data = execute_investigation(output_format=args.output_format)

    # Exit with appropriate code
    null_cat = data['products_with_null_category']
    if null_cat['skus_with_null_category'] > 0:
        sys.exit(1)  # Issues found
    else:
        sys.exit(0)  # All good


if __name__ == "__main__":
    main()
