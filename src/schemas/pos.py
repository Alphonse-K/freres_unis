from datetime import datetime, time, date
from decimal import Decimal
from typing import Optional, List
from pydantic import BaseModel, Field, ConfigDict, EmailStr, field_validator
from src.schemas.inventory import WarehouseOut
from src.schemas.catalog import ProductVariantOut
from enum import Enum
from pydantic import BaseModel
from src.schemas.common import ClientSimple
from src.models.pos import PosType


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
    CARD_VALIDATION = "card_validation"
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

class RoleSchema(BaseModel):
    id: int
    name: str
    model_config = {"from_attributes": True}


class POSUserBase(BaseModel):
    first_name: str | None = Field(None, max_length=120)
    last_name: str | None = Field(None, max_length=120)
    username: str = Field(..., max_length=120)
    phone: str = Field(..., max_length=40)
    email: str = Field(..., description="The email address of the user", max_length=255)
    is_active: bool | None = True
    allowed_login_start: time | None = None
    allowed_login_end: time | None = None


class POSUserCreate(POSUserBase):
    password_hash: str
    pin_hash: str


class POSUserUpdate(BaseModel):
    first_name: str | None = None
    last_name: str | None = None
    email: str | None = None
    is_active: bool | None = None
    allowed_login_start: time | None = None
    allowed_login_end: time | None = None
    password_hash: str | None = None
    pin_hash: str | None = None


class POSUserOut(POSUserBase):
    id: int
    pos_id: int
    model_config = ConfigDict(from_attributes=True)


class POSUserSimple(BaseModel):
    id: int
    first_name: str
    last_name: str
    username: str
    phone: str
    email: str

    model_config = ConfigDict(from_attributes=True)


# -------------------------------
# POS SCHEMAS
# -------------------------------
class POSBase(BaseModel):
    type: PosType
    pos_business_name: str = Field(..., max_length=255)
    phone: str = Field(..., max_length=40)
    balance: Decimal | None = Field(0, ge=0)
    status: PosStatus | None = PosStatus.CREATED
    warehouse_id: int | None = Field(None, description="Associated warehouse ID")
    

class POSCreate(POSBase):
    pass


class POSUpdate(BaseModel):
    type: PosType | None = None
    pos_business_name: str | None = Field(None, max_length=255)
    phone: str | None = Field(None, max_length=40)
    balance: Decimal | None = Field(None, ge=0)
    status: PosStatus | None = None
    warehouse_id: int | None = Field(None, description="Change associated warehouse")
    

class POSOut(POSBase):
    id: int
    warehouse: WarehouseOut | None = None
    users: List["POSUserOut"] = []
    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)

# This is a simplified version of the POS output schema for listing purposes, 
# excluding related users and warehouse details.
# The POSLightOut class is currently unused and has been commented out for potential future use or removal.
# class POSLightOut(BaseModel):
#     id: int,
#     pos_business_name: str = Field(..., max_length=255)
#     phone: str = Field(..., max_length=40)


class POSStats(BaseModel):
    pos_id: int
    pos_name: str
    total_sales: int | None = 0
    total_revenue: float | None = 0.0
    total_expenses: float | None = 0.0
    net_balance: float
    active_users: int | None = 0
    low_stock_items: int | None = 0
    pending_procurements: int | None = 0
    warehouse_id: int | None
    status: str
    last_updated: datetime | None = None

# ------------------------------- 
# POS EXPENSE SCHEMAS
# -------------------------------


class POSMini(POSBase):
    id: int
    model_config = ConfigDict(from_attributes=True)


class POSUserSchema(BaseModel):
    id: int
    email: EmailStr | None = None
    username: str
    roles: list[RoleSchema] | None = None
    pos: POSMini | None = None
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
    product_variant: Optional[ProductVariantOut] = None

    model_config = ConfigDict(from_attributes=True)


# -------------------------------
# SALE SCHEMAS
# -------------------------------
class SaleBase(BaseModel):
    pos_id: int
    created_by_id: int
    customer_id: int | None = None
    payment_mode: PaymentMethod
    transaction_date: datetime | None = None
    tax_rate: Decimal | None = Decimal('0')
    discount_amount: Decimal | None = Decimal('0')
    notes: str | None = None
    payment_operator_name: str | None = None
    payment_operator_reference: str | None = None
    card_number: str | None = None
    company_name: str | None = None


class SaleCreate(SaleBase):
    items: List[SaleItemCreate]
    customer_info: CustomerInfoCreate | None = None


class SaleItemUpdate(BaseModel):
    qty: Decimal | None = None
    unit_price: Decimal | None = None


class SaleUpdate(BaseModel):
    total_amount: Decimal | None = None
    payment_mode: PaymentMethod | None = None
    status: SaleStatus | None = None
    items: List[SaleItemUpdate] | None = None


class SaleOut(SaleBase):
    id: int
    subtotal_amount: Decimal
    tax_amount: Decimal
    total_amount: Decimal
    status: SaleStatus
    created_at: datetime
    items: List[SaleItemOut] = Field(default_factory=list)
    customer: ClientSimple | None = None
    counter_customer: CustomerInfoOut | None = None

    pos: POSMini | None = None
    created_by: POSUserOut | None = None

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
    # status: Optional[POSExpenseStatus] = None
    # approved_by_id: Optional[int] = None


class POSExpenseOut(POSExpenseBase):
    id: int
    reference: str
    created_by_id: int
    created_at: datetime
    pos: Optional[POSMini] = None
    created_by: Optional[POSUserOut] = None
    approved_by: Optional[POSUserOut] = None

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


