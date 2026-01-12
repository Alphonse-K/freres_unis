# src/schemas/account.py
from pydantic import BaseModel, ConfigDict
from typing import Optional, List
from decimal import Decimal
from datetime import datetime

class AccountBase(BaseModel):
    name: str
    type: str
    sub_type: Optional[str] = "other"
    account_number: str
    remark: Optional[str] = None
    balance: Optional[Decimal] = 0
    is_active: Optional[bool] = True

class AccountCreate(AccountBase):
    added_by_id: int

class AccountOut(AccountBase):
    id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class FundTransferBase(BaseModel):
    pos_id: int
    source_account_id: Optional[int] = None
    destination_account_id: int
    amount: Decimal
    approved_by_id: Optional[int] = None
    created_by_id: int
    status: Optional[str] = "completed"

class FundTransferCreate(FundTransferBase):
    pass

class FundTransferOut(FundTransferBase):
    id: int
    transfer_date: datetime

    model_config = ConfigDict(from_attributes=True)


class OrderAccountCreditBase(BaseModel):
    client_id: int
    account_id: int
    order_reference: str
    amount: Decimal

class OrderAccountCreditCreate(OrderAccountCreditBase):
    pass

class OrderAccountCreditOut(OrderAccountCreditBase):
    id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
