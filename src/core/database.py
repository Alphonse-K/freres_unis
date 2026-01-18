from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from src.core.config import settings

# -----------------------------------------------------
# Database Engine + Session
# -----------------------------------------------------

DATABASE_URL = settings.DATABASE_URL

engine = create_engine(
    DATABASE_URL,
    # connect_args={"options": "-csearch_path=public"},
    echo=settings.SQL_ECHO
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

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


