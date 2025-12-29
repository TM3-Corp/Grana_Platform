#!/usr/bin/env python3
"""
Fix Walmart Order Customer Mappings

This script:
1. Gets all orders currently assigned to Walmart (customer_id = 2284)
2. Verifies each order against Relbase API to get correct customer_id
3. Updates orders with incorrect customer mappings
4. Adds customer_id_relbase to customer_notes for audit trail
5. Refreshes the materialized view

Based on investigation:
- 42% of Walmart orders are incorrectly mapped
- Many should be CENCOSUD (596810) or RENDIC (596821)
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

def get_walmart_orders(conn):
    """Get all orders currently assigned to Walmart"""
    with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
        cur.execute("""
            SELECT o.id, o.external_id, o.customer_id, o.customer_notes, o.order_date,
                   c.name as customer_name, c.external_id as customer_external_id
            FROM orders o
            LEFT JOIN customers c ON c.id = o.customer_id
            WHERE o.source = 'relbase'
            AND c.name ILIKE '%walmart%'
            ORDER BY o.order_date DESC
        """)
        return cur.fetchall()

def get_relbase_order(order_external_id):
    """Fetch order details from Relbase API"""
    url = f"{RELBASE_API_URL}/dtes/{order_external_id}"
    try:
        response = requests.get(url, headers=RELBASE_HEADERS, timeout=30)
        if response.status_code == 200:
            data = response.json()
            if 'data' in data:
                return data['data']
        return None
    except Exception as e:
        print(f"  Error fetching order {order_external_id}: {e}")
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
    # Parse existing notes or create new
    if old_customer_notes:
        try:
            notes = json.loads(old_customer_notes) if isinstance(old_customer_notes, str) else old_customer_notes
        except:
            notes = {}
    else:
        notes = {}

    # Add audit trail
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

def add_audit_trail_only(conn, order_id, relbase_customer_id, old_customer_notes):
    """Add customer_id_relbase to notes without changing customer"""
    if old_customer_notes:
        try:
            notes = json.loads(old_customer_notes) if isinstance(old_customer_notes, str) else old_customer_notes
        except:
            notes = {}
    else:
        notes = {}

    # Add audit trail
    notes['customer_id_relbase'] = relbase_customer_id

    with conn.cursor() as cur:
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
    print("=" * 70)
    print("FIX WALMART ORDER CUSTOMER MAPPINGS")
    print("=" * 70)

    conn = get_db_connection()

    # Get all Walmart orders
    print("\nFetching all Walmart orders...")
    orders = get_walmart_orders(conn)
    total_orders = len(orders)
    print(f"Found {total_orders} orders assigned to Walmart")

    # Statistics
    stats = {
        'total': total_orders,
        'correct': 0,
        'fixed': 0,
        'api_errors': 0,
        'customer_not_found': 0,
        'by_correct_customer': {}
    }

    # Process each order
    print(f"\nProcessing orders (checking each against Relbase API)...")
    print("-" * 70)

    for i, order in enumerate(orders):
        order_id = order['id']
        external_id = order['external_id']
        current_customer_id = order['customer_id']
        current_customer_ext = order['customer_external_id']
        customer_notes = order['customer_notes']
        order_date = order['order_date']

        # Progress indicator
        if (i + 1) % 10 == 0 or i == 0:
            print(f"\nProgress: {i + 1}/{total_orders} orders processed...")

        # Fetch from Relbase API
        relbase_data = get_relbase_order(external_id)
        time.sleep(0.17)  # Rate limiting

        if not relbase_data:
            stats['api_errors'] += 1
            print(f"  [{i+1}] Order {external_id}: API error")
            continue

        # Get correct customer_id from Relbase
        relbase_customer_id = relbase_data.get('customer_id')

        if not relbase_customer_id:
            stats['api_errors'] += 1
            print(f"  [{i+1}] Order {external_id}: No customer_id in API response")
            continue

        # Check if it matches current assignment
        if str(relbase_customer_id) == str(current_customer_ext):
            # Correct assignment, just add audit trail if missing
            stats['correct'] += 1

            # Track correct customer
            customer_name = order['customer_name']
            if customer_name not in stats['by_correct_customer']:
                stats['by_correct_customer'][customer_name] = 0
            stats['by_correct_customer'][customer_name] += 1

            # Add audit trail if not present
            if customer_notes:
                try:
                    notes = json.loads(customer_notes) if isinstance(customer_notes, str) else customer_notes
                    if 'customer_id_relbase' not in notes:
                        add_audit_trail_only(conn, order_id, relbase_customer_id, customer_notes)
                except:
                    add_audit_trail_only(conn, order_id, relbase_customer_id, customer_notes)
            else:
                add_audit_trail_only(conn, order_id, relbase_customer_id, customer_notes)

            continue

        # Mismatch! Need to fix
        # Find correct customer in our database
        correct_customer = get_customer_db_id(conn, relbase_customer_id)

        if not correct_customer:
            stats['customer_not_found'] += 1
            print(f"  [{i+1}] Order {external_id}: Customer {relbase_customer_id} not in DB")
            continue

        # Update the order
        update_order_customer(conn, order_id, correct_customer['id'], relbase_customer_id, customer_notes)
        stats['fixed'] += 1

        # Track which customer it should be
        correct_name = correct_customer['name']
        if correct_name not in stats['by_correct_customer']:
            stats['by_correct_customer'][correct_name] = 0
        stats['by_correct_customer'][correct_name] += 1

        print(f"  [{i+1}] Order {external_id} ({order_date}): Fixed -> {correct_name}")

    # Commit all changes
    conn.commit()

    # Print summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"Total orders processed: {stats['total']}")
    print(f"Already correct (Walmart): {stats['correct']}")
    print(f"Fixed (wrong customer): {stats['fixed']}")
    print(f"API errors: {stats['api_errors']}")
    print(f"Customer not in DB: {stats['customer_not_found']}")

    print("\nBreakdown by correct customer:")
    for customer, count in sorted(stats['by_correct_customer'].items(), key=lambda x: -x[1]):
        print(f"  {customer}: {count} orders")

    # Refresh materialized view
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
