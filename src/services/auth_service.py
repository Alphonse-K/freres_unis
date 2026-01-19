# src/services/auth_service.py
import logging
from sqlalchemy.orm import Session
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, Union
from fastapi import HTTPException, Request
import bcrypt

from src.models.security import JWTBlacklist, RefreshToken, OTPCode, APIKey
from src.core.security import SecurityUtils
from src.models.users import User, UserStatus
from src.schemas.security import OTPVerify, APIKeyCreate
from src.schemas.users import UserCreate, PasswordLogin, PinLogin
from src.models.audit import AuditLog
from src.services.audit_service import AuditService
from src.services.otp_service import OTPService
from src.core.otp import OTPUtils
from src.services.email_service import EmailService
from src.core.jwt import JWTUtils
from src.models.users import User
from src.models.pos import POSUser
from src.models.clients import Client
import sqlalchemy

logger = logging.getLogger(__name__)

MAX_FAIL = 5
SUSP_MIN = 15

class AuthService:
    @staticmethod
    def authenticate(db: Session, identifier: str, secret: str, mode: str, ip: str, ua: str):
        try:
            print(f"DEBUG authenticate: identifier='{identifier}', mode='{mode}'")
            
            # -------- PASSWORD AUTH --------
            if mode == "password":
                # Try email login first
                if "@" in identifier:
                    print(f"DEBUG: Attempting email login for '{identifier}'")
                    
                    # Case-insensitive lookup
                    user = db.query(User).filter(User.email.ilike(identifier)).first()
                    print(f"DEBUG: User query result: {user}")
                    
                    if not user:
                        print(f"DEBUG: No user found with email '{identifier}'")
                        return None
                        
                    print(f"DEBUG: User found - ID: {user.id}, Email: {user.email}")
                    print(f"DEBUG: Password hash exists: {bool(user.password_hash)}")
                    
                    if not user.password_hash:
                        print("DEBUG: User has no password hash")
                        return None

                    # DEBUG password verification
                    print(f"DEBUG: Attempting password verification")
                    is_valid = SecurityUtils.verify_password(secret, user.password_hash)
                    print(f"DEBUG: Password verification result: {is_valid}")
                    
                    if not is_valid:
                        print(f"DEBUG: Password verification failed")
                        SecurityUtils.register_failed_attempt(user, db)
                        return None

                    print(f"DEBUG: Password verified successfully")
                    
                    # Auto-upgrade legacy bcrypt
                    try:
                        if bcrypt.checkpw(secret.encode(), user.password_hash.encode()):
                            print("DEBUG: Upgrading legacy password hash")
                            user.password_hash = SecurityUtils.hash_password(secret)
                            db.commit()
                    except Exception as e:
                        print(f"DEBUG: Legacy upgrade check failed: {e}")

                    # FIX: Safe call to SecurityUtils methods
                    try:
                        # Enforce policies
                        SecurityUtils.enforce_login_policies(user)
                        
                        # Update metadata
                        SecurityUtils.update_login_metadata(user, ip, ua, db)
                    except sqlalchemy.exc.ArgumentError as e:
                        # Handle boolean comparison error
                        print(f"WARNING: Fix needed in SecurityUtils methods: {e}")
                        # Basic metadata update
                        user.last_login = datetime.now(timezone.utc)
                        user.last_login_ip = ip
                        user.last_login_user_agent = ua
                        user.failed_login_attempts = 0  # Reset on success
                        db.commit()
                    
                    print(f"DEBUG: Authentication successful for user {user.id}")
                    return user

                print(f"DEBUG: '@' not in identifier, trying phone login...")
                
                # ---- POSUser / Client login (phone + password) ----
                for model in (POSUser, Client):
                    account = db.query(model).filter(model.phone == identifier).first()
                    if not account or not getattr(account, "password_hash", None):
                        continue

                    if not SecurityUtils.verify_password(secret, account.password_hash):
                        SecurityUtils.register_failed_attempt(account, db)
                        return None

                    # Auto-upgrade legacy bcrypt(password) → SHA256+bcrypt
                    try:
                        if bcrypt.checkpw(secret.encode(), account.password_hash.encode()):
                            account.password_hash = SecurityUtils.hash_password(secret)
                            db.commit()
                    except Exception:
                        pass

                    # FIX: Safe call for phone users
                    try:
                        SecurityUtils.enforce_login_policies(account)
                        SecurityUtils.update_login_metadata(account, ip, ua, db)
                    except sqlalchemy.exc.ArgumentError:
                        # Basic metadata update
                        account.last_login = datetime.now(timezone.utc)
                        account.last_login_ip = ip
                        account.last_login_user_agent = ua
                        account.failed_login_attempts = 0
                        db.commit()
                    
                    return account

                return None

            # -------- PIN AUTH --------
            if mode == "pin":
                print(f"DEBUG: Attempting PIN login for phone '{identifier}'")
                
                for model in (POSUser, Client):
                    account = db.query(model).filter(model.phone == identifier).first()
                    if not account:
                        continue
                        
                    print(f"DEBUG: Found {model.__name__} account: {account.id}")
                    print(f"DEBUG: PIN hash exists: {bool(getattr(account, 'pin_hash', None))}")
                    
                    if not getattr(account, "pin_hash", None):
                        print(f"DEBUG: No PIN hash for account")
                        continue

                    if not SecurityUtils.verify_password(secret, account.pin_hash):
                        print(f"DEBUG: PIN verification failed")
                        SecurityUtils.register_failed_attempt(account, db)
                        return None

                    print(f"DEBUG: PIN verified successfully")
                    
                    # Auto-upgrade legacy bcrypt PIN
                    try:
                        if bcrypt.checkpw(secret.encode(), account.pin_hash.encode()):
                            print("DEBUG: Upgrading legacy PIN hash")
                            account.pin_hash = SecurityUtils.hash_password(secret)
                            db.commit()
                    except Exception:
                        pass

                    # FIX: Safe call for PIN login
                    try:
                        SecurityUtils.enforce_login_policies(account)
                        SecurityUtils.update_login_metadata(account, ip, ua, db)
                    except sqlalchemy.exc.ArgumentError:
                        # Basic metadata update
                        account.last_login = datetime.now(timezone.utc)
                        account.last_login_ip = ip
                        account.last_login_user_agent = ua
                        account.failed_login_attempts = 0
                        db.commit()
                    
                    print(f"DEBUG: PIN authentication successful for {model.__name__} {account.id}")
                    return account

                print(f"DEBUG: No account found with phone '{identifier}' for PIN login")
                return None

            raise HTTPException(400, "Unsupported authentication mode")

        except HTTPException:
            raise

        except sqlalchemy.exc.ArgumentError as e:
            # Catch the specific boolean comparison error
            logger.error(f"SQLAlchemy argument error: {e}")
            print(f"ERROR: Fix SecurityUtils methods - replace .ilike() with == for booleans")
            raise HTTPException(500, "Authentication configuration error")
            
        except Exception as e:
            logger.exception("Authentication service error")
            print(f"ERROR: Authentication failed: {str(e)}")
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

    # @staticmethod
    # def generate_otp(db: Session, user: User, otp_type: str = "login") -> str:
    #     from src.core.otp import OTPUtils
    #     code = OTPUtils.generate_otp()
    #     expires_at = OTPUtils.get_expiry()
    #     db.query(OTPCode).filter(OTPCode.user_id==user.id, OTPCode.purpose==otp_type, OTPCode.is_used==False).delete()
    #     otp_record = OTPCode(user_id=user.id, code=code, purpose=otp_type, expires_at=expires_at)
    #     db.add(otp_record)
    #     db.commit()
    #     try: EmailService.send_otp_email(user.email, user.username, code, otp_type)
    #     except Exception as e: logger.error(f"OTP email failed: {str(e)}")
    #     return code

    # @staticmethod
    # def verify_otp(db: Session, verify_data: OTPVerify, otp_type: str = "login") -> Optional[User]:
    #     otp_record = db.query(OTPCode).join(User).filter(
    #         User.email==verify_data.email,
    #         OTPCode.code==verify_data.otp_code,
    #         OTPCode.purpose==otp_type,
    #         OTPCode.is_used==False,
    #         OTPCode.expires_at > datetime.now(timezone.utc)
    #     ).first()
    #     if not otp_record: return None
    #     otp_record.is_used = True
    #     user = otp_record.user
    #     user.last_login = datetime.now(timezone.utc)
    #     db.commit()
    #     return user
    @staticmethod
    def generate_otp(
        db: Session,
        account,  # User or POSUser instance
        purpose: str = "login"
    ) -> str:
        """
        Generate OTP for User OR POSUser
        Now uses polymorphic OTPCode table
        """
        
        # Determine account type
        if isinstance(account, User):
            account_type = "user"
            email = account.email
            name = account.username
            account_id = account.id
        elif isinstance(account, POSUser):
            account_type = "pos"
            email = account.email
            name = getattr(account, "name", "User")
            account_id = account.id
        else:
            raise ValueError(f"Unsupported account type: {type(account)}")
        
        # Delete old unused OTPs
        # FIXED: Using correct column names for polymorphic table
        db.query(OTPCode).filter(
            OTPCode.account_type == account_type,
            OTPCode.account_id == account_id,
            OTPCode.purpose == purpose,
            OTPCode.is_used == False
        ).delete()
        
        # Generate OTP
        code = OTPUtils.generate_otp()
        expires_at = OTPUtils.get_expiry()
        
        # Save OTP with polymorphic fields
        otp_record = OTPCode(
            account_type=account_type,
            account_id=account_id,
            code=code,
            purpose=purpose,
            expires_at=expires_at,
            # # Keep user_id for backward compatibility (nullable)
            # user_id=account_id if account_type == "user" else None
        )
        db.add(otp_record)
        db.commit()
        
        # Send email
        try:
            EmailService.send_otp_email(email, name, code, purpose)
        except Exception as e:
            logger.error(f"Failed to send OTP email: {str(e)}")
        
        return code
    
    @staticmethod
    def verify_otp(
        db: Session,
        email: str,
        code: str,
        purpose: str = "login"
    ):
        """
        Verify OTP for User OR POSUser
        Supports both old and new OTP records
        """
        email = email.strip().lower()
        
        # First try User
        user = db.query(User).filter(User.email == email).first()
        if user:
            # Try to find OTP with polymorphic fields first
            otp_record = db.query(OTPCode).filter(
                OTPCode.account_type == "user",
                OTPCode.account_id == user.id,
                OTPCode.code == code,
                OTPCode.purpose == purpose,
                OTPCode.is_used == False,
                OTPCode.expires_at > datetime.now(timezone.utc)
            ).first()
            
            # If not found, try with old user_id field (backward compatibility)
            if not otp_record:
                otp_record = db.query(OTPCode).filter(
                    OTPCode.user_id == user.id,  # Old field
                    OTPCode.code == code,
                    OTPCode.purpose == purpose,
                    OTPCode.is_used == False,
                    OTPCode.expires_at > datetime.now(timezone.utc)
                ).first()
                
                # If found with old format, update to new format
                if otp_record:
                    otp_record.account_type = "user"
                    otp_record.account_id = user.id
            
            if otp_record:
                otp_record.is_used = True
                otp_record.used_at = datetime.now(timezone.utc)
                user.last_login = datetime.now(timezone.utc)
                db.commit()
                return user
        
        # Try POSUser (only new format, POSUser didn't exist before)
        pos_user = db.query(POSUser).filter(POSUser.email == email).first()
        if pos_user:
            otp_record = db.query(OTPCode).filter(
                OTPCode.account_type == "pos",
                OTPCode.account_id == pos_user.id,
                OTPCode.code == code,
                OTPCode.purpose == purpose,
                OTPCode.is_used == False,
                OTPCode.expires_at > datetime.now(timezone.utc)
            ).first()
            
            if otp_record:
                otp_record.is_used = True
                otp_record.used_at = datetime.now(timezone.utc)
                pos_user.last_login = datetime.now(timezone.utc)
                db.commit()
                return pos_user
        
        return None    


    @staticmethod
    def create_tokens(
        db: Session,
        account: Union[User, POSUser, Client],
        device_info: Dict[str, Any] = None
    ) -> Dict[str, Any]:

        # Map model → account_type
        if isinstance(account, User):
            account_type = "user"
        elif isinstance(account, POSUser):
            account_type = "pos"
        elif isinstance(account, Client):
            account_type = "client"
        else:
            raise ValueError("Unknown account type")

        token_data = {
            "sub": str(account.id),
            "account_type": account_type,
            "role": getattr(account, "role", None),
            "token_type": "access",
        }

        access_token, access_expires_at, jti = SecurityUtils.create_access_token(token_data)
        refresh_token, refresh_expires_at = SecurityUtils.create_refresh_token(token_data)

        hashed_refresh = SecurityUtils.hash_refresh_token(refresh_token)

        refresh_record = RefreshToken(
            account_type=account_type,
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
            "access_expires_at": access_expires_at,
            "refresh_expires_at": refresh_expires_at,
            "jti": jti,
        }

    @staticmethod
    def validate_access_token(db: Session, token: str) -> Optional[dict]:
        payload = JWTUtils.decode_access_token(token)
        if not payload:
            return None

        # blacklist check
        jti = payload.get("jti")
        if jti and JWTUtils.is_blacklisted(db, jti):
            return None

        account_type = payload.get("account_type")
        account_id = payload.get("sub")

        if not account_type or not account_id:
            return None

        model_map = {
            "user": User,
            "pos": POSUser,
            "client": Client,
        }

        model = model_map.get(account_type)
        if not model:
            return None

        account = db.query(model).filter(model.id == int(account_id)).first()
        if not account:
            return None

        return {
            "account_type": account_type,
            "account": account,
            "payload": payload,  # optional but useful
        }

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
    def refresh_tokens(
        db: Session,
        refresh_token: str,
        device_info: Dict[str, Any] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Refresh access token using a hashed refresh token.
        Invalidates old refresh token and returns new tokens.
        Supports User, POSUser, and Client accounts.
        """
        # Verify JWT refresh token
        payload = SecurityUtils.verify_refresh_token(refresh_token)
        if not payload or "sub" not in payload or "account_type" not in payload:
            return None

        account_id = payload["sub"]
        account_type = payload["account_type"]  # 'user', 'pos', or 'client'

        # Find all active, non-expired refresh tokens for this account
        now = datetime.now(timezone.utc)
        tokens = db.query(RefreshToken).filter(
            RefreshToken.account_type == account_type,
            RefreshToken.account_id == account_id,
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

        # Fetch account depending on type
        account_model = {
            "user": User,
            "pos": POSUser,
            "client": Client
        }.get(account_type)

        if not account_model:
            return None

        account = db.query(account_model).filter(account_model.id == account_id).first()
        if not account:
            return None

        # Invalidate old refresh token
        token_record.is_active = False
        db.commit()

        # Create new access + refresh tokens
        return AuthService.create_tokens(db, account, device_info)

    @staticmethod
    def change_password(
        db: Session,
        account_type: str,
        account_id: int,
        old_password: str,
        new_password: str,
        confirm_password: str,
        ip_address: str = "",
    ) -> bool:
        """Change password for any account type"""
        
        print(f"=== CHANGE PASSWORD ===")
        print(f"Account type: {account_type}, Account ID: {account_id}")
        
        # Basic validation
        if new_password != confirm_password:
            print("DEBUG: New passwords don't match")
            return False
        
        if len(new_password) < 8:
            print("DEBUG: Password must be at least 8 characters")
            return False
        
        # Map account type to model
        model_map = {
            "user": User,
            "pos": POSUser,
            "client": Client,
        }
        
        account_model = model_map.get(account_type)
        if not account_model:
            print(f"DEBUG: Invalid account type: {account_type}")
            return False
        
        # Get account
        account = db.query(account_model).filter(account_model.id == account_id).first()
        if not account:
            print(f"DEBUG: Account not found")
            return False
        
        # Check if account has password_hash
        if not hasattr(account, "password_hash"):
            print(f"DEBUG: Account type {account_type} doesn't support password authentication")
            return False
        
        current_hash = account.password_hash
        if not current_hash:
            print(f"DEBUG: No password set for this account")
            # Allow setting password for the first time
            if old_password:
                print(f"DEBUG: Old password provided but no password set")
                return False
        
        # Verify old password (skip if first-time setup)
        if current_hash:
            print(f"DEBUG: Verifying old password...")
            if not SecurityUtils.verify_password(old_password, current_hash):
                print(f"DEBUG: Old password verification failed")
                return False
            print(f"DEBUG: Old password verified")
        
        # Set new password
        account.password_hash = SecurityUtils.hash_password(new_password)
        
        # Update metadata
        if hasattr(account, "last_password_change"):
            account.last_password_change = datetime.now(timezone.utc)
        
        if hasattr(account, "require_password_change"):
            account.require_password_change = False
        
        db.commit()
        print(f"DEBUG: Password changed successfully")
        return True


    @staticmethod
    def change_pin(
        db: Session,
        account_type: str,
        account_id: int,
        old_pin: str,
        new_pin: str,
        confirm_pin: str,
        ip_address: str = "",
    ) -> bool:
        """Change PIN for POS users and clients only"""
        
        print(f"=== CHANGE PIN ===")
        print(f"Account type: {account_type}, Account ID: {account_id}")
        
        # Only allow PIN changes for pos and client accounts
        if account_type not in ["pos", "client"]:
            print(f"DEBUG: PIN change not allowed for account type: {account_type}")
            return False
        
        # Basic validation
        if new_pin != confirm_pin:
            print("DEBUG: New PINs don't match")
            return False
        
        # PIN-specific validation
        if not new_pin.isdigit():
            print("DEBUG: PIN must contain only digits")
            return False
        
        if len(new_pin) not in [4, 6]:
            print("DEBUG: PIN must be 4 or 6 digits")
            return False
        
        # Map account type to model
        model_map = {
            "pos": POSUser,
            "client": Client,
        }
        
        account_model = model_map.get(account_type)
        if not account_model:
            print(f"DEBUG: Invalid account type for PIN change: {account_type}")
            return False
        
        # Get account
        account = db.query(account_model).filter(account_model.id == account_id).first()
        if not account:
            print(f"DEBUG: Account not found")
            return False
        
        # Check if account has pin_hash
        if not hasattr(account, "pin_hash"):
            print(f"DEBUG: Account type {account_type} doesn't support PIN authentication")
            return False
        
        current_pin_hash = account.pin_hash
        if not current_pin_hash:
            print(f"DEBUG: No PIN set for this account")
            # Allow setting PIN for the first time
            if old_pin:
                print(f"DEBUG: Old PIN provided but no PIN set")
                return False
        
        # Verify old PIN (skip if first-time setup)
        if current_pin_hash:
            print(f"DEBUG: Verifying old PIN...")
            if not SecurityUtils.verify_password(old_pin, current_pin_hash):
                print(f"DEBUG: Old PIN verification failed")
                return False
            print(f"DEBUG: Old PIN verified")
        
        # Set new PIN
        account.pin_hash = SecurityUtils.hash_password(new_pin)
        
        # Update metadata
        if hasattr(account, "last_pin_change"):
            account.last_pin_change = datetime.now(timezone.utc)
        
        db.commit()
        print(f"DEBUG: PIN changed successfully")
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
            RefreshToken.account_id == account.id,
            RefreshToken.is_active == True
        ).update({"is_active": False})
        db.commit()

    @staticmethod
    def logout_all_devices(db: Session, account, access_token: str = None):
        """
        Logout from all devices by blacklisting access token and deactivating all refresh tokens.
        """
        account_type = account.__class__.__name__.lower()  # user / client / posuser

        SecurityUtils.blacklist_token(db, access_token, account.id, account_type)

        db.query(RefreshToken).filter(
            RefreshToken.account_id == account.id,
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

    
    @staticmethod
    def admin_set_password(
        db: Session,
        client_id: int,
        new_password: str,
        admin_id: int,
        ip_address: str = "",
        user_agent: str = None,
        notes: str = "",
    ) -> tuple[bool, str]:
        """Admin sets password for a client (returns success, message)"""
        
        try:
            # Get client
            client = db.query(Client).filter(Client.id == client_id).first()
            if not client:
                return False, "Client not found"
            
            # Password validation
            if len(new_password) < 8:
                return False, "Password must be at least 8 characters"
            
            # Track if this is initial setup or reset
            is_initial_setup = not client.password_hash
            
            # Set password
            client.password_hash = SecurityUtils.hash_password(new_password)
            
            # Update timestamps
            client.updated_at = datetime.now(timezone.utc)
            if hasattr(client, 'last_password_change'):
                client.last_password_change = datetime.now(timezone.utc)
            
            # Log to audit
            AuditService.log_action(
                db=db,
                actor_type='admin',
                actor_id=admin_id,
                target_type='client',
                target_id=client_id,
                action='set_password',
                details={
                    'is_initial_setup': is_initial_setup,
                    'password_changed_by_admin': True,
                    'notes': notes,
                    'client_phone': client.phone,
                    'has_email': bool(client.email)
                },
                ip_address=ip_address,
                user_agent=user_agent,
            )
            
            db.commit()
            
            # Send notification if client has phone
            if client.phone:
                # SMSService.send_password_set_notification(client.phone, is_initial_setup)
                pass
            
            return True, "Password set successfully"
            
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to set client password: {str(e)}")
            return False, "Internal server error"
    
    @staticmethod
    def admin_reset_password(
        db: Session,
        client_id: int,
        admin_id: int,
        ip_address: str = "",
        user_agent: str = None,
        generate_random: bool = True,
        new_password: str = None,
    ) -> tuple[bool, str, Optional[str]]:
        """Admin resets client password (can generate random or use provided)"""
        
        try:
            client = db.query(Client).filter(Client.id == client_id).first()
            if not client:
                return False, "Client not found", None
            
            # Generate or use provided password
            if generate_random:
                import secrets
                import string
                alphabet = string.ascii_letters + string.digits + "!@#$%"
                new_password = ''.join(secrets.choice(alphabet) for _ in range(12))
            
            elif not new_password or len(new_password) < 8:
                return False, "Password must be at least 8 characters", None
            
            # Set password
            client.password_hash = SecurityUtils.hash_password(new_password)
            
            # Log to audit
            AuditService.log_action(
                db=db,
                actor_type='admin',
                actor_id=admin_id,
                target_type='client',
                target_id=client_id,
                action='reset_password',
                details={
                    'password_generated': generate_random,
                    'reset_by_admin': True,
                    'client_phone': client.phone,
                },
                ip_address=ip_address,
                user_agent=user_agent,
            )
            
            db.commit()
            
            return True, "Password reset successfully", new_password if generate_random else None
            
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to reset client password: {str(e)}")
            return False, "Internal server error", None
    
    @staticmethod
    def admin_set_pin(
        db: Session,
        client_id: int,
        new_pin: str,
        admin_id: int,
        ip_address: str = "",
        user_agent: str = None,
        notes: str = "",
    ) -> tuple[bool, str]:
        """Admin sets PIN for a client"""
        
        try:
            client = db.query(Client).filter(Client.id == client_id).first()
            if not client:
                return False, "Client not found"
            
            # PIN validation
            if not new_pin.isdigit():
                return False, "PIN must contain only digits"
            
            if len(new_pin) not in [4, 4]:
                return False, "PIN must be 4 digits"
            
            is_initial_setup = not getattr(client, 'pin_hash', None)
            
            # Set PIN
            client.pin_hash = SecurityUtils.hash_password(new_pin)
            
            # Log to audit
            AuditService.log_action(
                db=db,
                actor_type='admin',
                actor_id=admin_id,
                target_type='client',
                target_id=client_id,
                action='set_pin',
                details={
                    'is_initial_setup': is_initial_setup,
                    'pin_length': len(new_pin),
                    'notes': notes,
                    'client_phone': client.phone,
                },
                ip_address=ip_address,
                user_agent=user_agent,
            )
            
            db.commit()
            
            return True, "PIN set successfully"
            
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to set client PIN: {str(e)}")
            return False, "Internal server error"
    
    @staticmethod
    def client_self_reset_password(
        db: Session,
        identifier: str,  # phone or email
        otp: str,
        new_password: str,
        confirm_password: str,
        ip_address: str = "",
        user_agent: str = None,
    ) -> tuple[bool, str]:
        """Client self-reset password (only if they have email)"""
        
        try:
            # Find client
            client = None
            if "@" in identifier:
                client = db.query(Client).filter(Client.email.ilike(identifier)).first()
            else:
                client = db.query(Client).filter(Client.phone == identifier).first()
            
            if not client:
                # Security: don't reveal client doesn't exist
                return False, "Reset request processed"
            
            # Check if client has email (required for self-reset)
            if not client.email:
                return False, "Self-reset not available. Please contact admin."
            
            # Verify OTP (using your existing OTP service)
            if not AuthService.verify_otp(db, identifier, otp, "client_password_reset"):
                return False, "Invalid or expired OTP"
            
            # Password validation
            if new_password != confirm_password:
                return False, "Passwords do not match"
            
            if len(new_password) < 8:
                return False, "Password must be at least 8 characters"
            
            # Reset password
            client.password_hash = SecurityUtils.hash_password(new_password)
            
            # Log to audit
            AuditService.log_action(
                db=db,
                actor_type='client',
                actor_id=client.id,
                target_type='client',
                target_id=client.id,
                action='self_reset_password',
                details={
                    'via_otp': True,
                    'identifier_used': identifier,
                    'has_email': bool(client.email),
                },
                ip_address=ip_address,
                user_agent=user_agent,
            )
            
            db.commit()
            
            # Send confirmation
            if client.phone:
                # SMSService.send_password_changed_confirmation(client.phone)
                pass
            
            return True, "Password reset successfully"
            
        except Exception as e:
            db.rollback()
            logger.error(f"Client self-reset failed: {str(e)}")
            return False, "Reset failed. Please try again."
    
    @staticmethod
    def request_password_reset(
        db: Session,
        identifier: str,
        ip_address: str = "",
        user_agent: str = None,
    ) -> tuple[bool, str]:
        """Request password reset OTP for client (if they have email)"""
        
        try:
            client = None
            if "@" in identifier:
                client = db.query(Client).filter(Client.email.ilike(identifier)).first()
            else:
                client = db.query(Client).filter(Client.phone == identifier).first()
            
            if not client:
                # Security: return success even if no client
                return True, "If an account exists, reset instructions have been sent"
            
            # Check if client has email
            if not client.email:
                return False, "Self-reset not available. Please contact admin."
            
            # Generate OTP
            otp = AuthService.generate_otp(db, identifier, "client_password_reset")
            
            # Send OTP via email
            # EmailService.send_password_reset_otp(client.email, otp)
            
            # Log to audit
            AuditService.log_action(
                db=db,
                actor_type='client',
                actor_id=client.id,
                target_type='client',
                target_id=client.id,
                action='password_reset_request',
                details={
                    'identifier_used': identifier,
                    'has_email': bool(client.email),
                    'email_sent_to': client.email,
                },
                ip_address=ip_address,
                user_agent=user_agent,
            )
            
            return True, "Reset instructions sent to your email"
            
        except Exception as e:
            logger.error(f"Password reset request failed: {str(e)}")
            return False, "Failed to process request"
        

    @staticmethod
    def request_password_reset(
        db: Session,
        email: Optional[str] = None,
        phone: Optional[str] = None,
        ip_address: str = "",
        user_agent: str = None,
    ) -> tuple[bool, str, Optional[str]]:
        """
        Request password reset - send OTP to email or phone
        Returns: (success, message, debug_otp)
        """
        print(f"=== REQUEST PASSWORD RESET ===")
        print(f"Email: {email}, Phone: {phone}")
        
        if not email and not phone:
            return False, "Email or phone required", None
        
        account = None
        identifier = email or phone
        
        # Find account
        if email:
            # Email lookup - try User first, then POSUser
            account = db.query(User).filter(User.email.ilike(email)).first()
            if not account:
                account = db.query(POSUser).filter(POSUser.email.ilike(email)).first()
        elif phone:
            # Phone lookup - only for POSUser (Users don't have phone for auth)
            account = db.query(POSUser).filter(POSUser.phone == phone).first()
        
        if not account:
            # Security: Don't reveal account doesn't exist
            print("DEBUG: No account found (security response)")
            return True, "If an account exists, reset instructions have been sent", None
        
        print(f"DEBUG: Found {type(account).__name__} account ID: {account.id}")
        
        # Generate OTP
        otp = OTPService.generate_otp(db, account, "password_reset")
        
        # Log the request
        AuditService.log_action(
            db=db,
            actor_type=type(account).__name__.lower(),
            actor_id=account.id,
            target_type=type(account).__name__.lower(),
            target_id=account.id,
            action="password_reset_requested",
            details={
                "email": email,
                "phone": phone,
                "identifier_used": identifier
            },
            ip_address=ip_address,
            user_agent=user_agent,
        )
        
        print(f"DEBUG: OTP sent: {otp}")
        return True, "Reset instructions sent", otp
    
    @staticmethod
    def verify_and_reset_password(
        db: Session,
        email: Optional[str] = None,
        phone: Optional[str] = None,
        otp: str = None,
        new_password: str = None,
        ip_address: str = "",
        user_agent: str = None,
    ) -> tuple[bool, str]:
        """
        Verify OTP and reset password
        """
        print(f"=== VERIFY AND RESET PASSWORD ===")
        print(f"Email: {email}, Phone: {phone}, OTP: {otp}")
        
        if not email and not phone:
            return False, "Email or phone required"
        
        if len(new_password) < 8:
            return False, "Password must be at least 8 characters"
        
        # Determine identifier
        identifier = email or phone
        
        # Verify OTP
        account = OTPService.verify_otp(db, identifier, otp, "password_reset")
        
        if not account:
            return False, "Invalid or expired OTP"
        
        print(f"DEBUG: OTP verified for {type(account).__name__} ID: {account.id}")
        
        # Reset password
        account.password_hash = SecurityUtils.hash_password(new_password)
        
        # Update metadata
        if hasattr(account, "last_password_change"):
            account.last_password_change = datetime.now(timezone.utc)
        
        # Log the reset
        AuditService.log_action(
            db=db,
            actor_type=type(account).__name__.lower(),
            actor_id=account.id,
            target_type=type(account).__name__.lower(),
            target_id=account.id,
            action="password_reset_completed",
            details={
                "identifier_used": identifier,
                "password_changed": True
            },
            ip_address=ip_address,
            user_agent=user_agent,
        )
        
        db.commit()
        
        print(f"DEBUG: Password reset successful")
        return True, "Password reset successfully"