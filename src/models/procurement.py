from sqlalchemy import Column, Integer, Numeric, DateTime, Text, ForeignKey, Enum as PgEnum, String
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from src.core.database import Base
from datetime import datetime, timezone
import enum


class ProcurementStatus(str, enum.Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    SHIPPED = "SHIPPED"
    RECEIVED = "RECEIVED"
    CANCELLED = "CANCELLED"


class ProcurementReturnStatus(str, enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    CANCELLED = "cancelled"


class Procurement(Base):
    __tablename__ = "procurements"    
    id = Column(Integer, primary_key=True)    
    reference = Column(String(50), nullable=False, unique=True)
    provider_id = Column(Integer, ForeignKey("providers.id"), nullable=False)
    pos_id = Column(Integer, ForeignKey("pos.id"), nullable=False)
    # supplying_pos_id = Column(Integer, ForeignKey("pos.id"), nullable=True)
    created_by_id = Column(Integer, ForeignKey("pos_user.id"), nullable=False)    
    po_date = Column(DateTime(timezone=True), nullable=False, server_default=func.now())  
    expected_delivery_date = Column(DateTime(timezone=True), nullable=True) 
    total_amount = Column(Numeric(12, 2), nullable=False)    
    status = Column(
        PgEnum(ProcurementStatus),
        default=ProcurementStatus.PENDING,
        nullable=False
    )
    # Delivery tracking (added fields)
    delivery_date = Column(DateTime(timezone=True), nullable=True)
    received_by_id = Column(Integer, ForeignKey("pos_user.id"), nullable=True)
    delivery_notes = Column(Text, nullable=True)
    driver_name = Column(String(255), nullable=True)
    driver_phone = Column(String(40), nullable=True)    
    # Document storage
    delivery_note_photo = Column(String(500), nullable=True) 
    receipt_photo = Column(String(500), nullable=True)
    # Terms
    payment_terms = Column(String(255), nullable=True)
    shipping_terms = Column(String(255), nullable=True) 
    # Audit
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    provider = relationship("Provider")
    pos = relationship(
        "POS", 
        back_populates="procurements",
        foreign_keys=[pos_id]
    )
    created_by = relationship(
        "POSUser", 
        foreign_keys=[created_by_id]
    )
    received_by = relationship(
        "POSUser", 
        foreign_keys=[received_by_id]
    )
    purchase_invoice = relationship(
        "PurchaseInvoice", 
        back_populates="procurement", 
        uselist=False
    )
    items = relationship(
        "ProcurementItem",
        back_populates="procurement",
        cascade="all, delete-orphan"
    )
    returns = relationship("ProcurementReturn", back_populates="procurement")
        
    @property
    def warehouse(self):
        return self.pos.warehouse if self.pos else None

    @property
    def warehouse_id(self):
        return self.pos.warehouse_id if self.pos else None
    
    @property
    def due_amount(self):
        if self.purchase_invoice:
            return self.purchase_invoice.due_amount
        return self.total_amount
    
    @property
    def payment_status(self):
        if not self.purchase_invoice:
            return "no_invoice"
        
        due = self.due_amount
        if due == 0:
            return "paid"
        elif due < self.total_amount:
            return "partial"
        return "due"
    
    @property
    def item_count(self):
        return len(self.items) if self.items else 0
    
    @property
    def total_quantity(self):
        """Total quantity across all items"""
        return sum(item.qty for item in self.items) if self.items else 0
            
    @property
    def delivery_info(self):
        """Structured delivery information"""
        if not self.is_delivered:
            return None
        
        return {
            "date": self.delivery_date,
            "received_by": self.received_by.username if self.received_by else None,
            "driver": self.driver_name,
            "driver_phone": self.driver_phone,
            "notes": self.delivery_notes,
            "has_delivery_note_photo": bool(self.delivery_note_photo),
            "has_receipt_photo": bool(self.receipt_photo)
        }
    
    @property
    def days_since_order(self):
        """Days since order was placed"""
        if self.po_date:
            delta = datetime.now(timezone.utc) - self.po_date
            return delta.days
        return 0
        
    def __repr__(self):
        return f"<Procurement {self.reference} ({self.status.value})>"


class ProcurementItem(Base):
    __tablename__ = "procurement_items"
    id = Column(Integer, primary_key=True)
    procurement_id = Column(Integer, ForeignKey("procurements.id"), nullable=False)
    product_variant_id = Column(Integer, ForeignKey("product_variants.id"), nullable=False)
    qty = Column(Numeric(12, 2), nullable=False)
    price = Column(Numeric(12, 2), nullable=False)
    returned_qty = Column(Numeric(12,2), default=0)
    procurement = relationship("Procurement", back_populates="items")
    product_variant = relationship("ProductVariant")


class ProcurementReturn(Base):
    __tablename__ = "procurement_returns"

    id = Column(Integer, primary_key=True)
    reference = Column(String(50), unique=True, nullable=False)
    procurement_id = Column(Integer, ForeignKey("procurements.id"), nullable=False)
    initiator_pos_id = Column(Integer, ForeignKey("pos.id"), nullable=False)
    provider_pos_id = Column(Integer, ForeignKey("pos.id"), nullable=False)
    status = Column(PgEnum(ProcurementReturnStatus), default=ProcurementReturnStatus.PENDING)
    reason = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), default=datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), onupdate=datetime.now(timezone.utc))

    # relationships
    procurement = relationship("Procurement", back_populates="returns")
    initiator_pos = relationship("POS", foreign_keys=[initiator_pos_id])
    provider_pos = relationship("POS", foreign_keys=[provider_pos_id])
    items = relationship(
        "ProcurementReturnItem",
        back_populates="return_request",
        cascade="all, delete-orphan"
    )

class ProcurementReturnItem(Base):
    __tablename__ = "procurement_return_items"

    id = Column(Integer, primary_key=True)
    return_id = Column(Integer, ForeignKey("procurement_returns.id"), nullable=False)
    product_variant_id = Column(Integer, ForeignKey("product_variants.id"), nullable=False)
    quantity = Column(Numeric(12, 2), nullable=False)
    created_at = Column(DateTime(timezone=True), default=datetime.now(timezone.utc))

    return_request = relationship("ProcurementReturn", back_populates="items")