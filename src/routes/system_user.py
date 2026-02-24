
from fastapi import Depends, APIRouter
from sqlalchemy.orm import Session

from src.schemas.users import UserCreate, UserOut, UserUpdate, LogoutResponse, PaginatedResponse, PaginationParams, UserFilter
from src.services.user_service import UserService
from src.core.database import get_db
from src.core.auth_dependencies import require_role, require_permission
from src.core.permissions import Permissions
from src.models.users import UserRole

user_router = APIRouter(prefix="/users", tags=["System User"])

@user_router.post(
    "/create",
    response_model=UserOut,
    # dependencies=[Depends(require_role(["ADMIN"]))]
)
def create_user(
    user_data: UserCreate,
    db: Session = Depends(get_db),
):
    return UserService.create_user(db, user_data)

@user_router.patch(
    "/update/{user_id}", 
    response_model=UserOut, 
)
def update_user(
    user_id: int,
    user_data: UserUpdate,
    db: Session = Depends(get_db),
    current_user = Depends(require_permission(Permissions.UPDATE_USER))
):
    return UserService.update_user(db, user_id, user_data)

@user_router.delete(
    "/users/{user_id}", 
    response_model=LogoutResponse, 
)
def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(require_permission(Permissions.DELETE_USER))
):
    UserService.delete_user(db, user_id)
    return {"message": "User deleted successfully"}

@user_router.get(
    "/list-users",
    response_model=PaginatedResponse[UserOut],
)
def list_users(
    filters: UserFilter = Depends(),
    pagination: PaginationParams= Depends(),
    db: Session = Depends(get_db),
    current_user = Depends(require_permission(Permissions.READ_USER))
):
    total, users = UserService.list_users(db, filters, pagination)
    
    return {
        "total": total,
        "page": pagination.page,
        "page_size": pagination.page_size,
        "items": users,
    }


