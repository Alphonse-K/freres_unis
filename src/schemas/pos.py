# src/schemas/pos.py
from datetime import datetime, time, date
from decimal import Decimal
from typing import Optional, List
from pydantic import BaseModel, Field, ConfigDict, EmailStr, field_validator
from src.schemas.inventory import WarehouseOut
from enum import Enum
import re

# from src.models.pos import SaleStatus, PaymentMethod, POSExpenseCategory, POSExpenseStatus


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
    pos_business_name: str = Field(..., max_length=255)
    phone: str = Field(..., max_length=40)
    balance: Optional[Decimal] = Field(0, ge=0)
    status: Optional[PosStatus] = PosStatus.CREATED
    warehouse_id: Optional[int] = Field(None, description="Associated warehouse ID")
    
    # @field_validator('phone')
    # def validate_phone(cls, v):
    #     # Simple phone validation - adjust as needed
    #     if not re.match(r'^\+?[0-9\s\-\(\)]{10,}$', v):
    #         raise ValueError('Invalid phone number format')
    #     return v


class POSCreate(POSBase):
    pass


class POSUpdate(BaseModel):
    type: Optional[PosType] = None
    pos_business_name: Optional[str] = Field(None, max_length=255)
    phone: Optional[str] = Field(None, max_length=40)
    balance: Optional[Decimal] = Field(None, ge=0)
    status: Optional[PosStatus] = None
    warehouse_id: Optional[int] = Field(None, description="Change associated warehouse")
    
    # @field_validator('phone')
    # def validate_phone(cls, v):
    #     if v is not None:
    #         if not re.match(r'^\+?[0-9\s\-\(\)]{10,}$', v):
    #             raise ValueError('Invalid phone number format')
    #     return v


class POSOut(POSBase):
    id: int
    warehouse: Optional[WarehouseOut] = None
    users: List["POSUserOut"] = []
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class POSStats(BaseModel):
    pos_id: int
    pos_name: str
    total_sales: Optional[int] = 0
    total_revenue: Optional[float] = 0.0
    total_expenses: Optional[float] = 0.0
    net_balance: float
    active_users: Optional[int] = 0
    low_stock_items: Optional[int] = 0
    pending_procurements: Optional[int] = 0
    warehouse_id: Optional[int]
    status: str
    last_updated: Optional[datetime] = None

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


class POSUserSchema(BaseModel):
    id: int
    email: Optional[EmailStr] = None
    username: str
    role: Optional[str] = None
    model_config = ConfigDict(from_attributes=True)


# -------------------------------
# CUSTOMER INFO SCHEMAS
# -------------------------------
class CustomerInfoBase(BaseModel):
    first_name: Optional[str] = Field(None, max_length=120)
    last_name: Optional[str] = Field(None, max_length=120)
    phone: Optional[str] = Field(None, max_length=40)


class CustomerInfoCreate(CustomerInfoBase):
    pass


class CustomerInfoOut(CustomerInfoBase):
    id: int
    sale_id: int

    model_config = ConfigDict(from_attributes=True)


# -------------------------------
# SALE ITEM SCHEMAS
# -------------------------------
class SaleItemBase(BaseModel):
    product_variant_id: int
    qty: Decimal = Field(..., gt=0)
    unit_price: Decimal = Field(..., gt=0)


class SaleItemCreate(SaleItemBase):
    pass


class SaleItemOut(SaleItemBase):
    id: int
    sale_id: int
    product_variant: Optional[dict] = None

    model_config = ConfigDict(from_attributes=True)


# -------------------------------
# SALE SCHEMAS
# -------------------------------
class SaleBase(BaseModel):
    pos_id: int
    created_by_id: int
    customer_id: Optional[int] = None
    payment_mode: PaymentMethod
    transaction_date: Optional[datetime] = None
    tax_rate: Optional[Decimal] = Decimal('0')
    discount_amount: Optional[Decimal] = Decimal('0')
    notes: Optional[str] = None


class SaleCreate(SaleBase):
    items: List[SaleItemCreate]
    customer_info: Optional[CustomerInfoCreate] = None


class SaleItemUpdate(BaseModel):
    qty: Optional[Decimal] = None
    unit_price: Optional[Decimal] = None


class SaleUpdate(BaseModel):
    total_amount: Optional[Decimal] = None
    payment_mode: Optional[PaymentMethod] = None
    status: Optional[SaleStatus] = None
    items: Optional[List[SaleItemUpdate]] = None

class SaleOut(SaleBase):
    id: int
    subtotal_amount: Decimal
    tax_amount: Decimal
    total_amount: Decimal
    status: SaleStatus
    created_at: datetime
    items: List[SaleItemOut] = []
    customer: Optional[dict] = None
    counter_customer: Optional[CustomerInfoOut] = None
    pos: Optional[dict] = None
    created_by: Optional[dict] = None

    model_config = ConfigDict(from_attributes=True)


# -------------------------------
# SALE RETURN SCHEMAS
# -------------------------------
class ReturnItem(BaseModel):
    product_variant_id: int
    quantity: Decimal = Field(..., gt=0)


class SaleReturnBase(BaseModel):
    sale_id: int
    date: Optional[datetime] = None
    reason: str = Field(..., max_length=255)


class SaleReturnCreate(SaleReturnBase):
    items: List[ReturnItem]


class SaleReturnOut(SaleReturnBase):
    id: int
    created_at: datetime
    sale: Optional[dict] = None

    model_config = ConfigDict(from_attributes=True)


# -------------------------------
# SALE REPORT SCHEMAS
# -------------------------------
class SaleSummary(BaseModel):
    total_sales: int
    total_revenue: float
    average_sale_value: float
    payment_methods: List[dict] = []
    recent_sales: List[dict] = []


class DailySalesReport(BaseModel):
    date: date
    total_sales: int
    total_revenue: float
    top_products: List[dict] = []
    sales: List[dict] = []


class SalesTrendItem(BaseModel):
    date: date
    sales_count: int
    total_amount: float


class TopProductReport(BaseModel):
    product_variant_id: int
    variant_name: str
    product_id: int
    total_quantity: float
    total_value: float


# -------------------------------
# EXPENSE SCHEMAS
# -------------------------------
class POSExpenseBase(BaseModel):
    pos_id: int
    category: POSExpenseCategory
    amount: Decimal = Field(..., gt=0)
    description: Optional[str] = Field(None, max_length=255)
    expense_date: Optional[datetime] = None
    status: Optional[POSExpenseStatus] = POSExpenseStatus.DRAFT
    approved_by_id: Optional[int] = None


class POSExpenseCreate(POSExpenseBase):
    created_by_id: int


class POSExpenseUpdate(BaseModel):
    category: Optional[POSExpenseCategory] = None
    amount: Optional[Decimal] = None
    description: Optional[str] = None
    expense_date: Optional[datetime] = None
    status: Optional[POSExpenseStatus] = None
    approved_by_id: Optional[int] = None


class POSExpenseOut(POSExpenseBase):
    id: int
    reference: str
    created_by_id: int
    created_at: datetime
    pos: Optional[dict] = None
    created_by: Optional[dict] = None
    approved_by: Optional[dict] = None

    model_config = ConfigDict(from_attributes=True)


# -------------------------------
# EXPENSE FILTER SCHEMAS
# -------------------------------
class POSExpenseFilter(BaseModel):
    pos_id: Optional[int] = None
    category: Optional[POSExpenseCategory] = None
    status: Optional[POSExpenseStatus] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    created_by_id: Optional[int] = None
    approved_by_id: Optional[int] = None
    skip: int = 0
    limit: int = 50


# -------------------------------
# EXPENSE REPORT SCHEMAS
# -------------------------------
class ExpenseSummary(BaseModel):
    total_expenses: int
    total_amount: float
    by_status: List[dict] = []
    by_category: List[dict] = []
    recent_expenses: List[dict] = []


class ExpensesTrendItem(BaseModel):
    date: date
    expenses_count: int
    total_amount: float


class CategoryBreakdown(BaseModel):
    total_expenses: int
    total_amount: float
    breakdown: List[dict] = []
    top_category: Optional[str] = None
    period: dict = {}


class MonthlyExpenseReport(BaseModel):
    month: int
    year: int
    start_date: date
    end_date: date
    total_expenses: int
    total_amount: float
    weekly_breakdown: List[dict] = []
    daily_average: float


class ExpenseComparison(BaseModel):
    current_period: dict
    previous_period: dict
    comparison: dict


# -------------------------------
# EXPENSE ACTION SCHEMAS
# -------------------------------
class ExpenseApproveRequest(BaseModel):
    approver_id: int


class ExpenseRejectRequest(BaseModel):
    reason: Optional[str] = None