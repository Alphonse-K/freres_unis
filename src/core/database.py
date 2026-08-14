import logging

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from src.core.config import settings

logger = logging.getLogger(__name__)

# -----------------------------------------------------
# Database Engine + Session
# -----------------------------------------------------
DATABASE_URL = settings.DATABASE_URL

# Pool size is per-process: uvicorn's --workers and each Celery process all
# import this module separately and get their own pool. Keep DB_POOL_SIZE /
# DB_MAX_OVERFLOW small and override them per-service (web vs worker vs beat)
# via env vars in docker-compose.yaml instead of raising these defaults --
# multiplying a large pool by several processes is what exhausts Postgres's
# max_connections.
engine = create_engine(
    DATABASE_URL,
    echo=settings.SQL_ECHO,
    pool_pre_ping=True,
    pool_recycle=settings.DB_POOL_RECYCLE,
    pool_size=settings.DB_POOL_SIZE,
    max_overflow=settings.DB_MAX_OVERFLOW,
    pool_timeout=settings.DB_POOL_TIMEOUT,
)

logger.info(
    f"Database engine configured: pool_size={settings.DB_POOL_SIZE}, "
    f"max_overflow={settings.DB_MAX_OVERFLOW}, pool_timeout={settings.DB_POOL_TIMEOUT}s, "
    f"pool_recycle={settings.DB_POOL_RECYCLE}s"
)

SessionLocal = sessionmaker(
    autocommit=False, 
    autoflush=False, 
    bind=engine
)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# -----------------------------------------------------
# Base Model
# -----------------------------------------------------
class Base(DeclarativeBase):
    pass


