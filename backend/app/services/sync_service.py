"""
Sync Service - Business logic for scheduled data synchronization
Handles syncing sales from RelBase and inventory from RelBase + MercadoLibre

Author: Claude Code
Date: 2025-11-28
"""
import os
import json
import time
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from dataclasses import dataclass

import requests
import httpx

from app.core.database import get_db_connection_with_retry

logger = logging.getLogger(__name__)


# ============================================================================
# Response Models (dataclasses for type safety)
# ============================================================================

@dataclass
class SalesSyncResult:
    success: bool
    message: str
    orders_created: int
    orders_updated: int
    order_items_created: int
    errors: List[str]
    date_range: Dict[str, str]
    duration_seconds: float


@dataclass
class InventorySyncResult:
    success: bool
    message: str
    relbase_warehouses_synced: int
    relbase_products_updated: int
    mercadolibre_products_updated: int
    errors: List[str]
    duration_seconds: float


# ============================================================================
# Sync Service
# ============================================================================

class SyncService:
    """
    Service for synchronizing data from external sources (RelBase, MercadoLibre)

    Designed to be called by UptimeRobot or similar services to:
    1. Keep the Railway service warm (prevent cold starts)
    2. Sync data incrementally (fill gaps since last sync)
    """

    def __init__(self):
        # RelBase API configuration
        self.relbase_base_url = "https://api.relbase.cl"
        self.relbase_company_token = os.getenv('RELBASE_COMPANY_TOKEN')
        self.relbase_user_token = os.getenv('RELBASE_USER_TOKEN')

        # MercadoLibre API configuration
        self.ml_access_token = os.getenv('ML_ACCESS_TOKEN')
        self.ml_seller_id = os.getenv('ML_SELLER_ID')

        # Rate limiting
        self.rate_limit_delay = 0.17  # ~6 requests/second

    # =========================================================================
    # Status Methods
    # =========================================================================

    async def get_sync_status(self) -> Dict:
        """
        Get current sync status and statistics

        Returns:
            Dictionary with sync timestamps and counts
        """
        conn = get_db_connection_with_retry()
        cursor = conn.cursor()

        try:
            # Get last sales sync timestamp
            cursor.execute("""
                SELECT MAX(completed_at) as last_sync
                FROM sync_logs
                WHERE sync_type = 'orders' AND status = 'success'
            """)
            last_sales_sync = cursor.fetchone()[0]

            # Get last inventory sync timestamp
            cursor.execute("""
                SELECT MAX(completed_at) as last_sync
                FROM sync_logs
                WHERE sync_type = 'inventory' AND status = 'success'
            """)
            last_inventory_sync = cursor.fetchone()[0]

            # Get orders count and last order date
            cursor.execute("""
                SELECT COUNT(*) as count, MAX(order_date) as last_date
                FROM orders
                WHERE source = 'relbase'
            """)
            orders_result = cursor.fetchone()
            orders_count = orders_result[0] or 0
            last_order_date = orders_result[1]

            # Get warehouse count
            cursor.execute("""
                SELECT COUNT(*) as count
                FROM warehouses
                WHERE source = 'relbase' AND is_active = true
            """)
            warehouses_count = cursor.fetchone()[0] or 0

            # Get products with stock count
            cursor.execute("""
                SELECT COUNT(DISTINCT product_id) as count
                FROM warehouse_stock
                WHERE quantity > 0
            """)
            products_with_stock = cursor.fetchone()[0] or 0

            return {
                "last_sales_sync": last_sales_sync,
                "last_inventory_sync": last_inventory_sync,
                "orders_count": orders_count,
                "last_order_date": last_order_date,
                "warehouses_count": warehouses_count,
                "products_with_stock": products_with_stock
            }

        finally:
            cursor.close()
            conn.close()

    # =========================================================================
    # RelBase API Methods
    # =========================================================================

    def _get_relbase_headers(self) -> Dict[str, str]:
        """Get authentication headers for RelBase API"""
        return {
            'company': self.relbase_company_token,
            'authorization': self.relbase_user_token,
            'Content-Type': 'application/json'
        }

    def _fetch_relbase_dtes(self, date_from: str, date_to: str, page: int = 1, doc_type: int = 33) -> Dict:
        """
        Fetch DTEs (invoices/boletas) from RelBase API

        Args:
            date_from: Start date (YYYY-MM-DD)
            date_to: End date (YYYY-MM-DD)
            page: Page number for pagination
            doc_type: Document type (33=Factura, 39=Boleta)

        Returns:
            API response with DTEs
        """
        url = f"{self.relbase_base_url}/api/v1/dtes"
        headers = self._get_relbase_headers()
        # IMPORTANT: RelBase API uses 'start_date' and 'end_date' parameters
        # NOT 'date_from' and 'date_to' (which are silently ignored!)
        params = {
            'type_document': doc_type,
            'start_date': date_from,  # Correct param name for RelBase API
            'end_date': date_to,      # Correct param name for RelBase API
            'page': page,
            'per_page': 100
        }

        try:
            response = requests.get(url, headers=headers, params=params, timeout=60)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Error fetching RelBase DTEs (type={doc_type}): {e}")
            return {}

    def _fetch_relbase_dte_detail(self, dte_id: int) -> Dict:
        """Fetch detailed DTE information including products"""
        url = f"{self.relbase_base_url}/api/v1/dtes/{dte_id}"
        headers = self._get_relbase_headers()

        try:
            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Error fetching DTE {dte_id}: {e}")
            return {}

    def _fetch_relbase_warehouses(self) -> List[Dict]:
        """Fetch all warehouses from RelBase API"""
        url = f"{self.relbase_base_url}/api/v1/bodegas"
        headers = self._get_relbase_headers()

        try:
            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()
            data = response.json()
            return data.get('data', {}).get('warehouses', [])
        except Exception as e:
            logger.error(f"Error fetching RelBase warehouses: {e}")
            return []

    def _fetch_relbase_lot_serial(self, product_id: int, warehouse_id: int) -> List[Dict]:
        """Fetch lot/serial numbers for a product in a warehouse"""
        url = f"{self.relbase_base_url}/api/v1/productos/{product_id}/lotes_series/{warehouse_id}"
        headers = self._get_relbase_headers()

        try:
            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()
            data = response.json()
            return data.get('data', {}).get('lot_serial_numbers', [])
        except Exception as e:
            if hasattr(e, 'response') and e.response.status_code == 404:
                return []  # No lots found (normal case)
            logger.error(f"Error fetching lots for product {product_id}: {e}")
            return []

    def _fetch_relbase_customer(self, customer_id: int) -> Optional[Dict]:
        """
        Fetch customer details from RelBase API

        Args:
            customer_id: RelBase customer ID

        Returns:
            Customer data dict or None if not found
        """
        url = f"{self.relbase_base_url}/api/v1/clientes/{customer_id}"
        headers = self._get_relbase_headers()

        try:
            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            if hasattr(e, 'response') and getattr(e.response, 'status_code', None) == 404:
                logger.warning(f"Customer {customer_id} not found in RelBase")
                return None
            logger.error(f"Error fetching customer {customer_id}: {e}")
            return None

    # =========================================================================
    # MercadoLibre API Methods
    # =========================================================================

    async def _fetch_ml_listings(self) -> List[Dict]:
        """Fetch active listings from MercadoLibre"""
        if not self.ml_access_token or not self.ml_seller_id:
            logger.warning("MercadoLibre credentials not configured")
            return []

        base_url = "https://api.mercadolibre.com"
        headers = {
            'Authorization': f'Bearer {self.ml_access_token}',
            'Accept': 'application/json'
        }

        async with httpx.AsyncClient() as client:
            try:
                # Get item IDs
                response = await client.get(
                    f"{base_url}/users/{self.ml_seller_id}/items/search",
                    headers=headers,
                    params={'status': 'active'},
                    timeout=30.0
                )
                response.raise_for_status()
                data = response.json()

                item_ids = data.get('results', [])

                # Get details for each item (limited to 50 for performance)
                listings = []
                for item_id in item_ids[:50]:
                    item_response = await client.get(
                        f"{base_url}/items/{item_id}",
                        headers=headers,
                        timeout=30.0
                    )
                    if item_response.status_code == 200:
                        item_data = item_response.json()
                        listings.append({
                            'id': item_data.get('id'),
                            'title': item_data.get('title'),
                            'sku': item_data.get('seller_custom_field', ''),
                            'available_quantity': item_data.get('available_quantity', 0),
                            'status': item_data.get('status')
                        })

                return listings

            except Exception as e:
                logger.error(f"Error fetching ML listings: {e}")
                return []

    # =========================================================================
    # Sales Sync Logic
    # =========================================================================

    async def sync_sales_from_relbase(
        self,
        days_back: int = 7,
        force_full: bool = False,
        date_from_override: Optional[str] = None,
        date_to_override: Optional[str] = None
    ) -> SalesSyncResult:
        """
        Sync sales orders from RelBase

        Logic:
        1. Get last order date in database (or use days_back for full sync)
        2. Fetch all DTEs from RelBase since that date
        3. Create/update orders and order_items
        4. Fill any gaps in data

        Args:
            days_back: How many days to look back for gaps
            force_full: If True, sync all data regardless of last date
            date_from_override: Override start date (YYYY-MM-DD format)
            date_to_override: Override end date (YYYY-MM-DD format)

        Returns:
            SalesSyncResult with statistics
        """
        start_time = time.time()
        errors = []
        orders_created = 0
        orders_updated = 0
        order_items_created = 0

        conn = get_db_connection_with_retry()
        cursor = conn.cursor()

        try:
            # Determine date range
            if date_from_override and date_to_override:
                # Use explicit date range override
                date_from = date_from_override
                date_to = date_to_override
                logger.info(f"Using explicit date range override: {date_from} to {date_to}")
            elif force_full:
                # Sync from beginning of year
                date_from = datetime(datetime.now().year, 1, 1).strftime('%Y-%m-%d')
                date_to = datetime.now().strftime('%Y-%m-%d')
            else:
                # Get last order date or use days_back
                cursor.execute("""
                    SELECT MAX(order_date) FROM orders WHERE source = 'relbase'
                """)
                last_date = cursor.fetchone()[0]

                if last_date:
                    # Start from last date minus days_back (to fill gaps)
                    date_from = (last_date - timedelta(days=days_back)).strftime('%Y-%m-%d')
                else:
                    # No orders yet, sync last 30 days
                    date_from = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')

                date_to = datetime.now().strftime('%Y-%m-%d')

            logger.info(f"Syncing RelBase DTEs from {date_from} to {date_to}")

            # Get fallback channel ID for orders without channel_id in RelBase
            cursor.execute("SELECT id FROM channels WHERE code = 'relbase'")
            fallback_channel_result = cursor.fetchone()
            fallback_channel_id = fallback_channel_result[0] if fallback_channel_result else None

            # Fetch DTEs from RelBase for both Facturas (33) and Boletas (39)
            total_dtes = 0
            document_types = [33, 39]  # 33=Factura, 39=Boleta

            for doc_type in document_types:
                page = 1
                logger.info(f"Fetching document type {doc_type}...")

                while True:
                    dte_response = self._fetch_relbase_dtes(date_from, date_to, page, doc_type)

                    if not dte_response:
                        break

                    dtes = dte_response.get('data', {}).get('dtes', [])

                    if not dtes:
                        break

                    total_dtes += len(dtes)

                    for dte in dtes:
                        try:
                            dte_id = dte.get('id')

                            # Check if order exists
                            cursor.execute("""
                                SELECT id FROM orders
                                WHERE external_id = %s AND source = 'relbase'
                            """, (str(dte_id),))

                            existing = cursor.fetchone()

                            if existing:
                                # Order exists, could update if needed
                                orders_updated += 1
                                continue

                            # Fetch DTE details for products
                            dte_detail = self._fetch_relbase_dte_detail(dte_id)
                            time.sleep(self.rate_limit_delay)  # Rate limiting

                            if not dte_detail:
                                errors.append(f"Could not fetch details for DTE {dte_id}")
                                continue

                            # API returns data directly (not nested in 'dte')
                            dte_data = dte_detail.get('data', {})

                            # Parse DTE data (using correct Relbase field names)
                            folio = dte_data.get('folio', str(dte_id))
                            total = float(dte_data.get('amount_total', 0))
                            tax = float(dte_data.get('amount_iva', 0))
                            net = float(dte_data.get('amount_neto', total - tax))

                            # Parse date (start_date or created_at)
                            date_str = dte_data.get('start_date') or dte_data.get('created_at')
                            try:
                                if date_str:
                                    order_date = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                                else:
                                    order_date = datetime.now()
                            except:
                                order_date = datetime.now()

                            # Customer info (customer_id is direct field, not nested)
                            customer_id_relbase = dte_data.get('customer_id')
                            channel_id_relbase = dte_data.get('channel_id')

                            # SII status from RelBase (accepted, accepted_objection, cancel, declined)
                            sii_status = dte_data.get('sii_status', 'accepted')

                            # Map RelBase channel_id to internal channel via external_id
                            channel_id = fallback_channel_id  # Default to "Relbase" channel
                            if channel_id_relbase:
                                cursor.execute("""
                                    SELECT id FROM channels
                                    WHERE external_id = %s AND source = 'relbase'
                                """, (str(channel_id_relbase),))
                                channel_result = cursor.fetchone()
                                if channel_result:
                                    channel_id = channel_result[0]

                            # Map RelBase customer_id to internal customer via external_id
                            # If not found, fetch from API and create
                            customer_id = None
                            if customer_id_relbase:
                                cursor.execute("""
                                    SELECT id FROM customers
                                    WHERE external_id = %s AND source = 'relbase'
                                """, (str(customer_id_relbase),))
                                customer_result = cursor.fetchone()
                                if customer_result:
                                    customer_id = customer_result[0]
                                else:
                                    # Customer not found - fetch from RelBase API and create
                                    try:
                                        customer_response = self._fetch_relbase_customer(customer_id_relbase)
                                        if customer_response:
                                            cust_data = customer_response.get('data', {})
                                            cursor.execute("""
                                                INSERT INTO customers
                                                (external_id, source, name, rut, email, phone, address, created_at)
                                                VALUES (%s, 'relbase', %s, %s, %s, %s, %s, NOW())
                                                RETURNING id
                                            """, (
                                                str(customer_id_relbase),
                                                cust_data.get('name', f'Customer {customer_id_relbase}'),
                                                cust_data.get('rut', ''),
                                                cust_data.get('email', ''),
                                                cust_data.get('phone', ''),
                                                cust_data.get('address', '')
                                            ))
                                            customer_id = cursor.fetchone()[0]
                                            logger.info(f"Created new customer: {cust_data.get('name')} (ID: {customer_id})")
                                    except Exception as e:
                                        logger.warning(f"Could not create customer {customer_id_relbase}: {e}")

                            # Create order
                            cursor.execute("""
                                INSERT INTO orders
                                (external_id, order_number, source, channel_id, customer_id,
                                 subtotal, tax_amount, total, status, payment_status,
                                 invoice_status, order_date, invoice_number, invoice_type, invoice_date,
                                 customer_notes, created_at)
                                VALUES (%s, %s, 'relbase', %s, %s, %s, %s, %s, 'completed', 'paid',
                                        %s, %s, %s, %s, %s, %s, NOW())
                                RETURNING id
                            """, (
                                str(dte_id),
                                folio,
                                channel_id,
                                customer_id,
                                net,
                                tax,
                                total,
                                sii_status,  # Use SII status from RelBase API
                                order_date,
                                folio,
                                'factura' if dte_data.get('type_document') == 33 else 'boleta',
                                order_date,
                                json.dumps({
                                    'relbase_id': dte_id,
                                    'customer_id_relbase': customer_id_relbase,
                                    'channel_id_relbase': channel_id_relbase
                                })
                            ))

                            order_id = cursor.fetchone()[0]
                            orders_created += 1

                            # Create order items
                            # NOTE: We store the raw product_code from RelBase.
                            # SKU mapping to official catalog is done at display time by
                            # audit.py's map_sku_with_quantity() function using ProductCatalogService.
                            # This approach uses 13 smart rules (exact match, ANU- prefix, _WEB suffix, etc.)
                            # instead of the legacy relbase_product_mappings table.
                            products = dte_data.get('products', [])
                            for product in products:
                                product_code = product.get('code', '')
                                product_name = product.get('name', '')
                                quantity = float(product.get('quantity', 0))  # Can be decimal
                                price = float(product.get('price', 0))
                                subtotal = quantity * price

                                cursor.execute("""
                                    INSERT INTO order_items
                                    (order_id, product_id, product_sku, product_name,
                                     quantity, unit_price, subtotal, total, created_at)
                                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, NOW())
                                """, (
                                    order_id,
                                    None,  # product_id not used - mapping done at display time
                                    product_code,  # Store raw RelBase code
                                    product_name,
                                    quantity,
                                    price,
                                    subtotal,
                                    subtotal
                                ))
                                order_items_created += 1

                        except Exception as e:
                            errors.append(f"Error processing DTE {dte.get('id')}: {str(e)}")
                            logger.error(f"Error processing DTE: {e}")
                            continue

                    # Check for more pages
                    # NOTE: RelBase API returns pagination info in 'meta', not 'data.pagination'
                    pagination = dte_response.get('meta', {})
                    if page >= pagination.get('total_pages', 1):
                        break

                    page += 1
                    time.sleep(self.rate_limit_delay)  # Rate limiting between pages

            # Commit changes
            conn.commit()

            # Refresh materialized view for sales analytics (if orders were created)
            if orders_created > 0:
                try:
                    logger.info("Refreshing sales_facts_mv materialized view...")
                    cursor.execute("REFRESH MATERIALIZED VIEW sales_facts_mv")
                    conn.commit()
                    logger.info("Materialized view refreshed successfully")
                except Exception as mv_error:
                    logger.warning(f"Could not refresh materialized view: {mv_error}")
                    # Don't fail the whole sync if MV refresh fails

            # Log sync
            cursor.execute("""
                INSERT INTO sync_logs
                (source, sync_type, status, records_processed, records_failed,
                 details, started_at, completed_at)
                VALUES ('relbase', 'orders', %s, %s, %s, %s::jsonb, %s, NOW())
            """, (
                'success' if not errors else 'partial',
                orders_created + orders_updated,
                len(errors),
                json.dumps({
                    'date_range': {'from': date_from, 'to': date_to},
                    'orders_created': orders_created,
                    'orders_updated': orders_updated,
                    'order_items_created': order_items_created,
                    'errors': errors[:10]  # Limit stored errors
                }),
                datetime.now() - timedelta(seconds=time.time() - start_time)
            ))
            conn.commit()

            duration = time.time() - start_time

            return SalesSyncResult(
                success=len(errors) == 0,
                message=f"Synced {orders_created} new orders, {orders_updated} existing" if not errors else f"Completed with {len(errors)} errors",
                orders_created=orders_created,
                orders_updated=orders_updated,
                order_items_created=order_items_created,
                errors=errors[:10],  # Limit returned errors
                date_range={'from': date_from, 'to': date_to},
                duration_seconds=round(duration, 2)
            )

        except Exception as e:
            conn.rollback()
            logger.error(f"Sales sync failed: {e}")
            errors.append(str(e))

            return SalesSyncResult(
                success=False,
                message=f"Sync failed: {str(e)}",
                orders_created=orders_created,
                orders_updated=orders_updated,
                order_items_created=order_items_created,
                errors=errors,
                date_range={'from': date_from, 'to': date_to},
                duration_seconds=round(time.time() - start_time, 2)
            )

        finally:
            cursor.close()
            conn.close()

    # =========================================================================
    # Inventory Sync Logic
    # =========================================================================

    async def sync_inventory(self) -> InventorySyncResult:
        """
        Sync inventory from RelBase and MercadoLibre

        Logic:
        1. Fetch warehouses from RelBase and sync to database
        2. For products with external_id, fetch lot/serial stock from RelBase
        3. Fetch active listings from MercadoLibre and update stock

        Returns:
            InventorySyncResult with statistics
        """
        start_time = time.time()
        errors = []
        warehouses_synced = 0
        relbase_products_updated = 0
        ml_products_updated = 0

        conn = get_db_connection_with_retry()
        cursor = conn.cursor()

        try:
            # ================================================================
            # Phase 1: Sync Warehouses from RelBase
            # ================================================================
            logger.info("Phase 1: Syncing warehouses from RelBase...")

            warehouses = self._fetch_relbase_warehouses()

            for wh in warehouses:
                warehouse_id = wh['id']
                name = wh['name']
                address = wh.get('address', '')
                enabled = wh.get('enabled', True)

                # Sanitize code: remove special chars, accents, numbers; lowercase, underscores only
                import unicodedata
                code = unicodedata.normalize('NFD', name)
                code = code.encode('ascii', 'ignore').decode('ascii')  # Remove accents
                code = code.lower().replace(' ', '_').replace('-', '_')
                code = ''.join(c for c in code if c.isalpha() or c == '_')  # Keep only letters and underscore
                # Ensure code is not empty and doesn't start/end with underscore
                code = code.strip('_')
                if not code:
                    code = "warehouse_unnamed"  # Fallback for empty codes

                # Upsert warehouse
                cursor.execute("""
                    INSERT INTO warehouses (code, name, location, external_id, source, update_method, is_active)
                    VALUES (%s, %s, %s, %s, 'relbase', 'api', %s)
                    ON CONFLICT (code) DO UPDATE SET
                        external_id = EXCLUDED.external_id,
                        name = EXCLUDED.name,
                        location = EXCLUDED.location,
                        is_active = EXCLUDED.is_active,
                        updated_at = NOW()
                """, (code, name, address, str(warehouse_id), enabled))

                warehouses_synced += 1

            conn.commit()
            logger.info(f"Synced {warehouses_synced} warehouses")

            # ================================================================
            # Phase 2: Sync Stock from RelBase (for products with external_id)
            # ================================================================
            logger.info("Phase 2: Syncing stock from RelBase...")

            # Get products with external_id
            cursor.execute("""
                SELECT id, external_id, sku, name
                FROM products
                WHERE external_id IS NOT NULL
                AND source = 'relbase'
                AND is_active = true
            """)
            products = cursor.fetchall()

            # Get warehouses from DB
            cursor.execute("""
                SELECT id, external_id, code
                FROM warehouses
                WHERE source = 'relbase' AND is_active = true
            """)
            db_warehouses = cursor.fetchall()

            # For each product-warehouse combination, fetch stock
            # (Limited to first 20 products for performance in scheduled sync)
            for product in products[:20]:
                product_id_db, product_external_id, product_sku, product_name = product

                for warehouse in db_warehouses:
                    warehouse_id_db, warehouse_external_id, warehouse_code = warehouse

                    try:
                        lots = self._fetch_relbase_lot_serial(
                            int(product_external_id),
                            int(warehouse_external_id)
                        )

                        for lot in lots:
                            cursor.execute("""
                                INSERT INTO warehouse_stock (
                                    product_id, warehouse_id, quantity, lot_number,
                                    expiration_date, last_updated, updated_by
                                )
                                VALUES (%s, %s, %s, %s, %s, NOW(), 'sync_api')
                                ON CONFLICT (product_id, warehouse_id, lot_number)
                                DO UPDATE SET
                                    quantity = EXCLUDED.quantity,
                                    expiration_date = EXCLUDED.expiration_date,
                                    last_updated = NOW(),
                                    updated_by = 'sync_api'
                            """, (
                                product_id_db,
                                warehouse_id_db,
                                lot['stock'],
                                lot['lot_serial_number'],
                                lot.get('expiration_date')
                            ))
                            relbase_products_updated += 1

                        time.sleep(self.rate_limit_delay)

                    except Exception as e:
                        errors.append(f"Error syncing stock for {product_sku}: {str(e)}")

            conn.commit()
            logger.info(f"Updated {relbase_products_updated} stock records from RelBase")

            # ================================================================
            # Phase 3: Sync Stock from MercadoLibre
            # ================================================================
            logger.info("Phase 3: Syncing stock from MercadoLibre...")

            try:
                ml_listings = await self._fetch_ml_listings()

                # Get or create ML warehouse
                cursor.execute("""
                    INSERT INTO warehouses (code, name, source, update_method, is_active)
                    VALUES ('mercadolibre', 'MercadoLibre Stock', 'mercadolibre', 'api', true)
                    ON CONFLICT (code) DO UPDATE SET updated_at = NOW()
                    RETURNING id
                """)
                ml_warehouse_id = cursor.fetchone()[0]

                for listing in ml_listings:
                    sku = listing.get('sku')
                    if not sku:
                        continue

                    # Find product by SKU
                    cursor.execute("SELECT id FROM products WHERE sku = %s", (sku,))
                    product_result = cursor.fetchone()

                    if product_result:
                        product_id = product_result[0]
                        quantity = listing.get('available_quantity', 0)

                        cursor.execute("""
                            INSERT INTO warehouse_stock (
                                product_id, warehouse_id, quantity, lot_number,
                                last_updated, updated_by
                            )
                            VALUES (%s, %s, %s, 'ML_STOCK', NOW(), 'ml_api')
                            ON CONFLICT (product_id, warehouse_id, lot_number)
                            DO UPDATE SET
                                quantity = EXCLUDED.quantity,
                                last_updated = NOW(),
                                updated_by = 'ml_api'
                        """, (product_id, ml_warehouse_id, quantity))

                        ml_products_updated += 1

                conn.commit()
                logger.info(f"Updated {ml_products_updated} products from MercadoLibre")

            except Exception as e:
                errors.append(f"MercadoLibre sync error: {str(e)}")
                logger.error(f"ML sync error: {e}")

            # Log sync
            cursor.execute("""
                INSERT INTO sync_logs
                (source, sync_type, status, records_processed, records_failed,
                 details, started_at, completed_at)
                VALUES ('multiple', 'inventory', %s, %s, %s, %s::jsonb, %s, NOW())
            """, (
                'success' if not errors else 'partial',
                warehouses_synced + relbase_products_updated + ml_products_updated,
                len(errors),
                json.dumps({
                    'warehouses_synced': warehouses_synced,
                    'relbase_products_updated': relbase_products_updated,
                    'ml_products_updated': ml_products_updated,
                    'errors': errors[:10]
                }),
                datetime.now() - timedelta(seconds=time.time() - start_time)
            ))
            conn.commit()

            duration = time.time() - start_time

            return InventorySyncResult(
                success=len(errors) == 0,
                message="Inventory sync completed" if not errors else f"Completed with {len(errors)} errors",
                relbase_warehouses_synced=warehouses_synced,
                relbase_products_updated=relbase_products_updated,
                mercadolibre_products_updated=ml_products_updated,
                errors=errors[:10],
                duration_seconds=round(duration, 2)
            )

        except Exception as e:
            conn.rollback()
            logger.error(f"Inventory sync failed: {e}")
            errors.append(str(e))

            return InventorySyncResult(
                success=False,
                message=f"Sync failed: {str(e)}",
                relbase_warehouses_synced=warehouses_synced,
                relbase_products_updated=relbase_products_updated,
                mercadolibre_products_updated=ml_products_updated,
                errors=errors,
                duration_seconds=round(time.time() - start_time, 2)
            )

        finally:
            cursor.close()
            conn.close()

    # =========================================================================
    # Combined Sync (for background execution)
    # =========================================================================

    async def run_full_sync(self, days_back: int = 3) -> Dict:
        """
        Run full sync (sales + inventory) - designed for background execution

        Args:
            days_back: Days to look back for sales sync

        Returns:
            Combined results dictionary
        """
        logger.info(f"Starting full sync (days_back={days_back})")

        sales_result = await self.sync_sales_from_relbase(days_back=days_back)
        inventory_result = await self.sync_inventory()

        return {
            'sales': {
                'success': sales_result.success,
                'orders_created': sales_result.orders_created,
                'orders_updated': sales_result.orders_updated,
                'errors': len(sales_result.errors)
            },
            'inventory': {
                'success': inventory_result.success,
                'warehouses': inventory_result.relbase_warehouses_synced,
                'products': inventory_result.relbase_products_updated + inventory_result.mercadolibre_products_updated,
                'errors': len(inventory_result.errors)
            },
            'timestamp': datetime.now().isoformat()
        }
