#!/usr/bin/env python3
"""
Carga BULK optimizada de Shopify 2025
Usa execute_batch para máxima velocidad
"""
import json
from datetime import datetime
import psycopg2
from psycopg2.extras import execute_batch

SHOPIFY_CACHE = "/home/javier/Proyectos/Grana/grana-integration/validacion_2025_corregido/cache/shopify_2025_corregido.json"
DATABASE_URL = "postgresql://postgres.lypuvibmtxjaxmcmahxr:%24Ilofono1@aws-1-sa-east-1.pooler.supabase.com:6543/postgres"

print("="*70)
print("  🚀 CARGA BULK SHOPIFY 2025")
print("="*70)

# Cargar cache
with open(SHOPIFY_CACHE, 'r') as f:
    shopify_orders = json.load(f)

shopify_2025 = [o for o in shopify_orders if o.get('created_at', '').startswith('2025')]
print(f"\n  📂 {len(shopify_2025)} órdenes Shopify 2025 en cache")

# Conectar
conn = psycopg2.connect(DATABASE_URL)
cursor = conn.cursor()

# Get existing order IDs to skip
cursor.execute("SELECT external_id FROM orders WHERE source = 'shopify'")
existing_ids = {row[0] for row in cursor.fetchall()}
print(f"  📊 {len(existing_ids)} órdenes ya en DB - serán skipped")

# Prepare batch data
customers_to_insert = []
customers_map = {}  # external_id -> db_id (will populate)
orders_to_insert = []
items_to_insert = []
products_to_insert = []
products_map = {}  # sku -> db_id

skipped = 0
errors = 0
processed = 0

print("\n  🔄 Procesando órdenes...")

for order in shopify_2025:
    try:
        order_id = str(order['id'])

        if order_id in existing_ids:
            skipped += 1
            continue

        # Extract customer
        customer = order.get('customer', {})
        if not customer or not customer.get('id'):
            errors += 1
            continue

        cust_external_id = str(customer['id'])
        cust_name = f"{customer.get('first_name', '')} {customer.get('last_name', '')}".strip() or 'Cliente Shopify'

        customers_to_insert.append((
            cust_external_id,
            'shopify',
            cust_name,
            customer.get('email'),
            customer.get('phone'),
            'person'
        ))

        # Map status
        financial_status = order.get('financial_status', 'pending')
        status_map = {
            'paid': 'completed',
            'pending': 'pending',
            'refunded': 'refunded',
            'voided': 'cancelled',
            'partially_refunded': 'completed'
        }
        status = status_map.get(financial_status, 'pending')

        # Extract shipping
        shipping_lines = order.get('shipping_lines', [])
        shipping_cost = float(shipping_lines[0]['price']) if shipping_lines else 0.0

        orders_to_insert.append((
            order_id,
            order.get('name', f"#{order_id}"),
            'shopify',
            cust_external_id,  # temporary - will replace with db ID
            float(order.get('subtotal_price', 0)),
            float(order.get('total_tax', 0)),
            shipping_cost,
            float(order.get('total_price', 0)),
            status,
            order.get('created_at'),
            datetime.now(),
            datetime.now()
        ))

        # Extract items
        for item in order.get('line_items', []):
            sku = item.get('sku') or f"SHOPIFY-{item.get('product_id', 'UNKNOWN')}"
            product_name = item.get('title', 'Producto Shopify')

            products_to_insert.append((
                sku,
                product_name,
                'shopify'
            ))

            quantity = int(item.get('quantity', 1))
            unit_price = float(item.get('price', 0))
            subtotal = unit_price * quantity

            items_to_insert.append((
                order_id,  # temporary - will replace with db order ID
                sku,  # temporary - will replace with db product ID
                quantity,
                unit_price,
                subtotal,
                subtotal
            ))

        processed += 1

        if processed % 100 == 0:
            print(f"  ⚙️  Preparado: {processed} órdenes | ⏭️  {skipped} skipped | ❌ {errors} errors")

    except Exception as e:
        errors += 1
        continue

print(f"\n  ✅ Preparación completa: {processed} órdenes a insertar")
print(f"  📦 {len(customers_to_insert)} customers, {len(orders_to_insert)} orders, {len(items_to_insert)} items")

# STEP 1: Insert customers (with ON CONFLICT)
print("\n  💾 PASO 1: Insertando customers...")
execute_batch(cursor, """
    INSERT INTO customers (external_id, source, name, email, phone, type_customer)
    VALUES (%s, %s, %s, %s, %s, %s)
    ON CONFLICT (external_id, source) DO NOTHING
""", customers_to_insert, page_size=1000)
print(f"  ✅ {len(customers_to_insert)} customers procesados")

# Build customer ID map
cursor.execute("SELECT id, external_id FROM customers WHERE source = 'shopify'")
for cust_id, external_id in cursor.fetchall():
    customers_map[external_id] = cust_id

# STEP 2: Insert products (with ON CONFLICT)
print("\n  💾 PASO 2: Insertando products...")
# Deduplicate products first
unique_products = {p[0]: p for p in products_to_insert}  # sku -> (sku, name, source)
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

# STEP 3: Insert orders with mapped customer_id
print("\n  💾 PASO 3: Insertando orders...")
orders_with_customer_ids = [
    (
        external_id, order_number, source,
        customers_map.get(customer_external_id),  # Map to DB ID
        subtotal, tax, shipping, total, status, order_date, created, updated
    )
    for (external_id, order_number, source, customer_external_id,
         subtotal, tax, shipping, total, status, order_date, created, updated) in orders_to_insert
    if customers_map.get(customer_external_id) is not None
]

execute_batch(cursor, """
    INSERT INTO orders (external_id, order_number, source, customer_id,
                       subtotal, tax_amount, shipping_cost, total,
                       status, order_date, created_at, updated_at)
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    ON CONFLICT (external_id, source) DO NOTHING
    RETURNING id, external_id
""", orders_with_customer_ids, page_size=500)
print(f"  ✅ {len(orders_with_customer_ids)} orders insertadas")

# Build order ID map
orders_map = {}
cursor.execute("SELECT id, external_id FROM orders WHERE source = 'shopify'")
for order_id, external_id in cursor.fetchall():
    orders_map[external_id] = order_id

# STEP 4: Insert order_items with mapped order_id and product_id
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
    WHERE source = 'shopify' AND order_date >= '2025-01-01'
""")
count, total = cursor.fetchone()
print(f"\n  📊 SHOPIFY 2025: {count} órdenes | ${total:,.0f} CLP")
print(f"  🎯 ESPERADO: 1,241 órdenes | $40,976,808 CLP")

cursor.close()
conn.close()
