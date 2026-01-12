from sqlalchemy import Column, Integer, Numeric, DateTime, ForeignKey, Enum as PgEnum, String
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from src.core.database import Base
import enum


class ProcurementStatus(str, enum.Enum):
    PENDING = "pending"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"


class Procurement(Base):
    __tablename__ = "procurements"

    id = Column(Integer, primary_key=True)
    reference = Column(String(50), nullable=False, unique=True)

    provider_id = Column(Integer, ForeignKey("providers.id"), nullable=False)
    pos_id = Column(Integer, ForeignKey("pos.id"), nullable=False)
    created_by_id = Column(Integer, ForeignKey("pos_user.id"), nullable=False)

    warehouse_id = Column(Integer, ForeignKey("warehouses.id"))
    purchase_invoice_id = Column(Integer, ForeignKey("purchase_invoices.id"))

    total_amount = Column(Numeric(12, 2), nullable=False)
    date = Column(DateTime(timezone=True), nullable=False)

    status = Column(
        PgEnum(ProcurementStatus),
        default=ProcurementStatus.PENDING,
        nullable=False
    )

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # relationships
    provider = relationship("Provider")
    pos = relationship("POS", back_populates="procurements")
    created_by = relationship("POSUser")
    warehouse = relationship("Warehouse", back_populates="procurements")
    purchase_invoice = relationship("PurchaseInvoice")

    items = relationship(
        "ProcurementItem",
        back_populates="procurement",
        cascade="all, delete-orphan"
    )

    @property
    def due_amount(self):
        if self.purchase_invoice:
            return self.purchase_invoice.total_amount - self.purchase_invoice.paid_amount
        return self.total_amount

    @property
    def payment_status(self):
        due = self.due_amount
        if due == 0:
            return "paid"
        elif due < self.total_amount:
            return "partial"
        return "due"


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
