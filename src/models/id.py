from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship
from src.core.database import Base


class IDType(Base):
    __tablename__ = "id_types"

    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False, unique=True)

    clients = relationship("Client", back_populates="id_type")
