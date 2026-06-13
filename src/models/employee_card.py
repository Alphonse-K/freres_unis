# models/employee_card.py
import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from src.core.database import Base


class EmployeeCardRequest(Base):
    __tablename__ = "employee_card_requests"

    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=False)
    status = Column(String, default="pending")  # pending, approved, rejected
    reason = Column(String, nullable=True)       # optional note from creator
    rejection_reason = Column(String, nullable=True)
    requested_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
        nullable=False
    )
    reviewed_at = Column(DateTime(timezone=True), nullable=True)
    created_by_id = Column(Integer, ForeignKey("pos_user.id"), nullable=False)
    reviewed_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    employee = relationship("Employee", back_populates="card_requests")
    created_by = relationship("POSUser", foreign_keys=[created_by_id])
    reviewed_by = relationship("User", foreign_keys=[reviewed_by_id])


class EmployeeCard(Base):
    __tablename__ = "employee_cards"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=False)
    card_number = Column(String, unique=True, index=True)
    qr_token_hash = Column(String, nullable=False)
    qr_code_path = Column(String)
    issued_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
        nullable=False
    )
    expires_at = Column(DateTime(timezone=True), nullable=False)
    is_active = Column(Boolean, default=True)
    revoked_at = Column(DateTime(timezone=True), nullable=True)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)

    employee = relationship("Employee", back_populates="card")
    creator = relationship("User", foreign_keys=[created_by])


class EmployeeCardScanLog(Base):
    __tablename__ = "employee_card_scan_logs"

    id = Column(Integer, primary_key=True)
    card_id = Column(UUID(as_uuid=True), ForeignKey("employee_cards.id"), nullable=False, index=True)
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=False, index=True)
    scanned_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    scanned_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True
    )
    ip_address = Column(String, nullable=False)

    card = relationship("EmployeeCard")
    employee = relationship("Employee")