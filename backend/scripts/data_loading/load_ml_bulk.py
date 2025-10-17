#!/usr/bin/env python3
"""
Carga BULK optimizada de MercadoLibre 2025
"""
import json
from datetime import datetime
import psycopg2
from psycopg2.extras import execute_batch

ML_CACHE = "/home/javier/Proyectos/Grana/grana-integration/validacion_2025_corregido/cache/mercadolibre_2025_corregido.json"
DATABASE_URL = "postgresql://postgres.lypuvibmtxjaxmcmahxr:%24Ilofono1@aws-1-sa-east-1.pooler.supabase.com:6543/postgres"

print("="*70)
print("  🚀 CARGA BULK MERCADOLIBRE 2025")
print("="*70)

# Cargar cache
with open(ML_CACHE, 'r') as f:
    ml_orders = json.load(f)

ml_2025 = [o for o in ml_orders if o.get('date_created', '').startswith('2025')]
print(f"\n  📂 {len(ml_2025)} órdenes MercadoLibre 2025 en cache")

# Conectar
conn = psycopg2.connect(DATABASE_URL)
cursor = conn.cursor()

# Get existing order IDs to skip
cursor.execute("SELECT external_id FROM orders WHERE source = 'mercadolibre'")
existing_ids = {row[0] for row in cursor.fetchall()}
print(f"  📊 {len(existing_ids)} órdenes ya en DB - serán skipped")

# Prepare batch data
customers_to_insert = []
customers_map = {}
orders_to_insert = []
items_to_insert = []
products_to_insert = []
products_map = {}

skipped = 0
errors = 0
processed = 0

print("\n  🔄 Procesando órdenes...")

for order in ml_2025:
    try:
        order_id = str(order['id'])

        if order_id in existing_ids:
            skipped += 1
            continue

        # Extract buyer as customer
        buyer = order.get('buyer', {})
        if not buyer or not buyer.get('id'):
            errors += 1
            continue

        buyer_external_id = str(buyer['id'])
        buyer_name = buyer.get('nickname', 'Cliente MercadoLibre')

        customers_to_insert.append((
            buyer_external_id,
            'mercadolibre',
            buyer_name,
            buyer.get('email'),
            None,
            'person'
        ))

        # Map payment status
        payments = order.get('payments', [])
        payment_status = payments[0].get('status', 'pending') if payments else 'pending'

        status_map = {
            'approved': 'completed',
            'accredited': 'completed',
            'pending': 'pending',
            'in_process': 'processing',
            'rejected': 'failed',
            'cancelled': 'cancelled',
            'refunded': 'refunded'
        }
        status = status_map.get(payment_status, 'pending')

        total_amount = float(order.get('total_amount', 0))

        orders_to_insert.append((
            order_id,
            f"ML-{order_id}",
            'mercadolibre',
            buyer_external_id,
            total_amount,
            total_amount,
            status,
            order.get('date_created'),
            datetime.now(),
            datetime.now()
        ))

        # Extract items
        for item in order.get('order_items', []):
            item_data = item.get('item', {})
            sku = str(item_data.get('id', 'ML-UNKNOWN'))
            product_name = item_data.get('title', 'Producto MercadoLibre')

            products_to_insert.append((
                sku,
                product_name,
                'mercadolibre'
            ))

            quantity = int(item.get('quantity', 1))
            unit_price = float(item.get('unit_price', 0))
            subtotal = unit_price * quantity

            items_to_insert.append((
                order_id,
                sku,
                quantity,
                unit_price,
                subtotal,
                subtotal
            ))

        processed += 1

    except Exception as e:
        errors += 1
        print(f"  ⚠️  Error en orden {order.get('id')}: {str(e)[:80]}")
        continue

print(f"\n  ✅ Preparación completa: {processed} órdenes a insertar")
print(f"  📦 {len(customers_to_insert)} customers, {len(orders_to_insert)} orders, {len(items_to_insert)} items")

# STEP 1: Insert customers
print("\n  💾 PASO 1: Insertando customers...")
execute_batch(cursor, """
    INSERT INTO customers (external_id, source, name, email, phone, type_customer)
    VALUES (%s, %s, %s, %s, %s, %s)
    ON CONFLICT (external_id, source) DO NOTHING
""", customers_to_insert, page_size=1000)
print(f"  ✅ {len(customers_to_insert)} customers procesados")

# Build customer ID map
cursor.execute("SELECT id, external_id FROM customers WHERE source = 'mercadolibre'")
for cust_id, external_id in cursor.fetchall():
    customers_map[external_id] = cust_id

# STEP 2: Insert products
print("\n  💾 PASO 2: Insertando products...")
unique_products = {p[0]: p for p in products_to_insert}
execute_batch(cursor, """
    INSERT INTO products (sku, name, source, is_active)
    VALUES (%s, %s, %s, true)
    ON CONFLICT (sku) DO NOTHING
""", list(unique_products.values()), page_size=1000)
print(f"  ✅ {len(unique_products)} products procesados")

# Build product ID map
cursor.execute("SELECT id, sku FROM products")
for prod_id, sku in cursor.fetchall():
    products_map[sku] = prod_id

# STEP 3: Insert orders
print("\n  💾 PASO 3: Insertando orders...")
orders_with_customer_ids = [
    (
        external_id, order_number, source,
        customers_map.get(customer_external_id),
        subtotal, total, status, order_date, created, updated
    )
    for (external_id, order_number, source, customer_external_id,
         subtotal, total, status, order_date, created, updated) in orders_to_insert
    if customers_map.get(customer_external_id) is not None
]

execute_batch(cursor, """
    INSERT INTO orders (external_id, order_number, source, customer_id,
                       subtotal, total, status, order_date, created_at, updated_at)
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    ON CONFLICT (external_id, source) DO NOTHING
""", orders_with_customer_ids, page_size=500)
print(f"  ✅ {len(orders_with_customer_ids)} orders insertadas")

# Build order ID map
orders_map = {}
cursor.execute("SELECT id, external_id FROM orders WHERE source = 'mercadolibre'")
for order_id, external_id in cursor.fetchall():
    orders_map[external_id] = order_id

# STEP 4: Insert order_items
print("\n  💾 PASO 4: Insertando order_items...")
items_with_mapped_ids = [
    (
        orders_map.get(order_external_id),
        products_map.get(product_sku),
        quantity, unit_price, subtotal, total
    )
    for (order_external_id, product_sku, quantity, unit_price, subtotal, total) in items_to_insert
    if orders_map.get(order_external_id) is not None and products_map.get(product_sku) is not None
]

execute_batch(cursor, """
    INSERT INTO order_items (order_id, product_id, quantity, unit_price, subtotal, total)
    VALUES (%s, %s, %s, %s, %s, %s)
""", items_with_mapped_ids, page_size=1000)
print(f"  ✅ {len(items_with_mapped_ids)} items insertados")

# Commit
conn.commit()
print("\n" + "="*70)
print("  ✅ CARGA BULK COMPLETADA")
print("="*70)

# Verificar
cursor.execute("""
    SELECT COUNT(*), SUM(total)
    FROM orders
    WHERE source = 'mercadolibre' AND order_date >= '2025-01-01'
""")
count, total = cursor.fetchone()
print(f"\n  📊 MERCADOLIBRE 2025: {count} órdenes | ${total:,.0f} CLP")
print(f"  🎯 ESPERADO: 261 órdenes | $2,964,340 CLP")

cursor.close()
conn.close()
