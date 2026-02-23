from fastapi import FastAPI
from contextlib import asynccontextmanager
from fastapi.staticfiles import StaticFiles

from src.core.database import Base, engine, SessionLocal
from src.core.seed_permissions import seed_permissions, seed_role, seed_default_client_role_and_permissions

import src.models  # Ensure models are registered

from src.routes.auth import auth_router
from src.routes.system_user import user_router
from src.routes.clients import client_router
from src.routes.pos import pos_router
from src.routes.address import address_router
from src.routes.id_types_routes import id_type_router
from src.routes.pos_inventory import inventory_router
from src.routes.pos_sales import sales_router
from src.routes.pos_expenses import expenses_router
from src.routes.procurements import procurement_router
from src.routes.provider import provider_router
from src.routes.catalog_route import product_router
from src.routes import files


@asynccontextmanager
async def lifespan(app: FastAPI):
    # ---- STARTUP ----
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        seed_permissions(db)
        seed_role(db)
        seed_default_client_role_and_permissions(db)
    finally:
        db.close()

    yield

app = FastAPI(
    title="Freres Unis API",
    version="1.0.0",
    lifespan=lifespan
)

app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

API_PREFIX = "/api/v1"

app.include_router(auth_router, prefix=API_PREFIX)
app.include_router(user_router, prefix=API_PREFIX)
app.include_router(client_router, prefix=API_PREFIX)
app.include_router(pos_router, prefix=API_PREFIX)
app.include_router(product_router, prefix=API_PREFIX)
app.include_router(inventory_router, prefix=API_PREFIX)
app.include_router(sales_router, prefix=API_PREFIX)
app.include_router(expenses_router, prefix=API_PREFIX)
app.include_router(procurement_router, prefix=API_PREFIX)
app.include_router(provider_router, prefix=API_PREFIX)
app.include_router(address_router, prefix=API_PREFIX)
app.include_router(id_type_router, prefix=API_PREFIX)
app.include_router(files.router, prefix=API_PREFIX)


@app.get(f"{API_PREFIX}/")
def root():
    return {"message": "Freres Unis API is running"}