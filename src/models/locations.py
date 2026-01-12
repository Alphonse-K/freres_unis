from sqlalchemy import Column, Integer, String, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from src.core.database import Base


class Country(Base):
    __tablename__ = "countries"

    id = Column(Integer, primary_key=True)
    code = Column(String(2), unique=True, nullable=False)
    name = Column(String(120), nullable=False)
    phone_code = Column(String(10))
    currency_code = Column(String(3))
    is_active = Column(Boolean, default=True)

    regions = relationship("Region", back_populates="country")
    addresses = relationship("Address", back_populates="country")


class Region(Base):
    __tablename__ = "regions"

    id = Column(Integer, primary_key=True)
    country_id = Column(Integer, ForeignKey("countries.id"), nullable=False)
    name = Column(String(120), nullable=False)
    code = Column(String(20))

    country = relationship("Country", back_populates="regions")
    cities = relationship("City", back_populates="region")
    addresses = relationship("Address", back_populates="region")


class City(Base):
    __tablename__ = "cities"

    id = Column(Integer, primary_key=True)
    region_id = Column(Integer, ForeignKey("regions.id"), nullable=False)
    name = Column(String(120), nullable=False)
    postal_code = Column(String(20))

    region = relationship("Region", back_populates="cities")
    addresses = relationship("Address", back_populates="city")


class Address(Base):
    __tablename__ = "addresses"

    id = Column(Integer, primary_key=True)

    country_id = Column(Integer, ForeignKey("countries.id"), nullable=False)
    region_id = Column(Integer, ForeignKey("regions.id"), nullable=True)
    city_id = Column(Integer, ForeignKey("cities.id"), nullable=True)

    street_1 = Column(String(255))
    street_2 = Column(String(255))
    is_default = Column(Boolean, default=False)

    # ownership
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=True)
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=True)
    pos_id = Column(Integer, ForeignKey("pos.id"), nullable=True)
    
    # ownership
    provider_id = Column(Integer, ForeignKey("providers.id"), nullable=True)

    # owners
    provider = relationship("Provider", back_populates="addresses")

    # geography
    country = relationship("Country", back_populates="addresses")
    region = relationship("Region", back_populates="addresses")
    city = relationship("City", back_populates="addresses")

    # owners
    user = relationship("User", back_populates="addresses")
    client = relationship("Client", back_populates="addresses")
    employee = relationship("Employee", back_populates="addresses")
    pos = relationship("POS", back_populates="addresses")
