#!/usr/bin/env python3
"""
Debug script to trace sync_sales_from_relbase step by step
Identifies exactly where orders are being skipped
"""
import os
import sys
import json
import requests
from datetime import datetime, timedelta

# Add the backend to path
sys.path.insert(0, '/home/paul/projects/Grana/Grana_Platform/backend')

from dotenv import load_dotenv
load_dotenv('/home/paul/projects/Grana/Grana_Platform/backend/.env')

import psycopg2

DATABASE_URL = os.getenv('DATABASE_URL')
RELBASE_BASE_URL = "https://api.relbase.cl"
RELBASE_COMPANY_TOKEN = os.getenv('RELBASE_COMPANY_TOKEN')
RELBASE_USER_TOKEN = os.getenv('RELBASE_USER_TOKEN')

def get_relbase_headers():
    return {
        'company': RELBASE_COMPANY_TOKEN,
        'authorization': RELBASE_USER_TOKEN,
        'Content-Type': 'application/json'
    }

def fetch_relbase_dtes(date_from, date_to, page=1, doc_type=33):
    """Fetch DTEs from RelBase API - exact same logic as sync_service"""
    url = f"{RELBASE_BASE_URL}/api/v1/dtes"
    headers = get_relbase_headers()
    params = {
        'type_document': doc_type,
        'start_date': date_from,
        'end_date': date_to,
        'page': page,
        'per_page': 100
    }

    print(f"\n  📡 API Request:")
    print(f"     URL: {url}")
    print(f"     Params: {params}")

    try:
        response = requests.get(url, headers=headers, params=params, timeout=60)
        print(f"     Status: {response.status_code}")

        response.raise_for_status()
        data = response.json()

        # Show response structure
        print(f"     Response keys: {list(data.keys())}")
        if 'data' in data:
            print(f"     data keys: {list(data['data'].keys())}")
            dtes = data.get('data', {}).get('dtes', [])
            print(f"     DTEs count: {len(dtes)}")
        if 'meta' in data:
            print(f"     meta: {data['meta']}")

        return data
    except Exception as e:
        print(f"     ❌ Error: {e}")
        return {}

def main():
    print("=" * 70)
    print("🔍 DEBUG: Tracing sync_sales_from_relbase step by step")
    print("=" * 70)

    # Connect to database
    conn = psycopg2.connect(DATABASE_URL)
    cursor = conn.cursor()

    # Step 1: Determine date range (same logic as sync_service)
    print("\n📅 STEP 1: Determine date range")
    print("-" * 50)

    days_back = 7  # Default in sync_service

    cursor.execute("SELECT MAX(order_date) FROM orders WHERE source = 'relbase'")
    last_date = cursor.fetchone()[0]
    print(f"   Last order date in DB: {last_date}")

    if last_date:
        date_from = (last_date - timedelta(days=days_back)).strftime('%Y-%m-%d')
    else:
        date_from = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')

    date_to = datetime.now().strftime('%Y-%m-%d')

    print(f"   Calculated date_from: {date_from}")
    print(f"   Calculated date_to: {date_to}")

    # Step 2: Get fallback channel ID
    print("\n🏷️ STEP 2: Get fallback channel ID")
    print("-" * 50)

    cursor.execute("SELECT id FROM channels WHERE code = 'relbase'")
    fallback_channel_result = cursor.fetchone()
    fallback_channel_id = fallback_channel_result[0] if fallback_channel_result else None
    print(f"   Fallback channel ID: {fallback_channel_id}")

    if not fallback_channel_id:
        print("   ⚠️ WARNING: No 'relbase' channel found - this might cause issues!")

    # Step 3: Fetch DTEs from RelBase
    print("\n📦 STEP 3: Fetch DTEs from RelBase API")
    print("-" * 50)

    document_types = [33, 39]  # Factura, Boleta
    total_dtes = 0
    new_dtes = []
    existing_dtes = []

    for doc_type in document_types:
        doc_name = "Factura" if doc_type == 33 else "Boleta"
        print(f"\n  Fetching {doc_name} (type={doc_type})...")

        page = 1
        while True:
            dte_response = fetch_relbase_dtes(date_from, date_to, page, doc_type)

            if not dte_response:
                print("     Empty response - breaking")
                break

            dtes = dte_response.get('data', {}).get('dtes', [])

            if not dtes:
                print("     No DTEs in response - breaking")
                break

            total_dtes += len(dtes)

            # Check each DTE
            for dte in dtes:
                dte_id = dte.get('id')
                folio = dte.get('folio')
                date_str = dte.get('start_date') or dte.get('created_at')

                # Check if exists in DB
                cursor.execute("""
                    SELECT id FROM orders
                    WHERE external_id = %s AND source = 'relbase'
                """, (str(dte_id),))

                existing = cursor.fetchone()

                if existing:
                    existing_dtes.append({'id': dte_id, 'folio': folio, 'date': date_str})
                else:
                    new_dtes.append({'id': dte_id, 'folio': folio, 'date': date_str})

            # Check pagination
            pagination = dte_response.get('meta', {})
            current_page = pagination.get('current_page', 1)
            total_pages = pagination.get('total_pages', 1)
            print(f"     Page {current_page}/{total_pages}")

            if page >= total_pages:
                break

            page += 1

    # Step 4: Summary
    print("\n📊 STEP 4: Analysis Summary")
    print("-" * 50)
    print(f"   Total DTEs fetched: {total_dtes}")
    print(f"   New DTEs (not in DB): {len(new_dtes)}")
    print(f"   Existing DTEs (in DB): {len(existing_dtes)}")

    if new_dtes:
        print(f"\n   🆕 New DTEs that should be created:")
        for dte in new_dtes[:10]:  # Show first 10
            print(f"      DTE {dte['id']}, folio={dte['folio']}, date={dte['date']}")
        if len(new_dtes) > 10:
            print(f"      ... and {len(new_dtes) - 10} more")

    if not new_dtes:
        print("\n   ✅ All DTEs already exist in database - no new orders to create")
        print("   This explains why sync shows '0 records processed'")

    # Step 5: Check what's happening with individual DTE
    if new_dtes:
        print("\n🔬 STEP 5: Deep dive into first new DTE")
        print("-" * 50)

        first_dte = new_dtes[0]
        dte_id = first_dte['id']
        print(f"   Fetching details for DTE {dte_id}...")

        # Fetch DTE detail
        url = f"{RELBASE_BASE_URL}/api/v1/dtes/{dte_id}"
        headers = get_relbase_headers()

        try:
            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()
            dte_detail = response.json()

            dte_data = dte_detail.get('data', {})
            print(f"\n   DTE Detail Response:")
            print(f"     Keys: {list(dte_data.keys())}")
            print(f"     Folio: {dte_data.get('folio')}")
            print(f"     Type: {dte_data.get('type_document')}")
            print(f"     Total: ${dte_data.get('amount_total', 0):,.0f}")
            print(f"     Customer ID: {dte_data.get('customer_id')}")
            print(f"     Channel ID: {dte_data.get('channel_id')}")
            print(f"     SII Status: {dte_data.get('sii_status')}")

            products = dte_data.get('products', [])
            print(f"     Products: {len(products)}")
            for p in products[:3]:
                print(f"       - {p.get('code')}: {p.get('name')} x{p.get('quantity')}")

            # Check customer mapping
            customer_id_relbase = dte_data.get('customer_id')
            if customer_id_relbase:
                cursor.execute("""
                    SELECT id, name FROM customers
                    WHERE external_id = %s AND source = 'relbase'
                """, (str(customer_id_relbase),))
                customer = cursor.fetchone()
                if customer:
                    print(f"\n   ✅ Customer mapped: {customer[1]} (ID: {customer[0]})")
                else:
                    print(f"\n   ⚠️ Customer NOT in DB: will be fetched from API")

            # Check channel mapping
            channel_id_relbase = dte_data.get('channel_id')
            if channel_id_relbase:
                cursor.execute("""
                    SELECT id, name FROM channels
                    WHERE external_id = %s AND source = 'relbase'
                """, (str(channel_id_relbase),))
                channel = cursor.fetchone()
                if channel:
                    print(f"   ✅ Channel mapped: {channel[1]} (ID: {channel[0]})")
                else:
                    print(f"   ⚠️ Channel {channel_id_relbase} NOT in DB: will use fallback")

        except Exception as e:
            print(f"   ❌ Error fetching DTE detail: {e}")

    # Step 6: Check sync_logs for clues
    print("\n📋 STEP 6: Recent sync_logs")
    print("-" * 50)

    cursor.execute("""
        SELECT id, source, sync_type, status, records_processed, records_failed,
               details, completed_at
        FROM sync_logs
        WHERE sync_type = 'orders'
        ORDER BY completed_at DESC
        LIMIT 5
    """)
    logs = cursor.fetchall()

    for log in logs:
        log_id, source, sync_type, status, records, failed, details, completed = log
        print(f"\n   Log #{log_id} ({completed}):")
        print(f"     Status: {status}")
        print(f"     Records processed: {records}")
        print(f"     Records failed: {failed}")
        if details:
            d = json.loads(details) if isinstance(details, str) else details
            print(f"     Created: {d.get('orders_created', 'N/A')}")
            print(f"     Updated: {d.get('orders_updated', 'N/A')}")
            if d.get('errors'):
                print(f"     Errors: {d['errors'][:3]}")

    cursor.close()
    conn.close()

    print("\n" + "=" * 70)
    print("🏁 Debug complete")
    print("=" * 70)

if __name__ == "__main__":
    main()
