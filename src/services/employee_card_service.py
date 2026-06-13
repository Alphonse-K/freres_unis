# services/employee_card_service.py
import uuid
import qrcode
from datetime import datetime, timezone, timedelta
from fastapi import HTTPException
from sqlalchemy.orm import Session
from starlette import status

from src.core.security import generate_employee_card_token, verify_card_token, hash_token
from src.models.employee_card import EmployeeCard, EmployeeCardRequest, EmployeeCardScanLog
from src.models.employee import Employee
from src.schemas.employee_card import CardRequestCreate, CardRequestReject
from src.schemas.users import PaginationParams
from pathlib import Path
BASE_DIR = Path(__file__).resolve().parent.parent.parent
MEDIA_DIR = BASE_DIR / "media"


class EmployeeCardService:

    @staticmethod
    def create_request(db: Session, data: CardRequestCreate, created_by_id: int):
        employee = db.get(Employee, data.employee_id)
        if not employee:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Employee not found")

        # Block if pending request already exists
        existing = db.query(EmployeeCardRequest).filter_by(
            employee_id=data.employee_id,
            status="pending"
        ).first()
        if existing:
            return existing

        req = EmployeeCardRequest(
            employee_id=data.employee_id,
            reason=data.reason,
            created_by_id=created_by_id
        )
        db.add(req)
        db.commit()
        db.refresh(req)
        return req

    @staticmethod
    def approve_request(db: Session, request_id: int, reviewer_id: int):
        req = db.get(EmployeeCardRequest, request_id)
        if not req:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Request not found")

        # # Creator cannot approve their own request
        # if req.created_by_id == reviewer_id:
        #     raise HTTPException(
        #         status.HTTP_403_FORBIDDEN,
        #         detail="You cannot approve a request you created"
        #     )

        # Idempotency: already approved
        if req.status == "approved":
            existing_card = db.query(EmployeeCard).filter_by(
                employee_id=req.employee_id
            ).first()
            if existing_card:
                return existing_card

        elif req.status != "pending":
            raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Invalid request state")

        # Idempotency: active card already exists
        active_card = db.query(EmployeeCard).filter(
            EmployeeCard.employee_id == req.employee_id,
            EmployeeCard.is_active == True,
            EmployeeCard.expires_at > datetime.now(timezone.utc)
        ).first()
        if active_card:
            return active_card

        employee = db.get(Employee, req.employee_id)
        if not employee:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Employee not found")

        # Generate card
        card_id = uuid.uuid4()
        token = generate_employee_card_token(card_id, employee.id)
        token_hash = hash_token(token)

        qr_dir = MEDIA_DIR / "qrcodes" / "employees"
        qr_dir.mkdir(parents=True, exist_ok=True)
        qr_path = qr_dir / f"{card_id}.png"
        qrcode.make(token).save(str(qr_path))
        qr_public_path = f"/media/qrcodes/employees/{card_id}.png"

        card = EmployeeCard(
            id=card_id,
            employee_id=employee.id,
            card_number=getattr(employee, "registration_number", None) or str(employee.id),
            qr_token_hash=token_hash,
            qr_code_path=qr_public_path,
            expires_at=datetime.now(timezone.utc) + timedelta(days=365),
            created_by=reviewer_id
        )
        db.add(card)

        req.status = "approved"
        req.reviewed_at = datetime.now(timezone.utc)
        req.reviewed_by_id = reviewer_id

        db.commit()
        db.refresh(card)
        return card

    @staticmethod
    def reject_request(db: Session, request_id: int, reviewer_id: int, data: CardRequestReject):
        req = db.get(EmployeeCardRequest, request_id)
        if not req:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Request not found")

        # if req.created_by_id == reviewer_id:
        #     raise HTTPException(
        #         status.HTTP_403_FORBIDDEN,
        #         detail="You cannot reject a request you created"
        #     )

        if req.status == "rejected":
            return req

        if req.status != "pending":
            raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Invalid request state")

        req.status = "rejected"
        req.reviewed_at = datetime.now(timezone.utc)
        req.reviewed_by_id = reviewer_id
        req.rejection_reason = data.reason

        db.commit()
        db.refresh(req)
        return req

    @staticmethod
    def list_requests(db: Session, pagination: PaginationParams):
        query = db.query(EmployeeCardRequest).order_by(
            EmployeeCardRequest.requested_at.desc()
        )
        total = query.count()
        items = query.offset(pagination.offset).limit(pagination.page_size).all()
        return total, items

    @staticmethod
    def get_request(db: Session, request_id: int):
        req = db.get(EmployeeCardRequest, request_id)
        if not req:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Request not found")
        return req

    @staticmethod
    def get_employee_card(db: Session, employee_id: int):
        card = db.query(EmployeeCard).filter_by(employee_id=employee_id).first()
        if not card:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Card not found")
        return card

    @staticmethod
    def revoke_card(db: Session, card_id: uuid.UUID):
        card = db.get(EmployeeCard, card_id)
        if not card:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Card not found")

        card.is_active = False
        card.revoked_at = datetime.now(timezone.utc)

        db.commit()
        db.refresh(card)
        return card

    @staticmethod
    def scan_card(db: Session, token: str, agent_id: int, ip: str):
        try:
            payload = verify_card_token(token)
        except Exception:
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

        card = db.get(EmployeeCard, payload["sub"])
        if not card:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Card not found")

        if hash_token(token) != card.qr_token_hash:
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Token mismatch")

        if not card.is_active or card.revoked_at:
            raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Card inactive")

        if card.expires_at < datetime.now(timezone.utc):
            raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Card expired")

        log = EmployeeCardScanLog(
            card_id=card.id,
            employee_id=card.employee_id,
            scanned_by=agent_id,
            ip_address=ip,
            scanned_at=datetime.now(timezone.utc)
        )
        db.add(log)
        db.commit()
        return card.employee