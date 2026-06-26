from fastapi import APIRouter, Depends, Query
from datetime import date
from typing import Annotated, Any
from sqlalchemy.orm import Session
from src.core.database import get_db
from src.core.auth_dependencies import require_permission
from src.core.permissions import Permissions
from src.services.client_service import LedgerService
from src.schemas.clients import (
    ClientValidationResponse,
    POSValidationResponse,
    AllPOSValidationResponse
)


DB = Annotated[Session, Depends(get_db)]
FROM_DATE = Annotated[date | None, Query(None, description="Start date YYYY-MM-DD")]
DATE_TO = Annotated[date | None, Query(None, description="End date YYYY-MM-DD")]
CanReadLedger = Annotated[Any, require_permission(Permissions.LEDGER_READ)]


ledger_route = APIRouter(prefix="/ledger", tags=["Ledger Stats"])


@ledger_route.get("/clients/{client_id}/validations", response_model=ClientValidationResponse)
def client_validations(
    db: DB,
    client_id: int,
    date_from: FROM_DATE,
    date_to: DATE_TO,
    current_user = CanReadLedger
):
    return LedgerService.get_client_validations(db, client_id, date_from, date_to)


@ledger_route.get("/pos/{pos_id}/validations", response_model=POSValidationResponse)
def pos_validations(
    db: DB,
    pos_id: int,
    date_from: FROM_DATE,
    date_to: DATE_TO,
    current_user = CanReadLedger
):
    return LedgerService.get_pos_validations(db, pos_id, date_from, date_to)


@ledger_route.get("/pos/validations", response_model=AllPOSValidationResponse)
def all_pos_validations(
    db: DB,
    date_from: FROM_DATE,
    date_to: DATE_TO,
    current_user = CanReadLedger
):
    return LedgerService.get_all_pos_validations(db, date_from, date_to)