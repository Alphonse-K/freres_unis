from pydantic import BaseModel, ConfigDict
from datetime import datetime
from uuid import UUID
from src.schemas.employee import EmployeeSimple
from src.schemas.users import UserSimple
from src.schemas.pos import POSUserSimple 


class CardRequestCreate(BaseModel):
    employee_id: int
    reason: str | None = None


class CardRequestReject(BaseModel):
    reason: str | None = None


class EmployeeCardRequestOut(BaseModel):
    id: int
    employee_id: int
    status: str
    reason: str | None
    rejection_reason: str | None
    requested_at: datetime
    reviewed_at: datetime | None
    created_by_id: int
    reviewed_by_id: int | None
    employee: EmployeeSimple
    created_by: POSUserSimple   
    reviewed_by: UserSimple | None
    model_config = ConfigDict(from_attributes=True)


class EmployeeCardOut(BaseModel):
    id: UUID
    employee_id: int
    card_number: str
    qr_code_path: str | None
    issued_at: datetime
    expires_at: datetime
    is_active: bool
    revoked_at: datetime | None
    created_by: int
    employee: EmployeeSimple

    model_config = ConfigDict(from_attributes=True)


class EmployeeCardScanOut(BaseModel):
    employee: EmployeeSimple
    scanned_at: datetime

    model_config = ConfigDict(from_attributes=True)