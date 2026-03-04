from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List

from src.core.database import get_db
from src.core.auth_dependencies import require_permission
from src.core.permissions import Permissions
from src.schemas.taxes import *
from src.services.tax import TaxService


tax_router = APIRouter(prefix="/taxes", tags=["Taxes"])


@tax_router.post("/", response_model=TaxResponse, status_code=201)
def create_tax(
    data: TaxCreate,
    db: Session = Depends(get_db),
    user = Depends(require_permission(Permissions.CREATE_TAX))
):
    return TaxService.create_tax(db, data)


@tax_router.get("/{tax_id}", response_model=TaxResponse)
def get_tax(
    tax_id: int,
    db: Session = Depends(get_db),
    user = Depends(require_permission(Permissions.READ_TAX))
):
    return TaxService.get_tax(db, tax_id)


@tax_router.get("/", response_model=List[TaxResponse])
def list_taxes(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    user = Depends(require_permission(Permissions.READ_TAX))
):
    return TaxService.list_taxes(db, skip, limit)


@tax_router.patch("/{tax_id}", response_model=TaxResponse)
def update_tax(
    tax_id: int,
    data: TaxUpdate,
    db: Session = Depends(get_db),
    user = Depends(require_permission(Permissions.UPDATE_TAX))
):
    return TaxService.update_tax(db, tax_id, data)


@tax_router.delete("/{tax_id}", status_code=204)
def delete_tax(
    tax_id: int,
    db: Session = Depends(get_db),
    user = Depends(require_permission(Permissions.DELETE_TAX))
):
    TaxService.delete_tax(db, tax_id)