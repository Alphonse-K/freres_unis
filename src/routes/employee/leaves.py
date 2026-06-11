from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import Annotated
from src.core.database import get_db
from src.core.permissions import Permissions
from src.core.auth_dependencies import require_permission
from src.services.employee_service import LeaveService
from src.schemas.employee import LeaveRequestCreate, LeaveRequestUpdate, LeaveRequestOut
from src.schemas.users import PaginationParams

leave_router = APIRouter(prefix="/employees", tags=["Employee Leaves"])

DB = Annotated[Session, Depends(get_db)]
CanCreateEmployee = Annotated[None, Depends(require_permission(Permissions.CREATE_EMPLOYEE))]
CanReadEmployee   = Annotated[None, Depends(require_permission(Permissions.READ_EMPLOYEE))]
CanUpdateEmployee = Annotated[None, Depends(require_permission(Permissions.UPDATE_EMPLOYEE))]
CanDeleteEmployee = Annotated[None, Depends(require_permission(Permissions.DELETE_EMPLOYEE))]


@leave_router.post("/leaves", response_model=LeaveRequestOut)
def create_leave(data: LeaveRequestCreate, db: DB, current_user: CanCreateEmployee):
    return LeaveService.create(db, data)

@leave_router.get("/leaves", response_model=list[LeaveRequestOut])
def list_leaves(db: DB, current_user: CanReadEmployee, pagination: PaginationParams = Depends()):
    return LeaveService.list(db, pagination)

@leave_router.get("/leaves/employee/{employee_id}", response_model=list[LeaveRequestOut])
def list_leaves_by_employee(employee_id: int, db: DB, current_user: CanReadEmployee, pagination: PaginationParams = Depends()):
    return LeaveService.list_by_employee(db, employee_id, pagination)

@leave_router.get("/leaves/{leave_id}", response_model=LeaveRequestOut)
def get_leave(leave_id: int, db: DB, current_user: CanReadEmployee):
    return LeaveService.get(db, leave_id)

@leave_router.patch("/leaves/{leave_id}", response_model=LeaveRequestOut)
def update_leave(leave_id: int, data: LeaveRequestUpdate, db: DB, current_user: CanUpdateEmployee):
    return LeaveService.update(db, leave_id, data)

@leave_router.delete("/leaves/{leave_id}")
def delete_leave(leave_id: int, db: DB, current_user: CanDeleteEmployee):
    LeaveService.delete(db, leave_id)
    return {"message": "Deleted"}