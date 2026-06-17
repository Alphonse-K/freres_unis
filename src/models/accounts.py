from sqlalchemy import Column, Integer, String, Enum, Numeric, DateTime, ForeignKey, func, Boolean, Text
from sqlalchemy.orm import relationship
from src.core.database import Base
import enum

class AccountType(str, enum.Enum):
    INTERNAL_CASH = "internal_cash"
    EXTERNAL_ACCOUNT = "external_account"


class AccountSubType(str, enum.Enum):
    POS_CASH = "pos_cash"
    BANK = "bank"
    MOBILE_MONEY = "mobile_money"
    SAFE = "safe"
    TREASURY = "treasury"
    OTHER = "other"


class TransferStatus(str, enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    COMPLETED = "completed"


class TransferType(str, enum.Enum):
    POS_DEPOSIT = "pos_deposit"
    ACCOUNT_TRANSFER = "account_transfer"
    TREASURY_TRANSFER = "treasury_transfer"
    SUPPLIER_PAYMENT = "supplier_payment"
    CUSTOMER_REFUND = "customer_refund"
    CASH_WITHDRAWAL = "cash_withdrawal"


class Account(Base):
    __tablename__ = "accounts"

    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False, unique=True)
    type = Column(
        Enum(
            AccountType,
            values_callable=lambda x: [e.value for e in x]
        ), 
        nullable=False
    )
    sub_type = Column(
        Enum(
            AccountSubType,
            values_callable=lambda x: [e.value for e in x]
        ),
        nullable=True,
        default=AccountSubType.OTHER
    )
    account_number = Column(String(120), nullable=False, unique=True)
    remark = Column(String(255), nullable=True)
    balance = Column(Numeric(18, 2), nullable=False, default=0)
    is_active = Column(Boolean, default=True)
    added_by_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    added_by = relationship("User")

    # Updated: money movement relationships
    incoming_transfers = relationship(
        "FundTransfer",
        back_populates="destination_account",
        foreign_keys="FundTransfer.destination_account_id"
    )
    outgoing_transfers = relationship(
        "FundTransfer",
        back_populates="source_account",
        foreign_keys="FundTransfer.source_account_id"
    )

    def __repr__(self):
        return f"<Account {self.name} ({self.type}) bal={self.balance}>"


class FundTransfer(Base):
    __tablename__ = "fund_transfers"

    id = Column(Integer, primary_key=True)

    # MONEY MOVEMENT
    source_account_id = Column(
        Integer,
        ForeignKey("accounts.id"),
        nullable=True
    )

    destination_account_id = Column(
        Integer,
        ForeignKey("accounts.id"),
        nullable=False
    )

    amount = Column(
        Numeric(18, 2),
        nullable=False
    )

    transfer_type = Column(
        Enum(TransferType),
        nullable=False
    )

    status = Column(
        Enum(TransferStatus),
        nullable=False,
        default=TransferStatus.PENDING
    )

    note = Column(Text, nullable=True)

    # POS OPERATOR WHO CREATED REQUEST
    created_by_pos_user_id = Column(
        Integer,
        ForeignKey("pos_user.id"),
        nullable=True
    )

    # SYSTEM USER WHO APPROVED
    approved_by_user_id = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=True
    )

    # SYSTEM USER WHO REJECTED
    rejected_by_user_id = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=True
    )

    # SYSTEM USER WHO CANCELLED
    cancelled_by_user_id = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=True
    )

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now()
    )

    approved_at = Column(
        DateTime(timezone=True),
        nullable=True
    )

    rejected_at = Column(
        DateTime(timezone=True),
        nullable=True
    )

    cancelled_at = Column(
        DateTime(timezone=True),
        nullable=True
    )

    rejection_reason = Column(String(255), nullable=True)

    # RELATIONSHIPS
    source_account = relationship(
        "Account",
        foreign_keys=[source_account_id],
        back_populates="outgoing_transfers"
    )

    destination_account = relationship(
        "Account",
        foreign_keys=[destination_account_id],
        back_populates="incoming_transfers"
    )

    created_by_pos_user = relationship(
        "POSUser",
        foreign_keys=[created_by_pos_user_id]
    )

    approved_by_user = relationship(
        "User",
        foreign_keys=[approved_by_user_id]
    )

    rejected_by_user = relationship(
        "User",
        foreign_keys=[rejected_by_user_id]
    )

    cancelled_by_user = relationship(
        "User",
        foreign_keys=[cancelled_by_user_id]
    )