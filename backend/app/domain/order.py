"""
Order Domain Models

Represents order-related entities in the Grana system.
These are the single source of truth for order data structure.

Author: TM3
Date: 2025-10-17
"""
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List
from datetime import datetime, date
from decimal import Decimal


class OrderItem(BaseModel):
    """
    Order Item domain model - represents a line item in an order

    Fields:
        id: Internal order item ID
        order_id: Parent order ID
        product_id: Reference to product catalog
        product_sku: Product SKU at time of order
        product_name: Product name at time of order
        quantity: Number of units ordered
        unit_price: Price per unit
        subtotal: Subtotal before tax
        tax_amount: Tax amount for this line
        total: Total for this line item

        # From product catalog (optional)
        product_name_from_catalog: Current product name
        unit: Product unit description
        category: Product category
        brand: Product brand
        units_per_display: Conversion factor
        displays_per_box: Conversion factor
        boxes_per_pallet: Conversion factor
    """

    id: int = Field(..., description="Order item ID")
    order_id: int = Field(..., description="Parent order ID")
    product_id: Optional[int] = Field(None, description="Product catalog ID")
    product_sku: str = Field(..., description="Product SKU")
    product_name: str = Field(..., description="Product name at order time")
    quantity: int = Field(..., description="Quantity ordered", ge=1)
    unit_price: Decimal = Field(..., description="Price per unit", ge=0)
    subtotal: Decimal = Field(..., description="Subtotal before tax", ge=0)
    tax_amount: Decimal = Field(Decimal('0'), description="Tax amount", ge=0)
    total: Decimal = Field(..., description="Total for line item", ge=0)

    # From product catalog (optional, from JOIN)
    product_name_from_catalog: Optional[str] = Field(None, description="Current product name from catalog")
    unit: Optional[str] = Field(None, description="Product unit")
    category: Optional[str] = Field(None, description="Product category")
    brand: Optional[str] = Field(None, description="Product brand")
    units_per_display: Optional[int] = Field(None, description="Units per display")
    displays_per_box: Optional[int] = Field(None, description="Displays per box")
    boxes_per_pallet: Optional[int] = Field(None, description="Boxes per pallet")

    model_config = ConfigDict(
        from_attributes=True,
        json_encoders={
            Decimal: float,
            datetime: lambda v: v.isoformat()
        }
    )

    def to_dict(self) -> dict:
        """Convert to dictionary with Decimal to float conversion"""
        data = self.model_dump()

        # Convert Decimal fields to float
        for field in ['unit_price', 'subtotal', 'tax_amount', 'total']:
            if data.get(field) is not None:
                data[field] = float(data[field])

        return data


class Customer(BaseModel):
    """
    Customer domain model (lightweight for order context)

    This is a simplified customer model used in order queries.
    Full customer management will have its own module.
    """

    id: int = Field(..., description="Customer ID")
    name: str = Field(..., description="Customer name")
    email: Optional[str] = Field(None, description="Customer email")
    phone: Optional[str] = Field(None, description="Customer phone")
    address: Optional[str] = Field(None, description="Customer address")
    city: Optional[str] = Field(None, description="Customer city")

    model_config = ConfigDict(from_attributes=True)


class Channel(BaseModel):
    """
    Channel domain model (lightweight for order context)

    Represents sales channels (B2B, B2C, Marketplace, etc.)
    """

    id: int = Field(..., description="Channel ID")
    code: str = Field(..., description="Channel code")
    name: str = Field(..., description="Channel name")
    type: Optional[str] = Field(None, description="Channel type (B2B, B2C, etc.)")

    model_config = ConfigDict(from_attributes=True)


class Order(BaseModel):
    """
    Order domain model - represents a customer order

    This model matches the database schema and provides type safety
    for all order-related operations.

    Fields:
        id: Internal order ID (primary key)
        external_id: ID from external system (Shopify, MercadoLibre, etc.)
        order_number: Human-readable order number
        source: Origin platform (shopify, mercadolibre, walmart, cencosud)

        # References
        customer_id: Reference to customer
        channel_id: Reference to sales channel

        # Financial information
        subtotal: Order subtotal before tax/shipping
        tax_amount: Total tax amount
        shipping_cost: Shipping/delivery cost
        discount_amount: Total discounts applied
        total: Final order total

        # Status tracking
        status: Order status (pending, processing, completed, cancelled)
        payment_status: Payment status (pending, paid, refunded, etc.)
        fulfillment_status: Fulfillment status (unfulfilled, partial, fulfilled)

        # Dates and metadata
        order_date: Date order was placed
        customer_notes: Notes from customer
        created_at: When order was created in system
        updated_at: When order was last updated

        # Related data (optional, from JOINs)
        customer_name: Customer name (from JOIN)
        customer_email: Customer email (from JOIN)
        customer_phone: Customer phone (from JOIN)
        customer_address: Customer address (from JOIN)
        customer_city: Customer city (from JOIN)
        channel_name: Channel name (from JOIN)
        channel_code: Channel code (from JOIN)
        channel_type: Channel type (from JOIN)

        # Order items (one-to-many relationship)
        items: List of order items
    """

    # Primary identification
    id: int = Field(..., description="Internal order ID")
    external_id: Optional[str] = Field(None, description="External system ID")
    order_number: str = Field(..., description="Order number")
    source: str = Field(..., description="Source platform (shopify, mercadolibre, etc.)")

    # References
    customer_id: Optional[int] = Field(None, description="Customer ID")
    channel_id: Optional[int] = Field(None, description="Channel ID")

    # Financial information
    subtotal: Decimal = Field(..., description="Subtotal before tax/shipping", ge=0)
    tax_amount: Decimal = Field(Decimal('0'), description="Tax amount", ge=0)
    shipping_cost: Decimal = Field(Decimal('0'), description="Shipping cost", ge=0)
    discount_amount: Decimal = Field(Decimal('0'), description="Discount amount", ge=0)
    total: Decimal = Field(..., description="Total order amount", ge=0)

    # Status tracking
    status: str = Field(..., description="Order status")
    payment_status: Optional[str] = Field(None, description="Payment status")
    fulfillment_status: Optional[str] = Field(None, description="Fulfillment status")

    # Dates and metadata
    order_date: date = Field(..., description="Order date")
    customer_notes: Optional[str] = Field(None, description="Customer notes")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: Optional[datetime] = Field(None, description="Last update timestamp")

    # Related data (from JOINs - optional)
    customer_name: Optional[str] = Field(None, description="Customer name (from JOIN)")
    customer_email: Optional[str] = Field(None, description="Customer email (from JOIN)")
    customer_phone: Optional[str] = Field(None, description="Customer phone (from JOIN)")
    customer_address: Optional[str] = Field(None, description="Customer address (from JOIN)")
    customer_city: Optional[str] = Field(None, description="Customer city (from JOIN)")
    channel_name: Optional[str] = Field(None, description="Channel name (from JOIN)")
    channel_code: Optional[str] = Field(None, description="Channel code (from JOIN)")
    channel_type: Optional[str] = Field(None, description="Channel type (from JOIN)")

    # Order items (one-to-many)
    items: List[OrderItem] = Field(default_factory=list, description="Order items")

    # Pydantic v2 configuration
    model_config = ConfigDict(
        from_attributes=True,
        json_encoders={
            Decimal: float,
            datetime: lambda v: v.isoformat(),
            date: lambda v: v.isoformat()
        }
    )

    # Computed properties
    @property
    def item_count(self) -> int:
        """Total number of items in order"""
        return len(self.items)

    @property
    def total_quantity(self) -> int:
        """Total quantity of all items"""
        return sum(item.quantity for item in self.items)

    @property
    def is_paid(self) -> bool:
        """Check if order is paid"""
        return self.payment_status == 'paid'

    @property
    def is_fulfilled(self) -> bool:
        """Check if order is fulfilled"""
        return self.fulfillment_status == 'fulfilled'

    @property
    def is_completed(self) -> bool:
        """Check if order is completed (paid and fulfilled)"""
        return self.is_paid and self.is_fulfilled

    def to_dict(self) -> dict:
        """
        Convert to dictionary with computed fields

        Returns dict with all fields plus computed properties
        """
        data = self.model_dump()

        # Add computed properties
        data['item_count'] = self.item_count
        data['total_quantity'] = self.total_quantity
        data['is_paid'] = self.is_paid
        data['is_fulfilled'] = self.is_fulfilled
        data['is_completed'] = self.is_completed

        # Convert Decimal to float for JSON compatibility
        for field in ['subtotal', 'tax_amount', 'shipping_cost', 'discount_amount', 'total']:
            if data.get(field) is not None:
                data[field] = float(data[field])

        # Convert dates to ISO format
        if data.get('order_date'):
            data['order_date'] = data['order_date'].isoformat() if isinstance(data['order_date'], date) else data['order_date']
        if data.get('created_at'):
            data['created_at'] = data['created_at'].isoformat() if isinstance(data['created_at'], datetime) else data['created_at']
        if data.get('updated_at'):
            data['updated_at'] = data['updated_at'].isoformat() if isinstance(data['updated_at'], datetime) else data['updated_at']

        # Convert items to dicts
        data['items'] = [item.to_dict() for item in self.items]

        return data


class OrderCreate(BaseModel):
    """Schema for creating a new order"""
    external_id: Optional[str] = None
    order_number: str
    source: str
    customer_id: Optional[int] = None
    channel_id: Optional[int] = None
    subtotal: Decimal
    tax_amount: Decimal = Decimal('0')
    shipping_cost: Decimal = Decimal('0')
    discount_amount: Decimal = Decimal('0')
    total: Decimal
    status: str = "pending"
    payment_status: Optional[str] = "pending"
    fulfillment_status: Optional[str] = "unfulfilled"
    order_date: date
    customer_notes: Optional[str] = None


class OrderUpdate(BaseModel):
    """Schema for updating an existing order"""
    status: Optional[str] = None
    payment_status: Optional[str] = None
    fulfillment_status: Optional[str] = None
    customer_notes: Optional[str] = None
    subtotal: Optional[Decimal] = None
    tax_amount: Optional[Decimal] = None
    shipping_cost: Optional[Decimal] = None
    discount_amount: Optional[Decimal] = None
    total: Optional[Decimal] = None
