from sqlalchemy import Column, Integer, String, DateTime, Numeric, ForeignKey, Enum as PgEnum, Text, Boolean
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime, timezone
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from src.core.database import Base
import enum, uuid


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
    VALID = "VALID"
    TAKEN_EXPIRED = "TAKEN_EXPIRED"
    HELD_VALID = "HELD_VALID"
    HELD_NOBALANCE = "HELD_NOBALANCE"
    TAKEN_NON_EXPIRED = "TAKEN_NON_EXPIRED"
    EXPIRED_HELD = "EXPIRED_HELD"

    
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
    CANCELLED = "CANCELLED"


class Client(Base):
    __tablename__ = "clients"
    id = Column(Integer, primary_key=True)
    type = Column(PgEnum(ClientType), nullable=False)
    first_name = Column(String(120), nullable=False)
    last_name = Column(String(120), nullable=False)
    phone = Column(String(40), unique=True, nullable=False)
    email = Column(String(255))
    status = Column(PgEnum(ClientStatus), default=ClientStatus.INACTIVE)
    card_opening_balance = Column(Numeric(14, 2), default=0)
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
        default=MagneticCardStatus.VALID
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
    cart = relationship("Cart", back_populates="client")
    orders = relationship("Order", back_populates="client")
    invoices = relationship("ClientInvoice", back_populates="client")
    ledgers = relationship("LedgerEntry", back_populates="client")
    payments = relationship("ClientPayment", back_populates='client')
    returns = relationship("ClientReturn", back_populates="client")
    requests = relationship("ClientRequest", back_populates="client")
    approval = relationship(
        "ClientApproval",
        uselist=False,
        back_populates="client"
    )
    client_card = relationship("ClientCard", back_populates="client")
    client_card_request = relationship("ClientCardRequest", back_populates="client")
    heir = relationship("ClientHeir", back_populates="client")
    loans = relationship("ClientLoan", back_populates="client")



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
    magnetic_card_number = Column(String(120), unique=True)
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
    company_id = Column(Integer, ForeignKey("companies.id", ondelete="SET NULL"), nullable=True)
    # relationships
    id_type = relationship("IDType")
    reviewed_by = relationship("User")
    client = relationship("Client", back_populates="approval")
    company = relationship("Company", back_populates="clients")


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
    client = relationship("Client", back_populates="invoices")
    order = relationship("Order", back_populates="invoices")
    payments = relationship("ClientPayment", back_populates="invoice")


class ClientPayment(Base):
    __tablename__ = "client_payments"
    id = Column(Integer, primary_key=True)
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=False)
    invoice_id = Column(
        Integer,
        ForeignKey("client_invoices.id"),
        nullable=True
    )
    payment_date = Column(DateTime(timezone=True), nullable=False)
    amount = Column(Numeric(14, 2), nullable=False)
    payment_method = Column(PgEnum(
        PaymentMethod,
        values_callable=lambda x: [e.value for e in x]
    ), nullable=False)
    reference = Column(String(100))
    notes = Column(String(255))
    client = relationship("Client", back_populates="payments")
    invoice = relationship("ClientInvoice", back_populates="payments")


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
    approved_by = Column(Integer, ForeignKey("pos_user.id"), nullable=True)
    approved_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=True)
    items = relationship(
        "ClientReturnItem",
        back_populates="client_return",
        cascade="all, delete-orphan",
    )
    client = relationship("Client", back_populates="returns")
    order = relationship("Order")
    approved_by_user = relationship("POSUser", foreign_keys=[approved_by], back_populates="approved_returns")


class ClientReturnItem(Base):
    __tablename__ = "client_return_items"
    id = Column(Integer, primary_key=True)
    client_return_id = Column(
        Integer,
        ForeignKey("client_returns.id", ondelete="CASCADE"),
        nullable=False
    )
    product_variant_id = Column(
        Integer,
        ForeignKey("order_items.id"),
        nullable=False
    )
    qty_returned = Column(Numeric(12, 2), nullable=False)
    unit_price = Column(Numeric(12, 2), nullable=False)
    line_total = Column(Numeric(12, 2), nullable=False)
    client_return = relationship("ClientReturn", back_populates="items")
    order_item = relationship("OrderItem", back_populates="return_items")


class LedgerEntry(Base):
    __tablename__ = "client_ledger_entries"
    id = Column(Integer, primary_key=True)
    client_id = Column(Integer, ForeignKey("clients.id", ondelete="CASCADE"))
    pos_id = Column(Integer, ForeignKey("pos.id", ondelete="CASCADE"), nullable=True)
    amount = Column(Numeric(14, 2), nullable=False)
    entry_type = Column(String(10), nullable=False)
    balance_before = Column(Numeric(14, 2), nullable=False)
    balance_after = Column(Numeric(14, 2), nullable=False)
    reason = Column(String(255), nullable=False)
    reference_id = Column(String(100), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    client = relationship("Client", back_populates="ledgers")
    pos = relationship("POS", back_populates="ledger_entries")


class ClientRequest(Base):
    __tablename__ = "client_requests"
    id = Column(Integer, primary_key=True)
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=False)
    request = Column(Text, nullable=False)
    response = Column(Text, nullable=True)
    replied_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    replied_at = Column(DateTime(timezone=True), onupdate=func.now())
    client = relationship("Client", back_populates="requests")
    user = relationship("User")


class CardRequestStatus(str, enum.Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class ClientCardRequest(Base):
    __tablename__ = "client_card_requests"

    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=False)
    status = Column(PgEnum(CardRequestStatus), default=CardRequestStatus.PENDING)
    reason = Column(String, nullable=True)
    requested_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
        nullable=False
    )    
    reviewed_at = Column(DateTime(timezone=True), nullable=True)
    reviewer_id = Column(Integer, nullable=True)
    client = relationship("Client", back_populates="client_card_request")


class ClientCard(Base):
    __tablename__ = "client_cards"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=False)
    card_number = Column(String, unique=True, index=True)
    qr_token_hash = Column(String, nullable=False)
    qr_code_path = Column(String)
    issued_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
        nullable=False
    )
    expires_at = Column(DateTime(timezone=True), nullable=False)
    is_active = Column(Boolean, default=True)
    revoked_at = Column(DateTime(timezone=True), nullable=True)
    created_by = Column(Integer)
    client = relationship("Client", back_populates="client_card")


class CardScanLog(Base):
    __tablename__ = "card_scan_logs"

    id = Column(Integer, primary_key=True)
    card_id = Column(UUID(as_uuid=True), ForeignKey("client_cards.id"), nullable=False, index=True)
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=False, index=True)
    scanned_by = Column(Integer, nullable=False)
    pos_id = Column(Integer, nullable=True)
    scanned_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True
    )
    ip_address = Column(String, nullable=False)
    card = relationship("ClientCard")
    client = relationship("Client")


class ClientHeir(Base):
    __tablename__ = "clients_heirs"
    id = Column(Integer, primary_key=True)
    client_id = Column(Integer, ForeignKey("clients.id"))
    first_name = Column(String(255), nullable=False)
    last_name = Column(String(255), nullable=False)
    phone = Column(String(15), nullable=False)
    address = Column(String(255), nullable=False)
    client = relationship("Client", back_populates="heir")


class CardPriceStatus(str, enum.Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"


class CardPrice(Base):
    __tablename__ = "card_prices"
    id = Column(Integer, primary_key=True)
    price = Column(Numeric(12, 2), nullable=False)
    status = Column(PgEnum(CardPriceStatus), default=CardPriceStatus.ACTIVE)
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at = Column(DateTime(timezone=True), nullable=True)


class LoanStatus(str, enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    DISBURSED = "disbursed"
    PARTIALLY_REPAID = "partially_repaid"
    REPAID = "repaid"


class ClientLoan(Base):
    __tablename__ = "client_loans"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=False)
    amount = Column(Numeric(14, 2), nullable=False)
    remaining_amount = Column(Numeric(14, 2), nullable=False)
    status = Column(PgEnum(LoanStatus), default=LoanStatus.PENDING)
    requested_at = Column(DateTime(timezone=True), server_default=func.now())
    approved_at = Column(DateTime(timezone=True), nullable=True)
    disbursed_at = Column(DateTime(timezone=True), nullable=True)
    approved_by = Column(Integer, nullable=True)
    reason = Column(String, nullable=True)
    client = relationship("Client", back_populates="loans")