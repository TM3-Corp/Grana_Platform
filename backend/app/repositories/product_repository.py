"""
Product Repository - Data Access Layer for Products

Handles all database queries for products and returns Product domain models.

Author: TM3
Date: 2025-10-17
"""
from typing import List, Optional, Tuple
from app.domain.product import Product
from app.core.database import get_db_connection_dict


class ProductRepository:
    """
    Repository for Product data access

    All SQL queries for products are centralized here.
    Returns Product domain models, not raw dictionaries.
    """

    def find_by_id(self, product_id: int) -> Optional[Product]:
        """
        Find product by ID

        Args:
            product_id: Internal product ID

        Returns:
            Product or None if not found
        """
        conn = get_db_connection_dict()
        cursor = conn.cursor()

        try:
            cursor.execute("""
                SELECT
                    id, external_id, source, sku, name, description,
                    category, brand, unit,
                    units_per_display, displays_per_box, boxes_per_pallet,
                    display_name, box_name, pallet_name,
                    cost_price, sale_price, current_stock, min_stock,
                    is_active, created_at, updated_at
                FROM products
                WHERE id = %s
            """, (product_id,))

            row = cursor.fetchone()
            return Product(**row) if row else None

        finally:
            cursor.close()
            conn.close()

    def find_by_sku(self, sku: str) -> Optional[Product]:
        """
        Find product by SKU

        Args:
            sku: Product SKU

        Returns:
            Product or None if not found
        """
        conn = get_db_connection_dict()
        cursor = conn.cursor()

        try:
            cursor.execute("""
                SELECT
                    id, external_id, source, sku, name, description,
                    category, brand, unit,
                    units_per_display, displays_per_box, boxes_per_pallet,
                    display_name, box_name, pallet_name,
                    cost_price, sale_price, current_stock, min_stock,
                    is_active, created_at, updated_at
                FROM products
                WHERE sku = %s
            """, (sku,))

            row = cursor.fetchone()
            return Product(**row) if row else None

        finally:
            cursor.close()
            conn.close()

    def find_all(
        self,
        source: Optional[str] = None,
        category: Optional[str] = None,
        is_active: Optional[bool] = None,
        search: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> Tuple[List[Product], int]:
        """
        Find products with filters

        Args:
            source: Filter by source (shopify, mercadolibre, etc.)
            category: Filter by category
            is_active: Filter by active status
            search: Search in name or SKU
            limit: Maximum results to return
            offset: Number of results to skip

        Returns:
            Tuple of (list of products, total count)
        """
        conn = get_db_connection_dict()
        cursor = conn.cursor()

        try:
            # Build WHERE clause
            conditions = []
            params = []

            if source:
                conditions.append("source = %s")
                params.append(source)

            if category:
                conditions.append("category = %s")
                params.append(category)

            if is_active is not None:
                conditions.append("is_active = %s")
                params.append(is_active)

            if search:
                conditions.append("(name ILIKE %s OR sku ILIKE %s)")
                search_term = f"%{search}%"
                params.extend([search_term, search_term])

            where_clause = " AND ".join(conditions) if conditions else "1=1"

            # Get total count
            cursor.execute(f"""
                SELECT COUNT(*) as total
                FROM products
                WHERE {where_clause}
            """, params)
            total = cursor.fetchone()['total']

            # Get products
            cursor.execute(f"""
                SELECT
                    id, external_id, source, sku, name, description,
                    category, brand, unit,
                    units_per_display, displays_per_box, boxes_per_pallet,
                    display_name, box_name, pallet_name,
                    cost_price, sale_price, current_stock, min_stock,
                    is_active, created_at, updated_at
                FROM products
                WHERE {where_clause}
                ORDER BY name
                LIMIT %s OFFSET %s
            """, params + [limit, offset])

            rows = cursor.fetchall()
            products = [Product(**row) for row in rows]

            return products, total

        finally:
            cursor.close()
            conn.close()

    def find_by_source(self, source: str) -> List[Product]:
        """
        Find all products from a specific source

        Args:
            source: Source platform (shopify, mercadolibre, etc.)

        Returns:
            List of products
        """
        conn = get_db_connection_dict()
        cursor = conn.cursor()

        try:
            cursor.execute("""
                SELECT
                    id, external_id, source, sku, name, description,
                    category, brand, unit,
                    units_per_display, displays_per_box, boxes_per_pallet,
                    display_name, box_name, pallet_name,
                    cost_price, sale_price, current_stock, min_stock,
                    is_active, created_at, updated_at
                FROM products
                WHERE source = %s
                ORDER BY name
            """, (source,))

            rows = cursor.fetchall()
            return [Product(**row) for row in rows]

        finally:
            cursor.close()
            conn.close()

    def find_low_stock(self, threshold: Optional[int] = None) -> List[Product]:
        """
        Find products with low stock

        Args:
            threshold: Custom threshold (if None, uses min_stock)

        Returns:
            List of products with low stock
        """
        conn = get_db_connection_dict()
        cursor = conn.cursor()

        try:
            if threshold is not None:
                cursor.execute("""
                    SELECT
                        id, external_id, source, sku, name, description,
                        category, brand, unit,
                        units_per_display, displays_per_box, boxes_per_pallet,
                        display_name, box_name, pallet_name,
                        cost_price, sale_price, current_stock, min_stock,
                        is_active, created_at, updated_at
                    FROM products
                    WHERE is_active = true AND current_stock <= %s
                    ORDER BY current_stock ASC
                """, (threshold,))
            else:
                cursor.execute("""
                    SELECT
                        id, external_id, source, sku, name, description,
                        category, brand, unit,
                        units_per_display, displays_per_box, boxes_per_pallet,
                        display_name, box_name, pallet_name,
                        cost_price, sale_price, current_stock, min_stock,
                        is_active, created_at, updated_at
                    FROM products
                    WHERE is_active = true AND current_stock <= min_stock
                    ORDER BY current_stock ASC
                """)

            rows = cursor.fetchall()
            return [Product(**row) for row in rows]

        finally:
            cursor.close()
            conn.close()

    def count_by_filters(
        self,
        source: Optional[str] = None,
        category: Optional[str] = None,
        is_active: Optional[bool] = None
    ) -> int:
        """
        Count products matching filters

        Args:
            source: Filter by source
            category: Filter by category
            is_active: Filter by active status

        Returns:
            Count of matching products
        """
        conn = get_db_connection_dict()
        cursor = conn.cursor()

        try:
            conditions = []
            params = []

            if source:
                conditions.append("source = %s")
                params.append(source)

            if category:
                conditions.append("category = %s")
                params.append(category)

            if is_active is not None:
                conditions.append("is_active = %s")
                params.append(is_active)

            where_clause = " AND ".join(conditions) if conditions else "1=1"

            cursor.execute(f"""
                SELECT COUNT(*) as total
                FROM products
                WHERE {where_clause}
            """, params)

            return cursor.fetchone()['total']

        finally:
            cursor.close()
            conn.close()

    def get_stats(self) -> dict:
        """
        Get product statistics

        Returns:
            Dict with product stats (total, by_source, by_category, stock_levels)
        """
        conn = get_db_connection_dict()
        cursor = conn.cursor()

        try:
            # Total products
            cursor.execute("SELECT COUNT(*) as total FROM products WHERE is_active = true")
            total_active = cursor.fetchone()['total']

            cursor.execute("SELECT COUNT(*) as total FROM products")
            total_all = cursor.fetchone()['total']

            # By source
            cursor.execute("""
                SELECT source, COUNT(*) as count
                FROM products
                WHERE is_active = true
                GROUP BY source
                ORDER BY count DESC
            """)
            by_source = cursor.fetchall()

            # By category
            cursor.execute("""
                SELECT category, COUNT(*) as count
                FROM products
                WHERE is_active = true AND category IS NOT NULL
                GROUP BY category
                ORDER BY count DESC
                LIMIT 10
            """)
            by_category = cursor.fetchall()

            # Stock levels
            cursor.execute("""
                SELECT
                    COUNT(*) FILTER (WHERE current_stock <= 0) as out_of_stock,
                    COUNT(*) FILTER (WHERE current_stock > 0 AND current_stock <= min_stock) as low_stock,
                    COUNT(*) FILTER (WHERE current_stock > min_stock) as in_stock
                FROM products
                WHERE is_active = true
            """)
            stock_levels = cursor.fetchone()

            # Products with conversion data
            cursor.execute("""
                SELECT COUNT(*) as count
                FROM products
                WHERE units_per_display IS NOT NULL
                    AND displays_per_box IS NOT NULL
                    AND boxes_per_pallet IS NOT NULL
            """)
            with_conversions = cursor.fetchone()['count']

            return {
                'totals': {
                    'all': total_all,
                    'active': total_active,
                    'with_conversions': with_conversions
                },
                'by_source': by_source,
                'by_category': by_category,
                'stock_levels': stock_levels
            }

        finally:
            cursor.close()
            conn.close()
