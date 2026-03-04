from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from src.core.permissions import Permissions
from src.core.custom_exceptions import *
from src.schemas.taxes import *
from src.models.taxes import *


class TaxService:

    @staticmethod
    def create_tax(db: Session, data: TaxCreate) -> Tax:
        existing = db.query(Tax).filter(Tax.name == data.name).first()
        if existing:
            raise BusinessRuleException("Tax with this name already exists")

        tax = Tax(
            name=data.name,
            rate=data.rate,
            type=data.type,
            is_active=data.is_active if data.is_active is not None else True,
        )

        db.add(tax)
        db.commit()
        db.refresh(tax)
        return tax

    @staticmethod
    def get_tax(db: Session, tax_id: int) -> Tax:
        tax = db.query(Tax).filter(Tax.id == tax_id).first()
        if not tax:
            raise NotFoundException("Tax not found")
        return tax

    @staticmethod
    def list_taxes(db: Session, skip: int = 0, limit: int = 100):
        return db.query(Tax).offset(skip).limit(limit).all()

    @staticmethod
    def update_tax(db: Session, tax_id: int, data: TaxUpdate) -> Tax:
        tax = db.query(Tax).filter(Tax.id == tax_id).first()
        if not tax:
            raise NotFoundException("Tax not found")

        update_data = data.model_dump(exclude_unset=True)

        for field, value in update_data.items():
            setattr(tax, field, value)

        db.commit()
        db.refresh(tax)
        return tax

    @staticmethod
    def delete_tax(db: Session, tax_id: int):
        tax = db.query(Tax).filter(Tax.id == tax_id).first()
        if not tax:
            raise NotFoundException("Tax not found")

        db.delete(tax)
        db.commit()