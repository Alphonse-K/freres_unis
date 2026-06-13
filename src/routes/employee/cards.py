# routes/employee/cards.py
from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session
from typing import Annotated
from uuid import UUID
from src.core.database import get_db
from src.core.permissions import Permissions
from src.core.auth_dependencies import require_permission
from src.services.employee_card_service import EmployeeCardService
from src.schemas.employee_card import (
    CardRequestCreate,
    CardRequestReject,
    EmployeeCardRequestOut,
    EmployeeCardOut,
    EmployeeCardScanOut,
)
from src.schemas.users import PaginationParams
from datetime import datetime, timezone

card_router = APIRouter(prefix="/employees", tags=["Employee Cards"])

DB = Annotated[Session, Depends(get_db)]
CanCreateCard  = Annotated[None, Depends(require_permission(Permissions.CREATE_EMPLOYEE_CARD))]
CanReadCard    = Annotated[None, Depends(require_permission(Permissions.READ_EMPLOYEE_CARD))]
CanApproveCard = Annotated[None, Depends(require_permission(Permissions.APPROVE_EMPLOYEE_CARD))]
CanRevokeCard  = Annotated[None, Depends(require_permission(Permissions.REVOKE_EMPLOYEE_CARD))]


# --- Requests ---
@card_router.post("/cards/requests", response_model=EmployeeCardRequestOut)
def create_card_request(
    data: CardRequestCreate,
    db: DB,
    current_posuser: CanCreateCard
):
    return EmployeeCardService.create_request(db, data, created_by_id=current_posuser.id)


@card_router.get("/cards/requests", response_model=list[EmployeeCardRequestOut])
def list_card_requests(
    db: DB,
    current_user: CanReadCard,
    pagination: PaginationParams = Depends()
):
    total, items = EmployeeCardService.list_requests(db, pagination)
    return items


@card_router.get("/cards/requests/{request_id}", response_model=EmployeeCardRequestOut)
def get_card_request(
    request_id: int,
    db: DB,
    current_user: CanReadCard
):
    return EmployeeCardService.get_request(db, request_id)


@card_router.post("/cards/requests/{request_id}/approve", response_model=EmployeeCardOut)
def approve_card_request(
    request_id: int,
    db: DB,
    current_user: CanApproveCard
):
    return EmployeeCardService.approve_request(db, request_id, reviewer_id=current_user.id)


@card_router.post("/cards/requests/{request_id}/reject", response_model=EmployeeCardRequestOut)
def reject_card_request(
    request_id: int,
    data: CardRequestReject,
    db: DB,
    current_user: CanApproveCard
):
    return EmployeeCardService.reject_request(db, request_id, reviewer_id=current_user.id, data=data)


# --- Cards ---

@card_router.get("/cards/{employee_id}", response_model=EmployeeCardOut)
def get_employee_card(
    employee_id: int,
    db: DB,
    current_user: CanReadCard
):
    return EmployeeCardService.get_employee_card(db, employee_id)


@card_router.post("/cards/{card_id}/revoke", response_model=EmployeeCardOut)
def revoke_card(
    card_id: UUID,
    db: DB,
    current_user: CanRevokeCard
):
    return EmployeeCardService.revoke_card(db, card_id)


# --- Scan ---

@card_router.post("/cards/scan", response_model=EmployeeCardScanOut)
def scan_card(
    request: Request,
    token: str,
    db: DB,
    current_user: CanReadCard
):
    ip = request.client.host
    employee = EmployeeCardService.scan_card(db, token, agent_id=current_user.id, ip=ip)
    return {"employee": employee, "scanned_at": datetime.now(timezone.utc)}