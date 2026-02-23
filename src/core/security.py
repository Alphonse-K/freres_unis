# src/core/security.py
import secrets
import bcrypt
import hmac
import hashlib
from datetime import datetime, timezone, timedelta
from fastapi import HTTPException
from typing import Dict, Any, Optional
import uuid
from jose import JWTError, jwt
import base64
import enum
import logging
from sqlalchemy.orm import Session
from src.models.security import JWTBlacklist
from src.models.users import UserStatus
from src.core.config import settings


logger = logging.getLogger(__name__)


# Access JWT secret and expiry
SECRET_KEY = settings.SECRET_KEY
REFRESH_SECRET_KEY = settings.REFRESH_SECRET_KEY
ALGORITHM = settings.ALGORITHM

ACCESS_TOKEN_EXPIRE_MINUTES = settings.ACCESS_TOKEN_EXPIRE_MINUTES
REFRESH_TOKEN_EXPIRE_DAYS = settings.REFRESH_TOKEN_EXPIRE_DAYS
OTP_EXPIRE_MINUTES = settings.OTP_EXPIRE_MINUTES

# Account policies
MAX_FAIL = settings.MAX_FAIL
SUSP_MIN = settings.SUSP_MIN

API_KEY_LENGTH = settings.API_KEY_LENGTH
API_SECRET_LENGTH = settings.API_SECRET_LENGTH


class SecurityUtils:

    # ---------------- Password ----------------
    @staticmethod
    def hash_password(password: str) -> str:
        """
        SHA256 + bcrypt password hashing.
        Returns safe ASCII string (fits String(255))
        """
        sha = hashlib.sha256(password.encode("utf-8")).digest()
        hashed = bcrypt.hashpw(sha, bcrypt.gensalt())
        return hashed.decode()  # safe, bcrypt bytes are ASCII
    
        
    @staticmethod
    def verify_password(password: str, stored_hash: str) -> bool:
        
        # Try SHA256 + bcrypt first
        sha = hashlib.sha256(password.encode()).digest()
        
        try:
            if bcrypt.checkpw(sha, stored_hash.encode()):
                return True
        except Exception as e:
            print(f"DEBUG: SHA256+bcrypt check failed: {e}")
        
        # Try legacy bcrypt
        try:
            if bcrypt.checkpw(password.encode(), stored_hash.encode()):
                print("DEBUG: Legacy bcrypt verification successful")
                return True
        except Exception as e:
            print(f"DEBUG: Legacy bcrypt check failed: {e}")
        
        print("DEBUG: All password verification methods failed")
        return False    
    
    @staticmethod
    def validate_password_strength(password: str) -> tuple[bool, str]:
        if len(password) < 8: return False, "Password must be at least 8 characters"
        if len(password) > 128: return False, "Password cannot exceed 128 characters"
        if not any(c.isdigit() for c in password): return False, "Must contain a number"
        if not any(c.isupper() for c in password): return False, "Must contain uppercase"
        if not any(c.islower() for c in password): return False, "Must contain lowercase"

        return True, "Strong password"

    @staticmethod
    def validate_password_change(
        old_password: str,
        new_password: str,
        confirm_password: str,
        current_hashed_password: str
    ) -> tuple[bool, str]:
        """Validate password change request without performing DB updates"""
        # 1. Verify old password
        if not SecurityUtils.verify_password(old_password, current_hashed_password):
            return False, "Old password is incorrect"

        # 2. Confirm new password match
        if new_password != confirm_password:
            return False, "New passwords do not match"

        # 3. Prevent password reuse
        if old_password == new_password:
            return False, "New password must be different from old password"

        # 4. Validate strength
        is_strong, message = SecurityUtils.validate_password_strength(new_password)
        if not is_strong:
            return False, message

        return True, "Password change is valid"

    # ---------------- OTP ----------------
    @staticmethod
    def generate_otp() -> str:
        return ''.join(str(secrets.randbelow(10)) for _ in range(6))

    @staticmethod
    def get_otp_expiry(minutes: int = OTP_EXPIRE_MINUTES) -> datetime:
        return datetime.now(timezone.utc) + timedelta(minutes=minutes)

    @staticmethod
    def is_otp_expired(expires_at: datetime) -> bool:
        return datetime.now(timezone.utc) > expires_at

    # ---------------- JWT ----------------
    @staticmethod
    def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> tuple[str, datetime, str]:
        to_encode = data.copy()
        jti = str(uuid.uuid4())
        expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
        to_encode.update({"exp": expire, "iat": datetime.now(timezone.utc), "jti": jti, "type": "access"})
        token = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
        return token, expire, jti

    @staticmethod
    def create_refresh_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> tuple[str, datetime]:
        to_encode = data.copy()
        expire = datetime.now(timezone.utc) + (expires_delta or timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS))
        to_encode.update({"exp": expire, "iat": datetime.now(timezone.utc), "type": "refresh"})
        token = jwt.encode(to_encode, REFRESH_SECRET_KEY, algorithm=ALGORITHM)
        return token, expire

    @staticmethod
    def verify_access_token(token: str) -> Optional[Dict[str, Any]]:
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            if payload.get("type") != "access": return None
            return payload
        except JWTError:
            return None

    @staticmethod
    def verify_refresh_token(token: str) -> Optional[Dict[str, Any]]:
        try:
            payload = jwt.decode(token, REFRESH_SECRET_KEY, algorithms=[ALGORITHM])
            if payload.get("type") != "refresh": return None
            return payload
        except JWTError:
            return None

    # ---------------- Refresh Token Hash ----------------
    @staticmethod
    def hash_refresh_token(token: str) -> str:
        return SecurityUtils.hash_password(token)

    @staticmethod
    def verify_refresh_token_hash(plain_token: str, hashed_token: str) -> bool:
        return SecurityUtils.verify_password(plain_token, hashed_token)

    # ---------------- API Key ----------------
    @staticmethod
    def generate_api_key() -> str:
        return secrets.token_urlsafe(API_KEY_LENGTH)

    @staticmethod
    def generate_api_secret() -> str:
        return secrets.token_urlsafe(API_SECRET_LENGTH)

    @staticmethod
    def hash_api_secret(secret: str) -> str:
        return SecurityUtils.hash_password(secret)

    @staticmethod
    def verify_api_secret(plain_secret: str, hashed_secret: str) -> bool:
        return SecurityUtils.verify_password(plain_secret, hashed_secret)

    # ---------------- HMAC ----------------
    @staticmethod
    def generate_hmac_signature(secret: str, message: str) -> str:
        return hmac.new(secret.encode(), message.encode(), hashlib.sha256).hexdigest()

    @staticmethod
    def verify_hmac_signature(secret: str, message: str, signature: str) -> bool:
        return hmac.compare_digest(SecurityUtils.generate_hmac_signature(secret, message), signature)
    
    @staticmethod
    def enforce_login_policies(account) -> None:
        now = datetime.now(timezone.utc)

        # -----------------
        # Check active status
        # -----------------
        # User
        if hasattr(account, "status"):
            if isinstance(account.status, enum.Enum):
                if account.status.name.upper() != "ACTIVE" and account.status.value.upper() != "ACTIVE":
                    raise HTTPException(403, "Account not active")
            else:
                # fallback if status is a string
                if str(account.status).upper() != "ACTIVE":
                    raise HTTPException(403, "Account not active")

        # POSUser
        if hasattr(account, "is_active"):
            if not account.is_active:
                raise HTTPException(403, "Account not active")

        # Client
        if hasattr(account, "status") and isinstance(account.status, enum.Enum):
            if account.status.name not in ("APPROVED", "ACTIVE"):
                raise HTTPException(403, "Account not active")

        # -----------------
        # Check suspension
        # -----------------
        if hasattr(account, "suspended_until") and account.suspended_until:
            if now < account.suspended_until:
                remaining = int((account.suspended_until - now).total_seconds() / 60)
                raise HTTPException(
                    403,
                    f"Account suspended. Try again in {remaining} minutes."
                )
            # reset suspension
            account.suspended_until = None
            if hasattr(account, "failed_attempts"):
                account.failed_attempts = 0

        # -----------------
        # Check login time restrictions
        # -----------------
        if hasattr(account, "allowed_login_start") and hasattr(account, "allowed_login_end"):
            start = getattr(account, "allowed_login_start")
            end = getattr(account, "allowed_login_end")
            if start and end:
                current = now.time()
                if start <= end:
                    allowed = start <= current <= end
                else:
                    allowed = current >= start or current <= end

                if not allowed:
                    raise HTTPException(403, "Login not allowed at this time")

    @staticmethod
    def update_login_metadata(
        user,
        ip: str | None,
        user_agent: str | None,
        db: Session
    ) -> None:
        """
        Update security-related login metadata after a successful authentication.
        """

        now = datetime.now(timezone.utc)

        # Reset security counters
        user.failed_attempts = 0
        user.suspended_until = None

        # Login metadata
        user.last_login = now
        user.last_login_ip = ip
        user.last_login_user_agent = (
            user_agent[:255] if user_agent else None
        )

        try:
            db.add(user)
            db.commit()
            db.refresh(user)
        except Exception:
            db.rollback()
            logger.exception("Failed to update login metadata for user %s", user.id)
            raise

    # -------------- FAILED LOGIN HANDLING --------------
    @staticmethod
    def register_failed_attempt(account, db_session) -> None:
        """Increment failure count and suspend if threshold is exceeded."""
        if not hasattr(account, "failed_attempts"):
            return  # model does not track failures

        account.failed_attempts += 1

        if account.failed_attempts >= MAX_FAIL:  # reuse your existing constant
            account.suspended_until = datetime.now(timezone.utc) + timedelta(minutes=SUSP_MIN)
            logger.warning(f"Account suspended due to repeated failures: {account.username}")

        db_session.commit()

    @staticmethod
    def blacklist_token(db: Session, token: str, account_id: int, account_type: str, reason: str = "logout"):
        """
        Add the JWT to the blacklist so it cannot be used again.
        """
        from jose import jwt

        try:
            payload = jwt.get_unverified_claims(token)
            jti = payload.get("jti") or payload.get("sub")
            expires_at = datetime.fromtimestamp(payload["exp"], tz=timezone.utc)
        except Exception:
            raise HTTPException(400, "Invalid token")

        db.add(JWTBlacklist(
            account_id=account_id,
            account_type=account_type,
            token=token,
            jti=jti,
            expires_at=expires_at,
            reason=reason
        ))
        db.commit()