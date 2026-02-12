"""
Sync Service - Business logic for scheduled data synchronization
Handles syncing sales from RelBase and inventory from RelBase + MercadoLibre

Author: Claude Code
Date: 2025-11-28
"""
import asyncio
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
    customers_fixed: int = 0  # Cleanup: customers linked to orders
    channels_fixed: int = 0   # Cleanup: channels fixed for orders


@dataclass
class InventorySyncResult:
    success: bool
    message: str
    relbase_warehouses_synced: int
    relbase_products_updated: int
    mercadolibre_products_updated: int
    klog_products_updated: int = 0  # KLOG direct API sync
    errors: List[str] = None
    duration_seconds: float = 0.0


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
        # Note: .env uses MERCADOLIBRE_* prefix, not ML_*
        self.ml_access_token = os.getenv('MERCADOLIBRE_ACCESS_TOKEN') or os.getenv('ML_ACCESS_TOKEN')
        self.ml_seller_id = os.getenv('MERCADOLIBRE_SELLER_ID') or os.getenv('ML_SELLER_ID')

        # Rate limiting
        self.rate_limit_delay = 0.17  # ~6 requests/second

    # =========================================================================
    # Status Methods
    # =========================================================================

    def get_sync_status(self) -> Dict:
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

    def _relbase_request_with_retry(
        self,
        method: str,
        url: str,
        *,
        params: Optional[Dict] = None,
        timeout: int = 30,
        max_retries: int = 3,
    ) -> Optional[requests.Response]:
        """
        Make a RelBase API request with exponential backoff retry.

        Retries on: timeout, connection error, HTTP 429/500/502/503/504.
        Raises on non-retryable client errors (4xx except 429).

        Returns:
            requests.Response on success, None on exhausted retries.
        """
        headers = self._get_relbase_headers()
        retryable_status_codes = {429, 500, 502, 503, 504}

        for attempt in range(max_retries):
            try:
                if attempt > 0:
                    backoff = min(2 ** attempt, 10)
                    logger.info(f"Retry {attempt}/{max_retries - 1} for {url} (backoff {backoff}s)")
                    time.sleep(backoff)

                response = requests.request(
                    method, url, headers=headers, params=params, timeout=timeout
                )

                if response.status_code < 400:
                    return response

                if response.status_code in retryable_status_codes:
                    logger.warning(
                        f"Retryable HTTP {response.status_code} from {url}, "
                        f"attempt {attempt + 1}/{max_retries}"
                    )
                    continue

                # Non-retryable client error (400, 401, 403, 404, etc.)
                response.raise_for_status()

            except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as e:
                logger.warning(
                    f"{type(e).__name__} for {url}, attempt {attempt + 1}/{max_retries}"
                )
                if attempt == max_retries - 1:
                    logger.error(f"All {max_retries} attempts failed for {url}: {e}")
                    return None
                continue
            except requests.exceptions.HTTPError:
                # Non-retryable HTTP error already logged by raise_for_status
                raise

        logger.error(f"All {max_retries} attempts exhausted for {url}")
        return None

    def _fetch_relbase_dtes(self, date_from: str, date_to: str, page: int = 1, doc_type: int = 33) -> Optional[Dict]:
        """
        Fetch DTEs (invoices/boletas) from RelBase API

        Args:
            date_from: Start date (YYYY-MM-DD)
            date_to: End date (YYYY-MM-DD)
            page: Page number for pagination
            doc_type: Document type (33=Factura, 39=Boleta)

        Returns:
            API response dict on success, None on error.
        """
        url = f"{self.relbase_base_url}/api/v1/dtes"
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
            response = self._relbase_request_with_retry(
                'GET', url, params=params, timeout=60, max_retries=3
            )
            if response is None:
                return None
            return response.json()
        except requests.exceptions.HTTPError as e:
            if e.response is not None and e.response.status_code == 404:
                logger.info(f"DTE type {doc_type} not available in RelBase API (404)")
                return None
            logger.error(f"Error fetching RelBase DTEs (type={doc_type}): {e}")
            return None
        except Exception as e:
            logger.error(f"Error fetching RelBase DTEs (type={doc_type}): {e}")
            return None

    def _fetch_relbase_dte_detail(self, dte_id: int) -> Dict:
        """Fetch detailed DTE information including products"""
        url = f"{self.relbase_base_url}/api/v1/dtes/{dte_id}"

        try:
            response = self._relbase_request_with_retry(
                'GET', url, timeout=30, max_retries=3
            )
            if response is None:
                logger.warning(f"DTE_DETAIL_SKIPPED: Could not fetch detail for DTE {dte_id} after retries")
                return {}
            return response.json()
        except Exception as e:
            logger.error(f"DTE_DETAIL_FAILED: Error fetching DTE {dte_id}: {e}")
            return {}

    def _fetch_relbase_warehouses(self) -> List[Dict]:
        """Fetch all warehouses from RelBase API"""
        url = f"{self.relbase_base_url}/api/v1/bodegas"

        try:
            response = self._relbase_request_with_retry(
                'GET', url, timeout=30, max_retries=3
            )
            if response is None:
                return []
            data = response.json()
            return data.get('data', {}).get('warehouses', [])
        except Exception as e:
            logger.error(f"Error fetching RelBase warehouses: {e}")
            return []

    def _fetch_relbase_lot_serial(self, product_id: int, warehouse_id: int) -> List[Dict]:
        """Fetch lot/serial numbers for a product in a warehouse"""
        url = f"{self.relbase_base_url}/api/v1/productos/{product_id}/lotes_series/{warehouse_id}"

        try:
            response = self._relbase_request_with_retry(
                'GET', url, timeout=30, max_retries=2
            )
            if response is None:
                return []
            data = response.json()
            return data.get('data', {}).get('lot_serial_numbers', [])
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                return []  # No lots found (normal case)
            elif e.response.status_code in (401, 403):
                # Don't log every 401/403 - it floods the logs
                # 401 = unauthorized, 403 = forbidden (product not accessible, e.g. ANU- legacy)
                # Return special marker to indicate auth/permission failure
                return [{'_auth_error': True}]
            logger.error(f"Error fetching lots for product {product_id}: {e}")
            return []
        except Exception as e:
            logger.error(f"Error fetching lots for product {product_id}: {e}")
            return []

    def _fetch_relbase_active_products(self) -> Optional[List[Dict]]:
        """
        Fetch ACTIVE products from RelBase API.

        IMPORTANT: This is the correct way to get products for inventory sync.
        The /api/v1/productos endpoint returns ONLY active products in RelBase,
        avoiding 401/403 errors when syncing legacy/inactive products (e.g., ANU- prefix).

        Previously we used the local `products` table, which may contain stale data
        about products that no longer exist or are inactive in RelBase.

        Returns:
            List of product dictionaries on success, None on error.

        Note:
            - This endpoint may be paginated for large catalogs
            - Products returned here are guaranteed to be accessible for lot/serial queries
            - SKUs starting with ANU- are legacy and should be filtered out
        """
        url = f"{self.relbase_base_url}/api/v1/productos"

        try:
            response = self._relbase_request_with_retry(
                'GET', url, timeout=60, max_retries=3
            )
            if response is None:
                return None
            data = response.json()
            products = data.get('data', {}).get('products', [])

            # Filter out legacy products (ANU- prefix) just in case
            products = [p for p in products if not (p.get('sku', '') or '').upper().startswith('ANU')]

            logger.info(f"Fetched {len(products)} active products from RelBase API")
            return products
        except Exception as e:
            logger.error(f"Error fetching active products from RelBase: {e}")
            return None

    def _fetch_relbase_channels(self) -> List[Dict]:
        """
        Fetch all sales channels from RelBase API

        Returns:
            List of channel dictionaries with id and name
        """
        url = f"{self.relbase_base_url}/api/v1/canal_ventas"

        try:
            response = self._relbase_request_with_retry(
                'GET', url, timeout=30, max_retries=2
            )
            if response is None:
                return []
            data = response.json()
            return data.get('data', {}).get('channels', [])
        except Exception as e:
            logger.error(f"Error fetching RelBase channels: {e}")
            return []

    def _fetch_relbase_customer(self, customer_id: int, retries: int = 3) -> Optional[Dict]:
        """
        Fetch customer details from RelBase API with retry logic

        Args:
            customer_id: RelBase customer ID
            retries: Number of retry attempts (default 3)

        Returns:
            Customer data dict or None if not found
        """
        url = f"{self.relbase_base_url}/api/v1/clientes/{customer_id}"

        try:
            response = self._relbase_request_with_retry(
                'GET', url, timeout=30, max_retries=retries
            )
            if response is None:
                logger.error(f"Failed to fetch customer {customer_id} after {retries} attempts")
                return None
            return response.json()
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                logger.warning(f"Customer {customer_id} not found in RelBase (404)")
                return None
            logger.error(f"HTTP error fetching customer {customer_id}: {e}")
            return None
        except Exception as e:
            logger.error(f"Error fetching customer {customer_id}: {e}")
            return None

    def _fix_missing_order_references(self, cursor) -> tuple:
        """
        Cleanup step: Find and fix orders with missing customer/channel references.

        This catches any orders where customer/channel creation failed during sync.
        Called at the end of sync to ensure data integrity.

        Returns:
            Tuple of (customers_fixed, channels_fixed)
        """
        customers_fixed = 0
        channels_fixed = 0

        # === FIX MISSING CUSTOMERS ===
        # Find orders with customer_id_relbase in notes but no customer_id
        cursor.execute("""
            SELECT
                o.id,
                o.external_id,
                (o.customer_notes::jsonb->>'customer_id_relbase')::int as customer_id_relbase
            FROM orders o
            WHERE o.source = 'relbase'
              AND o.customer_id IS NULL
              AND o.customer_notes IS NOT NULL
              AND o.customer_notes::jsonb ? 'customer_id_relbase'
              AND (o.customer_notes::jsonb->>'customer_id_relbase') IS NOT NULL
              AND (o.customer_notes::jsonb->>'customer_id_relbase') != 'null'
        """)
        orders_missing_customer = cursor.fetchall()

        if orders_missing_customer:
            logger.info(f"Cleanup: Found {len(orders_missing_customer)} orders with missing customer_id")

        for order_id, external_id, customer_id_relbase in orders_missing_customer:
            if not customer_id_relbase:
                continue

            # Check if customer now exists (might have been created by another order)
            cursor.execute("""
                SELECT id FROM customers
                WHERE external_id = %s AND source = 'relbase'
            """, (str(customer_id_relbase),))
            existing = cursor.fetchone()

            if existing:
                customer_id = existing[0]
            else:
                # Fetch from Relbase API and create
                time.sleep(0.15)  # Rate limit protection
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
                        logger.info(f"Cleanup: Created customer {cust_data.get('name')} (ID: {customer_id})")
                    else:
                        logger.warning(f"Cleanup: Could not fetch customer {customer_id_relbase} for order {external_id}")
                        continue
                except Exception as e:
                    logger.error(f"Cleanup: Error creating customer {customer_id_relbase}: {e}")
                    continue

            # Update order with customer_id
            cursor.execute("UPDATE orders SET customer_id = %s WHERE id = %s", (customer_id, order_id))
            customers_fixed += 1
            logger.info(f"Cleanup: Linked order {external_id} to customer {customer_id}")

        # === FIX MISSING CHANNELS ===
        # Find orders with channel_id_relbase in notes but no channel_id (or wrong channel)
        cursor.execute("""
            SELECT
                o.id,
                o.external_id,
                o.channel_id,
                (o.customer_notes::jsonb->>'channel_id_relbase')::int as channel_id_relbase
            FROM orders o
            WHERE o.source = 'relbase'
              AND o.customer_notes IS NOT NULL
              AND o.customer_notes::jsonb ? 'channel_id_relbase'
              AND (o.customer_notes::jsonb->>'channel_id_relbase') IS NOT NULL
              AND (o.customer_notes::jsonb->>'channel_id_relbase') != 'null'
              AND (
                  o.channel_id IS NULL
                  OR NOT EXISTS (
                      SELECT 1 FROM channels c
                      WHERE c.id = o.channel_id
                        AND c.external_id = (o.customer_notes::jsonb->>'channel_id_relbase')
                  )
              )
        """)
        orders_wrong_channel = cursor.fetchall()

        for order_id, external_id, current_channel_id, channel_id_relbase in orders_wrong_channel:
            if not channel_id_relbase:
                continue

            # Find the correct channel
            cursor.execute("""
                SELECT id FROM channels
                WHERE external_id = %s AND source = 'relbase'
            """, (str(channel_id_relbase),))
            channel_result = cursor.fetchone()

            if channel_result:
                correct_channel_id = channel_result[0]
                if correct_channel_id != current_channel_id:
                    cursor.execute("UPDATE orders SET channel_id = %s WHERE id = %s", (correct_channel_id, order_id))
                    channels_fixed += 1
                    logger.info(f"Cleanup: Fixed channel for order {external_id} ({current_channel_id} -> {correct_channel_id})")

        return customers_fixed, channels_fixed

    # =========================================================================
    # MercadoLibre API Methods
    # =========================================================================

    def _get_ml_credentials(self) -> tuple:
        """
        Get ML credentials, preferring database tokens over env vars.
        Auto-refreshes token if expired.

        Returns:
            Tuple of (access_token, refresh_token) or (None, None) if not configured
        """
        conn = get_db_connection_with_retry()
        cursor = conn.cursor()

        try:
            # Get token from database (now uses api_credentials instead of ml_tokens)
            cursor.execute("""
                SELECT access_token, refresh_token, token_expires_at
                FROM api_credentials
                WHERE service_name = 'mercadolibre'
                  AND access_token IS NOT NULL
            """)
            row = cursor.fetchone()

            if row:
                access_token, refresh_token, expires_at = row

                # Check if token is expired or will expire in next 30 minutes
                if expires_at:
                    cursor.execute("SELECT NOW() + INTERVAL '30 minutes' > %s", (expires_at,))
                    is_expired = cursor.fetchone()[0]
                else:
                    is_expired = True  # No expiry set, try to refresh

                if is_expired:
                    logger.info("ML token expired or expiring soon, refreshing...")
                    new_access, new_refresh = self._refresh_ml_token(refresh_token)
                    if new_access:
                        return new_access, new_refresh
                    else:
                        logger.warning("Token refresh failed, using existing token")
                        return access_token, refresh_token
                else:
                    return access_token, refresh_token
            else:
                # No token in DB, try env vars
                logger.info("No ML token in database, using environment variables")
                return self.ml_access_token, None

        except Exception as e:
            logger.error(f"Error getting ML credentials: {e}")
            return self.ml_access_token, None
        finally:
            cursor.close()
            conn.close()

    def _refresh_ml_token(self, refresh_token: str) -> tuple:
        """
        Refresh ML access token using refresh token.
        Stores new tokens in database.

        Returns:
            Tuple of (new_access_token, new_refresh_token) or (None, None) on failure
        """
        ml_app_id = os.getenv('MERCADOLIBRE_APP_ID') or os.getenv('ML_APP_ID')
        ml_secret = os.getenv('MERCADOLIBRE_SECRET') or os.getenv('ML_SECRET')

        if not all([ml_app_id, ml_secret, refresh_token]):
            logger.error("Missing ML credentials for token refresh")
            return None, None

        try:
            response = requests.post(
                "https://api.mercadolibre.com/oauth/token",
                data={
                    'grant_type': 'refresh_token',
                    'client_id': ml_app_id,
                    'client_secret': ml_secret,
                    'refresh_token': refresh_token
                },
                timeout=30
            )
            response.raise_for_status()

            token_data = response.json()
            new_access = token_data['access_token']
            new_refresh = token_data.get('refresh_token', refresh_token)

            # Store in database (uses api_credentials instead of ml_tokens)
            conn = get_db_connection_with_retry()
            cursor = conn.cursor()
            try:
                cursor.execute("""
                    INSERT INTO api_credentials (service_name, access_token, refresh_token, token_expires_at)
                    VALUES ('mercadolibre', %s, %s, NOW() + INTERVAL '6 hours')
                    ON CONFLICT (service_name)
                    DO UPDATE SET
                        access_token = EXCLUDED.access_token,
                        refresh_token = EXCLUDED.refresh_token,
                        token_expires_at = EXCLUDED.token_expires_at,
                        updated_at = NOW()
                """, (new_access, new_refresh))
                conn.commit()
                logger.info("✅ ML token refreshed and stored in api_credentials")
            finally:
                cursor.close()
                conn.close()

            return new_access, new_refresh

        except Exception as e:
            logger.error(f"Failed to refresh ML token: {e}")
            return None, None

    async def _fetch_ml_listings(self) -> List[Dict]:
        """Fetch active listings from MercadoLibre (with pagination)"""
        # Get fresh token (auto-refreshes if expired)
        access_token, _ = self._get_ml_credentials()

        if not access_token or not self.ml_seller_id:
            logger.warning("MercadoLibre credentials not configured")
            return []

        base_url = "https://api.mercadolibre.com"
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Accept': 'application/json'
        }

        async with httpx.AsyncClient() as client:
            try:
                # Collect all item IDs with pagination
                all_item_ids = []
                offset = 0
                limit = 50  # ML API default page size

                # First request to get total count
                response = await client.get(
                    f"{base_url}/users/{self.ml_seller_id}/items/search",
                    headers=headers,
                    params={'status': 'active', 'offset': 0, 'limit': limit},
                    timeout=30.0
                )
                response.raise_for_status()
                data = response.json()

                total_items = data.get('paging', {}).get('total', 0)
                all_item_ids.extend(data.get('results', []))
                logger.info(f"MercadoLibre: {total_items} total active listings")

                # Fetch remaining pages
                while len(all_item_ids) < total_items:
                    offset += limit
                    response = await client.get(
                        f"{base_url}/users/{self.ml_seller_id}/items/search",
                        headers=headers,
                        params={'status': 'active', 'offset': offset, 'limit': limit},
                        timeout=30.0
                    )
                    response.raise_for_status()
                    page_data = response.json()
                    page_ids = page_data.get('results', [])
                    if not page_ids:
                        break
                    all_item_ids.extend(page_ids)
                    logger.info(f"  Fetched page {offset // limit + 1}: {len(all_item_ids)}/{total_items} IDs")

                logger.info(f"Fetching details for {len(all_item_ids)} MercadoLibre listings...")

                # Get details for each item
                listings = []
                for i, item_id in enumerate(all_item_ids):
                    item_response = await client.get(
                        f"{base_url}/items/{item_id}",
                        headers=headers,
                        timeout=30.0
                    )
                    if item_response.status_code == 200:
                        item_data = item_response.json()

                        # Extract SKU from attributes (SELLER_SKU field)
                        sku = None
                        for attr in item_data.get('attributes', []):
                            if attr.get('id') == 'SELLER_SKU':
                                sku = attr.get('value_name')
                                break

                        # Fallback to seller_custom_field if no SELLER_SKU attribute
                        if not sku:
                            sku = item_data.get('seller_custom_field', '')

                        listings.append({
                            'id': item_data.get('id'),
                            'title': item_data.get('title'),
                            'sku': sku,
                            'available_quantity': item_data.get('available_quantity', 0),
                            'status': item_data.get('status')
                        })

                    # Log progress every 50 items
                    if (i + 1) % 50 == 0:
                        logger.info(f"  Processed {i + 1}/{len(all_item_ids)} item details")

                logger.info(f"Fetched {len(listings)} ML listings with SKUs")
                return listings

            except Exception as e:
                logger.error(f"Error fetching ML listings: {e}")
                return []

    # =========================================================================
    # Sales Sync Logic
    # =========================================================================

    def sync_sales_from_relbase(
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
        SYNC_TIMEOUT_SECONDS = 300  # 5 min max for sales sync
        errors = []
        orders_created = 0
        orders_updated = 0
        order_items_created = 0

        # === VALIDATE CREDENTIALS ===
        if not self.relbase_company_token or not self.relbase_user_token:
            error_msg = "RELBASE_COMPANY_TOKEN or RELBASE_USER_TOKEN not configured"
            logger.error(f"Sync failed: {error_msg}")
            return SalesSyncResult(
                success=False,
                message=error_msg,
                orders_created=0,
                orders_updated=0,
                order_items_created=0,
                errors=[error_msg],
                date_range={'from': 'N/A', 'to': 'N/A'},
                duration_seconds=0,
                customers_fixed=0,
                channels_fixed=0
            )

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

            # Pre-fetch all channels from RelBase API for efficient lookup
            # This allows us to create missing channels on-demand
            relbase_channels_cache = {}
            try:
                relbase_channels = self._fetch_relbase_channels()
                for ch in relbase_channels:
                    relbase_channels_cache[ch['id']] = ch.get('name', f'Canal {ch["id"]}')
                logger.info(f"Cached {len(relbase_channels_cache)} channels from RelBase API")
            except Exception as e:
                logger.warning(f"Could not pre-fetch RelBase channels: {e}")

            # Fetch DTEs from RelBase
            total_dtes = 0
            # 33=Factura, 39=Boleta, 43=Liquidación Factura
            document_types = [33, 39, 43]
            DTE_TYPE_MAP = {33: 'factura', 39: 'boleta', 43: 'liquidacion_factura'}
            MAX_PAGES = 100  # Safety limit to prevent infinite pagination

            for doc_type in document_types:
                page = 1
                logger.info(f"Fetching document type {doc_type}...")

                while page <= MAX_PAGES:
                    dte_response = self._fetch_relbase_dtes(date_from, date_to, page, doc_type)

                    if dte_response is None:
                        if page == 1:
                            logger.info(f"No DTEs available for type={doc_type} (API returned error/404)")
                        else:
                            errors.append(f"Failed to fetch DTEs page {page} (type={doc_type})")
                        break  # stop this doc_type on API error

                    dtes = dte_response.get('data', {}).get('dtes', [])

                    if not dtes:
                        break

                    total_dtes += len(dtes)

                    for dte in dtes:
                        try:
                            dte_id = dte.get('id')

                            # SAVEPOINT per DTE so one failure doesn't poison the transaction
                            cursor.execute(f"SAVEPOINT sp_dte_{int(dte_id)}")

                            # Check if order exists
                            cursor.execute("""
                                SELECT id FROM orders
                                WHERE external_id = %s AND source = 'relbase'
                            """, (str(dte_id),))

                            existing = cursor.fetchone()

                            if existing:
                                # Update invoice_status if changed in RelBase
                                rb_status = dte.get('sii_status')
                                if rb_status:
                                    cursor.execute("""
                                        UPDATE orders SET invoice_status = %s
                                        WHERE id = %s AND invoice_status != %s
                                    """, (rb_status, existing[0], rb_status))
                                orders_updated += 1
                                cursor.execute(f"RELEASE SAVEPOINT sp_dte_{int(dte_id)}")
                                continue

                            # Fetch DTE details for products
                            dte_detail = self._fetch_relbase_dte_detail(dte_id)
                            time.sleep(self.rate_limit_delay)  # Rate limiting

                            if not dte_detail:
                                errors.append(f"DTE_SKIPPED: type={doc_type} id={dte_id} folio={dte.get('folio')}")
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
                            # Logic: 1) Check DB, 2) Fetch from RelBase API, 3) Use assigned_channel_id
                            channel_id = None  # Default to NULL (Sin Mapear)
                            if channel_id_relbase:
                                # Step 1: Check if channel exists in our database
                                cursor.execute("""
                                    SELECT id FROM channels
                                    WHERE external_id = %s AND source = 'relbase'
                                """, (str(channel_id_relbase),))
                                channel_result = cursor.fetchone()

                                if channel_result:
                                    channel_id = channel_result[0]
                                else:
                                    # Step 2: Channel not in DB - check RelBase API cache and create
                                    channel_name = relbase_channels_cache.get(channel_id_relbase)
                                    if channel_name:
                                        # Create the channel in our database
                                        channel_code = channel_name.lower().replace(' ', '_').replace('-', '_')
                                        channel_code = ''.join(c for c in channel_code if c.isalnum() or c == '_')

                                        cursor.execute("""
                                            INSERT INTO channels (code, name, external_id, source, is_active, created_at)
                                            VALUES (%s, %s, %s, 'relbase', true, NOW())
                                            ON CONFLICT (code) DO UPDATE SET
                                                external_id = EXCLUDED.external_id,
                                                name = EXCLUDED.name,
                                                source = EXCLUDED.source,
                                                updated_at = NOW()
                                            RETURNING id
                                        """, (channel_code, channel_name, str(channel_id_relbase)))
                                        channel_id = cursor.fetchone()[0]
                                        logger.info(f"Created new channel from RelBase: {channel_name} (ID: {channel_id}, external: {channel_id_relbase})")
                                    else:
                                        # Step 3: Channel not found in RelBase API either - use NULL
                                        logger.warning(f"Channel {channel_id_relbase} not found in RelBase API - order will have NULL channel")

                            # Step 4: If no channel_id yet and customer has assigned channel, use it
                            # assigned_channel_id stores RelBase external ID, resolve to internal id via channels table
                            if channel_id is None and customer_id_relbase:
                                cursor.execute("""
                                    SELECT ch.id
                                    FROM customers cust
                                    JOIN channels ch ON ch.external_id = cust.assigned_channel_id::text
                                                    AND ch.source = 'relbase'
                                    WHERE cust.external_id = %s AND cust.source = 'relbase'
                                      AND cust.assigned_channel_id IS NOT NULL
                                """, (str(customer_id_relbase),))
                                assigned_result = cursor.fetchone()
                                if assigned_result:
                                    channel_id = assigned_result[0]
                                    logger.info(f"Applied assigned channel for customer {customer_id_relbase} (resolved channel_id={channel_id})")

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
                                    # Add small delay to prevent rate limiting when creating many new customers
                                    time.sleep(0.15)  # 150ms delay between customer API calls

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
                                        else:
                                            # API returned None (404 or failed after retries)
                                            logger.error(f"CUSTOMER_MISSING: Could not fetch customer {customer_id_relbase} from Relbase API for DTE {dte_id}")
                                    except Exception as e:
                                        logger.error(f"CUSTOMER_CREATE_FAILED: Could not create customer {customer_id_relbase} for DTE {dte_id}: {e}")

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
                                DTE_TYPE_MAP.get(dte_data.get('type_document'), 'boleta'),
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
                            invoice_type = dte_data.get('type_document')  # 33=Factura, 39=Boleta, 43=Liquidación

                            if invoice_type == 39 and products:
                                # Boleta: RelBase product prices are GROSS but amount_neto
                                # includes per-item discounts not visible in product.price.
                                # Proportionally allocate order-level net across items by
                                # their gross weight so SUM(item.subtotal) = orders.subtotal.
                                gross_items = []
                                gross_total = 0.0
                                for product in products:
                                    qty = float(product.get('quantity', 0))
                                    price_gross = float(product.get('price', 0))
                                    line_gross = qty * price_gross
                                    gross_total += line_gross
                                    gross_items.append((product, qty, price_gross, line_gross))

                                for product, qty, price_gross, line_gross in gross_items:
                                    if gross_total > 0 and qty > 0:
                                        share = line_gross / gross_total
                                        item_net = round(net * share, 2)
                                        unit_price_net = round(item_net / qty, 2)
                                    else:
                                        unit_price_net = 0.0
                                        item_net = 0.0

                                    cursor.execute("""
                                        INSERT INTO order_items
                                        (order_id, product_id, product_sku, product_name,
                                         quantity, unit_price, subtotal, total, created_at)
                                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, NOW())
                                    """, (
                                        order_id,
                                        None,
                                        product.get('code', ''),
                                        product.get('name', ''),
                                        qty,
                                        unit_price_net,
                                        item_net,
                                        item_net
                                    ))
                                    order_items_created += 1
                            else:
                                # Factura: prices are already net, no conversion needed
                                for product in products:
                                    product_code = product.get('code', '')
                                    product_name = product.get('name', '')
                                    quantity = float(product.get('quantity', 0))
                                    price = float(product.get('price', 0))
                                    subtotal_item = quantity * price

                                    cursor.execute("""
                                        INSERT INTO order_items
                                        (order_id, product_id, product_sku, product_name,
                                         quantity, unit_price, subtotal, total, created_at)
                                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, NOW())
                                    """, (
                                        order_id,
                                        None,
                                        product_code,
                                        product_name,
                                        quantity,
                                        price,
                                        subtotal_item,
                                        subtotal_item
                                    ))
                                    order_items_created += 1

                            # Release savepoint on success
                            cursor.execute(f"RELEASE SAVEPOINT sp_dte_{int(dte_id)}")

                        except Exception as e:
                            # Rollback to savepoint so the transaction stays usable
                            try:
                                cursor.execute(f"ROLLBACK TO SAVEPOINT sp_dte_{int(dte_id)}")
                            except Exception:
                                pass
                            errors.append(f"Error processing DTE {dte.get('id')}: {str(e)}")
                            logger.error(f"Error processing DTE {dte.get('id')}: {e}")
                            continue

                    # Check for more pages
                    # NOTE: RelBase API returns pagination info in 'meta', not 'data.pagination'
                    pagination = dte_response.get('meta', {})
                    if page >= pagination.get('total_pages', 1):
                        break

                    # Check overall timeout
                    if time.time() - start_time > SYNC_TIMEOUT_SECONDS:
                        logger.error(f"Sales sync timed out after {SYNC_TIMEOUT_SECONDS}s on doc_type={doc_type}")
                        errors.append(f"Sales sync timed out after {SYNC_TIMEOUT_SECONDS}s")
                        break

                    page += 1
                    time.sleep(self.rate_limit_delay)  # Rate limiting between pages

                else:
                    # while loop exhausted MAX_PAGES without break
                    logger.error(f"Hit MAX_PAGES={MAX_PAGES} for doc_type={doc_type} — possible infinite pagination")
                    errors.append(f"Pagination limit reached for doc_type={doc_type}")

            # === CHECK STALE sent_sii ORDERS ===
            # These may have changed to accepted/cancel in RelBase since they
            # were first synced, but fall outside the current date range.
            try:
                cursor.execute("""
                    SELECT id, external_id FROM orders
                    WHERE source = 'relbase' AND invoice_status = 'sent_sii'
                """)
                sent_sii_orders = cursor.fetchall()
                sent_sii_updated = 0
                for order_row in sent_sii_orders:
                    order_id_local, ext_id = order_row
                    try:
                        dte_list_resp = requests.get(
                            f"{self.relbase_base_url}/api/v1/dtes/{ext_id}",
                            headers=self._get_relbase_headers(),
                            timeout=15
                        )
                        if dte_list_resp.status_code == 200:
                            current_status = dte_list_resp.json().get('data', {}).get('sii_status')
                            if current_status and current_status != 'sent_sii':
                                cursor.execute("""
                                    UPDATE orders SET invoice_status = %s, updated_at = NOW()
                                    WHERE id = %s
                                """, (current_status, order_id_local))
                                sent_sii_updated += 1
                                logger.info(f"SENT_SII_RESOLVED: order {ext_id} -> {current_status}")
                        time.sleep(0.2)
                    except Exception as e:
                        logger.warning(f"Could not check sent_sii order {ext_id}: {e}")
                if sent_sii_orders:
                    logger.info(f"Checked {len(sent_sii_orders)} sent_sii orders, {sent_sii_updated} status updated")
            except Exception as e:
                logger.warning(f"sent_sii check failed: {e}")

            # === CLEANUP: Fix any orders with missing customer/channel data ===
            customers_fixed, channels_fixed = self._fix_missing_order_references(cursor)
            if customers_fixed > 0 or channels_fixed > 0:
                logger.info(f"Cleanup: Fixed {customers_fixed} missing customers, {channels_fixed} missing channels")

            # Commit changes
            conn.commit()

            # Refresh materialized view for sales analytics (if orders were created)
            if orders_created > 0:
                try:
                    logger.info("Refreshing sales_facts_mv materialized view (CONCURRENTLY)...")
                    cursor.execute("REFRESH MATERIALIZED VIEW CONCURRENTLY sales_facts_mv")
                    conn.commit()
                    logger.info("Materialized view refreshed successfully (no read locks)")
                except Exception as mv_error:
                    conn.rollback()  # Clean aborted transaction before continuing
                    logger.warning(f"CONCURRENTLY refresh failed: {mv_error}, trying non-concurrent...")
                    try:
                        cursor.execute("REFRESH MATERIALIZED VIEW sales_facts_mv")
                        conn.commit()
                        logger.info("Materialized view refreshed (non-concurrent fallback)")
                    except Exception as mv_error2:
                        conn.rollback()
                        logger.warning(f"Could not refresh materialized view: {mv_error2}")

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
                duration_seconds=round(duration, 2),
                customers_fixed=customers_fixed,
                channels_fixed=channels_fixed
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
                duration_seconds=round(time.time() - start_time, 2),
                customers_fixed=0,  # No cleanup on error
                channels_fixed=0
            )

        finally:
            cursor.close()
            conn.close()

    # =========================================================================
    # Inventory Sync Logic
    # =========================================================================

    def sync_inventory(self) -> InventorySyncResult:
        """
        Sync inventory from RelBase and MercadoLibre

        Logic:
        1. Fetch warehouses from RelBase and sync to database
        2. For products with external_id, fetch lot/serial stock from RelBase
        3. Fetch active listings from MercadoLibre and update stock

        Note: No product limit - syncs ALL products. Runs in background mode
        so long sync times are acceptable. Products without lot data return
        quickly (404/empty), so actual time scales with products WITH data.

        Returns:
            InventorySyncResult with statistics
        """
        start_time = time.time()
        INVENTORY_TIMEOUT_SECONDS = 600  # 10 min max for inventory sync
        errors = []
        warehouses_synced = 0
        relbase_products_updated = 0
        ml_products_updated = 0
        klog_products_updated = 0

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

                # Upsert warehouse using external_id as the key (Relbase ID is the true identifier)
                # This handles cases where Relbase renames a warehouse (same ID, new name/code)
                cursor.execute("""
                    INSERT INTO warehouses (code, name, location, external_id, source, update_method, is_active)
                    VALUES (%s, %s, %s, %s, 'relbase', 'api', %s)
                    ON CONFLICT (external_id, source) WHERE external_id IS NOT NULL DO UPDATE SET
                        code = EXCLUDED.code,
                        name = EXCLUDED.name,
                        location = EXCLUDED.location,
                        is_active = EXCLUDED.is_active,
                        updated_at = NOW()
                """, (code, name, address, str(warehouse_id), enabled))

                warehouses_synced += 1

            conn.commit()
            logger.info(f"Synced {warehouses_synced} warehouses")

            # ================================================================
            # Phase 2: Sync Stock from RelBase (ACTIVE products only)
            # ================================================================
            # IMPORTANT: Fetch active products from RelBase API, NOT local DB.
            # The /api/v1/productos endpoint returns ONLY active products,
            # avoiding 401/403 errors for legacy/inactive products (e.g., ANU- prefix).
            # See: _fetch_relbase_active_products() docstring for details.
            #
            # SYNC STRATEGY: Full sync with stale deletion
            # 1. Record sync start time
            # 2. Upsert all current stock from RelBase (updates last_updated)
            # 3. Delete any RelBase stock not updated during this sync (stale)
            # This ensures our DB matches RelBase exactly.
            # ================================================================
            logger.info("Phase 2: Fetching active products from RelBase API...")

            # Record sync start time for stale detection
            sync_start_time = datetime.now()

            # Fetch active products directly from RelBase (the correct approach)
            relbase_products = self._fetch_relbase_active_products()

            if relbase_products is None:
                logger.error("Failed to fetch active products from RelBase API - skipping stock sync")
                errors.append("Failed to fetch active products from RelBase API")
            elif not relbase_products:
                logger.warning("No active products returned from RelBase API - skipping stock sync")
            else:
                # Get warehouses from DB
                # IMPORTANT: Exclude KLOG warehouse - it's synced directly via KLOG API (Phase 4)
                # This is a POKA-YOKE to prevent duplicate/conflicting data from RelBase
                # NOTE: Use ILIKE pattern because warehouse code is sanitized from RelBase name
                # (e.g., "KLOG Bodega 7 Lampa" -> "klog_bodega__lampa")
                cursor.execute("""
                    SELECT id, external_id, code
                    FROM warehouses
                    WHERE source = 'relbase' AND is_active = true
                    AND code NOT ILIKE '%klog%'  -- KLOG synced via direct API in Phase 4
                """)
                db_warehouses = cursor.fetchall()
                logger.info(f"RelBase warehouses (excluding KLOG): {[w[2] for w in db_warehouses]}")

                # Build a map of external_id -> db_id for products
                # We need to look up local product IDs for warehouse_stock foreign key
                cursor.execute("""
                    SELECT id, external_id
                    FROM products
                    WHERE external_id IS NOT NULL AND source = 'relbase'
                """)
                product_db_map = {str(row[1]): row[0] for row in cursor.fetchall()}

                # For each product-warehouse combination, fetch stock
                logger.info(f"Syncing stock for {len(relbase_products)} active products across {len(db_warehouses)} warehouses...")

                # Track auth errors - if we get too many 401s, skip lot sync entirely
                auth_error_count = 0
                auth_error_threshold = 5  # Skip lot sync after 5 consecutive auth errors
                skip_lot_sync = False

                for product in relbase_products:
                    if skip_lot_sync:
                        break  # Stop trying if auth is failing

                    # Check overall inventory timeout
                    if time.time() - start_time > INVENTORY_TIMEOUT_SECONDS:
                        logger.error(f"Inventory sync timed out after {INVENTORY_TIMEOUT_SECONDS}s during RelBase stock sync")
                        errors.append(f"Inventory sync timed out after {INVENTORY_TIMEOUT_SECONDS}s")
                        break

                    product_external_id = product.get('id')
                    product_sku = product.get('sku', '')
                    product_name = product.get('name', '')
                    product_id_db = product_db_map.get(str(product_external_id))

                    # Skip if product doesn't exist in local DB
                    # (it's in RelBase but hasn't been synced to our products table yet)
                    if not product_id_db:
                        continue

                    for warehouse in db_warehouses:
                        if skip_lot_sync:
                            break

                        warehouse_id_db, warehouse_external_id, warehouse_code = warehouse

                        try:
                            lots = self._fetch_relbase_lot_serial(
                                int(product_external_id),
                                int(warehouse_external_id)
                            )

                            # Check for auth error marker
                            if lots and len(lots) == 1 and lots[0].get('_auth_error'):
                                auth_error_count += 1
                                if auth_error_count >= auth_error_threshold:
                                    logger.warning(f"Lot/serial API returning 401 Unauthorized - skipping lot sync (permissions issue)")
                                    errors.append("RelBase lot/serial API returned 401 Unauthorized - check API permissions")
                                    skip_lot_sync = True
                                continue

                            # Reset auth error count on success
                            auth_error_count = 0

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

                    # Commit after each product to prevent connection timeout
                    conn.commit()

                logger.info(f"Updated {relbase_products_updated} stock records from RelBase")

                # ============================================================
                # Phase 2b: Delete stale RelBase stock entries
                # ============================================================
                # Any warehouse_stock entry for RelBase products that wasn't
                # updated during this sync is stale and should be deleted.
                # This handles: lots sold out, products deactivated, lot numbers
                # that changed format, etc.
                # ============================================================
                logger.info("Phase 2b: Cleaning up stale RelBase stock entries...")

                # Get all RelBase warehouse IDs
                relbase_warehouse_ids = [w[0] for w in db_warehouses]

                if relbase_warehouse_ids:
                    # Delete stock entries that:
                    # 1. Are in RelBase warehouses
                    # 2. Were last updated BEFORE this sync started
                    # 3. Were updated by sync_api (not manually entered)
                    cursor.execute("""
                        DELETE FROM warehouse_stock
                        WHERE warehouse_id = ANY(%s)
                          AND last_updated < %s
                          AND updated_by = 'sync_api'
                        RETURNING id, lot_number
                    """, (relbase_warehouse_ids, sync_start_time))

                    deleted_entries = cursor.fetchall()
                    stale_count = len(deleted_entries)

                    if stale_count > 0:
                        logger.info(f"Deleted {stale_count} stale stock entries from RelBase warehouses")
                    else:
                        logger.info("No stale stock entries found")

                    conn.commit()

            # ================================================================
            # Phase 3: Sync Stock from MercadoLibre
            # ================================================================
            logger.info("Phase 3: Syncing stock from MercadoLibre...")

            try:
                ml_listings = asyncio.run(self._fetch_ml_listings())

                # Get the existing Mercado Libre warehouse (from RelBase sync)
                # Use 'mercado_libre' which has source='relbase' and external_id=2013
                cursor.execute("""
                    SELECT id FROM warehouses
                    WHERE code = 'mercado_libre' AND source = 'relbase' AND is_active = true
                """)
                result = cursor.fetchone()

                if result:
                    ml_warehouse_id = result[0]
                else:
                    # Fallback: Create warehouse with source='relbase' so it appears in inventory
                    cursor.execute("""
                        INSERT INTO warehouses (code, name, source, update_method, is_active)
                        VALUES ('mercado_libre', 'Mercado Libre', 'relbase', 'api', true)
                        ON CONFLICT (code) DO UPDATE SET
                            source = 'relbase',
                            is_active = true,
                            updated_at = NOW()
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

            # ================================================================
            # Phase 4: Sync Stock from KLOG API (Direct) with Lot/Expiration
            # ================================================================
            # POKA-YOKE: KLOG warehouse is excluded from RelBase sync (Phase 2)
            # to prevent duplicate/conflicting data. This phase syncs directly
            # from KLOG API which provides real-time inventory data.
            #
            # LOT-LEVEL SYNC (updated 2026-02-03):
            # - Uses consultaWmsCajaAlmacenadasWS endpoint for box-level data
            # - Captures lot numbers (lote) and expiration dates (fechaVencimiento)
            # - Enables FEFO (First Expired, First Out) picking
            #
            # CONVERSION LOGIC:
            # - Master box SKUs (sku_master) are converted to display units (sku)
            #   using units_per_master_box conversion factor
            # - Example: BACM_C02810 (master) × 28 = BACM_U20010 (display x5)
            # ================================================================
            logger.info("Phase 4: Syncing stock from KLOG API (lot-level)...")

            try:
                from app.connectors.klog_connector import KLOGConnector

                # Check if KLOG credentials are configured
                klog_usuario = os.getenv('KLOG_USUARIO')
                klog_password = os.getenv('KLOG_PASSWORD')

                if not klog_usuario or not klog_password:
                    logger.warning("KLOG credentials not configured - skipping KLOG sync")
                    errors.append("KLOG_USUARIO/KLOG_PASSWORD not configured")
                else:
                    klog_connector = KLOGConnector(klog_usuario, klog_password)

                    # Get KLOG warehouse from DB
                    cursor.execute("""
                        SELECT id, code FROM warehouses
                        WHERE (code ILIKE '%klog%' OR name ILIKE '%klog%')
                        AND is_active = true
                        LIMIT 1
                    """)
                    klog_warehouse_result = cursor.fetchone()

                    if not klog_warehouse_result:
                        logger.warning("KLOG warehouse not found in database - skipping KLOG sync")
                        errors.append("KLOG warehouse not found in database")
                    else:
                        klog_warehouse_id = klog_warehouse_result[0]
                        klog_warehouse_code = klog_warehouse_result[1]
                        logger.info(f"Found KLOG warehouse: id={klog_warehouse_id}, code='{klog_warehouse_code}'")

                        # --------------------------------------------------------
                        # Step 1: Build SKU mappings from product_catalog
                        # --------------------------------------------------------
                        cursor.execute("""
                            SELECT DISTINCT sku FROM product_catalog
                            WHERE sku IS NOT NULL
                        """)
                        base_skus = set(r[0] for r in cursor.fetchall())

                        # Build master_to_base mapping: sku_master -> (sku, units_per_master_box)
                        cursor.execute("""
                            SELECT sku_master, sku, units_per_master_box
                            FROM product_catalog
                            WHERE sku_master IS NOT NULL AND units_per_master_box IS NOT NULL
                        """)
                        master_to_base = {}
                        for sku_master, sku, units in cursor.fetchall():
                            master_to_base[sku_master] = (sku, units)

                        # Get product_id mapping for base SKUs
                        cursor.execute("""
                            SELECT sku, id FROM products
                            WHERE source IN ('relbase', 'CATALOG')
                        """)
                        sku_to_product_id = {r[0]: r[1] for r in cursor.fetchall()}

                        # Record sync start time for stale deletion
                        klog_sync_start = datetime.utcnow()

                        # --------------------------------------------------------
                        # Step 2: Fetch LOT-LEVEL inventory from KLOG API
                        # --------------------------------------------------------
                        lot_inventory = asyncio.run(klog_connector.get_inventory_with_lots(
                            empresa="GRANA",
                            include_zero_stock=False
                        ))

                        logger.info(f"KLOG returned {len(lot_inventory)} lot records")

                        # --------------------------------------------------------
                        # Step 3: Convert and store lot-level inventory
                        # --------------------------------------------------------
                        # Key: (base_sku, lot_number, expiration_date) -> quantity
                        lot_aggregated = {}

                        for lot_record in lot_inventory:
                            sku = lot_record.get('sku')
                            lot_number = lot_record.get('lot_number')
                            exp_date = lot_record.get('expiration_date')
                            units = float(lot_record.get('total_units', 0))

                            if units <= 0:
                                continue

                            # Convert master box to base units
                            if sku in master_to_base:
                                base_sku, units_per_box = master_to_base[sku]
                                converted_units = units * units_per_box
                                key = (base_sku, lot_number, exp_date)
                                lot_aggregated[key] = lot_aggregated.get(key, 0) + converted_units
                            elif sku in base_skus:
                                key = (sku, lot_number, exp_date)
                                lot_aggregated[key] = lot_aggregated.get(key, 0) + units

                        logger.info(f"KLOG aggregated to {len(lot_aggregated)} (sku, lot, exp) combinations")

                        # --------------------------------------------------------
                        # Step 4: Upsert lot-level inventory to warehouse_stock
                        # --------------------------------------------------------
                        unmapped_skus = set()
                        for (base_sku, lot_number, exp_date), quantity in lot_aggregated.items():
                            product_id = sku_to_product_id.get(base_sku)

                            if not product_id:
                                unmapped_skus.add(base_sku)
                                continue

                            # Parse expiration date
                            expiration_date = None
                            if exp_date:
                                try:
                                    expiration_date = datetime.strptime(exp_date, '%Y-%m-%d').date()
                                except (ValueError, TypeError):
                                    pass

                            # Use lot_number or 'KLOG_NO_LOT' for items without lot
                            effective_lot = lot_number or 'KLOG_NO_LOT'

                            cursor.execute("""
                                INSERT INTO warehouse_stock (
                                    product_id, warehouse_id, quantity, lot_number,
                                    expiration_date, last_updated, updated_by
                                )
                                VALUES (%s, %s, %s, %s, %s, clock_timestamp(), 'klog_api')
                                ON CONFLICT (product_id, warehouse_id, lot_number)
                                DO UPDATE SET
                                    quantity = EXCLUDED.quantity,
                                    expiration_date = EXCLUDED.expiration_date,
                                    last_updated = clock_timestamp(),
                                    updated_by = 'klog_api'
                            """, (product_id, klog_warehouse_id, int(quantity), effective_lot, expiration_date))

                            klog_products_updated += 1

                        conn.commit()

                        if unmapped_skus:
                            logger.info(f"KLOG: {len(unmapped_skus)} SKUs not in products table: {list(unmapped_skus)[:10]}")

                        # Delete stale KLOG entries (items no longer in KLOG)
                        cursor.execute("""
                            DELETE FROM warehouse_stock
                            WHERE warehouse_id = %s
                              AND last_updated < %s
                              AND updated_by = 'klog_api'
                            RETURNING id
                        """, (klog_warehouse_id, klog_sync_start))
                        stale_klog = cursor.fetchall()
                        if stale_klog:
                            logger.info(f"KLOG: Deleted {len(stale_klog)} stale entries")
                        conn.commit()

                        # Log expiring inventory summary
                        expiring_soon = asyncio.run(klog_connector.get_expiring_inventory(days_threshold=90))
                        if expiring_soon:
                            logger.warning(f"KLOG: {len(expiring_soon)} lots expiring within 90 days")

                        logger.info(f"KLOG sync: {klog_products_updated} lot records updated")

            except Exception as e:
                errors.append(f"KLOG sync error: {str(e)}")
                logger.error(f"KLOG sync error: {e}")
                import traceback
                traceback.print_exc()

            # Log sync
            cursor.execute("""
                INSERT INTO sync_logs
                (source, sync_type, status, records_processed, records_failed,
                 details, started_at, completed_at)
                VALUES ('multiple', 'inventory', %s, %s, %s, %s::jsonb, %s, NOW())
            """, (
                'success' if not errors else 'partial',
                warehouses_synced + relbase_products_updated + ml_products_updated + klog_products_updated,
                len(errors),
                json.dumps({
                    'warehouses_synced': warehouses_synced,
                    'relbase_products_updated': relbase_products_updated,
                    'ml_products_updated': ml_products_updated,
                    'klog_products_updated': klog_products_updated,
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
                klog_products_updated=klog_products_updated,
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
                klog_products_updated=klog_products_updated,
                errors=errors,
                duration_seconds=round(time.time() - start_time, 2)
            )

        finally:
            cursor.close()
            conn.close()

    # =========================================================================
    # Combined Sync (for background execution)
    # =========================================================================

    def run_full_sync(self, days_back: int = 3) -> Dict:
        """
        Run full sync (sales + inventory) - designed for background execution

        Args:
            days_back: Days to look back for sales sync

        Returns:
            Combined results dictionary
        """
        logger.info(f"Starting full sync (days_back={days_back})")

        sales_result = self.sync_sales_from_relbase(days_back=days_back)
        inventory_result = self.sync_inventory()

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
