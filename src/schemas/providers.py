# src/schemas/provider.py
from pydantic import BaseModel, Field, EmailStr, ConfigDict
from datetime import date, datetime
from decimal import Decimal
from typing import List, Optional
from src.models.providers import PurchaseInvoiceStatus, PaymentMethod
from src.schemas.location import AddressCreate, AddressOut


class ProviderBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=255)
    phone: Optional[str] = Field(None, max_length=40)
    email: Optional[EmailStr] = None
    is_active: bool = True
    

class ProviderCreate(ProviderBase):
    opening_balance: Decimal = 0
    addresses: Optional[List[AddressCreate]] = None


class ProviderUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=255)
    phone: Optional[str] = Field(None, max_length=40)
    email: Optional[EmailStr] = None
    is_active: Optional[bool] = None


class ProviderResponse(ProviderBase):
    id: int
    opening_balance: Decimal
    current_balance: Decimal
    anticipated_balance: Decimal
    created_at: date
    updated_at: Optional[date]
    addresses: List[AddressOut] = []
    model_config = ConfigDict(from_attributes=True)


# class ProviderSummaryResponse(BaseModel):
#     id: int
#     name: str
#     total_invoices: Decimal
#     total_paid: Decimal
#     total_due: Decimal
#     invoice_count: int
#     last_purchase_date: Optional[datetime]
#     model_config = ConfigDict(from_attributes=True)
# =========================
# PROVIDER SUMMARY SCHEMAS
# =========================

class ProviderSummaryProvider(BaseModel):
    id: int
    name: str
    current_balance: Decimal
    is_active: bool
    created_at: date

    model_config = ConfigDict(from_attributes=True)


class ProviderInvoiceStatistics(BaseModel):
    total_invoices: int
    pending_invoices: int
    paid_invoices: int
    partially_paid_invoices: int
    overdue_invoices: int
    total_invoice_amount: Decimal
    total_paid_amount: Decimal
    outstanding_balance: Decimal


class ProviderAgingSummary(BaseModel):
    bucket_0_30: Decimal = Field(alias="0_30")
    bucket_31_60: Decimal = Field(alias="31_60")
    bucket_61_90: Decimal = Field(alias="61_90")
    bucket_90_plus: Decimal = Field(alias="90_plus")
    total: Decimal

    model_config = ConfigDict(populate_by_name=True)


class ProviderSummaryResponse(BaseModel):
    provider: ProviderSummaryProvider
    statistics: ProviderInvoiceStatistics
    aging: ProviderAgingSummary
    recent_procurements: List[dict]
    recent_payments: List[dict]
    default_address: Optional[AddressOut]


# Purchase Invoice Schemas
class PurchaseInvoiceBase(BaseModel):
    invoice_number: str
    invoice_date: datetime
    due_date: Optional[datetime] = None
    total_amount: Decimal = Field(gt=0)
    notes: Optional[str] = None


class PurchaseInvoiceCreate(PurchaseInvoiceBase):
    provider_id: int
    procurement_id: Optional[int] = None
    po_reference: Optional[str] = None


class PurchaseInvoiceUpdate(BaseModel):
    status: Optional[PurchaseInvoiceStatus] = None
    paid_amount: Optional[Decimal] = None
    notes: Optional[str] = None


class PurchaseInvoiceResponse(PurchaseInvoiceBase):
    id: int
    provider_id: int
    procurement_id: Optional[int]
    po_reference: Optional[str]
    posting_date: datetime
    paid_amount: Decimal
    status: PurchaseInvoiceStatus
    due_amount: Decimal
    is_overdue: bool
    age_days: int
    created_at: datetime
    updated_at: Optional[datetime]  
    model_config = ConfigDict(from_attributes=True)


# Payment Schemas
class ProviderPaymentBase(BaseModel):
    payment_date: date
    amount: Decimal = Field(gt=0)
    payment_method: PaymentMethod
    reference: Optional[str] = None
    notes: Optional[str] = None


class ProviderPaymentCreate(ProviderPaymentBase):
    provider_id: int
    purchase_invoice_id: Optional[int] = None


class ProviderPaymentResponse(ProviderPaymentBase):
    id: int
    provider_id: int
    purchase_invoice_id: Optional[int]
    model_config = ConfigDict(from_attributes=True)


# ================================
# ADDITIONAL SCHEMAS NEEDED
# ================================

# Add these to your src/schemas/provider.py file:
class PurchaseReturnCreate(BaseModel):
    purchase_invoice_id: int
    return_date: date
    amount: Decimal = Field(gt=0)
    reason: str = Field(..., min_length=2, max_length=255)


class PurchaseReturnResponse(BaseModel):
    id: int
    provider_id: int
    purchase_invoice_id: int
    return_date: date
    amount: Decimal
    reason: str
    
    model_config = ConfigDict(from_attributes=True)

