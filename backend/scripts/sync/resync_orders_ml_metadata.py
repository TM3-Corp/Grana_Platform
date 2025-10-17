#!/usr/bin/env python3
"""
Re-Sincronización de Metadata de Pedidos de MercadoLibre
Actualiza payment_status y channel_id desde MercadoLibre para pedidos históricos

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

from app.connectors.mercadolibre_connector import MercadoLibreConnector


class MLOrderMetadataResyncer:
    """Re-sincroniza payment_status y channel_id desde MercadoLibre"""

    def __init__(self, db_url: str):
        self.db_url = db_url
        self.connector = MercadoLibreConnector()

        # Mapeo de canales
        self.channel_map = {
            'mercadolibre': 2  # marketplace_ml
        }

        # Mapeo de payment status desde ML API
        self.payment_status_map = {
            'approved': 'paid',
            'accredited': 'paid',
            'pending': 'pending',
            'in_process': 'pending',
            'rejected': 'failed',
            'cancelled': 'cancelled',
            'refunded': 'refunded'
        }

        # Mapeo de shipping status
        self.shipping_status_map = {
            'shipped': 'fulfilled',
            'delivered': 'fulfilled',
            'ready_to_ship': 'pending',
            'pending': 'pending',
            'cancelled': 'cancelled'
        }

    def get_db_connection(self):
        """Get database connection"""
        return psycopg2.connect(self.db_url)

    async def fetch_order_from_ml(self, external_id: str):
        """
        Busca un pedido en MercadoLibre por external_id

        Args:
            external_id: ID del pedido en MercadoLibre

        Returns:
            dict con payment_status y channel_id o None si no se encuentra
        """
        try:
            # Get order details from ML API
            order_data = await self.connector.get_order_details(external_id)

            if not order_data or 'id' not in order_data:
                return None

            # Extract payment status from payments array
            payment_status = 'pending'
            if order_data.get('payments') and len(order_data['payments']) > 0:
                payment = order_data['payments'][0]
                ml_payment_status = payment.get('status', 'pending')
                payment_status = self.payment_status_map.get(ml_payment_status, 'pending')

            # Extract fulfillment status from shipping
            fulfillment_status = 'unfulfilled'
            if order_data.get('shipping'):
                ml_shipping_status = order_data['shipping'].get('status', 'pending')
                fulfillment_status = self.shipping_status_map.get(ml_shipping_status, 'unfulfilled')

            # MercadoLibre always uses channel marketplace_ml (id=2)
            channel_id = self.channel_map['mercadolibre']

            return {
                'payment_status': payment_status,
                'channel_id': channel_id,
                'fulfillment_status': fulfillment_status,
                'ml_id': order_data['id']
            }

        except Exception as e:
            print(f"  ⚠️  Error fetching from MercadoLibre: {e}")
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
        Re-sincroniza pedidos de MercadoLibre con metadata faltante

        Args:
            limit: Número máximo de pedidos a procesar (None = todos)
            dry_run: Si es True, solo simula sin actualizar la DB
        """
        print("\n" + "="*70)
        print("🔄 RE-SINCRONIZACIÓN DE METADATA DE PEDIDOS - MERCADOLIBRE")
        print("="*70)

        if dry_run:
            print("⚠️  MODO DRY RUN - No se actualizará la base de datos")

        # Obtener pedidos de MercadoLibre con metadata faltante
        conn = self.get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        query = """
            SELECT id, order_number, external_id, source, total, order_date
            FROM orders
            WHERE source = 'mercadolibre'
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
        print(f"\n📊 Pedidos de MercadoLibre a procesar: {total_orders}")

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
            external_id = order['external_id']

            if not external_id:
                print(f"[{i}/{total_orders}] ❌ {order_number} - Sin external_id")
                failed_count += 1
                continue

            print(f"[{i}/{total_orders}] Procesando {order_number} (ML ID: {external_id})...", end=" ")

            # Buscar en MercadoLibre
            metadata = await self.fetch_order_from_ml(external_id)

            if not metadata:
                print("❌ No encontrado en MercadoLibre")
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

    parser = argparse.ArgumentParser(description='Re-sincronizar metadata de pedidos desde MercadoLibre')
    parser.add_argument('--limit', type=int, help='Número máximo de pedidos a procesar')
    parser.add_argument('--dry-run', action='store_true', help='Modo simulación (no actualiza DB)')

    args = parser.parse_args()

    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        print("❌ ERROR: DATABASE_URL no configurado")
        sys.exit(1)

    resyncer = MLOrderMetadataResyncer(database_url)

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
