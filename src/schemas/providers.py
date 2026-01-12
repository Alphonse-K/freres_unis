# src/schemas/providers.py
from datetime import date
from decimal import Decimal
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict
from src.models.providers import PurchaseInvoiceStatus, PaymentMethod

# -------------------------------
# PROVIDER SCHEMAS
# -------------------------------

class ProviderBase(BaseModel):
    name: str = Field(..., max_length=255)
    phone: Optional[str] = Field(None, max_length=40)
    email: Optional[str] = Field(None, max_length=255)
    is_active: Optional[bool] = True

    opening_balance: Optional[Decimal] = 0
    anticipated_balance: Optional[Decimal] = 0
    current_balance: Optional[Decimal] = 0


class ProviderCreate(ProviderBase):
    pass  # no extra fields needed


class ProviderUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=255)
    phone: Optional[str] = Field(None, max_length=40)
    email: Optional[str] = Field(None, max_length=255)
    is_active: Optional[bool] = None

    opening_balance: Optional[Decimal] = None
    anticipated_balance: Optional[Decimal] = None
    current_balance: Optional[Decimal] = None


class ProviderOut(ProviderBase):
    id: int
    created_at: date

    model_config = ConfigDict(from_attributes=True)


# -------------------------------
# PURCHASE INVOICE SCHEMAS
# -------------------------------

class PurchaseInvoiceBase(BaseModel):
    invoice_number: str = Field(..., max_length=100)
    invoice_date: date
    posting_date: date
    total_amount: Decimal
    paid_amount: Optional[Decimal] = 0
    status: Optional[PurchaseInvoiceStatus] = PurchaseInvoiceStatus.DRAFT
    notes: Optional[str] = None


class PurchaseInvoiceCreate(PurchaseInvoiceBase):
    provider_id: int


class PurchaseInvoiceUpdate(BaseModel):
    invoice_number: Optional[str] = Field(None, max_length=100)
    invoice_date: Optional[date] = None
    posting_date: Optional[date] = None
    total_amount: Optional[Decimal] = None
    paid_amount: Optional[Decimal] = None
    status: Optional[PurchaseInvoiceStatus] = None
    notes: Optional[str] = None


class PurchaseInvoiceOut(PurchaseInvoiceBase):
    id: int
    provider_id: int

    model_config = ConfigDict(from_attributes=True)


# -------------------------------
# PURCHASE RETURN SCHEMAS
# -------------------------------

class PurchaseReturnBase(BaseModel):
    return_date: date
    amount: Decimal
    reason: Optional[str] = None


class PurchaseReturnCreate(PurchaseReturnBase):
    provider_id: int
    purchase_invoice_id: int


class PurchaseReturnUpdate(BaseModel):
    return_date: Optional[date] = None
    amount: Optional[Decimal] = None
    reason: Optional[str] = None


class PurchaseReturnOut(PurchaseReturnBase):
    id: int
    provider_id: int
    purchase_invoice_id: int

    model_config = ConfigDict(from_attributes=True)


# -------------------------------
# PROVIDER PAYMENT SCHEMAS
# -------------------------------

class ProviderPaymentBase(BaseModel):
    payment_date: date
    amount: Decimal
    payment_method: PaymentMethod
    reference: Optional[str] = None
    notes: Optional[str] = None


class ProviderPaymentCreate(ProviderPaymentBase):
    provider_id: int


class ProviderPaymentUpdate(BaseModel):
    payment_date: Optional[date] = None
    amount: Optional[Decimal] = None
    payment_method: Optional[PaymentMethod] = None
    reference: Optional[str] = None
    notes: Optional[str] = None


class ProviderPaymentOut(ProviderPaymentBase):
    id: int
    provider_id: int

    model_config = ConfigDict(from_attributes=True)
