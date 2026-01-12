# src/schemas/company.py
from pydantic import BaseModel, ConfigDict, Field, EmailStr
from typing import Optional, List
from datetime import datetime
from decimal import Decimal

class CompanyBase(BaseModel):
    name: str = Field(..., max_length=150, description="Company legal or business name")
    email: EmailStr = Field(..., max_length=150, description="Company contact email")
    phone: Optional[str] = Field(None, max_length=50, description="Primary phone number")
    address: Optional[str] = Field(None, max_length=255, description="Full postal address")
    is_active: Optional[bool] = Field(True, description="Active status flag")

class CompanyCreate(CompanyBase):
    pass  # No additional fields required at creation

class CompanyUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=150)
    email: Optional[EmailStr] = Field(None, max_length=150)
    phone: Optional[str] = Field(None, max_length=50)
    address: Optional[str] = Field(None, max_length=255)
    is_active: Optional[bool] = None

    # Input validation only — no ORM hydration

class CompanyOut(CompanyBase):
    id: int
    created_at: datetime
    api_keys: Optional[List["APIKeyOut"]] = None  # Nested response if eager-loaded

    model_config = ConfigDict(from_attributes=True)

# Resolve forward refs for nested output
from src.schemas.security import APIKeyOut  # or wherever APIKeyOut is defined
CompanyOut.model_rebuild()
