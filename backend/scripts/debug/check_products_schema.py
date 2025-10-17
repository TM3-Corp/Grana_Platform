#!/usr/bin/env python3
"""
Check products table schema
"""
import os
from dotenv import load_dotenv
import psycopg2

load_dotenv()

def check_schema():
    """Check the products table columns"""
    database_url = os.getenv("DATABASE_URL")

    conn = psycopg2.connect(database_url)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT column_name, data_type
        FROM information_schema.columns
        WHERE table_name = 'products'
        ORDER BY ordinal_position
    """)

    columns = cursor.fetchall()

    print("\n📋 Products Table Columns:")
    print("="*60)
    for col_name, data_type in columns:
        print(f"  {col_name:30} {data_type}")

    cursor.close()
    conn.close()

if __name__ == "__main__":
    check_schema()
