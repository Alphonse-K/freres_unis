from decimal import Decimal
from datetime import datetime, time
from typing import Optional, Generic, TypeVar, List
from pydantic import BaseModel, Field, EmailStr, model_validator, ConfigDict ,field_validator
from src.models.users import UserRole, UserStatus
from src.schemas.pos import RoleSchema
import re

class UserBase(BaseModel):
    first_name: str = Field(..., min_length=2, max_length=120)
    last_name: str = Field(..., min_length=2, max_length=120)
    username: str = Field(..., min_length=2, max_length=120)
    email: EmailStr = Field(..., example="user@company.com")
    phone: Optional[str] = Field(None, max_length=15)
    status: UserStatus = UserStatus.ACTIVE
    failed_attempts: int = 0
    suspended_until: Optional[datetime] = None
    allowed_login_start: Optional[time] = Field(None, description="User activity starting time")
    allowed_login_end: Optional[time] = Field(None, description="User activity end time")
    require_password_change: bool = False


    @model_validator(mode="after")
    def validate_time_window(self):
        if self.allowed_login_start and self.allowed_login_end:
            if self.allowed_login_start >= self.allowed_login_end:
                raise ValueError("allowed_login_start must be ealier than allowed_login_end")
        return self
    

class UserCreate(UserBase):

    password: str = Field(..., min_length=8, max_length=128)

    @field_validator('password')
    def validate_create_password(cls, value):
        # Require at least one special character
        if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", value):
            raise ValueError("Password must contain at least one special character")
        return value
 

class UserUpdate(BaseModel):
    first_name: Optional[str] = Field(None, max_length=120)
    last_name: Optional[str] = Field(None, max_length=120)
    username: Optional[str] = Field(None, max_length=120)
    email: Optional[EmailStr] = None
    phone: Optional[str] = Field(None, max_length=50)
    status: Optional[UserStatus] = None
    suspended_until: Optional[datetime] = None
    allowed_login_start: Optional[time] = None
    allowed_login_end: Optional[time] = None
    require_password_change: Optional[bool] = None

    @model_validator(mode="after")
    def validate_update_time_window(self):
        if self.allowed_login_start and self.allowed_login_end:
            if self.allowed_login_start >= self.allowed_login_end:
                raise ValueError("allowed_login_start must be earlier than allowed_login_end")
        return self
    

class PasswordLogin(BaseModel):
    email: Optional[EmailStr] = None  # for User
    phone: Optional[str] = None       # for POSUser or Client
    password: str


class PinLogin(BaseModel):
    phone: str
    pin: str


class UserOut(UserBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime]
    last_login: Optional[datetime]

    model_config = ConfigDict(from_attributes=True)


class UserSchema(BaseModel):
    id: int
    email: EmailStr = Field(None)
    username: str
    roles: List[RoleSchema]

    model_config = ConfigDict(from_attributes=True)


class LogoutResponse(BaseModel):
    message: str


class UserFilter(BaseModel):
    roles: Optional[List[RoleSchema]] = None
    status: Optional[UserStatus] = None
    email: Optional[str] = Field(None, description="Partial email match")
    username: Optional[str] = Field(None, description="Partial username match")
    phone: Optional[str] = Field(None)
    created_from: Optional[datetime] = None
    created_to: Optional[datetime] = None


class PaginationParams(BaseModel):
    page: int = Field(1, ge=1)
    page_size: int = Field(20, ge=1, le=100)

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.page_size


T = TypeVar("T")

class PaginatedResponse(BaseModel, Generic[T]):
    total: int
    page: int
    page_size: int
    items: List[T]



