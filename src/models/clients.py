# src/models/client.py
from sqlalchemy import Column, Integer, String, DateTime, Numeric, ForeignKey, Enum as PgEnum, Text, Time
from src.models.rbac_assiciation import client_roles

from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from src.core.database import Base
import enum


class ApprovalStatus(str, enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class ClientType(str, enum.Enum):
    PARTNER_CLIENT = "partner_client"
    ORDINARY = "ordinary"


class ClientStatus(str, enum.Enum):
    ACTIVE = "active"
    SUSPENDED = "suspended"
    BANNED = "banned"
    INACTIVE = "inactive"
    DELETED = "deleted"


class ClientRole(str, enum.Enum):
    CLIENT = "client",
    SUPER_CLIENT = "super_client"


class MagneticCardStatus(str, enum.Enum):
    TAKEN = "taken"
    HELD = "held"
    NOBALANCE = "nobalance"
    CLOSED = "closed"


class ClientInvoiceStatus(str, enum.Enum):
    DRAFT = "draft"
    PARTIALLY_PAID = "partially_paid"
    PAID = "paid"
    CANCELLED = "cancelled"


class PaymentMethod(str, enum.Enum):
    CASH = "cash"
    BANK_TRANSFER = "bank_transfer"
    MOBILE_MONEY = "mobile_money"
    CHEQUE = "cheque"
    CARD = "card"
    OTHER = "other"


class ReturnStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class Client(Base):
    __tablename__ = "clients"
    id = Column(Integer, primary_key=True)
    type = Column(PgEnum(ClientType), nullable=False)
    first_name = Column(String(120), nullable=False)
    last_name = Column(String(120), nullable=False)
    phone = Column(String(40), unique=True, nullable=False)
    email = Column(String(255))
    status = Column(PgEnum(ClientStatus), default=ClientStatus.INACTIVE)
    opening_balance = Column(Numeric(14, 2), default=0)
    anticipated_balance = Column(Numeric(14, 2), default=0)
    current_balance = Column(Numeric(14, 2), default=0)
    # Credentials (copied from approval)
    password_hash = Column(String(255), nullable=True)
    pin_hash = Column(String(255), nullable=True)
    # Identification
    id_type_id = Column(Integer, ForeignKey("id_types.id"), nullable=False)
    id_number = Column(String(100), nullable=False, unique=True)
    last_login_ip = Column(String, nullable=True)
    last_login_user_agent = Column(String, nullable=True)
    magnetic_card_status = Column(
        PgEnum(MagneticCardStatus),
        default=MagneticCardStatus.TAKEN
    )
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    # relationships
    id_type = relationship("IDType")
    addresses = relationship(
        "Address",
        back_populates="client",
        cascade="all, delete-orphan"
    )
    sales = relationship("Sale", back_populates="customer")
    carts = relationship("Cart", back_populates="client")
    orders = relationship("Order", back_populates="client")
    approval = relationship(
        "ClientApproval",
        uselist=False,
        back_populates="client"
    )
    # roles = relationship(
    #     "Role",
    #     secondary=client_roles,
    #     back_populates="clients"
    # )



class ClientApproval(Base):
    __tablename__ = "client_approvals"

    id = Column(Integer, primary_key=True)
    # Requested client type
    type = Column(PgEnum(ClientType), nullable=False)
    # Identity
    first_name = Column(String(120), nullable=False)
    last_name = Column(String(120), nullable=False)
    phone = Column(String(40), nullable=False)
    email = Column(String(255))
    # Identification
    id_type_id = Column(Integer, ForeignKey("id_types.id"), nullable=False)
    id_number = Column(String(100), nullable=False)
    # Partner-only fields
    employee_company = Column(String(255))
    employee_id_number = Column(String(120))
    company_address = Column(String(255))
    # KYC documents (paths / URLs)
    face_photo = Column(String(255), nullable=False)
    badge_photo = Column(String(255))
    id_photo_recto = Column(String(255), nullable=False)
    id_photo_verso = Column(String(255), nullable=False)
    magnetic_card_photo = Column(String(255))
    # Approval workflow
    status = Column(PgEnum(ApprovalStatus), default=ApprovalStatus.PENDING)
    rejection_reason = Column(Text)
    submitted_at = Column(DateTime(timezone=True), server_default=func.now())
    reviewed_at = Column(DateTime(timezone=True), server_default=func.now())
    reviewed_by_id = Column(Integer, ForeignKey("users.id"))
    # Link to created client (only after approval)
    client_id = Column(
        Integer,
        ForeignKey("clients.id", ondelete="SET NULL"),
        unique=True
    )
    # relationships
    id_type = relationship("IDType")
    reviewed_by = relationship("User")
    client = relationship("Client", back_populates="approval")


class ClientInvoice(Base):
    __tablename__ = "client_invoices"
    id = Column(Integer, primary_key=True)
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=False)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False, unique=True)
    invoice_number = Column(String(100), nullable=False)
    invoice_date = Column(DateTime(timezone=True), nullable=False)
    total_amount = Column(Numeric(14, 2), nullable=False)
    paid_amount = Column(Numeric(14, 2), default=0)
    status = Column(PgEnum(ClientInvoiceStatus), default=ClientInvoiceStatus.DRAFT)
    client = relationship("Client")
    order = relationship("Order")


class ClientPayment(Base):
    __tablename__ = "client_payments"
    id = Column(Integer, primary_key=True)
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=False)
    client_invoice_id = Column(
        Integer,
        ForeignKey("client_invoices.id"),
        nullable=True
    )
    payment_date = Column(DateTime(timezone=True), nullable=False)
    amount = Column(Numeric(14, 2), nullable=False)
    payment_method = Column(PgEnum(PaymentMethod), nullable=False)
    reference = Column(String(100))
    notes = Column(String(255))
    client = relationship("Client")
    invoice = relationship("ClientInvoice")


class ClientReturn(Base):
    __tablename__ = "client_returns"
    id = Column(Integer, primary_key=True)
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=False)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False)
    total_amount = Column(Numeric(14, 2), nullable=False)
    reason = Column(String(255))
    status = Column(
        PgEnum(ReturnStatus),
        nullable=False,
        default=ReturnStatus.PENDING,
        index=True,
    )
    approved_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    approved_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    items = relationship(
        "ClientReturnItem",
        back_populates="client_return",
        cascade="all, delete-orphan",
    )


class ClientReturnItem(Base):
    __tablename__ = "client_return_items"
    id = Column(Integer, primary_key=True)
    client_return_id = Column(
        Integer,
        ForeignKey("client_returns.id", ondelete="CASCADE"),
        nullable=False
    )
    order_item_id = Column(
        Integer,
        ForeignKey("order_items.id"),
        nullable=False
    )
    qty_returned = Column(Numeric(12, 2), nullable=False)
    unit_price = Column(Numeric(12, 2), nullable=False)
    line_total = Column(Numeric(12, 2), nullable=False)
    client_return = relationship("ClientReturn", back_populates="items")
    order_item = relationship("OrderItem")
