from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import Annotated
from datetime import date
from src.core.database import get_db
from src.core.permissions import Permissions
from src.core.auth_dependencies import require_permission
from src.services.employee_service import AttendanceService
from src.schemas.employee import AttendanceCreate, AttendanceUpdate, AttendanceOut
from src.schemas.users import PaginationParams

attendance_router = APIRouter(prefix="/employees", tags=["Employee Attendances"])

DB = Annotated[Session, Depends(get_db)]
CanCreateEmployee = Annotated[None, Depends(require_permission(Permissions.CREATE_EMPLOYEE))]
CanReadEmployee   = Annotated[None, Depends(require_permission(Permissions.READ_EMPLOYEE))]
CanUpdateEmployee = Annotated[None, Depends(require_permission(Permissions.UPDATE_EMPLOYEE))]
CanDeleteEmployee = Annotated[None, Depends(require_permission(Permissions.DELETE_EMPLOYEE))]


@attendance_router.post("/attendances", response_model=AttendanceOut)
def create_attendance(data: AttendanceCreate, db: DB, current_user: CanCreateEmployee):
    return AttendanceService.create(db, data)

@attendance_router.get("/attendances", response_model=list[AttendanceOut])
def list_attendances(db: DB, current_user: CanReadEmployee, pagination: PaginationParams = Depends()):
    return AttendanceService.list(db, pagination)

@attendance_router.get("/attendances/employee/{employee_id}", response_model=list[AttendanceOut])
def list_attendances_by_employee(employee_id: int, db: DB, current_user: CanReadEmployee, pagination: PaginationParams = Depends()):
    return AttendanceService.list_by_employee(db, employee_id, pagination)

@attendance_router.get("/attendances/date/{attendance_date}", response_model=list[AttendanceOut])
def list_attendances_by_date(attendance_date: date, db: DB, current_user: CanReadEmployee, pagination: PaginationParams = Depends()):
    return AttendanceService.list_by_date(db, attendance_date, pagination)

@attendance_router.get("/attendances/{attendance_id}", response_model=AttendanceOut)
def get_attendance(attendance_id: int, db: DB, current_user: CanReadEmployee):
    return AttendanceService.get(db, attendance_id)

@attendance_router.patch("/attendances/{attendance_id}", response_model=AttendanceOut)
def update_attendance(attendance_id: int, data: AttendanceUpdate, db: DB, current_user: CanUpdateEmployee):
    return AttendanceService.update(db, attendance_id, data)

@attendance_router.delete("/attendances/{attendance_id}")
def delete_attendance(attendance_id: int, db: DB, current_user: CanDeleteEmployee):
    AttendanceService.delete(db, attendance_id)
    return {"message": "Deleted"}