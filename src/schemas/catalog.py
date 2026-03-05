# src/schemas/product.py
from typing import Optional, List
from decimal import Decimal
from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime


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
    brand: Optional[str] = None
    is_active: Optional[bool] = True
    type: Optional[str] = "unique"

    tax_id: Optional[int] = None
    tax_inclusion: Optional[str] = "exclusive"

    custom_field1: Optional[str] = None
    custom_field2: Optional[str] = None
    custom_field3: Optional[str] = None
    custom_field4: Optional[str] = None


class ProductCreate(ProductBase):
    pass


class ProductUpdate(BaseModel):
    name: Optional[str] = None
    category_id: Optional[int] = None
    brand: Optional[str] = None
    is_active: Optional[bool] = None
    type: Optional[str] = None
    tax_id: Optional[int] = None
    tax_inclusion: Optional[str] = None
    custom_field1: Optional[str] = None
    custom_field2: Optional[str] = None
    custom_field3: Optional[str] = None
    custom_field4: Optional[str] = None


class ProductOut(ProductBase):
    id: int
    category: Optional[CategoryLight] = None
    image_url: Optional[str] = None
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


class ProductVariantCreate(ProductVariantBase):
    pass 


class ProductVariantUpdate(BaseModel):
    product_id: Optional[int] = None
    name:  str | None = None
    sku: Optional[str] = None
    image_url: Optional[str] = None


class ProductVariantOut(ProductVariantBase):
    id: int
    product: Optional[ProductLight] = None
    # computed properties
    price_ht: Optional[Decimal] = None
    price_ttc: Optional[Decimal] = None
    tax_amount: Optional[Decimal] = None
    total_stock: Optional[Decimal] = None
    model_config = ConfigDict(from_attributes=True)


class ProductVariantLight(BaseModel):
    id: int
    name: str
    sku: str
    image_url: Optional[str] = None
    model_config = ConfigDict(from_attributes=True)

class ProductPriceBase(BaseModel):
    product_variant_id: int
    qualification: str = Field(..., example="Retail")
    purchase_price: Decimal = Field(..., ge=0)
    sale_price: Decimal = Field(..., ge=0)


class ProductPriceCreate(ProductPriceBase):
    is_active: Optional[bool] = True


class ProductPriceUpdate(BaseModel):
    qualification: Optional[str] = None
    purchase_price: Optional[Decimal] = None
    sale_price: Optional[Decimal] = None
    is_active: Optional[bool] = None


class ProductPriceResponse(ProductPriceBase):
    id: int
    is_active: bool
    created_at: Optional[datetime]
    model_config = ConfigDict(from_attributes=True)
    
# -------------------------------
# Pydantic v2: rebuild forward references
# -------------------------------
CategoryOut.model_rebuild()
ProductOut.model_rebuild()
ProductVariantOut.model_rebuild()
