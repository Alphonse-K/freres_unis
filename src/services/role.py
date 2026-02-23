from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from src.models.role import Role 
from src.models.permission import Permission
from src.core.permissions import Permissions
from typing import List

def create_role(db: Session, role):
    db_role = Role(name=role.name)
    db.add(db_role)
    db.commit()
    db.refresh(db_role)
    return db_role

def update_role(db: Session, role_id: int, role_data):
    role = db.query(Role).filter(Role.id == role_id).first()

    if not role:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            detail="Role not found"
        )
    role.name = role_data.name
    db.commit()
    db.refresh(role)
    return role

def get_all_roles(db: Session):
    roles = db.query(Role).all()
    return roles

def get_role_by_id(db: Session, role_id: int):
    role = db.query(Role).filer(Role.id == role_id)
    if not role:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            detail="Role not found"
        )
    return role

def delete_role(db: Session, role_id: int):
    role = db.query(Role).filter(Role.id == role_id)
    if not role:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            detail="Role not found"
        )
    role.delete()
    db.commit()

def assign_permissions_to_role(db: Session, role_id: int, permissions: list[Permissions]):
    role = db.query(Role).filter_by(id=role_id).first()

    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Role not found"
        )

    permission_objects = db.query(Permission).filter(
        Permission.name.in_([perm.value for perm in permissions])
    ).all()

    role.permissions = permission_objects  # replace all permissions
    db.commit()
    db.refresh(role)

    return role