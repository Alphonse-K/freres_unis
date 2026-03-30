# src/services/client_approval_service.py
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from src.models.clients import ClientApproval, Client, ClientStatus, ApprovalStatus
from src.schemas.clients import (
    ClientApprovalUpdate,
)
from src.core.audit import audit_log
from src.utils.file_upload import save_image
from datetime import datetime, timezone

import logging

logger = logging.getLogger(__name__)


class ClientApprovalService:

    @staticmethod
    def submit_with_files(db: Session, data: dict, files: dict) -> ClientApproval:
        """
        Save uploaded KYC files and create ClientApproval record.
        Passwords are NOT handled here.
        """
        
        approval = ClientApproval(
            **data,
            face_photo=save_image(files["face_photo"], "face"),
            id_photo_recto=save_image(files["id_photo_recto"], "id"),
            id_photo_verso=save_image(files["id_photo_verso"], "id"),
            badge_photo=(save_image(files["badge_photo"], "badge") if files.get("badge_photo") else None),
            magnetic_card_photo=(save_image(files["magnetic_card_photo"], "cards") if files.get("magnetic_card_photo") else None)
        )
        db.add(approval)
        db.commit()
        db.refresh(approval)
        return approval

    @staticmethod
    def review(
        db: Session,
        approval_id: int,
        review: ClientApprovalUpdate,
        reviewer_id: int,
    ) -> ClientApproval:
        
        approval = db.query(ClientApproval)\
                .filter_by(id=approval_id)\
                .first()
        
        if not approval:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, 
                detail="Approval not found"
            )

        if approval.status != ApprovalStatus.PENDING:
            raise HTTPException(
                status_code=status.HTTP_406_NOT_ACCEPTABLE, 
                detail="Already reviewed"
            )

        approval.status = review.status
        approval.rejection_reason = review.rejection_reason
        approval.reviewed_by_id = reviewer_id
        approval.reviewed_at = datetime.now(timezone.utc)

        if review.status == ApprovalStatus.APPROVED:
            client = Client(
                type=approval.type,
                first_name=approval.first_name,
                last_name=approval.last_name,
                phone=approval.phone,
                email=approval.email,
                id_type_id=approval.id_type_id,
                id_number=approval.id_number,
                status=ClientStatus.INACTIVE,
            )
            db.add(client)
            db.flush()
            approval.client_id = client.id

        audit_log("Approve client", "client", approval_id, reviewer_id)
        db.commit()
        db.refresh(approval)  
        return approval
