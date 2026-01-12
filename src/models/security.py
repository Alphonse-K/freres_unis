from sqlalchemy import Column, String, Integer, Index, Boolean, ForeignKey, DateTime, func, JSON
from sqlalchemy.orm import relationship
from src.core.database import Base 


# ========== AUTH MODELS ==========
class JWTBlacklist(Base):
    __tablename__ = "jwt_blacklist"
    
    id = Column(Integer, primary_key=True, index=True)
    jti = Column(String(36), unique=True, index=True, nullable=False)
    account_id = Column(Integer, nullable=False)  # could be User, Client, or POSUser
    account_type = Column(String(20), nullable=False)  # 'user', 'client', 'posuser'
    token = Column(String(500), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    revoked_at = Column(DateTime(timezone=True), server_default=func.now())
    reason = Column(String(50))

    __table_args__ = (
        Index('ix_jwt_blacklist_account', 'account_id', 'account_type'),
        Index('ix_jwt_blacklist_expires', 'expires_at'),
    )


class OTPCode(Base):
    __tablename__ = "otp_codes"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    code = Column(String(6), nullable=False)
    purpose = Column(String(20), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    is_used = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    user = relationship("User", back_populates="otp_codes")
    
    __table_args__ = (
        Index('ix_otp_codes_user_purpose', 'user_id', 'purpose'),
        Index('ix_otp_codes_expires', 'expires_at'),
    )


class APIKey(Base):
    __tablename__ = "api_keys"
    
    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)
    name = Column(String(100), nullable=False)
    key = Column(String(64), unique=True, index=True, nullable=False)
    secret = Column(String(128), nullable=False)
    is_active = Column(Boolean, default=True)
    permissions = Column(JSON, nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    last_used = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    company = relationship("Company", back_populates="api_keys")
    
    __table_args__ = (
        Index('ix_api_keys_company', 'company_id'),
        Index('ix_api_keys_active', 'is_active'),
    )


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    token = Column(String(64), unique=True, index=True, nullable=False)
    device_info = Column(JSON)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    user = relationship("User", back_populates="refresh_tokens")
    
    __table_args__ = (
        Index('ix_refresh_tokens_user_active', 'user_id', 'is_active'),
    )
