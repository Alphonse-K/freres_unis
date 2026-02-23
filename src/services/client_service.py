# src/services/client_service.py
from fastapi import status, HTTPException
from sqlalchemy.orm import Session
from src.models.clients import Client
from src.schemas.clients import ClientUpdate
from src.schemas.users import PaginationParams
from src.core.audit import audit_log

class ClientService:

    @staticmethod
    def get(db: Session, client_id: int) -> Client:
        client = db.query(Client).filter_by(id=client_id).first()
        if not client:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Client not found")
        return client

    @staticmethod
    def list(db: Session, pagination: PaginationParams):
        query = db.query(Client)
        total = query.count()
        items = (
            query
            .order_by(Client.id.desc())
            .offset(pagination.offset)
            .limit(pagination.page_size)
            .all()
        )

        return total, items

    @staticmethod
    def update(
        db: Session,
        client_id: int,
        data: ClientUpdate,
        actor_id: int,
    ) -> Client:
        client = ClientService.get(db, client_id)
        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(client, field, value)

        db.commit()
        db.refresh(client)
        audit_log("UPDATE", "Client", client.id, actor_id)
        return client

    @staticmethod
    def change_status(
        db: Session,
        client_id: int,
        status,
        actor_id: int,
    ) -> Client:
        client = ClientService.get(db, client_id)
        client.status = status
        db.commit()

        audit_log("STATUS CHANGE", "Client", client.id, actor_id, {"status": status})
        return client
