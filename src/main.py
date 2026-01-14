from src.core.database import Base, engine
from fastapi import FastAPI
from src.routes.auth import auth_router
from src.routes.system_user import user_router
from src.routes.clients import client_router
from src.routes.pos import pos_router
from src.routes.address import address_router
from src.routes.id_types_routes import id_type_router
import src.models  


app = FastAPI(title="Freres Unis API", version="1.0.0")

# Define a base prefix
API_PREFIX = "/api/v1"

# Create tables
Base.metadata.create_all(bind=engine)

# Include all routers with the prefix
app.include_router(auth_router, prefix=API_PREFIX)
app.include_router(user_router, prefix=API_PREFIX)
app.include_router(client_router, prefix=API_PREFIX)
app.include_router(pos_router, prefix=API_PREFIX)
app.include_router(address_router, prefix=API_PREFIX)
app.include_router(id_type_router, prefix=API_PREFIX)


@app.get(f"{API_PREFIX}/")
def root():
    return {"message": "Freres Unis API API is running"}
