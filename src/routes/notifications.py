from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from src.core.database import get_db
from src.schemas.notifications import (
    NotificationOut,
    NotificationTemplateOut,
    NotificationTemplateCreate,
    SendNotificationRequest,
    NotificationTemplateUpdate
)
from src.models.notifications import NotificationTemplate, Notification
from src.models.clients import Client
from src.services.notifications import NotificationService, TemplateEngine
from src.core.permissions import Permissions
from src.core.auth_dependencies import require_permission


notification_router = APIRouter(prefix="/notifications", tags=["Notifications"])

@notification_router.post(
    "/templates",
    response_model=NotificationTemplateOut
)
def create_template(
    data: NotificationTemplateCreate, 
    db: Session = Depends(get_db),
    current_user = Depends(require_permission(Permissions.NOTIFICATION_CREATE))
):
    template = NotificationTemplate(**data.model_dump())
    db.add(template)
    db.commit()
    db.refresh(template)
    return template


@notification_router.put(
    "/templates/{template_id}/update",
    response_model=NotificationTemplateOut
)
def update_template(
    template_id: int,
    data: NotificationTemplateUpdate,
    db: Session = Depends(get_db),
    current_user = Depends(require_permission(Permissions.NOTIFICATION_UPDATE))
):
    return TemplateEngine.update_template(db, template_id, data)


@notification_router.get(
    "/templates",
    response_model=list[NotificationTemplateOut]
)
def list_templates(
    db: Session = Depends(get_db),
    current_user = Depends(require_permission(Permissions.NOTIFICATION_READ))
):
    return db.query(NotificationTemplate).all()


@notification_router.post("/send")
def send_notification(
    payload: SendNotificationRequest, 
    db: Session = Depends(get_db)
):
    return NotificationService.send(db, payload)

@notification_router.get(
    "/list/{user_id}/user",
    # response_model=list[NotificationOut]
)
def list_user_notification(
    user_id: int, 
    db: Session = Depends(get_db)
):
    notifications = (
        db.query(Notification)
        .filter(Notification.user_id == user_id)
        .all()
    )
    if not notifications:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Empty notifications"
        )
    return notifications

@notification_router.post(
    "/{notification_id}/read", 
    response_model=None
)
def mark_as_read(notification_id: int, db: Session = Depends(get_db)):
    notif = db.query(Notification).get(notification_id)
    notif.is_read = True
    db.commit()

@notification_router.post(
    "/read-all", 
    response_model=None
)
def mark_all_as_read(user_id: int, db: Session = Depends(get_db)):
    db.query(Notification).filter(
        Notification.user_id == user_id,
        Notification.is_read == False
    ).update({"is_read": True})
    db.commit()
