from sqlalchemy import (
    Column, Integer, String, Boolean, ForeignKey, Numeric, Enum
)
from sqlalchemy.orm import relationship
from src.core.database import Base
import enum
from decimal import Decimal


# ---------------- ENUMS ----------------

class ProductType(str, enum.Enum):
    UNIQUE = "unique"
    VARIABLE = "variable"
    COMBO = "combo"


class TaxInclusion(str, enum.Enum):
    EXCLUSIVE = "exclusive"   # HT
    INCLUSIVE = "inclusive"   # TTC
    NONE = "none"             # Tax exempt


# ---------------- CATEGORY ----------------

class Category(Base):
    __tablename__ = "categories"

    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)

    products = relationship("Product", back_populates="category")

    def __repr__(self):
        return f"<Category {self.name}>"

    
# ---------------- PRODUCT ----------------

class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True)

    name = Column(String(255), nullable=False)
    category_id = Column(Integer, ForeignKey("categories.id"), nullable=False)

    brand = Column(String(50))
    is_active = Column(Boolean, default=True)

    type = Column(Enum(ProductType), default=ProductType.UNIQUE)

    image_url = Column(String(255), nullable=True)

    # Tax configuration
    tax_id = Column(Integer, ForeignKey("taxes.id"), nullable=True)
    tax_inclusion = Column(
        Enum(TaxInclusion),
        default=TaxInclusion.EXCLUSIVE
    )

    # Optional custom fields
    custom_field1 = Column(String(255))
    custom_field2 = Column(String(255))
    custom_field3 = Column(String(255))
    custom_field4 = Column(String(255))

    # Relationships
    category = relationship("Category", back_populates="products")
    tax = relationship("Tax", back_populates="products")

    variants = relationship(
        "ProductVariant",
        back_populates="product",
        cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<Product {self.name}>"

# ---------------- PRODUCT VARIANT ----------------

class ProductVariant(Base):
    __tablename__ = "product_variants"

    id = Column(Integer, primary_key=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)

    sku = Column(String(120), unique=True, nullable=False)

    purchase_price = Column(Numeric(12, 2), nullable=False)
    sale_price = Column(Numeric(12, 2), nullable=False)

    image_url = Column(String(255), nullable=True)

    product = relationship("Product", back_populates="variants")

    inventory_items = relationship(
        "Inventory",
        back_populates="product_variant"
    )
    
    # ---------------- PRICING HELPERS ----------------

    @property
    def price_ht(self):
        """
        Price before tax (HT)
        """
        product = self.product
        if not product.tax or product.tax_inclusion in ["exclusive", "none"]:
            return self.sale_price

        rate = Decimal(product.tax.rate) / Decimal(100)
        return self.sale_price / (1 + rate)

    @property
    def price_ttc(self):
        """
        Price including tax (TTC)
        """
        product = self.product
        if not product.tax or product.tax_inclusion == "none":
            return self.sale_price

        rate = Decimal(product.tax.rate) / Decimal(100)

        if product.tax_inclusion == "inclusive":
            return self.sale_price

        return self.sale_price * (1 + rate)

    @property
    def tax_amount(self):
        """
        Tax amount per unit
        """
        return self.price_ttc - self.price_ht

    @property
    def total_stock(self):
        """
        Total quantity across all warehouses
        """
        return sum(inv.quantity for inv in self.inventory_items)

    def __repr__(self):
        return f"<Variant {self.sku}>"
