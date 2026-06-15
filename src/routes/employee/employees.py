from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import Annotated
from src.core.database import get_db
from src.core.permissions import Permissions
from src.core.auth_dependencies import require_permission, get_pos_id_or_none
from src.services.employee_service import EmployeeService
from src.schemas.employee import EmployeeCreate, EmployeeUpdate, EmployeeOut


employee_router = APIRouter(prefix="/employees", tags=["Employees"])

DB = Annotated[Session, Depends(get_db)]
CanCreateEmployee = Annotated[None, Depends(require_permission(Permissions.CREATE_EMPLOYEE))]
CanReadEmployee   = Annotated[None, Depends(require_permission(Permissions.READ_EMPLOYEE))]
CanUpdateEmployee = Annotated[None, Depends(require_permission(Permissions.UPDATE_EMPLOYEE))]
CanDeleteEmployee = Annotated[None, Depends(require_permission(Permissions.DELETE_EMPLOYEE))]


@employee_router.post("/", response_model=EmployeeOut)
def create_employee(
    data: EmployeeCreate, 
    db: DB, 
    current_user: CanCreateEmployee
):
    return EmployeeService.create(db, data)


@employee_router.get("/", response_model=list[EmployeeOut])
def list_employees(
    db: DB, 
    current_user: CanReadEmployee
):
    pos_id = get_pos_id_or_none(current_user)
    return EmployeeService.list(db, pos_id)


@employee_router.get("/{employee_id}", response_model=EmployeeOut)
def get_employee(
    employee_id: int, 
    db: DB, 
    current_user: CanReadEmployee
):
    pos_id = get_pos_id_or_none(current_user)
    return EmployeeService.get(db, employee_id, pos_id)


@employee_router.patch("/{employee_id}", response_model=EmployeeOut)
def update_employee(
    employee_id: int, 
    data: EmployeeUpdate, 
    db: DB, 
    current_user: CanUpdateEmployee
):
    pos_id = get_pos_id_or_none(current_user)
    return EmployeeService.update(db, employee_id, data, pos_id)


@employee_router.delete("/{employee_id}")
def delete_employee(
    employee_id: int, 
    db: DB, 
    current_user: CanDeleteEmployee
):
    pos_id = get_pos_id_or_none(current_user)
    EmployeeService.delete(db, employee_id, pos_id)
    return {"message": "Deleted"}