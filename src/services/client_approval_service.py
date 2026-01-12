# src/services/client_approval_service.py
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from src.models.clients import ClientApproval, Client
from src.schemas.clients import (
    ClientApprovalCreate,
    ClientApprovalUpdate,
)

import logging

logger = logging.getLogger(__name__)


class ClientApprovalService:

    @staticmethod
    def submit(db: Session, data: ClientApprovalCreate) -> ClientApproval:
        approval = ClientApproval(**data.model_dump())
        db.add(approval)
        db.commit()
        db.refresh(approval)

        logger.info("SUBMIT", "ClientApproval", approval.id, None)
        return approval

    @staticmethod
    def review(
        db: Session,
        approval_id: int,
        review: ClientApprovalUpdate,
        reviewer_id: int,
    ) -> Client:
        approval = db.query(ClientApproval).filter_by(id=approval_id).first()
        if not approval:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Approval request not found")

        if approval.status != approval.status.PENDING:
            raise HTTPException(status.HTTP_406_NOT_ACCEPTABLE, detail="Approval already reviewed")

        try:
            approval.status = review.status
            approval.rejection_reason = review.rejection_reason
            approval.reviewed_by_id = reviewer_id

            if review.status == review.status.APPROVED:
                client = Client(
                    type=approval.type,
                    first_name=approval.first_name,
                    last_name=approval.last_name,
                    username=approval.username,
                    phone=approval.phone,
                    email=approval.email,
                    password_hash=approval.password_hash,
                    pin_hash=approval.pin_hash,
                    id_type_id=approval.id_type_id,
                    id_number=approval.id_number,
                )

                db.add(client)
                db.flush()

                approval.client_id = client.id

                logger.info("APPROVE", "Client", client.id, reviewer_id)
            else:
                logger.info("REJECT", "ClientApproval", approval.id, reviewer_id)

            db.commit()
            return approval.client

        except IntegrityError:
            db.rollback()
            raise HTTPException(status.HTTP_406_NOT_ACCEPTABLE, detail="Client already exists or violates uniqueness")
