from sqlalchemy import Column, Integer, String, Numeric, Boolean, ForeignKey, Date
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from src.core.database import Base


class Inventory(Base):
    __tablename__ = "inventory"

    id = Column(Integer, primary_key=True)
    product_variant_id = Column(
        Integer,
        ForeignKey("product_variants.id"),
        nullable=False
    )
    created_at = Column(Date())
    warehouse_id = Column(
        Integer,
        ForeignKey("warehouses.id"),
        nullable=False
    )

    quantity = Column(Numeric(12, 2), default=0)
    reserved_quantity = Column(Numeric(12, 2), default=0)

    product_variant = relationship("ProductVariant", back_populates="inventory_items")
    warehouse = relationship("Warehouse", back_populates="inventory_items")
\

class Warehouse(Base):
    __tablename__ = "warehouses"

    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    location = Column(String(255))
    is_active = Column(Boolean, default=True)

    inventory_items = relationship(
        "Inventory",
        back_populates="warehouse",
        cascade="all, delete-orphan"
    )

    procurements = relationship(
        "Procurement",
        back_populates="warehouse",
        cascade="all, delete-orphan"
    )
