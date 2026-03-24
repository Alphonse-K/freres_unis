from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List

from src.core.database import get_db
from src.schemas.users import CompanyCreate, CompanyUpdate, CompanyOut
from src.services.company import CompanyService

from src.core.auth_dependencies import require_permission
from src.core.permissions import Permissions

company_router = APIRouter(prefix="/companies", tags=["Companies"])


@company_router.post("/", response_model=CompanyOut)
def create_company(
    payload: CompanyCreate,
    db: Session = Depends(get_db),
    current_user = Depends(require_permission(Permissions.CREATE_COMPANY))
):
    return CompanyService.create_company(db, payload)


@company_router.get("/{company_id}", response_model=CompanyOut)
def get_company(
    company_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(require_permission(Permissions.READ_COMPANY))
):
    return CompanyService.get_company(db, company_id)


@company_router.get("/", response_model=List[CompanyOut])
def list_companies(
    skip: int = 0,
    limit: int = 10,
    db: Session = Depends(get_db),
    current_user = Depends(require_permission(Permissions.READ_COMPANY))
):
    return CompanyService.list_companies(db, skip, limit)


@company_router.put("/{company_id}", response_model=CompanyOut)
def update_company(
    company_id: int,
    payload: CompanyUpdate,
    db: Session = Depends(get_db),
    current_user = Depends(require_permission(Permissions.UPDATE_COMPANY))

):
    return CompanyService.update_company(db, company_id, payload)


@company_router.delete("/{company_id}")
def delete_company(
    company_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(require_permission(Permissions.DELETE_COMPANY))
):
    CompanyService.delete_company(db, company_id)
    return {"message": "Company deleted successfully"}