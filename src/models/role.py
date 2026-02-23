from sqlalchemy import Column, String, Integer, Date, func
from src.core.database import Base
from src.models.users import User
from src.models.rbac_assiciation import role_permissions, user_roles, posuser_roles, client_roles
from sqlalchemy.orm import relationship


class Role(Base):
    __tablename__ = "roles"

    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True)
    permissions = relationship(
        "Permission",
        secondary=role_permissions,
        back_populates="roles"
    )
    users = relationship(
        "User",
        secondary=user_roles,
        back_populates="roles"
    )
    clients = relationship(
        "Client",
        secondary=client_roles,
        back_populates="roles"
    )
    posusers = relationship(
        "POSUser",
        secondary=posuser_roles,
        back_populates="roles"
    )
