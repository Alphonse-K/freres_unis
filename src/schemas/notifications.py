from pydantic import BaseModel, ConfigDict, Field
from typing import List


class NotificationTemplateCreate(BaseModel):
    name: str
    title: str
    content: str


class NotificationTemplateUpdate(BaseModel):
    name: str | None = None
    title: str | None = None
    content: str | None = None


class NotificationTemplateOut(BaseModel):
    id: int
    name: str
    title: str
    content: str
    model_config = ConfigDict(from_attributes=True)


class NotificationOut(BaseModel):
    id: int
    title: str
    content: str
    is_read: bool
    model_config = ConfigDict(from_attributes=True)


class SendNotificationRequest(BaseModel):
    template_id: int
    user_ids: List[int] = None
    send_to_all: bool = False

    # ONE payload for all users
    variables: dict | None = Field(
        default=None,
        example={
            "name": "Alphonse",
            "balance": "5000 GNF"
        }
    )  

    # PERSONALIZED payloads
    per_user_variables: List[dict] | None = Field(
        default=None,
        example=[
            {"name": "Alphonse", "balance": "5000 GNF"},
            {"name": "Pathe", "balance": "10000 GNF"}
        ]
    )