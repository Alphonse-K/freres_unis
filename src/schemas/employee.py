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


# -------------------------------
# EMPLOYEE SCHEMAS
# -------------------------------
class EmployeeBase(BaseModel):
    first_name: str
    last_name: str
    gender: Optional[Gender] = None
    birth_date: Optional[date] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    address: Optional[str] = None
    hire_date: Optional[date] = None


class EmployeeCreate(EmployeeBase):
    pass


class EmployeeUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    gender: Optional[Gender] = None
    birth_date: Optional[date] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    address: Optional[str] = None
    hire_date: Optional[date] = None


class EmployeeOut(EmployeeBase):
    id: int
    contracts: List["ContractOut"] = []
    attendances: List["AttendanceOut"] = []
    leaves: List["LeaveRequestOut"] = []
    salaries: List["SalaryOut"] = []
    addresses: List["AddressOut"] = []

    model_config = ConfigDict(from_attributes=True)


# -------------------------------
# CONTRACT SCHEMAS
# -------------------------------
class ContractBase(BaseModel):
    title: str
    start_date: date
    end_date: date
    salary_amount: Decimal
    is_active: Optional[bool] = True


class ContractCreate(ContractBase):
    employee_id: int


class ContractUpdate(BaseModel):
    title: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    salary_amount: Optional[Decimal] = None
    is_active: Optional[bool] = None


class ContractOut(ContractBase):
    id: int
    employee: Optional[EmployeeOut] = None

    model_config = ConfigDict(from_attributes=True)


# -------------------------------
# ATTENDANCE SCHEMAS
# -------------------------------
class AttendanceBase(BaseModel):
    date: date
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
    employee: Optional[EmployeeOut] = None

    model_config = ConfigDict(from_attributes=True)


# -------------------------------
# LEAVE REQUEST SCHEMAS
# -------------------------------
class LeaveRequestBase(BaseModel):
    start_date: date
    end_date: date
    reason: Optional[str] = None
    status: Optional[str] = "pending"


class LeaveRequestCreate(LeaveRequestBase):
    employee_id: int


class LeaveRequestUpdate(BaseModel):
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    reason: Optional[str] = None
    status: Optional[str] = None


class LeaveRequestOut(LeaveRequestBase):
    id: int
    employee: Optional[EmployeeOut] = None

    model_config = ConfigDict(from_attributes=True)


# -------------------------------
# SALARY SCHEMAS
# -------------------------------
class SalaryBase(BaseModel):
    base_salary: Decimal
    bonus: Optional[Decimal] = 0
    deductions: Optional[Decimal] = 0


class SalaryCreate(SalaryBase):
    employee_id: int


class SalaryUpdate(BaseModel):
    base_salary: Optional[Decimal] = None
    bonus: Optional[Decimal] = None
    deductions: Optional[Decimal] = None


class SalaryOut(SalaryBase):
    id: int
    employee: Optional[EmployeeOut] = None

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
    period: Optional[str] = None
    total_paid: Optional[Decimal] = None


class PayslipOut(PayslipBase):
    id: int
    employee: Optional[EmployeeOut] = None

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
