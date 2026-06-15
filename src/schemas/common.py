from pydantic import BaseModel, ConfigDict

class SimpleWarehouse(BaseModel):
    id: int
    name: str
    