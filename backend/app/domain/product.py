"""
Product Domain Model

Represents a product entity in the Grana system.
This is the single source of truth for product data structure.

Author: TM3
Date: 2025-10-17
"""
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional
from datetime import datetime
from decimal import Decimal


class Product(BaseModel):
    """
    Product domain model - represents a product in our catalog

    This model matches the database schema and provides type safety
    for all product-related operations.

    Fields:
        id: Internal product ID (primary key)
        external_id: ID from external system (Shopify, MercadoLibre, etc.)
        source: Origin platform (shopify, mercadolibre, walmart, cencosud)
        sku: Stock Keeping Unit (unique identifier)
        name: Product name
        description: Product description (optional)
        category: Product category (optional)
        brand: Product brand (optional)
        unit: Unit description (e.g., "1un", "100gr")

        # Conversion factors (Chilean B2B model)
        units_per_display: How many units in one display
        displays_per_box: How many displays in one box
        boxes_per_pallet: How many boxes in one pallet

        # Display names
        display_name: Name of display packaging
        box_name: Name of box packaging
        pallet_name: Name of pallet packaging

        # Pricing and inventory
        cost_price: Purchase/cost price
        sale_price: Selling price
        current_stock: Current stock level
        min_stock: Minimum stock alert threshold

        # Metadata
        is_active: Whether product is active in catalog
        created_at: When product was created
        updated_at: When product was last updated
    """

    # Primary identification
    id: int = Field(..., description="Internal product ID")
    external_id: Optional[str] = Field(None, description="External system ID")
    source: Optional[str] = Field(None, description="Source platform (shopify, mercadolibre, etc.)")
    sku: str = Field(..., description="Stock Keeping Unit")
    name: str = Field(..., description="Product name")

    # Details
    description: Optional[str] = Field(None, description="Product description")
    category: Optional[str] = Field(None, description="Product category")
    brand: Optional[str] = Field(None, description="Product brand")
    unit: Optional[str] = Field(None, description="Unit description (1un, 100gr, etc.)")

    # Conversion factors (Chilean B2B packaging hierarchy)
    units_per_display: Optional[int] = Field(None, description="Units per display", ge=1)
    displays_per_box: Optional[int] = Field(None, description="Displays per box", ge=1)
    boxes_per_pallet: Optional[int] = Field(None, description="Boxes per pallet", ge=1)

    # Packaging names
    display_name: Optional[str] = Field(None, description="Display packaging name")
    box_name: Optional[str] = Field(None, description="Box packaging name")
    pallet_name: Optional[str] = Field(None, description="Pallet packaging name")

    # Pricing
    cost_price: Optional[Decimal] = Field(None, description="Cost/purchase price", ge=0)
    sale_price: Optional[Decimal] = Field(None, description="Sale price", ge=0)

    # Inventory (allow negative for back-orders/corrections)
    current_stock: int = Field(0, description="Current stock level (can be negative for back-orders)")
    min_stock: int = Field(0, description="Minimum stock threshold", ge=0)

    # Metadata
    is_active: bool = Field(True, description="Whether product is active")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: Optional[datetime] = Field(None, description="Last update timestamp")

    # Pydantic v2 configuration
    model_config = ConfigDict(
        from_attributes=True,  # Allow creation from ORM objects
        json_encoders={
            Decimal: float,  # Convert Decimal to float for JSON
            datetime: lambda v: v.isoformat()  # ISO format for datetime
        }
    )

    # Computed properties
    @property
    def units_per_box(self) -> Optional[int]:
        """Calculate units per box"""
        if self.units_per_display and self.displays_per_box:
            return self.units_per_display * self.displays_per_box
        return None

    @property
    def units_per_pallet(self) -> Optional[int]:
        """Calculate units per pallet"""
        units_box = self.units_per_box
        if units_box and self.boxes_per_pallet:
            return units_box * self.boxes_per_pallet
        return None

    @property
    def has_conversion_data(self) -> bool:
        """Check if product has complete conversion data"""
        return all([
            self.units_per_display is not None,
            self.displays_per_box is not None,
            self.boxes_per_pallet is not None
        ])

    @property
    def is_low_stock(self) -> bool:
        """Check if product stock is below minimum threshold"""
        return self.current_stock <= self.min_stock

    @property
    def is_out_of_stock(self) -> bool:
        """Check if product is out of stock"""
        return self.current_stock <= 0

    def to_dict(self) -> dict:
        """
        Convert to dictionary with computed fields

        Returns dict with all fields plus computed properties
        """
        data = self.model_dump()

        # Add computed properties
        data['units_per_box'] = self.units_per_box
        data['units_per_pallet'] = self.units_per_pallet
        data['has_conversion_data'] = self.has_conversion_data
        data['is_low_stock'] = self.is_low_stock
        data['is_out_of_stock'] = self.is_out_of_stock

        # Convert Decimal to float for JSON compatibility
        if data.get('cost_price'):
            data['cost_price'] = float(data['cost_price'])
        if data.get('sale_price'):
            data['sale_price'] = float(data['sale_price'])

        return data


class ProductCreate(BaseModel):
    """Schema for creating a new product"""
    external_id: Optional[str] = None
    source: Optional[str] = None
    sku: str
    name: str
    description: Optional[str] = None
    category: Optional[str] = None
    brand: Optional[str] = None
    unit: Optional[str] = None
    units_per_display: Optional[int] = None
    displays_per_box: Optional[int] = None
    boxes_per_pallet: Optional[int] = None
    display_name: Optional[str] = None
    box_name: Optional[str] = None
    pallet_name: Optional[str] = None
    cost_price: Optional[Decimal] = None
    sale_price: Optional[Decimal] = None
    current_stock: int = 0
    min_stock: int = 0
    is_active: bool = True


class ProductUpdate(BaseModel):
    """Schema for updating an existing product"""
    external_id: Optional[str] = None
    name: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    brand: Optional[str] = None
    unit: Optional[str] = None
    units_per_display: Optional[int] = None
    displays_per_box: Optional[int] = None
    boxes_per_pallet: Optional[int] = None
    display_name: Optional[str] = None
    box_name: Optional[str] = None
    pallet_name: Optional[str] = None
    cost_price: Optional[Decimal] = None
    sale_price: Optional[Decimal] = None
    current_stock: Optional[int] = None
    min_stock: Optional[int] = None
    is_active: Optional[bool] = None
