from pydantic import BaseModel, ConfigDict, Field, field_validator, EmailStr
from typing import Optional, Dict, Any
from datetime import datetime


class JWTBlacklistBase(BaseModel):
    jti: str = Field(..., max_length=36, description="Token unique identifier (JTI)")
    account_id: int = Field(..., description="Owner of the blacklisted token")
    token: str = Field(..., max_length=500, description="Raw JWT token string")
    expires_at: datetime = Field(..., description="Token expiry timestamp")
    reason: Optional[str] = Field(None, max_length=50, description="Revocation reason")



class JWTBlacklistCreate(JWTBlacklistBase):
    pass  # All required fields already defined in Base


class JWTBlacklistOut(JWTBlacklistBase):
    id: int
    revoked_at: datetime

    model_config = ConfigDict(from_attributes=True)


class OTPCodeBase(BaseModel):
    user_id: int = Field(..., description="User receiving the OTP")
    code: str = Field(..., min_length=6, max_length=6, description="6-digit OTP code")
    purpose: str = Field(..., max_length=20, description="OTP purpose (login, transfer, etc.)")
    expires_at: datetime = Field(..., description="OTP expiry timestamp")
    is_used: Optional[bool] = Field(False, description="Whether OTP was consumed")


class OTPCodeCreate(OTPCodeBase):
    pass


class OTPCodeUpdate(BaseModel):
    code: Optional[str] = Field(None, min_length=6, max_length=6)
    expires_at: Optional[datetime] = None
    is_used: Optional[bool] = None

    # No ORM hydration — input validation only

class OTPCodeOut(OTPCodeBase):
    id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class OTPVerify(BaseModel):
    email: EmailStr = Field(..., example="user@company.com")
    otp_code: str = Field(..., example="123456")
    
    @field_validator('otp_code')
    @classmethod
    def validate_otp_format(cls, v: str) -> str:
        if not v.isdigit() or len(v) != 6:
            raise ValueError('OTP must be 6 digits')
        return v


class APIKeyBase(BaseModel):
    company_id: int = Field(..., description="Company that owns the API key")
    name: str = Field(..., max_length=100, description="Key label/name")
    is_active: Optional[bool] = Field(True, description="Key enabled status")
    permissions: Optional[Dict[str, Any]] = Field(None, description="JSON permissions blob")
    expires_at: Optional[datetime] = None
    last_used: Optional[datetime] = None


class APIKeyCreate(APIKeyBase):
    key: str = Field(..., min_length=32, max_length=64, description="Public key")
    secret: str = Field(..., min_length=64, max_length=128, description="Key secret")


class APIKeyUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=100)
    is_active: Optional[bool] = None
    permissions: Optional[Dict[str, Any]] = None
    expires_at: Optional[datetime] = None

    # No ORM hydration — PATCH JSON only


class APIKeyOut(APIKeyBase):
    id: int
    key: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class RefreshTokenRequest(BaseModel):
    refresh_token: str = Field(..., min_length=32)


class TokenPairResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    access_expires_at: datetime
    refresh_expires_at: datetime

    model_config = ConfigDict(from_attributes=True)

