"""
Product Repository - Data Access Layer for Products

Handles all database queries for products and returns Product domain models.

Author: TM3
Date: 2025-10-17
"""
from typing import List, Optional, Tuple, Dict
from app.domain.product import Product
from app.core.database import get_db_connection_dict


class ProductRepository:
    """
    Repository for Product data access

    All SQL queries for products are centralized here.
    Returns Product domain models, not raw dictionaries.
    """

    @staticmethod
    def _map_row_to_product(row: dict) -> Product:
        """
        Helper method to map database row to Product domain model.

        Database has units_per_box, but domain model expects detailed conversion hierarchy.
        We map units_per_box to units_per_display and set other fields to None.
        """
        return Product(
            id=row['id'],
            external_id=row['external_id'],
            source=row['source'],
            sku=row['sku'],
            name=row['name'],
            description=row['description'],
            category=row['category'],
            brand=row['brand'],
            unit=row['unit'],
            units_per_display=row.get('units_per_box'),
            displays_per_box=None,
            boxes_per_pallet=None,
            display_name=None,
            box_name=None,
            pallet_name=None,
            cost_price=row['cost_price'],
            sale_price=row['sale_price'],
            current_stock=row['current_stock'],
            min_stock=row['min_stock'],
            is_active=row['is_active'],
            created_at=row['created_at'],
            updated_at=row.get('updated_at')
        )

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
                    category, brand, unit, units_per_box,
                    cost_price, sale_price, current_stock, min_stock,
                    is_active, created_at, updated_at
                FROM products
                WHERE id = %s
            """, (product_id,))

            row = cursor.fetchone()
            if not row:
                return None

            return self._map_row_to_product(row)

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
                    category, brand, unit, units_per_box,
                    cost_price, sale_price, current_stock, min_stock,
                    is_active, created_at, updated_at
                FROM products
                WHERE sku = %s
            """, (sku,))

            row = cursor.fetchone()
            if not row:
                return None

            return self._map_row_to_product(row)

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
                    category, brand, unit, units_per_box,
                    cost_price, sale_price, current_stock, min_stock,
                    is_active, created_at, updated_at
                FROM products
                WHERE {where_clause}
                ORDER BY name
                LIMIT %s OFFSET %s
            """, params + [limit, offset])

            rows = cursor.fetchall()
            products = [self._map_row_to_product(row) for row in rows]

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
                    category, brand, unit, units_per_box,
                    cost_price, sale_price, current_stock, min_stock,
                    is_active, created_at, updated_at
                FROM products
                WHERE source = %s
                ORDER BY name
            """, (source,))

            rows = cursor.fetchall()
            return [self._map_row_to_product(row) for row in rows]

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
                        category, brand, unit, units_per_box,
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
                        category, brand, unit, units_per_box,
                        cost_price, sale_price, current_stock, min_stock,
                        is_active, created_at, updated_at
                    FROM products
                    WHERE is_active = true AND current_stock <= min_stock
                    ORDER BY current_stock ASC
                """)

            rows = cursor.fetchall()
            return [self._map_row_to_product(row) for row in rows]

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
            # Database only has units_per_box field
            cursor.execute("""
                SELECT COUNT(*) as count
                FROM products
                WHERE units_per_box IS NOT NULL
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

    def get_hierarchical_families(self) -> List[Dict]:
        """
        Get product families in hierarchical structure

        Returns products grouped by:
        - category (Familia): GRANOLAS, BARRAS, CRACKERS, KEEPERS
        - subfamily (Subfamilia): e.g., "Granola Low Carb Almendras"
        - format (Formato): e.g., "260g", "X1", "X5"

        Returns:
            List of family dictionaries with nested structure
        """
        conn = get_db_connection_dict()
        cursor = conn.cursor()

        try:
            # Query to get hierarchical structure
            # Only show the 4 main families: GRANOLAS, BARRAS, CRACKERS, KEEPERS
            cursor.execute("""
                WITH hierarchy AS (
                    SELECT
                        category,
                        COALESCE(subfamily, 'Sin Clasificar') as subfamily,
                        COALESCE(format, 'Unidad') as format,
                        sku,
                        name,
                        current_stock,
                        sale_price,
                        package_type,
                        units_per_package,
                        master_box_sku,
                        master_box_name
                    FROM products
                    WHERE is_active = true
                    AND category IN ('GRANOLAS', 'BARRAS', 'CRACKERS', 'KEEPERS')
                )
                SELECT
                    category,
                    subfamily,
                    format,
                    COUNT(*) as product_count,
                    SUM(COALESCE(current_stock, 0)) as total_stock,
                    json_agg(
                        json_build_object(
                            'sku', sku,
                            'name', name,
                            'stock', current_stock,
                            'price', sale_price,
                            'package_type', package_type,
                            'units_per_package', units_per_package,
                            'master_box_sku', master_box_sku,
                            'master_box_name', master_box_name
                        )
                    ) as products
                FROM hierarchy
                GROUP BY category, subfamily, format
                ORDER BY category, subfamily, format
            """)

            results = cursor.fetchall()

            # Group by category → subfamily → format
            families_dict = {}

            for row in results:
                category = row['category']
                subfamily = row['subfamily']
                format_name = row['format']

                # Initialize category if needed
                if category not in families_dict:
                    families_dict[category] = {
                        'name': category,
                        'subfamilies': {},
                        'total_stock': 0
                    }

                # Initialize subfamily if needed
                if subfamily not in families_dict[category]['subfamilies']:
                    families_dict[category]['subfamilies'][subfamily] = {
                        'name': subfamily,
                        'formats': [],
                        'total_stock': 0
                    }

                # Add format
                families_dict[category]['subfamilies'][subfamily]['formats'].append({
                    'name': format_name,
                    'product_count': row['product_count'],
                    'total_stock': row['total_stock'],
                    'products': row['products']
                })

                # Update stock totals
                families_dict[category]['subfamilies'][subfamily]['total_stock'] += row['total_stock']
                families_dict[category]['total_stock'] += row['total_stock']

            # Convert to list format
            families_list = []
            for category, category_data in families_dict.items():
                subfamily_list = []
                for subfamily_name, subfamily_data in category_data['subfamilies'].items():
                    subfamily_list.append({
                        'name': subfamily_name,
                        'formats': subfamily_data['formats'],
                        'total_stock': subfamily_data['total_stock']
                    })

                families_list.append({
                    'name': category,
                    'subfamilies': subfamily_list,
                    'total_stock': category_data['total_stock']
                })

            return families_list

        finally:
            cursor.close()
            conn.close()
