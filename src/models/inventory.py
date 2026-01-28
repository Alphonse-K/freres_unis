from sqlalchemy import Column, Integer, String, Numeric, Boolean, ForeignKey, Date, DateTime, func
from sqlalchemy.orm import relationship
from src.core.database import Base


class Inventory(Base):
    __tablename__ = "inventory"
    id = Column(Integer, primary_key=True)
    product_variant_id = Column(
        Integer,
        ForeignKey("product_variants.id"),
        nullable=False
    )
    warehouse_id = Column(
        Integer,
        ForeignKey("warehouses.id"),
        nullable=False
    )
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    quantity = Column(Numeric(12, 2), default=0)
    reserved_quantity = Column(Numeric(12, 2), default=0)
    @property
    def available_quantity(self):
        """Quantity available for sale (total - reserved)"""
        return self.quantity - self.reserved_quantity
    
    product_variant = relationship("ProductVariant", back_populates="inventory_items")
    warehouse = relationship("Warehouse", back_populates="inventory_items")


class Warehouse(Base):
    __tablename__ = "warehouses"
    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    location = Column(String(255))
    is_active = Column(Boolean, default=True)
    pos_id = Column(Integer, ForeignKey("pos.id"), nullable=True, unique=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    inventory_items = relationship(
        "Inventory",
        back_populates="warehouse",
        cascade="all, delete-orphan"
    )
    pos = relationship("POS", back_populates="warehouse", uselist=False)


