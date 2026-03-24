# src/schemas/employee.py
from typing import Optional, List
from decimal import Decimal
from datetime import date, datetime
from pydantic import BaseModel, Field, ConfigDict
from src.schemas.location import AddressOut
import enum


# -------------------------------
# ENUMS
# -------------------------------
class Gender(str, enum.Enum):
    MALE = "male"
    FEMALE = "female"


class LeaveStatus(str, enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    IN_PROGRESS = "in_progress"


# -------------------------------
# EMPLOYEE SCHEMAS
# -------------------------------
class EmployeeBase(BaseModel):
    first_name: str
    last_name: str
    gender: Gender
    birth_date: date
    phone: str
    email: str | None = None
    address: str
    hire_date: date


class EmployeeCreate(EmployeeBase):
    pass


class EmployeeUpdate(BaseModel):
    first_name: str | None = None
    last_name: str | None = None
    gender: Gender | None = None
    birth_date: Optional[date] = None
    phone: str | None = None
    email: str | None = None
    address: str | None = None
    hire_date: date | None = None


class EmployeeOut(EmployeeBase):
    id: int
    contracts: List["ContractOut"] = []
    attendances: List["AttendanceOut"] = []
    leaves: List["LeaveRequestOut"] = []
    salaries: List["SalaryOut"] = []
    addresses: List["AddressOut"] = []
    model_config = ConfigDict(from_attributes=True)

class EmployeeSimple(BaseModel):
    id: int
    first_name: str 
    last_name: str 
    gender: Gender 
    birth_date: date
    phone: str 
    email: str 
    address: str 
    hire_date: date 
    
    model_config = ConfigDict(from_attributes=True)
# -------------------------------
# CONTRACT SCHEMAS
# -------------------------------
class ContractBase(BaseModel):
    title: str
    start_date: date
    end_date: date
    salary_amount: Decimal
    is_active: bool | None = True


class ContractCreate(ContractBase):
    employee_id: int


class ContractUpdate(BaseModel):
    title: str | None = None
    start_date: date | None = None
    end_date: date | None = None
    salary_amount: Decimal | None = None
    is_active: bool | None = None


class ContractOut(ContractBase):
    id: int
    employee: EmployeeSimple | None = None
    model_config = ConfigDict(from_attributes=True)


# -------------------------------
# ATTENDANCE SCHEMAS
# -------------------------------
class AttendanceBase(BaseModel):
    attendance_date: date
    check_in: Optional[datetime] = None
    check_out: Optional[datetime] = None


class AttendanceCreate(AttendanceBase):
    employee_id: int


class AttendanceUpdate(BaseModel):
    attendance_date: Optional[date] = None
    check_in: Optional[datetime] = None
    check_out: Optional[datetime] = None


class AttendanceOut(AttendanceBase):
    id: int
    employee: EmployeeSimple | None = None
    model_config = ConfigDict(from_attributes=True)


# -------------------------------
# LEAVE REQUEST SCHEMAS
# -------------------------------
class LeaveRequestBase(BaseModel):
    start_date: date
    end_date: date
    reason: str | None = None

class LeaveRequestCreate(LeaveRequestBase):
    employee_id: int


class LeaveRequestUpdate(BaseModel):
    start_date: date | None = None
    end_date: date | None = None
    reason: str | None = None
    status: LeaveStatus | None = None


class LeaveRequestOut(LeaveRequestBase):
    id: int
    status: LeaveStatus
    employee: EmployeeSimple | None = None
    model_config = ConfigDict(from_attributes=True)


# -------------------------------
# SALARY SCHEMAS
# -------------------------------
class SalaryBase(BaseModel):
    base_salary: Decimal
    bonus: Decimal | None = 0
    deductions: Decimal | None = 0


class SalaryCreate(SalaryBase):
    employee_id: int


class SalaryUpdate(BaseModel):
    base_salary: Decimal | None = None
    bonus: Decimal | None = None
    deductions: Decimal | None = None


class SalaryOut(SalaryBase):
    id: int
    employee: EmployeeSimple | None = None
    model_config = ConfigDict(from_attributes=True)


# -------------------------------
# PAYSLIP SCHEMAS
# -------------------------------
class PayslipBase(BaseModel):
    period: str
    total_paid: Decimal


class PayslipCreate(PayslipBase):
    employee_id: int


class PayslipUpdate(BaseModel):
    period: str | None = None
    total_paid: Decimal | None = None


class PayslipOut(PayslipBase):
    id: int
    employee: EmployeeSimple | None = None
    model_config = ConfigDict(from_attributes=True)


# -------------------------------
# Pydantic v2: rebuild forward references
# -------------------------------
EmployeeOut.model_rebuild()
ContractOut.model_rebuild()
AttendanceOut.model_rebuild()
LeaveRequestOut.model_rebuild()
SalaryOut.model_rebuild()
PayslipOut.model_rebuild()
