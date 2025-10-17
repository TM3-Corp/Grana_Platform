"""
Product Mapping Repository - Data Access Layer for Product Variants and Channel Equivalents

Handles all database queries for product mappings and returns structured data.

Author: TM3
Date: 2025-10-17
"""
from typing import List, Optional, Dict, Any
from app.core.database import get_db_connection_dict


class ProductMappingRepository:
    """
    Repository for Product Mapping data access

    Handles:
    - Product variants (packaging relationships)
    - Channel equivalents (cross-platform product mappings)
    - Consolidated inventory views
    - Product family views
    """

    # ========================================
    # Product Variants
    # ========================================

    def find_variants_by_base_product(self, base_product_id: int) -> List[Dict[str, Any]]:
        """
        Find all variants for a base product

        Args:
            base_product_id: ID of the base product (1 unit)

        Returns:
            List of variant mappings with product details
        """
        conn = get_db_connection_dict()
        cursor = conn.cursor()

        try:
            cursor.execute("""
                SELECT
                    pv.id,
                    pv.base_product_id,
                    bp.sku as base_sku,
                    bp.name as base_name,
                    pv.variant_product_id,
                    vp.sku as variant_sku,
                    vp.name as variant_name,
                    pv.quantity_multiplier,
                    pv.packaging_type,
                    vp.current_stock as variant_stock,
                    vp.sale_price as variant_price,
                    pv.is_active,
                    pv.created_at
                FROM product_variants pv
                JOIN products bp ON pv.base_product_id = bp.id
                JOIN products vp ON pv.variant_product_id = vp.id
                WHERE pv.base_product_id = %s AND pv.is_active = true
                ORDER BY pv.quantity_multiplier
            """, (base_product_id,))

            return cursor.fetchall()

        finally:
            cursor.close()
            conn.close()

    def find_variant_by_id(self, variant_id: int) -> Optional[Dict[str, Any]]:
        """
        Find a variant mapping by ID

        Args:
            variant_id: ID of the variant mapping

        Returns:
            Variant mapping or None if not found
        """
        conn = get_db_connection_dict()
        cursor = conn.cursor()

        try:
            cursor.execute("""
                SELECT
                    pv.id,
                    pv.base_product_id,
                    bp.sku as base_sku,
                    bp.name as base_name,
                    pv.variant_product_id,
                    vp.sku as variant_sku,
                    vp.name as variant_name,
                    pv.quantity_multiplier,
                    pv.packaging_type,
                    pv.is_active,
                    pv.created_at
                FROM product_variants pv
                JOIN products bp ON pv.base_product_id = bp.id
                JOIN products vp ON pv.variant_product_id = vp.id
                WHERE pv.id = %s
            """, (variant_id,))

            return cursor.fetchone()

        finally:
            cursor.close()
            conn.close()

    def find_consolidated_inventory(
        self,
        base_product_id: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Get consolidated inventory from database view

        Args:
            base_product_id: Optional filter for specific product

        Returns:
            List of consolidated inventory records
        """
        conn = get_db_connection_dict()
        cursor = conn.cursor()

        try:
            if base_product_id:
                cursor.execute("""
                    SELECT
                        base_product_id,
                        base_sku,
                        base_name,
                        base_source,
                        base_unit_price,
                        base_direct_stock,
                        num_variants,
                        variant_stock_as_units,
                        total_units_available,
                        stock_status,
                        inventory_value
                    FROM inventory_consolidated
                    WHERE base_product_id = %s
                    ORDER BY base_name
                """, (base_product_id,))
            else:
                cursor.execute("""
                    SELECT
                        base_product_id,
                        base_sku,
                        base_name,
                        base_source,
                        base_unit_price,
                        base_direct_stock,
                        num_variants,
                        variant_stock_as_units,
                        total_units_available,
                        stock_status,
                        inventory_value
                    FROM inventory_consolidated
                    ORDER BY base_name
                """)

            return cursor.fetchall()

        finally:
            cursor.close()
            conn.close()

    def find_product_families(
        self,
        base_product_id: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Get product families from database view

        Args:
            base_product_id: Optional filter for specific product family

        Returns:
            List of product family records
        """
        conn = get_db_connection_dict()
        cursor = conn.cursor()

        try:
            if base_product_id:
                cursor.execute("""
                    SELECT
                        base_product_id,
                        base_sku,
                        base_name,
                        variant_product_id,
                        variant_sku,
                        variant_name,
                        quantity_multiplier,
                        packaging_type,
                        variant_stock,
                        variant_stock_as_base_units,
                        variant_price,
                        base_unit_price,
                        variant_unit_price,
                        discount_percentage
                    FROM product_families
                    WHERE base_product_id = %s
                    ORDER BY quantity_multiplier
                """, (base_product_id,))
            else:
                cursor.execute("""
                    SELECT
                        base_product_id,
                        base_sku,
                        base_name,
                        variant_product_id,
                        variant_sku,
                        variant_name,
                        quantity_multiplier,
                        packaging_type,
                        variant_stock,
                        variant_stock_as_base_units,
                        variant_price,
                        base_unit_price,
                        variant_unit_price,
                        discount_percentage
                    FROM product_families
                    ORDER BY base_name, quantity_multiplier
                """)

            return cursor.fetchall()

        finally:
            cursor.close()
            conn.close()

    def create_variant_mapping(
        self,
        base_product_id: int,
        variant_product_id: int,
        quantity_multiplier: int,
        packaging_type: str,
        is_active: bool = True
    ) -> Dict[str, Any]:
        """
        Create a new product variant mapping

        Args:
            base_product_id: ID of base product
            variant_product_id: ID of variant product
            quantity_multiplier: Number of base units in variant
            packaging_type: Type of packaging (individual, display_5, etc.)
            is_active: Whether mapping is active

        Returns:
            Result dict with success status and variant_id
        """
        conn = get_db_connection_dict()
        cursor = conn.cursor()

        try:
            # Check if mapping already exists
            cursor.execute("""
                SELECT id FROM product_variants
                WHERE base_product_id = %s AND variant_product_id = %s
            """, (base_product_id, variant_product_id))

            existing = cursor.fetchone()
            if existing:
                return {
                    'success': False,
                    'error': 'Variant mapping already exists'
                }

            # Create mapping
            cursor.execute("""
                INSERT INTO product_variants (
                    base_product_id,
                    variant_product_id,
                    quantity_multiplier,
                    packaging_type,
                    is_active
                )
                VALUES (%s, %s, %s, %s, %s)
                RETURNING id
            """, (base_product_id, variant_product_id, quantity_multiplier, packaging_type, is_active))

            variant_id = cursor.fetchone()['id']
            conn.commit()

            return {
                'success': True,
                'variant_id': variant_id
            }

        except Exception as e:
            conn.rollback()
            return {
                'success': False,
                'error': str(e)
            }

        finally:
            cursor.close()
            conn.close()

    def delete_variant_mapping(self, variant_id: int) -> Dict[str, Any]:
        """
        Soft delete a variant mapping

        Args:
            variant_id: ID of the variant mapping

        Returns:
            Result dict with success status
        """
        conn = get_db_connection_dict()
        cursor = conn.cursor()

        try:
            cursor.execute("""
                UPDATE product_variants
                SET is_active = false
                WHERE id = %s
                RETURNING id
            """, (variant_id,))

            result = cursor.fetchone()
            if not result:
                return {
                    'success': False,
                    'error': 'Variant mapping not found'
                }

            conn.commit()
            return {'success': True}

        except Exception as e:
            conn.rollback()
            return {
                'success': False,
                'error': str(e)
            }

        finally:
            cursor.close()
            conn.close()

    # ========================================
    # Channel Equivalents
    # ========================================

    def find_channel_equivalents(self) -> List[Dict[str, Any]]:
        """
        Get all channel equivalents with product details

        Returns:
            List of channel equivalent records
        """
        conn = get_db_connection_dict()
        cursor = conn.cursor()

        try:
            cursor.execute("""
                SELECT
                    ce.id,
                    ce.shopify_product_id,
                    sp.sku as shopify_sku,
                    sp.name as shopify_name,
                    sp.current_stock as shopify_stock,
                    sp.sale_price as shopify_price,
                    ce.mercadolibre_product_id,
                    mp.sku as mercadolibre_sku,
                    mp.name as mercadolibre_name,
                    mp.current_stock as mercadolibre_stock,
                    mp.sale_price as mercadolibre_price,
                    ce.equivalence_confidence,
                    ce.verified,
                    ce.notes,
                    ce.created_at
                FROM channel_equivalents ce
                JOIN products sp ON ce.shopify_product_id = sp.id
                JOIN products mp ON ce.mercadolibre_product_id = mp.id
                ORDER BY sp.name
            """)

            return cursor.fetchall()

        finally:
            cursor.close()
            conn.close()

    def find_equivalent_by_product(
        self,
        product_id: int,
        source: str
    ) -> Optional[Dict[str, Any]]:
        """
        Find channel equivalent for a product

        Args:
            product_id: Product ID
            source: Source platform (shopify or mercadolibre)

        Returns:
            Channel equivalent or None if not found
        """
        conn = get_db_connection_dict()
        cursor = conn.cursor()

        try:
            if source.lower() == 'shopify':
                cursor.execute("""
                    SELECT
                        ce.id,
                        ce.shopify_product_id,
                        sp.sku as shopify_sku,
                        sp.name as shopify_name,
                        ce.mercadolibre_product_id,
                        mp.sku as mercadolibre_sku,
                        mp.name as mercadolibre_name,
                        ce.equivalence_confidence,
                        ce.verified
                    FROM channel_equivalents ce
                    JOIN products sp ON ce.shopify_product_id = sp.id
                    JOIN products mp ON ce.mercadolibre_product_id = mp.id
                    WHERE ce.shopify_product_id = %s
                """, (product_id,))
            else:
                cursor.execute("""
                    SELECT
                        ce.id,
                        ce.shopify_product_id,
                        sp.sku as shopify_sku,
                        sp.name as shopify_name,
                        ce.mercadolibre_product_id,
                        mp.sku as mercadolibre_sku,
                        mp.name as mercadolibre_name,
                        ce.equivalence_confidence,
                        ce.verified
                    FROM channel_equivalents ce
                    JOIN products sp ON ce.shopify_product_id = sp.id
                    JOIN products mp ON ce.mercadolibre_product_id = mp.id
                    WHERE ce.mercadolibre_product_id = %s
                """, (product_id,))

            return cursor.fetchone()

        finally:
            cursor.close()
            conn.close()

    def create_channel_equivalent(
        self,
        shopify_product_id: int,
        mercadolibre_product_id: int,
        equivalence_confidence: float,
        verified: bool = False,
        notes: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create a new channel equivalent

        Args:
            shopify_product_id: Shopify product ID
            mercadolibre_product_id: MercadoLibre product ID
            equivalence_confidence: Confidence score (0-1)
            verified: Whether manually verified
            notes: Optional notes

        Returns:
            Result dict with success status and equivalent_id
        """
        conn = get_db_connection_dict()
        cursor = conn.cursor()

        try:
            # Check if mapping already exists
            cursor.execute("""
                SELECT id FROM channel_equivalents
                WHERE shopify_product_id = %s AND mercadolibre_product_id = %s
            """, (shopify_product_id, mercadolibre_product_id))

            existing = cursor.fetchone()
            if existing:
                return {
                    'success': False,
                    'error': 'Channel equivalent already exists'
                }

            # Create mapping
            cursor.execute("""
                INSERT INTO channel_equivalents (
                    shopify_product_id,
                    mercadolibre_product_id,
                    equivalence_confidence,
                    verified,
                    notes
                )
                VALUES (%s, %s, %s, %s, %s)
                RETURNING id
            """, (shopify_product_id, mercadolibre_product_id, equivalence_confidence, verified, notes))

            equivalent_id = cursor.fetchone()['id']
            conn.commit()

            return {
                'success': True,
                'equivalent_id': equivalent_id
            }

        except Exception as e:
            conn.rollback()
            return {
                'success': False,
                'error': str(e)
            }

        finally:
            cursor.close()
            conn.close()

    def delete_channel_equivalent(self, equivalent_id: int) -> Dict[str, Any]:
        """
        Delete a channel equivalent

        Args:
            equivalent_id: ID of the channel equivalent

        Returns:
            Result dict with success status
        """
        conn = get_db_connection_dict()
        cursor = conn.cursor()

        try:
            cursor.execute("""
                DELETE FROM channel_equivalents
                WHERE id = %s
                RETURNING id
            """, (equivalent_id,))

            result = cursor.fetchone()
            if not result:
                return {
                    'success': False,
                    'error': 'Channel equivalent not found'
                }

            conn.commit()
            return {'success': True}

        except Exception as e:
            conn.rollback()
            return {
                'success': False,
                'error': str(e)
            }

        finally:
            cursor.close()
            conn.close()

    # ========================================
    # Detection & Search Queries
    # ========================================

    def find_potential_variants_by_sku_pattern(
        self,
        base_sku: str,
        base_product_id: int
    ) -> List[Dict[str, Any]]:
        """
        Find potential variant products by SKU pattern matching

        Used for auto-detection of packaging variants.

        Args:
            base_sku: Base product SKU (e.g., BAKC_U04010)
            base_product_id: Base product ID to exclude

        Returns:
            List of potential variant products
        """
        conn = get_db_connection_dict()
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
        Find potential equivalent products from another channel

        Used for auto-detection of cross-channel equivalents.

        Args:
            source_to_match: Target source platform
            exclude_product_id: Product ID to exclude

        Returns:
            List of potential equivalent products
        """
        conn = get_db_connection_dict()
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
