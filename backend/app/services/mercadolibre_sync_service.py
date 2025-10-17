"""
MercadoLibre Sync Service
Syncs products and orders from MercadoLibre to database

Refactored to use repository pattern for data access.

Author: TM3
Date: 2025-10-04
Updated: 2025-10-17 (Repository pattern)
"""
from typing import Dict, List, Optional
from datetime import datetime
import logging

from app.connectors.mercadolibre_connector import MercadoLibreConnector
from app.services.order_processing_service import OrderProcessingService
from app.repositories.mercadolibre_repository import MercadoLibreRepository

logger = logging.getLogger(__name__)


class MercadoLibreSyncService:
    """
    Service to sync MercadoLibre data to our database

    Handles:
    - Product sync from ML listings
    - Order sync from ML sales
    - Customer data from ML buyers
    - Data transformation to our schema

    Uses MercadoLibreRepository for data access.
    """

    def __init__(self, db_connection_string: str):
        self.db_connection_string = db_connection_string
        self.connector = MercadoLibreConnector()
        self.order_processor = OrderProcessingService(db_connection_string)
        self.ml_repo = MercadoLibreRepository()

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

            synced = 0
            failed = 0

            for listing in listings:
                try:
                    # Check if product already exists
                    existing = self.ml_repo.find_product_by_external_id(listing['id'])

                    if existing:
                        # Update existing product
                        self.ml_repo.update_product(
                            external_id=listing['id'],
                            name=listing['title'],
                            sale_price=listing.get('price', 0),
                            current_stock=listing.get('available_quantity', 0),
                            is_active=listing.get('status') == 'active'
                        )
                    else:
                        # Create new product
                        # Generate SKU from ML item ID if no custom SKU
                        sku = listing.get('sku') or f"ML-{listing['id']}"

                        self.ml_repo.upsert_product(
                            external_id=listing['id'],
                            sku=sku,
                            name=listing['title'],
                            sale_price=listing.get('price', 0),
                            current_stock=listing.get('available_quantity', 0),
                            is_active=listing.get('status') == 'active'
                        )

                    synced += 1

                except Exception as e:
                    logger.error(f"Failed to sync product {listing.get('id')}: {e}")
                    failed += 1
                    continue

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
        try:
            # Use repository to get stats
            return self.ml_repo.get_sync_stats()

        except Exception as e:
            logger.error(f"Failed to get sync stats: {e}")
            return {
                'products_synced': 0,
                'orders_synced': 0,
                'recent_syncs': []
            }
