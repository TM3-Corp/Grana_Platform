"""
Repository Layer - Data Access

This layer handles all database queries and returns domain models.
Repositories abstract away SQL details from business logic.

Author: TM3
Date: 2025-10-17
"""
from app.repositories.product_repository import ProductRepository

__all__ = ['ProductRepository']
