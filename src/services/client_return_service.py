from sqlalchemy.orm import Session
from sqlalchemy import func
from fastapi import HTTPException, status
from decimal import Decimal

from src.models.clients import Client
from src.models.ecommerce import Order, OrderItem
from src.models.pos import POS, POSLedger
from src.models.clients import ClientReturn, ClientReturnItem, ReturnStatus, LedgerEntry
from src.schemas.clients import (
    ClientReturnCreate,
    ClientReturnFilter,
)
from src.schemas.users import PaginationParams
from datetime import datetime, timezone

class ClientReturnService:

    # =========================
    # CREATE RETURN REQUEST
    # =========================
    @staticmethod
    def create_return(db: Session, data: ClientReturnCreate):

        client = db.query(Client).filter_by(id=data.client_id).first()
        if not client:
            raise HTTPException(404, "Client not found")

        order = db.query(Order).filter(
            Order.id == data.order_id,
            Order.client_id == data.client_id
        ).first()

        if not order:
            raise HTTPException(404, "Order not found")

        # Lock order items
        order_items = {
            item.product_variant_id: item
            for item in db.query(OrderItem)
            .filter(OrderItem.order_id == order.id)
            .with_for_update()
            .all()
        }
        total_amount = Decimal("0.00")
        return_items = []

        for item in data.items:
            order_item = order_items.get(item.product_variant_id)
            if not order_item:
                raise HTTPException(400, "Invalid order item")

            already_returned = db.query(
                func.coalesce(func.sum(ClientReturnItem.qty_returned), 0)
            ).join(ClientReturn).filter(
                ClientReturn.order_id == order.id,
                ClientReturnItem.product_variant_id == order_item.product_variant_id
            ).scalar()

            available_qty = order_item.qty - already_returned
            if item.qty_returned > available_qty:
                raise HTTPException(400, "Return exceeds available quantity purchased")

            line_total = item.qty_returned * order_item.unit_price
            total_amount += line_total

            return_items.append(ClientReturnItem(
                product_variant_id=order_item.product_variant_id,
                qty_returned=item.qty_returned,
                unit_price=order_item.unit_price,
                line_total=line_total
            ))

        client_return = ClientReturn(
            client_id=data.client_id,
            order_id=data.order_id,
            total_amount=total_amount,
            reason=data.reason,
            status=ReturnStatus.PENDING,
            items=return_items
        )

        db.add(client_return)
        db.commit()
        db.refresh(client_return)
        return client_return

    @staticmethod
    def cancel_return(db: Session, client_return: ClientReturn, client: Client):
        if client_return.client_id != client.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Can only cancel your own returns"
            )
        
        if client_return.status != ReturnStatus.PENDING:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot cancel an already processed return"
            )

        client_return.status = ReturnStatus.CANCELLED
        client_return.updated_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(client_return)
        return client_return
    
    # =========================
    # APPROVE RETURN (CORE LOGIC)
    # =========================
    @staticmethod
    def approve_return(db: Session, return_id: int, approver_by):
        try:
            client_return = db.query(ClientReturn)\
                .filter(ClientReturn.id == return_id)\
                .with_for_update()\
                .first()

            if not client_return:
                raise HTTPException(404, "Return not found")

            if client_return.status != ReturnStatus.PENDING:
                raise HTTPException(400, "Return already processed")

            order = db.query(Order).filter_by(id=client_return.order_id).first()
            if not order:
                raise HTTPException(404, "Order not found")

            client = db.query(Client)\
                .filter_by(id=client_return.client_id)\
                .with_for_update()\
                .first()

            pos = db.query(POS)\
                .filter(POS.warehouse_id == order.warehouse_id)\
                .with_for_update()\
                .first()

            if not pos:
                raise HTTPException(404, "POS not found")

            # Financial check FIRST
            if pos.balance < client_return.total_amount:
                raise HTTPException(400, "POS insufficient balance")

            # Lock order items
            order_items = {
                oi.product_variant_id: oi
                for oi in db.query(OrderItem)
                .filter(OrderItem.order_id == client_return.order_id)
                .with_for_update()
                .all()
            }

            for item in client_return.items:
                order_item = order_items.get(item.product_variant_id)

                if not order_item:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail=f"Order item not found for product_variant_id={item.product_variant_id}"
                    )

                if order_item.returned_qty + item.qty_returned > order_item.qty:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail="Returned quantity exceeds purchased quantity"
                    )

                order_item.returned_qty += item.qty_returned

            # Financial updates
            before = client.current_balance
            client.current_balance += client_return.total_amount

            pos_balance_before = pos.balance
            pos.balance -= client_return.total_amount

            # Ledger
            db.add(LedgerEntry(
                client_id=client.id,
                entry_type="credit",
                amount=client_return.total_amount,
                balance_before=before,
                balance_after=client.current_balance,
                reference_id=f"RETURN-{client_return.id}",
                reason="remboursement de retour"
            ))

            db.add(POSLedger(
                pos_id=pos.id,
                entry_type="debit",
                amount=client_return.total_amount,
                balance_before=pos_balance_before,
                balance_after=pos.balance,
                reference_id=f"RETURN-{client_return.id}",
                reason="remboursement de retour"
            ))

            # Finalize
            client_return.status = ReturnStatus.APPROVED
            client_return.approved_by = approver_by.id
            client_return.approved_at = datetime.now(timezone.utc)

            db.commit()
            db.refresh(client_return)
            return client_return

        except Exception:
            db.rollback()
            raise

    # =========================
    # REJECT RETURN
    # =========================
    @staticmethod
    def reject_return(db: Session, return_id: int, approver_by, reason: str):

        client_return = db.query(ClientReturn)\
            .filter(ClientReturn.id == return_id)\
            .first()

        if not client_return:
            raise HTTPException(404, "Return not found")

        if client_return.status != ReturnStatus.PENDING:
            raise HTTPException(400, "Return already processed")

        client_return.status = ReturnStatus.REJECTED
        client_return.approved_by = approver_by.id
        client_return.approved_at = datetime.now(timezone.utc)
        client_return.updated_at = datetime.now(timezone.utc)
        client_return.reason = reason
        db.commit()
        db.refresh(client_return)
        return client_return

    # =========================
    # LIST RETURNS
    # =========================
    @staticmethod
    def list_returns(db: Session, filters, current_user, offset: int, limit: int):
        """
        - List client returns with role-based access:
        - Admin: sees all returns
        - Client: sees only their own returns
        - POS: sees returns for orders in their warehouse
        """
        query = db.query(ClientReturn)
        print(current_user)

        if current_user.get("account_type") == "user":
            pass
        elif current_user.get("account_type") == "client":
            query = query.filter(ClientReturn.client_id == filters.client_id)
        elif current_user.get("account_type") == "pos":
            account = current_user.get('account')
            warehouse_id = account.pos.warehouse_id
            query = query.join(ClientReturn.order)
            unauthorized = query.filter(Order.warehouse_id != warehouse_id).first()
            if unauthorized:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Unauthorized access: return does not belong to your warehouse"
                )  
            query = query.filter(Order.warehouse_id == warehouse_id)
        else: 
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, 
                detail="Unauthorized access"
            )
        
        total = query.count()
        results = query.order_by(ClientReturn.created_at.desc())\
            .offset(offset)\
            .limit(limit)\
            .all()
        return total, results

    # =========================
    # GET SINGLE RETURN
    # =========================
    @staticmethod
    def get_return(db: Session, return_id: int):

        obj = db.query(ClientReturn)\
            .filter(ClientReturn.id == return_id)\
            .first()

        if not obj:
            raise HTTPException(404, "Return not found")

        return obj
    