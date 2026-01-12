# src/schemas/inventory.py
from typing import Optional, List
from decimal import Decimal
from datetime import date
from src.schemas.catalog import ProductVariantOut
from pydantic import BaseModel, Field, ConfigDict


# -------------------------------
# WAREHOUSE SCHEMAS
# -------------------------------
class WarehouseBase(BaseModel):
    name: str = Field(..., max_length=255)
    location: Optional[str] = None
    is_active: Optional[bool] = True


class WarehouseCreate(WarehouseBase):
    pass


class WarehouseUpdate(BaseModel):
    name: Optional[str] = None
    location: Optional[str] = None
    is_active: Optional[bool] = None


class WarehouseOut(WarehouseBase):
    id: int
    inventory_items: List["InventoryOut"] = []

    model_config = ConfigDict(from_attributes=True)


# -------------------------------
# INVENTORY SCHEMAS
# -------------------------------
class InventoryBase(BaseModel):
    product_variant_id: int
    warehouse_id: int
    quantity: Optional[Decimal] = 0
    reserved_quantity: Optional[Decimal] = 0
    created_at: Optional[date] = None


class InventoryCreate(InventoryBase):
    pass


class InventoryUpdate(BaseModel):
    product_variant_id: Optional[int] = None
    warehouse_id: Optional[int] = None
    quantity: Optional[Decimal] = None
    reserved_quantity: Optional[Decimal] = None
    created_at: Optional[date] = None


class InventoryOut(InventoryBase):
    id: int
    product_variant: Optional["ProductVariantOut"] = None
    warehouse: Optional[WarehouseOut] = None

    model_config = ConfigDict(from_attributes=True)


# -------------------------------
# Pydantic v2: rebuild models to resolve forward references
# -------------------------------
WarehouseOut.model_rebuild()
InventoryOut.model_rebuild()
