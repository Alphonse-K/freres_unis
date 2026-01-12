from sqlalchemy import Column, Integer, String, Enum, Numeric, DateTime, ForeignKey, func, Boolean
from sqlalchemy.orm import relationship
from src.core.database import Base
import enum


class AccountType(str, enum.Enum):
    INTERNAL_CASH = "caisse_interne"
    EXTERNAL_ACCOUNT = "compte_externe"


class AccountSubType(str, enum.Enum):
    BANK = "bank"
    MOBILE_MONEY = "mobile_money"
    OTHER = "other"


class Account(Base):
    __tablename__ = "accounts"

    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False, unique=True)

    type = Column(Enum(AccountType), nullable=False)
    sub_type = Column(Enum(AccountSubType), nullable=True, default=AccountSubType.OTHER)

    account_number = Column(String(120), nullable=False, unique=True)
    remark = Column(String(255), nullable=True)

    balance = Column(Numeric(18, 2), nullable=False, default=0)
    is_active = Column(Boolean, default=True)

    added_by_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    added_by = relationship("User")
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Updated: money movement relationships
    transfers_in = relationship(
        "FundTransfer",
        back_populates="destination_account",
        foreign_keys="FundTransfer.destination_account_id"
    )
    transfers_out = relationship(
        "FundTransfer",
        back_populates="source_account",
        foreign_keys="FundTransfer.source_account_id"
    )

    def __repr__(self):
        return f"<Account {self.name} ({self.type}) bal={self.balance}>"


class FundTransfer(Base):
    __tablename__ = "fund_transfers"

    id = Column(Integer, primary_key=True)

    # Still linked to POS for traceability, but conceptually not owned by POS
    pos_id = Column(Integer, ForeignKey("pos.id"), nullable=False)

    # source can be a POS till (null account) OR another account
    source_account_id = Column(Integer, ForeignKey("accounts.id"), nullable=True)
    destination_account_id = Column(Integer, ForeignKey("accounts.id"), nullable=False)

    amount = Column(Numeric(18, 2), nullable=False)

    approved_by_id = Column(Integer, ForeignKey("pos_user.id"), nullable=True)
    approved_by = relationship("POSUser", foreign_keys=[approved_by_id])

    created_by_id = Column(Integer, ForeignKey("pos_user.id"), nullable=False)
    created_by = relationship("POSUser", foreign_keys=[created_by_id])

    transfer_date = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    status = Column(String(40), default="completed")  # can become Enum later

    # Updated: account relationships
    source_account = relationship(
        "Account",
        back_populates="transfers_out",
        foreign_keys=[source_account_id]
    )
    destination_account = relationship(
        "Account",
        back_populates="transfers_in",
        foreign_keys=[destination_account_id]
    )

    def __repr__(self):
        return f"<FundTransfer POS={self.pos_id} {self.amount} from={self.source_account_id} to={self.destination_account_id}>"


class OrderAccountCredit(Base):
    __tablename__ = "order_account_credits"

    id = Column(Integer, primary_key=True)
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=False)
    account_id = Column(Integer, ForeignKey("accounts.id"), nullable=False)

    order_reference = Column(String(50), nullable=False)
    amount = Column(Numeric(18, 2), nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    client = relationship("Client")
    account = relationship("Account")

    def __repr__(self):
        return f"<OrderAccountCredit order={self.order_reference} +{self.amount} -> account={self.account_id}>"
