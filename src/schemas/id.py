from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
from pydantic import ConfigDict

# Base schema
class IDTypeBase(BaseModel):
    name: str = Field(..., max_length=255)

    model_config = ConfigDict(from_attributes=True)

# Create schema
class IDTypeCreate(IDTypeBase):
    pass

# Update schema
class IDTypeUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=255)

    model_config = ConfigDict(from_attributes=True)

# Response schema
class IDTypeResponse(IDTypeBase):
    id: int
