from fastapi import APIRouter, Depends
from src.core.database import get_db
from src.core.permissions import Permissions
from src.core.auth_dependencies import require_permission
from sqlalchemy.orm import Session
from src.services.employee_service import (
    EmployeeService,
    AttendanceService,
    LeaveService,
    ContractService,
    PayslipService,
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
    PayslipCreate,
    PayslipUpdate,
    ContractOut,
    AttendanceOut,
    SalaryOut,
    LeaveRequestOut,
    PayslipOut
)

employee_router = APIRouter(prefix="/employees", tags=["Employees"])

@employee_router.post("/", response_model=EmployeeOut)
def create_employee(
    data: EmployeeCreate, 
    db: Session = Depends(get_db),
    # current_user = Depends(require_permission(Permissions.CREATE_EMPLOYEE))
):
    return EmployeeService.create(db, data)

@employee_router.get("/", response_model=list[EmployeeOut])
def list_employees(
    db: Session = Depends(get_db),
    # current_user = Depends(require_permission(Permissions.READ_EMPLOYEE))
):
    return EmployeeService.list(db)

@employee_router.get("/{employee_id}", response_model=EmployeeOut)
def get_employee(
    employee_id: int, 
    db: Session = Depends(get_db),
    # current_user = Depends(require_permission(Permissions.READ_EMPLOYEE))
):
    return EmployeeService.get(db, employee_id)

@employee_router.patch("/{employee_id}", response_model=EmployeeOut)
def update_employee(
    employee_id: int, 
    data: EmployeeUpdate, 
    db: Session = Depends(get_db),
    # current_user = Depends(require_permission(Permissions.UPDATE_EMPLOYEE))
):
    return EmployeeService.update(db, employee_id, data)

@employee_router.delete("/{employee_id}")
def delete_employee(
    employee_id: int, 
    db: Session = Depends(get_db),
    # current_user = Depends(require_permission(Permissions.DELETE_EMPLOYEE))
):
    EmployeeService.delete(db, employee_id)
    return {"message": "Deleted"}

@employee_router.post("/contracts", response_model=ContractOut)
def create_contract(
    data: ContractCreate, 
    db: Session = Depends(get_db),
    # current_user = Depends(require_permission(Permissions.CREATE_EMPLOYEE))
):
    return ContractService.create(db, data)

@employee_router.patch("/contracts/{contract_id}", response_model=ContractOut)
def update_contract(
    contract_id: int, 
    data: ContractUpdate, 
    db: Session = Depends(get_db),
    # current_user = Depends(require_permission(Permissions.UPDATE_EMPLOYEE))
):
    return ContractService.update(db, contract_id, data)

@employee_router.post("/attendances", response_model=AttendanceOut)
def create_attendance(
    data: AttendanceCreate, 
    db: Session = Depends(get_db),
    # current_user = Depends(require_permission(Permissions.CREATE_EMPLOYEE))
):
    return AttendanceService.create(db, data)

@employee_router.patch("/attendances/{attendance_id}", response_model=AttendanceOut)
def update_attendance(
    attendance_id: int, 
    data: AttendanceUpdate, 
    db: Session = Depends(get_db),
    # current_user = Depends(require_permission(Permissions.UPDATE_EMPLOYEE))
):
    return AttendanceService.update(db, attendance_id, data)

@employee_router.post("/leaves", response_model=LeaveRequestOut)
def create_leave(
    data: LeaveRequestCreate, 
    db: Session = Depends(get_db),
    # urrent_user = Depends(require_permission(Permissions.CREATE_EMPLOYEE))
):
    return LeaveService.create(db, data)

@employee_router.patch("/leaves/{leave_id}", response_model=LeaveRequestOut)
def update_leave(
    leave_id: int, 
    data: LeaveRequestUpdate, 
    db: Session = Depends(get_db),
    # current_user = Depends(require_permission(Permissions.UPDATE_EMPLOYEE))
):
    return LeaveService.update(db, leave_id, data)

@employee_router.post("/salaries", response_model=SalaryOut)
def create_salary(
    data: SalaryCreate, 
    db: Session = Depends(get_db),
    current_user = Depends(require_permission(Permissions.CREATE_EMPLOYEE))
):
    return SalaryService.create(db, data)

@employee_router.patch("/salaries/{salary_id}", response_model=SalaryOut)
def update_salary(
    salary_id: int, 
    data: SalaryUpdate, 
    db: Session = Depends(get_db),
    # current_user = Depends(require_permission(Permissions.UPDATE_EMPLOYEE))
):
    return SalaryService.update(db, salary_id, data)


@employee_router.post("/payslips", response_model=PayslipOut)
def create_payslip(
    data: PayslipCreate, 
    db: Session = Depends(get_db),
    # current_user = Depends(require_permission(Permissions.CREATE_EMPLOYEE))
):
    return PayslipService.create(db, data)

@employee_router.patch("/salaries/{payslip_id}", response_model=PayslipOut)
def update_payslip(
    payslip_id: int, 
    data: PayslipUpdate, 
    db: Session = Depends(get_db),
    # current_user = Depends(require_permission(Permissions.UPDATE_EMPLOYEE))
):
    return PayslipService.update(db, payslip_id, data)
