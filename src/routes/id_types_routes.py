from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from src.core.auth_dependencies import require_permission
from src.core.permissions import Permissions
from typing import List

from src.schemas.id import IDTypeCreate, IDTypeUpdate, IDTypeResponse
from src.services.id_type_service import IDTypeService
from src.core.auth_dependencies import get_db, require_role

id_type_router = APIRouter(prefix="/id-types", tags=["ID Types"])

@id_type_router.post("", response_model=IDTypeResponse, status_code=status.HTTP_201_CREATED)
def create_id_type(
    data: IDTypeCreate,
    current_user = Depends(require_permission(Permissions.ID_TYPE_CREATE)), 
    db: Session = Depends(get_db)
):
    return IDTypeService.create(db, data)


@id_type_router.patch("/{id_type_id}", response_model=IDTypeResponse)
def update_id_type(
    id_type_id: int, 
    data: IDTypeUpdate,
    current_user = Depends(require_permission(Permissions.ID_TYPE_UPDATE)), 
    db: Session = Depends(get_db)
):
    return IDTypeService.update(db, id_type_id, data)


@id_type_router.get("/{id_type_id}", response_model=IDTypeResponse)
def get_id_type(
    id_type_id: int,
    current_user = Depends(require_permission(Permissions.ID_TYPE_READ)), 
    db: Session = Depends(get_db)
):
    return IDTypeService.get(db, id_type_id)


@id_type_router.get("", response_model=List[IDTypeResponse])
def list_id_types(
    current_user = Depends(require_permission(Permissions.ID_TYPE_READ)),
    db: Session = Depends(get_db)
):
    return IDTypeService.list(db)
