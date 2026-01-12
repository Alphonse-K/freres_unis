# src/services/client_payment_service.py
from fastapi import status, HTTPException
from sqlalchemy.orm import Session
from src.models.clients import ClientPayment, Client, ClientInvoice
from src.schemas.clients import ClientPaymentCreate
from src.core.audit import audit_log


class ClientPaymentService:

    @staticmethod
    def create(db: Session, data: ClientPaymentCreate) -> ClientPayment:
        client = db.query(Client).filter_by(id=data.client_id).first()
        if not client:
            raise HTTPException(status.HTTP_404_NOT_FOUND,"Client not found")

        payment = ClientPayment(**data.model_dump())
        db.add(payment)

        client.current_balance -= data.amount

        if data.client_invoice_id:
            invoice = db.query(ClientInvoice).filter_by(id=data.client_invoice_id).first()
            if not invoice:
                raise HTTPException(status.HTTP_404_NOT_FOUND, "Invoice not found")

            invoice.paid_amount += data.amount

        db.commit()
        db.refresh(payment)

        audit_log("PAYMENT", "Client", client.id, None, {"amount": data.amount})
        return payment
    

