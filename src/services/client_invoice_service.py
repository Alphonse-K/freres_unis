# src/services/client_invoice_service.py
from sqlalchemy.orm import Session
from src.models.clients import ClientInvoice
from src.schemas.clients import ClientInvoiceCreate
from src.core.audit import audit_log


class ClientInvoiceService:

    @staticmethod
    def create(db: Session, data: ClientInvoiceCreate) -> ClientInvoice:
        invoice = ClientInvoice(**data.model_dump())
        db.add(invoice)
        db.commit()
        db.refresh(invoice)

        audit_log("CREATE", "ClientInvoice", invoice.id, None)
        return invoice

    @staticmethod
    def list_by_client(db: Session, client_id: int):
        return db.query(ClientInvoice).filter_by(client_id=client_id).all()
