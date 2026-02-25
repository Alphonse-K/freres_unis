from pydantic import BaseModel, ConfigDict
from typing import List, Optional
from src.core.permissions import Permissions

class RoleBase(BaseModel):
    name: str


class RoleCreate(RoleBase):
    permission_ids: Optional[List[int]] = []


class RoleUpdate(BaseModel):
    name: Optional[str] = None
    permission_ids: Optional[List[int]] = None


class RoleResponse(RoleBase):
    id: int
    model_config = ConfigDict(from_attributes=True)

class RolePermissionAssign(BaseModel):
    permission_ids: List[int]

class PermissionResponse(BaseModel):
    id: int
    name: str
    model_config = ConfigDict(from_attributes=True)