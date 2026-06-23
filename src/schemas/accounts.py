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
    name: Annotated[str, Field(min_length=2, max_length=255)]
    type: AccountType
    sub_type: AccountSubType | None = AccountSubType.OTHER
    account_number: Annotated[str, Field(min_length=2, max_length=120)]
    remark: Annotated[str, Field(max_length=255)] | None = None
    balance: NonNegativeAmount = Decimal("0")


class AccountUpdate(BaseModel):
    name: Annotated[str, Field(min_length=2, max_length=255)] = None
    sub_type: AccountSubType | None = None
    account_number: Annotated[str, Field(min_length=2, max_length=120)] = None
    remark: Annotated[str, Field(max_length=255)]= None
    is_active: Optional[bool] = None


class AccountResponse(BaseModel):
    id: int
    name: str
    type: AccountType
    sub_type: AccountSubType | None
    account_number: str
    remark: str | None
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
    source_account_id: int | None
    destination_account_id: int
    transfer_type: TransferType
    status: TransferStatus
    amount: Decimal
    note: str | None
    created_by_pos_user_id: int | None
    approved_by_user_id: int | None
    created_at: datetime
    approved_at: datetime | None
    model_config = ConfigDict(from_attributes=True)

# =========================
# POS -> ACCOUNT
# =========================

class POSToAccountTransferCreate(BaseModel):
    destination_account_id: PositiveIntId
    amount: PositiveAmount
    note: Annotated[str, Field(max_length=255)]= None


# =========================
# ACCOUNT -> ACCOUNT
# =========================

class AccountToAccountTransferCreate(BaseModel):
    source_account_id: PositiveIntId
    destination_account_id: PositiveIntId
    amount: PositiveAmount
    note: Annotated[str, Field(max_length=255)] = None


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