import logging

from fastapi import FastAPI
from contextlib import asynccontextmanager
from fastapi.staticfiles import StaticFiles
from pathlib import Path

from src.core.logging_config import setup_logging

setup_logging()

from src.core.database import Base, engine, SessionLocal
from src.core.seed_permissions import seed_permissions, seed_role
from src.core.middleware import RequestLoggingMiddleware
from src.core.exception_handlers import register_exception_handlers
from src.routes import register_routers
import src.models

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(application: FastAPI):
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        seed_permissions(db)
        seed_role(db)
    finally:
        db.close()
    logger.info("Application startup complete")
    yield
    logger.info("Application shutting down")

app = FastAPI(
    title="Freres Unis API",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(RequestLoggingMiddleware)
register_exception_handlers(app)


IS_DOCKER = Path("/app").exists()
UPLOAD_DIR = Path("/app/uploads") if IS_DOCKER else Path("uploads")
MEDIA_DIR = Path("/app/media") if IS_DOCKER else Path("media")

UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
MEDIA_DIR.mkdir(parents=True, exist_ok=True)

app.mount("/uploads", StaticFiles(directory=str(UPLOAD_DIR)), name="uploads")
app.mount("/media", StaticFiles(directory=str(MEDIA_DIR)), name="media")

register_routers(app)

@app.get("/api/v1/")
def root():
    return {"message": "Freres Unis API is running"}