from fastapi import status, HTTPException
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from src.models.clients import Client
from src.schemas.clients import (
    ClientInvoiceCreate, 
    ClientUpdate, 
    ClientRequestBase, 
    ClientRequestReplyUpdate, 
    ClientRequestUpdate,
    ClientRequestReply,
    ClientHeirCreate,
    ClientHeirUpdate, 
    CardRequestCreate,
    LoanRequestCreate,
)
from src.models.inventory import Inventory
from src.models.clients import (
    ClientPayment, 
    Client, 
    ClientInvoice, 
    ClientInvoiceStatus, 
    LedgerEntry, 
    ClientApproval,
    ClientInvoice, 
    ClientRequest,
    ClientCard, 
    ClientCardRequest, 
    CardScanLog, 
    CardRequestStatus,
    ClientHeir,
    MagneticCardStatus,
    CardPrice,
    CardPriceStatus,
    ClientCardRequest,
    ClientCard,
    ClientLoan,
    LoanStatus
)
from src.core.security import generate_card_token, verify_card_token, hash_token
from src.models.inventory import Warehouse
from src.models.ecommerce import Cart, CartItem, CartStatus, OrderStatus, OrderBeneficiaryInfo, Order, OrderItem
from src.schemas.ecommerce import OrderBeneficiaryInfoCreate
from src.models.pos import POS
from src.models.catalog import ProductVariant, PriceType
from decimal import Decimal
from src.schemas.users import PaginationParams
from datetime import datetime, timezone, timedelta
import uuid, qrcode
from src.core.audit import audit_log
from ulid import ULID
from pathlib import Path
from uuid import UUID
from src.services.account_service import FundTransferService
BASE_DIR = Path(__file__).resolve().parent.parent.parent
MEDIA_DIR = BASE_DIR / "media"


def generate_trx_id(cart_id: int):
    date_part = datetime.now(timezone.utc).strftime("%y%m%d")
    return f"FU-{date_part}-{str(ULID())[:7]}{cart_id}"


class ClientService:
    
    @staticmethod
    def get(db: Session, client_id: int) -> Client:
        client = db.query(Client).filter_by(id=client_id).first()
        if not client:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Client not found")
        return client

    @staticmethod
    def list(db: Session, pagination: PaginationParams):
        query = db.query(Client)
        total = query.count()
        items = (
            query
            .order_by(Client.id.desc())
            .offset(pagination.offset)
            .limit(pagination.page_size)
            .all()
        )
        return total, items

    @staticmethod
    def update(
        db: Session,
        client_id: int,
        data: ClientUpdate,
        actor_id: int,
    ) -> Client:
        client = ClientService.get(db, client_id)
        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(client, field, value)

        db.commit()
        db.refresh(client)
        audit_log("UPDATE", "Client", client.id, actor_id)
        return client

    @staticmethod
    def change_status(
        db: Session,
        client_id: int,
        status,
        actor_id: int,
    ) -> Client:
        client = ClientService.get(db, client_id)
        client.status = status
        db.commit()

        audit_log("STATUS CHANGE", "Client", client.id, actor_id, {"status": status})
        return client

    @staticmethod
    def validate_card(db: Session, card_number: str, amount: Decimal):
        try:
            client_approval = (
                db.query(ClientApproval)
                .filter(ClientApproval.magnetic_card_number == card_number)
                .with_for_update()
                .first()
            )

            if not client_approval:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Card number {card_number} not found"
                )

            client = client_approval.client

            if not client_approval.company:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Client's company is not define"
                )
                        
            if amount < Decimal('0'):
                raise HTTPException(
                    status_code=400,
                    detail="amount must be positive and greater than zero"
                )
            
            if client.card_opening_balance < amount:
                client.magnetic_card_status = MagneticCardStatus.HELD_NOBALANCE
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="No enough balance on client's card"
                )
            
            balance_before = client.current_balance
            client.card_opening_balance -= amount
            client.current_balance += amount
            LoanService.apply_repayment(db, client)
            reference_id = f"CARD{str(ULID())}"

            ledger = LedgerEntry(
                client_id=client.id,
                amount=amount,
                entry_type="credit",
                balance_before=balance_before,
                balance_after=client.current_balance,
                reason="Card validation",
                reference_id=reference_id
            )

            db.add(ledger)
            db.commit()
            db.refresh(ledger)
            return ledger
        except Exception:
            db.rollback()
            raise

    @staticmethod
    def increment_client_balance(db: Session, phone: str, amount: Decimal):
        try:
            client = (
                db.query(Client)
                .filter(Client.phone == phone)
                .with_for_update()
                .first()
            )

            if not client:
                raise HTTPException(404, f"Phone {phone} not found")

            if amount <= Decimal("0"):
                raise HTTPException(400, "Amount must be greater than zero")

            balance_before = client.current_balance
            client.current_balance += amount

            LoanService.apply_repayment(db, client)

            reference_id = f"DEP{str(ULID())}"

            ledger = LedgerEntry(
                client_id=client.id,
                amount=amount,
                entry_type="credit",
                balance_before=balance_before,
                balance_after=client.current_balance,
                reason="Balance top-up",
                reference_id=reference_id
            )

            db.add(ledger)
            db.commit()
            db.refresh(ledger)
            return ledger
        except Exception:
            db.rollback()
            raise
    
    @staticmethod
    def set_card_opening_balance(db: Session, client_id: int, amount: Decimal):
        client = db.get(Client, client_id)
        if not client:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="client not found"
            )

        if client.type != "partner_client":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Client not a partner client"
            )
        client.card_opening_balance += amount
        db.commit()
        db.refresh(client)
        return client

    @staticmethod
    def balance_transfert_between_client(
        db: Session, 
        client_id: int, 
        phone: str, 
        amount: Decimal
    ):
        try:
            # =========================
            # 1. LOCK CLIENT ROWS
            # =========================
            sending_client = (
                db.query(Client)
                .filter(Client.id == client_id)
                .with_for_update()
                .first()
            )

            receiving_client = (
                db.query(Client)
                .filter(Client.phone == phone)
                .with_for_update()
                .first()
            )

            if not sending_client or not receiving_client:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Sending and/or receiving client not found"
                )

            if amount <= Decimal("0"):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Amount must be greater than zero"
                )

            if sending_client.current_balance < amount:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Insufficient balance"
                )

            # =========================
            # 2. BALANCES BEFORE
            # =========================
            sc_balance_before = sending_client.current_balance
            rc_balance_before = receiving_client.current_balance

            # =========================
            # 3. UPDATE BALANCES
            # =========================
            sending_client.current_balance -= amount
            receiving_client.current_balance += amount

            # =========================
            # 4. SHARED REFERENCE
            # =========================
            LoanService.apply_repayment(db, receiving_client)
            reference_id = f"TRF{str(ULID())}"

            # =========================
            # 5. LEDGER ENTRIES
            # =========================

            # Sender (DEBIT)
            db.add(LedgerEntry(
                client_id=sending_client.id,
                entry_type="debit",
                amount=amount,
                balance_before=sc_balance_before,
                balance_after=sending_client.current_balance,
                reference_id=reference_id,
                reason=f"Transfer to {receiving_client.phone}"
            ))

            # Receiver (CREDIT)
            db.add(LedgerEntry(
                client_id=receiving_client.id,
                entry_type="credit",
                amount=amount,
                balance_before=rc_balance_before,
                balance_after=receiving_client.current_balance,
                reference_id=reference_id,
                reason=f"Transfer from {sending_client.phone}"
            ))

            # =========================
            # 6. COMMIT
            # =========================
            db.commit()

            return {
                "reference_id": reference_id,
                "amount": amount,
                "message": "Balance transfered successfully"
            }
        except Exception:
            db.rollback()
            raise
        
    def increment_partner_client_balances_with_scheduler(db: Session, client_id: int):
        clients = db.query(Client).filter(
            Client.type == "partner_client",
            Client.magnetic_card_status == "held_valid"
        ).all()
        for client in clients:
            client.current_balance += client.approval.company.card_amount
            audit_log("Balance increment", "client", client.id)

    def create_client_request(db: Session, client_id: int, request: ClientRequestBase):
        client = db.query(Client).filter_by(id=client_id).first()
        if not client:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="client not found"
            )
        request = ClientRequest(
            client_id=client_id,
            **request.model_dump()
        )
        db.add(request)
        db.commit()
        db.refresh(request)
        return request
    
    def update_client_request(db: Session, request_id: int, data: ClientRequestUpdate):
        request = db.query(ClientRequest).filter_by(id=request_id).first()
        if not request:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Request not found"
            )
        for key, value in data.model_dump(exclude_unset=True).items():
            setattr(request, key, value)
        
        db.commit()
        return request

    def reply_client_request(db: Session, request_id: int, replied_by: int, data: ClientRequestReply):
        request = db.query(ClientRequest).filter_by(id=request_id).first()
        if not request:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="request not found"
            )
        for k, v in data.model_dump().items():
            setattr(request, k, v)
        
        request.replied_by = replied_by
        db.commit()
        return request

    def client_reply_request_update(db: Session, request_id: int, data: ClientRequestReplyUpdate):
        request = db.query(ClientRequest).filter_by(id=request_id).first()
        if not request:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="request not found"
            )
        for k, v in data.model_dump().items():
            setattr(request, k, v)
        
        db.commit()
        return request
    
    # In ClientService

    @staticmethod
    def list_by_company(db: Session, company: str, pagination: PaginationParams):
        query = (
            db.query(Client)
            .join(ClientApproval, ClientApproval.client_id == Client.id)
            .filter(ClientApproval.employee_company == company)
        )
        total = query.count()
        items = (
            query
            .order_by(Client.id.desc())
            .offset(pagination.offset)
            .limit(pagination.page_size)
            .all()
        )
        return total, items

    @staticmethod
    def get_by_company(db: Session, client_id: int, company: str) -> Client:
        client = (
            db.query(Client)
            .join(ClientApproval, ClientApproval.client_id == Client.id)
            .filter(Client.id == client_id, ClientApproval.employee_company == company)
            .first()
        )
        if not client:
            raise HTTPException(
                status.HTTP_404_NOT_FOUND,
                detail="Client not found in your company"
            )
        return client


class ClientInvoiceService:

    @staticmethod
    def create(db: Session, data: ClientInvoiceCreate) -> ClientInvoice:
        invoice = ClientInvoice(**data.model_dump())
        db.add(invoice)
        db.commit()
        db.refresh(invoice)
        audit_log("CREATE", "ClientInvoice", invoice.id, None)
        return invoice
    
    @staticmethod
    def apply_payment(db: Session, invoice: ClientInvoice, amount: Decimal):
        invoice.paid_amount += amount
        if invoice.paid_amount >= invoice.total_amount:
            invoice.status = ClientInvoiceStatus.PAID
        else: 
            invoice.status = ClientInvoiceStatus.PARTIALLY_PAID

    @staticmethod
    def list_by_client(db: Session, client_id: int):
        """
        Returns all invoices for a client
        """
        return (
            db.query(ClientInvoice)
            .filter(ClientInvoice.client_id == client_id)
            .order_by(ClientInvoice.invoice_date.desc())
            .all()
        )

    @staticmethod
    def list_unpaid(db: Session, client_id: int):
        """
        Returns only unpaid or partially paid invoices
        """
        return (
            db.query(ClientInvoice)
            .filter(
                ClientInvoice.client_id == client_id,
                ClientInvoice.status.in_([
                    ClientInvoiceStatus.PENDING,
                    ClientInvoiceStatus.PARTIALLY_PAID
                ])
            )
            .order_by(ClientInvoice.invoice_date.asc())
            .all()
        )

    @staticmethod
    def get_by_id(db: Session, invoice_id: int):
        """
        Fetch single invoice with validation
        """
        invoice = db.query(ClientInvoice).filter_by(id=invoice_id).first()

        if not invoice:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Invoice not found"
            )

        return invoice

class ClientPaymentService:

    @staticmethod
    def create(
        db: Session, 
        client: Client, 
        invoice: ClientInvoice, 
        amount: Decimal, 
        method: str, 
        reference: str
    ) -> ClientPayment:
        payment = ClientPayment(
            client_id=client.id,
            invoice_id=invoice.id if invoice else None,
            payment_date=datetime.now(timezone.utc),
            amount=amount,
            payment_method=method,
            reference=reference if reference else f"FU-{uuid.uuid4().hex[:8]}"
        )
        db.add(payment)
        db.commit()
        db.refresh(payment)
        audit_log("PAYMENT", "Client", client.id, None, {"amount": amount})
        return payment
    
    @staticmethod
    def list_paginated(db: Session, client_id: int, offset: int, limit: int):
        query = db.query(ClientPayment).filter(
            ClientPayment.client_id == client_id
        )
        
        total = query.count()
        items = (
            query.order_by(ClientPayment.payment_date.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )
        return total, items
    

class LedgerService:

    @staticmethod
    def create_entry(db, client, amount, entry_type, source, reference_id):

        before = client.current_balance
        if entry_type == "debit":
            after = before - amount
        else:
            after = before + amount

        entry = LedgerEntry(
            client_id=client.id,
            amount=amount,
            entry_type=entry_type,
            balance_before=before,
            balance_after=after,
            source=source,
            reference_id=reference_id,
        )
        client.current_balance = after
        db.add(entry)
        db.flush()
        return entry
    
    @staticmethod
    def list_paginated(db: Session, client_id: int, offset: int, limit: int):
        """
        Paginated ledger (important for large datasets)
        """
        query = db.query(LedgerEntry).filter(
            LedgerEntry.client_id == client_id
        )
        total = query.count()
        items = (
            query.order_by(LedgerEntry.created_at.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )
        return total, items
    
    @staticmethod
    def list_by_company(db: Session, client_id: int, company: str, offset: int, limit: int):
        client = (
            db.query(Client)
            .join(ClientApproval, ClientApproval.client_id == Client.id)
            .filter(Client.id == client_id, ClientApproval.employee_company == company)
            .first()
        )
        if not client:
            raise HTTPException(
                status.HTTP_404_NOT_FOUND,
                detail="Client not found in your company"
            )

        query = db.query(LedgerEntry).filter(LedgerEntry.client_id == client_id)
        total = query.count()
        items = (
            query
            .order_by(LedgerEntry.created_at.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )
        return total, items


class CartService:
    
    @staticmethod
    def get_or_create_cart(db: Session, client_id: int, warehouse_id: int):
        client = db.query(Client).filter(Client.id==client_id).first()
        warehouse = db.query(Warehouse).filter(Warehouse.id==warehouse_id).first()

        if not client:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Client {client_id} not found"
            )
        if not warehouse:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"warehouse {client_id} not found"
            )

        cart = db.query(Cart).filter(
            Cart.client_id == client_id,
            Cart.warehouse_id == warehouse_id,
            Cart.status == CartStatus.OPEN
        ).first()

        if cart:
            return cart

        cart = CartService.create_cart(db, client_id, warehouse_id)

        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            # race condition fallback
            cart = db.query(Cart).filter(
                Cart.client_id == client_id,
                Cart.warehouse_id == warehouse_id,
                Cart.status == CartStatus.OPEN
            ).first()

        db.refresh(cart)
        return cart
    
    @staticmethod
    def create_cart(db: Session, client_id: int, warehouse_id: int):
        cart = Cart(
            client_id=client_id,
            warehouse_id=warehouse_id,
            status=CartStatus.OPEN
        )
        db.add(cart)
        return cart
    
    @staticmethod
    def add_item(
        db: Session,
        client_id: int,
        warehouse_id: int,
        product_variant_id: int,
        qty: Decimal
    ):

        if qty <= 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Quantity must be greater than 0"
            )

        cart = CartService.get_or_create_cart(db, client_id, warehouse_id)
        if cart.status != CartStatus.OPEN:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cart is not open"
            )

        product_variant = db.query(ProductVariant).filter_by(
            id=product_variant_id
        ).first()

        if not product_variant:
            raise HTTPException(404, "Product variant not found")

        inventory_item = db.query(Inventory).filter_by(
            warehouse_id=warehouse_id,
            product_variant_id=product_variant_id
        ).first()

        if not inventory_item:
            raise HTTPException(400, "Product not available in this warehouse")

        existing_item = next(
            (item for item in cart.items if item.product_variant_id == product_variant_id),
            None
        )

        if existing_item:
            existing_item.qty += qty
        else:
            cart_item = CartItem(
                cart_id=cart.id,
                product_variant_id=product_variant_id,
                qty=qty
            )
            db.add(cart_item)

        db.commit()
        db.refresh(cart)
        return cart

    @staticmethod
    def remove_item(
        db: Session,
        client_id: int,
        warehouse_id: int,
        product_variant_id: int
    ):
        cart = CartService.get_or_create_cart(db, client_id, warehouse_id)

        item = next(
            (i for i in cart.items if i.product_variant_id == product_variant_id),
            None
        )
        if not item:
            raise HTTPException(404, "Item not found")

        db.delete(item)
        db.commit()
        db.refresh(cart)
        return cart
    
    @staticmethod
    def clear_cart(db: Session, client_id: int, warehouse_id: int):
        cart = CartService.get_or_create_cart(db, client_id, warehouse_id)

        for item in cart.items:
            db.delete(item)

        db.commit()
        db.refresh(cart)
        return cart    

    @staticmethod
    def build_cart_response(db: Session, cart: Cart) -> dict:
        totals = PricingService.calculate_order_total(db, cart)

        return {
            "id": cart.id,
            "client_id": cart.client_id,
            "status": cart.status,
            "created_at": cart.created_at,
            "items": cart.items,
            "subtotal": totals["subtotal"],
            "tax": totals["tax"],
            "shipping_fee": totals["shipping_fee"],
            "total": totals["total"],
        }
    
class PricingService:
    
    @staticmethod
    def calculate_order_total(db: Session, cart: Cart) -> dict:
        try:
            subtotal = Decimal('0')
            tax_amount = Decimal('0')
            total_amount = Decimal('0')
            for item in cart.items:
                variant = item.product_variant
                retail_price = next(
                    (price for price in variant.prices 
                     if price.is_active and price.qualification==PriceType.RETAIL), 
                    None
                )
                if not retail_price:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail="No active retail price found for this variant"
                    )

                
                line_total = (retail_price.sale_price * item.qty).quantize(Decimal("0.01"))
                subtotal += line_total

            tax_amount = Decimal('0')
            shipping_fee = Decimal('0')
            total_amount = subtotal + tax_amount + shipping_fee
            return {
                "subtotal": subtotal,
                "tax": tax_amount,
                "shipping_fee": shipping_fee,
                "total": total_amount
            }
        except Exception as e:
            db.rollback()
            raise


class OrderService:

    @staticmethod
    def create_order(db: Session, cart: Cart, pos: POS, beneficiary: OrderBeneficiaryInfoCreate = None):

        if not cart.items:
            raise HTTPException(400, "Cart is empty")

        if cart.status != CartStatus.OPEN:
            raise HTTPException(400, "Cart already processed")

        # Ensure single warehouse constraint
        if cart.warehouse_id != pos.warehouse_id:
            raise HTTPException(400, "Cart warehouse mismatch with POS")

        # =========================
        # 1. PRICING
        # =========================
        pricing = PricingService.calculate_order_total(db, cart)
        
        # =========================
        # 2. STOCK VALIDATION + DEDUCTION
        # =========================
        for item in cart.items:
            inventory = db.query(Inventory).filter(
                Inventory.warehouse_id == cart.warehouse_id,
                Inventory.product_variant_id == item.product_variant_id
            ).with_for_update().first()

            if not inventory or inventory.quantity < item.qty:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Insufficient stock for variant {item.product_variant_id}"
                )

        # =========================
        # 3. CREATE ORDER
        # =========================
        order = Order(
            client_id=cart.client_id,
            warehouse_id=cart.warehouse_id,
            order_code=generate_trx_id(cart.id),
            subtotal=pricing["subtotal"],
            tax_amount=pricing["tax"],
            total_amount=pricing["total"],
        )
        db.add(order)
        db.flush()

        # =========================
        # 4. CREATE ORDER ITEMS
        # =========================
        for item in cart.items:
            sale_price = next(
                (
                    p for p in item.product_variant.prices
                    if p.is_active and p.qualification == PriceType.RETAIL
                ),
                None
            )

            if not sale_price:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND, 
                    detail="No active price found"
                )

            db.add(OrderItem(
                order_id=order.id,
                product_variant_id=item.product_variant_id,
                qty=item.qty,
                unit_price=sale_price.sale_price
            ))
        if beneficiary:
            db.add(OrderBeneficiaryInfo(
                order_id=order.id,
                first_name=beneficiary.first_name,
                last_name=beneficiary.last_name,
                phone=beneficiary.phone
            ))
        cart.status = CartStatus.COMPLETED
        db.commit()
        db.refresh(order)
        return order
    
    @staticmethod
    def checkout_order(db: Session, order_code: str):
        try:
            order = (
                db.query(Order)
                .filter(Order.order_code == order_code)
                .with_for_update()
                .first()
            )

            if not order:
                raise HTTPException(404, f"Order {order_code} not found")
            
            if order.status == "completed":
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Order already completed"
                )

            # STOCK
            for item in order.items:
                inventory = (
                    db.query(Inventory)
                    .filter(
                        Inventory.warehouse_id == order.warehouse_id,
                        Inventory.product_variant_id == item.product_variant_id
                    )
                    .with_for_update()
                    .first()
                )

                if not inventory or inventory.quantity < item.qty:
                    raise HTTPException(
                        400,
                        f"Insufficient stock for variant {item.product_variant_id}"
                    )

                inventory.quantity -= item.qty

            # FINANCE
            client = order.client

            if client.current_balance < order.total_amount:
                raise HTTPException(400, "Insufficient balance")

            balance_before = client.current_balance
            client.current_balance -= order.total_amount

            order.warehouse.pos.balance += order.total_amount

            reference_id = f"ORD{str(ULID())}"

            db.add(LedgerEntry(
                client_id=client.id,
                entry_type="debit",
                amount=order.total_amount,
                balance_before=balance_before,
                balance_after=client.current_balance,
                reference_id=reference_id,
                reason=f"Payment for order {order.order_code}"
            ))

            order.status = OrderStatus.COMPLETED

            db.commit()
            db.refresh(order)

            return order

        except Exception:
            db.rollback()
            raise
        
    @staticmethod
    def list_client_order(db: Session, client: Order, offset: int, limit: int):
        orders = (
            db.query(Order)
            .options(joinedload(Order.items), joinedload(Order.beneficiary))
            .filter(Order.client_id == client.id)
            .order_by(Order.created_at.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )
        return orders
    
    @staticmethod
    def get_order_details(db: Session, order_code: str):
        order = (
            db.query(Order)
            .options(joinedload(Order.items), joinedload(Order.beneficiary))
            .filter(Order.order_code == order_code)
            .first()
        )

        if not order:
            raise HTTPException(404, "Order not found")
        return order


class ClientCardService:

    @staticmethod
    def request_card(db: Session, client_id: int, data: CardRequestCreate):

        existing = db.query(ClientCardRequest).filter(
            ClientCardRequest.client_id == client_id,
            ClientCardRequest.status == CardRequestStatus.PENDING
        ).first()

        if existing:
            return existing

        req = ClientCardRequest(
            client_id=client_id,
            reason=data.reason
        )
        db.add(req)
        db.commit()
        db.refresh(req)
        return req    


    @staticmethod
    def approve_request(db: Session, request_id: int, reviewer_id: int):

        req = db.get(ClientCardRequest, request_id)

        if not req:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, 
                detail="Request not found"
            )

        client = db.get(Client, req.client_id)

        if not client:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, 
                detail="Client not found"
            )

        # IDEMPOTENCY CHECK 1: request already processed
        if req.status == CardRequestStatus.APPROVED:

            existing_card = db.query(ClientCard).filter(
                ClientCard.client_id == client.id,
                ClientCard.created_by == reviewer_id
            ).first()

            if existing_card:
                return existing_card

        elif req.status != CardRequestStatus.PENDING:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, 
                detail="Invalid request state"
            )

        # IDEMPOTENCY CHECK 2: avoid duplicate active card
        active_card = db.query(ClientCard).filter(
            ClientCard.client_id == client.id,
            ClientCard.is_active == True,
            ClientCard.expires_at > datetime.now(timezone.utc)
        ).first()

        if active_card:
            return active_card

        price = db.query(CardPrice).filter_by(status="active").first()
        if not price:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No card price set for now"
            )
        
        card_id = uuid.uuid4()
        token = generate_card_token(card_id, client.id)
        token_hash = hash_token(token)

        qr_dir = MEDIA_DIR / "qrcodes"
        qr_dir.mkdir(parents=True, exist_ok=True)

        qr_path = qr_dir / f"{card_id}.png"
        qrcode.make(token).save(str(qr_path))

        qr_public_path = f"/media/qrcodes/{card_id}.png"

        card = ClientCard(
            id=card_id,
            client_id=client.id,
            card_number=getattr(client.approval, "magnetic_card_number", None) or client.phone,
            qr_token_hash=token_hash,
            qr_code_path=qr_public_path,
            expires_at=datetime.now(timezone.utc) + timedelta(days=365),
            created_by=reviewer_id
        )

        db.add(card)

        # 5. FINANCIAL OPERATION ONLY THROUGH SERVICE
        FundTransferService.create_card_fee_transfer(
            db=db,
            client=client,
            amount=price.price,
            card_request_id=req.id,
            created_by_user_id=reviewer_id
        )
        
        req.status = CardRequestStatus.APPROVED
        req.reviewed_at = datetime.now(timezone.utc)
        req.reviewer_id = reviewer_id

        db.commit()
        db.refresh(card)

        return card

    @staticmethod
    def reject_request(
        db: Session,
        request_id: int,
        reviewer_id: int,
        reason: str | None = None
    ):
        req = db.get(ClientCardRequest, request_id)

        if not req:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Request not found"
            )

        # IDEMPOTENCY: already rejected
        if req.status == CardRequestStatus.REJECTED:
            return req

        # Prevent invalid transitions
        if req.status != CardRequestStatus.PENDING:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid request state"
            )

        req.status = CardRequestStatus.REJECTED
        req.reviewed_at = datetime.now(timezone.utc)
        req.reviewer_id = reviewer_id

        if reason:
            req.reason = reason

        db.commit()
        db.refresh(req)

        return req
    
    @staticmethod
    def list_card_request(db: Session, pagination: PaginationParams):
        items = db.query(ClientCardRequest)
        total = items.count()
        (items
         .order_by(ClientCardRequest.requested_at.desc())
         .offset(pagination.offset)
         .limit(pagination.page_size)
         .all()
        )
        return total, items
    
    @staticmethod
    def get_single_request(db: Session, client_id: int):
        client_req = db.query(ClientCardRequest).filter_by(client_id=client_id).first()
        if not client_req:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="client not found"
            )
        
        return client_req

    @staticmethod
    def scan_card(db: Session, token: str, agent_id: int, ip: str):
        try:
            payload = verify_card_token(token)
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, 
                detail="Invalid token"
            )

        card = db.get(ClientCard, payload["sub"])

        if not card:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, 
                detail="Card not found"
            )

        if hash_token(token) != card.qr_token_hash:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, 
                detail="Token mismatch"
            )

        if not card.is_active or card.revoked_at:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, 
                detail="Card inactive"
            )

        if card.expires_at < datetime.now(timezone.utc):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, 
                detail="Card expired"
            )

        client = card.client

        log = CardScanLog(
            card_id=card.id,
            client_id=client.id,
            scanned_by=agent_id,
            ip_address=ip,
            scanned_at=datetime.now(timezone.utc)
        )
        db.add(log)
        db.commit()
        return client

    @staticmethod
    def get_client_card(db: Session, client_id: int):
        card = db.query(ClientCard).filter_by(client_id=client_id).first()
        if not card:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, 
                detail="Card not found"
            )
        return card


    @staticmethod
    def revoke_card(db: Session, card_id):
        card = db.query(ClientCard).get(card_id)

        if not card:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, 
                detail="Card not found"
            )

        card.is_active = False
        card.revoked_at = datetime.now(timezone.utc)

        db.commit()
        return card
    

class ClientHeirService:

    @staticmethod
    def create_heir(db: Session, data: ClientHeirCreate):
        client = db.query(Client).filter_by(id=data.client_id).first()
        if not client:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Client not found"
            )
        
        heir = ClientHeir(**data.model_dump())
        db.add(heir)
        db.commit()
        db.refresh(heir)
        return heir
    
    @staticmethod
    def update_heir(db: Session, heir_id: int, data: ClientHeirUpdate):
        heir = db.query(ClientHeir).filter_by(id=heir_id).first()

        if not heir:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Heir not found"
            )
        
        updated_data = data.model_dump(exclude_unset=True)
        for k, v in updated_data.items():
            setattr(heir, k, v)
        
        db.commit()
        return heir


class CardPriceService:

    @staticmethod
    def create(db: Session, amount: Decimal):
        db.query(CardPrice).filter(
            CardPrice.status == CardPriceStatus.ACTIVE
        ).update({CardPrice.status: CardPriceStatus.INACTIVE})

        price = CardPrice(
            price=amount,
            status=CardPriceStatus.ACTIVE
        )

        db.add(price)
        db.commit()
        db.refresh(price)

        return price
    
    @staticmethod
    def get_price(db: Session):
        price = db.query(CardPrice).filter(
            CardPrice.status=="active"
        ).first()
        if not price:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Price not found"
            )
        
        return price

    @staticmethod
    def update(db: Session, price_id: int, amount: Decimal):
        price = db.get(CardPrice, price_id)

        if not price:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, 
                detail="Price not found"
            )

        price.price = amount

        db.commit()
        db.refresh(price)

        return price
    

class LoanService:

    @staticmethod
    def request_loan(db: Session, client_id: int, data: LoanRequestCreate):
        client = db.get(Client, client_id)

        if not client:
            raise HTTPException(404, "Client not found")

        # Prevent multiple active loans
        existing = db.query(ClientLoan).filter(
            ClientLoan.client_id == client_id,
            ClientLoan.status.in_([
                LoanStatus.PENDING,
                LoanStatus.DISBURSED,
                LoanStatus.PARTIALLY_REPAID
            ])
        ).first()

        if existing:
            raise HTTPException(400, "Existing active loan")

        loan = ClientLoan(
            client_id=client_id,
            amount=data.amount,
            remaining_amount=data.amount,
            reason=data.reason
        )

        db.add(loan)
        db.commit()
        db.refresh(loan)

        return loan

    @staticmethod
    def approve_loan(db: Session, loan_id: UUID, admin_id: int):
        loan = db.get(ClientLoan, loan_id)

        if not loan or loan.status != LoanStatus.PENDING:
            raise HTTPException(400, "Invalid loan")

        client = loan.client

        # Disbursement
        client.current_balance += loan.amount

        loan.status = LoanStatus.DISBURSED
        loan.approved_at = datetime.now(timezone.utc)
        loan.disbursed_at = datetime.now(timezone.utc)
        loan.approved_by = admin_id

        # Ledger entry
        db.add(LedgerEntry(
            client_id=client.id,
            entry_type="credit",
            amount=loan.amount,
            balance_before=client.current_balance - loan.amount,
            balance_after=client.current_balance,
            reference_id=str(loan.id),
            reason="Loan disbursement"
        ))

        db.commit()
        db.refresh(loan)

        return loan

    @staticmethod
    def reject_loan(db: Session, loan_id: UUID, admin_id: int, reason: str | None = None):
        loan = db.get(ClientLoan, loan_id)

        if not loan:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, 
                detail="Loan not found"
            )

        if loan.status == LoanStatus.REJECTED:
            return loan

        if loan.status != LoanStatus.PENDING:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, 
                detail="Invalid state"
            )

        loan.status = LoanStatus.REJECTED
        loan.approved_by = admin_id
        loan.reason = reason
        loan.approved_at = datetime.now(timezone.utc)

        db.commit()
        db.refresh(loan)

        return loan

    @staticmethod
    def apply_repayment(db: Session, client: Client):
        available = client.current_balance

        if available <= 0:
            return

        loans = db.query(ClientLoan).filter(
            ClientLoan.client_id == client.id,
            ClientLoan.status.in_([
                LoanStatus.DISBURSED,
                LoanStatus.PARTIALLY_REPAID
            ])
        ).order_by(ClientLoan.requested_at).all()

        for loan in loans:
            if available <= 0:
                break

            repay = min(available, loan.remaining_amount)

            if repay <= 0:
                continue

            balance_before = client.current_balance

            # update balances
            client.current_balance -= repay
            loan.remaining_amount -= repay

            db.add(LedgerEntry(
                client_id=client.id,
                entry_type="debit",
                amount=repay,
                balance_before=balance_before,
                balance_after=client.current_balance,
                reference_id=str(loan.id),
                reason="Loan repayment"
            ))

            if loan.remaining_amount == 0:
                loan.status = LoanStatus.REPAID
            else:
                loan.status = LoanStatus.PARTIALLY_REPAID

            available = client.current_balance

        db.flush()
    
    @staticmethod
    def get_client_financials(db: Session, client_id: int):
        client = db.get(Client, client_id)

        if not client:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Client not found"
            )

        total_outstanding_loans = db.query(
            func.coalesce(func.sum(ClientLoan.remaining_amount), 0)
        ).filter(
            ClientLoan.client_id == client_id,
            ClientLoan.status.in_([
                LoanStatus.DISBURSED,
                LoanStatus.PARTIALLY_REPAID
            ])
        ).scalar()

        net_position = client.current_balance - total_outstanding_loans

        return {
            "id": client.id,
            "balance": client.current_balance,
            "total_outstanding_loans": total_outstanding_loans,
            "net_position": net_position
        }
    
    @staticmethod
    def list(db: Session, pagination: PaginationParams):
        loans = db.query(ClientLoan)
        total = loans.count()
        loans\
        .order_by(ClientLoan.requested_at.desc())\
        .offset(pagination.offset)\
        .limit(pagination.page_size)\
        .all()
        return total, loans
    
    @staticmethod
    def get_client_requests(db: Session, client_id: int):
        client_loans = db.query(ClientLoan).filter(ClientLoan.client_id==client_id).first()
        if not client_loans:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No loan(s) found"
            )
        return client_loans


