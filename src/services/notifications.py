from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from src.models.notifications import NotificationTemplate, Notification
from src.models.clients import Client
from src.schemas.notifications import (
    SendNotificationRequest, 
    NotificationTemplateUpdate
)


class TemplateEngine:
    @staticmethod
    def render(content: str, variables: dict) -> str:
        for key, value in variables.items():
            placeholder = "{{" + key + "}}"
            content = content.replace(placeholder, str(value))
        return content
    
    @staticmethod
    def update_template(
        db: Session, 
        template_id: int, 
        data: NotificationTemplateUpdate
    ):
        template = (
            db.query(NotificationTemplate)
            .filter_by(id=template_id)
            .first()
        )
        if not template:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Template {template_id} not found"
            )
        
        for key, value in data.model_dump(exclude_unset=True).items():
            setattr(template, key, value)

        db.commit()
        db.refresh(template)
        return template
    

class NotificationService:

    @staticmethod
    def send(db: Session, payload: SendNotificationRequest):
        template = db.query(NotificationTemplate).get(payload.template_id)
        if not template:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, 
                detail="Template not found"
            )

        if payload.send_to_all:
            users = db.query(Client).all()
        else:
            users = db.query(Client).filter(
                Client.id.in_(payload.user_ids)
            ).all()

        notifications = []

        # CASE 1: personalized
        if payload.per_user_variables:
            if len(users) != len(payload.per_user_variables):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST, 
                    detail="Mismatch users and variables"
                )

            for user, vars in zip(users, payload.per_user_variables):
                content = TemplateEngine.render(template.content, vars)
                title = TemplateEngine.render(template.title, vars)

                notifications.append(Notification(
                    user_id=user.id,
                    title=title,
                    content=content
                ))

        # CASE 2: shared variables
        else:
            for user in users:
                content = TemplateEngine.render(
                    template.content,
                    payload.variables or {}
                )

                title = TemplateEngine.render(
                    template.title,
                    payload.variables or {}
                )

                notifications.append(Notification(
                    user_id=user.id,
                    title=title,
                    content=content
                ))

        db.bulk_save_objects(notifications)
        db.commit()
        return {"sent": len(notifications)}
    
