from fastapi import APIRouter, Depends, Request, HTTPException, status, Query, Body
from sqlalchemy.orm import Session
from src.schemas.security import APIKeyCreate, APIKeyOut, OTPVerify, RefreshTokenRequest, TokenPairResponse, ChangePasswordRequest, ChangePinRequest, AdminSetClientPassword, AdminResetClientPassword, AdminSetClientPin
from src.models.users import User
from src.models.clients import Client
from src.schemas.clients import ClientSchema
from src.models.pos import POSUser
from src.schemas.pos import POSUserSchema
from src.services.audit_service import AuditService
from src.schemas.users import PinLogin, PasswordLogin, UserOut, UserOut, UserSchema, LogoutResponse
from src.services.auth_service import AuthService
from src.core.security import SecurityUtils
from src.core.auth_dependencies import get_db, get_current_user, require_role, get_current_account
from datetime import timezone, datetime
from typing import Optional, Dict, Any
import logging


auth_router = APIRouter(prefix="/auth", tags=["Authentication"])

def _meta(request: Request):
    return request.client.host, request.headers.get("user-agent", "")


def _get_user_schema(account):
    """Return the proper schema depending on account type."""
    if isinstance(account, User):
        return UserSchema.model_validate(account)
    elif isinstance(account, POSUser):
        return POSUserSchema.model_validate(account)
    elif isinstance(account, Client):
        # sanitize email if invalid
        if not account.email or "@" not in account.email:
            account.email = None
        return ClientSchema.model_validate(account)
    else:
        return None


@auth_router.post("/login/password")
def login_password(
    data: PasswordLogin,
    request: Request,
    db: Session = Depends(get_db)
):
    ip, ua = _meta(request)
    
    # Get identifier safely
    identifier = None
    if data.email:
        identifier = data.email
    elif data.phone:
        identifier = data.phone
    
    if not identifier:
        raise HTTPException(422, "email or phone required")

    # DEBUG: Print what we're trying to login with
    print(f"Login attempt - Email: {data.email}, Phone: {data.phone}, Identifier: {identifier}")
    
    # DEBUG: Check all users
    all_users = db.query(User).all()
    print("All users in DB:", [(u.email, u.role) for u in all_users])

    # FIX: Only query by email if email is provided and not None
    if data.email:
        user = db.query(User).filter(User.email.ilike(data.email)).first()
        print(f"User found by email '{data.email}': {user}")
        if user:
            print(f"User password hash exists: {bool(user.password_hash)}")
    else:
        print("No email provided, skipping email lookup")

    # FIX: Pass the identifier that actually has a value
    account = AuthService.authenticate(
        db, identifier, data.password, "password", ip, ua
    )
    print("Authenticated account:", account)
    
    if not account:
        raise HTTPException(401, "Invalid credentials")
    
    # Rest of your code remains the same...    
    # Rest of your code...    
    # SYSTEM USER → OTP FLOW
    if isinstance(account, User) and AuthService.is_otp_required(account, ip, ua):
        AuthService.generate_otp(db, account, "login")
        return {
            "otp_required": True,
            "message": "OTP sent",
            "expires_in": 600
        }

    # Update last login metadata
    account.last_login = datetime.now(timezone.utc)
    account.last_login_ip = ip
    account.last_login_user_agent = ua
    db.commit()

    # Create tokens
    tokens = AuthService.create_tokens(db, account, {"ip_address": ip, "user_agent": ua})

    # Return proper schema
    return {
        **tokens,
        "user": _get_user_schema(account)
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

    # Update last login metadata
    account.last_login = datetime.now(timezone.utc)
    account.last_login_ip = ip
    account.last_login_user_agent = ua
    db.commit()

    # Create tokens
    tokens = AuthService.create_tokens(db, account, {"ip_address": ip, "user_agent": ua})

    # Return proper schema
    return {
        **tokens,
        "user": _get_user_schema(account)
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

    result = AuthService.refresh_tokens(db, refresh_data.refresh_token, device_info)
    if not result:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token"
        )

    # Decode to identify account
    payload = SecurityUtils.verify_access_token(result["access_token"])
    if not payload:
        raise HTTPException(401, "Invalid token")

    account_type = payload["account_type"]
    account_id = int(payload["sub"])

    model_map = {
        "user": User,
        "pos": POSUser,
        "client": Client
    }

    account = db.query(model_map[account_type]).get(account_id)

    return {
        **result,
        "user": serialize_account(account)
    }

@auth_router.post("/change-password", status_code=status.HTTP_200_OK)
def change_password(
    payload: ChangePasswordRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_account: dict = Depends(get_current_account),
):
    """Change password endpoint"""
    account = current_account["account"] 
    account_type = current_account["account_type"]
    
    ip_address = request.client.host if request.client else ""
    
    success = AuthService.change_password(
        db=db,
        account_type=account_type,
        account_id=account.id,
        old_password=payload.old_password,
        new_password=payload.new_password,
        confirm_password=payload.confirm_password,
        ip_address=ip_address,
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password change failed. Check old password or password requirements."
        )
    
    return {
        "success": True,
        "message": "Password changed successfully"
    }


@auth_router.post("/change-pin", status_code=status.HTTP_200_OK)
def change_pin(
    payload: ChangePinRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_account: dict = Depends(get_current_account),
):
    """Change PIN endpoint (POS users and clients only)"""
    account = current_account["account"] 
    account_type = current_account["account_type"]
    
    # Verify account type
    if account_type not in ["pos", "client"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="PIN change only available for POS users and clients"
        )
    
    ip_address = request.client.host if request.client else ""
    
    success = AuthService.change_pin(
        db=db,
        account_type=account_type,
        account_id=account.id,
        old_pin=payload.old_pin,
        new_pin=payload.new_pin,
        confirm_pin=payload.confirm_pin,
        ip_address=ip_address,
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="PIN change failed. Check old PIN or PIN requirements (4-6 digits)."
        )
    
    return {
        "success": True,
        "message": "PIN changed successfully"
    }

@auth_router.post("/clients/{phone}/auth/reset-password", status_code=200)
def reset_client_password(
    phone: str,
    payload: AdminResetClientPassword,
    request: Request,
    db: Session = Depends(get_db),
    current_admin: dict = Depends(get_current_account),
):
    """Admin resets client password (generates random or uses provided)"""
    
    admin = current_admin["account"]
    ip = request.client.host if request.client else ""
    ua = request.headers.get("user-agent")
    
    success, message, temp_password = AuthService.admin_reset_password(
        db=db,
        phone=phone,
        admin_id=admin.id,
        ip_address=ip,
        user_agent=ua,
        generate_random=payload.generate_random,
    )
    
    if not success:
        raise HTTPException(400, detail=message)
    
    response = {"success": True, "message": message}
    
    # Include temp password only if generated and admin should see it
    if temp_password:
        response["temporary_password"] = temp_password
        response["note"] = "Share this password securely with the client"
    
    return response


@auth_router.post("/clients/{phone}/auth/set-pin", status_code=200)
def set_client_pin(
    phone: str,
    payload: AdminSetClientPin,
    request: Request,
    db: Session = Depends(get_db),
    current_admin: dict = Depends(get_current_account),
):
    """Admin sets PIN for a client"""
    
    admin = current_admin["account"]
    ip = request.client.host if request.client else ""
    ua = request.headers.get("user-agent")
    
    success, message = AuthService.admin_set_pin(
        db=db,
        phone=phone,
        new_pin=payload.new_pin,
        admin_id=admin.id,
        ip_address=ip,
        user_agent=ua,
        notes=payload.notes,
    )
    
    if not success:
        raise HTTPException(400, detail=message)
    
    return {"success": True, "message": message}


@auth_router.get("/clients/{client_id}/auth/logs", status_code=200)
def get_client_auth_logs(
    client_id: int,
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_admin: dict = Depends(get_current_user),
):
    """Get authentication audit logs for a client"""
    
    logs = AuditService.get_client_auth_logs(db, client_id, limit)
    
    return {
        "success": True,
        "client_id": client_id,
        "logs": [
            {
                "id": log.id,
                "action": log.action,
                "actor_type": log.actor_type,
                "actor_id": log.actor_id,
                "details": log.details,
                "ip_address": log.ip_address,
                "created_at": log.created_at.isoformat(),
            }
            for log in logs
        ]
    }

@auth_router.get("/clients/{client_id}/auth/status", status_code=200)
def get_client_auth_status(
    client_id: int,
    db: Session = Depends(get_db),
    current_admin: dict = Depends(get_current_user),
):
    """Get client authentication status"""
    
    client = db.query(Client).filter(Client.id == client_id).first()
    if not client:
        raise HTTPException(404, "Client not found")
    
    # Get recent auth logs
    recent_logs = AuditService.get_client_auth_logs(db, client_id, 5)
    
    return {
        "success": True,
        "client": {
            "id": client.id,
            "phone": client.phone,
            "email": client.email,
            "has_password": bool(client.password_hash),
            "has_pin": bool(getattr(client, 'pin_hash', None)),
            "can_self_reset": bool(client.email),
            "requires_admin_setup": not client.email,
        },
        "recent_auth_activity": [
            {
                "action": log.action,
                "actor_type": log.actor_type,
                "created_at": log.created_at.isoformat(),
            }
            for log in recent_logs
        ]
    }

# routes/auth.py
@auth_router.post("/password-reset/request")
def request_password_reset(
    email: Optional[str] = Body(None),
    phone: Optional[str] = Body(None),
    request: Request = None,
    db: Session = Depends(get_db),
):
    """
    Route 1: Request password reset OTP
    Accepts email (for User/POSUser) OR phone (for POSUser only)
    """
    
    if not email and not phone:
        raise HTTPException(400, "Email or phone required")
    
    ip = request.client.host if request.client else ""
    ua = request.headers.get("user-agent")
    
    success, message, debug_otp = AuthService.request_password_reset(
        db=db,
        email=email,
        phone=phone,
        ip_address=ip,
        user_agent=ua,
    )
    
    if not success:
        raise HTTPException(400, detail=message)
    
    response = {
        "success": True,
        "message": message,
        "email": email,
        "phone": phone,
    }
        
    return response


@auth_router.post("/password-reset/verify")
def verify_password_reset(
    email: Optional[str] = Body(None),
    phone: Optional[str] = Body(None),
    otp: str = Body(...),
    new_password: str = Body(...),
    request: Request = None,
    db: Session = Depends(get_db),
):
    """
    Route 2: Verify OTP and reset password
    Accepts email OR phone + OTP + new password
    """
    
    if not email and not phone:
        raise HTTPException(400, "Email or phone required")
    
    ip = request.client.host if request.client else ""
    ua = request.headers.get("user-agent")
    
    success, message = AuthService.verify_and_reset_password(
        db=db,
        email=email,
        phone=phone,
        otp=otp,
        new_password=new_password,
        ip_address=ip,
        user_agent=ua,
    )
    
    if not success:
        raise HTTPException(400, detail=message)
    
    return {
        "success": True,
        "message": message,
        "email": email,
        "phone": phone,
    }

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

@auth_router.post("/logout", response_model=LogoutResponse)
def logout(
    request: Request,
    current_account_info: dict = Depends(get_current_account),  # CHANGED HERE
    db: Session = Depends(get_db)
):
    # Extract account object from the dict
    current_account = current_account_info['account']
    
    auth_header = request.headers.get("authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(400, "Invalid authorization header")
    
    token = auth_header.replace("Bearer ", "")
    AuthService.logout_user(db, current_account, token)
    
    return {"message": "Logged out successfully"}


@auth_router.post("/logout-all", response_model=LogoutResponse)
def logout_all(
    request: Request,  # Add this parameter
    current_account_info: dict = Depends(get_current_account),
    db: Session = Depends(get_db)
):
    """
    Log out from all machines
    """
    # Extract account object from the dict
    current_account = current_account_info['account']
    
    # Get token from request header (optional)
    access_token = ""
    auth_header = request.headers.get("authorization")
    if auth_header and auth_header.startswith("Bearer "):
        access_token = auth_header.replace("Bearer ", "")
    
    # Pass token only if it exists
    if access_token:
        AuthService.logout_all_devices(db, current_account, access_token)
    else:
        AuthService.logout_all_devices(db, current_account)  # No token parameter
    
    return {"message": "Logged out from all devices successfully"}

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
# @auth_router.get("/me", response_model=UserOut)
# def get_current_user_info(current_user: User = Depends(get_current_user)):
#     """
#     Get current user information
#     """
#     return UserOut.model_validate(current_user)
# CORRECT - should be:
@auth_router.get("/me")
async def get_current_user_info(
    current_user_info: Dict[str, Any] = Depends(get_current_user)
):
    """
    Handle User, POSUser, and Client accounts.
    Extract the account object from the dict and return appropriate data.
    """
    account_type = current_user_info.get("account_type")
    account = current_user_info.get("account")
    
    if not account or not account_type:
        raise HTTPException(status_code=401, detail="Invalid authentication data")
    
    # For ALL account types, extract the account object and use it
    if account_type == "user":
        # Use your existing UserOut schema for User objects
        from src.schemas.users import UserOut
        return UserOut.model_validate(account)
    
    elif account_type == "pos":
        # Handle POSUser
        return {
            "account_type": "pos",
            "id": account.id,
            "first_name": getattr(account, 'first_name', None),
            "last_name": getattr(account, 'last_name', None),
            "username": getattr(account, 'username', None),
            "email": getattr(account, 'email', None),
            "phone": getattr(account, 'phone', None),
            "status": getattr(account, 'status', None),
            "type": getattr(account, 'type', None),
            "is_active": getattr(account, 'is_active', True),
            "created_at": getattr(account, 'created_at', None),
            "updated_at": getattr(account, 'updated_at', None),
            "last_login": getattr(account, 'last_login', None)
        }
    
    elif account_type == "client":
        # Handle Client - this is your "partner_client"
        # Since Client has user-like attributes, you can either:
        # Option 1: Return Client-specific fields
        return {
            "account_type": "client",
            "id": account.id,
            "first_name": getattr(account, 'first_name', None),
            "last_name": getattr(account, 'last_name', None),
            "email": getattr(account, 'email', None),
            "phone": getattr(account, 'phone', None),
            "status": getattr(account, 'status', None),
            "type": getattr(account, 'type', None),
            "id_number": getattr(account, 'id_number', None),
            "current_balance": getattr(account, 'current_balance', 0),
            "created_at": getattr(account, 'created_at', None),
            "updated_at": getattr(account, 'updated_at', None),
            "last_login": getattr(account, 'last_login', None)
        }
    
    else:
        raise HTTPException(status_code=400, detail=f"Unknown account type: {account_type}")
    
def serialize_account(account):
    if isinstance(account, User):
        return UserSchema.model_validate(account)
    if isinstance(account, POSUser):
        return POSUserSchema.model_validate(account)
    if isinstance(account, Client):
        return ClientSchema.model_validate(account)
    raise ValueError("Unknown account type")
