#!/usr/bin/env python3
import psycopg2
from psycopg2.extras import RealDictCursor

DATABASE_URL = "postgresql://postgres.lypuvibmtxjaxmcmahxr:%24Ilofono1@aws-1-sa-east-1.pooler.supabase.com:6543/postgres"

try:
    conn = psycopg2.connect(DATABASE_URL)
    cursor = conn.cursor(cursor_factory=RealDictCursor)

    print("="*70)
    print("  📊 ESTADO ACTUAL DE LA BASE DE DATOS")
    print("="*70)

    # Orders by source
    print("\n  📦 ÓRDENES POR FUENTE:")
    cursor.execute("""
        SELECT
            source,
            COUNT(*) as count,
            MIN(order_date::date) as first_date,
            MAX(order_date::date) as last_date,
            SUM(total) as total_amount
        FROM orders
        GROUP BY source
        ORDER BY count DESC
    """)
    for row in cursor.fetchall():
        print(f"    {row['source']:15s}: {row['count']:4d} órdenes | ${row['total_amount']:,.0f} CLP | {row['first_date']} a {row['last_date']}")

    # 2025 orders specifically
    print("\n  📅 ÓRDENES 2025 POR FUENTE:")
    cursor.execute("""
        SELECT
            source,
            COUNT(*) as count,
            SUM(total) as total_amount
        FROM orders
        WHERE order_date >= '2025-01-01'
        GROUP BY source
        ORDER BY count DESC
    """)
    rows_2025 = cursor.fetchall()
    if rows_2025:
        for row in rows_2025:
            print(f"    {row['source']:15s}: {row['count']:4d} órdenes | ${row['total_amount']:,.0f} CLP")
    else:
        print("    ❌ No hay órdenes de 2025")

    # Products
    print("\n  🎁 PRODUCTOS:")
    cursor.execute("""
        SELECT
            COALESCE(source, 'NULL') as source,
            COUNT(*) as count
        FROM products
        GROUP BY source
        ORDER BY count DESC
    """)
    for row in cursor.fetchall():
        print(f"    {row['source']:15s}: {row['count']:4d} productos")

    # Customers
    print("\n  👥 CLIENTES:")
    cursor.execute("""
        SELECT
            source,
            COUNT(*) as count
        FROM customers
        GROUP BY source
        ORDER BY count DESC
    """)
    for row in cursor.fetchall():
        print(f"    {row['source']:15s}: {row['count']:4d} clientes")

    # Order items
    cursor.execute("SELECT COUNT(*) FROM order_items")
    print(f"\n  📝 ORDER ITEMS: {cursor.fetchone()['count']}")

    # Inventory movements
    cursor.execute("SELECT COUNT(*) FROM inventory_movements")
    print(f"  📦 INVENTORY MOVEMENTS: {cursor.fetchone()['count']}")

    cursor.close()
    conn.close()

except Exception as e:
    print(f"❌ Error: {e}")
