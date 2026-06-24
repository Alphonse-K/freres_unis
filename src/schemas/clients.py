from datetime import datetime
from decimal import Decimal
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict
from src.models.clients import (
    ClientType, 
    ClientStatus, 
    MagneticCardStatus, 
    ApprovalStatus, 
    ClientInvoiceStatus, 
    PaymentMethod,
    ReturnStatus,
    CardRequestStatus,
    CardPriceStatus
)
from uuid import UUID



class ClientBase(BaseModel):
    type: ClientType = Field(..., description="Client category")
    first_name: str = Field(..., max_length=120)
    last_name: str = Field(..., max_length=120)
    phone: str = Field(..., max_length=40)
    email: Optional[str] = Field(None, max_length=255)
    card_opening_balance: Decimal = Field(default=0, max_digits=14, decimal_places=2)
    anticipated_balance: Decimal = Field(default=0, max_digits=14, decimal_places=2)
    current_balance: Decimal = Field(default=0, max_digits=14, decimal_places=2)
    status: ClientStatus = Field(default=ClientStatus.ACTIVE)
    magnetic_card_status: MagneticCardStatus = Field(default=MagneticCardStatus.HELD_VALID)

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


class ClientApprovalInfo(BaseModel):
    employee_company: str | None = None
    magnetic_card_number: str | None = None
    model_config = ConfigDict(from_attributes=True)


class ClientHeirInfo(BaseModel):
    first_name: str | None = None
    last_name: str | None = None
    phone: str | None = None
    address: str | None = None
    model_config = ConfigDict(from_attributes=True)


class ClientResponse(ClientBase):
    id: int
    submitted_at: Optional[datetime] = None
    approval: ClientApprovalInfo
    heir: list [ClientHeirInfo]

# ---- APPROVAL FLOW ----
class ClientApprovalBase(BaseModel):
    type: ClientType
    first_name: str
    last_name: str
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
    magnetic_card_number: Optional[str] = None
    company_address: Optional[str] = None
    company_id: int | None = None

    model_config = ConfigDict(from_attributes=True)


class ClientApprovalCreate(ClientApprovalBase):
    pass


class ClientApprovalUpdate(BaseModel):
    type: ClientType | None = None
    first_name: str | None = None
    last_name: str | None = None
    email: str | None = None
    id_type_id: int | None = None
    id_number: str | None = None
    employee_company: str | None = None
    magnetic_card_number: str | None = None
    company_address: str | None = None
    company_id: int | None = None
    status: ApprovalStatus | None = None
    rejection_reason: str | None = None
    reviewed_by_id: int | None = None


class ClientApprovalResponse(ClientApprovalBase):
    id: int
    status: ApprovalStatus
    rejection_reason: Optional[str]
    submitted_at: datetime
    reviewed_at: Optional[datetime]
    reviewed_by_id: Optional[int]
    client_id: Optional[int]


class ClientActivationSetPassword(BaseModel):
    password: str = Field(..., min_length=8, max_length=12)
    pin: str = Field(..., min_length=4, max_length=4)


from pydantic import BaseModel, Field, field_validator
import re


class ClientActivationSetPassword(BaseModel):
    password: str = Field(..., min_length=8, max_length=12)
    pin: str = Field(..., min_length=4, max_length=4)
    
    @field_validator('password')
    @classmethod
    def validate_password(cls, v):
        """Validate password strength"""
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        if len(v) > 12:
            raise ValueError('Password must be at most 12 characters long')
        
        # Check for at least one uppercase letter
        if not re.search(r'[A-Z]', v):
            raise ValueError('Password must contain at least one uppercase letter')
        
        # Check for at least one lowercase letter
        if not re.search(r'[a-z]', v):
            raise ValueError('Password must contain at least one lowercase letter')
        
        # Check for at least one digit
        if not re.search(r'\d', v):
            raise ValueError('Password must contain at least one number')
        
        # Check for at least one special character
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', v):
            raise ValueError('Password must contain at least one special character')
        
        # Check for no spaces
        if ' ' in v:
            raise ValueError('Password cannot contain spaces')
        
        return v
    
    @field_validator('pin')
    @classmethod
    def validate_pin(cls, v):
        """Validate PIN is 4 digits only"""
        if not v.isdigit():
            raise ValueError('PIN must contain only digits')
        
        if len(v) != 4:
            raise ValueError('PIN must be exactly 4 digits')
        
        if len(set(v)) == 1:  # All digits are the same
            raise ValueError('PIN cannot be all the same digit')
        
        return v
    

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
    product_variant_id: int = Field(..., description="Order item being returned")
    qty_returned: Decimal = Field(..., gt=0)


class ClientReturnItemResponse(BaseModel):
    id: int
    product_variant_id: int
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
    status: ReturnStatus
    created_at: datetime
    items: list[ClientReturnItemResponse]

    model_config = ConfigDict(from_attributes=True)


class ClientReturnFiler(BaseModel):
    client_id: str
    order_id: str
    amount: Decimal


class ClientReturnFilter(BaseModel):
    client_id: int
    order_id: Optional[int] = None
    min_amount: Optional[Decimal] = None
    max_amount: Optional[Decimal] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None


class ClientSchema(BaseModel):
    id: int
    phone: str
    email: Optional[str] = None
    status: str
    model_config = ConfigDict(from_attributes=True)


class ClientLedgerResponse(BaseModel):
    id: int
    client_id: int
    amount: Decimal
    entry_type: str
    balance_before: Decimal
    balance_after: Decimal
    reason: str | None = None
    reference_id: str | None = None
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class ClientResponseLight(BaseModel):
    id: int
    first_name: str
    last_name: str
    phone: str
    status: ClientStatus
    current_balance: str
    approval: ClientApprovalInfo | None = None
    model_config = ConfigDict(from_attributes=True)


class TransferRequest(BaseModel):
    phone: str = Field(..., description="Provider valid client phone number without country code")
    amount: Decimal = Field(..., gt=0, example=1000)


class TransferResponse(BaseModel):
    reference_id: str
    amount: Decimal
    message: str
    model_config = ConfigDict(from_attributes=True)


################### CLIENT REQUEST ##################################33

class ClientRequestBase(BaseModel):
    request: str


class ClientRequestUpdate(BaseModel):
    request: str | None = None


class ClientRequestResponse(BaseModel):
    id: int
    client_id: int
    request: str
    response: str | None = None
    replied_by: int | None = None
    created_at: datetime
    replied_at: datetime | None = None
    model_config = ConfigDict(from_attributes=True)


class ClientRequestReply(BaseModel):
    response: str


class ClientRequestReplyUpdate(BaseModel):
    response: str | None = None


###################### CLIENT CARD ####################################
class CardRequestCreate(BaseModel):
    reason: str | None = None


class CardRequestResponse(BaseModel):
    id: int
    client_id: int
    status: CardRequestStatus
    reason: str | None
    requested_at: datetime
    reviewed_at: datetime | None
    model_config = ConfigDict(from_attributes=True)


class CardApproveRequest(BaseModel):
    approve: bool
    reason: str | None = None


class ClientCardResponse(BaseModel):
    id: UUID
    card_number: str
    issued_at: datetime
    expires_at: datetime
    is_active: bool
    model_config = ConfigDict(from_attributes=True)


class ScanRequest(BaseModel):
    token: str


class ScanResponse(BaseModel):
    client_id: int
    balance: Decimal
    first_name: str
    last_name: str
    model_config = ConfigDict(from_attributes=True)


class CardPriceResponse(BaseModel):
    id: int
    price: Decimal
    status: CardPriceStatus
    created_at: datetime
    updated_at: datetime | None
    model_config = ConfigDict(from_attributes=True)

##################### CLIENT HEIR ##################################

class ClientHeirBase(BaseModel):
    first_name: str
    last_name: str
    phone: str
    address: str


class ClientHeirCreate(ClientHeirBase):
    client_id: int


class ClientHeirUpdate(BaseModel):
    first_name: str | None = None
    last_name: str | None = None
    phone: str | None = None
    address: str | None = None


class ClientHeirResponse(ClientHeirBase):
    client_id: int
    model_config = ConfigDict(from_attributes=True)


########################### CLIENT LOAN #############################
class LoanRequestCreate(BaseModel):
    amount: Decimal
    reason: str | None = None


class LoanResponse(BaseModel):
    id: UUID
    client_id: int
    amount: Decimal
    remaining_amount: Decimal
    status: str
    requested_at: datetime
    model_config = ConfigDict(from_attributes=True)


class ClientWithDebtResponse(BaseModel):
    id: int
    balance: Decimal
    total_outstanding_loans: Decimal
    net_position: Decimal
    model_config = ConfigDict(from_attributes=True)