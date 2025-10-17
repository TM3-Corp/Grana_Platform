#!/usr/bin/env python3
import os
import psycopg2

DATABASE_URL = "postgresql://postgres.lypuvibmtxjaxmcmahxr:%24Ilofono1@aws-1-sa-east-1.pooler.supabase.com:6543/postgres"

try:
    print("Attempting to connect to database...")
    conn = psycopg2.connect(DATABASE_URL)
    print("✅ Connected successfully!")

    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM orders")
    count = cursor.fetchone()[0]
    print(f"Current orders count: {count}")

    cursor.close()
    conn.close()
    print("Connection closed")
except Exception as e:
    print(f"❌ Error: {e}")
