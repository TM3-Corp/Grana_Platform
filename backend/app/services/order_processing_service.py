"""
Order Processing Service
Handles order ingestion from external sources with conversion logic

Author: TM3
Date: 2025-10-03
"""
import os
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import psycopg2
from psycopg2.extras import RealDictCursor
from decimal import Decimal

from app.services.conversion_service import ConversionService


class OrderProcessingService:
    """
    Service for processing orders from external sources

    Handles:
    - Customer creation/matching
    - Product mapping (Shopify SKU → Our SKU)
    - Unit conversions
    - Order storage in database
    - Audit logging
    """

    def __init__(self, db_connection_string: str):
        self.db_connection_string = db_connection_string
        self.conversion_service = ConversionService(db_connection_string)

    def get_db_connection(self):
        """Get database connection"""
        return psycopg2.connect(self.db_connection_string)

    def find_or_create_customer(self, customer_data: Dict, conn=None) -> int:
        """
        Find existing customer or create new one

        Args:
            customer_data: Customer info from external source
            conn: Database connection (optional, will create if not provided)

        Returns:
            customer_id
        """
        should_close = conn is None
        if conn is None:
            conn = self.get_db_connection()

        try:
            cursor = conn.cursor(cursor_factory=RealDictCursor)

            # Try to find by external_id + source
            if customer_data.get('external_id') and customer_data.get('source'):
                cursor.execute("""
                    SELECT id FROM customers
                    WHERE external_id = %s AND source = %s
                """, (customer_data['external_id'], customer_data['source']))

                result = cursor.fetchone()
                if result:
                    return result['id']

            # Try to find by email
            if customer_data.get('email'):
                cursor.execute("""
                    SELECT id FROM customers
                    WHERE email = %s
                """, (customer_data['email'],))

                result = cursor.fetchone()
                if result:
                    return result['id']

            # Create new customer
            cursor.execute("""
                INSERT INTO customers (
                    external_id, source, name, email, phone,
                    address, city, type_customer, is_active
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s
                )
                RETURNING id
            """, (
                customer_data.get('external_id'),
                customer_data.get('source', 'unknown'),
                customer_data.get('name', 'Guest Customer'),
                customer_data.get('email'),
                customer_data.get('phone'),
                customer_data.get('address'),
                customer_data.get('city'),
                customer_data.get('type_customer', 'person'),
                True
            ))

            result = cursor.fetchone()
            conn.commit()
            return result['id']

        finally:
            cursor.close()
            if should_close:
                conn.close()

    def map_sku(self, external_sku: str, source: str, conn=None) -> Optional[str]:
        """
        Map external SKU to our internal SKU

        Args:
            external_sku: SKU from external system
            source: Source system ('shopify', 'mercadolibre', etc.)
            conn: Database connection

        Returns:
            Our internal SKU or None if not found
        """
        should_close = conn is None
        if conn is None:
            conn = self.get_db_connection()

        try:
            cursor = conn.cursor(cursor_factory=RealDictCursor)

            # First, try exact match on our products
            cursor.execute("""
                SELECT sku FROM products
                WHERE sku = %s AND is_active = true
            """, (external_sku,))

            result = cursor.fetchone()
            if result:
                return result['sku']

            # Try to find by external_id and source
            cursor.execute("""
                SELECT sku FROM products
                WHERE external_id = %s AND source = %s AND is_active = true
            """, (external_sku, source))

            result = cursor.fetchone()
            if result:
                return result['sku']

            # SKU not found in our catalog
            return None

        finally:
            cursor.close()
            if should_close:
                conn.close()

    def process_order(self, order_data: Dict, apply_conversions: bool = True) -> Dict:
        """
        Process an order from external source

        Steps:
        1. Find/create customer
        2. Map SKUs
        3. Apply conversions if needed
        4. Create order in database
        5. Create order items
        6. Log to sync_logs

        Args:
            order_data: Normalized order data
            apply_conversions: Whether to apply unit conversions

        Returns:
            Dict with order_id and status
        """
        conn = self.get_db_connection()

        try:
            cursor = conn.cursor(cursor_factory=RealDictCursor)

            # Check if order already exists
            cursor.execute("""
                SELECT id FROM orders
                WHERE external_id = %s AND source = %s
            """, (order_data['external_id'], order_data['source']))

            existing = cursor.fetchone()
            if existing:
                return {
                    'success': True,
                    'order_id': existing['id'],
                    'status': 'already_exists',
                    'message': f"Order already synced: {order_data['order_number']}"
                }

            # 1. Find or create customer
            customer_id = None
            if order_data.get('customer'):
                customer_id = self.find_or_create_customer(order_data['customer'], conn)

            # 2. Determine channel
            # Default to web_shopify for now, we'll make this smarter later
            source_to_channel = {
                'shopify': 'web_shopify',
                'mercadolibre': 'marketplace_ml',
                'walmart': 'retail_walmart',
                'cencosud': 'retail_cencosud'
            }

            cursor.execute("""
                SELECT id FROM channels
                WHERE code = %s
            """, (source_to_channel.get(order_data['source'], 'web_shopify'),))

            channel = cursor.fetchone()
            channel_id = channel['id'] if channel else None

            # 3. Create order
            cursor.execute("""
                INSERT INTO orders (
                    external_id, order_number, source,
                    customer_id, channel_id,
                    subtotal, tax_amount, shipping_cost, discount_amount, total,
                    status, payment_status, fulfillment_status,
                    order_date, customer_notes
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                )
                RETURNING id
            """, (
                order_data['external_id'],
                order_data['order_number'],
                order_data['source'],
                customer_id,
                channel_id,
                order_data.get('subtotal', 0),
                order_data.get('tax_amount', 0),
                order_data.get('shipping_cost', 0),
                order_data.get('discount_amount', 0),
                order_data['total'],
                order_data.get('status', 'pending'),
                order_data.get('payment_status', 'pending'),
                order_data.get('fulfillment_status', 'unfulfilled'),
                order_data.get('order_date', datetime.now()),
                f"Imported from {order_data['source']}"
            ))

            order_result = cursor.fetchone()
            order_id = order_result['id']

            # 4. Process and create order items
            unmapped_skus = []
            for item in order_data.get('items', []):
                # Map SKU
                our_sku = self.map_sku(item['product_sku'], order_data['source'], conn)

                # Find product in database
                product_id = None
                if our_sku:
                    cursor.execute("""
                        SELECT id FROM products WHERE sku = %s
                    """, (our_sku,))
                    product = cursor.fetchone()
                    if product:
                        product_id = product['id']
                else:
                    unmapped_skus.append(item['product_sku'])

                # Create order item
                cursor.execute("""
                    INSERT INTO order_items (
                        order_id, product_id,
                        product_sku, product_name,
                        quantity, unit_price, subtotal, tax_amount, total
                    ) VALUES (
                        %s, %s, %s, %s, %s, %s, %s, %s, %s
                    )
                """, (
                    order_id,
                    product_id,
                    item['product_sku'],
                    item['product_name'],
                    item['quantity'],
                    item['unit_price'],
                    item.get('subtotal', item['quantity'] * item['unit_price']),
                    item.get('tax_amount', 0),
                    item['total']
                ))

            # 5. Log sync
            import json
            cursor.execute("""
                INSERT INTO sync_logs (
                    source, sync_type, status,
                    records_processed, records_failed,
                    details, started_at, completed_at
                ) VALUES (
                    %s, %s, %s, %s, %s, %s::jsonb, NOW(), NOW()
                )
            """, (
                order_data['source'],
                'orders',
                'success',
                1,
                len(unmapped_skus),
                json.dumps({
                    'order_number': order_data['order_number'],
                    'unmapped_skus': unmapped_skus
                })
            ))

            conn.commit()

            return {
                'success': True,
                'order_id': order_id,
                'status': 'created',
                'message': f"Order {order_data['order_number']} created successfully",
                'warnings': unmapped_skus if unmapped_skus else None
            }

        except Exception as e:
            conn.rollback()
            # Log failed sync
            try:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO sync_logs (
                        source, sync_type, status,
                        records_processed, records_failed,
                        error_message, started_at, completed_at
                    ) VALUES (
                        %s, %s, %s, %s, %s, %s, NOW(), NOW()
                    )
                """, (
                    order_data['source'],
                    'orders',
                    'failed',
                    0,
                    1,
                    str(e)
                ))
                conn.commit()
            except:
                pass

            raise Exception(f"Failed to process order: {e}")

        finally:
            cursor.close()
            conn.close()

    def sync_product_from_external(self, product_data: Dict) -> Dict:
        """
        Sync a product from external source to our database

        Args:
            product_data: Normalized product data

        Returns:
            Dict with product_id and status
        """
        conn = self.get_db_connection()

        try:
            cursor = conn.cursor(cursor_factory=RealDictCursor)

            # Check if product exists
            cursor.execute("""
                SELECT id FROM products
                WHERE external_id = %s AND source = %s
            """, (product_data['external_id'], product_data['source']))

            existing = cursor.fetchone()

            if existing:
                # Update existing product
                cursor.execute("""
                    UPDATE products SET
                        name = %s,
                        description = %s,
                        category = %s,
                        brand = %s,
                        sale_price = %s,
                        current_stock = %s,
                        is_active = %s,
                        updated_at = NOW()
                    WHERE id = %s
                    RETURNING id
                """, (
                    product_data['name'],
                    product_data.get('description'),
                    product_data.get('category'),
                    product_data.get('brand'),
                    product_data.get('sale_price', 0),
                    product_data.get('current_stock', 0),
                    product_data.get('is_active', True),
                    existing['id']
                ))

                conn.commit()
                return {
                    'success': True,
                    'product_id': existing['id'],
                    'status': 'updated'
                }
            else:
                # Create new product
                cursor.execute("""
                    INSERT INTO products (
                        external_id, source, sku, name, description,
                        category, brand, unit, sale_price, current_stock, is_active
                    ) VALUES (
                        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                    )
                    RETURNING id
                """, (
                    product_data['external_id'],
                    product_data['source'],
                    product_data['sku'],
                    product_data['name'],
                    product_data.get('description'),
                    product_data.get('category'),
                    product_data.get('brand'),
                    product_data.get('unit', 'unidad'),
                    product_data.get('sale_price', 0),
                    product_data.get('current_stock', 0),
                    product_data.get('is_active', True)
                ))

                result = cursor.fetchone()
                conn.commit()
                return {
                    'success': True,
                    'product_id': result['id'],
                    'status': 'created'
                }

        finally:
            cursor.close()
            conn.close()
