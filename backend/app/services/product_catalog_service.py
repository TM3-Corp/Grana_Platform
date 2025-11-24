"""
Product Catalog Service
Replaces CSV-based product mapping with Supabase database queries

Purpose:
- Get SKU Primario (base/primary SKU for product families)
- Calculate units based on conversion factors
- Query product_catalog table for product information

Author: TM3
Date: 2025-11-18 (Phase 3: Replace CSV with Database)
"""
import os
from typing import Optional, Dict
from pathlib import Path
import psycopg2
from psycopg2.extras import RealDictCursor


class ProductCatalogService:
    """
    Service for querying product_catalog table from Supabase

    Replaces the CSV-based logic in audit.py with database queries.
    Maintains backward compatibility with existing API behavior.
    """

    def __init__(self):
        """Initialize service and load catalog from database"""
        self._catalog_cache: Optional[Dict[str, Dict]] = None
        self._master_sku_lookup: Optional[Dict[str, Dict]] = None  # Reverse lookup for master SKUs
        self._connection_string = self._get_database_url()

    def _get_database_url(self) -> str:
        """
        Get database connection string

        Priority:
        1. Environment variable DATABASE_URL
        2. backend/.env file
        3. Hardcoded Session Pooler URL (WSL2 compatible)
        """
        # Check environment variable first
        db_url = os.getenv('DATABASE_URL')
        if db_url:
            return db_url

        # Try loading from .env file
        env_path = Path(__file__).parent.parent.parent / '.env'
        if env_path.exists():
            with open(env_path, 'r') as f:
                for line in f:
                    if line.startswith('DATABASE_URL='):
                        return line.split('=', 1)[1].strip().strip('"').strip("'")

        # Fallback: Hardcoded Session Pooler URL (IPv4 - works in WSL2)
        return "postgresql://postgres.lypuvibmtxjaxmcmahxr:%24Ilofono1@aws-1-sa-east-1.pooler.supabase.com:6543/postgres"

    def _load_catalog_from_database(self) -> Dict[str, Dict]:
        """
        Load product catalog from Supabase into memory cache

        Returns:
            Dictionary mapping SKU to product data:
            {
                "BAKC_U04010": {
                    "sku": "BAKC_U04010",
                    "base_code": "BAKC",
                    "category": "BARRAS",
                    "units_per_display": 1,
                    "units_per_master_box": 200,
                    "is_master_sku": False,
                    "primario": "BAKC_U04010"  # Calculated
                },
                "BAKC_U20010": {
                    "sku": "BAKC_U20010",
                    "base_code": "BAKC",
                    "category": "BARRAS",
                    "units_per_display": 5,
                    "is_master_sku": False,
                    "primario": "BAKC_U04010"  # Points to X1 variant
                }
            }
        """
        catalog = {}

        try:
            conn = psycopg2.connect(self._connection_string)
            cursor = conn.cursor(cursor_factory=RealDictCursor)

            # Fetch all active products (including sku_master for reverse lookup)
            cursor.execute("""
                SELECT
                    sku,
                    sku_master,
                    base_code,
                    category,
                    product_name,
                    units_per_display,
                    units_per_master_box,
                    items_per_master_box,
                    is_master_sku,
                    language
                FROM product_catalog
                WHERE is_active = TRUE
                ORDER BY sku
            """)

            products = cursor.fetchall()

            # Build initial catalog and master SKU reverse lookup
            master_sku_lookup = {}

            for product in products:
                # Add to main catalog (indexed by normal SKU)
                catalog[product['sku']] = dict(product)

                # ALSO add to master SKU lookup (indexed by sku_master)
                # This allows us to find products when orders contain master box SKUs
                if product['sku_master']:
                    master_sku_lookup[product['sku_master']] = dict(product)

            # Calculate SKU Primario for each product
            # Rule: SKU Primario = SKU with same base_code AND units_per_display = 1 AND language = 'ESPAÑOL'
            # This is the minimal unit for each product family (Spanish version only)

            # First pass: Build a map of base_code -> minimal unit SKU (Spanish only)
            base_code_to_primario = {}
            for sku, data in catalog.items():
                base_code = data['base_code']
                units_per_display = data.get('units_per_display')
                language = data.get('language', '').upper()

                if base_code and units_per_display == 1 and language == 'ESPAÑOL':
                    # This is a Spanish minimal unit (X1) - it's the SKU Primario
                    # Only Spanish products are used as primarios
                    base_code_to_primario[base_code] = sku

            # Second pass: Assign SKU Primario to all products
            for sku, data in catalog.items():
                base_code = data['base_code']
                if base_code and base_code in base_code_to_primario:
                    # Found minimal unit for this base_code
                    data['primario'] = base_code_to_primario[base_code]
                else:
                    # No minimal unit found, SKU is its own primario
                    data['primario'] = sku

            # ALSO calculate SKU Primario for master SKUs in lookup
            for master_sku, data in master_sku_lookup.items():
                base_code = data['base_code']
                if base_code and base_code in base_code_to_primario:
                    # Found minimal unit for this base_code
                    data['primario'] = base_code_to_primario[base_code]
                else:
                    # No minimal unit found, use the product SKU (not master SKU)
                    data['primario'] = data.get('sku', master_sku)

            cursor.close()
            conn.close()

            # Store master SKU lookup for later use
            self._master_sku_lookup = master_sku_lookup

            return catalog

        except Exception as e:
            # If database fails, return empty catalog (graceful degradation)
            print(f"Warning: Failed to load product catalog from database: {e}")
            return {}

    def _get_catalog(self) -> Dict[str, Dict]:
        """
        Get cached catalog, loading from database if not cached

        Returns:
            Catalog dictionary
        """
        if self._catalog_cache is None:
            self._catalog_cache = self._load_catalog_from_database()
        return self._catalog_cache

    def reload_catalog(self):
        """
        Force reload catalog from database

        Useful for:
        - After catalog updates
        - Testing
        - Cache invalidation
        """
        self._catalog_cache = None
        self._catalog_cache = self._load_catalog_from_database()

    def get_sku_primario(self, sku: str) -> Optional[str]:
        """
        Get the SKU Primario (base/primary SKU) for any SKU variant

        Returns the X1 variant (_U04010 for Spanish) if it exists.
        If it doesn't exist in the catalog, returns the SKU itself.

        CRITICAL: We NEVER invent SKU codes that don't exist in the catalog.

        Args:
            sku: Product SKU (e.g., 'BAKC_U20010')

        Returns:
            SKU Primario (e.g., 'BAKC_U04010') or original SKU if not found

        Examples:
            BAKC_U20010 → BAKC_U04010 (primary exists in catalog)
            GRAL_U26010 → GRAL_U26010 (GRAL_U04010 doesn't exist, so use itself)
            UNKNOWN_SKU → UNKNOWN_SKU (not in catalog, return itself)
        """
        if not sku:
            return None

        catalog = self._get_catalog()

        # Check if we have it in catalog (normal SKU)
        if sku in catalog:
            return catalog[sku].get('primario', sku)

        # Check if it's a master box SKU
        if self._master_sku_lookup and sku in self._master_sku_lookup:
            return self._master_sku_lookup[sku].get('primario', sku)

        # Fallback: If SKU not in catalog, it's its own primario
        # We NEVER invent codes that don't exist
        return sku

    def calculate_units(self, sku: str, quantity: int) -> int:
        """
        Calculate total units based on SKU and quantity

        Formula: Units = Quantity × Conversion Factor

        Conversion factors from product_catalog:
        - units_per_display: For normal SKUs (X1, X5, X16, etc.)
        - items_per_master_box: For master box SKUs (_C pattern)

        IMPORTANT:
        - items_per_master_box = total individual items in master box
        - units_per_master_box = number of packages in master box (NOT used for conversion)

        Args:
            sku: Product SKU
            quantity: Quantity ordered

        Returns:
            Total units (int)

        Examples:
            - BAKC_U04010 (X1): 10 × 1 = 10 bars
            - BAKC_U20010 (X5): 10 × 5 = 50 bars
            - BAKC_C02810 (CM): 2 × 140 = 280 bars (NOT 2 × 28 = 56!)
        """
        if not sku or quantity is None:
            return 0

        catalog = self._get_catalog()

        # Try normal SKU first
        if sku in catalog:
            product = catalog[sku]
            # Normal SKUs use units_per_display
            conversion_factor = product.get('units_per_display', 1)
            return quantity * (conversion_factor or 1)

        # Try master box SKU lookup
        if self._master_sku_lookup and sku in self._master_sku_lookup:
            product = self._master_sku_lookup[sku]
            # Master box SKUs use items_per_master_box (total individual items)
            conversion_factor = product.get('items_per_master_box', 1)
            return quantity * (conversion_factor or 1)

        # SKU not found in catalog - return 1:1 conversion (no fallback patterns)
        # This ensures we rely 100% on the database
        # Products not in catalog will show quantity as units, making them easy to identify
        return quantity * 1

    def get_conversion_factor(self, sku: str) -> int:
        """
        Get the conversion factor for a SKU (without multiplying by quantity)

        This is used to display the conversion factor indicator in the UI (e.g., "×140")

        IMPORTANT: Returns 1 if SKU not found in catalog (no fallback patterns).
        This ensures we rely 100% on database data and can identify missing products.

        Returns:
            - units_per_display for normal SKUs (1, 5, 16, etc.)
            - items_per_master_box for master box SKUs (140, 200, etc.)
            - 1 for unknown SKUs (indicates missing catalog entry)

        Examples:
            - BAKC_U04010 (X1): returns 1
            - BAKC_U20010 (X5): returns 5
            - BAKC_C02810 (Caja Master): returns 140
            - UNKNOWN_SKU: returns 1 (not in catalog)
        """
        if not sku:
            return 1

        catalog = self._get_catalog()

        # Try normal SKU first
        if sku in catalog:
            return catalog[sku].get('units_per_display', 1) or 1

        # Try master box SKU lookup
        if self._master_sku_lookup and sku in self._master_sku_lookup:
            return self._master_sku_lookup[sku].get('items_per_master_box', 1) or 1

        # SKU not found in catalog - return 1 (no fallback patterns)
        # This helps identify products that need to be added to product_catalog table
        return 1

    def get_product_info(self, sku: str) -> Optional[Dict]:
        """
        Get complete product information from catalog

        Args:
            sku: Product SKU

        Returns:
            Product dictionary or None if not found
        """
        catalog = self._get_catalog()
        return catalog.get(sku)

    def get_product_name_for_sku_primario(self, sku_primario: str) -> Optional[str]:
        """
        Get formatted product name for a SKU Primario

        Args:
            sku_primario: Primary SKU (e.g., 'BAKC_U04010')

        Returns:
            Formatted product name in title case (e.g., 'Barra Keto Nuez')
            Returns None if SKU not found or product_name is empty

        Examples:
            BAKC_U04010 → 'Barra Keto Nuez'
            BACM_U04010 → 'Barra Low Carb Cacao Maní'
            BABE_U04010 → 'Barra Low Carb Berries'
        """
        if not sku_primario:
            return None

        # Get product info from catalog
        product_info = self.get_product_info(sku_primario)
        if not product_info:
            return None

        # Get product_name from catalog
        product_name = product_info.get('product_name')
        if not product_name:
            return None

        # Format: Convert to title case (capitalize first letter of each word)
        # This handles names like "BARRA KETO NUEZ" → "Barra Keto Nuez"
        formatted_name = product_name.strip().title()

        # Remove unit indicators (X1, X5, X16, etc.) from the end
        # Pattern: Remove " X" followed by digits at the end
        import re
        formatted_name = re.sub(r'\s+X\d+\s*$', '', formatted_name, flags=re.IGNORECASE)

        return formatted_name

    def get_all_products(self) -> Dict[str, Dict]:
        """
        Get all products from catalog

        Returns:
            Complete catalog dictionary
        """
        return self._get_catalog()

    def get_products_by_category(self, category: str) -> Dict[str, Dict]:
        """
        Get all products in a category

        Args:
            category: Category name (e.g., 'BARRAS', 'CRACKERS', 'GRANOLAS')

        Returns:
            Dictionary of products in that category
        """
        catalog = self._get_catalog()
        return {
            sku: data
            for sku, data in catalog.items()
            if data.get('category') == category
        }

    def get_product_family(self, base_code: str) -> Dict[str, Dict]:
        """
        Get all SKU variants in a product family

        Args:
            base_code: Base product code (e.g., 'BAKC', 'GRAL')

        Returns:
            Dictionary of all variants with that base_code
        """
        catalog = self._get_catalog()
        return {
            sku: data
            for sku, data in catalog.items()
            if data.get('base_code') == base_code
        }

    def get_catalog_stats(self) -> Dict:
        """
        Get statistics about the product catalog

        Returns:
            Dictionary with catalog statistics
        """
        catalog = self._get_catalog()

        categories = {}
        families = set()
        master_skus = 0

        for sku, data in catalog.items():
            # Count by category
            category = data.get('category')
            if category:
                categories[category] = categories.get(category, 0) + 1

            # Count families
            base_code = data.get('base_code')
            if base_code:
                families.add(base_code)

            # Count master SKUs
            if data.get('is_master_sku'):
                master_skus += 1

        return {
            'total_products': len(catalog),
            'total_families': len(families),
            'total_master_skus': master_skus,
            'categories': categories
        }
