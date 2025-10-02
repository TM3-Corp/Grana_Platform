"""
Modelos relacionados con órdenes/pedidos
"""
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, DECIMAL, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base


class Order(Base):
    """
    Tabla principal de órdenes - Single Source of Truth
    """
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True)

    # Identificación
    external_id = Column(String(255))
    order_number = Column(String(100), nullable=False, index=True)
    source = Column(String(50), nullable=False, index=True)

    # Relaciones
    customer_id = Column(Integer, ForeignKey("customers.id"), index=True)
    channel_id = Column(Integer, ForeignKey("channels.id"), index=True)

    # Montos
    subtotal = Column(DECIMAL(12, 2))
    tax_amount = Column(DECIMAL(12, 2))
    shipping_cost = Column(DECIMAL(12, 2))
    discount_amount = Column(DECIMAL(12, 2))
    total = Column(DECIMAL(12, 2), nullable=False)

    # Estados
    status = Column(String(50), default="pending", index=True)
    payment_status = Column(String(50))
    fulfillment_status = Column(String(50))

    # Fechas
    order_date = Column(DateTime(timezone=True), nullable=False, index=True)
    payment_date = Column(DateTime(timezone=True))
    shipped_date = Column(DateTime(timezone=True))
    delivered_date = Column(DateTime(timezone=True))

    # Facturación SII
    invoice_number = Column(String(100))
    invoice_type = Column(String(50))
    invoice_date = Column(DateTime(timezone=True))
    invoice_status = Column(String(50))

    # Correcciones manuales ⭐
    is_corrected = Column(Boolean, default=False, index=True)
    correction_reason = Column(Text)
    corrected_by = Column(String(100))
    corrected_at = Column(DateTime(timezone=True))

    # Notas
    customer_notes = Column(Text)
    internal_notes = Column(Text)

    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    customer = relationship("Customer", back_populates="orders")
    channel = relationship("Channel", back_populates="orders")
    items = relationship("OrderItem", back_populates="order", cascade="all, delete-orphan")
    audit_entries = relationship("OrderAudit", back_populates="order", cascade="all, delete-orphan")


class OrderItem(Base):
    """
    Items/productos de cada orden
    """
    __tablename__ = "order_items"

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id", ondelete="CASCADE"), index=True, nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), index=True)

    # Datos del producto al momento de venta
    product_sku = Column(String(100))
    product_name = Column(String(255))

    # Cantidades
    quantity = Column(Integer, nullable=False)
    unit_price = Column(DECIMAL(12, 2), nullable=False)
    subtotal = Column(DECIMAL(12, 2), nullable=False)
    tax_amount = Column(DECIMAL(12, 2))
    total = Column(DECIMAL(12, 2), nullable=False)

    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    order = relationship("Order", back_populates="items")
    product = relationship("Product", back_populates="order_items")


class OrderAudit(Base):
    """
    Auditoría completa de cambios en órdenes ⭐⭐⭐
    LA MÁS IMPORTANTE para Macarena
    """
    __tablename__ = "orders_audit"

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id", ondelete="CASCADE"), index=True, nullable=False)

    # Qué cambió
    field_changed = Column(String(100), nullable=False)
    old_value = Column(Text)
    new_value = Column(Text)

    # Quién y cuándo
    changed_by = Column(String(100), nullable=False, index=True)
    changed_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)

    # Por qué
    reason = Column(Text)

    # Contexto
    change_type = Column(String(50))  # 'manual_correction', 'system_update', 'sync'
    ip_address = Column(String(50))
    user_agent = Column(Text)

    # Relationships
    order = relationship("Order", back_populates="audit_entries")


class ManualCorrection(Base):
    """
    Registro de correcciones manuales
    """
    __tablename__ = "manual_corrections"

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"), index=True)

    correction_type = Column(String(50), nullable=False)
    description = Column(Text, nullable=False)

    corrected_by = Column(String(100), nullable=False)
    corrected_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)

    # Para referencia a audit entries relacionadas
    # audit_entries: lista de IDs (se maneja en aplicación, no FK)