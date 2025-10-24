#!/usr/bin/env python3
"""
Data Migration: Load Relbase 2025 Sales Data
=============================================

This script loads the complete 2025 Relbase sales data into the database:
1. Product mappings → relbase_product_mappings table
2. Invoices & Boletas → orders table
3. Line items → order_items table

Source Files:
- relbase_2025_complete.json (5,274 documents, 11,595 line items, 45.7 MB)
- relbase_complete_mapping.json (348 product code mappings)

Target Tables:
- relbase_product_mappings (new)
- orders (existing)
- order_items (existing)
- channels (existing - ensure 'relbase' channel exists)

Usage:
    python3 load_relbase_2025_data.py [--dry-run] [--batch-size 1000]
"""

import os
import sys
import json
import argparse
from datetime import datetime
from typing import Dict, List, Optional
import psycopg2
from psycopg2.extras import execute_batch, RealDictCursor
from psycopg2.extensions import connection as Connection

# Paths (relative to script location)
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, '../../..'))
DATA_DIR = os.path.join(PROJECT_ROOT, '.claude_sessions/current/relbase_fetch_progress')

RELBASE_DATA_FILE = os.path.join(DATA_DIR, 'relbase_2025_complete.json')
MAPPING_FILE = os.path.join(PROJECT_ROOT, '.claude_sessions/current/relbase_complete_mapping.json')

# Database connection
DB_URL = os.getenv('DATABASE_URL')
if not DB_URL:
    raise ValueError("DATABASE_URL environment variable is required")

class RelbaseDataLoader:
    """Loads Relbase sales data into Supabase"""

    def __init__(self, conn: Connection, dry_run: bool = False):
        self.conn = conn
        self.dry_run = dry_run
        self.stats = {
            'mappings_inserted': 0,
            'orders_inserted': 0,
            'order_items_inserted': 0,
            'errors': []
        }

    def load_mappings(self, mapping_data: Dict) -> None:
        """Load product code mappings into relbase_product_mappings table"""
        print("\n📦 Loading product mappings...")

        cur = self.conn.cursor(cursor_factory=RealDictCursor)

        mappings_to_insert = []

        # Process each mapping tier
        for match_type, mappings in mapping_data.get('mappings', {}).items():
            if match_type == 'no_match':
                confidence = 'none'
            elif match_type == 'caja_fuzzy':
                confidence = 'medium'
            else:
                confidence = 'high'

            for mapping in mappings:
                relbase_code = mapping['code']
                relbase_name = mapping.get('name', '')
                official_sku = mapping.get('sku')
                sales_count = mapping.get('count', 0)

                # Determine flags
                is_legacy = relbase_code.startswith('ANU-')
                is_service = any(keyword in relbase_name.upper()
                               for keyword in ['DESPACHO', 'DIFERENCIA', 'ENVÍO'])
                needs_review = (match_type == 'no_match' and not is_service)

                mappings_to_insert.append({
                    'relbase_code': relbase_code,
                    'relbase_name': relbase_name,
                    'official_sku': official_sku,
                    'match_type': match_type,
                    'confidence_level': confidence,
                    'total_sales': sales_count,
                    'is_legacy_code': is_legacy,
                    'is_service_item': is_service,
                    'needs_manual_review': needs_review
                })

        if not self.dry_run and mappings_to_insert:
            # Insert mappings
            insert_query = """
                INSERT INTO relbase_product_mappings
                (relbase_code, relbase_name, official_sku, match_type, confidence_level,
                 total_sales, is_legacy_code, is_service_item, needs_manual_review)
                VALUES (%(relbase_code)s, %(relbase_name)s, %(official_sku)s, %(match_type)s,
                        %(confidence_level)s, %(total_sales)s, %(is_legacy_code)s,
                        %(is_service_item)s, %(needs_manual_review)s)
                ON CONFLICT (relbase_code)
                DO UPDATE SET
                    relbase_name = EXCLUDED.relbase_name,
                    official_sku = EXCLUDED.official_sku,
                    match_type = EXCLUDED.match_type,
                    confidence_level = EXCLUDED.confidence_level,
                    total_sales = EXCLUDED.total_sales,
                    is_legacy_code = EXCLUDED.is_legacy_code,
                    is_service_item = EXCLUDED.is_service_item,
                    needs_manual_review = EXCLUDED.needs_manual_review,
                    updated_at = NOW()
            """

            execute_batch(cur, insert_query, mappings_to_insert, page_size=100)
            self.conn.commit()

        self.stats['mappings_inserted'] = len(mappings_to_insert)
        print(f"  ✅ Inserted/Updated {len(mappings_to_insert)} product mappings")

        cur.close()

    def ensure_channel_exists(self) -> int:
        """Ensure 'relbase' channel exists in channels table"""
        cur = self.conn.cursor(cursor_factory=RealDictCursor)

        # Check if relbase channel exists
        cur.execute("SELECT id FROM channels WHERE code = 'relbase'")
        result = cur.fetchone()

        if result:
            channel_id = result['id']
            print(f"  ✅ Relbase channel exists (ID: {channel_id})")
        else:
            if not self.dry_run:
                cur.execute("""
                    INSERT INTO channels (code, name, description, type, is_active)
                    VALUES ('relbase', 'Relbase', 'Relbase ERP - Cencosud Integration', 'erp', true)
                    RETURNING id
                """)
                result = cur.fetchone()
                channel_id = result['id']
                self.conn.commit()
                print(f"  ✅ Created relbase channel (ID: {channel_id})")
            else:
                channel_id = -1
                print(f"  🔍 [DRY RUN] Would create relbase channel")

        cur.close()
        return channel_id

    def get_product_id(self, sku: str) -> Optional[int]:
        """Get product ID from official SKU"""
        if not sku:
            return None

        cur = self.conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("SELECT id FROM products WHERE sku = %s", (sku,))
        result = cur.fetchone()
        cur.close()

        return result['id'] if result else None

    def load_orders(self, relbase_data: Dict, channel_id: int, batch_size: int = 500) -> None:
        """Load invoices and boletas into orders table"""
        print("\n📄 Loading orders (invoices and boletas)...")

        all_documents = []

        # Combine invoices and boletas
        for invoice in relbase_data.get('invoices', []):
            all_documents.append({**invoice, 'type': 'invoice', 'type_code': 33})

        for boleta in relbase_data.get('boletas', []):
            all_documents.append({**boleta, 'type': 'boleta', 'type_code': 39})

        print(f"  Total documents to load: {len(all_documents)}")

        cur = self.conn.cursor(cursor_factory=RealDictCursor)

        orders_inserted = 0
        items_inserted = 0

        for i, doc in enumerate(all_documents):
            if (i + 1) % 100 == 0:
                print(f"  Progress: {i + 1}/{len(all_documents)} documents...")

            try:
                # Parse document data
                doc_id = doc['id']
                doc_type = doc['type']
                folio = doc.get('folio', f"{doc_type}_{doc_id}")
                total = float(doc.get('total', 0))
                tax = float(doc.get('tax', 0))
                net = float(doc.get('net', total - tax))

                # Parse date
                date_str = doc.get('date', doc.get('emission_date', datetime.now().isoformat()))
                try:
                    order_date = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                except:
                    order_date = datetime.now()

                # Customer info (if available)
                customer_name = doc.get('receiver', {}).get('name', 'Cliente Relbase')
                customer_rut = doc.get('receiver', {}).get('rut')

                # Insert order
                if not self.dry_run:
                    cur.execute("""
                        INSERT INTO orders
                        (external_id, order_number, source, channel_id,
                         subtotal, tax_amount, total, status, payment_status,
                         order_date, invoice_number, invoice_type, invoice_date,
                         customer_notes, created_at)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
                        ON CONFLICT (external_id, source)
                        DO UPDATE SET updated_at = NOW()
                        RETURNING id
                    """, (
                        str(doc_id),
                        folio,
                        'relbase',
                        channel_id,
                        net,
                        tax,
                        total,
                        'completed',
                        'paid',
                        order_date,
                        folio,
                        doc_type,
                        order_date,
                        json.dumps({'relbase_id': doc_id, 'customer_rut': customer_rut})
                    ))

                    result = cur.fetchone()
                    order_id = result['id']
                    orders_inserted += 1

                    # Insert order items
                    products = doc.get('products', [])
                    for product in products:
                        product_code = product.get('code', '')
                        product_name = product.get('name', '')
                        quantity = int(product.get('quantity', 0))
                        price = float(product.get('price', 0))
                        subtotal = quantity * price

                        # Try to map to official product
                        cur.execute("""
                            SELECT official_sku FROM relbase_product_mappings
                            WHERE relbase_code = %s
                        """, (product_code,))
                        mapping = cur.fetchone()
                        official_sku = mapping['official_sku'] if mapping else None
                        product_id = self.get_product_id(official_sku) if official_sku else None

                        cur.execute("""
                            INSERT INTO order_items
                            (order_id, product_id, product_sku, product_name,
                             quantity, unit_price, subtotal, total, created_at)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, NOW())
                        """, (
                            order_id,
                            product_id,
                            official_sku or product_code,
                            product_name,
                            quantity,
                            price,
                            subtotal,
                            subtotal
                        ))
                        items_inserted += 1

                    # Commit every batch_size documents
                    if (i + 1) % batch_size == 0:
                        self.conn.commit()

            except Exception as e:
                self.stats['errors'].append(f"Error loading document {doc_id}: {str(e)}")
                print(f"  ⚠️  Error on document {doc_id}: {e}")
                continue

        if not self.dry_run:
            self.conn.commit()

        self.stats['orders_inserted'] = orders_inserted
        self.stats['order_items_inserted'] = items_inserted

        print(f"  ✅ Loaded {orders_inserted} orders")
        print(f"  ✅ Loaded {items_inserted} order items")

        cur.close()

    def print_summary(self):
        """Print migration summary"""
        print("\n" + "=" * 80)
        print("📊 MIGRATION SUMMARY")
        print("=" * 80)
        print(f"  Product Mappings: {self.stats['mappings_inserted']}")
        print(f"  Orders: {self.stats['orders_inserted']}")
        print(f"  Order Items: {self.stats['order_items_inserted']}")
        print(f"  Errors: {len(self.stats['errors'])}")

        if self.stats['errors']:
            print("\n⚠️  Errors encountered:")
            for error in self.stats['errors'][:10]:
                print(f"    - {error}")
            if len(self.stats['errors']) > 10:
                print(f"    ... and {len(self.stats['errors']) - 10} more")

        print("=" * 80)


def main():
    parser = argparse.ArgumentParser(description='Load Relbase 2025 sales data into Supabase')
    parser.add_argument('--dry-run', action='store_true', help='Preview changes without writing to database')
    parser.add_argument('--batch-size', type=int, default=500, help='Batch size for commits (default: 500)')
    args = parser.parse_args()

    print("=" * 80)
    print("🚀 RELBASE 2025 DATA MIGRATION")
    print("=" * 80)
    print(f"  Mode: {'DRY RUN' if args.dry_run else 'PRODUCTION'}")
    print(f"  Batch Size: {args.batch_size}")
    print()

    # Check if data files exist
    if not os.path.exists(RELBASE_DATA_FILE):
        print(f"❌ Error: Data file not found: {RELBASE_DATA_FILE}")
        sys.exit(1)

    if not os.path.exists(MAPPING_FILE):
        print(f"❌ Error: Mapping file not found: {MAPPING_FILE}")
        sys.exit(1)

    print(f"  ✅ Data file: {RELBASE_DATA_FILE}")
    print(f"  ✅ Mapping file: {MAPPING_FILE}")

    # Load JSON data
    print("\n📖 Loading JSON data...")
    with open(RELBASE_DATA_FILE, 'r') as f:
        relbase_data = json.load(f)

    with open(MAPPING_FILE, 'r') as f:
        mapping_data = json.load(f)

    print(f"  ✅ Loaded {relbase_data['summary']['total_documents']} documents")
    print(f"  ✅ Loaded {len(mapping_data.get('mappings', {}).get('exact', []))} exact mappings")

    # Connect to database
    print("\n🔌 Connecting to database...")
    conn = psycopg2.connect(DB_URL)
    print("  ✅ Connected")

    try:
        loader = RelbaseDataLoader(conn, dry_run=args.dry_run)

        # Step 1: Ensure channel exists
        print("\n1️⃣  Ensuring Relbase channel exists...")
        channel_id = loader.ensure_channel_exists()

        # Step 2: Load product mappings
        print("\n2️⃣  Loading product mappings...")
        loader.load_mappings(mapping_data)

        # Step 3: Load orders and order items
        print("\n3️⃣  Loading orders and order items...")
        loader.load_orders(relbase_data, channel_id, batch_size=args.batch_size)

        # Print summary
        loader.print_summary()

        if args.dry_run:
            print("\n🔍 DRY RUN COMPLETE - No changes were made to the database")
        else:
            print("\n✅ MIGRATION COMPLETE")

    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        import traceback
        traceback.print_exc()
        conn.rollback()
        sys.exit(1)

    finally:
        conn.close()


if __name__ == "__main__":
    main()
