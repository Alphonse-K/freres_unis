# src/services/otp_service.py
import logging
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from src.models.security import OTPCode
from src.models.users import User
from src.core.otp import OTPUtils
from src.services.email_service import EmailService

logger = logging.getLogger(__name__)

class OTPService:

    @staticmethod
    def generate_otp(db: Session, user: User, purpose: str = "login") -> str:
        # Remove old unused OTPs
        db.query(OTPCode).filter(
            OTPCode.user_id == user.id,
            OTPCode.purpose == purpose,
            OTPCode.is_used == False
        ).delete()
        
        code = OTPUtils.generate_otp()
        expires_at = OTPUtils.get_expiry()
        
        otp_record = OTPCode(
            user_id=user.id,
            code=code,
            purpose=purpose,
            expires_at=expires_at
        )
        db.add(otp_record)
        db.commit()

        try:
            EmailService.send_otp_email(user.email, user.username, code, purpose)
        except Exception as e:
            logger.error(f"Failed to send OTP email: {str(e)}")

        return code

    @staticmethod
    def verify_otp(db: Session, email: str, code: str, purpose: str = "login") -> User | None:
        otp_record = db.query(OTPCode).join(User).filter(
            User.email == email,
            OTPCode.code == code,
            OTPCode.purpose == purpose,
            OTPCode.is_used == False,
            OTPCode.expires_at > datetime.now(timezone.utc)
        ).first()

        if not otp_record:
            return None

        # Mark as used
        otp_record.is_used = True
        otp_record.used_at = datetime.now(timezone.utc)
        user = otp_record.user
        user.last_login = datetime.now(timezone.utc)
        db.commit()

        return user
