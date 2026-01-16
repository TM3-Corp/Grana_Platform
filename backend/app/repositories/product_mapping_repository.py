"""
Product Mapping Repository - Data Access Layer for Product Variants and Channel Equivalents

DEPRECATED: Tables product_variants and channel_equivalents were removed in migration 20260113.
- product_variants: Replaced by product_catalog families (sku_primario grouping)
- channel_equivalents: Never implemented, was always empty

This file is kept for backwards compatibility but all functions return empty results.
Use ProductCatalogService for family-based product queries.

Author: TM3
Date: 2025-10-17
Refactored: 2026-01-16
"""
from typing import List, Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)


class ProductMappingRepository:
    """
    Repository for Product Mapping data access

    DEPRECATED: The underlying tables were removed in migration 20260113.
    All methods now return empty results for backwards compatibility.

    For product family data, use ProductCatalogService which queries
    product_catalog with sku_primario for family grouping.
    """

    # ========================================
    # Product Variants (DEPRECATED)
    # ========================================

    def find_variants_by_base_product(self, base_product_id: int) -> List[Dict[str, Any]]:
        """
        DEPRECATED: Table product_variants was removed in migration 20260113.
        Use ProductCatalogService for family-based product queries.

        Returns empty list for backwards compatibility.
        """
        logger.warning(
            "find_variants_by_base_product is deprecated. "
            "Table product_variants removed in migration 20260113. "
            "Use ProductCatalogService with sku_primario for family queries."
        )
        return []

    def find_variant_by_id(self, variant_id: int) -> Optional[Dict[str, Any]]:
        """
        DEPRECATED: Table product_variants was removed in migration 20260113.

        Returns None for backwards compatibility.
        """
        logger.warning(
            "find_variant_by_id is deprecated. "
            "Table product_variants removed in migration 20260113."
        )
        return None

    def find_consolidated_inventory(
        self,
        base_product_id: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        DEPRECATED: View inventory_consolidated was removed in migration 20260113.

        Returns empty list for backwards compatibility.
        """
        logger.warning(
            "find_consolidated_inventory is deprecated. "
            "View inventory_consolidated removed in migration 20260113."
        )
        return []

    def find_product_families(
        self,
        base_product_id: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        DEPRECATED: View product_families was removed in migration 20260113.
        Use product_catalog with sku_primario for family grouping.

        Returns empty list for backwards compatibility.
        """
        return []

    def create_variant_mapping(
        self,
        base_product_id: int,
        variant_product_id: int,
        quantity_multiplier: int,
        packaging_type: str,
        is_active: bool = True
    ) -> Dict[str, Any]:
        """
        DEPRECATED: Table product_variants was removed in migration 20260113.

        Returns error for backwards compatibility.
        """
        logger.warning(
            "create_variant_mapping is deprecated. "
            "Table product_variants removed in migration 20260113. "
            "Use product_catalog for family management."
        )
        return {
            'success': False,
            'error': 'Table product_variants was removed. Use product_catalog for family management.'
        }

    def delete_variant_mapping(self, variant_id: int) -> Dict[str, Any]:
        """
        DEPRECATED: Table product_variants was removed in migration 20260113.

        Returns error for backwards compatibility.
        """
        logger.warning(
            "delete_variant_mapping is deprecated. "
            "Table product_variants removed in migration 20260113."
        )
        return {
            'success': False,
            'error': 'Table product_variants was removed.'
        }

    # ========================================
    # Channel Equivalents (DEPRECATED)
    # ========================================

    def find_channel_equivalents(self) -> List[Dict[str, Any]]:
        """
        DEPRECATED: Table channel_equivalents was removed in migration 20260113.
        This feature was never implemented.

        Returns empty list for backwards compatibility.
        """
        logger.warning(
            "find_channel_equivalents is deprecated. "
            "Table channel_equivalents removed in migration 20260113."
        )
        return []

    def find_equivalent_by_product(
        self,
        product_id: int,
        source: str
    ) -> Optional[Dict[str, Any]]:
        """
        DEPRECATED: Table channel_equivalents was removed in migration 20260113.

        Returns None for backwards compatibility.
        """
        logger.warning(
            "find_equivalent_by_product is deprecated. "
            "Table channel_equivalents removed in migration 20260113."
        )
        return None

    def create_channel_equivalent(
        self,
        shopify_product_id: int,
        mercadolibre_product_id: int,
        equivalence_confidence: float,
        verified: bool = False,
        notes: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        DEPRECATED: Table channel_equivalents was removed in migration 20260113.

        Returns error for backwards compatibility.
        """
        logger.warning(
            "create_channel_equivalent is deprecated. "
            "Table channel_equivalents removed in migration 20260113."
        )
        return {
            'success': False,
            'error': 'Table channel_equivalents was removed. Feature was never implemented.'
        }

    def delete_channel_equivalent(self, equivalent_id: int) -> Dict[str, Any]:
        """
        DEPRECATED: Table channel_equivalents was removed in migration 20260113.

        Returns error for backwards compatibility.
        """
        logger.warning(
            "delete_channel_equivalent is deprecated. "
            "Table channel_equivalents removed in migration 20260113."
        )
        return {
            'success': False,
            'error': 'Table channel_equivalents was removed.'
        }

    # ========================================
    # Detection & Search Queries (Still functional)
    # ========================================

    def find_potential_variants_by_sku_pattern(
        self,
        base_sku: str,
        base_product_id: int
    ) -> List[Dict[str, Any]]:
        """
        Find potential variant products by SKU pattern matching.

        This method still works as it queries the products table directly.
        Used for auto-detection of packaging variants.

        Args:
            base_sku: Base product SKU (e.g., BAKC_U04010)
            base_product_id: Base product ID to exclude

        Returns:
            List of potential variant products
        """
        from app.core.database import get_db_connection_dict_with_retry

        conn = get_db_connection_dict_with_retry()
        cursor = conn.cursor()

        try:
            # Extract base code from SKU (e.g., BAKC from BAKC_U04010)
            base_code = base_sku.split('_')[0] if '_' in base_sku else base_sku[:4]

            cursor.execute("""
                SELECT
                    id,
                    sku,
                    name,
                    current_stock,
                    sale_price,
                    source
                FROM products
                WHERE sku LIKE %s
                    AND id != %s
                    AND is_active = true
                ORDER BY sku
            """, (f"{base_code}_%", base_product_id))

            return cursor.fetchall()

        finally:
            cursor.close()
            conn.close()

    def find_potential_equivalents_by_source(
        self,
        source_to_match: str,
        exclude_product_id: int
    ) -> List[Dict[str, Any]]:
        """
        Find potential equivalent products from another channel.

        This method still works as it queries the products table directly.
        Used for auto-detection of cross-channel equivalents.

        Args:
            source_to_match: Target source platform
            exclude_product_id: Product ID to exclude

        Returns:
            List of potential equivalent products
        """
        from app.core.database import get_db_connection_dict_with_retry

        conn = get_db_connection_dict_with_retry()
        cursor = conn.cursor()

        try:
            cursor.execute("""
                SELECT
                    id,
                    sku,
                    name,
                    current_stock,
                    sale_price,
                    source
                FROM products
                WHERE source = %s
                    AND id != %s
                    AND is_active = true
                ORDER BY name
            """, (source_to_match, exclude_product_id))

            return cursor.fetchall()

        finally:
            cursor.close()
            conn.close()
