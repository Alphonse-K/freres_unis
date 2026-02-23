# src/models/users.py
from sqlalchemy import (
    Column, Integer, String, Boolean, DateTime, Enum as SAEnum, ForeignKey, Time
)
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from src.core.database import Base
from src.models.rbac_assiciation import user_roles

import enum

class UserRole(str, enum.Enum):
    ADMIN = "ADMIN"
    CHECKER = "CHECKER"
    MAKER = "MAKER"
    USER = "USER"
    PARTNERD = "PARTNERD"
    RH = "RH"
    FINANCE = "FINANCE"


class UserStatus(str, enum.Enum):
    ACTIVE = "active"
    SUSPENDED = "suspended"
    BANNED = "banned"
    INACTIVE = "inactive"
    DELETED = "deleted"


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    first_name = Column(String(120))
    last_name = Column(String(120))
    username = Column(String(120), unique=True, nullable=False)
    email = Column(String(255), unique=True)
    phone = Column(String(50), unique=True)
    password_hash = Column(String(255), nullable=False)
    last_login_ip = Column(String, nullable=True)
    last_login_user_agent = Column(String, nullable=True)
    status = Column(
        SAEnum(UserStatus, name="user_status_enum", create_constraint=True),
        nullable=False,
        default=UserStatus.ACTIVE
    )

    # Security & Logging
    failed_attempts = Column(Integer, default=0)
    last_login = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    suspended_until = Column(DateTime(timezone=True), nullable=True)
    allowed_login_start = Column(Time, nullable=True)
    allowed_login_end = Column(Time, nullable=True)

    # Flags
    require_password_change = Column(Boolean, default=False)

    addresses = relationship(
        "Address",
        back_populates="user",
        cascade="all, delete-orphan"
    )
    roles = relationship(
        "Role",
        secondary=user_roles,
        back_populates="users"
    )

    def __repr__(self):
        return f"<User {self.username} ({self.roles})>"



