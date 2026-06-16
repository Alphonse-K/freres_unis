from sqlalchemy import (
    Column, 
    Integer, 
    String, 
    ForeignKey, 
    Date, 
    DateTime, 
    Boolean, 
    Numeric, 
    Enum, 
    Text
)
from sqlalchemy.orm import relationship
from src.core.database import Base
import enum


class Gender(str, enum.Enum):
    MALE = "male"
    FEMALE = "female"


class LeaveStatus(str, enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    IN_PROGRESS = "in_progress"


class Employee(Base):
    __tablename__ = "employees"
    id = Column(Integer, primary_key=True)
    pos_id = Column(Integer, ForeignKey("pos.id"), nullable=True)
    first_name = Column(String(120))
    last_name = Column(String(120))
    gender = Column(Enum(Gender))
    birth_date = Column(Date)
    phone = Column(String(30))
    email = Column(String(255))
    face_image = Column(String(255), nullable=True)
    address = Column(String(255))
    hire_date = Column(Date)

    contracts = relationship("Contract", back_populates="employee")
    attendances = relationship("Attendance", back_populates="employee")
    leaves = relationship("LeaveRequest", back_populates="employee")
    salaries = relationship("Salary", back_populates="employee")
    addresses = relationship("Address", back_populates="employee", cascade="all, delete-orphan")
    card_requests = relationship("EmployeeCardRequest", back_populates="employee")
    card = relationship("EmployeeCard", back_populates="employee", uselist=False)
    pos = relationship("POS", back_populates="employees")


class Contract(Base):
    __tablename__ = "contracts"
    id = Column(Integer, primary_key=True)
    employee_id = Column(Integer, ForeignKey("employees.id"))
    title = Column(String(200))
    slip = Column(String(255), nullable=True)
    start_date = Column(Date)
    end_date = Column(Date)
    is_active = Column(Boolean, default=True)

    employee = relationship("Employee", back_populates="contracts")


class Attendance(Base):
    __tablename__ = "attendance"
    id = Column(Integer, primary_key=True)
    employee_id = Column(Integer, ForeignKey("employees.id"))
    attendance_date = Column(Date)
    check_in = Column(DateTime)
    check_out = Column(DateTime)

    employee = relationship("Employee", back_populates="attendances")


class LeaveRequest(Base):
    __tablename__ = "leave_requests"
    id = Column(Integer, primary_key=True)
    employee_id = Column(Integer, ForeignKey("employees.id"))
    start_date = Column(Date)
    end_date = Column(Date)
    reason = Column(Text)
    status = Column(Enum(LeaveStatus), default=LeaveStatus.PENDING)

    employee = relationship("Employee", back_populates="leaves")


class Salary(Base):
    __tablename__ = "salaries"
    id = Column(Integer, primary_key=True)
    employee_id = Column(Integer, ForeignKey("employees.id"))
    registration_number = Column(String(100), nullable=True)
    position = Column(String(100), nullable=False)
    month_of_function = Column(String(50), nullable=False)
    period = Column(String(50), nullable=False)
    base_salary = Column(Numeric(12, 2), nullable=False)
    additional_hours = Column(Numeric(12, 2), nullable=True)
    compensations = Column(Numeric(12, 2), nullable=True)
    gross_total = Column(Numeric(12, 2), nullable=False)
    cnss_insurances = Column(Numeric(12, 2), nullable=False)
    income_tax = Column(Numeric(12, 2), nullable=False)
    other_taxes = Column(Numeric(12, 2), nullable=True)
    total_held = Column(Numeric(12, 2), nullable=False)
    bonus = Column(Numeric(12, 2), nullable=True)
    net_salary_to_be_paid = Column(Numeric(12, 2), nullable=False)

    # Workflow
    status = Column(String, default="pending")
    rejection_reason = Column(String, nullable=True)
    created_by_id = Column(Integer, ForeignKey("pos_user.id"), nullable=False)
    reviewed_by_id = Column(Integer, ForeignKey("pos_user.id"), nullable=True)
    reviewed_at = Column(DateTime(timezone=True), nullable=True)

    employee = relationship("Employee", back_populates="salaries")
    created_by = relationship("POSUser", foreign_keys=[created_by_id])
    reviewed_by = relationship("POSUser", foreign_keys=[reviewed_by_id])