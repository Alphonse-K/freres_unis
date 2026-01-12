from sqlalchemy import Column, Integer, String, Numeric, Boolean, Enum
from sqlalchemy.orm import relationship
from src.core.database import Base
import enum


class TaxType(str, enum.Enum):
    SALE = "sale"
    PURCHASE = "purchase"
    BOTH = "both"


class Tax(Base):
    __tablename__ = "taxes"

    id = Column(Integer, primary_key=True)

    name = Column(String(100), nullable=False)      # e.g. TVA 18%
    rate = Column(Numeric(5, 2), nullable=False)   # e.g. 18.00
    type = Column(Enum(TaxType), nullable=False)

    is_active = Column(Boolean, default=True)

    products = relationship("Product", back_populates="tax")

    def __repr__(self):
        return f"<Tax {self.name} ({self.rate}%)>"
