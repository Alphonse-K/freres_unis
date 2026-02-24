# src/services/user_service.py

from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from typing import List, Optional

from src.models.users import User, UserStatus, UserRole
from src.schemas.users import UserCreate, UserUpdate, PaginationParams, UserFilter
from src.core.security import SecurityUtils


class UserService:

    @staticmethod
    def create_user(db: Session, user_data: UserCreate) -> User:
        # Uniqueness checks
        exists = db.query(User).filter(
            (User.email == user_data.email) |
            (User.username == user_data.username)
        ).first()

        if exists:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email or username already exists"
            )

        hashed_password = SecurityUtils.hash_password(user_data.password)

        user = User(
            first_name=user_data.first_name,
            last_name=user_data.last_name,
            username=user_data.username,
            email=user_data.email,
            phone=user_data.phone,
            role=user_data.role,
            status=user_data.status,
            failed_attempts=user_data.failed_attempts,
            suspended_until=user_data.suspended_until,
            allowed_login_start=user_data.allowed_login_start,
            allowed_login_end=user_data.allowed_login_end,
            require_password_change=user_data.require_password_change,
            password_hash=hashed_password
        )

        db.add(user)
        db.commit()
        db.refresh(user)

        return user
    

    @staticmethod
    def update_user(db: Session, user_id: int, data: UserUpdate) -> User:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        updates = data.model_dump(exclude_unset=True)

        for field, value in updates.items():
            if field == "password":
                user.password_hash = SecurityUtils.hash_password(value)
            else:
                setattr(user, field, value)

        db.commit()
        db.refresh(user)
        return user
    
    @staticmethod
    def delete_user(db: Session, user_id: int) -> None:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        user.status = UserStatus.DELETED
        db.commit()
    
    @staticmethod
    def list_users(
        db: Session,
        filters: UserFilter,
        pagination: PaginationParams,
    ):
        query = db.query(User)

        # if filters.role:
        #     query = query.filter(User.role == filters.role)

        if filters.status:
            query = query.filter(User.status == filters.status)

        if filters.email:
            query = query.filter(User.email.ilike(f"%{filters.email}%"))

        if filters.username:
            query = query.filter(User.username.ilike(f"%{filters.username}%"))

        if filters.phone:
            query = query.filter(User.phone.ilike(f"%{filters.phone}%"))

        if filters.created_from:
            query = query.filter(User.created_at >= filters.created_from)

        if filters.created_to:
            query = query.filter(User.created_at <= filters.created_to)

        total = query.count()

        items = (
            query
            .order_by(User.created_at.desc())
            .offset(pagination.offset)
            .limit(pagination.page_size)
            .all()
        )

        return total, items