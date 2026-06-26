from fastapi import (
    APIRouter, 
    Depends, 
    status, 
    Query, 
    HTTPException, 
    Form, 
    UploadFile, 
    File, 
    Request
)
from sqlalchemy.orm import Session
from typing import Optional

from src.core.database import get_db
from src.schemas.users import PaginationParams, PaginatedResponse
from src.models.clients import (
    ClientApproval, 
    Client, 
    ClientStatus, 
    ClientReturn, 
    ClientRequest,
    # LoanStatus
)
from src.models.id import IDType
from src.models.clients import LedgerEntry
from src.models.users import User
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
    ClientResponseLight,
    TransferRequest,
    TransferResponse,
    ClientRequestBase,
    ClientRequestResponse,
    ClientRequestUpdate,
    ClientRequestReplyUpdate,
    ClientRequestReply,
    CardRequestCreate,
    ScanRequest,
    ScanResponse,
    # ClientCardResponse,
    # CardApproveRequest,
    CardRequestResponse,
    CardRequestCreate,
    ClientHeirCreate,
    ClientHeirUpdate,
    ClientHeirResponse,
    CardRequestResponse,
    CardPriceResponse,
    LoanRequestCreate,
    LoanResponse,
    ClientWithDebtResponse,
)
from src.schemas.ecommerce import (
    CartOut,
    OrderOut,
    OrderBeneficiaryInfoCreate,
)
from src.services.client_return_service import ClientReturnService
from typing import Annotated
from src.services.client_service import (
    ClientService, 
    CartService,
    OrderService,
    LedgerService,
    ClientCardService,
    ClientHeirService,
    CardPriceService,
    LoanService
)
from src.services.pos import POSService
from src.services.client_approval_service import ClientApprovalService
from src.core.security import SecurityUtils
from src.core.auth_dependencies import (
    optional_permission_for_client, 
    require_permission, 
    get_current_account,
    get_pos_id_or_none
)
from src.core.permissions import Permissions
from decimal import Decimal
from uuid import UUID


client_router = APIRouter(
    prefix="/clients",
    tags=["Clients"]
)

CanReadClient = Annotated[User, Depends(require_permission(Permissions.READ_CLIENT))]
DB = Annotated[Session, Depends(get_db)]

def get_user_company(current_user: CanReadClient) -> str:
    """Extracts and validates the connected user's company."""
    company = getattr(current_user, "company", None)
    if not company:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            detail="Your account is not associated with a company"
        )
    return company


CompanyUser = Annotated[str, Depends(get_user_company)]


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
    magnetic_card_number: Optional[str] = Form(None),
    company_address: Optional[str] = Form(None),
    company_id: int | None = Form(None),
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
        "magnetic_card_number": magnetic_card_number,
        "company_address": company_address,
        "company_id": company_id,
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

@client_router.post(
    "/card/{card_number}/validate",
    response_model=ClientLedgerResponse
)    
def validate_card(
    card_number: str, 
    amount: Decimal,
    db: Session = Depends(get_db),
    current_account = Depends(require_permission(Permissions.VALIDATE_CLIENT_CARD))
):
    print("current account: " , current_account)
    current_account = current_account
    return ClientService.validate_card(db, current_account.pos.id, card_number, amount)

@client_router.post(
    "/balance/{client_phone}/increment",
    response_model=ClientLedgerResponse
)
def increment_client_balance(
    client_phone: str, 
    amount: Decimal, 
    db: Session = Depends(get_db),
    current_account = Depends(require_permission(Permissions.INCREMENT_CLIENT_BALANCE))
):
    pos_user = get_pos_id_or_none(current_account)
    return ClientService.increment_client_balance(db, client_phone, amount, pos_user.pos.id)

@client_router.put(
    "/card-opening-balance/{client_id}/set",
    response_model=ClientResponse
)
def set_card_opening_balance(
    client_id: int, 
    amount: Decimal, 
    db: Session = Depends(get_db),
    current_account: Client = Depends(get_current_account)
):
    return ClientService.set_card_opening_balance(db, client_id, amount)

@client_router.post(
    "/transfer",
    response_model=TransferResponse,
    status_code=status.HTTP_200_OK
)
def transfer_balance(
    payload: TransferRequest,
    db: Session = Depends(get_db),
    current_client: Client = Depends(get_current_account)
):
    result = ClientService.balance_transfer_between_client(
        db=db,
        client_id=current_client["account"].id,
        phone=payload.phone,
        amount=payload.amount
    )
    return result

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
    current_user = Depends(optional_permission_for_client(Permissions.READ_CLIENT)),
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

@client_router.get("/company", response_model=PaginatedResponse[ClientResponse])
def list_clients_by_company(
    db: DB,
    company: CompanyUser,
    pagination: PaginationParams = Depends()
):
    total, items = ClientService.list_by_company(db, company, pagination)
    return PaginatedResponse(total=total, items=items)


@client_router.get("/company/{client_id}", response_model=ClientResponse)
def get_client_by_company(
    client_id: int,
    db: DB,
    company: CompanyUser,
):
    return ClientService.get_by_company(db, client_id, company)

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
@client_router.post(
    "/heir/create",
    response_model=ClientHeirResponse
)
def create_client_heir(
    data: ClientHeirCreate, 
    db: Session = Depends(get_db),
    current_user = Depends(optional_permission_for_client(Permissions.CREATE_CLIENT))
):
    return ClientHeirService.create_heir(db, data)

@client_router.put(
    "/heir/{heir_id}/update",
    response_model=ClientHeirResponse
)
def update_client_heir(
    heir_id, 
    data: ClientHeirUpdate, 
    db: Session = Depends(get_db),
    current_user = Depends(optional_permission_for_client(Permissions.CREATE_CLIENT))
):
    return ClientHeirService.update_heir(db, heir_id, data)

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
   "/order/{client_id}/warehouse/{warehouse_id}/create",
   response_model=OrderOut
)
def create_order(
    client_id: int, 
    warehouse_id: int, 
    pos_id: int,
    beneficiary:  OrderBeneficiaryInfoCreate | None = None,
    db: Session = Depends(get_db), 
    current_user = Depends(get_current_account)
):
    cart = CartService.get_or_create_cart(db, client_id, warehouse_id)    
    pos = POSService.get_pos(db, pos_id, include_warehouse=False)
    return OrderService.create_order(db, cart, pos, beneficiary)

@client_router.post(
        "/order/{order_code}/place-order",
        response_model=OrderOut
)
def checkout(
    order_code: str,
    db: Session = Depends(get_db), 
    current_user = Depends(get_current_account)
):
    order = OrderService.checkout_order(db, order_code)
    return order

@client_router.get(
        "/orders/{client_id}/client",
        response_model=list[OrderOut]
)
def client_orders(
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
        "/order/{order_code}/details",
        response_model=OrderOut
)
def get_order_details(
    order_code: str,
    db: Session = Depends(get_db), 
    current_user = Depends(get_current_account)
):
    order = OrderService.get_order_details(db, order_code)
    return order

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

@client_router.get(
    "/company/{client_id}/ledger", 
    response_model=PaginatedResponse[ClientLedgerResponse]
)
def list_client_ledger_by_company(
    client_id: int,
    db: DB,
    company: CompanyUser,
    pagination: PaginationParams = Depends()
):
    total, items = LedgerService.list_by_company(
        db, client_id, company,
        offset=pagination.offset,
        limit=pagination.page_size
    )
    return PaginatedResponse(total=total, items=items)


@client_router.get(
    "/company/{client_id}/ledger/{ledger_id}", 
    response_model=ClientLedgerResponse
)
def get_client_ledger_entry_by_company(
    client_id: int,
    ledger_id: int,
    db: DB,
    company: CompanyUser,
):
    # Verify client belongs to company first
    ClientService.get_by_company(db, client_id, company)

    entry = db.query(LedgerEntry).filter(
        LedgerEntry.id == ledger_id,
        LedgerEntry.client_id == client_id
    ).first()

    if not entry:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            detail="Ledger entry not found"
        )
    return entry


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
def cancel_return(
    return_id: int, 
    db: Session = Depends(get_db), 
    current_user = Depends(get_current_account)
):
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


@client_router.post(
    "/client-request/create",
    response_model=ClientRequestResponse,
)
def create_client_request(
    request: ClientRequestBase,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_account)
):
    return ClientService.create_client_request(
        db, 
        int(current_user["payload"]["sub"]), 
        request
    )


@client_router.put(
    "/client-request/{request_id}/update",
    response_model=ClientRequestResponse,
)
def update_client_request(
    request_id: int,
    request: ClientRequestUpdate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_account)
):
    return ClientService.update_client_request(
        db, 
        request_id, 
        request
    )


@client_router.patch(
    "/client-request/{request_id}/response",
    response_model=ClientRequestResponse,
)
def reply_client_request(
    request_id: int,
    request: ClientRequestReply,
    db: Session = Depends(get_db),
    current_user = Depends(require_permission(Permissions.CLIENT_REQUEST_REPLY))
):
    return ClientService.reply_client_request(
        db, 
        request_id, 
        current_user.id,
        request
    )


@client_router.put(
    "/client-request/{request_id}/update/reply",
    response_model=ClientRequestResponse,
)
def client_reply_request_update(
    request_id: int,
    request: ClientRequestReplyUpdate,
    db: Session = Depends(get_db),
    current_user = Depends(require_permission(Permissions.CLIENT_REQUEST_REPLY))
):
    return ClientService.client_reply_request_update(
        db, 
        request_id, 
        request
    )


@client_router.get(
    "/client-request/{client_id}/list",
    response_model=list[ClientRequestResponse],
)
def list_client_requests(
    client_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(optional_permission_for_client(Permissions.CLIENT_REQUEST_READ))
):
    return db.query(ClientRequest).filter_by(client_id=client_id).all()


@client_router.post("/cards/{client_id}/request", response_model=CardRequestResponse)
def request_card(
    client_id: int,
    data: CardRequestCreate,
    db: Session = Depends(get_db),
    current = Depends(optional_permission_for_client(Permissions.CARD_REQUEST))
):
    return ClientCardService.request_card(db, client_id, data)


@client_router.get(
    "/cards/request/list", 
response_model=PaginatedResponse[CardRequestResponse]
)
def list_card_request(
    pagination: PaginationParams = Depends(),
    db: Session = Depends(get_db),
    current_user = Depends(require_permission(Permissions.CLIENT_REQUEST_READ))
):
    total, items = ClientCardService.list_card_request(db, pagination)
    return {
        "total": total,
        "page": pagination.page,
        "page_size": pagination.page_size,
        "items": items
    }


@client_router.get(
    "/cards/request/{client_id}/get", 
response_model=CardRequestResponse
)
def get_card_request(
    client_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(require_permission(Permissions.CLIENT_REQUEST_READ))
):
    return ClientCardService.get_single_request(db, client_id)


@client_router.patch("/cards/request/{request_id}/approve")
def approve_request(
    request_id: int,
    db: Session = Depends(get_db),
    current = Depends(require_permission(Permissions.APPROVE_CLIENT))
):
    return ClientCardService.approve_request(db, request_id, current.id)


@client_router.put("/cards/request/{request_id}/reject")
def reject_request(
    request_id: int,
    reason: str | None,
    db: Session = Depends(get_db),
    current = Depends(require_permission(Permissions.APPROVE_CLIENT))
):
    return ClientCardService.reject_request(db, request_id, current.id, reason)


@client_router.post("/cards/scan", response_model=ScanResponse)
def scan_card(
    payload: ScanRequest,
    request: Request,
    db: Session = Depends(get_db),
    current = Depends(require_permission(Permissions.SCAN_QR_CODE))
):
    client = ClientCardService.scan_card(
        db,
        payload.token,
        agent_id=current.id,
        ip=request.client.host
    )

    return {
        "client_id": client.id,
        "balance": client.current_balance,
        "first_name": client.first_name,
        "last_name": client.last_name
    }


@client_router.get("/cards/{client_id}/get")
def get_client_card(
    client_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(optional_permission_for_client(Permissions.READ_CLIENT))
):
    return ClientCardService.get_client_card(db, client_id)


@client_router.post("/cards/{card_id}/revoke")
def revoke_card(
    card_id: str,
    db: Session = Depends(get_db),
    current = Depends(require_permission(Permissions.UPDATE_CLIENT))
):
    return ClientCardService.revoke_card(db, card_id)


@client_router.post("/card/create-card-price")
def create_card_price(
    amount: Decimal, 
    db: Session = Depends(get_db),
    current = Depends(require_permission(Permissions.CREATE_CLIENT))
):
    return CardPriceService.create(db, amount)


@client_router.get("/card/price", response_model=CardPriceResponse)
def get_card_price(
    db: Session = Depends(get_db),
    current = Depends(optional_permission_for_client(Permissions.READ_CLIENT))
):
    return CardPriceService.get_price(db)


@client_router.put("/card-price/{price_id}/update", response_model=CardPriceResponse)
def update_card_price(
    price_id: int, 
    amount: Decimal, 
    db: Session = Depends(get_db),
    current = Depends(require_permission(Permissions.CREATE_CLIENT))
):
    return CardPriceService.update(db, price_id, amount)

####################### LOAN ############################################
@client_router.post("/loans/request", response_model=LoanResponse)
def request_loan(
    client_id: int,
    data: LoanRequestCreate,
    db: Session = Depends(get_db),
    current_user = Depends(optional_permission_for_client(Permissions.LOAN_CREATE))
):
    return LoanService.request_loan(db, client_id, data)


@client_router.post("/loans/{loan_id}/approve", response_model=LoanResponse)
def approve_loan(
    loan_id: UUID,
    db: Session = Depends(get_db),
    user = Depends(require_permission(Permissions.LOAN_APPROVE))
):
    return LoanService.approve_loan(db, loan_id, user.id)


@client_router.get("/loans/list", response_model=PaginatedResponse[LoanResponse])
def list_loans(
    pagination: PaginationParams = Depends(),
    db: Session = Depends(get_db),
    user = Depends(require_permission(Permissions.LOAN_READ))
):
    total, loans = LoanService.list(db, pagination)
    return {
        "total": total,
        "page": pagination.page,
        "page_size": pagination.page_size,
        "items": loans
    }


@client_router.get("/loans/{client_id}/get", response_model=LoanResponse)
def get_client_request(
    client_id: int,
    db: Session = Depends(get_db),
    user = Depends(optional_permission_for_client(Permissions.LOAN_READ))
):
    return LoanService.get_client_requests(db, client_id)


@client_router.post("/loans/{loan_id}/reject")
def reject_loan(
    loan_id: UUID,
    reason: str | None,
    db: Session = Depends(get_db),
    user = Depends(require_permission(Permissions.LOAN_REJECT))
):
    return LoanService.reject_loan(db, loan_id, user.id, reason)


@client_router.get("/clients/{client_id}/financials", response_model=ClientWithDebtResponse)
def get_financials(client_id: int, db: Session = Depends(get_db)):
    return LoanService.get_client_financials(db, client_id)



