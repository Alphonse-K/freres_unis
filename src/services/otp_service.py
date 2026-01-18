# src/services/otp_service.py
import logging
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from src.models.security import OTPCode
from src.models.users import User
from src.models.pos import POSUser
from src.core.otp import OTPUtils
from src.services.email_service import EmailService

logger = logging.getLogger(__name__)

# services/otp_service.py - UPDATED
class OTPService:
    
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
            # Keep user_id for backward compatibility (nullable)
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
        identifier: str,  # Can be email or phone
        code: str,
        purpose: str = "login"
    ):
        """
        Verify OTP for User (by email) or POSUser (by email or phone)
        """
        identifier = identifier.strip().lower()
        
        print(f"DEBUG verify_otp: identifier='{identifier}', purpose='{purpose}'")
        
        # Strategy: Try all possibilities
        
        # 1. Try User by email
        if "@" in identifier:
            user = db.query(User).filter(User.email.ilike(identifier)).first()
            if user:
                print(f"DEBUG: Trying User with email: {identifier}")
                otp_record = db.query(OTPCode).filter(
                    OTPCode.account_type == "user",
                    OTPCode.account_id == user.id,
                    OTPCode.code == code,
                    OTPCode.purpose == purpose,
                    OTPCode.is_used == False,
                    OTPCode.expires_at > datetime.now(timezone.utc)
                ).first()
                
                if otp_record:
                    print(f"DEBUG: OTP found for User ID: {user.id}")
                    otp_record.is_used = True
                    otp_record.used_at = datetime.now(timezone.utc)
                    user.last_login = datetime.now(timezone.utc)
                    db.commit()
                    return user
        
        # 2. Try POSUser by email
        if "@" in identifier:
            pos_user = db.query(POSUser).filter(POSUser.email.ilike(identifier)).first()
            if pos_user:
                print(f"DEBUG: Trying POSUser with email: {identifier}")
                otp_record = db.query(OTPCode).filter(
                    OTPCode.account_type == "pos",
                    OTPCode.account_id == pos_user.id,
                    OTPCode.code == code,
                    OTPCode.purpose == purpose,
                    OTPCode.is_used == False,
                    OTPCode.expires_at > datetime.now(timezone.utc)
                ).first()
                
                if otp_record:
                    print(f"DEBUG: OTP found for POSUser ID: {pos_user.id}")
                    otp_record.is_used = True
                    otp_record.used_at = datetime.now(timezone.utc)
                    pos_user.last_login = datetime.now(timezone.utc)
                    db.commit()
                    return pos_user
        
        # 3. Try POSUser by phone (only for phone identifiers)
        if not "@" in identifier:
            pos_user = db.query(POSUser).filter(POSUser.phone == identifier).first()
            if pos_user:
                print(f"DEBUG: Trying POSUser with phone: {identifier}")
                otp_record = db.query(OTPCode).filter(
                    OTPCode.account_type == "pos",
                    OTPCode.account_id == pos_user.id,
                    OTPCode.code == code,
                    OTPCode.purpose == purpose,
                    OTPCode.is_used == False,
                    OTPCode.expires_at > datetime.now(timezone.utc)
                ).first()
                
                if otp_record:
                    print(f"DEBUG: OTP found for POSUser ID: {pos_user.id}")
                    otp_record.is_used = True
                    otp_record.used_at = datetime.now(timezone.utc)
                    pos_user.last_login = datetime.now(timezone.utc)
                    db.commit()
                    return pos_user
        
        print(f"DEBUG: No valid OTP found for identifier: {identifier}")
        return None