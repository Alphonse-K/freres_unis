from sqlalchemy.orm import Session
from sqlalchemy import func
from fastapi import HTTPException, status
from decimal import Decimal

from src.models.clients import Client
from src.models.ecommerce import Order, OrderItem
from src.models.clients import ClientReturn, ClientReturnItem, ReturnStatus
from src.schemas.clients import (
    ClientReturnCreate,
    ClientReturnFilter,
)
from src.schemas.users import PaginationParams
from datetime import datetime, timezone

class ClientReturnService:

    @staticmethod
    def create_return(db: Session, data: ClientReturnCreate) -> ClientReturn:
        # 1. Validate client
        client = db.query(Client).filter(Client.id == data.client_id).first()
        if not client:
            raise HTTPException(status_code=404, detail="Client not found")

        # 2. Validate order
        order = (
            db.query(Order)
            .filter(
                Order.id == data.order_id,
                Order.client_id == data.client_id,
            )
            .first()
        )
        if not order:
            raise HTTPException(status_code=404, detail="Order not found")

        # 3. Lock order items (important for concurrency)
        order_items = {
            item.id: item
            for item in db.query(OrderItem)
            .filter(OrderItem.order_id == order.id)
            .with_for_update()
            .all()
        }

        if not order_items:
            raise HTTPException(
                status_code=400,
                detail="Order has no items"
            )

        total_amount = Decimal("0.00")
        return_items = []

        # 4. Process each return item
        for item in data.items:
            order_item = order_items.get(item.order_item_id)

            if not order_item:
                raise HTTPException(
                    status_code=400,
                    detail=f"Order item {item.order_item_id} does not belong to order"
                )

            # 5. Calculate already returned quantity
            already_returned_qty = (
                db.query(func.coalesce(func.sum(ClientReturnItem.qty_returned), 0))
                .join(ClientReturn)
                .filter(
                    ClientReturn.order_id == order.id,
                    ClientReturnItem.order_item_id == order_item.id
                )
                .scalar()
            )

            available_qty = order_item.qty - already_returned_qty

            if item.qty_returned > available_qty:
                raise HTTPException(
                    status_code=400,
                    detail=(
                        f"Return qty exceeds available quantity "
                        f"for order item {order_item.id}"
                    )
                )

            line_total = item.qty_returned * order_item.unit_price
            total_amount += line_total

            return_items.append(
                ClientReturnItem(
                    order_item_id=order_item.id,
                    qty_returned=item.qty_returned,
                    unit_price=order_item.unit_price,
                    line_total=line_total,
                )
            )

        # 6. Create return record
        client_return = ClientReturn(
            client_id=data.client_id,
            order_id=data.order_id,
            total_amount=total_amount,
            reason=data.reason,
            status=ReturnStatus.PENDING,
            items=return_items,
        )

        db.add(client_return)
        db.commit()
        db.refresh(client_return)

        return client_return
    
    @staticmethod
    def list_returns(
        db: Session,
        filters: ClientReturnFilter,
        pagination: PaginationParams
    ):
        query = db.query(ClientReturn)

        if filters.client_id:
            query = query.filter(ClientReturn.client_id == filters.client_id)

        if filters.order_id:
            query = query.filter(ClientReturn.order_id == filters.order_id)

        if filters.min_amount:
            query = query.filter(ClientReturn.total_amount >= filters.min_amount)

        if filters.max_amount:
            query = query.filter(ClientReturn.total_amount <= filters.max_amount)

        if filters.start_date:
            query = query.filter(ClientReturn.created_at >= filters.start_date)

        if filters.end_date:
            query = query.filter(ClientReturn.created_at <= filters.end_date)

        total = query.count()
        results = (
            query.order_by(ClientReturn.created_at.desc())
            .offset(pagination.offset)
            .limit(pagination.page_size)
            .all()
        )

        return total, results


    @staticmethod
    def get_return(db: Session, return_id: int) -> ClientReturn:
        client_return = (
            db.query(ClientReturn)
            .filter(ClientReturn.id == return_id)
            .first()
        )

        if not client_return:
            raise HTTPException(status_code=404, detail="Return not found")

        return client_return
    
    @staticmethod
    def approve_return(
        db: Session,
        return_id: int,
        approver_id: int,
    ) -> ClientReturn:

        client_return = (
            db.query(ClientReturn)
            .filter(ClientReturn.id == return_id)
            .with_for_update()
            .first()
        )

        if not client_return:
            raise HTTPException(status_code=404, detail="Return not found")

        if client_return.status != ReturnStatus.PENDING:
            raise HTTPException(
                status_code=400,
                detail="Only pending returns can be approved",
            )

        client = (
            db.query(Client)
            .filter(Client.id == client_return.client_id)
            .with_for_update()
            .first()
        )

        # 1. Update balance
        client.current_balance -= client_return.total_amount

        # 2. Update return status
        client_return.status = ReturnStatus.APPROVED
        client_return.approved_by = approver_id
        client_return.approved_at = datetime.now(timezone.utc)

        db.commit()
        db.refresh(client_return)

        return client_return
    
    @staticmethod
    def reject_return(
        db: Session,
        return_id: int,
        approver_id: int,
        reason: str,
    ) -> ClientReturn:

        client_return = db.query(ClientReturn).first()

        if not client_return:
            raise HTTPException(status_code=404, detail="Return not found")

        if client_return.status != ReturnStatus.PENDING:
            raise HTTPException(
                status_code=400,
                detail="Only pending returns can be rejected"
            )

        client_return.status = ReturnStatus.REJECTED
        client_return.approved_by = approver_id
        client_return.approved_at = datetime.now(timezone.utc)
        client_return.reason = reason

        db.commit()
        db.refresh(client_return)

        return client_return

