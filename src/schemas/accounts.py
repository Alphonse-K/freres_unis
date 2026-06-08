from datetime import datetime
from decimal import Decimal
from typing import Optional, Annotated

from pydantic import BaseModel, ConfigDict, Field

from src.models.accounts import (
    AccountType,
    AccountSubType,
    TransferStatus,
    TransferType
)

# =========================
# REUSABLE TYPES
# =========================

PositiveAmount = Annotated[
    Decimal,
    Field(gt=0, decimal_places=2)
]

NonNegativeAmount = Annotated[
    Decimal,
    Field(ge=0, decimal_places=2)
]

PositiveIntId = Annotated[
    int,
    Field(gt=0)
]


# =========================
# ACCOUNT SCHEMAS
# =========================

class AccountCreate(BaseModel):
    name: Annotated[
        str,
        Field(min_length=2, max_length=255)
    ]

    type: AccountType

    sub_type: Optional[AccountSubType] = AccountSubType.OTHER

    account_number: Annotated[
        str,
        Field(min_length=2, max_length=120)
    ]

    remark: Optional[
        Annotated[str, Field(max_length=255)]
    ] = None

    balance: NonNegativeAmount = Decimal("0")


class AccountUpdate(BaseModel):
    name: Optional[
        Annotated[str, Field(min_length=2, max_length=255)]
    ] = None

    sub_type: Optional[AccountSubType] = None

    account_number: Optional[
        Annotated[str, Field(min_length=2, max_length=120)]
    ] = None

    remark: Optional[
        Annotated[str, Field(max_length=255)]
    ] = None

    is_active: Optional[bool] = None


class AccountResponse(BaseModel):
    id: int
    name: str
    type: AccountType
    sub_type: Optional[AccountSubType]
    account_number: str
    remark: Optional[str]
    balance: Decimal
    is_active: bool
    added_by_id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# =========================
# FUND TRANSFER SCHEMAS
# =========================

class FundTransferResponse(BaseModel):
    id: int

    pos_id: Optional[int]

    source_account_id: Optional[int]
    destination_account_id: int

    transfer_type: TransferType
    status: TransferStatus

    amount: Decimal
    note: Optional[str]

    created_by_pos_user_id: Optional[int]
    created_by_user_id: Optional[int]

    approved_by_user_id: Optional[int]

    transfer_date: datetime
    approved_at: Optional[datetime]

    model_config = ConfigDict(from_attributes=True)


# =========================
# POS -> ACCOUNT
# =========================

class POSToAccountTransferCreate(BaseModel):
    destination_account_id: PositiveIntId

    amount: PositiveAmount

    note: Optional[
        Annotated[str, Field(max_length=255)]
    ] = None


# =========================
# ACCOUNT -> ACCOUNT
# =========================

class AccountToAccountTransferCreate(BaseModel):
    source_account_id: PositiveIntId

    destination_account_id: PositiveIntId

    amount: PositiveAmount

    note: Optional[
        Annotated[str, Field(max_length=255)]
    ] = None


# =========================
# APPROVAL
# =========================

class TransferApprove(BaseModel):
    approved: bool

class TransferReject(BaseModel):
    reason: Annotated[
        str,
        Field(min_length=3, max_length=255)
    ]