from typing import Optional, List

from sqlalchemy.orm import Session
from sqlalchemy import desc, or_
from src.models.pos import POS
from src.models.clients import Client
from src.models.pos import POSUser
from decimal import Decimal
from datetime import datetime, timezone
from src.models.users import User

from src.models.accounts import (
    Account,
    FundTransfer,
    AccountType,
    AccountSubType,
    FundTransfer,
    TransferType,
    TransferStatus
)

from src.schemas.accounts import (
    AccountCreate,
    AccountUpdate,
    POSToAccountTransferCreate,
    AccountToAccountTransferCreate,
    TransferReject
)

from src.core.custom_exceptions import (
    BusinessRuleException,
    NotFoundException
)


class AccountService:

    @staticmethod
    def create_account(
        db: Session,
        data: AccountCreate,
        current_user
    ) -> Account:

        existing_name = db.query(Account).filter(
            Account.name == data.name
        ).first()

        if existing_name:
            raise BusinessRuleException(
                f"Account with name '{data.name}' already exists"
            )

        existing_number = db.query(Account).filter(
            Account.account_number == data.account_number
        ).first()

        if existing_number:
            raise BusinessRuleException(
                f"Account number '{data.account_number}' already exists"
            )

        account = Account(
            name=data.name,
            type=data.type,
            sub_type=data.sub_type,
            account_number=data.account_number,
            remark=data.remark,
            balance=data.balance,
            added_by_id=current_user["account"].id
        )

        db.add(account)
        db.commit()
        db.refresh(account)

        return account

    @staticmethod
    def get_account(
        db: Session,
        account_id: int
    ) -> Account:

        account = db.query(Account).filter(
            Account.id == account_id
        ).first()

        if not account:
            raise NotFoundException(
                f"Account {account_id} not found"
            )

        return account

    @staticmethod
    def list_accounts(
        db: Session,
        account_type: Optional[AccountType] = None,
        sub_type: Optional[AccountSubType] = None,
        is_active: Optional[bool] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Account]:

        query = db.query(Account)

        if account_type:
            query = query.filter(
                Account.type == account_type
            )

        if sub_type:
            query = query.filter(
                Account.sub_type == sub_type
            )

        if is_active is not None:
            query = query.filter(
                Account.is_active == is_active
            )

        return (
            query
            .order_by(desc(Account.created_at))
            .offset(offset)
            .limit(limit)
            .all()
        )

    @staticmethod
    def update_account(
        db: Session,
        account_id: int,
        data: AccountUpdate
    ) -> Account:

        account = AccountService.get_account(
            db,
            account_id
        )

        update_data = data.model_dump(
            exclude_unset=True
        )

        if "name" in update_data:
            existing = db.query(Account).filter(
                Account.name == update_data["name"],
                Account.id != account_id
            ).first()

            if existing:
                raise BusinessRuleException(
                    f"Account name '{update_data['name']}' already taken"
                )

        if "account_number" in update_data:
            existing = db.query(Account).filter(
                Account.account_number == update_data["account_number"],
                Account.id != account_id
            ).first()

            if existing:
                raise BusinessRuleException(
                    f"Account number '{update_data['account_number']}' already taken"
                )

        for field, value in update_data.items():
            setattr(account, field, value)

        db.commit()
        db.refresh(account)

        return account

    @staticmethod
    def delete_account(
        db: Session,
        account_id: int
    ) -> None:

        account = AccountService.get_account(
            db,
            account_id
        )

        has_transfers = db.query(FundTransfer).filter(
            or_(
                FundTransfer.source_account_id == account_id,
                FundTransfer.destination_account_id == account_id
            )
        ).first()

        if has_transfers:
            raise BusinessRuleException(
                "Cannot delete account with existing transfers. Deactivate it instead."
            )

        db.delete(account)
        db.commit()


class FundTransferService:

    # =====================================
    # POS -> ACCOUNT
    # =====================================

    @staticmethod
    def create_pos_transfer(
        db: Session,
        current_user: POSUser,
        data: POSToAccountTransferCreate
    ) -> FundTransfer:

        pos = db.query(POS).filter(
            POS.id == current_user.pos_id
        ).first()

        if not pos:
            raise NotFoundException("POS not found")

        if pos.balance < data.amount:
            raise BusinessRuleException(
                "Insufficient POS balance"
            )

        destination = db.query(Account).filter(
            Account.id == data.destination_account_id,
            Account.is_active == True
        ).first()

        if not destination:
            raise NotFoundException(
                "Destination account not found or inactive"
            )

        transfer = FundTransfer(
            pos_id=pos.id,
            source_account_id=None,
            destination_account_id=destination.id,
            transfer_type=TransferType.POS_DEPOSIT,
            amount=data.amount,
            note=data.note,
            status=TransferStatus.PENDING,
            created_by_pos_user_id=current_user.id
        )

        db.add(transfer)
        db.commit()
        db.refresh(transfer)

        return transfer

    # =====================================
    # ACCOUNT -> ACCOUNT
    # =====================================

    @staticmethod
    def create_account_transfer(
        db: Session,
        current_user,
        data: AccountToAccountTransferCreate
    ) -> FundTransfer:

        if data.source_account_id == data.destination_account_id:
            raise BusinessRuleException(
                "Source and destination cannot be the same"
            )

        source = db.query(Account).filter(
            Account.id == data.source_account_id,
            Account.is_active == True
        ).first()

        if not source:
            raise NotFoundException(
                "Source account not found or inactive"
            )

        if source.balance < data.amount:
            raise BusinessRuleException(
                "Insufficient balance in source account"
            )

        destination = db.query(Account).filter(
            Account.id == data.destination_account_id,
            Account.is_active == True
        ).first()

        if not destination:
            raise NotFoundException(
                "Destination account not found or inactive"
            )

        transfer = FundTransfer(
            pos_id=None,
            source_account_id=source.id,
            destination_account_id=destination.id,
            transfer_type=TransferType.ACCOUNT_TRANSFER,
            amount=data.amount,
            note=data.note,
            status=TransferStatus.PENDING,
            created_by_user_id=current_user.id
        )

        db.add(transfer)
        db.commit()
        db.refresh(transfer)

        return transfer

    # =====================================
    # CARD FEE
    # =====================================

    @staticmethod
    def create_card_fee_transfer(
        db: Session,
        client: Client,
        amount: Decimal,
        card_request_id: int,
        created_by_user_id: int
    ) -> FundTransfer:

        # 1. Get card treasury account
        card_account = db.query(Account).filter(
            Account.name == "Card_purchase_account",
            Account.is_active == True
        ).first()

        if not card_account:
            raise BusinessRuleException(
                "Card purchase account not configured"
            )

        # 2. Idempotency check (prevents double charging)
        existing_transfer = db.query(FundTransfer).filter(
            FundTransfer.card_request_id == card_request_id,
            FundTransfer.transfer_type == TransferType.TREASURY_TRANSFER
        ).first()

        if existing_transfer:
            return existing_transfer

        # 3. Balance check
        if client.current_balance < amount:
            raise BusinessRuleException(
                "Insufficient client balance"
            )

        # 4. Create ledger entry
        transfer = FundTransfer(
            source_account_id=client.account_id,
            destination_account_id=card_account.id,
            amount=amount,
            transfer_type=TransferType.TREASURY_TRANSFER,
            status=TransferStatus.APPROVED,
            note="Card issuance fee",

            created_by_pos_user_id=None,
            approved_by_user_id=created_by_user_id,
            approved_at=datetime.now(timezone.utc)
        )

        db.add(transfer)

        # 5. Apply money movement (ONLY HERE)
        client.current_balance -= amount
        card_account.balance += amount

        return transfer
    # =====================================
    # APPROVE TRANSFER
    # =====================================

    @staticmethod
    def approve_transfer(
        db: Session,
        transfer_id: int,
        current_user: User
    ) -> FundTransfer:

        transfer = db.query(FundTransfer).filter(
            FundTransfer.id == transfer_id
        ).first()

        if not transfer:
            raise NotFoundException("Transfer not found")

        if transfer.status != TransferStatus.PENDING:
            raise BusinessRuleException(
                f"Transfer already {transfer.status.value}"
            )

        # ---------------------------------------
        # POS → ACCOUNT
        # ---------------------------------------
        if transfer.transfer_type == TransferType.POS_DEPOSIT:

            pos = db.query(POS).filter(
                POS.id == transfer.pos_id
            ).first()

            if not pos:
                raise NotFoundException("POS not found")

            if pos.balance < transfer.amount:
                raise BusinessRuleException(
                    "Insufficient POS balance"
                )

            pos.balance -= transfer.amount
            transfer.destination_account.balance += transfer.amount

        # ---------------------------------------
        # ACCOUNT → ACCOUNT
        # ---------------------------------------
        elif transfer.transfer_type == TransferType.ACCOUNT_TRANSFER:

            source = transfer.source_account

            if source.balance < transfer.amount:
                raise BusinessRuleException(
                    "Insufficient source account balance"
                )

            source.balance -= transfer.amount
            transfer.destination_account.balance += transfer.amount

        transfer.status = TransferStatus.APPROVED
        transfer.approved_by_user_id = current_user.id
        transfer.approved_at = datetime.now(timezone.utc)

        db.commit()
        db.refresh(transfer)

        return transfer
    
    @staticmethod
    def reject_transfer(
        db: Session,
        transfer_id: int,
        current_user: User,
        data: TransferReject
    ) -> FundTransfer:

        transfer = db.query(FundTransfer).filter(
            FundTransfer.id == transfer_id
        ).first()

        if not transfer:
            raise NotFoundException("Transfer not found")

        if transfer.status != TransferStatus.PENDING:
            raise BusinessRuleException(
                f"Transfer already {transfer.status.value}"
            )

        transfer.status = TransferStatus.REJECTED
        transfer.rejection_reason = data.reason
        transfer.approved_by_user_id = current_user.id
        transfer.approved_at = datetime.now(timezone.utc)

        db.commit()
        db.refresh(transfer)

        return transfer