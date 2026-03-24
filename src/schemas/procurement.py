# src/schemas/procurement.py
from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime
from decimal import Decimal
from typing import List, Optional
from src.models.procurement import ProcurementStatus


class ProcurementItemCreate(BaseModel):
    product_variant_id: int
    qty: Decimal = Field(gt=0)


class ProcurementCreate(BaseModel):
    provider_id: int
    items: List[ProcurementItemCreate]
    expected_delivery_date: Optional[datetime] = None
    payment_terms: Optional[str] = None
    shipping_terms: Optional[str] = None
    notes: Optional[str] = None


class ProcurementUpdate(BaseModel):
    status: Optional[ProcurementStatus] = None
    delivery_date: Optional[datetime] = None
    delivery_notes: Optional[str] = None
    driver_name: Optional[str] = None
    driver_phone: Optional[str] = None


class ProcurementItemResponse(BaseModel):
    id: int
    product_variant_id: int
    product_name: Optional[str] = None
    qty: Decimal
    model_config = ConfigDict(from_attributes=True)


class ProcurementResponse(BaseModel):
    id: int
    reference: str
    provider_id: int
    provider_name: Optional[str] = None
    pos_id: int
    pos_name: Optional[str] = None
    po_date: datetime
    expected_delivery_date: Optional[datetime]
    total_amount: Decimal
    status: ProcurementStatus
    delivery_date: Optional[datetime]
    payment_status: str
    due_amount: Decimal
    receipt_photo: str | None = None
    items: List[ProcurementItemResponse]
    created_at: datetime
    updated_at: Optional[datetime]
    model_config = ConfigDict(from_attributes=True)


class ProcurementUpdateStatus(BaseModel):
    status: ProcurementStatus


class ReturnItem(BaseModel):
    product_variant_id: int = Field(..., example=1)
    qty: int = Field(..., gt=0, example=5)

class CreateReturnRequest(BaseModel):
    items: List[ReturnItem]
    reason: str = Field(None, example="Damaged goods")

class UpdateReturn(CreateReturnRequest):
    pass

class ReturnItemResponse(BaseModel):
    product_variant_id: int
    quantity: int  

    model_config = ConfigDict(from_attributes=True)
class ProcurementReturnResponse(BaseModel):
    id: int
    reference: str
    procurement_id: int
    initiator_pos_id: int
    provider_pos_id: int
    status: str
    reason: Optional[str]
    created_at: datetime
    updated_at: Optional[datetime]
    items: List[ReturnItemResponse] = []
    model_config = ConfigDict(from_attributes=True)