# src/services/client_service.py
from fastapi import status, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from src.models.clients import Client
from src.schemas.clients import ClientUpdate
from src.models.inventory import Inventory
from src.models.clients import ClientInvoice
from src.schemas.clients import ClientInvoiceCreate
from src.models.clients import ClientPayment, Client, ClientInvoice, ClientInvoiceStatus, LedgerEntry
from src.models.inventory import Warehouse
from src.schemas.clients import ClientPaymentCreate
from src.models.ecommerce import Cart, CartItem, CartStatus, OrderStatus
from src.models.pos import POS
from src.models.catalog import ProductVariant, PriceType
from src.models.ecommerce import Order, OrderItem
from decimal import Decimal
from src.schemas.users import PaginationParams
from datetime import datetime, timezone
import uuid
from src.core.audit import audit_log

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
    def checkout_cart(db: Session, cart: Cart, pos: POS):

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

            # Deduct stock
            inventory.quantity -= item.qty

        # =========================
        # 3. CREATE ORDER
        # =========================
        order = Order(
            client_id=cart.client_id,
            warehouse_id=cart.warehouse_id,
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

        # =========================
        # 5. FINANCIAL OPERATIONS
        # =========================
        client = db.query(Client).filter(Client.id == cart.client_id).first()

        if client.current_balance < pricing["total"]:
            raise HTTPException(400, "Insufficient client balance")

        balance_before = client.current_balance
        client.current_balance -= pricing["total"]
        pos.balance += pricing["total"]

        # =========================
        # 6. LEDGER ENTRY (CLIENT)
        # =========================
        db.add(LedgerEntry(
            client_id=client.id,
            entry_type="debit",
            amount=pricing["total"],
            balance_before=balance_before,
            balance_after=client.current_balance,
            reference_id=f"ORDER-{order.id}",
            reason="paying order"
        ))

        # =========================
        # 8. FINALIZE
        # =========================
        cart.status = CartStatus.COMPLETED
        order.status = OrderStatus.COMPLETED
        db.commit()
        db.refresh(order)
        return order
    
    @staticmethod
    def list_client_order(db: Session, client: Order, offset: int, limit: int):
        orders = (
            db.query(Order)
            .filter(Order.client_id == client.id)
            .order_by(Order.created_at.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )
        return orders
    
