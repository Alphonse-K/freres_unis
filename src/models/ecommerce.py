from sqlalchemy import Column, Integer, ForeignKey, DateTime, Enum, Numeric
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from src.core.database import Base
import enum


class CartStatus(str, enum.Enum):
    OPEN = "open"
    CLOSED = "closed"
    COMPLETED = "completed"


class OrderStatus(str, enum.Enum):
    CREATED = "created"
    PENDING = "pending" 
    COMPLETED = "completed" 


class Cart(Base):
    __tablename__ = "carts"

    id = Column(Integer, primary_key=True)

    client_id = Column(Integer, ForeignKey("clients.id"), nullable=True)
    status = Column(Enum(CartStatus), nullable=False, default=CartStatus.OPEN)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    client = relationship("Client", back_populates="carts")

    items = relationship(
        "CartItem",
        back_populates="cart",
        cascade="all, delete-orphan"
    )


class CartItem(Base):
    __tablename__ = "cart_items"

    id = Column(Integer, primary_key=True)

    cart_id = Column(Integer, ForeignKey("carts.id"), nullable=False)
    product_variant_id = Column(Integer, ForeignKey("product_variants.id"), nullable=False)

    qty = Column(Numeric(12, 2), nullable=False)

    cart = relationship("Cart", back_populates="items")
    product_variant = relationship("ProductVariant")


class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True)

    client_id = Column(Integer, ForeignKey("clients.id"), nullable=False)

    status = Column(Enum(OrderStatus), nullable=False, default=OrderStatus.CREATED)

    subtotal = Column(Numeric(12, 2), nullable=False)
    shipping_fee = Column(Numeric(12, 2), default=0)
    total_amount = Column(Numeric(12, 2), nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    client = relationship("Client", back_populates="orders")

    items = relationship(
        "OrderItem",
        back_populates="order",
        cascade="all, delete-orphan"
    )


class OrderItem(Base):
    __tablename__ = "order_items"

    id = Column(Integer, primary_key=True)

    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False)
    product_variant_id = Column(Integer, ForeignKey("product_variants.id"), nullable=False)

    qty = Column(Numeric(12, 2), nullable=False)
    returned_qty = Column(Numeric(12, 2), default=0)
    unit_price = Column(Numeric(12, 2), nullable=False)

    order = relationship("Order", back_populates="items")
    product_variant = relationship("ProductVariant")
