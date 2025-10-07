"""
MercadoLibre Sync Service
Syncs products and orders from MercadoLibre to database

Author: TM3
Date: 2025-10-04
"""
import os
from typing import Dict, List, Optional
from datetime import datetime
import logging
import psycopg2
from psycopg2.extras import RealDictCursor

from app.connectors.mercadolibre_connector import MercadoLibreConnector
from app.services.order_processing_service import OrderProcessingService

logger = logging.getLogger(__name__)


class MercadoLibreSyncService:
    """
    Service to sync MercadoLibre data to our database

    Handles:
    - Product sync from ML listings
    - Order sync from ML sales
    - Customer data from ML buyers
    - Data transformation to our schema
    """

    def __init__(self, db_connection_string: str):
        self.db_connection_string = db_connection_string
        self.connector = MercadoLibreConnector()
        self.order_processor = OrderProcessingService(db_connection_string)

    def get_db_connection(self):
        """Get database connection"""
        return psycopg2.connect(self.db_connection_string)

    async def sync_products(self) -> Dict:
        """
        Sync active product listings from MercadoLibre

        Returns:
            Dict with sync results
        """
        logger.info("Starting MercadoLibre product sync...")

        try:
            # Get active listings from ML
            listings = await self.connector.get_active_listings()

            if not listings:
                logger.warning("No active listings found in MercadoLibre")
                return {
                    'success': True,
                    'products_synced': 0,
                    'products_failed': 0,
                    'message': 'No active listings found'
                }

            conn = self.get_db_connection()
            cursor = conn.cursor(cursor_factory=RealDictCursor)

            synced = 0
            failed = 0

            for listing in listings:
                try:
                    # Check if product already exists
                    cursor.execute("""
                        SELECT id FROM products
                        WHERE external_id = %s AND source = 'mercadolibre'
                    """, (listing['id'],))

                    existing = cursor.fetchone()

                    if existing:
                        # Update existing product
                        cursor.execute("""
                            UPDATE products SET
                                name = %s,
                                sale_price = %s,
                                current_stock = %s,
                                is_active = %s,
                                updated_at = NOW()
                            WHERE external_id = %s AND source = 'mercadolibre'
                        """, (
                            listing['title'],
                            listing.get('price', 0),
                            listing.get('available_quantity', 0),
                            listing.get('status') == 'active',
                            listing['id']
                        ))
                    else:
                        # Create new product
                        # Generate SKU from ML item ID if no custom SKU
                        sku = listing.get('sku') or f"ML-{listing['id']}"

                        cursor.execute("""
                            INSERT INTO products (
                                external_id, source, sku, name,
                                sale_price, current_stock,
                                is_active, created_at, updated_at
                            ) VALUES (
                                %s, 'mercadolibre', %s, %s, %s, %s, %s, NOW(), NOW()
                            )
                            ON CONFLICT (sku) DO UPDATE SET
                                name = EXCLUDED.name,
                                sale_price = EXCLUDED.sale_price,
                                current_stock = EXCLUDED.current_stock,
                                updated_at = NOW()
                        """, (
                            listing['id'],
                            sku,
                            listing['title'],
                            listing.get('price', 0),
                            listing.get('available_quantity', 0),
                            listing.get('status') == 'active'
                        ))

                    synced += 1

                except Exception as e:
                    logger.error(f"Failed to sync product {listing.get('id')}: {e}")
                    failed += 1
                    continue

            conn.commit()
            cursor.close()
            conn.close()

            logger.info(f"Product sync complete: {synced} synced, {failed} failed")

            return {
                'success': True,
                'products_synced': synced,
                'products_failed': failed,
                'message': f'Synced {synced} products from MercadoLibre'
            }

        except Exception as e:
            logger.error(f"Product sync failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'products_synced': 0,
                'products_failed': 0
            }

    async def sync_orders(self, days: int = 30) -> Dict:
        """
        Sync recent orders from MercadoLibre

        Args:
            days: Number of days to look back (default 30)

        Returns:
            Dict with sync results
        """
        logger.info(f"Starting MercadoLibre order sync (last {days} days)...")

        try:
            # Get recent orders from ML
            ml_orders = await self.connector.get_recent_orders(days)

            if not ml_orders:
                logger.warning("No orders found in MercadoLibre")
                return {
                    'success': True,
                    'orders_synced': 0,
                    'orders_failed': 0,
                    'message': 'No orders found'
                }

            synced = 0
            failed = 0
            errors = []

            for ml_order in ml_orders:
                try:
                    # Transform ML order to our normalized format
                    normalized_order = self._transform_ml_order(ml_order)

                    # Process order using existing service
                    result = self.order_processor.process_order(normalized_order, apply_conversions=False)

                    if result['success']:
                        if result['status'] == 'created':
                            synced += 1
                        # 'already_exists' doesn't count as synced or failed
                    else:
                        failed += 1
                        errors.append({
                            'order': ml_order['id'],
                            'error': result.get('message', 'Unknown error')
                        })

                except Exception as e:
                    logger.error(f"Failed to process ML order {ml_order.get('id')}: {e}")
                    failed += 1
                    errors.append({
                        'order': ml_order.get('id'),
                        'error': str(e)
                    })
                    continue

            logger.info(f"Order sync complete: {synced} synced, {failed} failed")

            return {
                'success': True,
                'orders_synced': synced,
                'orders_failed': failed,
                'total_orders': len(ml_orders),
                'message': f'Synced {synced} new orders from MercadoLibre',
                'errors': errors if errors else None
            }

        except Exception as e:
            logger.error(f"Order sync failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'orders_synced': 0,
                'orders_failed': 0
            }

    def _transform_ml_order(self, ml_order: Dict) -> Dict:
        """
        Transform MercadoLibre order to normalized format

        Args:
            ml_order: Raw ML order data

        Returns:
            Normalized order data for OrderProcessingService
        """
        # Extract customer info
        customer_data = None
        if ml_order.get('buyer'):
            buyer = ml_order['buyer']
            customer_data = {
                'external_id': str(buyer.get('id', '')),
                'source': 'mercadolibre',
                'name': buyer.get('nickname', 'MercadoLibre Customer'),
                'email': None,  # ML doesn't provide email in API
                'phone': None,
                'type_customer': 'person'
            }

            # Try to extract city from shipping if available
            if ml_order.get('shipping') and ml_order['shipping'].get('receiver_address'):
                address = ml_order['shipping']['receiver_address']
                customer_data['city'] = address.get('city', {}).get('name') if isinstance(address.get('city'), dict) else address.get('city')
                customer_data['address'] = f"{address.get('street_name', '')} {address.get('street_number', '')}"

        # Extract order items
        items = []
        for item in ml_order.get('order_items', []):
            ml_item = item.get('item', {})

            # Use seller_sku if available, otherwise use ML item ID
            sku = ml_item.get('seller_sku') or f"ML-{ml_item.get('id')}"

            items.append({
                'product_sku': sku,
                'product_name': ml_item.get('title', 'MercadoLibre Product'),
                'quantity': item.get('quantity', 1),
                'unit_price': float(item.get('unit_price', 0)),
                'total': float(item.get('unit_price', 0) * item.get('quantity', 1)),
                'subtotal': float(item.get('unit_price', 0) * item.get('quantity', 1)),
                'tax_amount': 0  # ML includes tax in price
            })

        # Extract payment status
        payment_status = 'pending'
        if ml_order.get('payments') and len(ml_order['payments']) > 0:
            payment = ml_order['payments'][0]
            ml_status = payment.get('status', 'pending')
            # Map ML payment statuses to our statuses
            status_map = {
                'approved': 'paid',
                'accredited': 'paid',
                'pending': 'pending',
                'in_process': 'pending',
                'rejected': 'failed',
                'cancelled': 'cancelled',
                'refunded': 'refunded'
            }
            payment_status = status_map.get(ml_status, 'pending')

        # Extract shipping status
        shipping_status = 'unfulfilled'
        if ml_order.get('shipping'):
            ml_shipping_status = ml_order['shipping'].get('status', 'pending')
            shipping_map = {
                'shipped': 'fulfilled',
                'delivered': 'fulfilled',
                'ready_to_ship': 'pending',
                'pending': 'pending',
                'cancelled': 'cancelled'
            }
            shipping_status = shipping_map.get(ml_shipping_status, 'unfulfilled')

        # Extract shipping cost
        shipping_cost = 0
        if ml_order.get('shipping') and ml_order['shipping'].get('cost'):
            shipping_cost = float(ml_order['shipping']['cost'])

        # Determine order status
        ml_status = ml_order.get('status', 'pending')
        status_map = {
            'confirmed': 'completed',
            'payment_required': 'pending',
            'payment_in_process': 'pending',
            'partially_paid': 'pending',
            'paid': 'completed',
            'cancelled': 'cancelled'
        }
        order_status = status_map.get(ml_status, 'pending')

        return {
            'external_id': str(ml_order['id']),
            'order_number': f"ML-{ml_order['id']}",
            'source': 'mercadolibre',
            'customer': customer_data,
            'items': items,
            'subtotal': float(ml_order.get('total_amount', 0)) - shipping_cost,
            'tax_amount': 0,  # ML includes tax in price
            'shipping_cost': shipping_cost,
            'discount_amount': 0,
            'total': float(ml_order.get('total_amount', 0)),
            'status': order_status,
            'payment_status': payment_status,
            'fulfillment_status': shipping_status,
            'order_date': ml_order.get('date_created', datetime.now().isoformat())
        }

    async def get_sync_stats(self) -> Dict:
        """
        Get sync statistics for MercadoLibre

        Returns:
            Dict with sync stats
        """
        conn = self.get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        try:
            # Get product stats
            cursor.execute("""
                SELECT COUNT(*) as total
                FROM products
                WHERE source = 'mercadolibre'
            """)
            products = cursor.fetchone()

            # Get order stats
            cursor.execute("""
                SELECT COUNT(*) as total
                FROM orders
                WHERE source = 'mercadolibre'
            """)
            orders = cursor.fetchone()

            # Get recent sync logs
            cursor.execute("""
                SELECT sync_type, status, records_processed, records_failed,
                       completed_at
                FROM sync_logs
                WHERE source = 'mercadolibre'
                ORDER BY completed_at DESC
                LIMIT 10
            """)
            recent_syncs = cursor.fetchall()

            return {
                'products_synced': products['total'] if products else 0,
                'orders_synced': orders['total'] if orders else 0,
                'recent_syncs': [dict(row) for row in recent_syncs] if recent_syncs else []
            }

        finally:
            cursor.close()
            conn.close()
