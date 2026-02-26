from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from src.schemas.pos import POSCreate, POSUpdate, POSOut, POSUserCreate, POSUserUpdate, POSUserOut, POSStats
from src.services.pos import POSService
from src.core.database import get_db
from src.core.auth_dependencies import require_permission, get_current_account
from src.core.permissions import Permissions
from src.services.pos import POSUserService
from src.schemas.users import PaginatedResponse, PaginationParams


pos_router = APIRouter(prefix="/pos", tags=["POS"])


@pos_router.get(
    "/list",
    response_model=PaginatedResponse[POSOut],
    dependencies=[Depends(get_current_account)]
)
def list_pos(
    pagination: PaginationParams = Depends(),
    db: Session = Depends(get_db),
):
    # Use pagination.offset for query offset
    items, total = POSService.list_pos(db, skip=pagination.offset, limit=pagination.page_size)

    return PaginatedResponse[POSOut](
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
        items=items
    )

@pos_router.post(
    "/create",
    response_model=POSOut,
    dependencies=[Depends(require_permission(Permissions.CREATE_POS))]
)
def create_pos(data: POSCreate, db: Session = Depends(get_db)):
    return POSService.create_pos(db, data)

@pos_router.patch(
    "/{pos_id}",
    response_model=POSOut,
    dependencies=[Depends(require_permission(Permissions.UPDATE_POS))]
)
def update_pos(pos_id: int, data: POSUpdate, db: Session = Depends(get_db)):
    return POSService.update_pos(db, pos_id, data)

@pos_router.get(
    "/{pos_id}",
    response_model=POSOut,
    dependencies=[Depends(get_current_account)]
)
def get_pos(pos_id: int, db: Session = Depends(get_db)):
    return POSService.get_pos(db, pos_id)

@pos_router.get(
    "/stats/{pos_id}",
    response_model=POSStats,
    dependencies=[Depends(require_permission(Permissions.READ_POS_REPORT))]
)
def get_pos_stats(pos_id: int, db: Session = Depends(get_db)):
    return POSService.get_pos_stats(db, pos_id)

@pos_router.post(
    "/{pos_id}/users",
    response_model=POSUserOut,
    dependencies=[Depends(require_permission(Permissions.CREATE_POS_USER))]
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
    dependencies=[Depends(require_permission(Permissions.UPDATE_POS_USER))]
)
def update_pos_user(
    user_id: int,
    data: POSUserUpdate,
    db: Session = Depends(get_db),
):
    return POSUserService.update_pos_user(db, user_id, data)
