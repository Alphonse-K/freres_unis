# src/schemas/cart.py
from pydantic import BaseModel, ConfigDict
from typing import Optional, List
from decimal import Decimal
from datetime import datetime
from src.schemas.common import SimpleWarehouse


class CartItemBase(BaseModel):
    product_variant_id: int
    qty: Decimal


class CartItemCreate(CartItemBase):
    pass


class CartItemOut(CartItemBase):
    id: int
    model_config = ConfigDict(from_attributes=True)


class CartBase(BaseModel):
    client_id: Optional[int] = None
    status: Optional[str] = "open"


class CartCreate(CartBase):
    pass


class CartOut(CartBase):
    id: int
    subtotal: Decimal
    tax: Decimal
    shipping_fee: Decimal
    total: Decimal
    created_at: datetime
    items: List[CartItemOut] = []
    model_config = ConfigDict(from_attributes=True)


class OrderItemBase(BaseModel):
    product_variant_id: int
    qty: Decimal
    unit_price: Decimal


class OrderItemCreate(OrderItemBase):
    pass


class OrderItemOut(OrderItemBase):
    id: int
    model_config = ConfigDict(from_attributes=True)


class OrderBeneficiaryInfoCreate(BaseModel):
    first_name: str | None = None
    last_name: str | None = None
    phone: str | None = None


class OrderBeneficiaryInfoOut(BaseModel):
    first_name: str | None = None
    last_name: str | None = None
    phone: str | None = None
    model_config = ConfigDict(from_attributes=True)


class OrderBase(BaseModel):
    client_id: int
    status: Optional[str] = "created"
    subtotal: Decimal
    shipping_fee: Optional[Decimal] = 0
    total_amount: Decimal


class OrderOut(OrderBase):
    id: int
    created_at: datetime
    order_code: str
    warehouse: SimpleWarehouse
    items: List[OrderItemOut] = []
    beneficiary: OrderBeneficiaryInfoOut | None = None
    model_config = ConfigDict(from_attributes=True)
