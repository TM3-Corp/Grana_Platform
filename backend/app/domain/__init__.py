"""
Domain Layer - Business Entities

This layer contains Pydantic models representing business entities.
These models enforce type safety and validation across the application.

Author: TM3
Date: 2025-10-17
"""
from app.domain.product import Product

__all__ = ['Product']
