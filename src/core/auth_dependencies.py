from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional
from fastapi import Depends, HTTPException, status, Header
from sqlalchemy.orm import Session
from src.services.auth_service import AuthService 
from src.models.security import APIKey
from src.core.database import get_db
from src.core.permissions import Permissions


security = HTTPBearer()

def get_current_account(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security) , 
    db: Session = Depends(get_db)
) -> dict:
    """
        Returns:
        {
            "account_type": "user" | "client" | "posuser",
            "account": SQLAlchemy instance
        }
    """
    if not credentials:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            detail="Authorization required"
        )
    token = credentials.credentials
    account_info = AuthService.validate_access_token(db, token)

    if not account_info:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired access token"
        )
    
    return account_info

def get_api_key(
        x_api_key: str = Header(..., alias="X-API-Key"),
        x_api_secret: str = Header(..., alias="X-API-Secret"),
        db: Session = Depends(get_db)
) -> APIKey:
    api_key = AuthService.validate_api_key(db, x_api_key, x_api_secret)

    if not api_key:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API Key or secret"
        )
    return api_key

def require_role(required_roles: list[str]):
    def checker(current_user: dict =  Depends(get_current_account)):
        account = current_user['account']
        roles  = getattr(account, 'roles', [])
        role_names = [role.name for role in roles]

        # SUPER_ADMIN bypass
        if "SUPER_ADMIN" in role_names:
            return account
        
        for role in role_names:
            if role in required_roles:
                return account
            
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            detail=f"Required role(s): {required_roles}"
        )
    return checker

def require_permission(permission_name: Permissions):
    def checker(current_user: dict = Depends(get_current_account)):
        account = current_user["account"]
        roles = getattr(account, "roles", [])

        for role in roles:
            if role.name == "SUPER_ADMIN":
                return account
        
        for role in roles:
            for perm in role.permissions:
                if perm.name == permission_name.value:
                    return account
                
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            detail=f"Required: {permission_name.value}"
        )
    return checker

def api_key_permission(required_permission: str):
    def checker(api_key: APIKey = Depends(get_api_key)):
        permissions = api_key.permissions or []

        if required_permission not in permissions:
            raise HTTPException(
                status.HTTP_403_FORBIDDEN,
                detail="Insufficient API permissions"
            )
        return api_key
    return checker