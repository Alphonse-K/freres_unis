from pydantic import BaseModel, ConfigDict
from decimal import Decimal
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