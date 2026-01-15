from sqlalchemy import Column, Integer, String, Numeric, Enum, DateTime, ForeignKey, Boolean, Time

from sqlalchemy.orm import relationship

from sqlalchemy.sql import func
from src.core.database import Base
import enum


class PosType(str, enum.Enum):
    INTERNAL = "internal"
    EXTERNAL = "external"


class PosStatus(str, enum.Enum):
    ACTIVE = "active"
    SUSPENDED = "suspended"
    BANNED = "banned"
    INACTIVE = "inactive"
    DELETED = "deleted"
    CREATED = "created"


class PosCartStatus(str, enum.Enum):
    OPEN = "open"
    CLOSED = "closed"
    COMPLETED = "completed"


class PaymentMethod(str, enum.Enum):
    CASH = "cash"
    BANK_TRANSFER = "bank_transfer"
    MOBILE_MONEY = "mobile_money"
    CHEQUE = "cheque"
    CARD = "card"
    OTHER = "other"


class ProcurementStatus(str, enum.Enum):
    PENDING = "pending"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"


class SaleStatus(str, enum.Enum):
    COMPLETED = "completed"
    PARTIAL = "partial"
    CANCELLED = "cancelled"


class POSUserRole(str, enum.Enum):
    MANAGER = "manager"
    CASHIER = "cashier"
    STOREKEEPER = "storekeeper"


class POSExpenseCategory(str, enum.Enum):
    RENT = "rent"
    TRANSPORT = "transport"
    UTILITIES = "utilities"
    SUPPLIES = "supplies"
    MAINTENANCE = "maintenance"
    SALARY = "salary"
    COMMISSION = "commission"
    OTHER = "other"


class POSExpenseStatus(str, enum.Enum):
    DRAFT = "draft"
    APPROVED = "approved"
    REJECTED = "rejected"
    PAID = "paid"


class POS(Base):
    __tablename__ = "pos"

    id = Column(Integer, primary_key=True)
    type = Column(Enum(PosType), nullable=False)
    pos_business_name= Column(String(255), nullable=False)
    phone = Column(String(40), unique=True, nullable=False)


    balance = Column(Numeric(12, 2), default=0)
    status = Column(Enum(PosStatus), default=PosStatus.CREATED)

    # relationships
    addresses = relationship(
        "Address",
        back_populates="pos",
        cascade="all, delete-orphan"
    )

    sales = relationship("Sale", back_populates="pos")
    procurements = relationship("Procurement", back_populates="pos")

    users = relationship(
        "POSUser",
        back_populates="pos",
        cascade="all, delete-orphan"
    )

    expenses = relationship(
        "POSExpense",
        back_populates="pos",
        cascade="all, delete-orphan"
    )


class POSUser(Base):
    __tablename__ = "pos_user"

    id = Column(Integer, primary_key=True)

    pos_id = Column(
        Integer,
        ForeignKey("pos.id", ondelete="CASCADE"),
        nullable=False
    )

    first_name = Column(String(120))
    last_name = Column(String(120))
    username = Column(String(120), unique=True, nullable=False)
    phone = Column(String(40), unique=True, nullable=False)
    email = Column(String(255), nullable=False)

    password_hash = Column(String(255), nullable=False)
    pin_hash = Column(String(255), nullable=False)
    last_login_ip = Column(String, nullable=True)
    last_login_user_agent = Column(String, nullable=True)

    is_active = Column(Boolean, default=True)
    face_photo = Column(String(255))
    id_photo_recto = Column(String(255))
    id_photo_verso = Column(String(255))

    require_password_change = Column(Boolean, default=True)

    allowed_login_start = Column(Time, nullable=True)  # e.g. 08:00
    allowed_login_end = Column(Time, nullable=True)    # e.g. 18:00

    role = Column(
        Enum(
            POSUserRole,
            name="pos_user_role_enum",
            values_callable=lambda e: [i.value for i in e],
        ),
        nullable=False,
        default=POSUserRole.CASHIER,
    )


    # relationship
    pos = relationship("POS", back_populates="users")


class Sale(Base):
    __tablename__ = "sales"

    id = Column(Integer, primary_key=True)

    pos_id = Column(Integer, ForeignKey("pos.id"), nullable=False)
    created_by_id = Column(Integer, ForeignKey("pos_user.id"), nullable=False)

    customer_id = Column(Integer, ForeignKey("clients.id"))
    total_amount = Column(Numeric(12, 2), nullable=False)

    payment_mode = Column(Enum(PaymentMethod), nullable=False)
    status = Column(Enum(SaleStatus), default=SaleStatus.COMPLETED)

    date = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # relationships
    pos = relationship("POS", back_populates="sales")
    created_by = relationship("POSUser")

    customer = relationship("Client", back_populates="sales")

    items = relationship(
        "SaleItem",
        back_populates="sale",
        cascade="all, delete-orphan"
    )

    returns = relationship(
        "SaleReturn",
        back_populates="sale",
        cascade="all, delete-orphan"
    )

    counter_customer = relationship(
        "SaleCustomerInfo",
        uselist=False,
        back_populates="sale",
        cascade="all, delete-orphan"
    )


class SaleItem(Base):
    __tablename__ = "sale_items"

    id = Column(Integer, primary_key=True)
    sale_id = Column(Integer, ForeignKey("sales.id"))
    product_variant_id = Column(Integer, ForeignKey("product_variants.id"))
    qty = Column(Numeric(12, 2))
    unit_price = Column(Numeric(12, 2))

    sale = relationship("Sale", back_populates="items")


class SaleReturn(Base):
    __tablename__ = "sale_returns"

    id = Column(Integer, primary_key=True)
    sale_id = Column(Integer, ForeignKey("sales.id"))
    date = Column(DateTime(timezone=True))
    reason = Column(String(255))
    sale = relationship("Sale", back_populates="returns")


class POSCart(Base):
    __tablename__ = "pos_carts"

    id = Column(Integer, primary_key=True)

    pos_id = Column(Integer, ForeignKey("pos.id"), nullable=False)
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=True)

    status = Column(Enum(PosStatus), default=PosCartStatus.OPEN)  # open / suspended / completed

    cart_id = Column(Integer, ForeignKey("carts.id"), unique=True)

    cart = relationship("Cart")


class SaleCustomerInfo(Base):
    __tablename__ = "sale_customer_infos"

    id = Column(Integer, primary_key=True)

    sale_id = Column(Integer, ForeignKey("sales.id"), nullable=False, unique=True)

    first_name = Column(String(120), nullable=False)
    last_name = Column(String(120), nullable=False)
    phone = Column(String(40), nullable=True)

    sale = relationship("Sale", back_populates="counter_customer")


class POSExpense(Base):
    __tablename__ = "pos_expenses"

    id = Column(Integer, primary_key=True)

    reference = Column(String(50), unique=True, nullable=False)

    pos_id = Column(Integer, ForeignKey("pos.id"), nullable=False)
    category = Column(
        Enum(POSExpenseCategory, name="pos_expense_category_enum"),
        nullable=False
    )

    amount = Column(Numeric(12, 2), nullable=False)

    description = Column(String(255))

    expense_date = Column(DateTime(timezone=True), nullable=False)

    status = Column(
        Enum(POSExpenseStatus, name="pos_expense_status_enum"),
        default=POSExpenseStatus.DRAFT,
        nullable=False
    )

    created_by_id = Column(Integer, ForeignKey("pos_user.id"), nullable=False)
    approved_by_id = Column(Integer, ForeignKey("pos_user.id"), nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # relationships
    pos = relationship("POS", back_populates="expenses")

    created_by = relationship(
        "POSUser",
        foreign_keys=[created_by_id]
    )

    approved_by = relationship(
        "POSUser",
        foreign_keys=[approved_by_id]
    )


