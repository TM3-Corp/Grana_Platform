#!/usr/bin/env python3
"""
Fix missing customer data for orders that have customer_id_relbase in notes but no customer_id.

This script:
1. Finds all orders with missing customer_id that have customer_id_relbase in customer_notes
2. Fetches customer data from Relbase API
3. Creates customer records in our database
4. Updates orders to link them to the new customers
"""

import psycopg2
import requests
import json
import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env from backend directory
backend_dir = Path(__file__).parent.parent.parent / 'backend'
load_dotenv(backend_dir / '.env')

DATABASE_URL = os.getenv('DATABASE_URL')
RELBASE_API_URL = os.getenv('RELBASE_API_URL')
RELBASE_COMPANY_TOKEN = os.getenv('RELBASE_COMPANY_TOKEN')
RELBASE_USER_TOKEN = os.getenv('RELBASE_USER_TOKEN')

def fetch_relbase_customer(customer_id: int) -> dict:
    """Fetch customer details from RelBase API"""
    headers = {
        'company': RELBASE_COMPANY_TOKEN,
        'authorization': RELBASE_USER_TOKEN
    }
    url = f"{RELBASE_API_URL}/clientes/{customer_id}"

    response = requests.get(url, headers=headers, timeout=30)
    response.raise_for_status()
    return response.json().get('data', {})

def main():
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()

    # Find orders with missing customer_id that have customer_id_relbase in notes
    cur.execute("""
        SELECT
            o.id,
            o.external_id,
            o.customer_notes
        FROM orders o
        WHERE o.source = 'relbase'
          AND o.customer_id IS NULL
          AND o.customer_notes IS NOT NULL
          AND o.customer_notes::jsonb ? 'customer_id_relbase'
          AND (o.customer_notes::jsonb->>'customer_id_relbase') IS NOT NULL
    """)

    orders_to_fix = cur.fetchall()
    print(f"Found {len(orders_to_fix)} orders with missing customer_id to fix")

    customers_created = 0
    orders_updated = 0

    for order_id, external_id, customer_notes in orders_to_fix:
        notes = json.loads(customer_notes) if customer_notes else {}
        customer_id_relbase = notes.get('customer_id_relbase')

        if not customer_id_relbase:
            continue

        # Check if customer already exists
        cur.execute("""
            SELECT id, name FROM customers
            WHERE external_id = %s AND source = 'relbase'
        """, (str(customer_id_relbase),))

        existing = cur.fetchone()

        if existing:
            customer_id = existing[0]
            print(f"  Order {external_id}: Customer {customer_id_relbase} already exists as ID {customer_id}")
        else:
            # Fetch from Relbase API
            try:
                cust_data = fetch_relbase_customer(customer_id_relbase)

                cur.execute("""
                    INSERT INTO customers
                    (external_id, source, name, rut, email, phone, address, created_at)
                    VALUES (%s, 'relbase', %s, %s, %s, %s, %s, NOW())
                    RETURNING id
                """, (
                    str(customer_id_relbase),
                    cust_data.get('name', f'Customer {customer_id_relbase}'),
                    cust_data.get('rut', ''),
                    cust_data.get('email', ''),
                    cust_data.get('phone', ''),
                    cust_data.get('address', '')
                ))
                customer_id = cur.fetchone()[0]
                customers_created += 1
                print(f"  ✅ Created customer: {cust_data.get('name')} (Relbase ID: {customer_id_relbase}, DB ID: {customer_id})")
            except Exception as e:
                print(f"  ❌ Error creating customer {customer_id_relbase}: {e}")
                continue

        # Update order with customer_id
        cur.execute("""
            UPDATE orders SET customer_id = %s WHERE id = %s
        """, (customer_id, order_id))
        orders_updated += 1
        print(f"  📝 Updated order {external_id} with customer_id={customer_id}")

    conn.commit()
    cur.close()
    conn.close()

    print(f"\n=== Summary ===")
    print(f"Customers created: {customers_created}")
    print(f"Orders updated: {orders_updated}")

if __name__ == '__main__':
    main()
