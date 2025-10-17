"""
Unit tests for ProductRepository

These tests validate repository logic without requiring a database connection.

Author: TM3
Date: 2025-10-17
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
from decimal import Decimal

from app.repositories.product_repository import ProductRepository
from app.domain.product import Product


class TestProductRepository:
    """Test ProductRepository methods"""

    @patch('app.repositories.product_repository.get_db_connection_dict')
    def test_find_by_id_returns_product(self, mock_get_conn):
        """Test find_by_id returns a Product domain model"""
        # Arrange: Mock database connection
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_get_conn.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor

        # Mock database row
        mock_cursor.fetchone.return_value = {
            'id': 1,
            'external_id': 'shopify_123',
            'source': 'shopify',
            'sku': 'BAKC_U04010',
            'name': 'Barra Keto Cacao',
            'description': 'Delicious keto bar',
            'category': 'BARRAS',
            'brand': 'Grana',
            'unit': '1un',
            'units_per_display': 12,
            'displays_per_box': 12,
            'boxes_per_pallet': 20,
            'display_name': 'Display',
            'box_name': 'Box',
            'pallet_name': 'Pallet',
            'cost_price': Decimal('1000.00'),
            'sale_price': Decimal('1500.00'),
            'current_stock': 100,
            'min_stock': 10,
            'is_active': True,
            'created_at': datetime.now(),
            'updated_at': None
        }

        # Act: Call repository method
        repo = ProductRepository()
        product = repo.find_by_id(1)

        # Assert: Verify result
        assert product is not None
        assert isinstance(product, Product)
        assert product.id == 1
        assert product.sku == 'BAKC_U04010'
        assert product.name == 'Barra Keto Cacao'
        assert product.units_per_box == 144  # 12 * 12
        assert product.units_per_pallet == 2880  # 144 * 20

        # Verify database was called correctly
        mock_cursor.execute.assert_called_once()
        mock_cursor.close.assert_called_once()
        mock_conn.close.assert_called_once()

    @patch('app.repositories.product_repository.get_db_connection_dict')
    def test_find_by_id_returns_none_when_not_found(self, mock_get_conn):
        """Test find_by_id returns None when product doesn't exist"""
        # Arrange
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_get_conn.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.fetchone.return_value = None

        # Act
        repo = ProductRepository()
        product = repo.find_by_id(999)

        # Assert
        assert product is None

    @patch('app.repositories.product_repository.get_db_connection_dict')
    def test_find_all_returns_products_and_count(self, mock_get_conn):
        """Test find_all returns list of products and total count"""
        # Arrange
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_get_conn.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor

        # Mock count query
        mock_cursor.fetchone.side_effect = [
            {'total': 2},  # Count query
        ]

        # Mock products query
        mock_cursor.fetchall.return_value = [
            {
                'id': 1,
                'external_id': 'shopify_123',
                'source': 'shopify',
                'sku': 'BAKC_U04010',
                'name': 'Barra Keto Cacao',
                'description': None,
                'category': 'BARRAS',
                'brand': None,
                'unit': '1un',
                'units_per_display': 12,
                'displays_per_box': 12,
                'boxes_per_pallet': 20,
                'display_name': None,
                'box_name': None,
                'pallet_name': None,
                'cost_price': None,
                'sale_price': Decimal('1500.00'),
                'current_stock': 100,
                'min_stock': 10,
                'is_active': True,
                'created_at': datetime.now(),
                'updated_at': None
            },
            {
                'id': 2,
                'external_id': 'shopify_124',
                'source': 'shopify',
                'sku': 'BAKC_U20010',
                'name': 'Barra Keto Cacao Display 5',
                'description': None,
                'category': 'BARRAS',
                'brand': None,
                'unit': '5un',
                'units_per_display': None,
                'displays_per_box': None,
                'boxes_per_pallet': None,
                'display_name': None,
                'box_name': None,
                'pallet_name': None,
                'cost_price': None,
                'sale_price': Decimal('7000.00'),
                'current_stock': 20,
                'min_stock': 5,
                'is_active': True,
                'created_at': datetime.now(),
                'updated_at': None
            }
        ]

        # Act
        repo = ProductRepository()
        products, total = repo.find_all(source='shopify', limit=10)

        # Assert
        assert len(products) == 2
        assert total == 2
        assert all(isinstance(p, Product) for p in products)
        assert products[0].sku == 'BAKC_U04010'
        assert products[1].sku == 'BAKC_U20010'

    @patch('app.repositories.product_repository.get_db_connection_dict')
    def test_count_by_filters(self, mock_get_conn):
        """Test count_by_filters returns correct count"""
        # Arrange
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_get_conn.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.fetchone.return_value = {'total': 42}

        # Act
        repo = ProductRepository()
        count = repo.count_by_filters(source='shopify', is_active=True)

        # Assert
        assert count == 42

    def test_product_domain_model_computed_properties(self):
        """Test Product domain model computed properties work correctly"""
        # Arrange
        product = Product(
            id=1,
            source='shopify',
            sku='BAKC_U04010',
            name='Barra Keto Cacao',
            units_per_display=12,
            displays_per_box=12,
            boxes_per_pallet=20,
            current_stock=100,
            min_stock=10,
            is_active=True,
            created_at=datetime.now()
        )

        # Assert computed properties
        assert product.units_per_box == 144
        assert product.units_per_pallet == 2880
        assert product.has_conversion_data is True
        assert product.is_low_stock is False
        assert product.is_out_of_stock is False

    def test_product_domain_model_low_stock(self):
        """Test Product domain model detects low stock correctly"""
        # Arrange
        product = Product(
            id=1,
            source='shopify',
            sku='BAKC_U04010',
            name='Barra Keto Cacao',
            current_stock=5,
            min_stock=10,
            is_active=True,
            created_at=datetime.now()
        )

        # Assert
        assert product.is_low_stock is True
        assert product.is_out_of_stock is False

    def test_product_domain_model_out_of_stock(self):
        """Test Product domain model detects out of stock correctly"""
        # Arrange
        product = Product(
            id=1,
            source='shopify',
            sku='BAKC_U04010',
            name='Barra Keto Cacao',
            current_stock=0,
            min_stock=10,
            is_active=True,
            created_at=datetime.now()
        )

        # Assert
        assert product.is_low_stock is True
        assert product.is_out_of_stock is True
