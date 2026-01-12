# src/core/jwt.py
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from typing import Optional
from jose import jwt
from src.models.security import JWTBlacklist
from src.core.security import SECRET_KEY, ALGORITHM

class JWTUtils:
    @staticmethod
    def decode_access_token(token: str) -> Optional[dict]:
        from jose import JWTError
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            if payload.get("type") != "access":
                return None
            return payload
        except JWTError:
            return None

    @staticmethod
    def is_blacklisted(db: Session, jti: str) -> bool:
        return db.query(JWTBlacklist).filter(JWTBlacklist.jti == jti).first() is not None
