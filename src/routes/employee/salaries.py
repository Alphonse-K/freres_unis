# src/routes/employee/salaries.py
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import Annotated
from src.core.database import get_db
from src.core.permissions import Permissions
from src.core.auth_dependencies import require_permission
from src.services.employee_service import SalaryService
from src.schemas.employee import SalaryCreate, SalaryUpdate, SalaryOut
from src.schemas.users import PaginationParams
from src.schemas.employee import SalaryCreate, SalaryUpdate, SalaryOut, SalaryReject


salary_router = APIRouter(prefix="/employees", tags=["Employee Salaries"])


DB = Annotated[Session, Depends(get_db)]
CanCreateEmployee = Annotated[None, Depends(require_permission(Permissions.CREATE_EMPLOYEE))]
CanReadEmployee   = Annotated[None, Depends(require_permission(Permissions.READ_EMPLOYEE))]
CanUpdateEmployee = Annotated[None, Depends(require_permission(Permissions.UPDATE_EMPLOYEE))]
CanDeleteEmployee = Annotated[None, Depends(require_permission(Permissions.DELETE_EMPLOYEE))]
CanCreateSalary   = Annotated[None, Depends(require_permission(Permissions.CREATE_EMPLOYEE_SALARY))]
CanApproveSalary = Annotated[None, Depends(require_permission(Permissions.APPROVE_EMPLOYEE_SALARY))]
CanRejectSalary = Annotated[None, Depends(require_permission(Permissions.REJECT_EMPLOYEE_SALARY))]



@salary_router.post("/salaries", response_model=SalaryOut)
def create_salary(
    data: SalaryCreate,
    db: DB,
    current_posuser: CanCreateSalary   # POSUser
):
    return SalaryService.create(db, data, created_by_id=current_posuser.id)


@salary_router.post(
    "/salaries/{salary_id}/approve", 
    response_model=SalaryOut
)
def approve_salary(
    salary_id: int,
    db: DB,
    current_user: CanApproveSalary     # User (admin)
):
    return SalaryService.approve(db, salary_id, reviewer_id=current_user.id)


@salary_router.post(
    "/salaries/{salary_id}/reject", 
        response_model=SalaryOut
)
def reject_salary(
    salary_id: int,
    data: SalaryReject,
    db: DB,
    current_user: CanRejectSalary 
):
    return SalaryService.reject(db, salary_id, reviewer_id=current_user.id, data=data)


@salary_router.get(
    "/salaries", 
    response_model=list[SalaryOut]
)
def list_salaries(
    db: DB, 
    current_user: CanReadEmployee, 
    pagination: PaginationParams = Depends()
):
    return SalaryService.list(db, pagination)


@salary_router.get(
    "/salaries/employee/{employee_id}", 
    response_model=list[SalaryOut]
)
def list_salaries_by_employee(
    employee_id: int, 
    db: DB, 
    current_user: CanReadEmployee, 
    pagination: PaginationParams = Depends()
):
    return SalaryService.list_by_employee(db, employee_id, pagination)


@salary_router.get(
    "/salaries/{salary_id}", 
    response_model=SalaryOut
)
def get_salary(
    salary_id: int, 
    db: DB, 
    current_user: CanReadEmployee
):
    return SalaryService.get(db, salary_id)


@salary_router.patch(
    "/salaries/{salary_id}", 
    response_model=SalaryOut
)
def update_salary(
    salary_id: int, 
    data: SalaryUpdate, 
    db: DB, 
    current_user: CanUpdateEmployee
):
    return SalaryService.update(db, salary_id, data)


@salary_router.delete(
    "/salaries/{salary_id}"
)
def delete_salary(
    salary_id: int, 
db: DB, 
current_user: CanDeleteEmployee
):
    SalaryService.delete(db, salary_id)
    return {"message": "Deleted"}