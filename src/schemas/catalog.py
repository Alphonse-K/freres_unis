# src/schemas/product.py
from typing import Optional, List
from decimal import Decimal
from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime
from src.models.catalog import PriceType

# -------------------------------
# CATEGORY SCHEMAS
# -------------------------------

class CategoryBase(BaseModel):
    name: str = Field(..., max_length=255)


class CategoryCreate(CategoryBase):
    pass


class CategoryUpdate(BaseModel):
    name: Optional[str] = None


class CategoryLight(BaseModel):
    id: int
    name: str
    model_config = ConfigDict(from_attributes=True)


class CategoryOut(CategoryBase):
    id: int
    products: List["ProductOut"] = []
    model_config = ConfigDict(from_attributes=True)


# -------------------------------
# PRODUCT SCHEMAS
# -------------------------------
class ProductLight(BaseModel):
    id: int
    name: str
    image_url: Optional[str] = None
    model_config = ConfigDict(from_attributes=True)

    
class ProductBase(BaseModel):
    name: str = Field(..., max_length=255)
    category_id: int
    brand: str | None = None
    is_active: bool | None = True
    type: str | None = "unique"

    tax_id: Optional[int] = None
    tax_inclusion: Optional[str] = "exclusive"


class ProductCreate(ProductBase):
    pass


class ProductUpdate(BaseModel):
    name: str | None = None
    category_id: str | None = None
    brand: str | None = None
    is_active: str | None = None
    type: str | None = None
    tax_id: str | None = None
    tax_inclusion: str | None = None


class ProductOut(ProductBase):
    id: int
    category: Optional[CategoryLight] = None
    image_url: str | None = None
    variants: List["ProductVariantLight"] = []
    model_config = ConfigDict(from_attributes=True)

# -------------------------------
# PRODUCT VARIANT SCHEMAS
# -------------------------------
# ProductVariant schemas

class ProductVariantBase(BaseModel):
    product_id: int
    name: str
    sku: str = Field(..., max_length=120)
    image_url: Optional[str] = None


class ProductPriceLight(BaseModel):
    id: int
    qualification: PriceType
    type_sold_in: str
    quantity: int
    content: int
    purchase_price: Decimal
    sale_price: Decimal
    model_config = ConfigDict(from_attributes=True)


class ProductVariantOut(BaseModel):
    id: int
    product_id: int
    name: str
    sku: str
    image_url: Optional[str] = None
    price_ht: Optional[Decimal] = None
    price_ttc: Optional[Decimal] = None
    tax_amount: Optional[Decimal] = None
    total_stock: Optional[Decimal] = None
    prices: list[ProductPriceLight] = []
    model_config = ConfigDict(from_attributes=True)


class ProductVariantCreate(ProductVariantBase):
    pass 


class ProductVariantUpdate(BaseModel):
    product_id: Optional[int] = None
    name:  str | None = None
    sku: Optional[str] = None
    image_url: Optional[str] = None


class ProductVariantLight(BaseModel):
    id: int
    name: str
    sku: str
    image_url: Optional[str] = None
    model_config = ConfigDict(from_attributes=True)

class ProductPriceBase(BaseModel):
    product_variant_id: int
    qualification: PriceType = Field(..., example="retail")
    type_sold_in: str = Field(..., example="Carton")
    quantity: int
    content: int
    purchase_price: Decimal = Field(..., ge=0)
    sale_price: Decimal = Field(..., ge=0)


class ProductPriceCreate(ProductPriceBase):
    pass

class ProductPriceUpdate(BaseModel):
    qualification: PriceType | None = None
    type_sold_int: str | None = None
    quantity: int | None = None
    content: int | None = None
    purchase_price: Optional[Decimal] = None
    sale_price: Optional[Decimal] = None


class ProductPriceResponse(ProductPriceBase):
    id: int
    created_at: Optional[datetime]
    model_config = ConfigDict(from_attributes=True)
    
# -------------------------------
# Pydantic v2: rebuild forward references
# -------------------------------
CategoryOut.model_rebuild()
ProductOut.model_rebuild()
ProductVariantOut.model_rebuild()
