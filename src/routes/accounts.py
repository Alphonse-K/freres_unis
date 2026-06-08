from typing import Optional, List, Annotated

from fastapi import (
    APIRouter,
    Depends,
    Query,
    Path,
    status
)

from sqlalchemy.orm import Session

from src.core.database import get_db

from src.models.accounts import (
    AccountType,
    AccountSubType
)

from src.models.users import User
from src.models.pos import POSUser
from src.schemas.accounts import (
    AccountCreate,
    AccountUpdate,
    AccountResponse,
    POSToAccountTransferCreate,
    AccountToAccountTransferCreate,
    FundTransferResponse,
    TransferReject
)
from src.services.account_service import (
    AccountService,
    FundTransferService
)

from src.core.auth_dependencies import (
    get_current_account
)

router = APIRouter(
    prefix="/accounts",
    tags=["System Accounts & Fund Transfers"]
)

# =========================================================
# ACCOUNT ROUTES
# =========================================================

@router.post(
    "/",
    response_model=AccountResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create account"
)
def create_account(
    data: AccountCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_account)
):
    return AccountService.create_account(
        db,
        data,
        current_user
    )


@router.get(
    "/",
    response_model=List[AccountResponse],
    summary="List accounts"
)
def list_accounts(
    account_type: Annotated[
        Optional[AccountType],
        Query(description="Filter by account type")
    ] = None,

    sub_type: Annotated[
        Optional[AccountSubType],
        Query(description="Filter by account subtype")
    ] = None,

    is_active: Annotated[
        Optional[bool],
        Query(description="Filter active/inactive accounts")
    ] = None,

    limit: Annotated[
        int,
        Query(ge=1, le=200)
    ] = 100,

    offset: Annotated[
        int,
        Query(ge=0)
    ] = 0,

    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_account)
):
    return AccountService.list_accounts(
        db,
        account_type,
        sub_type,
        is_active,
        limit,
        offset
    )


@router.get(
    "/{account_id}",
    response_model=AccountResponse,
    summary="Get account"
)
def get_account(
    account_id: Annotated[
        int,
        Path(gt=0)
    ],
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_account)
):
    return AccountService.get_account(
        db,
        account_id
    )


@router.patch(
    "/{account_id}",
    response_model=AccountResponse,
    summary="Update account"
)
def update_account(
    account_id: Annotated[
        int,
        Path(gt=0)
    ],
    data: AccountUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_account)
):
    return AccountService.update_account(
        db,
        account_id,
        data
    )


@router.delete(
    "/{account_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete account"
)
def delete_account(
    account_id: Annotated[
        int,
        Path(gt=0)
    ],
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_account)
):
    AccountService.delete_account(
        db,
        account_id
    )


# =========================================================
# TRANSFER ROUTES
# =========================================================

# ---------------------------------------------------------
# POS -> ACCOUNT
# ---------------------------------------------------------

@router.post(
    "/transfers/pos-to-account",
    response_model=FundTransferResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create POS to account transfer request"
)
def pos_to_account_transfer(
    data: POSToAccountTransferCreate,
    db: Session = Depends(get_db),
    current_user: POSUser = Depends(get_current_account)
):
    return FundTransferService.create_pos_transfer(
        db,
        current_user,
        data
    )


# ---------------------------------------------------------
# ACCOUNT -> ACCOUNT
# ---------------------------------------------------------

@router.post(
    "/transfers/account-to-account",
    response_model=FundTransferResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create account to account transfer"
)
def account_to_account_transfer(
    data: AccountToAccountTransferCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_account)
):
    return FundTransferService.create_account_transfer(
        db,
        current_user,
        data
    )


# ---------------------------------------------------------
# APPROVE TRANSFER
# ---------------------------------------------------------

@router.patch(
    "/transfers/{transfer_id}/approve",
    response_model=FundTransferResponse,
    summary="Approve transfer"
)
def approve_transfer(
    transfer_id: Annotated[
        int,
        Path(gt=0)
    ],
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_account)
):
    return FundTransferService.approve_transfer(
        db,
        transfer_id,
        current_user
    )


# ---------------------------------------------------------
# REJECT TRANSFER
# ---------------------------------------------------------

@router.patch(
    "/transfers/{transfer_id}/reject",
    response_model=FundTransferResponse,
    summary="Reject transfer"
)
def reject_transfer(
    transfer_id: Annotated[
        int,
        Path(gt=0)
    ],
    data: TransferReject,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_account)
):
    return FundTransferService.reject_transfer(
        db,
        transfer_id,
        current_user,
        data
    )

# ---------------------------------------------------------
# LIST TRANSFERS
# ---------------------------------------------------------

@router.get(
    "/transfers",
    response_model=List[FundTransferResponse],
    summary="List transfers"
)
def list_transfers(
    limit: Annotated[
        int,
        Query(ge=1, le=200)
    ] = 100,

    offset: Annotated[
        int,
        Query(ge=0)
    ] = 0,

    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_account)
):
    return FundTransferService.list_transfers(
        db,
        limit,
        offset
    )


# ---------------------------------------------------------
# GET SINGLE TRANSFER
# ---------------------------------------------------------

@router.get(
    "/transfers/{transfer_id}",
    response_model=FundTransferResponse,
    summary="Get transfer details"
)
def get_transfer(
    transfer_id: Annotated[
        int,
        Path(gt=0)
    ],
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_account)
):
    return FundTransferService.get_transfer(
        db,
        transfer_id
    )