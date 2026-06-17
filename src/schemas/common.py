from pydantic import BaseModel, ConfigDict, Field
from decimal import Decimal
from typing import Annotated
import enum


class ClientType(str, enum.Enum):
    PARTNER_CLIENT = "partner_client"
    ORDINARY = "ordinary"

class ClientStatus(str, enum.Enum):
    ACTIVE = "active"
    SUSPENDED = "suspended"
    BANNED = "banned"
    INACTIVE = "inactive"
    DELETED = "deleted"

Money = Annotated[Decimal, Field(max_digits=12, decimal_places=2, examples=["1500.00"])]
OptionalMoney = Annotated[Decimal | None, Field(None, max_digits=12, decimal_places=2, examples=["500.00"])]


class SimpleWarehouse(BaseModel):
    id: int
    name: str
    

class ClientSimple(BaseModel):
    id: int
    first_name: str
    last_name: str
    phone: str
    type: ClientType
    status: ClientStatus
    current_balance: Decimal

    model_config = ConfigDict(from_attributes=True)