# src/schemas/pos.py
from datetime import datetime, time
from decimal import Decimal
from typing import Optional, List
from pydantic import BaseModel, Field, ConfigDict
from enum import Enum


# --- ENUMS ---
class PosType(str, Enum):
    INTERNAL = "internal"
    EXTERNAL = "external"


class PosStatus(str, Enum):
    ACTIVE = "active"
    SUSPENDED = "suspended"
    BANNED = "banned"
    INACTIVE = "inactive"
    DELETED = "deleted"
    CREATED = "created"


class PosCartStatus(str, Enum):
    OPEN = "open"
    CLOSED = "closed"
    COMPLETED = "completed"


class PaymentMethod(str, Enum):
    CASH = "cash"
    BANK_TRANSFER = "bank_transfer"
    MOBILE_MONEY = "mobile_money"
    CHEQUE = "cheque"
    CARD = "card"
    OTHER = "other"


class ProcurementStatus(str, Enum):
    PENDING = "pending"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"


class SaleStatus(str, Enum):
    COMPLETED = "completed"
    PARTIAL = "partial"
    CANCELLED = "cancelled"


class POSUserRole(str, Enum):
    MANAGER = "manager"
    CASHIER = "cashier"
    STOREKEEPER = "storekeeper"


class POSExpenseCategory(str, Enum):
    RENT = "rent"
    TRANSPORT = "transport"
    UTILITIES = "utilities"
    SUPPLIES = "supplies"
    MAINTENANCE = "maintenance"
    SALARY = "salary"
    COMMISSION = "commission"
    OTHER = "other"


class POSExpenseStatus(str, Enum):
    DRAFT = "draft"
    APPROVED = "approved"
    REJECTED = "rejected"
    PAID = "paid"


# -------------------------------
# POS USER SCHEMAS
# -------------------------------

class POSUserBase(BaseModel):
    first_name: Optional[str] = Field(None, max_length=120)
    last_name: Optional[str] = Field(None, max_length=120)
    username: str = Field(..., max_length=120)
    phone: str = Field(..., max_length=40)
    email: Optional[str] = Field(None, max_length=255)
    role: Optional[POSUserRole] = POSUserRole.CASHIER
    is_active: Optional[bool] = True
    allowed_login_start: Optional[time] = None
    allowed_login_end: Optional[time] = None


class POSUserCreate(POSUserBase):
    password_hash: str
    pin_hash: str


class POSUserUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    role: Optional[POSUserRole] = None
    is_active: Optional[bool] = None
    allowed_login_start: Optional[time] = None
    allowed_login_end: Optional[time] = None
    password_hash: Optional[str] = None
    pin_hash: Optional[str] = None


class POSUserOut(POSUserBase):
    id: int
    pos_id: int

    model_config = ConfigDict(from_attributes=True)


# -------------------------------
# POS SCHEMAS
# -------------------------------

class POSBase(BaseModel):
    type: PosType
    pos_business_name: str
    balance: Optional[Decimal] = 0
    status: Optional[PosStatus] = PosStatus.CREATED


class POSCreate(POSBase):
    pass


class POSUpdate(BaseModel):
    type: Optional[PosType] = None
    pos_business_name: Optional[str] = None
    balance: Optional[Decimal] = None
    status: Optional[PosStatus] = None


class POSOut(POSBase):
    id: int
    users: List[POSUserOut] = []

    model_config = ConfigDict(from_attributes=True)


# -------------------------------
# SALE SCHEMAS
# -------------------------------

class SaleItemBase(BaseModel):
    product_variant_id: int
    qty: Decimal
    unit_price: Decimal


class SaleItemCreate(SaleItemBase):
    pass


class SaleItemUpdate(BaseModel):
    qty: Optional[Decimal] = None
    unit_price: Optional[Decimal] = None


class SaleItemOut(SaleItemBase):
    id: int
    sale_id: int

    model_config = ConfigDict(from_attributes=True)


class SaleBase(BaseModel):
    pos_id: int
    created_by_id: int
    customer_id: Optional[int] = None
    total_amount: Decimal
    payment_mode: PaymentMethod
    status: Optional[SaleStatus] = SaleStatus.COMPLETED
    date: datetime


class SaleCreate(SaleBase):
    items: List[SaleItemCreate]


class SaleUpdate(BaseModel):
    total_amount: Optional[Decimal] = None
    payment_mode: Optional[PaymentMethod] = None
    status: Optional[SaleStatus] = None
    items: Optional[List[SaleItemUpdate]] = None


class SaleOut(SaleBase):
    id: int
    items: List[SaleItemOut] = []

    model_config = ConfigDict(from_attributes=True)


# -------------------------------
# POS EXPENSE SCHEMAS
# -------------------------------

class POSExpenseBase(BaseModel):
    reference: str
    category: POSExpenseCategory
    amount: Decimal
    description: Optional[str] = None
    expense_date: datetime
    status: Optional[POSExpenseStatus] = POSExpenseStatus.DRAFT
    created_by_id: int
    approved_by_id: int


class POSExpenseCreate(POSExpenseBase):
    pos_id: int


class POSExpenseUpdate(BaseModel):
    category: Optional[POSExpenseCategory] = None
    amount: Optional[Decimal] = None
    description: Optional[str] = None
    expense_date: Optional[datetime] = None
    status: Optional[POSExpenseStatus] = None
    approved_by_id: Optional[int] = None


class POSExpenseOut(POSExpenseBase):
    id: int
    pos_id: int

    model_config = ConfigDict(from_attributes=True)
