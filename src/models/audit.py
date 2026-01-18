# models/audit_log.py
from sqlalchemy import Column, String, Integer, Boolean, DateTime, func, Index, Text, JSON
from src.core.database import Base 
from datetime import timezone, datetime


class AuditLog(Base):
    __tablename__ = "audit_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Who performed the action
    actor_type = Column(String(50))  # 'admin', 'system', 'user', 'client'
    actor_id = Column(Integer)  # ID of the admin/user/client
    
    # What was affected
    target_type = Column(String(50))  # 'client', 'user', 'posuser'
    target_id = Column(Integer)  # ID of the affected account
    
    # Action details
    action = Column(String(100))  # e.g., 'set_password', 'reset_pin', 'change_password'
    details = Column(JSON)  # Additional details in JSON format
    
    # Technical details
    ip_address = Column(String(45))
    user_agent = Column(Text, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), default=datetime.now(timezone.utc))
    
    # Indexes for fast querying
    __table_args__ = (
        Index('idx_actor', 'actor_type', 'actor_id'),
        Index('idx_target', 'target_type', 'target_id'),
        Index('idx_action', 'action'),
        Index('idx_created_at', 'created_at'),
    )