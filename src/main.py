from fastapi import FastAPI
from contextlib import asynccontextmanager
from fastapi.staticfiles import StaticFiles
from pathlib import Path

from src.core.database import Base, engine, SessionLocal
from src.core.seed_permissions import seed_permissions, seed_role
from src.routes import register_routers
import src.models


@asynccontextmanager
async def lifespan(application: FastAPI):
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        seed_permissions(db)
        seed_role(db)
    finally:
        db.close()
    yield

app = FastAPI(
    title="Freres Unis API",
    version="1.0.0",
    lifespan=lifespan
)


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