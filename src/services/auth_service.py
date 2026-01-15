# src/services/auth_service.py
import logging
from sqlalchemy.orm import Session
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, Union
from fastapi import HTTPException, Request

from src.models.security import JWTBlacklist, RefreshToken, OTPCode, APIKey
from src.core.security import SecurityUtils
from src.models.users import User, UserStatus
from src.schemas.security import OTPVerify, APIKeyCreate
from src.schemas.users import UserCreate, PasswordLogin, PinLogin
from src.services.email_service import EmailService
from src.core.jwt import JWTUtils
from src.models.users import User
from src.models.pos import POSUser
from src.models.clients import Client


logger = logging.getLogger(__name__)

MAX_FAIL = 5
SUSP_MIN = 15

class AuthService:
    @staticmethod
    def authenticate(db: Session, identifier: str, secret: str, mode: str, ip: str, ua: str):
        try:
            # -------- PASSWORD AUTH --------
            if mode == "password":

                if "@" in identifier:
                    user = db.query(User).filter(User.email == identifier).first()
                    if user:
                        if SecurityUtils.verify_password(secret, user.password_hash):
                            SecurityUtils.enforce_login_policies(user)
                            # SecurityUtils.update_login_metadata(user, ip, ua, db)
                            return user

                        SecurityUtils.register_failed_attempt(user, db)
                    return None

                for model in (POSUser, Client):
                    account = db.query(model).filter(model.phone == identifier).first()
                    if account:
                        if SecurityUtils.verify_password(secret, account.password_hash):
                            SecurityUtils.enforce_login_policies(account)
                            SecurityUtils.update_login_metadata(account, ip, ua, db)
                            return account

                        SecurityUtils.register_failed_attempt(account, db)
                        return None

                return None

            # -------- PIN AUTH --------
            if mode == "pin":
                for model in (POSUser, Client):
                    account = db.query(model).filter(model.phone == identifier).first()
                    if account:
                        if SecurityUtils.verify_password(secret, account.pin_hash):
                            SecurityUtils.enforce_login_policies(account)
                            SecurityUtils.update_login_metadata(account, ip, ua, db)
                            return account

                        SecurityUtils.register_failed_attempt(account, db)
                        return None

                return None

            raise HTTPException(400, "Unsupported authentication mode")

        except HTTPException:
            raise

        except Exception:
            logger.exception("Authentication service error")
            raise HTTPException(500, "Authentication failure")

    @staticmethod
    def is_otp_required(user, current_ip: str, current_ua: str) -> bool:
        """
        OTP is required if:
            - First login ever
            - OR last login >= 24 hours ago
            - OR client IP address changed
            - OR device (user-agent) changed
        """
        
        # 1. First-time login
        if not user.last_login:
            return True

        # 2. Last login >= 24 hours
        now = datetime.now(timezone.utc)
        if now - user.last_login >= timedelta(hours=24):
            return True

        # 3. IP address changed
        if user.last_login_ip and user.last_login_ip != current_ip:
            return True

        # 4. Device (User-Agent) changed
        if user.last_login_user_agent and user.last_login_user_agent != current_ua:
            return True

        # Otherwise no OTP required
        return False

    @staticmethod
    def generate_otp(db: Session, user: User, otp_type: str = "login") -> str:
        from src.core.otp import OTPUtils
        code = OTPUtils.generate_otp()
        expires_at = OTPUtils.get_expiry()
        db.query(OTPCode).filter(OTPCode.user_id==user.id, OTPCode.purpose==otp_type, OTPCode.is_used==False).delete()
        otp_record = OTPCode(user_id=user.id, code=code, purpose=otp_type, expires_at=expires_at)
        db.add(otp_record)
        db.commit()
        try: EmailService.send_otp_email(user.email, user.username, code, otp_type)
        except Exception as e: logger.error(f"OTP email failed: {str(e)}")
        return code

    @staticmethod
    def verify_otp(db: Session, verify_data: OTPVerify, otp_type: str = "login") -> Optional[User]:
        otp_record = db.query(OTPCode).join(User).filter(
            User.email==verify_data.email,
            OTPCode.code==verify_data.otp_code,
            OTPCode.purpose==otp_type,
            OTPCode.is_used==False,
            OTPCode.expires_at > datetime.now(timezone.utc)
        ).first()
        if not otp_record: return None
        otp_record.is_used = True
        user = otp_record.user
        user.last_login = datetime.now(timezone.utc)
        db.commit()
        return user

    # ---------------- Token Management ----------------
    # @staticmethod
    # def create_tokens(db: Session, user: User, device_info: Dict[str, Any] = None) -> Dict[str, Any]:
    #     token_data = {"sub": str(user.id), "email": user.email, "role": user.role}
    #     access_token, expires_at, jti = SecurityUtils.create_access_token(token_data)
    #     refresh_token, refresh_expires_at = SecurityUtils.create_refresh_token(token_data)
    #     hashed_refresh = SecurityUtils.hash_refresh_token(refresh_token)
    #     refresh_record = RefreshToken(user_id=user.id, token=hashed_refresh, device_info=device_info, expires_at=refresh_expires_at)
    #     db.add(refresh_record)
    #     db.commit()
    #     return {"access_token": access_token, "refresh_token": refresh_token, "expires_at": expires_at, "jti": jti}

    @staticmethod
    def create_tokens(
        db: Session,
        account: Union[User, POSUser, Client],
        device_info: Dict[str, Any] = None
    ) -> Dict[str, Any]:

        # token payload
        token_data = {
            "sub": str(account.id),
            "role": getattr(account, "role", None),
            "type": account.__class__.__name__.lower(),  # "user", "posuser", "client"
        }

        access_token, expires_at, jti = SecurityUtils.create_access_token(token_data)
        refresh_token, refresh_expires_at = SecurityUtils.create_refresh_token(token_data)
        hashed_refresh = SecurityUtils.hash_refresh_token(refresh_token)

        # polymorphic refresh token
        refresh_record = RefreshToken(
            account_type=account.__class__.__name__.lower(),  # "user", "posuser", "client"
            account_id=account.id,
            token=hashed_refresh,
            device_info=device_info,
            expires_at=refresh_expires_at,
        )

        db.add(refresh_record)
        db.commit()
        db.refresh(refresh_record)

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "expires_at": expires_at,
            "jti": jti
        }

    @staticmethod
    def validate_access_token(db: Session, token: str) -> Optional[User]:
        payload = JWTUtils.decode_access_token(token)
        if not payload: return None
        if JWTUtils.is_blacklisted(db, payload.get("jti")): return None
        user_id = payload.get("sub")
        if not user_id: return None
        return db.query(User).filter(User.id==int(user_id)).first()

    @staticmethod
    def validate_api_key(db: Session, api_key: str, api_secret: str) -> Optional[APIKey]:
        key_record = db.query(APIKey).filter(APIKey.key==api_key, APIKey.is_active==True).first()
        if not key_record: return None
        if key_record.expires_at and key_record.expires_at < datetime.now(timezone.utc): return None
        if not SecurityUtils.verify_api_secret(api_secret, key_record.secret): return None
        key_record.last_used = datetime.now(timezone.utc)
        db.commit()
        return key_record
    
    @staticmethod
    def refresh_tokens(db: Session, refresh_token: str, device_info: Dict[str, Any] = None) -> Optional[Dict[str, Any]]:
        """
        Refresh access token using a hashed refresh token.
        Invalidates old refresh token and returns new tokens.
        """
        # Verify JWT refresh token
        payload = SecurityUtils.verify_refresh_token(refresh_token)
        if not payload or "sub" not in payload:
            return None

        user_id = payload["sub"]

        # Find all active, non-expired refresh tokens for this user
        now = datetime.now(timezone.utc)
        tokens = db.query(RefreshToken).filter(
            RefreshToken.user_id == user_id,
            RefreshToken.is_active == True,
            RefreshToken.expires_at > now
        ).all()

        # Match the provided token against stored hashed tokens
        token_record = None
        for t in tokens:
            if SecurityUtils.verify_refresh_token_hash(refresh_token, t.token):
                token_record = t
                break

        if not token_record:
            return None

        # Fetch user
        user = db.query(User).filter(User.id == user_id, str(User.status) == UserStatus.ACTIVE).first()
        if not user:
            return None

        # Invalidate old refresh token
        token_record.is_active = False
        db.commit()

        # Create new access + refresh tokens
        return AuthService.create_tokens(db, user, device_info)

    @staticmethod
    def change_password(
        db: Session,
        user_id: int,
        old_password: str,
        new_password: str,
        confirm_password: str,
        ip_address: str = ""
    ) -> bool:
        """
        Change user password with validation and notification.
        """
        user = db.query(User).filter(
            User.id == user_id,
        ).first()

        if not user:
            return False

        # Validate password change request
        is_valid, message = SecurityUtils.validate_password_change(
            old_password,
            new_password,
            confirm_password,
            user.password_hash
        )

        if not is_valid:
            raise HTTPException(status_code=403, detail=message)

        # Update password hash
        user.password_hash = SecurityUtils.hash_password(new_password)

        # Optional: update last login security context
        user.last_login = datetime.now(timezone.utc)
        if ip_address:
            user.last_login_ip = ip_address

        db.commit()

        # Send notification email
        try:
            EmailService.send_password_change_notification(
                to_email=user.email,
                name=user.username,
                ip=ip_address
            )
        except Exception as e:
            logger.warning(f"Password change email failed for {user.email}: {str(e)}")

        return True


    # -------------- SUCCESSFUL LOGIN METADATA --------------
    @staticmethod
    def update_login_metadata(account: User, ip: str, user_agent: str, db_session) -> None:
        """Update last login fields and reset failure counter."""
        if hasattr(account, "last_login"):
            account.last_login = datetime.now(timezone.utc)
        if hasattr(account, "last_login_ip"):
            account.last_login_ip = ip
        if hasattr(account, "last_login_user_agent"):
            account.last_login_user_agent = user_agent
        if hasattr(account, "failed_attempts"):
            account.failed_attempts = 0
        if hasattr(account, "suspended_until"):
            account.suspended_until = None  # clear suspension after success

        db_session.commit()

    @staticmethod
    def logout_user(db: Session, account, access_token: str):
        """
        Logout current device by blacklisting the access token
        and deactivating the matching refresh token.
        """
        account_type = account.__class__.__name__.lower()  # user / client / posuser

        # Blacklist access token
        SecurityUtils.blacklist_token(db, access_token, account.id, account_type)

        # Deactivate refresh tokens for this device if you track device_info
        # For now, deactivate all active refresh tokens for simplicity
        db.query(RefreshToken).filter(
            RefreshToken.user_id == account.id,
            RefreshToken.is_active == True
        ).update({"is_active": False})
        db.commit()

    @staticmethod
    def logout_all_devices(db: Session, account, access_token: str):
        """
        Logout from all devices by blacklisting access token and deactivating all refresh tokens.
        """
        account_type = account.__class__.__name__.lower()  # user / client / posuser

        SecurityUtils.blacklist_token(db, access_token, account.id, account_type)

        db.query(RefreshToken).filter(
            RefreshToken.user_id == account.id,
            RefreshToken.is_active == True
        ).update({"is_active": False})

        db.commit()

    # ==================== API KEY MANAGEMENT ====================
    @staticmethod
    def create_api_key(db: Session, company_id: int, create_data: APIKeyCreate) -> dict:
        """
        Create API key for a company.
        Returns key and secret (secret only shown once).
        """
        # Generate keys
        api_key = SecurityUtils.generate_api_key()
        api_secret = SecurityUtils.generate_api_secret()
        hashed_secret = SecurityUtils.hash_api_secret(api_secret)
        
        # Store API key
        api_key_record = APIKey(
            company_id=company_id,
            name=create_data.name,
            key=api_key,
            secret=hashed_secret,
            permissions=create_data.permissions,
            expires_at=create_data.expires_at
        )
        
        db.add(api_key_record)
        db.commit()
        db.refresh(api_key_record)
        
        # Return with secret (only shown once)
        return {
            "id": api_key_record.id,
            "name": api_key_record.name,
            "key": api_key,
            "secret": api_secret,
            "permissions": create_data.permissions,
            "expires_at": create_data.expires_at,
            "created_at": api_key_record.created_at
        }
    
    @staticmethod
    def validate_api_key(db: Session, api_key: str, api_secret: str) -> Optional[APIKey]:
        """
        Validate API key and secret.
        Updates last used timestamp.
        """
        key_record = db.query(APIKey).filter(
            APIKey.key == api_key,
            APIKey.is_active == True
        ).first()
        
        if not key_record:
            return None
        
        # Check expiration
        if key_record.expires_at and key_record.expires_at < datetime.now(timezone.utc):
            return None
        
        # Verify secret
        if not SecurityUtils.verify_api_secret(api_secret, key_record.secret):
            return None
        
        # Update last used
        key_record.last_used = datetime.now(timezone.utc)
        db.commit()
        
        return key_record
    
    @staticmethod
    def get_company_api_keys(db: Session, company_id: int) -> list[dict]:
        """List all keys for a company (hide secrets)."""
        keys = db.query(APIKey).filter(APIKey.company_id == company_id).all()
        return [
            {
                "id": k.id,
                "key": k.key,
                "name": k.name,
                "permissions": k.permissions,
                "expires_at": k.expires_at,
                "is_active": k.is_active,
                "last_used": k.last_used,
                "created_at": k.created_at
            }
            for k in keys
        ]    
    
    @staticmethod
    def revoke_api_key(db: Session, key_id: int, company_id: int) -> bool:
        """Revoke an API key"""
        key = db.query(APIKey).filter(
            APIKey.id == key_id,
            APIKey.company_id == company_id
        ).first()
        
        if key:
            key.is_active = False
            db.commit()
            return True
        
        return False


