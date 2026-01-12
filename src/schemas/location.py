# src/schemas/geography.py
from typing import Optional, List
from pydantic import BaseModel, Field, ConfigDict


# -------------------------------
# COUNTRY SCHEMAS
# -------------------------------
class CountryBase(BaseModel):
    code: str = Field(..., max_length=2)
    name: str = Field(..., max_length=120)
    phone_code: Optional[str] = None
    currency_code: Optional[str] = None
    is_active: Optional[bool] = True


class CountryCreate(CountryBase):
    pass


class CountryUpdate(BaseModel):
    code: Optional[str] = None
    name: Optional[str] = None
    phone_code: Optional[str] = None
    currency_code: Optional[str] = None
    is_active: Optional[bool] = None


class CountryOut(CountryBase):
    id: int
    regions: List["RegionOut"] = []

    model_config = ConfigDict(from_attributes=True)


# -------------------------------
# REGION SCHEMAS
# -------------------------------
class RegionBase(BaseModel):
    name: str = Field(..., max_length=120)
    code: Optional[str] = None
    country_id: int


class RegionCreate(RegionBase):
    pass


class RegionUpdate(BaseModel):
    name: Optional[str] = None
    code: Optional[str] = None
    country_id: Optional[int] = None


class RegionOut(RegionBase):
    id: int
    cities: List["CityOut"] = []

    model_config = ConfigDict(from_attributes=True)


# -------------------------------
# CITY SCHEMAS
# -------------------------------
class CityBase(BaseModel):
    name: str = Field(..., max_length=120)
    postal_code: Optional[str] = None
    region_id: int


class CityCreate(CityBase):
    pass


class CityUpdate(BaseModel):
    name: Optional[str] = None
    postal_code: Optional[str] = None
    region_id: Optional[int] = None


class CityOut(CityBase):
    id: int

    model_config = ConfigDict(from_attributes=True)


# -------------------------------
# ADDRESS SCHEMAS
# -------------------------------
class AddressBase(BaseModel):
    street_1: Optional[str] = Field(None, max_length=255)
    street_2: Optional[str] = Field(None, max_length=255)
    is_default: Optional[bool] = False

    country_id: int
    region_id: Optional[int] = None
    city_id: Optional[int] = None

    # ownership
    user_id: Optional[int] = None
    client_id: Optional[int] = None
    employee_id: Optional[int] = None
    pos_id: Optional[int] = None
    provider_id: Optional[int] = None


class AddressCreate(AddressBase):
    pass


class AddressUpdate(BaseModel):
    street_1: Optional[str] = None
    street_2: Optional[str] = None
    is_default: Optional[bool] = None

    country_id: Optional[int] = None
    region_id: Optional[int] = None
    city_id: Optional[int] = None

    user_id: Optional[int] = None
    client_id: Optional[int] = None
    employee_id: Optional[int] = None
    pos_id: Optional[int] = None
    provider_id: Optional[int] = None


class AddressOut(AddressBase):
    id: int
    country: Optional[CountryOut] = None
    region: Optional[RegionOut] = None
    city: Optional[CityOut] = None

    model_config = ConfigDict(from_attributes=True)


# -------------------------------
# Pydantic v2: rebuild models to resolve forward references
# -------------------------------
CountryOut.model_rebuild()
RegionOut.model_rebuild()
CityOut.model_rebuild()
AddressOut.model_rebuild()
