# src/schemas/procurements.py
from datetime import datetime
from decimal import Decimal
from typing import Optional, List
from pydantic import BaseModel, Field, ConfigDict
from src.models.procurement import ProcurementStatus


# -------------------------------
# PROCUREMENT ITEM SCHEMAS
# -------------------------------

class ProcurementItemBase(BaseModel):
    product_variant_id: int
    qty: Decimal
    price: Decimal
    returned_qty: Optional[Decimal] = 0


class ProcurementItemCreate(ProcurementItemBase):
    pass


class ProcurementItemUpdate(BaseModel):
    qty: Optional[Decimal] = None
    price: Optional[Decimal] = None
    returned_qty: Optional[Decimal] = None


class ProcurementItemOut(ProcurementItemBase):
    id: int
    procurement_id: int

    model_config = ConfigDict(from_attributes=True)


# -------------------------------
# PROCUREMENT SCHEMAS
# -------------------------------

class ProcurementBase(BaseModel):
    reference: str = Field(..., max_length=50)
    provider_id: int
    pos_id: int
    created_by_id: int

    warehouse_id: Optional[int] = None
    purchase_invoice_id: Optional[int] = None

    total_amount: Decimal
    date: datetime
    status: Optional[ProcurementStatus] = ProcurementStatus.PENDING


class ProcurementCreate(ProcurementBase):
    items: List[ProcurementItemCreate]


class ProcurementUpdate(BaseModel):
    reference: Optional[str] = Field(None, max_length=50)
    provider_id: Optional[int] = None
    pos_id: Optional[int] = None
    created_by_id: Optional[int] = None
    warehouse_id: Optional[int] = None
    purchase_invoice_id: Optional[int] = None
    total_amount: Optional[Decimal] = None
    date: Optional[datetime] = None
    status: Optional[ProcurementStatus] = None
    items: Optional[List[ProcurementItemUpdate]] = None  # optional updates to items


class ProcurementOut(ProcurementBase):
    id: int
    created_at: datetime
    items: List[ProcurementItemOut] = []

    # Optional computed properties
    due_amount: Optional[Decimal] = None
    payment_status: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)
