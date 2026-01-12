from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

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
# USER ADDRESSES
# -------------------------------
@address_router.post("/users/{user_id}/addresses", response_model=AddressOut)
def create_user_address(
    user_id: int,
    payload: AddressCreate,
    db: Session = Depends(get_db)
):
    return AddressService.create_for_user(db, user_id, payload)


@address_router.get("/users/{user_id}/addresses", response_model=list[AddressOut])
def list_user_addresses(user_id: int, db: Session = Depends(get_db)):
    return AddressService.list_for_user(db, user_id)


@address_router.patch("/addresses/{address_id}", response_model=AddressOut)
def update_address(
    address_id: int,
    payload: AddressUpdate,
    db: Session = Depends(get_db)
):
    return AddressService.update(db, address_id, payload)
