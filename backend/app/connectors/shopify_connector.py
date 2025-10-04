"""
Shopify GraphQL Connector
Handles all interactions with Shopify API

Author: TM3
Date: 2025-10-03
"""
import os
from typing import Dict, List, Optional, Any
import httpx
from datetime import datetime
import json


class ShopifyConnector:
    """
    Connector for Shopify GraphQL API

    Handles:
    - Product sync
    - Customer sync
    - Order retrieval
    - Webhook verification
    """

    def __init__(self, shop_name: str = None, access_token: str = None):
        """
        Initialize Shopify connector

        Args:
            shop_name: Shopify store name (e.g., 'granafoods')
            access_token: Shopify Admin API access token
        """
        self.shop_name = shop_name or os.getenv('SHOPIFY_STORE_NAME')
        self.access_token = access_token or os.getenv('SHOPIFY_PASSWORD')

        if not self.shop_name or not self.access_token:
            raise ValueError("Shopify credentials not configured. Set SHOPIFY_STORE_NAME and SHOPIFY_PASSWORD")

        self.api_url = f"https://{self.shop_name}.myshopify.com/admin/api/2024-10/graphql.json"
        self.headers = {
            'Content-Type': 'application/json',
            'X-Shopify-Access-Token': self.access_token
        }

    async def _execute_query(self, query: str, variables: Dict = None) -> Dict:
        """Execute a GraphQL query"""
        async with httpx.AsyncClient() as client:
            payload = {'query': query}
            if variables:
                payload['variables'] = variables

            response = await client.post(
                self.api_url,
                json=payload,
                headers=self.headers,
                timeout=30.0
            )
            response.raise_for_status()

            data = response.json()

            if 'errors' in data:
                raise Exception(f"Shopify GraphQL errors: {data['errors']}")

            return data.get('data', {})

    async def get_products(self, limit: int = 50, cursor: str = None) -> Dict:
        """
        Get products from Shopify

        Args:
            limit: Number of products to fetch (max 250)
            cursor: Pagination cursor for next page

        Returns:
            Dict with products and pagination info
        """
        query = """
        query ($first: Int!, $after: String) {
          products(first: $first, after: $after) {
            edges {
              cursor
              node {
                id
                title
                description
                vendor
                productType
                status
                createdAt
                updatedAt
                variants(first: 10) {
                  edges {
                    node {
                      id
                      title
                      sku
                      price
                      inventoryQuantity
                    }
                  }
                }
              }
            }
            pageInfo {
              hasNextPage
              endCursor
            }
          }
        }
        """

        variables = {'first': limit}
        if cursor:
            variables['after'] = cursor

        return await self._execute_query(query, variables)

    async def get_orders(self, limit: int = 50, cursor: str = None,
                        created_after: datetime = None) -> Dict:
        """
        Get orders from Shopify

        Args:
            limit: Number of orders to fetch (max 250)
            cursor: Pagination cursor for next page
            created_after: Only get orders created after this datetime

        Returns:
            Dict with orders and pagination info
        """
        # Build query filter
        query_filter = ""
        if created_after:
            # Format: created_at:>='2024-01-01T00:00:00Z'
            date_str = created_after.strftime('%Y-%m-%dT%H:%M:%SZ')
            query_filter = f'created_at:>=\\"{date_str}\\"'

        query = """
        query ($first: Int!, $after: String, $query: String) {
          orders(first: $first, after: $after, query: $query) {
            edges {
              cursor
              node {
                id
                name
                email
                createdAt
                updatedAt
                cancelledAt
                closedAt
                fullyPaid
                displayFulfillmentStatus
                displayFinancialStatus
                totalPriceSet {
                  shopMoney {
                    amount
                    currencyCode
                  }
                }
                subtotalPriceSet {
                  shopMoney {
                    amount
                  }
                }
                totalTaxSet {
                  shopMoney {
                    amount
                  }
                }
                totalShippingPriceSet {
                  shopMoney {
                    amount
                  }
                }
                totalDiscountsSet {
                  shopMoney {
                    amount
                  }
                }
                customer {
                  id
                  firstName
                  lastName
                  email
                  phone
                  defaultAddress {
                    address1
                    address2
                    city
                    province
                    zip
                    country
                  }
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
                      originalUnitPriceSet {
                        shopMoney {
                          amount
                        }
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
            pageInfo {
              hasNextPage
              endCursor
            }
          }
        }
        """

        variables = {'first': limit}
        if cursor:
            variables['after'] = cursor
        if query_filter:
            variables['query'] = query_filter

        return await self._execute_query(query, variables)

    async def get_order_by_id(self, order_id: str) -> Dict:
        """
        Get a single order by ID

        Args:
            order_id: Shopify order ID (gid://shopify/Order/123456)

        Returns:
            Order data
        """
        query = """
        query ($id: ID!) {
          order(id: $id) {
            id
            name
            email
            createdAt
            updatedAt
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
            }
            lineItems(first: 50) {
              edges {
                node {
                  title
                  quantity
                  variant {
                    sku
                    price
                  }
                }
              }
            }
          }
        }
        """

        result = await self._execute_query(query, {'id': order_id})
        return result.get('order', {})

    async def get_customers(self, limit: int = 50, cursor: str = None) -> Dict:
        """
        Get customers from Shopify

        Args:
            limit: Number of customers to fetch (max 250)
            cursor: Pagination cursor for next page

        Returns:
            Dict with customers and pagination info
        """
        query = """
        query ($first: Int!, $after: String) {
          customers(first: $first, after: $after) {
            edges {
              cursor
              node {
                id
                firstName
                lastName
                email
                phone
                createdAt
                updatedAt
                numberOfOrders
                defaultAddress {
                  address1
                  address2
                  city
                  province
                  zip
                  country
                }
              }
            }
            pageInfo {
              hasNextPage
              endCursor
            }
          }
        }
        """

        variables = {'first': limit}
        if cursor:
            variables['after'] = cursor

        return await self._execute_query(query, variables)

    def normalize_order(self, shopify_order: Dict) -> Dict:
        """
        Normalize Shopify order to our database format

        Args:
            shopify_order: Raw order data from Shopify

        Returns:
            Normalized order dict ready for database
        """
        node = shopify_order if 'id' in shopify_order else shopify_order.get('node', {})

        # Extract customer info
        customer = node.get('customer', {})
        customer_data = None
        if customer:
            address = customer.get('defaultAddress', {})
            customer_data = {
                'external_id': customer.get('id', '').split('/')[-1],
                'source': 'shopify',
                'name': f"{customer.get('firstName', '')} {customer.get('lastName', '')}".strip(),
                'email': customer.get('email'),
                'phone': customer.get('phone'),
                'address': f"{address.get('address1', '')} {address.get('address2', '')}".strip(),
                'city': address.get('city'),
                'type_customer': 'person'
            }

        # Extract line items
        line_items = []
        for edge in node.get('lineItems', {}).get('edges', []):
            item = edge.get('node', {})
            variant = item.get('variant') or {}  # Handle None variant

            # Get price from variant or from discountedUnitPriceSet
            price = 0
            if variant and variant.get('price'):
                price = float(variant.get('price'))
            elif item.get('discountedUnitPriceSet'):
                price_data = item.get('discountedUnitPriceSet', {}).get('shopMoney', {})
                price = float(price_data.get('amount', 0))

            line_items.append({
                'product_sku': variant.get('sku', 'UNKNOWN') if variant else 'UNKNOWN',
                'product_name': item.get('title', 'Unknown Product'),
                'quantity': item.get('quantity', 0),
                'unit_price': price,
                'subtotal': price * item.get('quantity', 0),
                'total': price * item.get('quantity', 0)
            })

        # Build normalized order
        total_price = node.get('totalPriceSet', {}).get('shopMoney', {})
        subtotal = node.get('subtotalPriceSet', {}).get('shopMoney', {})
        tax = node.get('totalTaxSet', {}).get('shopMoney', {})
        shipping = node.get('totalShippingPriceSet', {}).get('shopMoney', {})
        discount = node.get('totalDiscountsSet', {}).get('shopMoney', {})

        return {
            'external_id': node.get('id', '').split('/')[-1],
            'order_number': node.get('name', ''),
            'source': 'shopify',
            'customer': customer_data,
            'subtotal': float(subtotal.get('amount', 0)),
            'tax_amount': float(tax.get('amount', 0)),
            'shipping_cost': float(shipping.get('amount', 0)),
            'discount_amount': float(discount.get('amount', 0)),
            'total': float(total_price.get('amount', 0)),
            'status': 'completed' if node.get('closedAt') else 'pending',
            'payment_status': 'paid' if node.get('fullyPaid') else 'pending',
            'fulfillment_status': node.get('displayFulfillmentStatus', 'unfulfilled').lower(),
            'order_date': node.get('createdAt'),
            'items': line_items
        }

    def normalize_product(self, shopify_product: Dict) -> List[Dict]:
        """
        Normalize Shopify product to our database format

        Note: Shopify products can have multiple variants, so we return a list

        Args:
            shopify_product: Raw product data from Shopify

        Returns:
            List of normalized product variants ready for database
        """
        node = shopify_product if 'id' in shopify_product else shopify_product.get('node', {})

        products = []

        for variant_edge in node.get('variants', {}).get('edges', []):
            variant = variant_edge.get('node', {})

            products.append({
                'external_id': variant.get('id', '').split('/')[-1],
                'source': 'shopify',
                'sku': variant.get('sku') or f"SHOPIFY-{variant.get('id', '').split('/')[-1]}",
                'name': f"{node.get('title')} - {variant.get('title')}" if variant.get('title') != 'Default Title' else node.get('title'),
                'description': node.get('description'),
                'category': node.get('productType'),
                'brand': node.get('vendor'),
                'unit': 'unidad',
                'sale_price': float(variant.get('price', 0)),
                'current_stock': variant.get('inventoryQuantity', 0),
                'is_active': node.get('status') == 'ACTIVE'
            })

        return products

    async def test_connection(self) -> Dict:
        """Test Shopify connection"""
        query = """
        {
          shop {
            name
            email
            currencyCode
            primaryDomain {
              url
            }
          }
        }
        """

        try:
            result = await self._execute_query(query)
            shop = result.get('shop', {})
            return {
                'success': True,
                'shop_name': shop.get('name'),
                'email': shop.get('email'),
                'currency': shop.get('currencyCode'),
                'url': shop.get('primaryDomain', {}).get('url')
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
