# src/routes/clients.py
from fastapi import APIRouter, Depends, status, Query, HTTPException, Form, UploadFile, File
from sqlalchemy.orm import Session
from typing import Optional, List
from src.core.database import get_db
from src.schemas.users import PaginationParams, PaginatedResponse, UserRole
from src.models.clients import ClientApproval, Client, ClientStatus, ClientReturn
from src.models.id import IDType
from src.schemas.clients import (
    ClientResponse,
    ClientUpdate,
    ClientApprovalUpdate,
    ClientApprovalResponse,
    ClientReturnCreate,
    ClientReturnResponse,
    ClientReturnFilter,
    ClientActivationSetPassword,
    ClientLedgerResponse,
    ClientResponseLight
)
from src.schemas.ecommerce import (
    CartOut,
    OrderOut
)
from src.services.client_return_service import ClientReturnService

from src.services.client_service import (
    ClientService, 
    CartService,
    OrderService,
    LedgerService
)
from src.services.pos import POSService
from src.services.client_approval_service import ClientApprovalService
from src.core.security import SecurityUtils
from src.core.auth_dependencies import optional_permission_for_client, require_permission, get_current_account
from src.core.permissions import Permissions
from decimal import Decimal

client_router = APIRouter(
    prefix="/clients",
    tags=["Clients"]
)


# -----------------------------
# SUBMIT CLIENT APPROVAL (WITH FILES)
# -----------------------------
@client_router.post(
    "/approvals",
    response_model=ClientApprovalResponse,
    status_code=status.HTTP_201_CREATED,
)
def submit_client_approval(
    type: str = Form(...),
    first_name: str = Form(...),
    last_name: str = Form(...),
    phone: str = Form(...),
    email: Optional[str] = Form(None),
    id_type_id: int = Form(...),
    id_number: str = Form(...),
    employee_company: Optional[str] = Form(None),
    employee_id_number: Optional[str] = Form(None),
    company_address: Optional[str] = Form(None),
    face_photo: UploadFile = File(...),
    id_photo_recto: UploadFile = File(...),
    id_photo_verso: UploadFile = File(...),
    badge_photo: Optional[UploadFile] = File(None),
    magnetic_card_photo: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db),
):
    
    card_id = db.query(IDType).filter_by(id=id_type_id).first()
    if not card_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"ID {id_type_id} not found"
        )
    
    data = {
        "type": type,
        "first_name": first_name,
        "last_name": last_name,
        "phone": phone,
        "email": email,
        "id_type_id": id_type_id,
        "id_number": id_number,
        "employee_company": employee_company,
        "employee_id_number": employee_id_number,
        "company_address": company_address,
    }

    files = {
        "face_photo": face_photo,
        "id_photo_recto": id_photo_recto,
        "id_photo_verso": id_photo_verso,
        "badge_photo": badge_photo,
        "magnetic_card_photo": magnetic_card_photo,
    }

    return ClientApprovalService.submit_with_files(db=db, data=data, files=files)

# -----------------------------
# LIST CLIENT APPROVALS
# -----------------------------
@client_router.get(
    "/approvals",
    response_model=list[ClientApprovalResponse],
)
def list_client_approvals(db: Session = Depends(get_db), current_user = Depends(require_permission(Permissions.READ_CLIENT))):
    return db.query(ClientApproval).order_by(
        ClientApproval.submitted_at.desc()
    ).all()


@client_router.get(
        "/phone/{phone}",
        response_model=ClientResponseLight
)
def get_client_by_number(
    phone: str,
    db: Session = Depends(get_db), 
):
    client = db.query(Client).filter_by(phone=phone).first()
    if not client:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Client with {phone} not found"
        )
    
    if not client.approval:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Approval not found"
        )
    
    return client
    
# -----------------------------
# REVIEW CLIENT APPROVAL
# -----------------------------
@client_router.patch(
    "/approvals/{approval_id}",
    response_model=ClientApprovalResponse,
    status_code=status.HTTP_200_OK,
)
def review_client_approval(
    approval_id: int,
    review: ClientApprovalUpdate,
    db: Session = Depends(get_db),
    current_account = Depends(require_permission(Permissions.APPROVE_CLIENT)),
):
    """
    Review a client approval (approve / reject).
    Only system users (admin or RH) can do this.
    """
    
    return ClientApprovalService.review(
        db=db,
        approval_id=approval_id,
        review=review,
        reviewer_id=current_account.id,
    )

@client_router.get(
    "/{client_id}",
    response_model=ClientResponse,
)
def get_client(
    client_id: int,
    currrent_user = Depends(require_permission(Permissions.READ_CLIENT)),
    db: Session = Depends(get_db),
):
    return ClientService.get(db, client_id)


@client_router.get(
    "",
    response_model=PaginatedResponse[ClientResponse],
)
def list_clients(
    pagination: PaginationParams = Depends(),
    current_user = Depends(require_permission(Permissions.READ_CLIENT)),
    db: Session = Depends(get_db),
):
    total, items = ClientService.list(db, pagination)
    return {
        "total": total,
        "page": pagination.page,
        "page_size": pagination.page_size,
        "items": items,
    }

@client_router.patch(
    "/{client_id}",
    response_model=ClientResponse,
)
def update_client(
    client_id: int,
    data: ClientUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(require_permission(Permissions.UPDATE_CLIENT)),
):
    return ClientService.update(
        db=db,
        client_id=client_id,
        data=data,
        actor_id=current_user.id,
    )

@client_router.patch(
    "/{client_id}/status",
    response_model=ClientResponse,
)
def change_client_status(
    client_id: int,
    status,
    db: Session = Depends(get_db),
    current_user=Depends(require_permission(Permissions.UPDATE_CLIENT)),
):
    return ClientService.change_status(
        db=db,
        client_id=client_id,
        status=status,
        actor_id=current_user.id,
    )

@client_router.post("/clients/{phone}/activate")
def activate_client(
    phone: str,
    data: ClientActivationSetPassword,
    db: Session = Depends(get_db),
):
    client = db.query(Client).filter_by(phone=phone).first()
    if not client:
        raise HTTPException(404, "Client not found")
    
    # Check if client is already active
    if client.status == ClientStatus.ACTIVE:
        raise HTTPException(
            status_code=400, 
            detail="Client is already active"
        )
    
    if client.status == ClientStatus.INACTIVE:  # If you have a PENDING status
        client.password_hash = SecurityUtils.hash_password(data.password)
        client.pin_hash = SecurityUtils.hash_password(data.pin)
        client.status = ClientStatus.ACTIVE

        db.commit()
        return {"status": "Client activated successfully !"}
    
    else:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot activate client with status: {client.status}"
        )

@client_router.get(
    "/cart/{client_id}/warehouse/{warehouse_id}",
    response_model=CartOut
)
def get_cart(
    client_id: int,
    warehouse_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_account)
):
    cart = CartService.get_or_create_cart(db, client_id, warehouse_id)
    return CartService.build_cart_response(db, cart)

@client_router.post(
    "/cart/{client_id}/warehouse/{warehouse_id}/add/{product_variant_id}",
    response_model=CartOut
)
def add_to_cart(
    client_id: int,
    warehouse_id: int,
    product_variant_id: int,
    qty: Decimal,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_account)
):
    cart = CartService.add_item(
        db,
        client_id,
        warehouse_id,
        product_variant_id,
        qty
    )
    return CartService.build_cart_response(db, cart)

@client_router.delete(
    "/cart/{client_id}/warehouse/{warehouse_id}/remove/{product_variant_id}",
    response_model=CartOut
)
def remove_from_cart(
    client_id: int,
    warehouse_id: int,
    product_variant_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_account)
):
    cart = CartService.remove_item(
        db,
        client_id,
        warehouse_id,
        product_variant_id
    )
    return CartService.build_cart_response(db, cart)

@client_router.post(
    "/cart/{client_id}/warehouse/{warehouse_id}/clear"
)
def clear_cart(
    client_id: int,
    warehouse_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_account)
):
    return CartService.clear_cart(
        db,
        client_id,
        warehouse_id
    )

@client_router.post(
        "/cart/{client_id}/warehouse/{warehouse_id}/place-order",
        response_model=OrderOut
)
def checkout(
    client_id: int, 
    warehouse_id: int, 
    pos_id: int, 
    db: Session = Depends(get_db), 
    current_user = Depends(get_current_account)
):
    cart = CartService.get_or_create_cart(db, client_id, warehouse_id)    
    pos = POSService.get_pos(db, pos_id, include_warehouse=False)
    order = OrderService.checkout_cart(db, cart, pos)
    return order

@client_router.get(
        "/orders/{client_id}/client",
        response_model=list[OrderOut]
)
def client_oders(
    client_id: int, 
    offset: int | None = 1, 
    limit: int | None = 20, 
    db: Session = Depends(get_db), 
    current_user = Depends(get_current_account)
):
    client = db.query(Client).filter_by(id=client_id).first()
    if not client:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Order {client_id} not found"
        )
    offset =(offset - 1) * limit
    return OrderService.list_client_order(db, client, offset, limit)

@client_router.get(
    "/{client_id}/ledger/paginated",
    response_model=PaginatedResponse[ClientLedgerResponse],
)
def get_client_ledger_paginated(
    client_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, le=100),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_account)

):
    offset = (page - 1) * page_size

    total, items = LedgerService.list_paginated(
        db, client_id, offset, page_size
    )
    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": items,
    }
        
@client_router.post(
    "/client-returns",
    response_model=ClientReturnResponse,
)
def create_client_return(
    payload: ClientReturnCreate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_account)
):
    return ClientReturnService.create_return(db, payload)

@client_router.get(
    "/client-returns/{client_id}",
    response_model=PaginatedResponse[ClientReturnResponse],
)
def list_client_returns(
    filters: ClientReturnFilter = Depends(),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, le=100),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_account)
):
    offset = (page - 1) * page_size
    total, items = ClientReturnService.list_returns(
        db, filters, current_user, offset, page_size
    )

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": items,
    }

@client_router.get(
    "/client-returns/{return_id}/client-returns",
    response_model=ClientReturnResponse,
)
def get_client_return(
    return_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_account)
):
    return ClientReturnService.get_return(db, return_id)

@client_router.post(
        "/client-return/{return_id}/cancel"
)
def cancel_return(return_id: int, db: Session = Depends(get_db), current_user = Depends(get_current_account)):
    client_return = db.query(ClientReturn).filter_by(id=return_id).first()
    if not client_return:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Return not found"
        )
    return ClientReturnService.cancel_return(db, client_return, client_return.client)
    
@client_router.post(
    "/client-returns/{return_id}/approve",
    response_model=ClientReturnResponse,
)
def approve_client_return(
    return_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(require_permission(Permissions.APPROVE_CLIENT_RETURN))
):
    return ClientReturnService.approve_return(
        db=db,
        return_id=return_id,
        approver_by=current_user
    )

@client_router.post(
    "/client-returns/{return_id}/reject",
    response_model=ClientReturnResponse,
)
def reject_client_return(
    return_id: int,
    reason: str,
    db: Session = Depends(get_db),
    current_user = Depends(require_permission(Permissions.REJECT_CLIENT_RETURN))
):
    return ClientReturnService.reject_return(
        db, return_id, current_user, reason
    )

