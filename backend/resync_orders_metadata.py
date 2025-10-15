#!/usr/bin/env python3
"""
Re-Sincronización de Metadata de Pedidos
Actualiza payment_status y channel_id desde Shopify para pedidos históricos

Author: TM3
Date: 2025-10-13
"""
import os
import sys
import asyncio
from pathlib import Path
from dotenv import load_dotenv
import psycopg2
from psycopg2.extras import RealDictCursor

# Load environment
env_path = Path(__file__).parent / '.env'
load_dotenv(env_path)

from app.connectors.shopify_connector import ShopifyConnector


class OrderMetadataResyncer:
    """Re-sincroniza payment_status y channel_id desde Shopify"""

    def __init__(self, db_url: str):
        self.db_url = db_url
        self.connector = ShopifyConnector()

        # Mapeo de canales
        self.channel_map = {
            'shopify': 1,  # web_shopify
            'mercadolibre': 2  # marketplace_ml
        }

        # Mapeo de payment status
        self.payment_status_map = {
            True: 'paid',    # fullyPaid = true
            False: 'pending'  # fullyPaid = false
        }

    def get_db_connection(self):
        """Get database connection"""
        return psycopg2.connect(self.db_url)

    async def fetch_order_from_shopify(self, order_number: str):
        """
        Busca un pedido en Shopify por número

        Returns:
            dict con payment_status y channel_id o None si no se encuentra
        """
        query = """
        query ($query: String!) {
          orders(first: 1, query: $query) {
            edges {
              node {
                id
                name
                fullyPaid
                displayFulfillmentStatus
              }
            }
          }
        }
        """

        try:
            variables = {'query': f'name:{order_number}'}
            result = await self.connector._execute_query(query, variables)

            orders = result.get('orders', {}).get('edges', [])

            if not orders:
                return None

            order_node = orders[0]['node']

            # Mapear payment_status
            fully_paid = order_node.get('fullyPaid', False)
            payment_status = self.payment_status_map.get(fully_paid, 'pending')

            # Para Shopify, siempre es canal web_shopify (id=1)
            channel_id = self.channel_map['shopify']

            return {
                'payment_status': payment_status,
                'channel_id': channel_id,
                'shopify_id': order_node['id'],
                'fulfillment_status': order_node.get('displayFulfillmentStatus', 'UNFULFILLED').lower()
            }

        except Exception as e:
            print(f"  ⚠️  Error fetching from Shopify: {e}")
            return None

    def update_order_metadata(self, order_id: int, metadata: dict, dry_run: bool = False):
        """
        Actualiza payment_status y channel_id de un pedido

        Args:
            order_id: ID del pedido en la base de datos
            metadata: dict con payment_status, channel_id, etc.
            dry_run: Si es True, solo muestra qué haría sin actualizar
        """
        if dry_run:
            print(f"  [DRY RUN] Actualizaría pedido {order_id}:")
            print(f"    payment_status: {metadata['payment_status']}")
            print(f"    channel_id: {metadata['channel_id']}")
            print(f"    fulfillment_status: {metadata.get('fulfillment_status', 'N/A')}")
            return True

        try:
            conn = self.get_db_connection()
            cursor = conn.cursor()

            cursor.execute("""
                UPDATE orders
                SET
                    payment_status = %s,
                    channel_id = %s,
                    fulfillment_status = %s,
                    updated_at = NOW()
                WHERE id = %s
            """, (
                metadata['payment_status'],
                metadata['channel_id'],
                metadata.get('fulfillment_status'),
                order_id
            ))

            conn.commit()
            cursor.close()
            conn.close()

            return True

        except Exception as e:
            print(f"  ❌ Error updating order {order_id}: {e}")
            return False

    async def resync_orders(self, limit: int = None, dry_run: bool = False):
        """
        Re-sincroniza pedidos de Shopify con metadata faltante

        Args:
            limit: Número máximo de pedidos a procesar (None = todos)
            dry_run: Si es True, solo simula sin actualizar la DB
        """
        print("\n" + "="*70)
        print("🔄 RE-SINCRONIZACIÓN DE METADATA DE PEDIDOS")
        print("="*70)

        if dry_run:
            print("⚠️  MODO DRY RUN - No se actualizará la base de datos")

        # Obtener pedidos de Shopify con metadata faltante
        conn = self.get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        query = """
            SELECT id, order_number, source, total, order_date
            FROM orders
            WHERE source = 'shopify'
              AND (payment_status IS NULL OR channel_id IS NULL)
            ORDER BY order_date DESC
        """

        if limit:
            query += f" LIMIT {limit}"

        cursor.execute(query)
        orders = cursor.fetchall()

        cursor.close()
        conn.close()

        total_orders = len(orders)
        print(f"\n📊 Pedidos de Shopify a procesar: {total_orders}")

        if total_orders == 0:
            print("✅ No hay pedidos que requieran actualización")
            return

        print(f"\n{'='*70}")
        print("Procesando pedidos...")
        print(f"{'='*70}\n")

        success_count = 0
        failed_count = 0
        not_found_count = 0

        for i, order in enumerate(orders, 1):
            order_number = order['order_number']
            order_id = order['id']

            print(f"[{i}/{total_orders}] Procesando {order_number}...", end=" ")

            # Buscar en Shopify
            metadata = await self.fetch_order_from_shopify(order_number)

            if not metadata:
                print("❌ No encontrado en Shopify")
                not_found_count += 1
                continue

            # Actualizar en DB
            success = self.update_order_metadata(order_id, metadata, dry_run)

            if success:
                print(f"✅ payment_status={metadata['payment_status']}, channel={metadata['channel_id']}")
                success_count += 1
            else:
                print("❌ Error al actualizar")
                failed_count += 1

            # Progress cada 50 pedidos
            if i % 50 == 0:
                print(f"\n📊 Progreso: {success_count} exitosos, {failed_count} fallidos, {not_found_count} no encontrados\n")

        # Resumen final
        print(f"\n{'='*70}")
        print("📊 RESUMEN FINAL")
        print(f"{'='*70}")
        print(f"Total procesados: {total_orders}")
        print(f"✅ Exitosos: {success_count}")
        print(f"❌ Fallidos: {failed_count}")
        print(f"⚠️  No encontrados: {not_found_count}")

        if dry_run:
            print("\n⚠️  DRY RUN completado - No se modificó la base de datos")
        else:
            print("\n✅ Re-sincronización completada")


async def main():
    """Main function"""
    import argparse

    parser = argparse.ArgumentParser(description='Re-sincronizar metadata de pedidos desde Shopify')
    parser.add_argument('--limit', type=int, help='Número máximo de pedidos a procesar')
    parser.add_argument('--dry-run', action='store_true', help='Modo simulación (no actualiza DB)')

    args = parser.parse_args()

    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        print("❌ ERROR: DATABASE_URL no configurado")
        sys.exit(1)

    resyncer = OrderMetadataResyncer(database_url)

    try:
        await resyncer.resync_orders(limit=args.limit, dry_run=args.dry_run)
    except KeyboardInterrupt:
        print("\n\n⚠️  Proceso interrumpido por el usuario")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
