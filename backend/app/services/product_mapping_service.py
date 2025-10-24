"""
Product Mapping Service
Detects and manages product variants and cross-channel equivalents

Author: TM3
Date: 2025-10-14
Updated: 2025-10-17 (refactor: use repository pattern + catalog module)
"""
import re
from typing import List, Dict, Optional
from difflib import SequenceMatcher
from app.repositories import ProductRepository, ProductMappingRepository
from app.domain import catalog


class ProductMappingService:
    """
    Service for detecting and managing product relationships

    This service handles:
    - Product variant detection and management
    - Cross-channel equivalent detection
    - SKU parsing and pattern matching
    - Confidence scoring algorithms
    """

    def __init__(self):
        # Initialize repositories
        self.product_repo = ProductRepository()
        self.mapping_repo = ProductMappingRepository()

        # Shopify SKU pattern: [PRODUCT]_U[SIZE][TYPE]
        # Examples: BAKC_U04010 (1 unit), BAKC_U20010 (5 units), BAKC_U64010 (16 units)
        self.shopify_sku_pattern = re.compile(r'^([A-Z]{4})_U(\d{2})(\d{3})$')

        # Known quantity multipliers from SKU codes
        self.quantity_map = {
            '04': 1,    # Individual unit
            '20': 5,    # Display 5 units
            '64': 16,   # Display 16 units
            '25': 7,    # Display 7 units
            '15': 5,    # Display 5 units (alt)
            '54': 18,   # Display 18 units
        }

        # Packaging type names
        self.packaging_types = {
            1: 'individual',
            5: 'display_5',
            7: 'display_7',
            16: 'display_16',
            18: 'display_18',
        }

    # ========================================
    # SKU Parsing (Business Logic)
    # ========================================

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

    # ========================================
    # Variant Detection (Business Logic + Repository)
    # ========================================

    def detect_packaging_variants(self, product_id: int) -> List[Dict]:
        """
        Detect potential packaging variants for a given product

        Uses catalog module for official product data and repository for database queries.

        Args:
            product_id: ID of the base product

        Returns:
            List of potential variant products with confidence scores
        """
        # Get the base product from database
        base_product = self.product_repo.find_by_id(product_id)
        if not base_product or not base_product.is_active:
            return []

        # Only works for Shopify products with parseable SKUs
        if base_product.source != 'shopify':
            return []

        parsed_base = self.parse_shopify_sku(base_product.sku)
        if not parsed_base or not parsed_base['is_base']:
            return []

        # Use repository to find potential variants
        potential_variants = self.mapping_repo.find_potential_variants_by_sku_pattern(
            base_sku=base_product.sku,
            base_product_id=product_id
        )

        variants = []
        for variant_data in potential_variants:
            # Parse variant SKU
            parsed_variant = self.parse_shopify_sku(variant_data['sku'])
            if not parsed_variant or parsed_variant['quantity'] is None:
                continue

            # Calculate confidence based on name similarity
            name_similarity = SequenceMatcher(
                None,
                base_product.name.lower(),
                variant_data['name'].lower()
            ).ratio()

            # Check if this variant exists in official catalog
            catalog_product = catalog.get_product_by_sku(variant_data['sku'])
            if catalog_product:
                # Boost confidence for catalog products
                name_similarity = min(1.0, name_similarity + 0.1)

            variants.append({
                'variant_product_id': variant_data['id'],
                'variant_sku': variant_data['sku'],
                'variant_name': variant_data['name'],
                'quantity_multiplier': parsed_variant['quantity'],
                'packaging_type': self.packaging_types.get(parsed_variant['quantity'], 'unknown'),
                'confidence': round(name_similarity, 2),
                'current_stock': variant_data['current_stock'],
                'sale_price': float(variant_data['sale_price']) if variant_data['sale_price'] else None,
                'in_catalog': catalog_product is not None
            })

        return sorted(variants, key=lambda x: x['quantity_multiplier'])

    def detect_channel_equivalents(
        self,
        product_id: int,
        min_confidence: float = 0.7
    ) -> List[Dict]:
        """
        Detect potential cross-channel equivalents for a product

        Args:
            product_id: ID of the product
            min_confidence: Minimum confidence threshold (0-1)

        Returns:
            List of potential equivalent products from other channels
        """
        # Get the source product from database
        source_product = self.product_repo.find_by_id(product_id)
        if not source_product or not source_product.is_active:
            return []

        # Determine target source
        if source_product.source == 'shopify':
            target_source = 'mercadolibre'
        elif source_product.source == 'mercadolibre':
            target_source = 'shopify'
        else:
            return []

        # Get potential equivalents from repository
        potential_equivalents = self.mapping_repo.find_potential_equivalents_by_source(
            source_to_match=target_source,
            exclude_product_id=product_id
        )

        equivalents = []

        # Extract key terms from source product name
        source_terms = self._extract_key_terms(source_product.name)

        for target_data in potential_equivalents:
            # Calculate name similarity
            name_similarity = SequenceMatcher(
                None,
                source_product.name.lower(),
                target_data['name'].lower()
            ).ratio()

            # Calculate term overlap
            target_terms = self._extract_key_terms(target_data['name'])
            common_terms = source_terms.intersection(target_terms)
            term_overlap = len(common_terms) / max(len(source_terms), len(target_terms), 1)

            # Calculate price similarity if both have prices
            price_similarity = 0.5  # Default neutral
            if source_product.sale_price and target_data['sale_price']:
                price_diff = abs(float(source_product.sale_price) - float(target_data['sale_price']))
                price_avg = (float(source_product.sale_price) + float(target_data['sale_price'])) / 2
                price_similarity = max(0, 1 - (price_diff / price_avg))

            # Combined confidence score
            confidence = (
                name_similarity * 0.5 +
                term_overlap * 0.3 +
                price_similarity * 0.2
            )

            if confidence >= min_confidence:
                equivalents.append({
                    'target_product_id': target_data['id'],
                    'target_sku': target_data['sku'],
                    'target_name': target_data['name'],
                    'target_source': target_data['source'],
                    'confidence': round(confidence, 2),
                    'name_similarity': round(name_similarity, 2),
                    'term_overlap': round(term_overlap, 2),
                    'price_similarity': round(price_similarity, 2),
                    'current_stock': target_data['current_stock'],
                    'sale_price': float(target_data['sale_price']) if target_data['sale_price'] else None
                })

        return sorted(equivalents, key=lambda x: x['confidence'], reverse=True)

    def _extract_key_terms(self, text: str) -> set:
        """
        Extract key terms from product name for comparison

        Args:
            text: Product name text

        Returns:
            Set of key terms (normalized, filtered)
        """
        # Remove common stop words and normalize
        stop_words = {'de', 'con', 'la', 'el', 'y', 'un', 'una', 'uds', 'gr', 'grs', 'display', 'pack'}

        # Convert to lowercase and split
        words = re.findall(r'\b[a-záéíóúñ]+\b', text.lower())

        # Filter out stop words and short words
        key_terms = {w for w in words if w not in stop_words and len(w) > 2}

        return key_terms

    # ========================================
    # Consolidated Views (Repository Delegation)
    # ========================================

    def get_consolidated_inventory(self, base_product_id: Optional[int] = None) -> List[Dict]:
        """
        Get consolidated inventory for product families

        Args:
            base_product_id: Optional filter for specific product

        Returns:
            List of consolidated inventory records
        """
        return self.mapping_repo.find_consolidated_inventory(base_product_id)

    def get_product_families(self, base_product_id: Optional[int] = None) -> List[Dict]:
        """
        Get complete product families with all variants

        Args:
            base_product_id: Optional filter for specific product family

        Returns:
            List of product family records
        """
        return self.mapping_repo.find_product_families(base_product_id)

    def get_channel_equivalents(self) -> List[Dict]:
        """
        Get all channel equivalents with product details

        Returns:
            List of channel equivalent records with joined product data
        """
        return self.mapping_repo.find_channel_equivalents()

    # ========================================
    # CRUD Operations (Repository Delegation)
    # ========================================

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

        Args:
            base_product_id: ID of base product
            variant_product_id: ID of variant product
            quantity_multiplier: Number of base units in variant
            packaging_type: Type of packaging
            is_active: Whether mapping is active

        Returns:
            Created variant record or error
        """
        # Validate products exist
        base_product = self.product_repo.find_by_id(base_product_id)
        variant_product = self.product_repo.find_by_id(variant_product_id)

        if not base_product:
            return {
                'success': False,
                'error': f'Base product {base_product_id} not found'
            }

        if not variant_product:
            return {
                'success': False,
                'error': f'Variant product {variant_product_id} not found'
            }

        # Delegate to repository
        return self.mapping_repo.create_variant_mapping(
            base_product_id=base_product_id,
            variant_product_id=variant_product_id,
            quantity_multiplier=quantity_multiplier,
            packaging_type=packaging_type,
            is_active=is_active
        )

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

        Args:
            shopify_product_id: Shopify product ID
            mercadolibre_product_id: MercadoLibre product ID
            equivalence_confidence: Confidence score (0-1)
            verified: Whether manually verified
            notes: Optional notes

        Returns:
            Created equivalent record or error
        """
        # Validate products exist and have correct sources
        shopify_product = self.product_repo.find_by_id(shopify_product_id)
        ml_product = self.product_repo.find_by_id(mercadolibre_product_id)

        if not shopify_product:
            return {
                'success': False,
                'error': f'Shopify product {shopify_product_id} not found'
            }

        if not ml_product:
            return {
                'success': False,
                'error': f'MercadoLibre product {mercadolibre_product_id} not found'
            }

        if shopify_product.source != 'shopify':
            return {
                'success': False,
                'error': f'Product {shopify_product_id} is not a Shopify product'
            }

        if ml_product.source != 'mercadolibre':
            return {
                'success': False,
                'error': f'Product {mercadolibre_product_id} is not a MercadoLibre product'
            }

        # Delegate to repository
        return self.mapping_repo.create_channel_equivalent(
            shopify_product_id=shopify_product_id,
            mercadolibre_product_id=mercadolibre_product_id,
            equivalence_confidence=equivalence_confidence,
            verified=verified,
            notes=notes
        )

    def delete_variant_mapping(self, variant_id: int) -> Dict:
        """
        Delete a product variant mapping

        Args:
            variant_id: ID of the variant mapping

        Returns:
            Result dict with success status
        """
        return self.mapping_repo.delete_variant_mapping(variant_id)

    def delete_channel_equivalent(self, equivalent_id: int) -> Dict:
        """
        Delete a cross-channel equivalent mapping

        Args:
            equivalent_id: ID of the channel equivalent

        Returns:
            Result dict with success status
        """
        return self.mapping_repo.delete_channel_equivalent(equivalent_id)

    def get_hierarchical_families(self) -> List[Dict]:
        """
        Get product families in hierarchical structure

        Returns products grouped by:
        - Categoria (Family): GRANOLAS, BARRAS, CRACKERS, KEEPERS
        - Subfamilia (Product variant): e.g., "Granola Low Carb Almendras"
        - Formato (Format): e.g., "260g", "X1", "X5"

        Returns:
            List of family dictionaries with nested structure
        """
        families = self.product_repo.get_hierarchical_families()
        return families
