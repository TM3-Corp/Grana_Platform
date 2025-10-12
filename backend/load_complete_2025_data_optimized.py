#!/usr/bin/env python3
"""
Carga COMPLETA de datos 2025 a tablas actuales de Supabase - OPTIMIZADA
Rellena: orders, products, customers, order_items

Author: TM3
Date: 2025-10-12
VERSIÓN OPTIMIZADA: Inserts en batch, sin OrderProcessingService
"""
import json
import os
from datetime import datetime
from typing import Dict, List
import psycopg2
from psycopg2.extras import execute_batch, RealDictCursor

# Paths a caches validados
CACHE_DIR = "/home/javier/Proyectos/Grana/grana-integration/validacion_2025_corregido/cache"
SHOPIFY_CACHE = f"{CACHE_DIR}/shopify_2025_corregido.json"
ML_CACHE = f"{CACHE_DIR}/mercadolibre_2025_corregido.json"

DATABASE_URL = "postgresql://postgres.lypuvibmtxjaxmcmahxr:%24Ilofono1@aws-1-sa-east-1.pooler.supabase.com:6543/postgres"


def get_db_connection():
    """Get database connection"""
    return psycopg2.connect(DATABASE_URL)


def clean_demo_data(conn):
    """PASO 1: Limpiar datos demo de Shopify 2022"""
    print("\n" + "="*70)
    print("  🧹 PASO 1: LIMPIANDO DATOS DEMO 2022")
    print("="*70)

    cursor = conn.cursor()

    # Contar antes
    cursor.execute("""
        SELECT COUNT(*)
        FROM orders
        WHERE source = 'shopify' AND order_date < '2025-01-01'
    """)
    demo_count = cursor.fetchone()[0]

    if demo_count == 0:
        print("   ✅ No hay datos demo para eliminar")
        return

    print(f"   📊 Órdenes demo a eliminar: {demo_count}")

    # Eliminar inventory_movements primero (foreign key constraint)
    cursor.execute("""
        DELETE FROM inventory_movements
        WHERE order_id IN (
            SELECT id FROM orders
            WHERE source = 'shopify' AND order_date < '2025-01-01'
        )
    """)
    movements_deleted = cursor.rowcount

    # Eliminar order_items (foreign key constraint)
    cursor.execute("""
        DELETE FROM order_items
        WHERE order_id IN (
            SELECT id FROM orders
            WHERE source = 'shopify' AND order_date < '2025-01-01'
        )
    """)
    items_deleted = cursor.rowcount

    # Eliminar orders
    cursor.execute("""
        DELETE FROM orders
        WHERE source = 'shopify' AND order_date < '2025-01-01'
    """)
    orders_deleted = cursor.rowcount

    conn.commit()

    print(f"   ✅ {orders_deleted} órdenes eliminadas")
    print(f"   ✅ {items_deleted} order_items eliminados")
    print(f"   ✅ {movements_deleted} inventory_movements eliminados")


def ensure_customer(cursor, customer_data: Dict) -> int:
    """Asegurar que el customer existe y retornar su ID"""
    # Try to find existing customer
    cursor.execute("""
        SELECT id FROM customers
        WHERE external_id = %s AND source = %s
    """, (customer_data['external_id'], customer_data['source']))

    result = cursor.fetchone()
    if result:
        return result[0]

    # Insert new customer
    cursor.execute("""
        INSERT INTO customers (external_id, source, name, email, phone, type_customer)
        VALUES (%s, %s, %s, %s, %s, %s)
        RETURNING id
    """, (
        customer_data['external_id'],
        customer_data['source'],
        customer_data['name'],
        customer_data.get('email'),
        customer_data.get('phone'),
        customer_data.get('type_customer', 'person')
    ))

    return cursor.fetchone()[0]


def ensure_product(cursor, sku: str, name: str, source: str) -> int:
    """Asegurar que el producto existe y retornar su ID"""
    # Try to find existing product
    cursor.execute("SELECT id FROM products WHERE sku = %s", (sku,))

    result = cursor.fetchone()
    if result:
        return result[0]

    # Insert new product
    cursor.execute("""
        INSERT INTO products (sku, name, source, is_active)
        VALUES (%s, %s, %s, true)
        ON CONFLICT (sku) DO UPDATE SET name = EXCLUDED.name
        RETURNING id
    """, (sku, name, source))

    return cursor.fetchone()[0]


def load_shopify_complete(conn):
    """PASO 2: Cargar Shopify 2025 COMPLETO - OPTIMIZADO"""
    print("\n" + "="*70)
    print("  📦 PASO 2: CARGANDO SHOPIFY 2025")
    print("="*70)

    # Cargar cache
    with open(SHOPIFY_CACHE, 'r') as f:
        shopify_orders = json.load(f)

    print(f"   📂 {len(shopify_orders)} órdenes en cache")

    # Filtrar 2025
    shopify_2025 = [o for o in shopify_orders if o.get('created_at', '').startswith('2025')]
    print(f"   📅 {len(shopify_2025)} órdenes de 2025")

    cursor = conn.cursor()
    synced = 0
    skipped = 0
    errors = 0

    for i, order in enumerate(shopify_2025, 1):
        try:
            # Start a savepoint for this order
            cursor.execute("SAVEPOINT order_savepoint")

            # Check if order already exists
            cursor.execute("""
                SELECT id FROM orders WHERE external_id = %s AND source = 'shopify'
            """, (str(order['id']),))

            if cursor.fetchone():
                cursor.execute("RELEASE SAVEPOINT order_savepoint")
                skipped += 1
                if i % 100 == 0:
                    print(f"   📊 Progreso: {i}/{len(shopify_2025)} órdenes | ✅ {synced} nuevas | ⏭️  {skipped} duplicadas | ❌ {errors} errores")
                continue

            # Extract customer
            customer = order.get('customer', {})
            if not customer or not customer.get('id'):
                # Sin customer válido, skip
                cursor.execute("ROLLBACK TO SAVEPOINT order_savepoint")
                errors += 1
                continue

            customer_data = {
                'external_id': str(customer['id']),
                'source': 'shopify',
                'name': f"{customer.get('first_name', '')} {customer.get('last_name', '')}".strip() or 'Cliente Shopify',
                'email': customer.get('email'),
                'phone': customer.get('phone'),
                'type_customer': 'person'
            }

            customer_id = ensure_customer(cursor, customer_data)

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

            # Extract shipping cost
            shipping_lines = order.get('shipping_lines', [])
            shipping_cost = float(shipping_lines[0]['price']) if shipping_lines else 0.0

            # Insert order
            cursor.execute("""
                INSERT INTO orders (
                    external_id, order_number, source, customer_id,
                    subtotal, tax_amount, shipping_cost, total,
                    status, order_date, created_at, updated_at
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
            """, (
                str(order['id']),
                order.get('name', f"#{order['id']}"),
                'shopify',
                customer_id,
                float(order.get('subtotal_price', 0)),
                float(order.get('total_tax', 0)),
                shipping_cost,
                float(order.get('total_price', 0)),
                status,
                order.get('created_at'),
                datetime.now(),
                datetime.now()
            ))

            order_id = cursor.fetchone()[0]

            # Insert order items
            line_items = order.get('line_items', [])
            for item in line_items:
                sku = item.get('sku') or f"SHOPIFY-{item.get('product_id', 'UNKNOWN')}"
                product_name = item.get('title', 'Producto Shopify')

                product_id = ensure_product(cursor, sku, product_name, 'shopify')

                quantity = int(item.get('quantity', 1))
                unit_price = float(item.get('price', 0))
                subtotal = unit_price * quantity
                total = subtotal  # Shopify incluye tax en el price total de la orden

                cursor.execute("""
                    INSERT INTO order_items (
                        order_id, product_id, quantity, unit_price, subtotal, total
                    )
                    VALUES (%s, %s, %s, %s, %s, %s)
                """, (
                    order_id,
                    product_id,
                    quantity,
                    unit_price,
                    subtotal,
                    total
                ))

            cursor.execute("RELEASE SAVEPOINT order_savepoint")
            synced += 1

            # Progress report every 100 orders
            if i % 100 == 0:
                conn.commit()  # Commit in batches
                print(f"   📊 Progreso: {i}/{len(shopify_2025)} órdenes | ✅ {synced} nuevas | ⏭️  {skipped} duplicadas | ❌ {errors} errores")

        except Exception as e:
            cursor.execute("ROLLBACK TO SAVEPOINT order_savepoint")
            errors += 1
            print(f"   ⚠️  Error en orden {order.get('name', order.get('id'))}: {str(e)[:100]}")
            continue

    # Final commit
    conn.commit()
    cursor.close()

    print(f"\n   ✅ SHOPIFY COMPLETADO: {synced} órdenes nuevas, {skipped} duplicadas, {errors} errores")


def load_mercadolibre_complete(conn):
    """PASO 3: Cargar MercadoLibre 2025 COMPLETO - OPTIMIZADO"""
    print("\n" + "="*70)
    print("  📦 PASO 3: CARGANDO MERCADOLIBRE 2025")
    print("="*70)

    # Cargar cache
    with open(ML_CACHE, 'r') as f:
        ml_orders = json.load(f)

    print(f"   📂 {len(ml_orders)} órdenes en cache")

    # Filtrar 2025
    ml_2025 = [o for o in ml_orders if o.get('date_created', '').startswith('2025')]
    print(f"   📅 {len(ml_2025)} órdenes de 2025")

    cursor = conn.cursor()
    synced = 0
    skipped = 0
    errors = 0

    for i, order in enumerate(ml_2025, 1):
        try:
            # Start a savepoint for this order
            cursor.execute("SAVEPOINT order_savepoint")

            # Check if order already exists
            cursor.execute("""
                SELECT id FROM orders WHERE external_id = %s AND source = 'mercadolibre'
            """, (str(order['id']),))

            if cursor.fetchone():
                cursor.execute("RELEASE SAVEPOINT order_savepoint")
                skipped += 1
                continue

            # Extract buyer as customer
            buyer = order.get('buyer', {})
            if not buyer or not buyer.get('id'):
                cursor.execute("ROLLBACK TO SAVEPOINT order_savepoint")
                errors += 1
                continue

            customer_data = {
                'external_id': str(buyer['id']),
                'source': 'mercadolibre',
                'name': buyer.get('nickname', 'Cliente MercadoLibre'),
                'email': buyer.get('email'),  # ML doesn't usually provide this
                'phone': None,
                'type_customer': 'person'
            }

            customer_id = ensure_customer(cursor, customer_data)

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

            # Insert order
            cursor.execute("""
                INSERT INTO orders (
                    external_id, order_number, source, customer_id,
                    subtotal, total, status, order_date,
                    created_at, updated_at
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
            """, (
                str(order['id']),
                f"ML-{order['id']}",
                'mercadolibre',
                customer_id,
                float(order.get('total_amount', 0)),
                float(order.get('total_amount', 0)),
                status,
                order.get('date_created'),
                datetime.now(),
                datetime.now()
            ))

            order_id = cursor.fetchone()[0]

            # Insert order items
            order_items = order.get('order_items', [])
            for item in order_items:
                item_data = item.get('item', {})
                sku = str(item_data.get('id', 'ML-UNKNOWN'))
                product_name = item_data.get('title', 'Producto MercadoLibre')

                product_id = ensure_product(cursor, sku, product_name, 'mercadolibre')

                quantity = int(item.get('quantity', 1))
                unit_price = float(item.get('unit_price', 0))
                subtotal = unit_price * quantity
                total = subtotal

                cursor.execute("""
                    INSERT INTO order_items (
                        order_id, product_id, quantity, unit_price, subtotal, total
                    )
                    VALUES (%s, %s, %s, %s, %s, %s)
                """, (
                    order_id,
                    product_id,
                    quantity,
                    unit_price,
                    subtotal,
                    total
                ))

            cursor.execute("RELEASE SAVEPOINT order_savepoint")
            synced += 1

            if i % 50 == 0:
                conn.commit()
                print(f"   📊 Progreso: {i}/{len(ml_2025)} órdenes | ✅ {synced} nuevas | ⏭️  {skipped} duplicadas | ❌ {errors} errores")

        except Exception as e:
            cursor.execute("ROLLBACK TO SAVEPOINT order_savepoint")
            errors += 1
            print(f"   ⚠️  Error en orden {order.get('id')}: {str(e)[:100]}")
            continue

    # Final commit
    conn.commit()
    cursor.close()

    print(f"\n   ✅ MERCADOLIBRE COMPLETADO: {synced} órdenes nuevas, {skipped} duplicadas, {errors} errores")


def verify_integrity(conn):
    """PASO 4: Verificar integridad de datos cargados"""
    print("\n" + "="*70)
    print("  🔍 PASO 4: VERIFICANDO INTEGRIDAD")
    print("="*70)

    cursor = conn.cursor(cursor_factory=RealDictCursor)

    # Orders 2025 by source
    cursor.execute("""
        SELECT
            source,
            COUNT(*) as count,
            SUM(total) as total_amount
        FROM orders
        WHERE order_date >= '2025-01-01'
        GROUP BY source
        ORDER BY source
    """)

    print("\n   📊 ÓRDENES 2025 POR FUENTE:")
    for row in cursor.fetchall():
        print(f"      {row['source']:15s}: {row['count']:4d} órdenes | ${row['total_amount']:,.0f} CLP")

    # Expected values
    print("\n   🎯 VALORES ESPERADOS:")
    print("      Shopify        : 1,241 órdenes | $40,976,808 CLP")
    print("      MercadoLibre   :   261 órdenes | $2,964,340 CLP")

    cursor.close()


def main():
    print("="*70)
    print("  📦 CARGA COMPLETA DE DATOS 2025 A SUPABASE - OPTIMIZADA")
    print("  Destino: Tablas actuales (orders, products, customers)")
    print("  Fuente Única de Verdad")
    print("="*70)

    # Verificar caches
    if not os.path.exists(SHOPIFY_CACHE):
        print(f"❌ ERROR: No se encuentra {SHOPIFY_CACHE}")
        return

    if not os.path.exists(ML_CACHE):
        print(f"❌ ERROR: No se encuentra {ML_CACHE}")
        return

    print("  ✅ Caches encontrados")

    # Conectar a DB
    try:
        conn = get_db_connection()
        print("  ✅ Conectado a Supabase")

        # Ejecutar pasos
        clean_demo_data(conn)
        load_shopify_complete(conn)
        load_mercadolibre_complete(conn)
        verify_integrity(conn)

        conn.close()
        print("\n" + "="*70)
        print("  ✅ CARGA COMPLETA EXITOSA")
        print("="*70)

    except Exception as e:
        print(f"\n  ❌ ERROR durante la carga: {e}")
        if 'conn' in locals():
            conn.close()


if __name__ == "__main__":
    main()
