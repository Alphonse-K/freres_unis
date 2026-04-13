from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from src.core.database import get_db
from src.schemas.partner_company import *
from src.services.partner_company import CompanyService, CompanyClientsResponse
from src.core.auth_dependencies import require_permission, optional_permission_for_client
from src.core.permissions import Permissions


partner_company_router = APIRouter(prefix="/partner_companies", tags=["Partner Companies"])


@partner_company_router.post("/", response_model=CompanyOut)
def create_company(
    payload: CompanyCreate,
    db: Session = Depends(get_db),
    current_user = Depends(require_permission(Permissions.CREATE_COMPANY))
):
    return CompanyService.create_company(db, payload)

@partner_company_router.get("/", response_model=list[CompanyOut])
def get_companies(
    db: Session = Depends(get_db),
    current_user = Depends(optional_permission_for_client(Permissions.CREATE_COMPANY))
):
    return CompanyService.get_all_companies(db)

@partner_company_router.get("/{company_id}", response_model=CompanyOut)
def get_company(
    company_id: int, 
    db: Session = Depends(get_db),
    current_user = Depends(optional_permission_for_client(Permissions.READ_COMPANY))
):
    return CompanyService.get_company(db, company_id)

@partner_company_router.put("/{company_id}", response_model=CompanyOut)
def update_company(
    company_id: int,
    payload: CompanyUpdate,
    db: Session = Depends(get_db),
    current_user = Depends(require_permission(Permissions.UPDATE_COMPANY))
):
    return CompanyService.update_company(db, company_id, payload)

@partner_company_router.delete("/{company_id}")
def delete_company(
    company_id: int, 
    db: Session = Depends(get_db),
    current_user = Depends(require_permission(Permissions.DELETE_COMPANY))
):
    return CompanyService.delete_company(db, company_id)

@partner_company_router.get(

    "/{company_id}/clients",
    response_model=CompanyClientsResponse
)
def get_company_clients(
    company_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(require_permission(Permissions.READ_COMPANY))
):
    return CompanyService.get_company_clients(db, company_id)