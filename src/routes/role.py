from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from src.schemas.roles_perm import (
    RoleCreate, RoleUpdate, RoleResponse
)
from src.services.role import (
    create_role, get_role_by_id, update_role, delete_role, get_all_roles,
)
from src.core.auth_dependencies import require_permission
from src.core.database import get_db
from src.core.permissions import Permissions
from src.models.role import Role
from src.schemas.roles_perm import RolePermissionAssign
from src.services.role import assign_permissions_to_role

role_router = APIRouter(prefix="/rbac", tags=["RBAC"])

@role_router.post("/role/", response_model=RoleResponse)
def create_new_role(
    role: RoleCreate, 
    db: Session = Depends(get_db),
    current_user = Depends(require_permission(Permissions.CREATE_ROLE))
):
    return create_role(db, role)

@role_router.put("/roles/{role_id}", response_model=RoleResponse)
def update_role(
    role_id: int, 
    data: RoleUpdate, 
    db: Session = Depends(get_db), 
    current_user = Depends(require_permission(Permissions.UPDATE_ROLE))
):
    updated_role = update_role(db, role_id, data)
    return updated_role
    
@role_router.get("/role/{role_id}")
def get_role(
    role_id: int, 
    db: Session = Depends(get_db),
    current_user = Depends(require_permission(Permissions.READ_ROLE))
):
    return get_role_by_id(db, role_id)

@role_router.get("/roles/", response_model=List[RoleResponse])
def get_roles(
    db: Session = Depends(get_db), 
    current_user = Depends(require_permission(Permissions.READ_ROLE))
):
    return get_all_roles(db)

@role_router.post("/roles/")
def delete_user_role(
    role_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(require_permission(Permissions.DELETE_ROLE))
):
    if not delete_role(db, role_id):
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            detail="Role not found"
        )
    
@role_router.post(
    "/roles/{role_id}/permissions",
    response_model=RoleResponse,
)
def assign_permissions(
    role_id: int,
    data: RolePermissionAssign,
    db: Session = Depends(get_db),
    current_user = Depends(require_permission(Permissions.UPDATE_ROLE))
):
    return assign_permissions_to_role(db, role_id, data.permissions)

@role_router.delete(
    "/roles/{role_id}/permissions",
    response_model=RoleResponse,
)
def remove_permissions(
    role_id: int,
    data: RolePermissionAssign,
    db: Session = Depends(get_db),
    current_user = Depends(require_permission(Permissions.UPDATE_ROLE))
):
    role = db.query(Role).filter_by(id=role_id).first()

    if not role:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Role not found")

    role.permissions = [
        perm for perm in role.permissions
        if perm.name not in [p.value for p in data.permissions]
    ]

    db.commit()
    db.refresh(role)
    return role