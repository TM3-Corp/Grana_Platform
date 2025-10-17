"""
Repository Layer - Data Access

This layer handles all database queries and returns domain models.
Repositories abstract away SQL details from business logic.

Author: TM3
Date: 2025-10-17
"""
from app.repositories.product_repository import ProductRepository
from app.repositories.order_repository import OrderRepository
from app.repositories.product_mapping_repository import ProductMappingRepository
from app.repositories.mercadolibre_repository import MercadoLibreRepository

__all__ = [
    'ProductRepository',
    'OrderRepository',
    'ProductMappingRepository',
    'MercadoLibreRepository'
]
