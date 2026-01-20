# src/routes/clients.py
from fastapi import APIRouter, Depends, status, Query, HTTPException, Form, UploadFile, File
from sqlalchemy.orm import Session
from typing import Optional
from src.core.database import get_db
from src.schemas.users import PaginationParams, PaginatedResponse, UserRole
from src.models.clients import ClientApproval, ClientPayment, Client, ClientStatus
from src.schemas.clients import (
    ClientResponse,
    ClientUpdate,
    ClientApprovalCreate,
    ClientApprovalUpdate,
    ClientApprovalResponse,
    ClientInvoiceCreate,
    ClientInvoiceResponse,
    ClientPaymentCreate,
    ClientPaymentResponse,
    ClientReturnCreate,
    ClientReturnResponse,
    ClientReturnFilter,
    ClientActivationSetPassword
)
from src.services.client_return_service import ClientReturnService

from src.services.client_service import ClientService
from src.services.client_approval_service import ClientApprovalService
from src.services.client_invoice_service import ClientInvoiceService
from src.services.client_payment_service import ClientPaymentService
from src.core.security import SecurityUtils
from src.core.auth_dependencies import require_role, get_current_user, get_current_account

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
    username: str = Form(...),
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
    data = {
        "type": type,
        "first_name": first_name,
        "last_name": last_name,
        "username": username,
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
    dependencies=[Depends(require_role(["ADMIN", "COMPLIANCE"]))],
)
def list_client_approvals(db: Session = Depends(get_db)):
    return db.query(ClientApproval).order_by(
        ClientApproval.submitted_at.desc()
    ).all()

# -----------------------------
# REVIEW CLIENT APPROVAL
# -----------------------------
@client_router.patch(
    "/approvals/{approval_id}",
    response_model=ClientApprovalResponse,
    dependencies=[Depends(require_role([UserRole.ADMIN, UserRole.RH]))],
    status_code=status.HTTP_200_OK,
)
def review_client_approval(
    approval_id: int,
    review: ClientApprovalUpdate,
    db: Session = Depends(get_db),
    current_account: dict = Depends(get_current_account),
):
    """
    Review a client approval (approve / reject).
    Only system users (admin or RH) can do this.
    """

    account_type = current_account["account_type"]
    account = current_account["account"]

    # Only 'user' accounts can review approvals
    if account_type != "user":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only system users can review client approvals"
        )

    return ClientApprovalService.review(
        db=db,
        approval_id=approval_id,
        review=review,
        reviewer_id=account.id,
    )

@client_router.get(
    "/{client_id}",
    response_model=ClientResponse,
    dependencies=[Depends(require_role(["ADMIN", "CHECKER", "RH", "MAKER"]))]
)
def get_client(
    client_id: int,
    db: Session = Depends(get_db),
):
    return ClientService.get(db, client_id)


@client_router.get(
    "",
    response_model=PaginatedResponse[ClientResponse],
    dependencies=[Depends(require_role(["ADMIN", "CHECKER", "RH", "MAKER"]))]
)
def list_clients(
    pagination: PaginationParams = Depends(),
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
    dependencies=[Depends(require_role(["ADMIN", "RH"]))]
)
def update_client(
    client_id: int,
    data: ClientUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
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
    dependencies=[Depends(require_role(["ADMIN", "RH"]))]
)
def change_client_status(
    client_id: int,
    status,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
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
    "/{client_id}/invoices",
    response_model=ClientInvoiceResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_role(["ADMIN", "FINANCE"]))]
)
def create_client_invoice(
    client_id: int,
    data: ClientInvoiceCreate,
    db: Session = Depends(get_db),
):
    return ClientInvoiceService.create(db, data)

@client_router.get(
    "/{client_id}/invoices",
    response_model=list[ClientInvoiceResponse],
    dependencies=[Depends(require_role(["ADMIN", "FINANCE", "RH"]))]
)
def list_client_invoices(
    client_id: int,
    db: Session = Depends(get_db),
):
    return ClientInvoiceService.list_by_client(db, client_id)

@client_router.post(
    "/{client_id}/payments",
    response_model=ClientPaymentResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_role(["ADMIN", "FINANCE", "CASHIER"]))]
)
def create_client_payment(
    client_id: int,
    data: ClientPaymentCreate,
    db: Session = Depends(get_db),
):
    return ClientPaymentService.create(db, data)

@client_router.get(
    "/{client_id}/payments",
    response_model=list[ClientPaymentResponse],
    dependencies=[Depends(require_role(["ADMIN", "FINANCE", "SUPPORT"]))]
)
def list_client_payments(
    client_id: int,
    db: Session = Depends(get_db),
):
    return (
        db.query(ClientPayment)
        .filter_by(client_id=client_id)
        .order_by(ClientPayment.payment_date.desc())
        .all()
    )

@client_router.post(
    "/client-returns",
    response_model=ClientReturnResponse,
)
def create_client_return(
    payload: ClientReturnCreate,
    db: Session = Depends(get_db),
):
    return ClientReturnService.create_return(db, payload)


@client_router.get(
    "/client-returns",
    response_model=PaginatedResponse[ClientReturnResponse],
    dependencies=[Depends(require_role(["ADMIN", "CHECKER", "MANAGER"]))],
)
def list_client_returns(
    filters: ClientReturnFilter = Depends(),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, le=100),
    db: Session = Depends(get_db),
):
    offset = (page - 1) * page_size
    total, items = ClientReturnService.list_returns(
        db, filters, offset, page_size
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
    dependencies=[Depends(require_role(["ADMIN", "CHECKER", "MANAGER"]))],
)
def get_client_return(
    return_id: int,
    db: Session = Depends(get_db),
):
    return ClientReturnService.get_return(db, return_id)

@client_router.post(
    "/client-returns/{return_id}/approve",
    response_model=ClientReturnResponse,
    dependencies=[Depends(require_role(["ADMIN", "CHECKER"]))],
)
def approve_client_return(
    return_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return ClientReturnService.approve_return(
        db=db,
        return_id=return_id,
        approver_id=current_user.id,
    )

@client_router.post(
    "/client-returns/{return_id}/reject",
    response_model=ClientReturnResponse,
    dependencies=[Depends(require_role(["ADMIN", "CHECKER"]))],
)
def reject_client_return(
    return_id: int,
    reason: str,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return ClientReturnService.reject_return(
        db, return_id, current_user.id, reason
    )

