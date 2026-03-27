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
    

class LeaveService:

    @staticmethod
    def create(db, data: LeaveRequestCreate):
        leave = LeaveRequest(**data.model_dump())
        db.add(leave)
        db.commit()
        db.refresh(leave)
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
    

class SalaryService:

    @staticmethod
    def create(db, data: SalaryCreate):
        salary = Salary(**data.model_dump())
        db.add(salary)
        db.commit()
        db.refresh(salary)
        return salary
    
    @staticmethod
    def update(db, salary_id: int, data: SalaryUpdate):
        salary = db.query(Salary).filter_by(id=salary_id).first()
        if not salary:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Salary not found"
            )
        
        update_data = data.model_dump(exclude_unset=True)
        for k, v in update_data.items():
            setattr(salary, k, v)

        db.commit()
        db.refresh(salary)
        return salary
    