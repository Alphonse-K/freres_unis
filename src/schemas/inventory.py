# src/schemas/inventory.py
from typing import Optional, List
from decimal import Decimal
from datetime import date, datetime
from pydantic import BaseModel, Field, ConfigDict

from src.schemas.catalog import ProductVariantOut


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
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


# -------------------------------
# INVENTORY SCHEMAS
# -------------------------------
class InventoryBase(BaseModel):
    product_variant_id: int
    warehouse_id: int
    quantity: Optional[Decimal] = Decimal('0')
    reserved_quantity: Optional[Decimal] = Decimal('0')


class InventoryCreate(InventoryBase):
    pass


class InventoryUpdate(BaseModel):
    product_variant_id: Optional[int] = None
    warehouse_id: Optional[int] = None
    quantity: Optional[Decimal] = None
    reserved_quantity: Optional[Decimal] = None


class InventoryOut(InventoryBase):
    id: int
    available_quantity: Decimal
    product_variant: Optional[ProductVariantOut] = None
    warehouse: Optional[WarehouseOut] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


# -------------------------------
# STOCK OPERATION SCHEMAS
# -------------------------------
class StockIncreaseRequest(BaseModel):
    warehouse_id: int
    product_variant_id: int
    quantity: Decimal = Field(..., gt=0)
    source: Optional[str] = "manual"


class StockDecreaseRequest(BaseModel):
    warehouse_id: int
    product_variant_id: int
    quantity: Decimal = Field(..., gt=0)
    reserve_first: Optional[bool] = False


class StockReserveRequest(BaseModel):
    warehouse_id: int
    product_variant_id: int
    quantity: Decimal = Field(..., gt=0)
    reference_type: Optional[str] = "sale"
    reference_id: Optional[int] = None


class StockReleaseRequest(BaseModel):
    warehouse_id: int
    product_variant_id: int
    quantity: Decimal = Field(..., gt=0)


class StockTransferRequest(BaseModel):
    from_warehouse_id: int
    to_warehouse_id: int
    product_variant_id: int
    quantity: Decimal = Field(..., gt=0)
    notes: Optional[str] = None


class StockCheckRequest(BaseModel):
    warehouse_id: int
    product_variant_id: int
    quantity: Decimal = Field(..., gt=0)


class StockCheckResponse(BaseModel):
    is_available: bool
    available: Decimal
    required: Decimal
    shortage: Decimal
    inventory_item_id: Optional[int] = None
    product_variant_id: int
    warehouse_id: int


# -------------------------------
# INVENTORY REPORT SCHEMAS
# -------------------------------
class InventorySummary(BaseModel):
    total_items: int
    total_quantity: float
    total_reserved: float
    total_available: float
    low_stock_items: int
    out_of_stock_items: int
    recent_updates: List[dict] = []


class LowStockItem(BaseModel):
    inventory_item_id: int
    warehouse_id: int
    warehouse_name: str
    product_variant_id: int
    product_name: str
    variant_name: str
    current_stock: Decimal
    reserved_stock: Decimal
    available_stock: Decimal
    threshold: Decimal
    shortage: Decimal


class StockLevelReportItem(BaseModel):
    inventory_id: int
    product_id: int
    product_name: str
    variant_id: int
    variant_name: str
    warehouse_id: int
    warehouse_name: str
    total_quantity: Decimal
    reserved_quantity: Decimal
    available_quantity: Decimal
    status: str
    last_updated: Optional[datetime]


# -------------------------------
# PROCUREMENT RECEIVING
# -------------------------------
class ProcurementReceiveRequest(BaseModel):
    procurement_id: int
    warehouse_id: int
    received_by_id: int


# -------------------------------
# SALE PROCESSING
# -------------------------------
class SaleItemRequest(BaseModel):
    product_variant_id: int
    quantity: Decimal


class SaleProcessRequest(BaseModel):
    pos_id: int
    items: List[SaleItemRequest]


class SaleProcessResponse(BaseModel):
    pos_id: int
    warehouse_id: int
    items_processed: int
    details: List[dict]
    
# -------------------------------
# Pydantic v2: rebuild models to resolve forward references
# -------------------------------
WarehouseOut.model_rebuild()
InventoryOut.model_rebuild()
