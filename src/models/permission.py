from sqlalchemy import Column, String, Integer
from src.core.database import Base
from src.models.rbac_assiciation import role_permissions
from sqlalchemy.orm import relationship


class Permission(Base):
    __tablename__ = "permissions"
    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True)
    roles = relationship(
        "Role",
        secondary=role_permissions,
        back_populates="permissions"
    )
