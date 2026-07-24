from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from src.core.config import settings

# -----------------------------------------------------
# Database Engine + Session
# -----------------------------------------------------
DATABASE_URL = settings.DATABASE_URL

# engine = create_engine(
#     DATABASE_URL,
#     echo=settings.SQL_ECHO
# )

engine = create_engine(
    DATABASE_URL,
    echo=settings.SQL_ECHO,
    pool_pre_ping=True,
    pool_recycle=3600,
    pool_size=20,
    max_overflow=40,
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


