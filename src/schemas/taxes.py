from decimal import Decimal
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict
from src.models.taxes import TaxType  # adjust import path if different


class TaxBase(BaseModel):
    name: str = Field(..., max_length=100, example="TVA 18%")
    rate: Decimal = Field(..., ge=0, le=100, example="18.00")
    type: TaxType = Field(..., description="Tax applicability")

    model_config = ConfigDict(from_attributes=True)


class TaxCreate(TaxBase):
    """Schema for creating a new tax record"""
    is_active: Optional[bool] = Field(default=True)


class TaxUpdate(BaseModel):
    """Schema for partial updates (exclude_unset allows PATCH-like behavior)"""
    name: Optional[str] = Field(None, max_length=100)
    rate: Optional[Decimal] = Field(None, ge=0, le=100)
    type: Optional[TaxType] = None
    is_active: Optional[bool] = None

    model_config = ConfigDict(from_attributes=True)


class TaxResponse(TaxBase):
    """Schema returned to API clients"""
    id: int
    is_active: bool
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
