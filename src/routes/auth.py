from fastapi import APIRouter, Depends, Request, HTTPException, status
from sqlalchemy.orm import Session
from src.schemas.security import APIKeyCreate, APIKeyOut, OTPVerify, RefreshTokenRequest, TokenPairResponse
from src.models.users import User
from src.models.clients import Client
from src.models.pos import POSUser
from src.schemas.users import PinLogin, PasswordLogin, UserOut, UserOut, UserSchema, LogoutResponse
from src.services.auth_service import AuthService
from src.core.security import SecurityUtils
from src.core.auth_dependencies import get_db, get_current_user, require_role
from datetime import timezone, datetime
import logging


auth_router = APIRouter(prefix="/auth", tags=["Authentication"])

def _meta(request: Request):
    return request.client.host, request.headers.get("user-agent", "")

@auth_router.post("/login/password")
def login_password(
    data: PasswordLogin,
    request: Request,
    db: Session = Depends(get_db)
):
    ip, ua = _meta(request)
    identifier = data.email or data.phone

    if not identifier:
        raise HTTPException(422, "email or phone required")

    account = AuthService.authenticate(
        db, identifier, data.password, "password", ip, ua
    )

    if not account:
        raise HTTPException(401, "Invalid credentials")

    # SYSTEM USER → OTP FLOW
    if isinstance(account, User):
        if AuthService.is_otp_required(account, ip, ua):
            AuthService.generate_otp(db, account, "login")
            return {
                "otp_required": True,
                "message": "OTP sent",
                "expires_in": 600
            }

    # Extract device info
    device_info = {
        "user_agent": ua,
        "ip_address": ip
    }

    # UPDATE last login metadata
    account.last_login = datetime.now(timezone.utc)
    account.last_login_ip = device_info["ip_address"]
    account.last_login_user_agent = device_info["user_agent"]
    db.commit()

    # Create tokens
    tokens = AuthService.create_tokens(db, account, device_info)
    
    # Return token response
    return {
        **tokens,
        "user": UserSchema.model_validate(account)
    }

@auth_router.post("/login/pin")
def login_pin(
    data: PinLogin,
    request: Request,
    db: Session = Depends(get_db)
):
    ip, ua = _meta(request)

    account = AuthService.authenticate(
        db, data.phone, data.pin, "pin", ip, ua
    )

    if not account:
        raise HTTPException(401, "Invalid credentials")

    # Extract device info
    device_info = {
        "user_agent": ua,
        "ip_address": ip
    }

    # UPDATE last login metadata
    account.last_login = datetime.now(timezone.utc)
    account.last_login_ip = device_info["ip_address"]
    account.last_login_user_agent = device_info["user_agent"]
    db.commit()

    # Create tokens
    tokens = AuthService.create_tokens(db, account, device_info)
    
    # Return token response
    return {
        **tokens,
        "user": UserSchema.model_validate(account)
    }

@auth_router.post("/verify-otp")
def verify_otp(
    verify_data: OTPVerify,
    request: Request,
    db: Session = Depends(get_db)
):
    user = AuthService.verify_otp(db, verify_data, "login")
    if not user:
        raise HTTPException(401, "Invalid or expired OTP")

    ip, ua = _meta(request)
    device_info = {
        "ip_address": ip,
        "user_agent": ua
    }

    AuthService.update_login_metadata(
        user,
        device_info["ip_address"],
        device_info["user_agent"],
        db
    )

    tokens = AuthService.create_tokens(db, user, device_info)

    return {
        **tokens,
        "user": UserSchema.model_validate(user)
    }

@auth_router.post("/refresh", response_model=TokenPairResponse)
def refresh_tokens(
    refresh_data: RefreshTokenRequest,
    request: Request,
    db: Session = Depends(get_db)
):
    ip, ua = _meta(request)
    device_info = {
        "ip_address": ip,
        "user_agent": ua
    }

    # Refresh tokens
    result = AuthService.refresh_tokens(db, refresh_data.refresh_token, device_info)
    if not result:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token"
        )

    # Get user info from new access token
    payload = SecurityUtils.verify_access_token(result["access_token"])
    if not payload or "sub" not in payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid access token generated"
        )

    user = db.query(User).filter(User.id == int(payload["sub"])).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )

    return {
        **result,
        "user": UserSchema.model_validate(user)
    }

@auth_router.post("/logout", response_model=LogoutResponse)
def logout(
    request: Request,
    current_account: User | Client | POSUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    auth_header = request.headers.get("authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(400, "Invalid authorization header")
    
    token = auth_header.replace("Bearer ", "")
    AuthService.logout_user(db, current_account, token)
    
    return {"message": "Logged out successfully"}

@auth_router.post("/logout-all", response_model=LogoutResponse)
def logout_all(
    current_account: User | Client | POSUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Log out from all machine
    """

    access_token = ""  # optionally pass last used access token
    AuthService.logout_all_devices(db, current_account, access_token)
    
    return {"message": "Logged out from all devices successfully"}

# API Key Management Routes
@auth_router.post("/api-keys", response_model=APIKeyOut)
def create_api_key(
    create_data: APIKeyCreate,
    current_user: User = Depends(require_role(["ADMIN"])),
    db: Session = Depends(get_db)
):
    """
    Create new API key for machine-to-machine communication
    """
    result = AuthService.create_api_key(db, current_user.company_id, create_data)
    return result

@auth_router.get("/api-keys")
def list_api_keys(
    company_id: int ,
    db: Session = Depends(get_db)
):
    """
    List all API keys for the current company
    """
    keys = AuthService.get_company_api_keys(db, company_id)
    return keys

@auth_router.delete("/api-keys/{key_id}")
def revoke_api_key(
    key_id: int,
    current_user: User = Depends(require_role(["ADMIN"])),
    db: Session = Depends(get_db)
):
    """
    Revoke (disable) an API key
    """
    success = AuthService.revoke_api_key(db, key_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API key not found"
        )
    
    return {"message": "API key revoked successfully"}

# Utility endpoints
@auth_router.get("/me", response_model=UserOut)
def get_current_user_info(current_user: User = Depends(get_current_user)):
    """
    Get current user information
    """
    return current_user
