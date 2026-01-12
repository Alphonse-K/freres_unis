# src/services/api_key_service.py
from sqlalchemy.orm import Session
from datetime import datetime, timezone, timedelta
from src.models.security import APIKey
from src.core.api_keys import APIKeyUtils

class APIKeyService:

    @staticmethod
    def create_api_key(db: Session, user_id: int, permissions: list[str] = None, expires_days: int = 30) -> APIKey:
        key = APIKeyUtils.generate_key()
        secret = APIKeyUtils.generate_secret()
        hashed_secret = APIKeyUtils.hash_secret(secret)

        api_key_record = APIKey(
            user_id=user_id,
            key=key,
            secret=hashed_secret,
            permissions=permissions or [],
            expires_at=datetime.now(timezone.utc) + timedelta(days=expires_days)
        )
        db.add(api_key_record)
        db.commit()
        db.refresh(api_key_record)

        # Return plaintext secret for the client
        api_key_record.plain_secret = secret  # optional, not stored in DB
        return api_key_record

    @staticmethod
    def validate_api_key(db: Session, key: str, secret: str) -> APIKey | None:
        record = db.query(APIKey).filter(APIKey.key == key, APIKey.is_active == True).first()
        if not record:
            return None
        if record.expires_at and record.expires_at < datetime.now(timezone.utc):
            return None
        if not APIKeyUtils.verify_secret(secret, record.secret):
            return None
        record.last_used = datetime.now(timezone.utc)
        db.commit()
        return record
