#!/usr/bin/env python3
"""
Script de diagnóstico: Inspeccionar pedido específico en Shopify
Muestra exactamente qué datos trae la API para comparar con lo guardado en DB
"""
import os
import sys
import asyncio
import json
from pathlib import Path
from dotenv import load_dotenv

# Load environment
env_path = Path(__file__).parent / '.env'
load_dotenv(env_path)

from app.connectors.shopify_connector import ShopifyConnector


async def inspect_order(order_number: str):
    """Buscar y mostrar datos del pedido en Shopify"""
    print("\n" + "="*70)
    print(f"🔍 INSPECCIÓN DE PEDIDO: {order_number}")
    print("="*70)

    try:
        connector = ShopifyConnector()

        # Test connection
        print("\n📡 Conectando a Shopify...")
        test_result = await connector.test_connection()
        if not test_result['success']:
            print(f"❌ Error de conexión: {test_result.get('error')}")
            return

        print(f"✅ Conectado a {test_result['shop_name']}")

        # Search for order by name/number
        print(f"\n🔎 Buscando pedido {order_number}...")

        # Query GraphQL para buscar el pedido específico
        query = """
        query ($query: String!) {
          orders(first: 1, query: $query) {
            edges {
              node {
                id
                name
                email
                createdAt
                fullyPaid
                displayFulfillmentStatus
                totalPriceSet {
                  shopMoney {
                    amount
                    currencyCode
                  }
                }
                customer {
                  id
                  firstName
                  lastName
                  email
                  phone
                }
                lineItems(first: 50) {
                  edges {
                    node {
                      id
                      title
                      quantity
                      variant {
                        id
                        sku
                        title
                        price
                      }
                      discountedUnitPriceSet {
                        shopMoney {
                          amount
                        }
                      }
                    }
                  }
                }
              }
            }
          }
        }
        """

        # Shopify usa "name:" para buscar por número de orden
        variables = {
            'query': f'name:{order_number}'
        }

        result = await connector._execute_query(query, variables)

        orders = result.get('orders', {}).get('edges', [])

        if not orders:
            print(f"❌ No se encontró el pedido {order_number} en Shopify")
            print("\n💡 Nota: El pedido puede haber sido eliminado o archivado en Shopify")
            return

        order_node = orders[0]['node']

        # Mostrar información del pedido
        print("\n" + "="*70)
        print("📦 INFORMACIÓN DEL PEDIDO EN SHOPIFY")
        print("="*70)
        print(f"\nID Shopify: {order_node['id']}")
        print(f"Número: {order_node['name']}")
        print(f"Fecha: {order_node['createdAt']}")
        print(f"Total: ${order_node['totalPriceSet']['shopMoney']['amount']} {order_node['totalPriceSet']['shopMoney']['currencyCode']}")

        if order_node.get('customer'):
            customer = order_node['customer']
            print(f"\nCliente:")
            print(f"  Nombre: {customer.get('firstName', '')} {customer.get('lastName', '')}")
            print(f"  Email: {customer.get('email', 'N/A')}")
            print(f"  Teléfono: {customer.get('phone', 'N/A')}")

        # ANALIZAR LINE ITEMS (ESTA ES LA PARTE CRÍTICA)
        print("\n" + "="*70)
        print("📋 LINE ITEMS (PRODUCTOS) - ANÁLISIS DETALLADO")
        print("="*70)

        line_items = order_node.get('lineItems', {}).get('edges', [])
        print(f"\nTotal items: {len(line_items)}")

        for i, edge in enumerate(line_items, 1):
            item = edge['node']
            variant = item.get('variant')

            print(f"\n--- Item #{i} ---")
            print(f"  Item ID: {item['id']}")
            print(f"  Title: {item.get('title', 'N/A')}")
            print(f"  Quantity: {item.get('quantity', 0)}")

            if variant:
                print(f"\n  Variant Info:")
                print(f"    Variant ID: {variant['id']}")
                print(f"    Variant Title: {variant.get('title', 'N/A')}")
                print(f"    SKU: {variant.get('sku', 'N/A')}")
                print(f"    Price: ${variant.get('price', '0')}")

                # DIAGNÓSTICO CRÍTICO
                if not variant.get('sku'):
                    print(f"    ⚠️  WARNING: SKU está vacío o None!")
                if not item.get('title'):
                    print(f"    ⚠️  WARNING: Title está vacío o None!")
            else:
                print(f"  ⚠️  WARNING: Variant es None!")

            # Mostrar precio
            price_set = item.get('discountedUnitPriceSet', {}).get('shopMoney', {})
            if price_set:
                print(f"  Unit Price: ${price_set.get('amount', '0')}")

        # MOSTRAR JSON RAW para análisis profundo
        print("\n" + "="*70)
        print("🔬 JSON RAW DEL PEDIDO (para análisis)")
        print("="*70)
        print(json.dumps(order_node, indent=2, ensure_ascii=False))

        # NORMALIZAR Y COMPARAR
        print("\n" + "="*70)
        print("🔄 DATOS NORMALIZADOS (como se guardarían en DB)")
        print("="*70)

        normalized = connector.normalize_order(order_node)
        print(f"\nOrder Number: {normalized['order_number']}")
        print(f"Total: ${normalized['total']}")
        print(f"Items count: {len(normalized['items'])}")

        print("\nItems normalizados:")
        for i, item in enumerate(normalized['items'], 1):
            print(f"\n  Item #{i}:")
            print(f"    product_sku: '{item.get('product_sku', '')}' {' ⚠️ VACÍO!' if not item.get('product_sku') else ''}")
            print(f"    product_name: '{item.get('product_name', '')}' {' ⚠️ VACÍO!' if not item.get('product_name') else ''}")
            print(f"    quantity: {item.get('quantity')}")
            print(f"    unit_price: ${item.get('unit_price')}")
            print(f"    total: ${item.get('total')}")

        print("\n" + "="*70)
        print("✅ INSPECCIÓN COMPLETA")
        print("="*70)

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python3 inspect_order.py <order_number>")
        print("Ejemplo: python3 inspect_order.py '#2928'")
        sys.exit(1)

    order_number = sys.argv[1]
    asyncio.run(inspect_order(order_number))
