#!/usr/bin/env python3
"""
Fix Walmart Non-BARRAS Order Customer Mappings

This script checks all Walmart orders that have non-BARRAS products
and verifies them against Relbase API with retry logic for 100% completion.
"""

import psycopg2
import psycopg2.extras
import requests
import time
import json
from datetime import datetime

# Database connection (Session Pooler for WSL2 IPv4)
DATABASE_URL = "postgresql://postgres.lypuvibmtxjaxmcmahxr:%24Ilofono1@aws-1-sa-east-1.pooler.supabase.com:6543/postgres"

# Relbase API credentials
RELBASE_API_URL = "https://api.relbase.cl/api/v1"
RELBASE_HEADERS = {
    'company': '8iNGjKSPBJQ7R2su4ZtftBsP',
    'authorization': '3dk4TybsDQwiCH39AvnSHiEi'
}

# Customer mapping cache (external_id -> db_id)
customer_cache = {}

def get_db_connection():
    """Get database connection"""
    return psycopg2.connect(DATABASE_URL)

def get_walmart_non_barras_orders(conn):
    """Get all Walmart orders with non-BARRAS products"""
    with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
        cur.execute("""
            SELECT DISTINCT o.id, o.external_id, o.order_date, o.customer_notes,
                   o.customer_id, c.name as customer_name, c.external_id as customer_external_id
            FROM orders o
            LEFT JOIN customers c ON c.id = o.customer_id
            LEFT JOIN order_items oi ON oi.order_id = o.id
            LEFT JOIN products p ON p.sku = oi.product_sku
            WHERE o.source = 'relbase'
            AND c.name ILIKE '%walmart%'
            AND p.category IS NOT NULL
            AND p.category <> 'BARRAS'
            ORDER BY o.order_date DESC
        """)
        return cur.fetchall()

def get_relbase_order_with_retry(order_external_id, max_retries=5):
    """Fetch order details from Relbase API with retry logic"""
    url = f"{RELBASE_API_URL}/dtes/{order_external_id}"

    for attempt in range(max_retries):
        try:
            response = requests.get(url, headers=RELBASE_HEADERS, timeout=60)
            if response.status_code == 200:
                data = response.json()
                if 'data' in data:
                    return data['data']
                return None
            elif response.status_code == 429:  # Rate limited
                wait_time = 30 * (attempt + 1)
                print(f"    Rate limited, waiting {wait_time}s...")
                time.sleep(wait_time)
            else:
                return None
        except requests.exceptions.Timeout:
            wait_time = 10 * (attempt + 1)
            print(f"    Timeout on attempt {attempt + 1}, waiting {wait_time}s...")
            time.sleep(wait_time)
        except requests.exceptions.ConnectionError:
            wait_time = 15 * (attempt + 1)
            print(f"    Connection error on attempt {attempt + 1}, waiting {wait_time}s...")
            time.sleep(wait_time)
        except Exception as e:
            print(f"    Error on attempt {attempt + 1}: {e}")
            time.sleep(5)

    return None

def get_customer_db_id(conn, external_id):
    """Get database customer ID from Relbase external_id"""
    if external_id in customer_cache:
        return customer_cache[external_id]

    with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
        cur.execute("""
            SELECT id, name FROM customers
            WHERE external_id = %s AND source = 'relbase'
        """, (str(external_id),))
        result = cur.fetchone()
        if result:
            customer_cache[external_id] = {'id': result['id'], 'name': result['name']}
            return customer_cache[external_id]
    return None

def update_order_customer(conn, order_id, new_customer_id, relbase_customer_id, old_customer_notes):
    """Update order with correct customer and add audit trail"""
    if old_customer_notes:
        try:
            notes = json.loads(old_customer_notes) if isinstance(old_customer_notes, str) else old_customer_notes
        except:
            notes = {}
    else:
        notes = {}

    notes['customer_id_relbase'] = relbase_customer_id
    notes['customer_mapping_fixed'] = True
    notes['fixed_at'] = datetime.now().isoformat()

    with conn.cursor() as cur:
        cur.execute("""
            UPDATE orders
            SET customer_id = %s,
                customer_notes = %s,
                updated_at = NOW()
            WHERE id = %s
        """, (new_customer_id, json.dumps(notes), order_id))

    return True

def refresh_materialized_view(conn):
    """Refresh the sales_facts_mv materialized view"""
    print("\nRefreshing sales_facts_mv materialized view...")
    with conn.cursor() as cur:
        cur.execute("REFRESH MATERIALIZED VIEW sales_facts_mv")
    print("Materialized view refreshed successfully!")

def main():
    print("=" * 70)
    print("FIX WALMART NON-BARRAS ORDER CUSTOMER MAPPINGS")
    print("(With retry logic for 100% completion)")
    print("=" * 70)

    conn = get_db_connection()

    # Get all Walmart orders with non-BARRAS products
    print("\nFetching Walmart orders with non-BARRAS products...")
    orders = get_walmart_non_barras_orders(conn)
    total_orders = len(orders)
    print(f"Found {total_orders} orders to verify")

    # Statistics
    stats = {
        'total': total_orders,
        'correct': 0,
        'fixed': 0,
        'api_errors': 0,
        'customer_not_found': 0,
        'by_correct_customer': {}
    }

    failed_orders = []

    print(f"\nVerifying each order against Relbase API...")
    print("-" * 70)

    for i, order in enumerate(orders):
        order_id = order['id']
        external_id = order['external_id']
        current_customer_ext = order['customer_external_id']
        customer_notes = order['customer_notes']
        order_date = order['order_date']

        print(f"[{i+1}/{total_orders}] Checking order {external_id}...", end=" ")

        # Fetch from Relbase API with retry
        relbase_data = get_relbase_order_with_retry(external_id)
        time.sleep(0.5)  # Rate limiting between successful requests

        if not relbase_data:
            stats['api_errors'] += 1
            failed_orders.append(external_id)
            print("FAILED (will retry later)")
            continue

        relbase_customer_id = relbase_data.get('customer_id')

        if not relbase_customer_id:
            stats['api_errors'] += 1
            failed_orders.append(external_id)
            print("NO CUSTOMER ID")
            continue

        # Check if it matches
        if str(relbase_customer_id) == str(current_customer_ext):
            stats['correct'] += 1
            customer_name = order['customer_name']
            if customer_name not in stats['by_correct_customer']:
                stats['by_correct_customer'][customer_name] = 0
            stats['by_correct_customer'][customer_name] += 1
            print(f"OK (correct: {customer_name})")
            continue

        # Mismatch! Need to fix
        correct_customer = get_customer_db_id(conn, relbase_customer_id)

        if not correct_customer:
            stats['customer_not_found'] += 1
            print(f"Customer {relbase_customer_id} not in DB")
            continue

        # Update the order
        update_order_customer(conn, order_id, correct_customer['id'], relbase_customer_id, customer_notes)
        stats['fixed'] += 1

        correct_name = correct_customer['name']
        if correct_name not in stats['by_correct_customer']:
            stats['by_correct_customer'][correct_name] = 0
        stats['by_correct_customer'][correct_name] += 1

        print(f"FIXED -> {correct_name}")

    # Retry failed orders with longer delays
    if failed_orders:
        print(f"\n{'=' * 70}")
        print(f"RETRYING {len(failed_orders)} FAILED ORDERS (with longer delays)")
        print("=" * 70)

        for i, external_id in enumerate(failed_orders):
            print(f"\n[Retry {i+1}/{len(failed_orders)}] Order {external_id}")
            time.sleep(5)  # Extra delay before retry

            # Get order info again
            with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                cur.execute("""
                    SELECT o.id, o.external_id, o.order_date, o.customer_notes,
                           o.customer_id, c.name as customer_name, c.external_id as customer_external_id
                    FROM orders o
                    LEFT JOIN customers c ON c.id = o.customer_id
                    WHERE o.external_id = %s
                """, (external_id,))
                order = cur.fetchone()

            if not order:
                print("  Order not found in DB")
                continue

            relbase_data = get_relbase_order_with_retry(external_id, max_retries=10)

            if not relbase_data:
                print("  Still failed after retries")
                continue

            relbase_customer_id = relbase_data.get('customer_id')
            if not relbase_customer_id:
                print("  No customer_id in response")
                continue

            current_customer_ext = order['customer_external_id']

            if str(relbase_customer_id) == str(current_customer_ext):
                stats['api_errors'] -= 1
                stats['correct'] += 1
                print(f"  OK (correct: Walmart)")
            else:
                correct_customer = get_customer_db_id(conn, relbase_customer_id)
                if correct_customer:
                    update_order_customer(conn, order['id'], correct_customer['id'],
                                         relbase_customer_id, order['customer_notes'])
                    stats['api_errors'] -= 1
                    stats['fixed'] += 1
                    print(f"  FIXED -> {correct_customer['name']}")
                else:
                    print(f"  Customer {relbase_customer_id} not in DB")

    # Commit
    conn.commit()

    # Summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"Total orders checked: {stats['total']}")
    print(f"Already correct: {stats['correct']}")
    print(f"Fixed: {stats['fixed']}")
    print(f"API errors (unrecoverable): {stats['api_errors']}")
    print(f"Customer not in DB: {stats['customer_not_found']}")

    completion_rate = ((stats['correct'] + stats['fixed']) / stats['total']) * 100
    print(f"\nCompletion rate: {completion_rate:.1f}%")

    print("\nBreakdown by customer:")
    for customer, count in sorted(stats['by_correct_customer'].items(), key=lambda x: -x[1]):
        print(f"  {customer}: {count} orders")

    # Refresh view if fixes made
    if stats['fixed'] > 0:
        refresh_materialized_view(conn)
        conn.commit()

    conn.close()

    print("\n" + "=" * 70)
    print("DONE!")
    print("=" * 70)

    return stats

if __name__ == "__main__":
    main()
