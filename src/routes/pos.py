from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from src.schemas.pos import POSCreate, POSUpdate, POSOut, POSUserCreate, POSUserUpdate, POSUserOut
from src.services.pos import POSService
from src.core.database import get_db
from src.core.auth_dependencies import require_role
from src.services.pos import POSUserService


pos_router = APIRouter(prefix="/pos", tags=["POS"])


@pos_router.post(
    "/create",
    response_model=POSOut,
    dependencies=[Depends(require_role(["ADMIN"]))]
)
def create_pos(data: POSCreate, db: Session = Depends(get_db)):
    return POSService.create_pos(db, data)

@pos_router.patch(
    "/{pos_id}",
    response_model=POSOut,
    dependencies=[Depends(require_role(["ADMIN"]))]
)
def update_pos(pos_id: int, data: POSUpdate, db: Session = Depends(get_db)):
    return POSService.update_pos(db, pos_id, data)

@pos_router.get(
    "/{pos_id}",
    response_model=POSOut,
    dependencies=[Depends(require_role(["ADMIN", "CHECKER"]))]
)
def get_pos(pos_id: int, db: Session = Depends(get_db)):
    return POSService.get_pos(db, pos_id)

from fastapi import Query


@pos_router.get(
    "/list",
    response_model=dict,
    dependencies=[Depends(require_role(["ADMIN"]))]
)
def list_pos(
    db: Session = Depends(get_db),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100)
):
    items, total = POSService.list_pos(db, skip=skip, limit=limit)

    return {
        "total": total,
        "items": items
    }

@pos_router.post(
    "/{pos_id}/users",
    response_model=POSUserOut,
    dependencies=[Depends(require_role(["ADMIN", "MANAGER"]))]
)
def create_pos_user(
    pos_id: int,
    data: POSUserCreate,
    db: Session = Depends(get_db),
):
    return POSUserService.create_pos_user(db, pos_id, data)

@pos_router.patch(
    "/users/{user_id}",
    response_model=POSUserOut,
    dependencies=[Depends(require_role(["ADMIN", "MANAGER"]))]
)
def update_pos_user(
    user_id: int,
    data: POSUserUpdate,
    db: Session = Depends(get_db),
):
    return POSUserService.update_pos_user(db, user_id, data)
