# src/models/providers.py
from sqlalchemy import Column, Integer, String, Numeric, Boolean, Date, Text, Enum as PgEnum, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from src.core.database import Base
import enum


class PurchaseInvoiceStatus(enum.Enum):
    DRAFT = "draft"
    PARTIALLY_PAID = "partially_paid"
    PENDING = "pending"
    PAID = "paid"
    CANCELLED = "cancelled"


class PaymentMethod(str, enum.Enum):
    CASH = "cash"
    BANK_TRANSFER = "bank_transfer"
    MOBILE_MONEY = "mobile_money"
    CHEQUE = "cheque"
    CARD = "card"
    OTHER = "other"


class Provider(Base):
    __tablename__ = "providers"

    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    phone = Column(String(40))
    email = Column(String(255))
    is_active = Column(Boolean, default=True)

    # --- Balances ---
    opening_balance = Column(Numeric(14, 2), default=0)
    anticipated_balance = Column(Numeric(14, 2), default=0)
    current_balance = Column(Numeric(14, 2), default=0)
    created_at = Column(Date(), server_default=func.now())

    # --- Relationships ---
    addresses = relationship(
        "Address",
        back_populates="provider",
        cascade="all, delete-orphan"
    )

    purchase_invoices = relationship("PurchaseInvoice", back_populates="provider")
    purchase_returns = relationship("PurchaseReturn", back_populates="provider")
    payments = relationship("ProviderPayment", back_populates="provider")


class PurchaseInvoice(Base):
    __tablename__ = "purchase_invoices"

    id = Column(Integer, primary_key=True)

    provider_id = Column(Integer, ForeignKey("providers.id"), nullable=False)

    invoice_number = Column(String(100), nullable=False)
    invoice_date = Column(Date(), nullable=False)
    posting_date = Column(Date(), nullable=False)

    total_amount = Column(Numeric(14, 2), nullable=False)
    paid_amount = Column(Numeric(14, 2), default=0)

    status = Column(
        PgEnum(PurchaseInvoiceStatus),
        default=PurchaseInvoiceStatus.DRAFT,
        nullable=False
    )

    notes = Column(String(255))

    # relationships
    provider = relationship("Provider", back_populates="purchase_invoices")
    returns = relationship("PurchaseReturn", back_populates="purchase_invoice")


class PurchaseReturn(Base):
    __tablename__ = "purchase_returns"

    id = Column(Integer, primary_key=True)

    provider_id = Column(Integer, ForeignKey("providers.id"), nullable=False)
    purchase_invoice_id = Column(
        Integer,
        ForeignKey("purchase_invoices.id"),
        nullable=False
    )

    return_date = Column(Date(), nullable=False)
    amount = Column(Numeric(14, 2), nullable=False)

    reason = Column(String(255))

    # relationships
    provider = relationship("Provider", back_populates="purchase_returns")
    purchase_invoice = relationship("PurchaseInvoice", back_populates="returns")


class ProviderPayment(Base):
    __tablename__ = "provider_payments"

    id = Column(Integer, primary_key=True)

    provider_id = Column(Integer, ForeignKey("providers.id"), nullable=False)

    payment_date = Column(Date(), nullable=False)
    amount = Column(Numeric(14, 2), nullable=False)

    payment_method = Column(PgEnum(PaymentMethod), nullable=False)  # cash, bank, mobile, etc.
    reference = Column(String(100))      # receipt / transaction id
    notes = Column(String(255))

    # relationships
    provider = relationship("Provider", back_populates="payments")
