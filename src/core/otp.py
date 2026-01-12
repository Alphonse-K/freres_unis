# src/core/otp.py
from datetime import datetime, timezone, timedelta
import secrets


OTP_EXPIRE_MINUTES = 5

class OTPUtils:
    @staticmethod
    def generate_otp() -> str:
        return ''.join(str(secrets.randbelow(10)) for _ in range(6))

    @staticmethod
    def get_expiry(minutes: int = OTP_EXPIRE_MINUTES) -> datetime:
        return datetime.now(timezone.utc) + timedelta(minutes=minutes)

    @staticmethod
    def is_expired(expires_at: datetime) -> bool:
        return datetime.now(timezone.utc) > expires_at
