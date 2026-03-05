from fastapi import HTTPException, status, UploadFile
from sqlalchemy.orm import Session, joinedload, selectinload
from typing import List, Optional
import logging
from decimal import Decimal


from src.utils.file_upload import save_image
from src.models.catalog import Product, ProductVariant, Category, ProductPrice
from src.schemas.catalog import (
    ProductCreate, ProductUpdate,
    ProductVariantCreate, ProductVariantUpdate, 
    CategoryCreate, CategoryUpdate, ProductPriceCreate, 
    ProductPriceUpdate, ProductPriceResponse
)


logger = logging.getLogger(__name__)

class CategoryService:

    @staticmethod
    def create_category(db: Session, data: CategoryCreate) -> Category:
        existing = db.query(Category).filter(
            Category.name.ilike(data.name)
        ).first()

        if existing:
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                detail="Category already exists"
            )

        category = Category(**data.model_dump())
        db.add(category)
        db.commit()
        db.refresh(category)
        return category

    @staticmethod
    def list_categories(db: Session) -> List[Category]:
        return db.query(Category).order_by(Category.name.asc()).all()

    @staticmethod
    def get_category(db: Session, category_id: int) -> Category:
        category = db.query(Category).filter(
            Category.id == category_id
        ).first()

        if not category:
            raise HTTPException(
                status.HTTP_404_NOT_FOUND,
                detail="Category not found"
            )

        return category

    @staticmethod
    def update_category(
        db: Session,
        category_id: int,
        data: CategoryUpdate
    ) -> Category:
        category = db.query(Category).filter(
            Category.id == category_id
        ).first()

        if not category:
            raise HTTPException(
                status.HTTP_404_NOT_FOUND,
                detail="Category not found"
            )

        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(category, field, value)

        db.commit()
        db.refresh(category)
        return category

    @staticmethod
    def delete_category(db: Session, category_id: int):
        category = db.query(Category).filter(
            Category.id == category_id
        ).first()

        if not category:
            raise HTTPException(
                status.HTTP_404_NOT_FOUND,
                detail="Category not found"
            )

        if category.products:
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                detail="Cannot delete category with products"
            )

        db.delete(category)
        db.commit()


class CatalogService:

    # ========================
    # PRODUCT
    # ========================

    @staticmethod
    def create_product(db: Session, data: ProductCreate) -> Product:
        category = db.query(Category).filter(Category.id == data.category_id).first()
        if not category:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Category not found")

        product = Product(**data.model_dump())
        db.add(product)
        db.commit()
        db.refresh(product)
        return product
    
    @staticmethod
    def upload_product_image(
        db: Session,
        product_id: int,
        file: UploadFile
    ) -> Product:
        product = db.query(Product).filter(Product.id == product_id).first()
        if not product:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Product not found")

        product.image_url = save_image(file, "products")

        db.commit()
        db.refresh(product)
        return product

    @staticmethod
    def list_products(db: Session, active_only: bool = True) -> List[Product]:
        query = db.query(Product).options(
            joinedload(Product.category),
            joinedload(Product.variants)
        )
        if active_only:
            query = query.filter(Product.is_active == True)

        return query.all()

    @staticmethod
    def get_product(db: Session, product_id: int) -> Product:
        product = db.query(Product).options(
            joinedload(Product.category),
            joinedload(Product.variants)
        ).filter(Product.id == product_id).first()

        if not product:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Product not found")

        return product

    @staticmethod
    def update_product(db: Session, product_id: int, data: ProductUpdate) -> Product:
        product = db.query(Product).filter(Product.id == product_id).first()
        if not product:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Product not found")

        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(product, field, value)

        db.commit()
        db.refresh(product)
        return product

    # ========================
    # PRODUCT VARIANT
    # ========================

    @staticmethod
    def create_variant(db: Session, data: ProductVariantCreate) -> ProductVariant:
        product = db.query(Product).filter(Product.id == data.product_id).first()
        if not product:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Product not found")

        variant = ProductVariant(**data.model_dump())
        db.add(variant)
        db.commit()
        db.refresh(variant)
        return variant
    
    @staticmethod
    def upload_variant_image(
        db: Session,
        variant_id: int,
        file: UploadFile
    ) -> ProductVariant:
        variant = db.query(ProductVariant).filter(
            ProductVariant.id == variant_id
        ).first()

        if not variant:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Variant not found")

        variant.image_url = save_image(file, "variants")

        db.commit()
        db.refresh(variant)
        return variant

    @staticmethod
    def update_variant(
        db: Session,
        variant_id: int,
        data: ProductVariantUpdate
    ) -> ProductVariant:
        variant = db.query(ProductVariant).filter(
            ProductVariant.id == variant_id
        ).first()

        if not variant:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Variant not found")

        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(variant, field, value)

        db.commit()
        db.refresh(variant)
        return variant

    def list_product_variants(db: Session):
        # eager load prices relationship
        variants = db.query(ProductVariant).options(
            selectinload(ProductVariant.prices)
        ).all()

        result = []
        for variant in variants:
            # find active price
            active_price = next(
                (p for p in variant.prices if p.is_active), None
            )

            variant_data = {
                "id": variant.id,
                "name": variant.name,
                "sku": variant.sku,
                "image_url": variant.image_url,
                "product_id": variant.product_id,
                "price_ht": active_price.sale_price if active_price else None,
                "price_ttc": active_price.sale_price if active_price else None,  # optionally apply tax calculation
                "tax_amount": None,  # you can compute based on product tax
                "total_stock": sum(inv.quantity for inv in variant.inventory_items),
                "prices": [
                    {
                        "id": p.id,
                        "qualification": p.qualification,
                        "purchase_price": p.purchase_price,
                        "sale_price": p.sale_price,
                        "is_active": p.is_active
                    } for p in variant.prices
                ]
            }
            result.append(variant_data)

        return result

class ProductPriceService:

    @staticmethod
    def create_price(db: Session, data: ProductPriceCreate) -> ProductPrice:

        variant = db.query(ProductVariant).filter(
            ProductVariant.id == data.product_variant_id
        ).first()

        if not variant:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Product variant not found"
            )

        if data.is_active:
            db.query(ProductPrice).filter(
                ProductPrice.product_variant_id == data.product_variant_id,
                ProductPrice.is_active == True
            ).update({"is_active": False})

        price = ProductPrice(**data.dict())

        db.add(price)
        db.commit()
        db.refresh(price)

        return price


    @staticmethod
    def list_prices(db: Session, variant_id: int) -> List[ProductPrice]:

        return db.query(ProductPrice).filter(
            ProductPrice.product_variant_id == variant_id
        ).all()


    @staticmethod
    def update_price(db: Session, price_id: int, data: ProductPriceUpdate):

        price = db.query(ProductPrice).filter(
            ProductPrice.id == price_id
        ).first()

        if not price:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Price not found"
            )

        update_data = data.dict(exclude_unset=True)

        if update_data.get("is_active") is True:
            db.query(ProductPrice).filter(
                ProductPrice.product_variant_id == price.product_variant_id,
                ProductPrice.is_active == True
            ).update({"is_active": False})

        for key, value in update_data.items():
            setattr(price, key, value)

        db.commit()
        db.refresh(price)

        return price


    @staticmethod
    def delete_price(db: Session, price_id: int):

        price = db.query(ProductPrice).filter(
            ProductPrice.id == price_id
        ).first()

        if not price:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Price not found"
            )

        db.delete(price)
        db.commit()

        return {"message": "Price deleted"}