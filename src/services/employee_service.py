from fastapi import HTTPException, status
from src.models.employee import Employee, Contract, Attendance, LeaveRequest, Salary
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
    LeaveStatus
)
from src.schemas.users import PaginationParams    
from datetime import date
from decimal import Decimal

class EmployeeService:

    @staticmethod
    def create(db, data: EmployeeCreate):
        employee = Employee(**data.model_dump())
        db.add(employee)
        db.commit()
        db.refresh(employee)
        return employee

    @staticmethod
    def get(db, employee_id: int):
        employee = db.query(Employee).filter_by(id=employee_id).first()
        if not employee:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, 
                detail="Employee not found"
            )
        return employee

    @staticmethod
    def list(db):
        return db.query(Employee).all()

    @staticmethod
    def update(db, employee_id: int, data: EmployeeUpdate):
        employee = EmployeeService.get(db, employee_id)
        update_data = data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(employee, key, value)

        db.commit()
        db.refresh(employee)
        return employee

    @staticmethod
    def delete(db, employee_id: int):
        employee = EmployeeService.get(db, employee_id)
        db.delete(employee)
        db.commit()


class ContractService:

    @staticmethod
    def create(db, data: ContractCreate):
        contract = Contract(**data.model_dump())
        db.add(contract)
        db.commit()
        db.refresh(contract)
        return contract

    @staticmethod
    def list(db, pagination: PaginationParams):
        query = db.query(Contract)
        if pagination:
            query = query.offset(pagination.offset).limit(pagination.page_size)
        return query.all()
    
    @staticmethod
    def get(db, contract_id: int):
        contract = db.query(Contract).get(contract_id)
        if not contract:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, 
                detail="Contract not found"
            )
        return contract
    
    @staticmethod
    def list_by_employee(db, employee_id: int, pagination: PaginationParams):
        query = db.query(Contract).filter_by(employee_id=employee_id)
        if pagination:
            query = query.offset(pagination.offset).limit(pagination.page_size)
        return query.all()

    @staticmethod
    def update(db, contract_id: int, data: ContractUpdate):
        contract = db.query(Contract).get(contract_id)
        if not contract:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, 
                detail="Contract not found"
        )

        update_data = data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(contract, key, value)

        db.commit()
        db.refresh(contract)
        return contract
    

class AttendanceService:

    @staticmethod
    def create(db, data: AttendanceCreate):
        attendance = Attendance(**data.model_dump())
        db.add(attendance)
        db.commit()
        db.refresh(attendance)
        return attendance
    
    @staticmethod
    def list_by_employee(db, employee_id: int, pagination: PaginationParams):
        query = db.query(Attendance).filter_by(employee_id=employee_id)
        if pagination:
            query = query.offset(pagination.offset).limit(pagination.page_size)
        return query.all()

    @staticmethod
    def list(db, pagination: PaginationParams):
        query = db.query(Attendance)
        if pagination:
            query = query.offset(pagination.offset).limit(pagination.page_size)
        return query.all()
    
    @staticmethod
    def list_by_date(db, attendance_date: date, pagination: PaginationParams):
        query = db.query(Attendance).filter_by(attendance_date=attendance_date)
        if pagination:
            query = query.offset(pagination.offset).limit(pagination.page_size)
        return query.all()
    
    @staticmethod
    def get(db, attendance_id: int):
        attendance = db.query(Attendance).get(attendance_id)
        if not attendance:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, 
                detail="Attendance not found"
            )
        return attendance
    
    @staticmethod
    def update(db, attendance_id: int, data: AttendanceUpdate):
        attendance = db.query(Attendance).get(attendance_id)
        if not attendance:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, 
                detail="Attendance not found"
            )

        update_data = data.model_dump(exclude_unset=True)
        for k, v in update_data.items():
            setattr(attendance, k, v)

        db.commit()
        db.refresh(attendance)
        return attendance
    
    @staticmethod
    def delete(db, attendance_id: int):
        attendance = db.query(Attendance).get(attendance_id)
        if not attendance:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, 
                detail="Attendance not found"
            )
        db.delete(attendance)
        db.commit()


class LeaveService:

    @staticmethod
    def create(db, data: LeaveRequestCreate):
        leave = LeaveRequest(**data.model_dump())
        db.add(leave)
        db.commit()
        db.refresh(leave)
        return leave

    @staticmethod
    def list(db, pagination: PaginationParams):
        query = db.query(LeaveRequest)
        if pagination:
            query = query.offset(pagination.offset).limit(pagination.page_size)
        return query.all()
    
    @staticmethod
    def list_by_employee(db, employee_id: int, pagination: PaginationParams):
        query = db.query(LeaveRequest).filter_by(employee_id=employee_id)
        if pagination:
            query = query.offset(pagination.offset).limit(pagination.page_size)
        return query.all()
    
    @staticmethod
    def get(db, leave_id: int):
        leave = db.query(LeaveRequest).get(leave_id)
        if not leave:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, 
                detail="Leave not found"
            )
        return leave    
    
    @staticmethod
    def update(db, leave_id: int, data: LeaveRequestUpdate):
        leave = db.query(LeaveRequest).get(leave_id)
        if not leave:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, 
                detail="Leave not found"
            )

        update_data = data.model_dump(exclude_unset=True)
        if leave.status == LeaveStatus.APPROVED:
            raise HTTPException(400, "Cannot modify approved leave")

        for k, v in update_data.items():
            setattr(leave, k, v)

        db.commit()
        db.refresh(leave)
        return leave
    
    @staticmethod
    def delete(db, leave_id: int):
        leave = db.query(LeaveRequest).get(leave_id)
        if not leave:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, 
                detail="Leave not found"
            )
        if leave.status == LeaveStatus.APPROVED:
            raise HTTPException(400, "Cannot delete approved leave")
        db.delete(leave)
        db.commit()


class SalaryService:

    @staticmethod
    def create(db, data: SalaryCreate):
        d = data.model_dump()

        gross_total = (
            d["base_salary"]
            + (d["additional_hours"] or Decimal("0"))
            + (d["compensations"] or Decimal("0"))
        )

        total_held = (
            d["cnss_insurances"]
            + d["income_tax"]
            + (d["other_taxes"] or Decimal("0"))
        )

        net_salary_to_be_paid = gross_total - total_held + (d["bonus"] or Decimal("0"))

        salary = Salary(
            **d,
            gross_total=gross_total,
            total_held=total_held,
            net_salary_to_be_paid=net_salary_to_be_paid
        )

        db.add(salary)
        db.commit()
        db.refresh(salary)
        return salary
    
    @staticmethod
    def list(db, pagination: PaginationParams):
        query = db.query(Salary)
        if pagination:
            query = query.offset(pagination.offset).limit(pagination.page_size)
        return query.all()

    @staticmethod
    def list_by_employee(db, employee_id: int, pagination: PaginationParams):
        query = db.query(Salary).filter_by(employee_id=employee_id)
        if pagination:
            query = query.offset(pagination.offset).limit(pagination.page_size)
        return query.all()

    @staticmethod
    def get(db, salary_id: int):
        salary = db.query(Salary).get(salary_id)
        if not salary:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Salary not found"
            )
        return salary

    @staticmethod
    def update(db, salary_id: int, data: SalaryUpdate):
        salary = db.query(Salary).get(salary_id)
        if not salary:
            raise HTTPException(status_code=404, detail="Salary not found")

        update_data = data.model_dump(exclude_unset=True)
        for k, v in update_data.items():
            setattr(salary, k, v)

        # Recalculate derived fields
        salary.gross_total = (
            salary.base_salary
            + (salary.additional_hours or Decimal("0"))
            + (salary.compensations or Decimal("0"))
        )

        salary.total_held = (
            salary.cnss_insurances
            + salary.income_tax
            + (salary.other_taxes or Decimal("0"))
        )

        salary.net_salary_to_be_paid = (
            salary.gross_total
            - salary.total_held
            + (salary.bonus or Decimal("0"))
        )

        db.commit()
        db.refresh(salary)
        return salary
    
    @staticmethod
    def delete(db, salary_id: int):
        salary = db.query(Salary).get(salary_id)
        if not salary:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Salary not found"
            )
        db.delete(salary)
        db.commit()