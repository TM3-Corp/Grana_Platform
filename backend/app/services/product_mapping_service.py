"""
Product Mapping Service
Detects and manages product variants and cross-channel equivalents

Author: TM3
Date: 2025-10-14
"""
import re
from typing import List, Dict, Optional, Tuple
from difflib import SequenceMatcher
from app.database import get_db_connection


class ProductMappingService:
    """Service for detecting and managing product relationships"""

    def __init__(self):
        # Shopify SKU pattern: [PRODUCT]_U[SIZE][TYPE]
        # Examples: BAKC_U04010 (1 unit), BAKC_U20010 (5 units), BAKC_U64010 (16 units)
        self.shopify_sku_pattern = re.compile(r'^([A-Z]{4})_U(\d{2})(\d{3})$')

        # Known quantity multipliers from SKU codes
        self.quantity_map = {
            '04': 1,    # Individual unit
            '20': 5,    # Display 5 units
            '64': 16,   # Display 16 units
        }

        # Packaging type names
        self.packaging_types = {
            1: 'individual',
            5: 'display_5',
            16: 'display_16',
        }

    def parse_shopify_sku(self, sku: str) -> Optional[Dict]:
        """
        Parse Shopify SKU to extract base product code and quantity

        Args:
            sku: Shopify SKU (e.g., 'BAKC_U04010')

        Returns:
            dict with 'base_code', 'quantity', 'type_code' or None if invalid
        """
        match = self.shopify_sku_pattern.match(sku)
        if not match:
            return None

        base_code = match.group(1)  # e.g., 'BAKC'
        size_code = match.group(2)  # e.g., '04'
        type_code = match.group(3)  # e.g., '010'

        quantity = self.quantity_map.get(size_code)

        return {
            'base_code': base_code,
            'quantity': quantity,
            'size_code': size_code,
            'type_code': type_code,
            'is_base': quantity == 1
        }

    def detect_packaging_variants(self, product_id: int) -> List[Dict]:
        """
        Detect potential packaging variants for a given product

        Args:
            product_id: ID of the base product

        Returns:
            List of potential variant products with confidence scores
        """
        conn = get_db_connection()
        cursor = conn.cursor()

        # Get the base product
        cursor.execute("""
            SELECT id, sku, name, source
            FROM products
            WHERE id = %s AND is_active = true
        """, (product_id,))

        base_product = cursor.fetchone()
        if not base_product:
            cursor.close()
            conn.close()
            return []

        base_id, base_sku, base_name, base_source = base_product

        # Only works for Shopify products with parseable SKUs
        if base_source != 'shopify':
            cursor.close()
            conn.close()
            return []

        parsed_base = self.parse_shopify_sku(base_sku)
        if not parsed_base or not parsed_base['is_base']:
            cursor.close()
            conn.close()
            return []

        # Find products with same base code but different quantities
        base_code = parsed_base['base_code']
        type_code = parsed_base['type_code']

        cursor.execute("""
            SELECT id, sku, name, current_stock, sale_price
            FROM products
            WHERE source = 'shopify'
              AND sku LIKE %s
              AND sku != %s
              AND is_active = true
        """, (f'{base_code}_U%{type_code}', base_sku))

        variants = []
        for row in cursor.fetchall():
            variant_id, variant_sku, variant_name, variant_stock, variant_price = row

            parsed_variant = self.parse_shopify_sku(variant_sku)
            if not parsed_variant or parsed_variant['quantity'] is None:
                continue

            # Calculate confidence based on name similarity
            name_similarity = SequenceMatcher(None, base_name.lower(), variant_name.lower()).ratio()

            variants.append({
                'variant_product_id': variant_id,
                'variant_sku': variant_sku,
                'variant_name': variant_name,
                'quantity_multiplier': parsed_variant['quantity'],
                'packaging_type': self.packaging_types.get(parsed_variant['quantity'], 'unknown'),
                'confidence': round(name_similarity, 2),
                'current_stock': variant_stock,
                'sale_price': float(variant_price) if variant_price else None
            })

        cursor.close()
        conn.close()

        return sorted(variants, key=lambda x: x['quantity_multiplier'])

    def detect_channel_equivalents(self, product_id: int, min_confidence: float = 0.7) -> List[Dict]:
        """
        Detect potential cross-channel equivalents for a product

        Args:
            product_id: ID of the product
            min_confidence: Minimum confidence threshold (0-1)

        Returns:
            List of potential equivalent products from other channels
        """
        conn = get_db_connection()
        cursor = conn.cursor()

        # Get the source product
        cursor.execute("""
            SELECT id, sku, name, source, sale_price
            FROM products
            WHERE id = %s AND is_active = true
        """, (product_id,))

        source_product = cursor.fetchone()
        if not source_product:
            cursor.close()
            conn.close()
            return []

        source_id, source_sku, source_name, source_source, source_price = source_product

        # Determine target source
        if source_source == 'shopify':
            target_source = 'mercadolibre'
        elif source_source == 'mercadolibre':
            target_source = 'shopify'
        else:
            cursor.close()
            conn.close()
            return []

        # Get all products from target source
        cursor.execute("""
            SELECT id, sku, name, sale_price, current_stock
            FROM products
            WHERE source = %s AND is_active = true
        """, (target_source,))

        equivalents = []

        # Extract key terms from source product name
        source_terms = self._extract_key_terms(source_name)

        for row in cursor.fetchall():
            target_id, target_sku, target_name, target_price, target_stock = row

            # Calculate name similarity
            name_similarity = SequenceMatcher(None, source_name.lower(), target_name.lower()).ratio()

            # Calculate term overlap
            target_terms = self._extract_key_terms(target_name)
            common_terms = source_terms.intersection(target_terms)
            term_overlap = len(common_terms) / max(len(source_terms), len(target_terms), 1)

            # Calculate price similarity if both have prices
            price_similarity = 0.5  # Default neutral
            if source_price and target_price:
                price_diff = abs(float(source_price) - float(target_price))
                price_avg = (float(source_price) + float(target_price)) / 2
                price_similarity = max(0, 1 - (price_diff / price_avg))

            # Combined confidence score
            confidence = (
                name_similarity * 0.5 +
                term_overlap * 0.3 +
                price_similarity * 0.2
            )

            if confidence >= min_confidence:
                equivalents.append({
                    'target_product_id': target_id,
                    'target_sku': target_sku,
                    'target_name': target_name,
                    'target_source': target_source,
                    'confidence': round(confidence, 2),
                    'name_similarity': round(name_similarity, 2),
                    'term_overlap': round(term_overlap, 2),
                    'price_similarity': round(price_similarity, 2),
                    'current_stock': target_stock,
                    'sale_price': float(target_price) if target_price else None
                })

        cursor.close()
        conn.close()

        return sorted(equivalents, key=lambda x: x['confidence'], reverse=True)

    def _extract_key_terms(self, text: str) -> set:
        """Extract key terms from product name for comparison"""
        # Remove common stop words and normalize
        stop_words = {'de', 'con', 'la', 'el', 'y', 'un', 'una', 'uds', 'gr', 'grs'}

        # Convert to lowercase and split
        words = re.findall(r'\b[a-záéíóúñ]+\b', text.lower())

        # Filter out stop words and short words
        key_terms = {w for w in words if w not in stop_words and len(w) > 2}

        return key_terms

    def get_consolidated_inventory(self, base_product_id: Optional[int] = None) -> List[Dict]:
        """
        Get consolidated inventory for product families

        Args:
            base_product_id: Optional filter for specific product

        Returns:
            List of consolidated inventory records
        """
        conn = get_db_connection()
        cursor = conn.cursor()

        query = """
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
        """

        if base_product_id:
            query += " WHERE base_product_id = %s"
            cursor.execute(query, (base_product_id,))
        else:
            query += " ORDER BY stock_status DESC, base_sku"
            cursor.execute(query)

        columns = [desc[0] for desc in cursor.description]
        results = []

        for row in cursor.fetchall():
            record = dict(zip(columns, row))
            # Convert Decimal to float for JSON serialization
            for key in ['base_unit_price', 'inventory_value']:
                if record.get(key) is not None:
                    record[key] = float(record[key])
            results.append(record)

        cursor.close()
        conn.close()

        return results

    def get_product_families(self, base_product_id: Optional[int] = None) -> List[Dict]:
        """
        Get complete product families with all variants

        Args:
            base_product_id: Optional filter for specific product family

        Returns:
            List of product family records
        """
        conn = get_db_connection()
        cursor = conn.cursor()

        query = """
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
        """

        if base_product_id:
            query += " WHERE base_product_id = %s"
            cursor.execute(query, (base_product_id,))
        else:
            query += " ORDER BY base_sku, quantity_multiplier"
            cursor.execute(query)

        columns = [desc[0] for desc in cursor.description]
        results = []

        for row in cursor.fetchall():
            record = dict(zip(columns, row))
            # Convert Decimal to float
            for key in ['variant_price', 'base_unit_price', 'variant_unit_price', 'discount_percentage']:
                if record.get(key) is not None:
                    record[key] = float(record[key])
            results.append(record)

        cursor.close()
        conn.close()

        return results

    def create_variant_mapping(
        self,
        base_product_id: int,
        variant_product_id: int,
        quantity_multiplier: int,
        packaging_type: str,
        is_active: bool = True
    ) -> Dict:
        """
        Create a new product variant mapping

        Returns:
            Created variant record or error
        """
        conn = get_db_connection()
        cursor = conn.cursor()

        try:
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

            variant_id = cursor.fetchone()[0]
            conn.commit()

            cursor.close()
            conn.close()

            return {
                'success': True,
                'id': variant_id,
                'base_product_id': base_product_id,
                'variant_product_id': variant_product_id,
                'quantity_multiplier': quantity_multiplier,
                'packaging_type': packaging_type
            }

        except Exception as e:
            conn.rollback()
            cursor.close()
            conn.close()

            return {
                'success': False,
                'error': str(e)
            }

    def create_channel_equivalent(
        self,
        shopify_product_id: int,
        mercadolibre_product_id: int,
        equivalence_confidence: float,
        verified: bool = False,
        notes: Optional[str] = None
    ) -> Dict:
        """
        Create a new cross-channel equivalent mapping

        Returns:
            Created equivalent record or error
        """
        conn = get_db_connection()
        cursor = conn.cursor()

        try:
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

            equivalent_id = cursor.fetchone()[0]
            conn.commit()

            cursor.close()
            conn.close()

            return {
                'success': True,
                'id': equivalent_id,
                'shopify_product_id': shopify_product_id,
                'mercadolibre_product_id': mercadolibre_product_id,
                'equivalence_confidence': equivalence_confidence
            }

        except Exception as e:
            conn.rollback()
            cursor.close()
            conn.close()

            return {
                'success': False,
                'error': str(e)
            }

    def delete_variant_mapping(self, variant_id: int) -> Dict:
        """Delete a product variant mapping"""
        conn = get_db_connection()
        cursor = conn.cursor()

        try:
            cursor.execute("DELETE FROM product_variants WHERE id = %s", (variant_id,))
            conn.commit()

            cursor.close()
            conn.close()

            return {'success': True}

        except Exception as e:
            conn.rollback()
            cursor.close()
            conn.close()

            return {'success': False, 'error': str(e)}

    def delete_channel_equivalent(self, equivalent_id: int) -> Dict:
        """Delete a cross-channel equivalent mapping"""
        conn = get_db_connection()
        cursor = conn.cursor()

        try:
            cursor.execute("DELETE FROM channel_equivalents WHERE id = %s", (equivalent_id,))
            conn.commit()

            cursor.close()
            conn.close()

            return {'success': True}

        except Exception as e:
            conn.rollback()
            cursor.close()
            conn.close()

            return {'success': False, 'error': str(e)}

    def get_channel_equivalents(self) -> List[Dict]:
        """
        Get all channel equivalents with product details

        Returns:
            List of channel equivalent records with joined product data
        """
        conn = get_db_connection()
        cursor = conn.cursor()

        query = """
            SELECT
                ce.id,
                ce.shopify_product_id,
                ce.mercadolibre_product_id,
                ce.equivalence_confidence,
                ce.verified,
                ce.notes,
                -- Shopify product details
                p_shopify.sku as shopify_sku,
                p_shopify.name as shopify_name,
                p_shopify.sale_price as shopify_price,
                p_shopify.current_stock as shopify_stock,
                -- MercadoLibre product details
                p_ml.sku as ml_sku,
                p_ml.name as ml_name,
                p_ml.sale_price as ml_price,
                p_ml.current_stock as ml_stock
            FROM channel_equivalents ce
            INNER JOIN products p_shopify ON ce.shopify_product_id = p_shopify.id
            INNER JOIN products p_ml ON ce.mercadolibre_product_id = p_ml.id
            WHERE p_shopify.is_active = true AND p_ml.is_active = true
            ORDER BY ce.verified DESC, ce.equivalence_confidence DESC
        """

        cursor.execute(query)
        columns = [desc[0] for desc in cursor.description]
        results = []

        for row in cursor.fetchall():
            record = dict(zip(columns, row))
            # Convert Decimal to float for JSON serialization
            for key in ['equivalence_confidence', 'shopify_price', 'ml_price']:
                if record.get(key) is not None:
                    record[key] = float(record[key])
            results.append(record)

        cursor.close()
        conn.close()

        return results
