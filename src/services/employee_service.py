from fastapi import HTTPException, status
from src.models.employee import Employee, Contract, Attendance, LeaveRequest, Salary
from src.models.pos import POSUser
from src.schemas.employee import (
    EmployeeCreate, 
    EmployeeUpdate,
    ContractCreate,
    ContractUpdate,
    AttendanceCreate,
    AttendanceUpdate,   
    LeaveRequestCreate,
    LeaveRequestUpdate,
    SalaryCreate,
    SalaryUpdate,
    LeaveStatus,
    SalaryReject
)
from src.utils.file_upload import save_image
from sqlalchemy.orm import Session
from datetime import datetime
from src.schemas.users import PaginationParams    
from datetime import date, timezone
from decimal import Decimal


class EmployeeService:

    @staticmethod
    def get(db, employee_id: int, pos_id: int | None = None):
        query = db.query(Employee).filter(Employee.id == employee_id)

        # pos_id=None means admin — no POS restriction
        if pos_id is not None:
            query = query.filter(Employee.pos_id == pos_id)

        employee = query.first()
        if not employee:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Employee not found"
            )
        return employee

    @staticmethod
    def list(db, pos_id: int | None = None):
        query = db.query(Employee)

        if pos_id is not None:
            query = query.filter(Employee.pos_id == pos_id)

        return query.all()

    @staticmethod
    def update(
        db, 
        employee_id: int, 
        data: EmployeeUpdate, 
        pos_id: int | None = None, 
        face_image: str | None = None
    ):
        employee = EmployeeService.get(db, employee_id, pos_id)

        for key, value in data.model_dump(exclude_unset=True).items():
            setattr(employee, key, value)

        if face_image:
            employee.face_image=save_image(face_image, "face_image")

        db.commit()
        db.refresh(employee)
        return employee

    @staticmethod
    def delete(db, employee_id: int, pos_id: int | None = None):
        employee = EmployeeService.get(db, employee_id, pos_id)
        db.delete(employee)
        db.commit()

    @staticmethod
    def create(db: Session, data: EmployeeCreate, face_image: str | None = None):
        employee = Employee(
            **data.model_dump(),
            face_image=save_image(face_image, "face_image")
        )
        db.add(employee)
        db.commit()
        db.refresh(employee)
        return employee


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
    
    @staticmethod
    def delete(db, contract_id: int):
        contract = db.query(Contract).get(contract_id)
        if not contract:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Contract not found"
            )
        db.delete(contract)
        db.commit()
        
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
    def create(db: Session, data: SalaryCreate, created_by_id: int):
        d = data.model_dump()

        pos_user = db.query(POSUser).get(created_by_id)
        
        if not pos_user:
            raise HTTPException(
                status.HTTP_404_NOT_FOUND, 
                detail="POS User not found"
            )

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
            net_salary_to_be_paid=net_salary_to_be_paid,
            status="pending",
            created_by_id=created_by_id
        )
        db.add(salary)
        db.commit()
        db.refresh(salary)
        return salary

    @staticmethod
    def approve(db: Session, salary_id: int, reviewer_id: int):
        salary = db.get(Salary, salary_id)
        if not salary:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Salary not found")

        # Idempotency
        if salary.status == "approved":
            return salary

        if salary.status != "pending":
            raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Invalid salary state")

        salary.status = "approved"
        salary.reviewed_by_id = reviewer_id
        salary.reviewed_at = datetime.now(timezone.utc)

        db.commit()
        db.refresh(salary)
        return salary

    @staticmethod
    def reject(db: Session, salary_id: int, reviewer_id: int, data: SalaryReject):
        salary = db.get(Salary, salary_id)
        if not salary:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Salary not found")

        # Idempotency
        if salary.status == "rejected":
            return salary

        if salary.status != "pending":
            raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Invalid salary state")

        salary.status = "rejected"
        salary.reviewed_by_id = reviewer_id
        salary.reviewed_at = datetime.now(timezone.utc)
        salary.rejection_reason = data.reason

        db.commit()
        db.refresh(salary)
        return salary

    @staticmethod
    def update(db: Session, salary_id: int, data: SalaryUpdate):
        salary = db.get(Salary, salary_id)
        if not salary:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Salary not found")

        if salary.status == "approved":
            raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Cannot modify approved salary")

        for k, v in data.model_dump(exclude_unset=True).items():
            setattr(salary, k, v)

        # Recalculate
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
    def list(db: Session, pagination: PaginationParams):
        query = db.query(Salary).order_by(Salary.id.desc())
        total = query.count()
        items = query.offset(pagination.offset).limit(pagination.page_size).all()
        return total, items

    @staticmethod
    def list_by_employee(db: Session, employee_id: int, pagination: PaginationParams):
        query = db.query(Salary).filter_by(employee_id=employee_id).order_by(Salary.id.desc())
        total = query.count()
        items = query.offset(pagination.offset).limit(pagination.page_size).all()
        return total, items

    @staticmethod
    def get(db: Session, salary_id: int):
        salary = db.get(Salary, salary_id)
        if not salary:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Salary not found")
        return salary

    @staticmethod
    def delete(db: Session, salary_id: int):
        salary = db.get(Salary, salary_id)
        if not salary:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Salary not found")
        if salary.status == "approved":
            raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Cannot delete approved salary")
        db.delete(salary)
        db.commit()