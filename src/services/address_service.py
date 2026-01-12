from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from src.models.locations import Country, Region, City, Address
from src.schemas.location import (
    CountryCreate, CountryUpdate,
    RegionCreate, RegionUpdate,
    CityCreate, CityUpdate,
    AddressCreate, AddressUpdate
)


# -------------------------------
# COUNTRY SERVICES
# -------------------------------
class CountryService:

    @staticmethod
    def create(db: Session, data: CountryCreate) -> Country:
        if db.query(Country).filter_by(code=data.code).first():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Country code already exists"
            )

        country = Country(**data.model_dump())
        db.add(country)
        db.commit()
        db.refresh(country)
        return country

    @staticmethod
    def list(db: Session):
        return db.query(Country).order_by(Country.name).all()

    @staticmethod
    def update(db: Session, country_id: int, data: CountryUpdate) -> Country:
        country = db.get(Country, country_id)
        if not country:
            raise HTTPException(status_code=404, detail="Country not found")

        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(country, field, value)

        db.commit()
        db.refresh(country)
        return country


# -------------------------------
# REGION SERVICES
# -------------------------------
class RegionService:

    @staticmethod
    def create(db: Session, data: RegionCreate) -> Region:
        region = Region(**data.model_dump())
        db.add(region)
        db.commit()
        db.refresh(region)
        return region

    @staticmethod
    def update(db: Session, region_id: int, data: RegionUpdate) -> Region:
        region = db.get(Region, region_id)
        if not region:
            raise HTTPException(status_code=404, detail="Region not found")

        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(region, field, value)

        db.commit()
        db.refresh(region)
        return region


# -------------------------------
# CITY SERVICES
# -------------------------------
class CityService:

    @staticmethod
    def create(db: Session, data: CityCreate) -> City:
        city = City(**data.model_dump())
        db.add(city)
        db.commit()
        db.refresh(city)
        return city


# -------------------------------
# ADDRESS SERVICES
# -------------------------------
class AddressService:

    @staticmethod
    def create_for_user(
        db: Session,
        user_id: int,
        data: AddressCreate
    ) -> Address:

        payload = data.model_dump()
        payload["user_id"] = user_id

        if payload.get("is_default"):
            db.query(Address).filter(
                Address.user_id == user_id,
                Address.is_default.is_(True)
            ).update({"is_default": False})

        address = Address(**payload)
        db.add(address)
        db.commit()
        db.refresh(address)
        return address

    @staticmethod
    def list_for_user(db: Session, user_id: int):
        return db.query(Address).filter_by(user_id=user_id).all()

    @staticmethod
    def update(
        db: Session,
        address_id: int,
        data: AddressUpdate
    ) -> Address:

        address = db.get(Address, address_id)
        if not address:
            raise HTTPException(status_code=404, detail="Address not found")

        if data.is_default:
            db.query(Address).filter(
                Address.user_id == address.user_id,
                Address.is_default.is_(True)
            ).update({"is_default": False})

        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(address, field, value)

        db.commit()
        db.refresh(address)
        return address
