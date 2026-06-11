# src/routes/employee/contracts.py
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import Annotated
from src.core.database import get_db
from src.core.permissions import Permissions
from src.core.auth_dependencies import require_permission
from src.services.employee_service import ContractService
from src.schemas.employee import ContractCreate, ContractUpdate, ContractOut
from src.schemas.users import PaginationParams

contract_router = APIRouter(prefix="/employees", tags=["Employee Contracts"])

DB = Annotated[Session, Depends(get_db)]
CanCreateEmployee = Annotated[None, Depends(require_permission(Permissions.CREATE_EMPLOYEE))]
CanReadEmployee   = Annotated[None, Depends(require_permission(Permissions.READ_EMPLOYEE))]
CanUpdateEmployee = Annotated[None, Depends(require_permission(Permissions.UPDATE_EMPLOYEE))]


@contract_router.post("/contracts", response_model=ContractOut)
def create_contract(data: ContractCreate, db: DB, current_user: CanCreateEmployee):
    return ContractService.create(db, data)

@contract_router.get("/contracts", response_model=list[ContractOut])
def list_contracts(db: DB, current_user: CanReadEmployee, pagination: PaginationParams = Depends()):
    return ContractService.list(db, pagination)

@contract_router.get("/contracts/{contract_id}", response_model=ContractOut)
def get_contract(contract_id: int, db: DB, current_user: CanReadEmployee):
    return ContractService.get(db, contract_id)

@contract_router.get("/{employee_id}/contracts", response_model=list[ContractOut])
def list_employee_contracts(employee_id: int, db: DB, current_user: CanReadEmployee, pagination: PaginationParams = Depends()):
    return ContractService.list_by_employee(db, employee_id, pagination)

@contract_router.patch("/contracts/{contract_id}", response_model=ContractOut)
def update_contract(contract_id: int, data: ContractUpdate, db: DB, current_user: CanUpdateEmployee):
    return ContractService.update(db, contract_id, data)

@contract_router.delete("/contracts/{contract_id}")
def delete_contract(contract_id: int, db: DB, current_user: CanCreateEmployee):
    ContractService.delete(db, contract_id)
    return {"message": "Deleted"}