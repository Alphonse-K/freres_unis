from fastapi import APIRouter, Depends
from src.core.database import get_db
from src.core.permissions import Permissions
from src.core.auth_dependencies import require_permission
from sqlalchemy.orm import Session
from typing import Annotated    
from src.services.employee_service import (
    EmployeeService,
    AttendanceService,
    LeaveService,
    ContractService,
    SalaryService
)
from src.schemas.employee import (
    EmployeeCreate, 
    EmployeeUpdate,
    EmployeeOut,
    ContractCreate,
    ContractUpdate,
    AttendanceCreate,
    AttendanceUpdate,
    LeaveRequestCreate,
    LeaveRequestUpdate,
    SalaryCreate,
    SalaryUpdate,
    ContractOut,
    AttendanceOut,
    SalaryOut,
    LeaveRequestOut,
)
from src.schemas.users import PaginationParams
from datetime import date


employee_router = APIRouter(prefix="/employees", tags=["Employees"])

DB = Annotated[Session, Depends(get_db)]

CanCreateEmployee = Annotated[None, Depends(require_permission(Permissions.CREATE_EMPLOYEE))]
CanReadEmployee = Annotated[None, Depends(require_permission(Permissions.READ_EMPLOYEE))]
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
    return EmployeeService.list(db)

@employee_router.get(
    "/{employee_id}", 
    response_model=EmployeeOut
)
def get_employee(
    employee_id: int, 
    db: DB,
    current_user: CanReadEmployee
):
    return EmployeeService.get(db, employee_id)

@employee_router.patch(
    "/{employee_id}", 
    response_model=EmployeeOut
)
def update_employee(
    employee_id: int, 
    data: EmployeeUpdate, 
    db: DB,
    current_user: CanUpdateEmployee
):
    return EmployeeService.update(db, employee_id, data)

@employee_router.delete("/{employee_id}")
def delete_employee(
    employee_id: int, 
    db: DB,
    current_user: CanDeleteEmployee
):
    EmployeeService.delete(db, employee_id)
    return {"message": "Deleted"}


@employee_router.post(
    "/contracts", 
    response_model=ContractOut
)
def create_contract(
    data: ContractCreate, 
    db: DB,
    current_user: CanCreateEmployee
):
    return ContractService.create(db, data)

@employee_router.get(
    "/contracts", 
    response_model=list[ContractOut]
)
def list_contracts(
    db: DB, 
    current_user: CanReadEmployee, 
    pagination: PaginationParams = Depends()):
    return ContractService.list(db, pagination)

@employee_router.get(
    "/{employee_id}/contracts", 
    response_model=list[ContractOut]
)
def list_employee_contracts(
    employee_id: int, 
    db: DB, 
    current_user: CanReadEmployee, 
    pagination: PaginationParams = Depends()):
    return ContractService.list_by_employee(
        db, 
        employee_id, 
        pagination
    )

@employee_router.patch(
    "/contracts/{contract_id}", 
    response_model=ContractOut
)
def update_contract(
    contract_id: int, 
    data: ContractUpdate, 
    db: DB,
    current_user: CanUpdateEmployee
):
    return ContractService.update(db, contract_id, data)


@employee_router.post(
    "/attendances", 
    response_model=AttendanceOut
)
def create_attendance(
    data: AttendanceCreate, 
    db: DB,
    current_user: CanCreateEmployee
):
    return AttendanceService.create(db, data)

@employee_router.get(
    "/attendances/employee/{employee_id}",
    response_model=list[AttendanceOut]
)
def list_attendances_by_employee(
    employee_id: int,
    db: DB,
    current_user: CanReadEmployee,
    pagination: PaginationParams = Depends()
):
    return AttendanceService.list_by_employee(db, employee_id, pagination)

@employee_router.get(
    "/attendances/{attendance_id}",
    response_model=AttendanceOut
)
def get_attendance(
    attendance_id: int,
    db: DB,
    current_user: CanReadEmployee
):
    return AttendanceService.get(db, attendance_id)

@employee_router.get(
    "/attendances/date/{attendance_date}",
    response_model=list[AttendanceOut]
)
def list_attendances_by_date(
    attendance_date: date,
    db: DB,
    current_user: CanReadEmployee,
    pagination: PaginationParams = Depends()
):
    return AttendanceService.list_by_date(db, attendance_date, pagination)

@employee_router.patch(
    "/attendances/{attendance_id}", 
    response_model=AttendanceOut
)
def update_attendance(
    attendance_id: int, 
    data: AttendanceUpdate, 
    db: DB,
    current_user: CanUpdateEmployee
):
    return AttendanceService.update(db, attendance_id, data)

@employee_router.delete("/attendances/{attendance_id}")
def delete_attendance(
    attendance_id: int,
    db: DB,
    current_user: CanDeleteEmployee,
):
    AttendanceService.delete(db, attendance_id)
    return {"message": "Deleted"}


@employee_router.post("/leaves", response_model=LeaveRequestOut)
def create_leave(
    data: LeaveRequestCreate,
    db: DB,
    current_user: CanCreateEmployee
):
    return LeaveService.create(db, data)


@employee_router.get("/leaves", response_model=list[LeaveRequestOut])
def list_leaves(
    db: DB,
    current_user: CanReadEmployee,
    pagination: PaginationParams = Depends()
):
    return LeaveService.list(db, pagination)


@employee_router.get("/leaves/employee/{employee_id}", response_model=list[LeaveRequestOut])
def list_leaves_by_employee(
    employee_id: int,
    db: DB,
    current_user: CanReadEmployee,
    pagination: PaginationParams = Depends()
):
    return LeaveService.list_by_employee(db, employee_id, pagination)


@employee_router.get("/leaves/{leave_id}", response_model=LeaveRequestOut)
def get_leave(
    leave_id: int,
    db: DB,
    current_user: CanReadEmployee
):
    return LeaveService.get(db, leave_id)


@employee_router.patch("/leaves/{leave_id}", response_model=LeaveRequestOut)
def update_leave(
    leave_id: int,
    data: LeaveRequestUpdate,
    db: DB,
    current_user: CanUpdateEmployee
):
    return LeaveService.update(db, leave_id, data)


@employee_router.delete("/leaves/{leave_id}")
def delete_leave(
    leave_id: int,
    db: DB,
    current_user: CanDeleteEmployee
):
    LeaveService.delete(db, leave_id)
    return {"message": "Deleted"}


@employee_router.post("/salaries", response_model=SalaryOut)
def create_salary(
    data: SalaryCreate,
    db: DB,
    current_user: CanCreateEmployee
):
    return SalaryService.create(db, data)


@employee_router.get("/salaries", response_model=list[SalaryOut])
def list_salaries(
    db: DB,
    current_user: CanReadEmployee,
    pagination: PaginationParams = Depends()
):
    return SalaryService.list(db, pagination)


@employee_router.get(
    "/salaries/employee/{employee_id}", 
    response_model=Paginated
)
def list_salaries_by_employee(
    employee_id: int,
    db: DB,
    current_user: CanReadEmployee,
    pagination: PaginationParams = Depends()
):
    return SalaryService.list_by_employee(db, employee_id, pagination)


@employee_router.get("/salaries/{salary_id}", response_model=SalaryOut)
def get_salary(
    salary_id: int,
    db: DB,
    current_user: CanReadEmployee
):
    return SalaryService.get(db, salary_id)


@employee_router.patch("/salaries/{salary_id}", response_model=SalaryOut)
def update_salary(
    salary_id: int,
    data: SalaryUpdate,
    db: DB,
    current_user: CanUpdateEmployee
):
    return SalaryService.update(db, salary_id, data)


@employee_router.delete("/salaries/{salary_id}")
def delete_salary(
    salary_id: int,
    db: DB,
    current_user: CanDeleteEmployee
):
    SalaryService.delete(db, salary_id)
    return {"message": "Deleted"}