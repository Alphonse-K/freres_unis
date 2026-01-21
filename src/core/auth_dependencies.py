# src/core/auth_dependencies.py
from fastapi import Depends, HTTPException, status, Header
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from typing import Optional, Dict
from src.services.auth_service import AuthService
from src.core.database import get_db
from src.models.security import APIKey
from src.models.users import UserRole, User
# from src.models.clients import Client
# from src.models.pos import POSUser
from src.models.clients import ClientRole



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


def require_role(allowed_user_roles: list[UserRole], allowed_client_roles: list[ClientRole] = None):
    """
    Flexible dependency that can check both user and client roles
    
    Examples:
    - require_role([UserRole.ADMIN])  # Only admin users
    - require_role([UserRole.USER], [ClientRole.SUPER_CLIENT])  # User role OR Super Client
    - require_role(allowed_client_roles=[ClientRole.CLIENT])  # Any client
    """
    def role_checker(
        current_account: dict = Depends(get_current_account)
    ):
        account_type = current_account["account_type"]
        account = current_account["account"]
        
        # Handle CLIENTS
        if account_type == "client":
            if not allowed_client_roles:
                raise HTTPException(403, "Clients not allowed for this route")
            
            if account.role.name not in allowed_client_roles:
                raise HTTPException(
                    403, 
                    f"Client role '{account.role.name}' not authorized. Required: {[r for r in allowed_client_roles]}"
                )
            return account
        
        # Handle USERS
        if account_type == "user":
            if account.role == UserRole.ADMIN:
                return account
            
            if not allowed_user_roles:
                raise HTTPException(403, "Users not allowed for this route")
            
            if account.role not in allowed_user_roles:
                raise HTTPException(
                    403,
                    f"User role '{account.role.value}' not authorized. Required: {[r.value for r in allowed_user_roles]}"
                )
            return account
        
        raise HTTPException(403, "Unknown account type")
    
    return role_checker

def require_permission(required_permission: str):
    def permission_checker(api_key: APIKey = Depends(get_api_key)):
        permissions = api_key.permissions or []
        if required_permission not in permissions:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")
        return api_key
    return permission_checker
