from pydantic_settings import BaseSettings
from functools import lru_cache

class Settings(BaseSettings):
    # -----------------------------
    # Database
    # -----------------------------
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str
    DATABASE_URL: str
    SQL_ECHO: bool = False

    # -----------------------------
    # Message broker
    # -----------------------------
    REDIS_URL: str
    CELERY_BROKER_URL: str
    CELERY_RESULT_BACKEND: str
    REDIS_PASSWORD: str

    # -----------------------------
    # Security / Authentication
    # -----------------------------
    SECRET_KEY: str
    REFRESH_SECRET_KEY: str = None  # optional, fallback to SECRET_KEY + "refresh"
    ALGORITHM: str = "HS256"

    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30
    OTP_EXPIRE_MINUTES: int = 5

    MAX_FAIL: int = 5
    SUSP_MIN: int = 30  # suspension duration in minutes

    # -----------------------------
    # API Keys
    # -----------------------------
    API_KEY_LENGTH: int = 32
    API_SECRET_LENGTH: int = 64

    # -----------------------------
    # Email / SMTP
    # -----------------------------
    SMTP_SERVER: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USERNAME: str = ""
    SMTP_PASSWORD: str = ""
    EMAIL_FROM: str = "noreply@cashmoov.net"
    EMAIL_FROM_NAME: str = "CashMoov"
    
    # -----------------------------
    # App Environment
    # -----------------------------
    ENVIRONMENT: str = "development"
    LOG_LEVEL: str = "info"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


# -----------------------------
# Cached settings instance
# -----------------------------
@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()

# Optional: Fallback for REFRESH_SECRET_KEY
if not settings.REFRESH_SECRET_KEY:
    settings.REFRESH_SECRET_KEY = settings.SECRET_KEY + "refresh"
