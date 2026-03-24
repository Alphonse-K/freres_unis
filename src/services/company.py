from sqlalchemy.orm import Session
from typing import List, Optional
from fastapi import HTTPException, status

from src.models.users import UnitedCompany
from src.schemas.users import CompanyCreate, CompanyUpdate


class CompanyService:

    @staticmethod
    def create_company(db: Session, payload: CompanyCreate) -> UnitedCompany:
        # uniqueness checks
        existing = db.query(UnitedCompany).filter(
            (UnitedCompany.registration_number == payload.registration_number) |
            (UnitedCompany.email == payload.email) |
            (UnitedCompany.phone == payload.phone)
        ).first()

        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="UnitedCompany with same registration/email/phone already exists"
            )

        company = UnitedCompany(**payload.model_dump())
        db.add(company)
        db.commit()
        db.refresh(company)
        return company

    @staticmethod
    def get_company(db: Session, company_id: int) -> UnitedCompany:
        company = db.query(UnitedCompany).filter(UnitedCompany.id == company_id).first()
        if not company:
            raise HTTPException(status_code=404, detail="Company not found")
        return company

    @staticmethod
    def list_companies(db: Session, skip: int = 0, limit: int = 10) -> List[UnitedCompany]:
        return db.query(UnitedCompany).offset(skip).limit(limit).all()

    @staticmethod
    def update_company(
        db: Session,
        company_id: int,
        payload: CompanyUpdate
    ) -> UnitedCompany:

        company = CompanyService.get_company(db, company_id)
        update_data = payload.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(company, key, value)

        db.commit()
        db.refresh(company)
        return company

    @staticmethod
    def delete_company(db: Session, company_id: int) -> None:
        company = CompanyService.get_company(db, company_id)

        db.delete(company)
        db.commit()