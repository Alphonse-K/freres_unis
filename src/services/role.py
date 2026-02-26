from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from src.models.role import Role 
from src.models.permission import Permission
from src.core.permissions import Permissions
from typing import List
from src.models.clients import Client
from src.models.users import User
from src.models.pos import POSUser

MODEL_MAP = {
    "CLIENT": Client,
    "USER": User,
    "POS_USER": POSUser
}

def create_role(db: Session, role):
    db_role = Role(name=role.name)
    db.add(db_role)
    db.commit()
    db.refresh(db_role)
    return db_role

def assign_roles_to_entity(
    db: Session,
    entity_type: str,
    entity_id: int,
    role_ids: List[int]
):
    Model = MODEL_MAP.get(entity_type.upper())

    if not Model:
        raise HTTPException(status_code=400, detail="Invalid entity type")

    entity = db.query(Model).filter(Model.id == entity_id).first()

    if not entity:
        raise HTTPException(status_code=404, detail="Entity not found")

    roles = db.query(Role).filter(Role.id.in_(role_ids)).all()
    entity.roles = roles
    db.commit()
    db.refresh(entity)
    return entity

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
    role = db.query(Role).filter(Role.id == role_id)
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

def assign_permissions_to_role(
    db: Session,
    role_id: int,
    permission_ids: list[int]
):
    role = db.query(Role).filter_by(id=role_id).first()

    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Role not found"
        )

    permissions = db.query(Permission).filter(
        Permission.id.in_(permission_ids)
    ).all()

    if not permissions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No valid permissions found"
        )

    role.permissions = permissions
    db.commit()
    db.refresh(role)
    return role
