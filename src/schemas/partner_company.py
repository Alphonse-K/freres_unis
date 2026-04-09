# # src/schemas/company.py
# from pydantic import BaseModel, ConfigDict, Field, EmailStr
# from typing import Optional, List
# from datetime import datetime
# from decimal import Decimal

# class CompanyBase(BaseModel):
#     name: str = Field(..., max_length=150, description="Company legal or business name")
#     email: EmailStr = Field(..., max_length=150, description="Company contact email")
#     phone: Optional[str] = Field(None, max_length=50, description="Primary phone number")
#     address: Optional[str] = Field(None, max_length=255, description="Full postal address")
#     is_active: Optional[bool] = Field(True, description="Active status flag")

# class CompanyCreate(CompanyBase):
#     pass  # No additional fields required at creation

# class CompanyUpdate(BaseModel):
#     name: Optional[str] = Field(None, max_length=150)
#     email: Optional[EmailStr] = Field(None, max_length=150)
#     phone: Optional[str] = Field(None, max_length=50)
#     address: Optional[str] = Field(None, max_length=255)
#     is_active: Optional[bool] = None

#     # Input validation only — no ORM hydration

# class CompanyOut(CompanyBase):
#     id: int
#     created_at: datetime
#     api_keys: Optional[List["APIKeyOut"]] = None  # Nested response if eager-loaded

#     model_config = ConfigDict(from_attributes=True)

# # Resolve forward refs for nested output
# from src.schemas.security import APIKeyOut  # or wherever APIKeyOut is defined
# CompanyOut.model_rebuild()

from pydantic import BaseModel, EmailStr, ConfigDict
from decimal import Decimal
from typing import Optional
from datetime import datetime


class CompanyCreate(BaseModel):
    name: str
    email: EmailStr
    phone: Optional[str] = None
    card_amount: Decimal
    address: Optional[str] = None

class CompanyUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    card_amount: Optional[Decimal] = None
    address: Optional[str] = None
    is_active: Optional[bool] = None


class CompanyOut(BaseModel):
    id: int
    name: str
    email: str
    phone: Optional[str]
    card_amount: Decimal
    address: Optional[str]
    is_active: bool
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)



class ClientApprovalInfo(BaseModel):
    employee_company: str | None = None
    magnetic_card_number: str | None = None
    model_config = ConfigDict(from_attributes=True)


class CompanyClientResponse(BaseModel):
    id: int
    first_name: str
    last_name: str
    phone: str
    balance: Decimal  # make sure this matches your Client model field
    approval: ClientApprovalInfo
    model_config = ConfigDict(from_attributes=True)

class CompanyClientsResponse(BaseModel):
    company_id: int
    company_name: str
    clients: list[CompanyClientResponse]
    model_config = ConfigDict(from_attributes=True)