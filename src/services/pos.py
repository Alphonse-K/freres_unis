from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from src.models.pos import POS, POSUser
from src.schemas.pos import POSCreate, POSUpdate, POSUserCreate, POSUserUpdate
from src.core.security import SecurityUtils
import logging

logger = logging.getLogger(__name__)

class POSService:

    # ------------------------
    # POS
    # ------------------------
    @staticmethod
    def create_pos(db: Session, data: POSCreate) -> POS:
        pos = POS(**data.model_dump())
        db.add(pos)
        db.commit()
        db.refresh(pos)

        logger.info("POS created", extra={"pos_id": pos.id})
        return pos

    @staticmethod
    def update_pos(db: Session, pos_id: int, data: POSUpdate) -> POS:
        pos = db.query(POS).filter(POS.id == pos_id).first()
        if not pos:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "POS not found")

        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(pos, field, value)

        db.commit()
        db.refresh(pos)

        logger.info("POS updated", extra={"pos_id": pos.id})
        return pos

    @staticmethod
    def get_pos(db: Session, pos_id: int) -> POS:
        pos = db.query(POS).filter(POS.id == pos_id).first()
        if not pos:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "POS not found")
        return pos


class POSUserService:

    @staticmethod
    def create_pos_user(
        db: Session,
        pos_id: int,
        data: POSUserCreate
    ) -> POSUser:

        if db.query(POSUser).filter(POSUser.username == data.username).first():
            raise HTTPException(status.HTTP_406_NOT_ACCEPTABLE, "POS user username already exists")

        user = POSUser(
            pos_id=pos_id,
            **data.model_dump(exclude={"password_hash", "pin_hash"}),
            password_hash=SecurityUtils.hash_password(data.password_hash),
            pin_hash=SecurityUtils.hash_password(data.pin_hash),
        )

        db.add(user)
        db.commit()
        db.refresh(user)

        logger.info(
            "POS user created",
            extra={"pos_id": pos_id, "pos_user_id": user.id}
        )

        return user

    @staticmethod
    def update_pos_user(
        db: Session,
        user_id: int,
        data: POSUserUpdate
    ) -> POSUser:

        user = db.query(POSUser).filter(POSUser.id == user_id).first()
        if not user:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "POS user not found")

        payload = data.model_dump(exclude_unset=True)

        if "password_hash" in payload:
            payload["password_hash"] = SecurityUtils.hash_password(payload["password_hash"])

        if "pin_hash" in payload:
            payload["pin_hash"] = SecurityUtils.hash_password(payload["pin_hash"])

        for field, value in payload.items():
            setattr(user, field, value)

        db.commit()
        db.refresh(user)

        logger.info(f"POS user updated", extra={"pos_user_id": str(user.id)})
        return user
