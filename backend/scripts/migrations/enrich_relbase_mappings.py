#!/usr/bin/env python3
"""
Enrich Relbase Product Mappings with Description, Product ID, and Image
========================================================================

This script enriches the existing relbase_product_mappings table with:
- description: Detailed product descriptions from Relbase API
- product_id_relbase: Relbase's internal stable product ID
- url_image: Product image URLs

Source: invoices_detailed.json and boletas_detailed.json

Usage:
    python3 enrich_relbase_mappings.py
"""

import os
import sys
import json
from collections import defaultdict
from typing import Dict, List, Optional
import psycopg2
from psycopg2.extras import execute_batch, RealDictCursor

# Paths
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, '../../..'))
DATA_DIR = os.path.join(PROJECT_ROOT, '.claude_sessions/current/relbase_fetch_progress')

INVOICES_FILE = os.path.join(DATA_DIR, 'invoices_detailed.json')
BOLETAS_FILE = os.path.join(DATA_DIR, 'boletas_detailed.json')

# Database connection
DB_URL = os.getenv('DATABASE_URL')
if not DB_URL:
    raise ValueError("DATABASE_URL environment variable is required")

def load_product_details():
    """Load product details from invoices and boletas"""
    print("📚 Loading product details from Relbase data...")

    product_details = {}  # code → {description, product_id, url_image}

    files_to_load = [
        (INVOICES_FILE, "invoices"),
        (BOLETAS_FILE, "boletas")
    ]

    for file_path, file_type in files_to_load:
        if not os.path.exists(file_path):
            print(f"  ⚠️  {file_type} file not found: {file_path}")
            continue

        with open(file_path, 'r', encoding='utf-8') as f:
            documents = json.load(f)
            print(f"  ✅ Loaded {len(documents)} {file_type}")

            for doc in documents:
                for product in doc.get('products', []):
                    code = product.get('code')
                    if not code:
                        continue

                    # Store first occurrence of product details
                    if code not in product_details:
                        product_details[code] = {
                            'description': product.get('description', ''),
                            'product_id_relbase': product.get('product_id'),
                            'url_image': product.get('url_image', '')
                        }

    print(f"\n  📊 Found details for {len(product_details)} unique product codes")
    return product_details

def enrich_mappings(conn, product_details: Dict):
    """Update mappings table with product details"""
    print("\n🔧 Enriching product mappings...")

    cur = conn.cursor(cursor_factory=RealDictCursor)

    # Prepare updates
    updates = []
    for code, details in product_details.items():
        updates.append({
            'relbase_code': code,
            'description': details['description'] or None,
            'product_id_relbase': details['product_id_relbase'],
            'url_image': details['url_image'] or None
        })

    if updates:
        update_query = """
            UPDATE relbase_product_mappings
            SET description = %(description)s,
                product_id_relbase = %(product_id_relbase)s,
                url_image = %(url_image)s,
                updated_at = NOW()
            WHERE relbase_code = %(relbase_code)s
        """

        execute_batch(cur, update_query, updates, page_size=100)
        conn.commit()

        print(f"  ✅ Updated {len(updates)} product mappings with detailed info")

        # Show statistics
        cur.execute("""
            SELECT
                COUNT(*) as total,
                COUNT(description) FILTER (WHERE description IS NOT NULL AND description != '') as with_description,
                COUNT(product_id_relbase) as with_product_id,
                COUNT(url_image) FILTER (WHERE url_image IS NOT NULL AND url_image != '') as with_image
            FROM relbase_product_mappings
        """)
        stats = cur.fetchone()

        print(f"\n📊 Enrichment Statistics:")
        print(f"  Total products: {stats['total']}")
        print(f"  With description: {stats['with_description']} ({stats['with_description']*100//stats['total']}%)")
        print(f"  With product_id: {stats['with_product_id']} ({stats['with_product_id']*100//stats['total']}%)")
        print(f"  With image: {stats['with_image']} ({stats['with_image']*100//stats['total']}%)")

    cur.close()

def main():
    print("=" * 80)
    print("ENRICH RELBASE PRODUCT MAPPINGS")
    print("=" * 80)

    # Load product details from detailed JSON files
    product_details = load_product_details()

    if not product_details:
        print("\n❌ No product details found. Exiting.")
        return

    # Connect to database
    print("\n🔌 Connecting to database...")
    conn = psycopg2.connect(DB_URL)

    try:
        # Enrich mappings
        enrich_mappings(conn, product_details)

        print("\n✅ Enrichment complete!")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()

if __name__ == '__main__':
    main()
