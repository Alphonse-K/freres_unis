# src/schemas/cart.py
from pydantic import BaseModel, ConfigDict
from typing import Optional, List
from decimal import Decimal
from datetime import datetime


# --- CART ITEM ---
class CartItemBase(BaseModel):
    product_variant_id: int
    qty: Decimal


class CartItemCreate(CartItemBase):
    pass


class CartItemOut(CartItemBase):
    id: int
    model_config = ConfigDict(from_attributes=True)

# --- CART ---
class CartBase(BaseModel):
    client_id: Optional[int] = None
    status: Optional[str] = "open"


class CartCreate(CartBase):
    pass


class CartOut(CartBase):
    id: int
    created_at: datetime
    items: List[CartItemOut] = []

    model_config = ConfigDict(from_attributes=True)


# --- ORDER ITEM ---
class OrderItemBase(BaseModel):
    product_variant_id: int
    qty: Decimal
    unit_price: Decimal


class OrderItemCreate(OrderItemBase):
    pass


class OrderItemOut(OrderItemBase):
    id: int

    model_config = ConfigDict(from_attributes=True)


# --- ORDER ---
class OrderBase(BaseModel):
    client_id: int
    status: Optional[str] = "created"
    subtotal: Decimal
    shipping_fee: Optional[Decimal] = 0
    total_amount: Decimal


class OrderCreate(OrderBase):
    items: List[OrderItemCreate]


class OrderOut(OrderBase):
    id: int
    created_at: datetime
    items: List[OrderItemOut] = []

    model_config = ConfigDict(from_attributes=True)
