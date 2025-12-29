#!/usr/bin/env python3
"""
Comprehensive Customer Mapping Verification (2024-2025)

This script verifies ALL Relbase orders from 2024-2025 against the Relbase API
to ensure customer mappings are correct.

Scope: 1,897 unverified orders
Estimated time: ~20 minutes
"""

import psycopg2
import psycopg2.extras
import requests
import time
import json
from datetime import datetime
from collections import defaultdict

# Database connection (Session Pooler for WSL2 IPv4)
DATABASE_URL = "postgresql://postgres.lypuvibmtxjaxmcmahxr:%24Ilofono1@aws-1-sa-east-1.pooler.supabase.com:6543/postgres"

# Relbase API credentials
RELBASE_API_URL = "https://api.relbase.cl/api/v1"
RELBASE_HEADERS = {
    'company': '8iNGjKSPBJQ7R2su4ZtftBsP',
    'authorization': '3dk4TybsDQwiCH39AvnSHiEi'
}

# Caches
customer_cache = {}  # external_id -> {id, name}
customer_ext_cache = {}  # db_id -> external_id

def get_db_connection():
    """Get database connection"""
    return psycopg2.connect(DATABASE_URL)

def get_unverified_orders(conn):
    """Get all orders that haven't been verified yet"""
    with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
        cur.execute("""
            SELECT o.id, o.external_id, o.order_date, o.customer_notes,
                   o.customer_id, c.name as customer_name, c.external_id as customer_external_id
            FROM orders o
            LEFT JOIN customers c ON c.id = o.customer_id
            WHERE o.source = 'relbase'
            AND o.order_date >= '2024-01-01'
            AND (o.customer_notes IS NULL OR o.customer_notes::text NOT LIKE '%customer_id_relbase%')
            ORDER BY o.order_date DESC
        """)
        return cur.fetchall()

def get_relbase_order_with_retry(order_external_id, max_retries=10):
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
            elif response.status_code == 404:
                return None  # Order not found
            else:
                print(f"    HTTP {response.status_code}, retrying...")
                time.sleep(5 * (attempt + 1))
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

def get_customer_db_info(conn, external_id):
    """Get database customer ID and name from Relbase external_id"""
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

def update_order_with_verification(conn, order_id, new_customer_id, relbase_customer_id, old_customer_notes, fixed=False):
    """Update order with verified customer_id_relbase"""
    if old_customer_notes:
        try:
            notes = json.loads(old_customer_notes) if isinstance(old_customer_notes, str) else old_customer_notes
        except:
            notes = {}
    else:
        notes = {}

    notes['customer_id_relbase'] = relbase_customer_id
    notes['verified_at'] = datetime.now().isoformat()
    if fixed:
        notes['customer_mapping_fixed'] = True
        notes['fixed_at'] = datetime.now().isoformat()

    with conn.cursor() as cur:
        if new_customer_id and fixed:
            cur.execute("""
                UPDATE orders
                SET customer_id = %s,
                    customer_notes = %s,
                    updated_at = NOW()
                WHERE id = %s
            """, (new_customer_id, json.dumps(notes), order_id))
        else:
            cur.execute("""
                UPDATE orders
                SET customer_notes = %s,
                    updated_at = NOW()
                WHERE id = %s
            """, (json.dumps(notes), order_id))

    return True

def refresh_materialized_view(conn):
    """Refresh the sales_facts_mv materialized view"""
    print("\nRefreshing sales_facts_mv materialized view...")
    with conn.cursor() as cur:
        cur.execute("REFRESH MATERIALIZED VIEW sales_facts_mv")
    print("Materialized view refreshed successfully!")

def main():
    start_time = datetime.now()

    print("=" * 70)
    print("COMPREHENSIVE CUSTOMER MAPPING VERIFICATION (2024-2025)")
    print("=" * 70)
    print(f"Started at: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")

    conn = get_db_connection()

    # Get all unverified orders
    print("\nFetching unverified orders...")
    orders = get_unverified_orders(conn)
    total_orders = len(orders)
    print(f"Found {total_orders} orders to verify")

    # Statistics
    stats = {
        'total': total_orders,
        'correct': 0,
        'fixed': 0,
        'api_errors': 0,
        'customer_not_found': 0,
        'fixes_by_from_to': defaultdict(int),  # "FromCustomer -> ToCustomer": count
    }

    failed_orders = []

    print(f"\nVerifying each order against Relbase API...")
    print("-" * 70)

    batch_size = 100
    for i, order in enumerate(orders):
        order_id = order['id']
        external_id = order['external_id']
        current_customer_name = order['customer_name'] or 'UNKNOWN'
        current_customer_ext = order['customer_external_id']
        customer_notes = order['customer_notes']

        # Progress indicator
        if (i + 1) % batch_size == 0 or i == 0:
            elapsed = (datetime.now() - start_time).total_seconds()
            rate = (i + 1) / elapsed if elapsed > 0 else 0
            remaining = (total_orders - i - 1) / rate if rate > 0 else 0
            print(f"\n[{i+1}/{total_orders}] Progress: {(i+1)/total_orders*100:.1f}% | "
                  f"Elapsed: {elapsed/60:.1f}min | ETA: {remaining/60:.1f}min | "
                  f"Fixed: {stats['fixed']} | Correct: {stats['correct']}")

        # Fetch from Relbase API
        relbase_data = get_relbase_order_with_retry(external_id)
        time.sleep(0.5)  # Rate limiting

        if not relbase_data:
            stats['api_errors'] += 1
            failed_orders.append(external_id)
            continue

        relbase_customer_id = relbase_data.get('customer_id')

        if not relbase_customer_id:
            stats['api_errors'] += 1
            failed_orders.append(external_id)
            continue

        # Check if it matches current assignment
        if str(relbase_customer_id) == str(current_customer_ext):
            # Correct assignment - just add verification
            stats['correct'] += 1
            update_order_with_verification(conn, order_id, None, relbase_customer_id, customer_notes, fixed=False)
        else:
            # Mismatch! Need to fix
            correct_customer = get_customer_db_info(conn, relbase_customer_id)

            if not correct_customer:
                stats['customer_not_found'] += 1
                # Still add the relbase customer_id for audit
                update_order_with_verification(conn, order_id, None, relbase_customer_id, customer_notes, fixed=False)
                print(f"  Order {external_id}: Customer {relbase_customer_id} not in DB (was {current_customer_name})")
                continue

            # Update the order
            update_order_with_verification(
                conn, order_id, correct_customer['id'], relbase_customer_id, customer_notes, fixed=True
            )
            stats['fixed'] += 1

            # Track the fix
            fix_key = f"{current_customer_name[:30]} -> {correct_customer['name'][:30]}"
            stats['fixes_by_from_to'][fix_key] += 1

            # Print significant fixes (customers with many orders)
            if stats['fixes_by_from_to'][fix_key] <= 3:  # Only print first 3 of each type
                print(f"  FIXED: Order {external_id} | {current_customer_name[:25]} -> {correct_customer['name'][:25]}")

        # Commit every 100 orders
        if (i + 1) % batch_size == 0:
            conn.commit()

    # Final commit
    conn.commit()

    # Retry failed orders
    if failed_orders:
        print(f"\n{'=' * 70}")
        print(f"RETRYING {len(failed_orders)} FAILED ORDERS")
        print("=" * 70)

        for i, external_id in enumerate(failed_orders[:50]):  # Limit retries to 50
            print(f"[Retry {i+1}/{min(len(failed_orders), 50)}] Order {external_id}")
            time.sleep(3)

            relbase_data = get_relbase_order_with_retry(external_id, max_retries=15)

            if not relbase_data:
                print("  Still failed")
                continue

            relbase_customer_id = relbase_data.get('customer_id')
            if not relbase_customer_id:
                continue

            # Get current order info
            with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                cur.execute("""
                    SELECT o.id, o.customer_notes, o.customer_id, c.external_id as customer_external_id,
                           c.name as customer_name
                    FROM orders o
                    LEFT JOIN customers c ON c.id = o.customer_id
                    WHERE o.external_id = %s
                """, (external_id,))
                order = cur.fetchone()

            if not order:
                continue

            current_customer_ext = order['customer_external_id']

            if str(relbase_customer_id) == str(current_customer_ext):
                stats['api_errors'] -= 1
                stats['correct'] += 1
                update_order_with_verification(conn, order['id'], None, relbase_customer_id, order['customer_notes'], fixed=False)
                print("  OK (correct)")
            else:
                correct_customer = get_customer_db_info(conn, relbase_customer_id)
                if correct_customer:
                    update_order_with_verification(
                        conn, order['id'], correct_customer['id'], relbase_customer_id, order['customer_notes'], fixed=True
                    )
                    stats['api_errors'] -= 1
                    stats['fixed'] += 1
                    print(f"  FIXED -> {correct_customer['name']}")

        conn.commit()

    # Summary
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()

    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"Total orders verified: {stats['total']}")
    print(f"Already correct: {stats['correct']}")
    print(f"Fixed (wrong customer): {stats['fixed']}")
    print(f"API errors (unrecoverable): {stats['api_errors']}")
    print(f"Customer not in DB: {stats['customer_not_found']}")

    completion_rate = ((stats['correct'] + stats['fixed']) / stats['total']) * 100 if stats['total'] > 0 else 0
    print(f"\nCompletion rate: {completion_rate:.1f}%")
    print(f"Duration: {duration/60:.1f} minutes")

    if stats['fixes_by_from_to']:
        print("\n" + "-" * 70)
        print("FIXES BY CUSTOMER TRANSITION:")
        print("-" * 70)
        for transition, count in sorted(stats['fixes_by_from_to'].items(), key=lambda x: -x[1]):
            print(f"  {transition}: {count} orders")

    # Refresh materialized view if any fixes were made
    if stats['fixed'] > 0:
        refresh_materialized_view(conn)
        conn.commit()

    conn.close()

    print("\n" + "=" * 70)
    print(f"DONE! Completed at: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)

    return stats

if __name__ == "__main__":
    main()
