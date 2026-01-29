# src/models/providers.py
from sqlalchemy import Column, Integer, String, Numeric, Boolean, Date, DateTime, Text, Enum as PgEnum, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from src.core.database import Base
from datetime import datetime, timezone
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy import case
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
    updated_at = Column(Date(), onupdate=func.now())

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
    # Link to Procurement (for tracking)
    procurement_id = Column(Integer, ForeignKey("procurements.id"), nullable=True)    
    invoice_number = Column(String(100), nullable=False)
    invoice_date = Column(DateTime(timezone=True), nullable=False)  
    posting_date = Column(DateTime(timezone=True), nullable=False)  
    due_date = Column(DateTime(timezone=True), nullable=True)     
    total_amount = Column(Numeric(14, 2), nullable=False)
    paid_amount = Column(Numeric(14, 2), default=0)    
    status = Column(
        PgEnum(PurchaseInvoiceStatus),
        default=PurchaseInvoiceStatus.DRAFT,
        nullable=False
    )    
    # Document references
    po_reference = Column(String(50), nullable=True)  # Purchase Order reference
    delivery_note_ref = Column(String(50), nullable=True)  
    notes = Column(String(255))    
    # Audit
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())    
    # Relationships
    provider = relationship("Provider", back_populates="purchase_invoices")
    returns = relationship("PurchaseReturn", back_populates="purchase_invoice")
    procurement = relationship("Procurement", back_populates="purchase_invoice", uselist=False, foreign_keys=[procurement_id])
    payments = relationship(
        "ProviderPayment",
        back_populates="purchase_invoice",
        cascade="all, delete-orphan"
    )
    
    # =========================
    # Hybrid / Queryable helpers
    # =========================

    @hybrid_property
    def due_amount(self):
        return self.total_amount - self.paid_amount

    @due_amount.expression
    def due_amount(cls):
        return cls.total_amount - cls.paid_amount


    @hybrid_property
    def is_fully_paid(self):
        return self.paid_amount >= self.total_amount

    @is_fully_paid.expression
    def is_fully_paid(cls):
        return cls.paid_amount >= cls.total_amount

    @hybrid_property
    def is_overdue(self):
        if self.due_date is None:
            return False
        return self.due_amount > 0 and datetime.now(timezone.utc) > self.due_date

    @is_overdue.expression
    def is_overdue(cls):
        return case(
            (
                (cls.due_date.isnot(None)) &
                ((cls.total_amount - cls.paid_amount) > 0) &
                (cls.due_date < func.now()),
                True
            ),
            else_=False
        )
    
    def __repr__(self):
        return f"<PurchaseInvoice {self.invoice_number} ({self.status.value})>"


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
    purchase_invoice_id = Column(
        Integer,
        ForeignKey("purchase_invoices.id"),
        nullable=True
    )
    payment_method = Column(PgEnum(PaymentMethod), nullable=False)  # cash, bank, mobile, etc.
    reference = Column(String(100))      # receipt / transaction id
    notes = Column(String(255))

    # relationships
    provider = relationship("Provider", back_populates="payments")
    purchase_invoice = relationship(
            "PurchaseInvoice",
            back_populates="payments",
            foreign_keys=[purchase_invoice_id]
        )
