"""
MercadoLibre Repository - Data access layer for MercadoLibre sync operations
Handles database operations for syncing ML products and tracking sync stats

Author: TM3
Date: 2025-10-17
"""
from typing import Dict, List, Optional, Any
import psycopg2
from psycopg2.extras import RealDictCursor

from app.core.database import get_db_connection_dict


class MercadoLibreRepository:
    """
    Repository for MercadoLibre sync data access operations

    Handles:
    - Product sync (check, create, update)
    - Sync statistics
    - Sync logs
    """

    def __init__(self):
        pass

    # ============================================
    # Product Sync Operations
    # ============================================

    def find_product_by_external_id(self, external_id: str) -> Optional[Dict[str, Any]]:
        """
        Find a product by MercadoLibre external_id

        Args:
            external_id: MercadoLibre item ID

        Returns:
            Product dict if found, None otherwise
        """
        conn = get_db_connection_dict()
        cursor = conn.cursor()

        try:
            cursor.execute(
                """
                SELECT id, sku, name, external_id, sale_price, current_stock, is_active
                FROM products
                WHERE external_id = %s AND source = 'mercadolibre'
                """,
                (external_id,)
            )

            row = cursor.fetchone()
            if not row:
                return None

            return {
                'id': row[0],
                'sku': row[1],
                'name': row[2],
                'external_id': row[3],
                'sale_price': row[4],
                'current_stock': row[5],
                'is_active': row[6]
            }

        finally:
            cursor.close()
            conn.close()

    def update_product(
        self,
        external_id: str,
        name: str,
        sale_price: float,
        current_stock: int,
        is_active: bool
    ) -> bool:
        """
        Update an existing MercadoLibre product

        Args:
            external_id: MercadoLibre item ID
            name: Product title from ML
            sale_price: Product price
            current_stock: Available quantity
            is_active: Whether product is active

        Returns:
            True if update successful
        """
        conn = get_db_connection_dict()
        cursor = conn.cursor()

        try:
            cursor.execute(
                """
                UPDATE products SET
                    name = %s,
                    sale_price = %s,
                    current_stock = %s,
                    is_active = %s,
                    updated_at = NOW()
                WHERE external_id = %s AND source = 'mercadolibre'
                """,
                (name, sale_price, current_stock, is_active, external_id)
            )

            conn.commit()
            return True

        except Exception as e:
            conn.rollback()
            raise e

        finally:
            cursor.close()
            conn.close()

    def upsert_product(
        self,
        external_id: str,
        sku: str,
        name: str,
        sale_price: float,
        current_stock: int,
        is_active: bool
    ) -> bool:
        """
        Insert or update a MercadoLibre product

        Uses ON CONFLICT to handle duplicates by SKU

        Args:
            external_id: MercadoLibre item ID
            sku: Product SKU (generated or from ML)
            name: Product title from ML
            sale_price: Product price
            current_stock: Available quantity
            is_active: Whether product is active

        Returns:
            True if operation successful
        """
        conn = get_db_connection_dict()
        cursor = conn.cursor()

        try:
            cursor.execute(
                """
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
                """,
                (external_id, sku, name, sale_price, current_stock, is_active)
            )

            conn.commit()
            return True

        except Exception as e:
            conn.rollback()
            raise e

        finally:
            cursor.close()
            conn.close()

    # ============================================
    # Statistics & Monitoring
    # ============================================

    def get_product_count(self) -> int:
        """
        Get total count of MercadoLibre products in database

        Returns:
            Number of ML products
        """
        conn = get_db_connection_dict()
        cursor = conn.cursor()

        try:
            cursor.execute(
                """
                SELECT COUNT(*) as total
                FROM products
                WHERE source = 'mercadolibre'
                """
            )

            row = cursor.fetchone()
            return row[0] if row else 0

        finally:
            cursor.close()
            conn.close()

    def get_order_count(self) -> int:
        """
        Get total count of MercadoLibre orders in database

        Returns:
            Number of ML orders
        """
        conn = get_db_connection_dict()
        cursor = conn.cursor()

        try:
            cursor.execute(
                """
                SELECT COUNT(*) as total
                FROM orders
                WHERE source = 'mercadolibre'
                """
            )

            row = cursor.fetchone()
            return row[0] if row else 0

        finally:
            cursor.close()
            conn.close()

    def get_recent_sync_logs(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get recent sync logs for MercadoLibre

        Args:
            limit: Maximum number of logs to return (default: 10)

        Returns:
            List of sync log dicts
        """
        conn = get_db_connection_dict()
        cursor = conn.cursor()

        try:
            cursor.execute(
                """
                SELECT sync_type, status, records_processed, records_failed,
                       completed_at
                FROM sync_logs
                WHERE source = 'mercadolibre'
                ORDER BY completed_at DESC
                LIMIT %s
                """,
                (limit,)
            )

            rows = cursor.fetchall()
            if not rows:
                return []

            return [
                {
                    'sync_type': row[0],
                    'status': row[1],
                    'records_processed': row[2],
                    'records_failed': row[3],
                    'completed_at': row[4]
                }
                for row in rows
            ]

        finally:
            cursor.close()
            conn.close()

    def get_sync_stats(self) -> Dict[str, Any]:
        """
        Get comprehensive sync statistics for MercadoLibre

        Returns:
            Dict with product count, order count, and recent sync logs
        """
        return {
            'products_synced': self.get_product_count(),
            'orders_synced': self.get_order_count(),
            'recent_syncs': self.get_recent_sync_logs()
        }
