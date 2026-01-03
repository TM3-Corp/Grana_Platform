"""
MercadoLibre API Connector
Handles all interactions with MercadoLibre REST API

Author: TM3
Date: 2025-10-04
Updated: 2026-01-03 - Added database-backed token persistence
"""
import os
from typing import Dict, List, Optional, Any
import httpx
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


class MercadoLibreConnector:
    """
    Connector for MercadoLibre REST API

    Handles:
    - OAuth token management and refresh (with database persistence)
    - Order retrieval
    - Product listings
    - Sales metrics

    Token Management:
    - Tokens are stored in the database (api_credentials table)
    - On 401, automatically refreshes and persists new tokens
    - Falls back to env vars if database tokens not available
    """

    def __init__(self, app_id: str = None, secret_key: str = None,
                 access_token: str = None, refresh_token: str = None, seller_id: str = None,
                 use_db_credentials: bool = True):
        """
        Initialize MercadoLibre connector

        Args:
            app_id: MercadoLibre app ID (optional if using DB credentials)
            secret_key: MercadoLibre secret key (optional if using DB credentials)
            access_token: OAuth access token (optional if using DB credentials)
            refresh_token: OAuth refresh token (optional if using DB credentials)
            seller_id: MercadoLibre seller ID (optional if using DB credentials)
            use_db_credentials: If True, load credentials from database (default: True)
        """
        self._credentials_service = None

        if use_db_credentials:
            try:
                from app.services.credentials_service import get_credentials_service
                self._credentials_service = get_credentials_service()
                creds = self._credentials_service.get_mercadolibre_credentials()

                self.app_id = creds.get('app_id') or app_id or os.getenv('ML_APP_ID')
                self.secret_key = creds.get('secret') or secret_key or os.getenv('ML_SECRET')
                self.access_token = creds.get('access_token') or access_token or os.getenv('ML_ACCESS_TOKEN')
                self.refresh_token = creds.get('refresh_token') or refresh_token or os.getenv('ML_REFRESH_TOKEN')
                self.seller_id = creds.get('seller_id') or seller_id or os.getenv('ML_SELLER_ID')

                logger.info("MercadoLibre credentials loaded from database")
            except Exception as e:
                logger.warning(f"Could not load ML credentials from database: {e}, falling back to env vars")
                self.app_id = app_id or os.getenv('ML_APP_ID')
                self.secret_key = secret_key or os.getenv('ML_SECRET')
                self.access_token = access_token or os.getenv('ML_ACCESS_TOKEN')
                self.refresh_token = refresh_token or os.getenv('ML_REFRESH_TOKEN')
                self.seller_id = seller_id or os.getenv('ML_SELLER_ID')
        else:
            self.app_id = app_id or os.getenv('ML_APP_ID')
            self.secret_key = secret_key or os.getenv('ML_SECRET')
            self.access_token = access_token or os.getenv('ML_ACCESS_TOKEN')
            self.refresh_token = refresh_token or os.getenv('ML_REFRESH_TOKEN')
            self.seller_id = seller_id or os.getenv('ML_SELLER_ID')

        if not all([self.app_id, self.secret_key, self.access_token, self.seller_id]):
            raise ValueError("MercadoLibre credentials not configured. Set ML_APP_ID, ML_SECRET, ML_ACCESS_TOKEN, and ML_SELLER_ID")

        self.base_url = "https://api.mercadolibre.com"
        self.api_calls = 0
        self.last_refresh = datetime.now()

        logger.info(f"MercadoLibre connector initialized for seller {self.seller_id}")

    async def _make_request(self, endpoint: str, params: Optional[Dict] = None, method: str = "GET") -> Dict:
        """
        Make authenticated request to MercadoLibre API

        Args:
            endpoint: API endpoint (e.g., '/users/123')
            params: Query parameters
            method: HTTP method (GET, POST)

        Returns:
            API response as dictionary
        """
        url = f"{self.base_url}{endpoint}"

        headers = {
            'Authorization': f'Bearer {self.access_token}',
            'Accept': 'application/json'
        }

        async with httpx.AsyncClient() as client:
            try:
                if method == "GET":
                    response = await client.get(url, headers=headers, params=params, timeout=30.0)
                elif method == "POST":
                    response = await client.post(url, headers=headers, json=params, timeout=30.0)
                else:
                    raise ValueError(f"Unsupported HTTP method: {method}")

                self.api_calls += 1

                # Handle token expiration
                if response.status_code == 401:
                    logger.warning("Token expired, attempting refresh...")
                    if await self.refresh_access_token():
                        # Retry with new token
                        headers['Authorization'] = f'Bearer {self.access_token}'
                        if method == "GET":
                            response = await client.get(url, headers=headers, params=params, timeout=30.0)
                        else:
                            response = await client.post(url, headers=headers, json=params, timeout=30.0)
                        self.api_calls += 1

                response.raise_for_status()
                return response.json()

            except httpx.HTTPStatusError as e:
                logger.error(f"API request failed: {e.response.status_code} - {e.response.text}")
                return {}
            except Exception as e:
                logger.error(f"API request error: {e}")
                return {}

    async def refresh_access_token(self) -> bool:
        """
        Refresh the OAuth access token using refresh token

        On success, persists the new tokens to the database for durability
        across container restarts.

        Returns:
            True if refresh successful, False otherwise
        """
        if not self.refresh_token:
            logger.error("No refresh token available")
            return False

        url = f"{self.base_url}/oauth/token"
        data = {
            'grant_type': 'refresh_token',
            'client_id': self.app_id,
            'client_secret': self.secret_key,
            'refresh_token': self.refresh_token
        }

        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(url, data=data, timeout=30.0)
                response.raise_for_status()

                token_data = response.json()
                new_access_token = token_data['access_token']
                new_refresh_token = token_data.get('refresh_token', self.refresh_token)
                expires_in = token_data.get('expires_in', 21600)  # Default 6 hours

                # Update in-memory tokens
                self.access_token = new_access_token
                self.refresh_token = new_refresh_token
                self.last_refresh = datetime.now()

                # Persist to database if credentials service is available
                if self._credentials_service:
                    try:
                        self._credentials_service.update_mercadolibre_tokens(
                            access_token=new_access_token,
                            refresh_token=new_refresh_token,
                            expires_in_seconds=expires_in
                        )
                        logger.info("Access token refreshed and persisted to database")
                    except Exception as db_error:
                        logger.warning(f"Token refreshed but failed to persist to database: {db_error}")
                else:
                    logger.warning("Token refreshed but credentials service not available - token not persisted")

                return True

            except Exception as e:
                logger.error(f"Token refresh failed: {e}")
                return False

    # ==================== CORE API METHODS ====================

    async def get_seller_info(self) -> Dict:
        """
        Get seller information

        Returns:
            Dictionary with seller details
        """
        try:
            seller_data = await self._make_request(f"/users/{self.seller_id}")

            if seller_data:
                return {
                    'id': seller_data.get('id'),
                    'nickname': seller_data.get('nickname'),
                    'registration_date': seller_data.get('registration_date'),
                    'country_id': seller_data.get('country_id'),
                    'city': seller_data.get('city', {}).get('name') if seller_data.get('city') else None,
                    'user_type': seller_data.get('user_type'),
                    'seller_reputation': seller_data.get('seller_reputation', {}),
                    'status': seller_data.get('status', {})
                }
            return {}

        except Exception as e:
            logger.error(f"Error fetching seller info: {e}")
            return {}

    async def get_recent_orders(self, days: int = 30) -> List[Dict]:
        """
        Get recent orders

        Args:
            days: Number of days to look back (default 30)

        Returns:
            List of order dictionaries
        """
        date_from = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%dT00:00:00.000-04:00')
        date_to = datetime.now().strftime('%Y-%m-%dT23:59:59.999-04:00')

        params = {
            'seller': self.seller_id,
            'order.date_created.from': date_from,
            'order.date_created.to': date_to,
            'sort': 'date_desc'
        }

        all_orders = []
        offset = 0
        limit = 50

        while True:
            params.update({'offset': offset, 'limit': limit})
            response = await self._make_request('/orders/search', params)

            if not response or 'results' not in response:
                break

            orders = response['results']
            if not orders:
                break

            all_orders.extend(orders)

            # Check for more pages
            if len(orders) < limit:
                break

            offset += limit

            # Safety limit
            if offset >= 1000:
                logger.warning("Reached 1000 orders limit")
                break

        logger.info(f"Retrieved {len(all_orders)} orders from last {days} days")
        return all_orders

    async def get_order_details(self, order_id: str) -> Dict:
        """
        Get detailed information for a specific order

        Args:
            order_id: MercadoLibre order ID

        Returns:
            Order details including items
        """
        response = await self._make_request(f'/orders/{order_id}')
        return response if response else {}

    async def get_product_details(self, item_id: str) -> Dict:
        """
        Get detailed product information

        Args:
            item_id: MercadoLibre item ID

        Returns:
            Product details dictionary
        """
        response = await self._make_request(f'/items/{item_id}')

        if not response:
            return {}

        return {
            'id': response.get('id'),
            'title': response.get('title'),
            'price': response.get('price'),
            'available_quantity': response.get('available_quantity'),
            'sold_quantity': response.get('sold_quantity'),
            'sku': response.get('seller_custom_field', ''),
            'category_id': response.get('category_id'),
            'status': response.get('status'),
            'listing_type_id': response.get('listing_type_id'),
            'permalink': response.get('permalink'),
            'pictures': [p['url'] for p in response.get('pictures', [])][:3]
        }

    async def get_active_listings(self) -> List[Dict]:
        """
        Get all active product listings

        Returns:
            List of active products
        """
        params = {'status': 'active'}

        response = await self._make_request(f'/users/{self.seller_id}/items/search', params)

        if not response or 'results' not in response:
            return []

        item_ids = response['results']

        # Get details for each listing (limit to 50 for performance)
        listings = []
        for item_id in item_ids[:50]:
            details = await self.get_product_details(item_id)
            if details:
                listings.append(details)

        logger.info(f"Retrieved {len(listings)} active listings")
        return listings

    async def get_sales_summary(self, days: int = 30) -> Dict:
        """
        Get comprehensive sales summary

        Args:
            days: Number of days to analyze

        Returns:
            Dictionary with complete sales analysis
        """
        logger.info(f"Generating sales summary for last {days} days...")

        # Get orders
        orders = await self.get_recent_orders(days)

        # Process orders
        total_revenue = 0
        total_items = 0
        products_sold = {}
        customers = set()

        for order in orders:
            # Sum revenue
            if order.get('total_amount'):
                total_revenue += order['total_amount']

            # Count items and products
            if order.get('order_items'):
                for item in order['order_items']:
                    total_items += item.get('quantity', 0)

                    # Track product sales
                    item_id = item['item']['id']
                    if item_id not in products_sold:
                        products_sold[item_id] = {
                            'title': item['item']['title'],
                            'quantity': 0,
                            'revenue': 0
                        }

                    products_sold[item_id]['quantity'] += item.get('quantity', 0)
                    products_sold[item_id]['revenue'] += (
                        item.get('unit_price', 0) * item.get('quantity', 0)
                    )

            # Track unique customers
            if order.get('buyer'):
                customers.add(order['buyer']['id'])

        # Get top products
        top_products = sorted(
            products_sold.items(),
            key=lambda x: x[1]['revenue'],
            reverse=True
        )[:10]

        summary = {
            'period_days': days,
            'total_orders': len(orders),
            'total_revenue': total_revenue,
            'total_items_sold': total_items,
            'unique_customers': len(customers),
            'average_order_value': total_revenue / len(orders) if orders else 0,
            'top_products': [
                {
                    'id': prod_id,
                    'title': data['title'],
                    'quantity_sold': data['quantity'],
                    'revenue': data['revenue']
                }
                for prod_id, data in top_products
            ],
            'currency': 'CLP',
            'generated_at': datetime.now().isoformat(),
            'api_calls_used': self.api_calls
        }

        logger.info(f"Sales summary generated: {summary['total_orders']} orders, "
                   f"${summary['total_revenue']:,.0f} {summary['currency']}")

        return summary
