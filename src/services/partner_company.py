from sqlalchemy.orm import Session, joinedload
from fastapi import HTTPException, status
from src.models.partner_company import Company
from src.schemas.partner_company import *
from src.models.clients import ClientApproval


class CompanyService:
    @staticmethod
    def create_company(db: Session, payload: CompanyCreate):
        try:
            existing = db.query(Company).filter(
                (Company.email == payload.email) |
                (Company.name == payload.name)
            ).first()

            if existing:
                raise HTTPException(
                    status_code=400,
                    detail="Company with same name or email already exists"
                )

            company = Company(**payload.model_dump())
            db.add(company)
            db.commit()
            db.refresh(company)
            return company
        except Exception:
            db.rollback()
            raise

    @staticmethod
    def get_all_companies(db: Session):
        return db.query(Company).all()

    @staticmethod
    def get_company(db: Session, company_id: int):
        company = db.query(Company).filter(Company.id == company_id).first()

        if not company:
            raise HTTPException(
                status_code=404,
                detail="Company not found"
            )
        return company

    @staticmethod
    def update_company(db: Session, company_id: int, payload: CompanyUpdate):
        try:
            company = db.query(Company).filter(Company.id == company_id).first()
            if not company:
                raise HTTPException(404, "Company not found")

            for key, value in payload.model_dump(exclude_unset=True).items():
                setattr(company, key, value)

            db.commit()
            db.refresh(company)
            return company
        except Exception:
            db.rollback()
            raise

    @staticmethod
    def delete_company(db: Session, company_id: int):
        try:
            company = db.query(Company).filter(Company.id == company_id).first()
            if not company:
                raise HTTPException(404, "Company not found")

            db.delete(company)
            db.commit()
            return {"message": "Company deleted successfully"}
        except Exception:
            db.rollback()
            raise

    # @staticmethod
    # def get_company_clients(db: Session, company_id: int):
    #     company = (
    #         db.query(Company)
    #         .options(joinedload(Company.clients).joinedload(ClientApproval.client))
    #         .filter(Company.id == company_id)
    #         .first()
    #     )

    #     if not company:
    #         raise HTTPException(404, "Company not found")

    #     return [ca.client for ca in company.clients]
    @staticmethod
    def get_company_clients(db: Session, company_id: int):
        company = (
            db.query(Company)
            .options(joinedload(Company.clients).joinedload(ClientApproval.client))
            .filter(Company.id == company_id)
            .first()
        )

        if not company:
            raise HTTPException(404, "Company not found")

        clients = []
        for ca in company.clients:
            client = ca.client
            if client:
                clients.append(
                    CompanyClientResponse(
                        id=client.id,
                        first_name=client.first_name,
                        last_name=client.last_name,
                        phone=client.phone,
                        balance=client.current_balance,
                        approval=ClientApprovalInfo(
                            employee_company=ca.employee_company,
                            magnetic_card_number=ca.magnetic_card_number
                        )
                    )
                )

        return CompanyClientsResponse(
            company_id=company.id,
            company_name=company.name,
            clients=clients
        )