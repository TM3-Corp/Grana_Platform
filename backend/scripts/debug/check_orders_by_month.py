#!/usr/bin/env python3
import psycopg2
from psycopg2.extras import RealDictCursor

DATABASE_URL = "postgresql://postgres.lypuvibmtxjaxmcmahxr:%24Ilofono1@aws-1-sa-east-1.pooler.supabase.com:6543/postgres"

conn = psycopg2.connect(DATABASE_URL)
cursor = conn.cursor(cursor_factory=RealDictCursor)

# Órdenes 2025 por mes
print("="*80)
print("  📅 ÓRDENES 2025 POR MES Y FUENTE")
print("="*80)
cursor.execute("""
    SELECT
        TO_CHAR(order_date, 'YYYY-MM') as mes,
        source,
        COUNT(*) as count,
        SUM(total) as total
    FROM orders
    WHERE order_date >= '2025-01-01' AND order_date < '2026-01-01'
    GROUP BY mes, source
    ORDER BY mes, source
""")

for row in cursor.fetchall():
    print(f"  {row['mes']} | {row['source']:15s} | {row['count']:4d} órdenes | ${row['total']:,.0f} CLP")

# Total por mes
print()
print("="*80)
print("  📊 TOTAL POR MES (todas las fuentes)")
print("="*80)
cursor.execute("""
    SELECT
        TO_CHAR(order_date, 'YYYY-MM') as mes,
        COUNT(*) as count,
        SUM(total) as total
    FROM orders
    WHERE order_date >= '2025-01-01' AND order_date < '2026-01-01'
    GROUP BY mes
    ORDER BY mes
""")

total_orders = 0
total_revenue = 0
for row in cursor.fetchall():
    total_orders += row['count']
    total_revenue += row['total']
    print(f"  {row['mes']} | {row['count']:4d} órdenes | ${row['total']:,.0f} CLP")

print()
print("="*80)
print(f"  ✅ TOTAL 2025: {total_orders} órdenes | ${total_revenue:,.0f} CLP")
print("="*80)

cursor.close()
conn.close()
