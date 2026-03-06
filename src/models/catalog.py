from sqlalchemy import (
    Column, Integer, String, Boolean, ForeignKey, Numeric, Enum, DateTime, func, UniqueConstraint
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
    EXCLUSIVE = "exclusive"   
    INCLUSIVE = "inclusive"  
    NONE = "none"


class PriceType(str, enum.Enum):
    PURCHASE = "purchase"
    SALE = "sale"
    WHOLESALE = "wholesale"
    PROMOTION = "promotion"


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
    name = Column(String(255), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    sku = Column(String(120), unique=True, nullable=False)
    image_url = Column(String(255), nullable=True)
    product = relationship("Product", back_populates="variants")
    inventory_items = relationship(
        "Inventory",
        back_populates="product_variant"
    )
    prices = relationship(
        "ProductPrice",
        back_populates="variant",
        cascade="all, delete-orphan"
    )

    # ---------------- PRICING HELPERS ----------------
    @property
    def purchase_price(self):
        price = next((p for p in self.prices if p.is_active), None)
        return price.purchase_price if price else None

    @property
    def sale_price(self):
        price = next((p for p in self.prices if p.is_active), None)
        return price.sale_price if price else None

    @property
    def price_ht(self):
        """
        Price before tax
        """
        sale_price = self.sale_price
        if not sale_price:
            return None

        product = self.product

        if not product.tax or product.tax_inclusion in ["exclusive", "none"]:
            return sale_price

        rate = Decimal(product.tax.rate) / Decimal(100)
        return sale_price / (1 + rate)

    @property
    def price_ttc(self):
        """
        Price including tax
        """
        sale_price = self.sale_price
        if not sale_price:
            return None

        product = self.product

        if not product.tax or product.tax_inclusion == "none":
            return sale_price

        rate = Decimal(product.tax.rate) / Decimal(100)

        if product.tax_inclusion == "inclusive":
            return sale_price

        return sale_price * (1 + rate)

    @property
    def tax_amount(self):
        if not self.sale_price:
            return None

        return self.price_ttc - self.price_ht

    @property
    def total_stock(self):
        """
        Total quantity across warehouses
        """
        return sum(inv.quantity for inv in self.inventory_items)

    def __repr__(self):
        return f"<Variant {self.sku}>"


class ProductPrice(Base):
    __tablename__ = "product_prices"
    id = Column(Integer, primary_key=True)
    product_variant_id = Column(
        Integer,
        ForeignKey("product_variants.id"),
        nullable=False
    )
    qualification = Column(String(255), nullable=False)
    whole_sale_quantity = Column(Integer, nullable=False)
    retail_sale_quantity = Column(Integer, nullable=False)
    purchase_price = Column(Numeric(12, 2), nullable=False)
    sale_price = Column(Numeric(12, 2), nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now()
    )
    variant = relationship(
        "ProductVariant",
        back_populates="prices"
    )

    def __repr__(self):
        return f"<Price purchase={self.purchase_price} sale={self.sale_price}>"