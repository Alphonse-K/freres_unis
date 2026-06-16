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
    registration_number: str
    birth_date: date
    phone: str
    email: str | None = None
    address: str
    hire_date: date


class EmployeeCreate(EmployeeBase):
    pos_id: int | None = None


class EmployeeUpdate(BaseModel):
    first_name: str | None = None
    last_name: str | None = None
    gender: Gender | None = None
    registration_number: str | None = None
    birth_date: date | None = None
    phone: str | None = None
    email: str | None = None
    address: str | None = None
    hire_date: date | None = None


class EmployeeOut(EmployeeBase):
    id: int
    pos_id: int | None = None
    face_image: str | None = None
    addresses: List["AddressOut"] = []
    model_config = ConfigDict(from_attributes=True)

class EmployeeSimple(BaseModel):
    id: int
    first_name: str 
    last_name: str 
    gender: Gender 
    registration_number: str
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
    slip: str
    is_active: bool | None = True


class ContractCreate(ContractBase):
    employee_id: int


class ContractUpdate(BaseModel):
    title: str | None = None
    start_date: date | None = None
    end_date: date | None = None
    slip: str | None = None
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
    check_in: datetime | None = None
    check_out: datetime | None = None


class AttendanceCreate(AttendanceBase):
    employee_id: int


class AttendanceUpdate(BaseModel):
    attendance_date: date | None = None
    check_in: datetime | None = None
    check_out: datetime | None = None


class AttendanceOut(AttendanceBase):
    id: int
    employee: EmployeeSimple | None = None
    model_config = ConfigDict(from_attributes=True)


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
    registration_number: str
    position: str
    month_of_function: str
    period: str
    base_salary: Decimal
    additional_hours: Decimal | None = None
    compensations: Decimal | None = None
    cnss_insurances: Decimal
    income_tax: Decimal
    other_taxes: Decimal | None = None
    bonus: Decimal | None = None


class SalaryCreate(SalaryBase):
    employee_id: int


class SalaryUpdate(BaseModel):
    # registration_number: str | None = None
    position: str | None = None
    month_of_function: str | None = None
    period: str | None = None
    base_salary: Decimal | None = None
    additional_hours: Decimal | None = None
    compensations: Decimal | None = None
    cnss_insurances: Decimal | None = None
    income_tax: Decimal | None = None
    other_taxes: Decimal | None = None
    bonus: Decimal | None = None


class SalaryOut(BaseModel):
    registration_number: str
    position: str
    month_of_function: str
    period: str
    base_salary: Decimal
    additional_hours: Decimal | None
    compensations: Decimal | None
    cnss_insurances: Decimal
    income_tax: Decimal
    other_taxes: Decimal | None
    bonus: Decimal | None
    gross_total: Decimal
    total_held: Decimal
    net_salary_to_be_paid: Decimal
    status: str
    rejection_reason: str | None
    created_by_id: int
    reviewed_by_id: int | None
    reviewed_at: datetime | None
    employee: EmployeeSimple

    model_config = ConfigDict(from_attributes=True)


class PaginatedSalaryOut(BaseModel):
    total: int
    items: List[SalaryOut]


class SalaryReject(BaseModel):
    reason: str | None = None

# -------------------------------
# Pydantic v2: rebuild forward references
# -------------------------------
EmployeeOut.model_rebuild()
ContractOut.model_rebuild()
AttendanceOut.model_rebuild()
LeaveRequestOut.model_rebuild()
SalaryOut.model_rebuild()
