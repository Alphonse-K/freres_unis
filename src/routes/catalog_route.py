from fastapi import APIRouter, Depends, UploadFile, File
from sqlalchemy.orm import Session
from typing import List

from src.core.database import get_db
from src.services.catalog_service import CatalogService, CategoryService
from src.schemas.catalog import (
    ProductCreate, ProductUpdate, ProductOut,
    ProductVariantCreate, ProductVariantUpdate, ProductVariantOut,
    CategoryUpdate, CategoryOut, CategoryCreate
)

product_router = APIRouter(prefix="/catalog", tags=["Product Catalog"])


# ========================
# PRODUCTS
# ========================

@product_router.post("/products/category", response_model=CategoryOut)
def create_category(
    data: CategoryCreate,
    db: Session = Depends(get_db)
):
    return CategoryService.create_category(db, data)


@product_router.get("/products/category", response_model=List[CategoryOut])
def list_categories(db: Session = Depends(get_db)):
    return CategoryService.list_categories(db)


@product_router.get("/products/category{category_id}", response_model=CategoryOut)
def get_category(
    category_id: int,
    db: Session = Depends(get_db)
):
    return CategoryService.get_category(db, category_id)


@product_router.put("/products/category{category_id}", response_model=CategoryOut)
def update_category(
    category_id: int,
    data: CategoryUpdate,
    db: Session = Depends(get_db)
):
    return CategoryService.update_category(db, category_id, data)

@product_router.post("/products", response_model=ProductOut)
def create_product(data: ProductCreate, db: Session = Depends(get_db)):
    return CatalogService.create_product(db, data)

@product_router.post("/{product_id}/image")
def upload_product_image(
    product_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    return CatalogService.upload_product_image(db, product_id, file)

@product_router.get("/products", response_model=List[ProductOut])
def list_products(db: Session = Depends(get_db)):
    return CatalogService.list_products(db)


@product_router.get("/products/{product_id}", response_model=ProductOut)
def get_product(product_id: int, db: Session = Depends(get_db)):
    return CatalogService.get_product(db, product_id)


@product_router.put("/products/{product_id}", response_model=ProductOut)
def update_product(
    product_id: int,
    data: ProductUpdate,
    db: Session = Depends(get_db)
):
    return CatalogService.update_product(db, product_id, data)


# ========================
# VARIANTS
# ========================

@product_router.post("/variants", response_model=ProductVariantOut)
def create_variant(data: ProductVariantCreate, db: Session = Depends(get_db)):
    return CatalogService.create_variant(db, data)

@product_router.post("/variants/{variant_id}/image")
def upload_variant_image(
    variant_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    return CatalogService.upload_variant_image(db, variant_id, file)

@product_router.put("/variants/{variant_id}", response_model=ProductVariantOut)
def update_variant(
    variant_id: int,
    data: ProductVariantUpdate,
    db: Session = Depends(get_db)
):
    return CatalogService.update_variant(db, variant_id, data)


@product_router.get("/variants", response_model=List[ProductVariantOut])
def list_variants(db: Session = Depends(get_db)):
    return CatalogService.list_variants(db)
