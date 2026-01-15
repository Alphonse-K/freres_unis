from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import Optional
from src.core.database import get_db
from src.schemas.location import (
    CountryCreate, CountryUpdate, CountryOut,
    RegionCreate, RegionUpdate, RegionOut,
    CityCreate, CityOut,
    AddressCreate, AddressUpdate, AddressOut
)
from src.services.address_service import (
    CountryService, RegionService, CityService, AddressService
)

address_router = APIRouter(prefix="/address", tags=["Address"])

# -------------------------------
# COUNTRIES
# -------------------------------

@address_router.post("/countries", response_model=CountryOut)
def create_country(payload: CountryCreate, db: Session = Depends(get_db)):
    return CountryService.create(db, payload)


@address_router.get("/countries", response_model=list[CountryOut])
def list_countries(db: Session = Depends(get_db)):
    return CountryService.list(db)


@address_router.patch("/countries/{country_id}", response_model=CountryOut)
def update_country(
    country_id: int,
    payload: CountryUpdate,
    db: Session = Depends(get_db)
):
    return CountryService.update(db, country_id, payload)


# -------------------------------
# REGIONS
# -------------------------------
@address_router.post("/regions", response_model=RegionOut)
def create_region(payload: RegionCreate, db: Session = Depends(get_db)):
    return RegionService.create(db, payload)


@address_router.patch("/regions/{region_id}", response_model=RegionOut)
def update_region(
    region_id: int,
    payload: RegionUpdate,
    db: Session = Depends(get_db)
):
    return RegionService.update(db, region_id, payload)


# -------------------------------
# CITIES
# -------------------------------
@address_router.post("/cities", response_model=CityOut)
def create_city(payload: CityCreate, db: Session = Depends(get_db)):
    return CityService.create(db, payload)


# -------------------------------
# ADDRESS ENDPOINTS
# -------------------------------
@address_router.post("/addresses", response_model=AddressOut)
def create_address(
    payload: AddressCreate,
    db: Session = Depends(get_db)
):
    """
    Create an address. Owner can be assigned later via user_id, client_id, pos_id, employee_id, or provider_id.
    """
    return AddressService.create(db, payload)


@address_router.get("/addresses", response_model=list[AddressOut])
def list_addresses(
    user_id: Optional[int] = None,
    client_id: Optional[int] = None,
    employee_id: Optional[int] = None,
    pos_id: Optional[int] = None,
    provider_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """
    List addresses optionally filtered by owner.
    """
    return AddressService.list(db, user_id, client_id, employee_id, pos_id, provider_id)


@address_router.patch("/addresses/{address_id}", response_model=AddressOut)
def update_address(
    address_id: int,
    payload: AddressUpdate,
    db: Session = Depends(get_db)
):
    return AddressService.update(db, address_id, payload)
