from datetime import datetime
from decimal import Decimal
from typing import Optional, List
from pydantic import BaseModel, Field, ConfigDict, model_validator
from src.models.clients import ClientType, ClientStatus, MagneticCardStatus, ApprovalStatus, ClientInvoiceStatus, PaymentMethod


class ClientBase(BaseModel):
    type: ClientType = Field(..., description="Client category")
    first_name: str = Field(..., max_length=120)
    last_name: str = Field(..., max_length=120)
    username: str = Field(..., max_length=120)
    phone: str = Field(..., max_length=40)
    email: Optional[str] = Field(None, max_length=255)
    opening_balance: Decimal = Field(default=0, max_digits=14, decimal_places=2)
    anticipated_balance: Decimal = Field(default=0, max_digits=14, decimal_places=2)
    current_balance: Decimal = Field(default=0, max_digits=14, decimal_places=2)
    status: ClientStatus = Field(default=ClientStatus.ACTIVE)
    magnetic_card_status: MagneticCardStatus = Field(default=MagneticCardStatus.TAKEN)

    model_config = ConfigDict(from_attributes=True)


class ClientCreate(ClientBase):
    password_hash: str = Field(..., description="Hashed password")
    pin_hash: str = Field(..., description="Hashed PIN")
    id_type_id: int = Field(..., description="ID document type reference")
    id_number: str = Field(..., max_length=100, description="Government ID number")


class ClientUpdate(BaseModel):
    first_name: Optional[str] = Field(None, max_length=120)
    last_name: Optional[str] = Field(None, max_length=120)
    email: Optional[str] = Field(None, max_length=255)
    status: Optional[ClientStatus] = Field(None)
    magnetic_card_status: Optional[MagneticCardStatus] = Field(None)

    model_config = ConfigDict(from_attributes=True)


class ClientResponse(ClientBase):
    id: int
    submitted_at: Optional[datetime] = None


# ---- APPROVAL FLOW ----
class ClientApprovalBase(BaseModel):
    type: ClientType
    first_name: str
    last_name: str
    username: str
    phone: str
    email: Optional[str]
    id_type_id: int
    id_number: str

    face_photo: str
    badge_photo: Optional[str]
    id_photo_recto: str
    id_photo_verso: str
    magnetic_card_photo: Optional[str]

    employee_company: Optional[str] = None
    employee_id_number: Optional[str] = None
    company_address: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class ClientApprovalCreate(ClientApprovalBase):
    pass


class ClientApprovalUpdate(BaseModel):
    status: Optional[ApprovalStatus] = None
    rejection_reason: Optional[str] = None
    reviewed_by_id: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)


class ClientApprovalResponse(ClientApprovalBase):
    id: int
    status: ApprovalStatus
    rejection_reason: Optional[str]
    submitted_at: datetime
    reviewed_at: Optional[datetime]
    reviewed_by_id: Optional[int]
    client_id: Optional[int]

class ClientActivationSetPassword(BaseModel):
    password: str = Field(..., min_length=8)
    pin: str = Field(..., min_length=4, max_length=6)


# ---- INVOICES ----
class ClientInvoiceBase(BaseModel):
    invoice_number: str = Field(..., max_length=100)
    invoice_date: datetime = Field(...)
    total_amount: Decimal = Field(..., max_digits=14, decimal_places=2)
    paid_amount: Decimal = Field(default=0, max_digits=14, decimal_places=2)
    status: ClientInvoiceStatus = Field(default=ClientInvoiceStatus.DRAFT)

    model_config = ConfigDict(from_attributes=True)


class ClientInvoiceCreate(ClientInvoiceBase):
    client_id: int = Field(...)
    order_id: int = Field(...)


class ClientInvoiceUpdate(BaseModel):
    paid_amount: Optional[Decimal] = Field(None, max_digits=14, decimal_places=2)
    status: Optional[ClientInvoiceStatus] = None

    model_config = ConfigDict(from_attributes=True)


class ClientInvoiceResponse(ClientInvoiceBase):
    id: int
    client_id: int
    order_id: int


# ---- PAYMENTS ----

class ClientPaymentBase(BaseModel):
    payment_date: datetime = Field(...)
    amount: Decimal = Field(..., max_digits=14, decimal_places=2)
    payment_method: PaymentMethod = Field(...)
    reference: Optional[str] = Field(None, max_length=100)
    notes: Optional[str] = Field(None, max_length=255)

    model_config = ConfigDict(from_attributes=True)


class ClientPaymentCreate(ClientPaymentBase):
    client_id: int = Field(...)
    client_invoice_id: Optional[int] = None


class ClientPaymentUpdate(BaseModel):
    amount: Optional[Decimal] = Field(None, max_digits=14, decimal_places=2)
    payment_method: Optional[PaymentMethod] = None
    reference: Optional[str] = None
    notes: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class ClientPaymentResponse(ClientPaymentBase):
    id: int
    client_id: int
    client_invoice_id: Optional[int]


# ---- RETURNS ----

class ClientReturnItemCreate(BaseModel):
    order_item_id: int = Field(..., description="Order item being returned")
    qty_returned: Decimal = Field(..., gt=0)


class ClientReturnItemResponse(BaseModel):
    id: int
    order_item_id: int
    qty_returned: Decimal
    unit_price: Decimal
    line_total: Decimal

    model_config = ConfigDict(from_attributes=True)


class ClientReturnBase(BaseModel):
    reason: Optional[str] = Field(None, max_length=255)


class ClientReturnCreate(ClientReturnBase):
    client_id: int
    order_id: int
    items: list[ClientReturnItemCreate]

    @classmethod
    def validate_items(cls, values):
        if not values.get("items"):
            raise ValueError("At least one return item is required")
        return values


class ClientReturnUpdate(BaseModel):
    reason: Optional[str] = None


class ClientReturnResponse(ClientReturnBase):
    id: int
    client_id: int
    order_id: int
    total_amount: Decimal
    created_at: datetime
    items: list[ClientReturnItemResponse]

    model_config = ConfigDict(from_attributes=True)


class ClientReturnFiler(BaseModel):
    client_id: str
    order_id: str
    amount: Decimal


class ClientReturnFilter(BaseModel):
    client_id: Optional[int] = None
    order_id: Optional[int] = None
    min_amount: Optional[Decimal] = None
    max_amount: Optional[Decimal] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
