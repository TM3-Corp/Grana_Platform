#!/usr/bin/env python3
"""
Carga COMPLETA de datos 2025 a tablas actuales de Supabase
Rellena: orders, products, customers, order_items

Author: TM3
Date: 2025-10-12
"""
import json
import os
import sys
from datetime import datetime
from typing import Dict, List
import psycopg2
from psycopg2.extras import RealDictCursor

# Add app to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.services.order_processing_service import OrderProcessingService

# Paths a caches validados
CACHE_DIR = "/home/javier/Proyectos/Grana/grana-integration/validacion_2025_corregido/cache"
SHOPIFY_CACHE = f"{CACHE_DIR}/shopify_2025_corregido.json"
ML_CACHE = f"{CACHE_DIR}/mercadolibre_2025_corregido.json"


def get_db_connection():
    """Get database connection"""
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise ValueError("DATABASE_URL not set in environment")
    return psycopg2.connect(database_url)


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


def transform_shopify_order(shopify_order: Dict) -> Dict:
    """
    Transforma orden de Shopify a formato normalizado
    Compatible con OrderProcessingService
    """
    # Extraer customer
    customer = shopify_order.get('customer', {})
    customer_data = None

    if customer and customer.get('id'):
        # Extraer dirección
        address = None
        if customer.get('default_address'):
            addr = customer['default_address']
            address_parts = [
                addr.get('address1'),
                addr.get('address2'),
                addr.get('city'),
                addr.get('province')
            ]
            address = ', '.join([p for p in address_parts if p])

        customer_data = {
            'external_id': str(customer.get('id', '')),
            'source': 'shopify',
            'name': f"{customer.get('first_name', '')} {customer.get('last_name', '')}".strip() or 'Cliente Shopify',
            'email': customer.get('email'),
            'phone': customer.get('phone'),
            'address': address,
            'city': customer.get('default_address', {}).get('city'),
            'type_customer': 'person'
        }

    # Extraer items
    items = []
    for line_item in shopify_order.get('line_items', []):
        sku = line_item.get('sku') or f"SHOPIFY-{line_item.get('product_id', 'UNKNOWN')}"

        items.append({
            'product_sku': sku,
            'product_name': line_item.get('title', 'Producto sin nombre'),
            'quantity': int(line_item.get('quantity', 1)),
            'unit_price': float(line_item.get('price', 0)),
            'total': float(line_item.get('price', 0)) * int(line_item.get('quantity', 1))
        })

    # Mapear statuses de Shopify a nuestros statuses
    status_map = {
        'pending': 'pending',
        'authorized': 'pending',
        'partially_paid': 'pending',
        'paid': 'completed',
        'partially_refunded': 'completed',
        'refunded': 'refunded',
        'voided': 'cancelled'
    }

    # Calcular shipping cost
    shipping_lines = shopify_order.get('shipping_lines', [])
    shipping_cost = sum(float(s.get('price', 0)) for s in shipping_lines)

    return {
        'external_id': str(shopify_order['id']),
        'order_number': shopify_order.get('name', f"#{shopify_order['id']}"),
        'source': 'shopify',
        'customer': customer_data,
        'items': items,
        'subtotal': float(shopify_order.get('subtotal_price', 0)),
        'tax_amount': float(shopify_order.get('total_tax', 0)),
        'shipping_cost': shipping_cost,
        'discount_amount': float(shopify_order.get('total_discounts', 0)),
        'total': float(shopify_order.get('total_price', 0)),
        'status': status_map.get(shopify_order.get('financial_status'), 'pending'),
        'payment_status': shopify_order.get('financial_status', 'pending'),
        'fulfillment_status': shopify_order.get('fulfillment_status'),
        'order_date': shopify_order.get('created_at')
    }


def load_shopify_complete(processor: OrderProcessingService):
    """PASO 2: Cargar Shopify 2025 COMPLETO"""
    print("\n" + "="*70)
    print("  📦 PASO 2: CARGANDO SHOPIFY 2025 COMPLETO")
    print("="*70)

    # Cargar cache
    print(f"   📂 Cargando cache: {SHOPIFY_CACHE}")

    if not os.path.exists(SHOPIFY_CACHE):
        print(f"   ❌ Error: Cache no encontrado")
        return

    with open(SHOPIFY_CACHE, 'r', encoding='utf-8') as f:
        orders = json.load(f)

    print(f"   📊 Órdenes en cache: {len(orders)}")

    # Filtrar solo 2025
    orders_2025 = [
        o for o in orders
        if o.get('created_at', '').startswith('2025')
    ]

    print(f"   📅 Órdenes 2025: {len(orders_2025)}")

    if len(orders_2025) != len(orders):
        print(f"   ⚠️  Filtradas: {len(orders) - len(orders_2025)} órdenes fuera de 2025")

    # Procesar cada orden
    synced = 0
    skipped = 0
    errors = []

    print(f"\n   🔄 Procesando órdenes...")

    for i, order in enumerate(orders_2025, 1):
        if i % 100 == 0:
            print(f"      Procesadas: {i}/{len(orders_2025)} ({synced} nuevas, {skipped} existentes)")

        try:
            # Transformar a formato normalizado
            normalized = transform_shopify_order(order)

            # Procesar usando servicio existente
            result = processor.process_order(normalized, apply_conversions=False)

            if result['success']:
                if result['status'] == 'created':
                    synced += 1
                elif result['status'] == 'already_exists':
                    skipped += 1
            else:
                errors.append({
                    'order': order.get('name'),
                    'error': result.get('message', 'Unknown error')
                })

        except Exception as e:
            errors.append({
                'order': order.get('name', 'unknown'),
                'error': str(e)
            })

    print(f"\n   ✅ Órdenes nuevas insertadas: {synced}")
    print(f"   ⏭️  Órdenes ya existentes: {skipped}")

    if errors:
        print(f"   ❌ Errores: {len(errors)}")
        print(f"\n   Primeros 5 errores:")
        for err in errors[:5]:
            print(f"      • {err['order']}: {err['error']}")


def transform_ml_order(ml_order: Dict) -> Dict:
    """
    Transforma orden de MercadoLibre a formato normalizado
    Compatible con OrderProcessingService
    """
    # Extraer buyer (customer)
    buyer = ml_order.get('buyer', {})
    customer_data = None

    if buyer and buyer.get('id'):
        customer_data = {
            'external_id': str(buyer.get('id', '')),
            'source': 'mercadolibre',
            'name': buyer.get('nickname', 'Cliente MercadoLibre'),
            'email': None,  # ML no provee email en API
            'phone': None,
            'type_customer': 'person'
        }

    # Extraer items
    items = []
    for item in ml_order.get('order_items', []):
        ml_item = item.get('item', {})
        sku = ml_item.get('seller_sku') or f"ML-{ml_item.get('id', 'UNKNOWN')}"

        items.append({
            'product_sku': sku,
            'product_name': ml_item.get('title', 'Producto sin nombre'),
            'quantity': int(item.get('quantity', 1)),
            'unit_price': float(item.get('unit_price', 0)),
            'total': float(item.get('unit_price', 0)) * int(item.get('quantity', 1))
        })

    # Mapear statuses de ML
    status_map = {
        'confirmed': 'completed',
        'payment_required': 'pending',
        'payment_in_process': 'pending',
        'paid': 'completed',
        'cancelled': 'cancelled'
    }

    payment_status_map = {
        'approved': 'paid',
        'accredited': 'paid',
        'pending': 'pending',
        'rejected': 'failed',
        'cancelled': 'cancelled',
        'refunded': 'refunded'
    }

    # Obtener payment status
    payment_status = 'pending'
    if ml_order.get('payments') and len(ml_order['payments']) > 0:
        ml_payment_status = ml_order['payments'][0].get('status', 'pending')
        payment_status = payment_status_map.get(ml_payment_status, 'pending')

    # Calcular shipping
    shipping = ml_order.get('shipping', {})
    shipping_cost = float(shipping.get('cost', 0))

    total_amount = float(ml_order.get('total_amount', 0))

    return {
        'external_id': str(ml_order['id']),
        'order_number': f"ML-{ml_order['id']}",
        'source': 'mercadolibre',
        'customer': customer_data,
        'items': items,
        'subtotal': total_amount - shipping_cost,
        'tax_amount': 0,  # ML incluye impuestos en el precio
        'shipping_cost': shipping_cost,
        'discount_amount': 0,
        'total': total_amount,
        'status': status_map.get(ml_order.get('status'), 'pending'),
        'payment_status': payment_status,
        'fulfillment_status': ml_order.get('shipping', {}).get('status'),
        'order_date': ml_order.get('date_created')
    }


def load_mercadolibre_complete(processor: OrderProcessingService):
    """PASO 3: Cargar MercadoLibre 2025 COMPLETO"""
    print("\n" + "="*70)
    print("  🏪 PASO 3: CARGANDO MERCADOLIBRE 2025 COMPLETO")
    print("="*70)

    # Cargar cache
    print(f"   📂 Cargando cache: {ML_CACHE}")

    if not os.path.exists(ML_CACHE):
        print(f"   ❌ Error: Cache no encontrado")
        return

    with open(ML_CACHE, 'r', encoding='utf-8') as f:
        orders = json.load(f)

    print(f"   📊 Órdenes en cache: {len(orders)}")

    # Filtrar solo 2025
    orders_2025 = [
        o for o in orders
        if o.get('date_created', '').startswith('2025')
    ]

    print(f"   📅 Órdenes 2025: {len(orders_2025)}")
    print(f"   ℹ️  Nota: Algunas órdenes ya pueden estar en DB")

    # Procesar cada orden
    synced = 0
    skipped = 0
    errors = []

    print(f"\n   🔄 Procesando órdenes...")

    for i, order in enumerate(orders_2025, 1):
        if i % 50 == 0:
            print(f"      Procesadas: {i}/{len(orders_2025)} ({synced} nuevas, {skipped} existentes)")

        try:
            # Transformar a formato normalizado
            normalized = transform_ml_order(order)

            # Procesar usando servicio existente
            result = processor.process_order(normalized, apply_conversions=False)

            if result['success']:
                if result['status'] == 'created':
                    synced += 1
                elif result['status'] == 'already_exists':
                    skipped += 1
            else:
                errors.append({
                    'order': order.get('id'),
                    'error': result.get('message', 'Unknown error')
                })

        except Exception as e:
            errors.append({
                'order': order.get('id', 'unknown'),
                'error': str(e)
            })

    print(f"\n   ✅ Órdenes nuevas insertadas: {synced}")
    print(f"   ⏭️  Órdenes ya existentes: {skipped}")

    if errors:
        print(f"   ❌ Errores: {len(errors)}")
        print(f"\n   Primeros 5 errores:")
        for err in errors[:5]:
            print(f"      • {err['order']}: {err['error']}")


def sync_products_from_orders(conn):
    """PASO 4: Sincronizar productos mencionados en órdenes"""
    print("\n" + "="*70)
    print("  🏷️  PASO 4: SINCRONIZANDO PRODUCTOS")
    print("="*70)

    cursor = conn.cursor(cursor_factory=RealDictCursor)

    # Encontrar SKUs en order_items que no existen en products
    cursor.execute("""
        SELECT DISTINCT
            oi.product_sku,
            oi.product_name,
            o.source
        FROM order_items oi
        JOIN orders o ON o.id = oi.order_id
        WHERE NOT EXISTS (
            SELECT 1 FROM products p
            WHERE p.sku = oi.product_sku
        )
        AND o.order_date >= '2025-01-01'
    """)

    missing_products = cursor.fetchall()

    if not missing_products:
        print("   ✅ Todos los productos ya existen en la tabla products")
        return

    print(f"   📊 Productos faltantes: {len(missing_products)}")
    print(f"   🔄 Creando productos básicos...")

    created = 0
    for product in missing_products:
        try:
            cursor.execute("""
                INSERT INTO products (sku, name, source, is_active, created_at)
                VALUES (%s, %s, %s, true, NOW())
                ON CONFLICT (sku) DO NOTHING
            """, (
                product['product_sku'],
                product['product_name'],
                product['source']
            ))

            if cursor.rowcount > 0:
                created += 1

        except Exception as e:
            print(f"      ⚠️  Error creando {product['product_sku']}: {e}")

    conn.commit()

    print(f"   ✅ Productos creados: {created}")


def verify_integrity(conn):
    """PASO 5: Verificar integridad de datos cargados"""
    print("\n" + "="*70)
    print("  🔍 PASO 5: VERIFICACIÓN DE INTEGRIDAD")
    print("="*70)

    cursor = conn.cursor(cursor_factory=RealDictCursor)

    # 1. Conteo por source y totales
    print("\n   📊 ÓRDENES 2025 POR FUENTE:")
    cursor.execute("""
        SELECT
            source,
            COUNT(*) as count,
            SUM(total) as revenue,
            MIN(order_date) as first_order,
            MAX(order_date) as last_order
        FROM orders
        WHERE order_date >= '2025-01-01'
        GROUP BY source
        ORDER BY revenue DESC
    """)

    total_orders = 0
    total_revenue = 0

    for row in cursor.fetchall():
        total_orders += row['count']
        total_revenue += float(row['revenue'] or 0)
        print(f"      {row['source']:15} {row['count']:4} órdenes = ${row['revenue']:>12,.0f} CLP")
        print(f"                        Rango: {row['first_order']} → {row['last_order']}")

    print(f"\n      {'TOTAL':15} {total_orders:4} órdenes = ${total_revenue:>12,.0f} CLP")

    # 2. Verificar productos
    print("\n   🏷️  PRODUCTOS POR FUENTE:")
    cursor.execute("""
        SELECT
            source,
            COUNT(*) as count,
            COUNT(*) FILTER (WHERE is_active = true) as active
        FROM products
        WHERE source IS NOT NULL
        GROUP BY source
        ORDER BY count DESC
    """)

    for row in cursor.fetchall():
        print(f"      {row['source']:15} {row['count']:4} productos ({row['active']} activos)")

    # 3. Verificar customers
    print("\n   👥 CLIENTES POR FUENTE:")
    cursor.execute("""
        SELECT
            source,
            COUNT(*) as count
        FROM customers
        WHERE source IS NOT NULL
        GROUP BY source
        ORDER BY count DESC
    """)

    for row in cursor.fetchall():
        print(f"      {row['source']:15} {row['count']:4} clientes")

    # 4. Órfanos (orders sin customer - normal en algunos casos)
    cursor.execute("""
        SELECT COUNT(*) as count
        FROM orders
        WHERE customer_id IS NULL
        AND order_date >= '2025-01-01'
    """)
    orphans = cursor.fetchone()['count']

    if orphans > 0:
        print(f"\n   ℹ️  {orphans} órdenes sin customer asignado (normal para algunos casos)")

    # 5. Verificar totales contra datos validados
    print("\n   💰 VALIDACIÓN CONTRA DATOS ESPERADOS:")

    cursor.execute("""
        SELECT SUM(total) as total
        FROM orders
        WHERE source='shopify' AND order_date >= '2025-01-01'
    """)
    shopify_total = float(cursor.fetchone()['total'] or 0)

    cursor.execute("""
        SELECT SUM(total) as total
        FROM orders
        WHERE source='mercadolibre' AND order_date >= '2025-01-01'
    """)
    ml_total = float(cursor.fetchone()['total'] or 0)

    # Totales esperados (de validación previa)
    expected_shopify = 40976808
    expected_ml = 2964340

    shopify_diff = abs(shopify_total - expected_shopify)
    shopify_diff_pct = (shopify_diff / expected_shopify) * 100

    ml_diff = abs(ml_total - expected_ml)
    ml_diff_pct = (ml_diff / expected_ml) * 100

    print(f"\n      Shopify:")
    print(f"         DB:       ${shopify_total:>12,.0f} CLP")
    print(f"         Esperado: ${expected_shopify:>12,.0f} CLP")
    print(f"         Diff:     ${shopify_diff:>12,.0f} ({shopify_diff_pct:.2f}%)")

    if shopify_diff_pct < 1:
        print(f"         ✅ Coincide con datos validados")
    else:
        print(f"         ⚠️  Difiere de lo esperado")

    print(f"\n      MercadoLibre:")
    print(f"         DB:       ${ml_total:>12,.0f} CLP")
    print(f"         Esperado: ${expected_ml:>12,.0f} CLP")
    print(f"         Diff:     ${ml_diff:>12,.0f} ({ml_diff_pct:.2f}%)")

    if ml_diff_pct < 1:
        print(f"         ✅ Coincide con datos validados")
    else:
        print(f"         ⚠️  Difiere de lo esperado")

    # 6. Verificar que no hay duplicados
    print("\n   🔎 VERIFICACIÓN DE DUPLICADOS:")

    cursor.execute("""
        SELECT
            COUNT(*) as total,
            COUNT(DISTINCT (external_id, source)) as unique_orders
        FROM orders
        WHERE order_date >= '2025-01-01'
    """)

    dup_check = cursor.fetchone()
    if dup_check['total'] == dup_check['unique_orders']:
        print(f"      ✅ Sin duplicados detectados ({dup_check['total']} órdenes únicas)")
    else:
        duplicates = dup_check['total'] - dup_check['unique_orders']
        print(f"      ⚠️  {duplicates} órdenes duplicadas encontradas!")


def main():
    """Función principal"""
    print("\n" + "="*70)
    print("  📦 CARGA COMPLETA DE DATOS 2025 A SUPABASE")
    print("  Destino: Tablas actuales (orders, products, customers)")
    print("  Fuente Única de Verdad")
    print("="*70)
    print(f"\n  📂 Cache directory: {CACHE_DIR}")
    print(f"  📅 Período: 2025-01-01 a 2025-12-31")

    # Verificar que existen los caches
    if not os.path.exists(SHOPIFY_CACHE):
        print(f"\n  ❌ ERROR: Cache de Shopify no encontrado: {SHOPIFY_CACHE}")
        return False

    if not os.path.exists(ML_CACHE):
        print(f"\n  ❌ ERROR: Cache de MercadoLibre no encontrado: {ML_CACHE}")
        return False

    print(f"\n  ✅ Caches encontrados")

    # Conectar a base de datos
    try:
        conn = get_db_connection()
        print(f"  ✅ Conectado a Supabase")
    except Exception as e:
        print(f"\n  ❌ ERROR conectando a base de datos: {e}")
        return False

    # Crear processor de órdenes
    try:
        processor = OrderProcessingService(os.getenv("DATABASE_URL"))
        print(f"  ✅ OrderProcessingService inicializado")
    except Exception as e:
        print(f"\n  ❌ ERROR inicializando processor: {e}")
        conn.close()
        return False

    try:
        # PASO 1: Limpiar demo
        clean_demo_data(conn)

        # PASO 2: Cargar Shopify 2025
        load_shopify_complete(processor)

        # PASO 3: Cargar MercadoLibre 2025
        load_mercadolibre_complete(processor)

        # PASO 4: Sincronizar productos
        sync_products_from_orders(conn)

        # PASO 5: Verificar integridad
        verify_integrity(conn)

        print("\n" + "="*70)
        print("  ✅ CARGA COMPLETADA EXITOSAMENTE")
        print("="*70)
        print("\n  🎯 Dashboard automáticamente mostrará los nuevos datos")
        print("  📊 Tablas actualizadas:")
        print("     • orders (con data 2025 completa)")
        print("     • products (sincronizados)")
        print("     • customers (sincronizados)")
        print("     • order_items (todos los items)")

        return True

    except Exception as e:
        print(f"\n  ❌ ERROR durante la carga: {e}")
        import traceback
        traceback.print_exc()
        conn.rollback()
        return False

    finally:
        conn.close()
        print(f"\n  🔌 Conexión cerrada")


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
