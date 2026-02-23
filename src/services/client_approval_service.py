# src/services/client_approval_service.py
from fastapi import HTTPException, status, UploadFile
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from src.models.clients import ClientApproval, Client, ClientStatus, ApprovalStatus
from src.models.role import Role
from src.schemas.clients import (
    ClientApprovalCreate,
    ClientApprovalUpdate,
)
from src.core.audit import audit_log
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
        from pathlib import Path
        import uuid

        def save_file(file: UploadFile, subdir: str) -> str:
            import os
            from pathlib import Path
            
            ext = file.filename.split(".")[-1]
            filename = f"{uuid.uuid4()}.{ext}"
            
            # Use absolute path
            BASE_DIR = "/app"
            uploads_dir = os.path.join(BASE_DIR, "uploads", "clients", subdir)
            
            # Create directory
            os.makedirs(uploads_dir, exist_ok=True)
            
            # Fix ownership if running as non-root
            try:
                os.chown(uploads_dir, 999, 999)  # UID 999 = appuser
            except:
                pass  # Ignore if we can't change ownership
            
            full_path = os.path.join(uploads_dir, filename)
            
            # Save file
            with open(full_path, "wb") as f:
                f.write(file.file.read())
            
            # Try to fix file ownership too
            try:
                os.chown(full_path, 999, 999)
            except:
                pass
            
            return f"uploads/clients/{subdir}/{filename}"
        
        approval = ClientApproval(
            **data,
            face_photo=save_file(files["face_photo"], "face"),
            id_photo_recto=save_file(files["id_photo_recto"], "id"),
            id_photo_verso=save_file(files["id_photo_verso"], "id"),
            badge_photo=(save_file(files["badge_photo"], "badge") if files.get("badge_photo") else None),
            magnetic_card_photo=(save_file(files["magnetic_card_photo"], "cards") if files.get("magnetic_card_photo") else None),
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
        approval = db.query(ClientApproval).filter_by(id=approval_id).first()
        if not approval:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Approval not found")

        if approval.status != ApprovalStatus.PENDING:
            raise HTTPException(status.HTTP_406_NOT_ACCEPTABLE, "Already reviewed")

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

            # Assign default role to client
            default_role = db.query(Role).filter(Role.name=="CLIENT_BASIC").first()
            if default_role:
                client.roles.append(default_role)
                
        db.commit()
        db.refresh(approval)  
        return approval
