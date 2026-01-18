# src/core/auth_dependencies.py
from fastapi import Depends, HTTPException, status, Header
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from typing import Optional, Dict
from src.services.auth_service import AuthService
from src.core.database import get_db
from src.models.security import APIKey
from src.models.users import UserRole, User
from src.models.clients import Client
from src.models.pos import POSUser


security = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    if not credentials:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")
    token = credentials.credentials
    user = AuthService.validate_access_token(db, token)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")
    return user


def get_current_account(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db)
) -> dict:
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required"
        )
    
    token = credentials.credentials
    account_info = AuthService.validate_access_token(db, token)
    
    if not account_info:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token"
        )

    return account_info


def get_api_key(
    x_api_key: str = Header(..., alias="X-API-Key"),
    x_api_secret: str = Header(..., alias="X-API-Secret"),
    db: Session = Depends(get_db)
) -> APIKey:
    api_key = AuthService.validate_api_key(db, x_api_key, x_api_secret)
    if not api_key:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key or secret")
    return api_key

def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db)
) -> Optional[User]:
    if not credentials: return None
    return AuthService.validate_access_token(db, credentials.credentials)

# def require_role(required_roles: list[str]):
#     def role_checker(current_user: User = Depends(get_current_user)):
#         if current_user.role not in required_roles and current_user.role != UserRole.ADMIN:
#             raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")
#         return current_user
#     return role_checker
def require_role(required_roles: list[UserRole]):
    def role_checker(
        current_account: dict = Depends(get_current_account)
    ):
        account_type = current_account["account_type"]
        account = current_account["account"]

        if account_type != "user":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only users can access this resource"
            )

        if account.role == UserRole.ADMIN:
            return account

        if account.role not in required_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions"
            )

        return account

    return role_checker

def require_permission(required_permission: str):
    def permission_checker(api_key: APIKey = Depends(get_api_key)):
        permissions = api_key.permissions or []
        if required_permission not in permissions:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")
        return api_key
    return permission_checker
