# src/services/provider_service.py (COMPLETE VERSION)
from sqlalchemy.orm import Session, joinedload, selectinload
from sqlalchemy import func, and_, or_, desc
from sqlalchemy.exc import IntegrityError
from fastapi import HTTPException, status
from datetime import datetime, date, timezone, timedelta
from decimal import Decimal
from typing import List, Optional, Dict, Tuple
import logging

from src.models.providers import (
    Provider, PurchaseInvoice, ProviderPayment, PurchaseReturn,
    PurchaseInvoiceStatus, PaymentMethod
)
from src.models.locations import Address, Country, Region, City
from src.models.procurement import Procurement, ProcurementItem
from src.schemas.providers import (
    ProviderCreate, ProviderUpdate, ProviderPaymentCreate,
    PurchaseInvoiceCreate, PurchaseInvoiceUpdate
)
from src.schemas.location import AddressCreate, AddressUpdate

logger = logging.getLogger(__name__)


class ProviderService:
    
    # ===== PROVIDER CRUD =====
    
    @staticmethod
    def create_provider(
        db: Session,
        data: ProviderCreate
    ) -> Provider:
        """
        Create a new provider with addresses using geography system
        """
        try:
            # Create provider
            provider = Provider(
                name=data.name,
                phone=data.phone,
                email=data.email,
                is_active=data.is_active,
                opening_balance=data.opening_balance,
                current_balance=data.opening_balance,
                anticipated_balance=0,
                created_at=date.today()
            )
            
            db.add(provider)
            db.flush()  # Get provider.id for addresses
            
            # Add addresses if provided
            if data.addresses:
                for addr_data in data.addferences:
                    # Verify geography references exist
                    country = db.query(Country).filter_by(id=addr_data.country_id).first()
                    if not country:
                        raise HTTPException(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            detail=f"Country with ID {addr_data.country_id} not found"
                        )
                    
                    address = Address(
                        street_1=addr_data.street_1,
                        street_2=addr_data.street_2,
                        is_default=addr_data.is_default,
                        country_id=addr_data.country_id,
                        region_id=addr_data.region_id,
                        city_id=addr_data.city_id,
                        provider_id=provider.id
                    )
                    db.add(address)
            
            db.commit()
            db.refresh(provider)
            
            logger.info(f"Provider created: {provider.name} (ID: {provider.id})")
            return provider
            
        except IntegrityError as e:
            db.rollback()
            logger.error(f"Integrity error creating provider: {e}")
            if "unique constraint" in str(e).lower():
                if "name" in str(e).lower():
                    detail = "Provider with this name already exists"
                elif "phone" in str(e).lower():
                    detail = "Provider with this phone already exists"
                elif "email" in str(e).lower():
                    detail = "Provider with this email already exists"
                else:
                    detail = "Duplicate provider data"
            else:
                detail = "Database integrity error"
                
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=detail
            )
        except HTTPException:
            raise
        except Exception as e:
            db.rollback()
            logger.error(f"Error creating provider: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create provider"
            )
    
    @staticmethod
    def get_provider(
        db: Session,
        provider_id: int,
        include_details: bool = True
    ) -> Optional[Provider]:
        """
        Get provider by ID with addresses and geography
        """
        query = db.query(Provider)
        
        if include_details:
            query = query.options(
                joinedload(Provider.addresses).joinedload(Address.country),
                joinedload(Provider.addresses).joinedload(Address.region),
                joinedload(Provider.addresses).joinedload(Address.city),
                selectinload(Provider.purchase_invoices),
                selectinload(Provider.payments),
                selectinload(Provider.purchase_returns)
            )
        
        return query.filter_by(id=provider_id).first()
    
    @staticmethod
    def list_providers(
        db: Session,
        search: Optional[str] = None,
        is_active: Optional[bool] = None,
        country_id: Optional[int] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Provider]:
        """
        List providers with filtering and search
        """
        query = db.query(Provider).options(
            joinedload(Provider.addresses).joinedload(Address.country),
            joinedload(Provider.addresses).joinedload(Address.region),
            joinedload(Provider.addresses).joinedload(Address.city)
        )
        
        if search:
            search_term = f"%{search}%"
            query = query.filter(
                or_(
                    Provider.name.ilike(search_term),
                    Provider.phone.ilike(search_term),
                    Provider.email.ilike(search_term)
                )
            )
        
        if is_active is not None:
            query = query.filter_by(is_active=is_active)
        
        if country_id:
            query = query.join(Address).filter(
                Address.provider_id == Provider.id,
                Address.country_id == country_id
            )
        
        query = query.order_by(Provider.name)
        
        return query.offset(offset).limit(limit).all()
    
    @staticmethod
    def update_provider(
        db: Session,
        provider_id: int,
        data: ProviderUpdate
    ) -> Provider:
        """
        Update provider information
        """
        provider = db.query(Provider).filter_by(id=provider_id).first()
        
        if not provider:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Provider not found"
            )
        
        update_data = data.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(provider, field, value)
        
        provider.updated_at = date.today()
        db.commit()
        db.refresh(provider)
        
        logger.info(f"Provider updated: {provider.name}")
        return provider
    
    @staticmethod
    def delete_provider(
        db: Session,
        provider_id: int
    ) -> bool:
        """
        Soft delete provider (set is_active = False)
        """
        provider = db.query(Provider).filter_by(id=provider_id).first()
        
        if not provider:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Provider not found"
            )
        
        # Check if provider has outstanding invoices
        outstanding_invoices = db.query(PurchaseInvoice).filter(
            PurchaseInvoice.provider_id == provider_id,
            PurchaseInvoice.status.in_([
                PurchaseInvoiceStatus.PENDING,
                PurchaseInvoiceStatus.PARTIALLY_PAID
            ]),
            PurchaseInvoice.due_amount > 0
        ).count()
        
        if outstanding_invoices > 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot delete provider with {outstanding_invoices} outstanding invoices"
            )
        
        provider.is_active = False
        provider.updated_at = date.today()
        db.commit()
        
        logger.info(f"Provider deactivated: {provider.name}")
        return True
    
    # ===== ADDRESS MANAGEMENT =====
    
    @staticmethod
    def add_provider_address(
        db: Session,
        provider_id: int,
        address_data: AddressCreate
    ) -> Address:
        """
        Add an address to a provider
        """
        provider = db.query(Provider).filter_by(id=provider_id).first()
        if not provider:
            raise HTTPException(404, "Provider not found")
        
        # Verify country exists
        country = db.query(Country).filter_by(id=address_data.country_id).first()
        if not country:
            raise HTTPException(400, f"Country with ID {address_data.country_id} not found")
        
        # Verify region if provided
        if address_data.region_id:
            region = db.query(Region).filter_by(id=address_data.region_id).first()
            if not region:
                raise HTTPException(400, f"Region with ID {address_data.region_id} not found")
        
        # Verify city if provided
        if address_data.city_id:
            city = db.query(City).filter_by(id=address_data.city_id).first()
            if not city:
                raise HTTPException(400, f"City with ID {address_data.city_id} not found")
        
        # If setting as default, unset other defaults
        if address_data.is_default:
            db.query(Address).filter_by(
                provider_id=provider_id,
                is_default=True
            ).update({"is_default": False})
        
        # Create address
        address = Address(
            street_1=address_data.street_1,
            street_2=address_data.street_2,
            is_default=address_data.is_default,
            country_id=address_data.country_id,
            region_id=address_data.region_id,
            city_id=address_data.city_id,
            provider_id=provider_id
        )
        
        db.add(address)
        db.commit()
        db.refresh(address)
        
        address = db.query(Address).options(
            joinedload(Address.country),
            joinedload(Address.region),
            joinedload(Address.city)
        ).filter_by(id=address.id).first()
        
        logger.info(f"Address added to provider {provider.name}")
        return address
    
    @staticmethod
    def update_provider_address(
        db: Session,
        provider_id: int,
        address_id: int,
        address_data: AddressUpdate
    ) -> Address:
        """
        Update a provider's address
        """
        address = db.query(Address).filter_by(
            id=address_id,
            provider_id=provider_id
        ).first()
        
        if not address:
            raise HTTPException(404, "Address not found or doesn't belong to this provider")
        
        update_data = address_data.dict(exclude_unset=True)
        
        if 'country_id' in update_data:
            country = db.query(Country).filter_by(id=update_data['country_id']).first()
            if not country:
                raise HTTPException(400, f"Country with ID {update_data['country_id']} not found")
        
        if 'region_id' in update_data and update_data['region_id']:
            region = db.query(Region).filter_by(id=update_data['region_id']).first()
            if not region:
                raise HTTPException(400, f"Region with ID {update_data['region_id']} not found")
        
        if 'city_id' in update_data and update_data['city_id']:
            city = db.query(City).filter_by(id=update_data['city_id']).first()
            if not city:
                raise HTTPException(400, f"City with ID {update_data['city_id']} not found")
        
        if update_data.get('is_default', False):
            db.query(Address).filter_by(
                provider_id=provider_id,
                is_default=True
            ).update({"is_default": False})
        
        for field, value in update_data.items():
            setattr(address, field, value)
        
        db.commit()
        db.refresh(address)
        
        address = db.query(Address).options(
            joinedload(Address.country),
            joinedload(Address.region),
            joinedload(Address.city)
        ).filter_by(id=address.id).first()
        
        logger.info(f"Address updated for provider ID {provider_id}")
        return address
    
    @staticmethod
    def delete_provider_address(
        db: Session,
        provider_id: int,
        address_id: int
    ) -> bool:
        """
        Delete a provider's address
        """
        address = db.query(Address).filter_by(
            id=address_id,
            provider_id=provider_id
        ).first()
        
        if not address:
            raise HTTPException(404, "Address not found or doesn't belong to this provider")
        
        db.delete(address)
        db.commit()
        
        logger.info(f"Address deleted from provider ID {provider_id}")
        return True
    
    @staticmethod
    def get_provider_addresses(
        db: Session,
        provider_id: int
    ) -> List[Address]:
        """
        Get all addresses for a provider with geography
        """
        return db.query(Address).options(
            joinedload(Address.country),
            joinedload(Address.region),
            joinedload(Address.city)
        ).filter_by(provider_id=provider_id).all()
    
    @staticmethod
    def get_provider_default_address(
        db: Session,
        provider_id: int
    ) -> Optional[Address]:
        """
        Get provider's default address
        """
        return db.query(Address).options(
            joinedload(Address.country),
            joinedload(Address.region),
            joinedload(Address.city)
        ).filter_by(
            provider_id=provider_id,
            is_default=True
        ).first()
    
    # ===== BALANCE CALCULATION =====
    
    @staticmethod
    def calculate_provider_balance(db: Session, provider_id: int) -> Dict:
        """
        Calculate provider's current balance
        Balance = Opening + Total Invoices - Total Payments - Total Returns
        """
        provider = db.query(Provider).filter_by(id=provider_id).first()
        
        if not provider:
            raise HTTPException(404, "Provider not found")
        
        # Get total invoices (excluding cancelled)
        total_invoices = db.query(func.coalesce(func.sum(PurchaseInvoice.total_amount), 0)).filter(
            PurchaseInvoice.provider_id == provider_id,
            PurchaseInvoice.status != PurchaseInvoiceStatus.CANCELLED
        ).scalar() or Decimal('0')
        
        # Get total payments
        total_payments = db.query(func.coalesce(func.sum(ProviderPayment.amount), 0)).filter(
            ProviderPayment.provider_id == provider_id
        ).scalar() or Decimal('0')
        
        # Get total returns
        total_returns = db.query(func.coalesce(func.sum(PurchaseReturn.amount), 0)).filter(
            PurchaseReturn.provider_id == provider_id
        ).scalar() or Decimal('0')
        
        # Calculate current balance
        current_balance = (
            provider.opening_balance +
            Decimal(str(total_invoices)) -
            Decimal(str(total_payments)) -
            Decimal(str(total_returns))
        )
        
        # Update provider's current balance
        provider.current_balance = current_balance
        provider.updated_at = date.today()
        db.commit()
        
        return {
            "provider_id": provider_id,
            "provider_name": provider.name,
            "opening_balance": provider.opening_balance,
            "total_invoices": Decimal(str(total_invoices)),
            "total_payments": Decimal(str(total_payments)),
            "total_returns": Decimal(str(total_returns)),
            "current_balance": current_balance,
            "outstanding_invoices": Decimal(str(total_invoices)) - Decimal(str(total_payments)),
            "last_updated": datetime.now(timezone.utc)
        }
    
    @staticmethod
    def get_provider_balance_history(
        db: Session,
        provider_id: int,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
    ) -> List[Dict]:
        """
        Get provider balance history over time
        """
        # This is a simplified version - in production you might want a ledger table
        payments = db.query(ProviderPayment).filter_by(provider_id=provider_id)
        invoices = db.query(PurchaseInvoice).filter_by(provider_id=provider_id)
        
        if start_date:
            payments = payments.filter(ProviderPayment.payment_date >= start_date)
            invoices = invoices.filter(PurchaseInvoice.invoice_date >= start_date)
        
        if end_date:
            payments = payments.filter(ProviderPayment.payment_date <= end_date)
            invoices = invoices.filter(PurchaseInvoice.invoice_date <= end_date)
        
        # Group by month for trend analysis
        from sqlalchemy import extract
        payment_trend = db.query(
            extract('year', ProviderPayment.payment_date).label('year'),
            extract('month', ProviderPayment.payment_date).label('month'),
            func.sum(ProviderPayment.amount).label('total_payments')
        ).filter_by(provider_id=provider_id).group_by('year', 'month').all()
        
        return {
            "payments_by_month": [
                {
                    "year": int(year),
                    "month": int(month),
                    "total_payments": float(total)
                } for year, month, total in payment_trend
            ]
        }
    
    # ===== PURCHASE INVOICE MANAGEMENT =====
    
    @staticmethod
    def create_purchase_invoice(
        db: Session,
        data: PurchaseInvoiceCreate
    ) -> PurchaseInvoice:
        """
        Create a purchase invoice
        """
        try:
            # Verify provider exists
            provider = db.query(Provider).filter_by(id=data.provider_id).first()
            if not provider:
                raise HTTPException(404, "Provider not found")
            
            # Check if invoice number already exists
            existing = db.query(PurchaseInvoice).filter_by(
                invoice_number=data.invoice_number
            ).first()
            
            if existing:
                raise HTTPException(400, "Invoice number already exists")
            
            # Verify procurement if provided
            if data.procurement_id:
                procurement = db.query(Procurement).filter_by(id=data.procurement_id).first()
                if not procurement:
                    raise HTTPException(404, "Procurement not found")
                if procurement.provider_id != data.provider_id:
                    raise HTTPException(400, "Procurement doesn't belong to this provider")
            
            # Create invoice
            invoice = PurchaseInvoice(
                provider_id=data.provider_id,
                procurement_id=data.procurement_id,
                invoice_number=data.invoice_number,
                invoice_date=data.invoice_date,
                posting_date=datetime.now(timezone.utc),
                due_date=data.due_date or data.invoice_date.replace(day=data.invoice_date.day + 30),
                total_amount=data.total_amount,
                paid_amount=0,
                po_reference=data.po_reference,
                status=PurchaseInvoiceStatus.PENDING,
                notes=data.notes
            )
            
            db.add(invoice)
            db.commit()
            db.refresh(invoice)
            
            # Update provider balance
            ProviderService.calculate_provider_balance(db, provider_id=data.provider_id)
            
            logger.info(f"Purchase invoice created: {invoice.invoice_number}")
            return invoice
            
        except IntegrityError as e:
            db.rollback()
            logger.error(f"Integrity error creating invoice: {e}")
            raise HTTPException(400, "Database integrity error")
        except HTTPException:
            raise
        except Exception as e:
            db.rollback()
            logger.error(f"Error creating invoice: {e}")
            raise HTTPException(500, "Failed to create purchase invoice")
    
    @staticmethod
    def get_purchase_invoice(
        db: Session,
        invoice_id: int
    ) -> Optional[PurchaseInvoice]:
        """
        Get purchase invoice with details
        """
        return db.query(PurchaseInvoice).options(
            joinedload(PurchaseInvoice.provider),
            joinedload(PurchaseInvoice.procurement).joinedload(Procurement.pos),
            selectinload(PurchaseInvoice.returns)
        ).filter_by(id=invoice_id).first()
    
    @staticmethod
    def list_provider_invoices(
        db: Session,
        provider_id: int,
        status: Optional[PurchaseInvoiceStatus] = None,
        overdue_only: bool = False,
        limit: int = 100,
        offset: int = 0
    ) -> List[PurchaseInvoice]:
        """
        List invoices for a provider
        """
        query = db.query(PurchaseInvoice).filter_by(provider_id=provider_id)
        
        if status:
            query = query.filter_by(status=status)
        
        if overdue_only:
            query = query.filter(
                PurchaseInvoice.due_date < datetime.now(timezone.utc),
                PurchaseInvoice.due_amount > 0
            )
        
        query = query.order_by(desc(PurchaseInvoice.invoice_date))
        
        return query.offset(offset).limit(limit).all()
    
    @staticmethod
    def update_purchase_invoice(
        db: Session,
        invoice_id: int,
        data: PurchaseInvoiceUpdate
    ) -> PurchaseInvoice:
        """
        Update purchase invoice
        """
        invoice = db.query(PurchaseInvoice).filter_by(id=invoice_id).first()
        
        if not invoice:
            raise HTTPException(404, "Invoice not found")
        
        update_data = data.dict(exclude_unset=True)
        
        if 'paid_amount' in update_data:
            new_paid = update_data['paid_amount']
            if new_paid < 0 or new_paid > invoice.total_amount:
                raise HTTPException(400, "Paid amount must be between 0 and total amount")
            
            invoice.paid_amount = new_paid
            
            if new_paid == 0:
                invoice.status = PurchaseInvoiceStatus.PENDING
            elif new_paid < invoice.total_amount:
                invoice.status = PurchaseInvoiceStatus.PARTIALLY_PAID
            else:
                invoice.status = PurchaseInvoiceStatus.PAID
        
        for field, value in update_data.items():
            if field != 'paid_amount':
                setattr(invoice, field, value)
        
        invoice.updated_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(invoice)
        
        ProviderService.calculate_provider_balance(db, provider_id=invoice.provider_id)
        
        logger.info(f"Purchase invoice updated: {invoice.invoice_number}")
        return invoice
    
    @staticmethod
    def cancel_purchase_invoice(
        db: Session,
        invoice_id: int,
        reason: Optional[str] = None
    ) -> PurchaseInvoice:
        """
        Cancel a purchase invoice
        """
        invoice = db.query(PurchaseInvoice).filter_by(id=invoice_id).first()
        
        if not invoice:
            raise HTTPException(404, "Invoice not found")
        
        if invoice.status == PurchaseInvoiceStatus.PAID:
            raise HTTPException(400, "Cannot cancel paid invoice")
        
        invoice.status = PurchaseInvoiceStatus.CANCELLED
        invoice.notes = f"{invoice.notes or ''}\nCancelled: {reason}".strip()
        invoice.updated_at = datetime.now(timezone.utc)
        
        db.commit()
        db.refresh(invoice)
        
        ProviderService.calculate_provider_balance(db, provider_id=invoice.provider_id)
        
        logger.info(f"Purchase invoice cancelled: {invoice.invoice_number}")
        return invoice
    
    # ===== PAYMENT MANAGEMENT =====
    
    @staticmethod
    def create_payment(
        db: Session,
        data: ProviderPaymentCreate
    ) -> ProviderPayment:
        """
        Record a payment to provider
        """
        try:
            provider = db.query(Provider).filter_by(id=data.provider_id).first()
            if not provider:
                raise HTTPException(404, "Provider not found")
            
            invoice = None
            if data.purchase_invoice_id:
                invoice = db.query(PurchaseInvoice).filter_by(id=data.purchase_invoice_id).first()
                if not invoice:
                    raise HTTPException(404, "Invoice not found")
                
                if invoice.provider_id != data.provider_id:
                    raise HTTPException(400, "Invoice doesn't belong to this provider")
                
                remaining = invoice.total_amount - invoice.paid_amount
                if data.amount > remaining:
                    raise HTTPException(
                        400,
                        f"Payment amount (${data.amount}) exceeds invoice balance (${remaining})"
                    )
                
                invoice.paid_amount += data.amount
                
                if invoice.paid_amount >= invoice.total_amount:
                    invoice.status = PurchaseInvoiceStatus.PAID
                elif invoice.paid_amount > 0:
                    invoice.status = PurchaseInvoiceStatus.PARTIALLY_PAID
                
                invoice.updated_at = datetime.now(timezone.utc)
            
            payment = ProviderPayment(
                provider_id=data.provider_id,
                purchase_invoice_id=data.purchase_invoice_id,
                payment_date=data.payment_date,
                amount=data.amount,
                payment_method=data.payment_method,
                reference=data.reference,
                notes=data.notes
            )
            
            db.add(payment)
            db.commit()
            
            ProviderService.calculate_provider_balance(db, provider_id=data.provider_id)
            
            logger.info(f"Payment recorded: ${data.amount} to provider {provider.name}")
            return payment
            
        except IntegrityError as e:
            db.rollback()
            logger.error(f"Integrity error recording payment: {e}")
            raise HTTPException(400, "Database integrity error")
        except HTTPException:
            raise
        except Exception as e:
            db.rollback()
            logger.error(f"Error recording payment: {e}")
            raise HTTPException(500, "Failed to record payment")
    
    @staticmethod
    def get_provider_payments(
        db: Session,
        provider_id: int,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[ProviderPayment]:
        """
        Get payments for a provider
        """
        query = db.query(ProviderPayment).filter_by(provider_id=provider_id)
        
        if start_date:
            query = query.filter(ProviderPayment.payment_date >= start_date)
        
        if end_date:
            query = query.filter(ProviderPayment.payment_date <= end_date)
        
        query = query.order_by(desc(ProviderPayment.payment_date))
        
        return query.offset(offset).limit(limit).all()
    
    @staticmethod
    def get_payment(
        db: Session,
        payment_id: int
    ) -> Optional[ProviderPayment]:
        """
        Get payment details
        """
        return db.query(ProviderPayment).options(
            joinedload(ProviderPayment.provider),
            joinedload(ProviderPayment.purchase_invoice)
        ).filter_by(id=payment_id).first()
    
    # ===== PURCHASE RETURNS =====
    
    @staticmethod
    def create_purchase_return(
        db: Session,
        provider_id: int,
        purchase_invoice_id: int,
        return_date: date,
        amount: Decimal,
        reason: str
    ) -> PurchaseReturn:
        """
        Record a purchase return
        """
        try:
            # Verify invoice exists and belongs to provider
            invoice = db.query(PurchaseInvoice).filter_by(
                id=purchase_invoice_id,
                provider_id=provider_id
            ).first()
            
            if not invoice:
                raise HTTPException(404, "Invoice not found or doesn't belong to provider")
            
            # Check if return amount is reasonable
            if amount <= 0:
                raise HTTPException(400, "Return amount must be positive")
            
            if amount > invoice.total_amount:
                raise HTTPException(400, "Return amount cannot exceed invoice total")
            
            # Create return
            purchase_return = PurchaseReturn(
                provider_id=provider_id,
                purchase_invoice_id=purchase_invoice_id,
                return_date=return_date,
                amount=amount,
                reason=reason
            )
            
            db.add(purchase_return)
            db.commit()
            
            # Update provider balance
            ProviderService.calculate_provider_balance(db, provider_id=provider_id)
            
            logger.info(f"Purchase return recorded: ${amount} for provider {provider_id}")
            return purchase_return
            
        except IntegrityError as e:
            db.rollback()
            logger.error(f"Integrity error creating return: {e}")
            raise HTTPException(400, "Database integrity error")
        except HTTPException:
            raise
        except Exception as e:
            db.rollback()
            logger.error(f"Error creating return: {e}")
            raise HTTPException(500, "Failed to record purchase return")
    
    @staticmethod
    def get_provider_returns(
        db: Session,
        provider_id: int,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
    ) -> List[PurchaseReturn]:
        """
        Get purchase returns for a provider
        """
        query = db.query(PurchaseReturn).filter_by(provider_id=provider_id)
        
        if start_date:
            query = query.filter(PurchaseReturn.return_date >= start_date)
        
        if end_date:
            query = query.filter(PurchaseReturn.return_date <= end_date)
        
        return query.order_by(desc(PurchaseReturn.return_date)).all()
    
    # ===== REPORTING & ANALYTICS =====
    
    @staticmethod
    def get_provider_summary(
        db: Session,
        provider_id: int
    ) -> Dict:
        """
        Get comprehensive provider summary
        """
        provider = db.query(Provider).filter_by(id=provider_id).first()
        
        if not provider:
            raise HTTPException(404, "Provider not found")
        
        # Invoice statistics
        invoices = db.query(PurchaseInvoice).filter_by(provider_id=provider_id)
        total_invoices = invoices.count()
        
        pending_invoices = invoices.filter_by(status=PurchaseInvoiceStatus.PENDING).count()
        paid_invoices = invoices.filter_by(status=PurchaseInvoiceStatus.PAID).count()
        partially_paid_invoices = invoices.filter_by(status=PurchaseInvoiceStatus.PARTIALLY_PAID).count()
        
        overdue_invoices = invoices.filter(
            PurchaseInvoice.due_date < datetime.now(timezone.utc),
            PurchaseInvoice.due_amount > 0
        ).count()
        
        # Amounts
        total_invoice_amount = db.query(
            func.coalesce(func.sum(PurchaseInvoice.total_amount), 0)
        ).filter_by(
            provider_id=provider_id,
            status=PurchaseInvoiceStatus.PAID
        ).scalar() or Decimal('0')
        
        total_paid_amount = db.query(
            func.coalesce(func.sum(ProviderPayment.amount), 0)
        ).filter_by(provider_id=provider_id).scalar() or Decimal('0')
        
        # Recent procurements
        recent_procurements = db.query(Procurement).filter_by(
            provider_id=provider_id
        ).order_by(desc(Procurement.po_date)).limit(5).all()
        
        # Recent payments
        recent_payments = db.query(ProviderPayment).filter_by(
            provider_id=provider_id
        ).order_by(desc(ProviderPayment.payment_date)).limit(5).all()
        
        # Calculate aging
        aging = ProviderService._calculate_invoice_aging(db, provider_id)
        
        return {
            "provider": {
                "id": provider.id,
                "name": provider.name,
                "current_balance": provider.current_balance,
                "is_active": provider.is_active,
                "created_at": provider.created_at
            },
            "statistics": {
                "total_invoices": total_invoices,
                "pending_invoices": pending_invoices,
                "paid_invoices": paid_invoices,
                "partially_paid_invoices": partially_paid_invoices,
                "overdue_invoices": overdue_invoices,
                "total_invoice_amount": Decimal(str(total_invoice_amount)),
                "total_paid_amount": Decimal(str(total_paid_amount)),
                "outstanding_balance": provider.current_balance
            },
            "aging": aging,
            "recent_procurements": recent_procurements,
            "recent_payments": recent_payments,
            "default_address": ProviderService.get_provider_default_address(db, provider_id)
        }
    
    @staticmethod
    def _calculate_invoice_aging(db: Session, provider_id: int) -> Dict:
        """
        Calculate invoice aging (0-30, 31-60, 61-90, 90+ days)
        """
        today = datetime.now(timezone.utc).date()
        
        aging = {
            "0_30": Decimal('0'),
            "31_60": Decimal('0'),
            "61_90": Decimal('0'),
            "90_plus": Decimal('0'),
            "total": Decimal('0')
        }
        
        invoices = db.query(PurchaseInvoice).filter(
            PurchaseInvoice.provider_id == provider_id,
            PurchaseInvoice.due_amount > 0,
            PurchaseInvoice.status.in_([
                PurchaseInvoiceStatus.PENDING,
                PurchaseInvoiceStatus.PARTIALLY_PAID
            ])
        ).all()
        
        for invoice in invoices:
            if invoice.due_date:
                days_overdue = (today - invoice.due_date.date()).days
                amount = invoice.due_amount
                
                if days_overdue <= 30:
                    aging["0_30"] += amount
                elif days_overdue <= 60:
                    aging["31_60"] += amount
                elif days_overdue <= 90:
                    aging["61_90"] += amount
                else:
                    aging["90_plus"] += amount
                
                aging["total"] += amount
        
        return aging
    
    @staticmethod
    def get_overdue_invoices(
        db: Session,
        days_overdue: int = 30
    ) -> List[PurchaseInvoice]:
        """
        Get all overdue invoices across all providers
        """
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days_overdue)
        
        return db.query(PurchaseInvoice).options(
            joinedload(PurchaseInvoice.provider)
        ).filter(
            PurchaseInvoice.due_date < datetime.now(timezone.utc),
            PurchaseInvoice.due_amount > 0,
            PurchaseInvoice.status.in_([
                PurchaseInvoiceStatus.PENDING,
                PurchaseInvoiceStatus.PARTIALLY_PAID
            ])
        ).order_by(PurchaseInvoice.due_date).all()
    
    @staticmethod
    def get_top_providers_by_purchases(
        db: Session,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        limit: int = 10
    ) -> List[Dict]:
        """
        Get top providers by purchase amount
        """
        query = db.query(
            Provider.id,
            Provider.name,
            func.count(PurchaseInvoice.id).label('invoice_count'),
            func.coalesce(func.sum(PurchaseInvoice.total_amount), 0).label('total_amount')
        ).join(
            PurchaseInvoice, Provider.id == PurchaseInvoice.provider_id
        ).filter(
            PurchaseInvoice.status != PurchaseInvoiceStatus.CANCELLED
        )
        
        if start_date:
            query = query.filter(PurchaseInvoice.invoice_date >= start_date)
        
        if end_date:
            query = query.filter(PurchaseInvoice.invoice_date <= end_date)
        
        return query.group_by(
            Provider.id, Provider.name
        ).order_by(
            desc('total_amount')
        ).limit(limit).all()
    
    @staticmethod
    def get_provider_performance_metrics(
        db: Session,
        provider_id: int,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
    ) -> Dict:
        """
        Get provider performance metrics
        """
        # Average payment time
        avg_payment_days = db.query(
            func.avg(
                func.extract('day', ProviderPayment.payment_date - PurchaseInvoice.invoice_date)
            )
        ).join(
            PurchaseInvoice, ProviderPayment.purchase_invoice_id == PurchaseInvoice.id
        ).filter(
            ProviderPayment.provider_id == provider_id,
            ProviderPayment.payment_date.isnot(None),
            PurchaseInvoice.invoice_date.isnot(None)
        ).scalar()
        
        # On-time payment rate
        on_time_payments = db.query(ProviderPayment).join(
            PurchaseInvoice, ProviderPayment.purchase_invoice_id == PurchaseInvoice.id
        ).filter(
            ProviderPayment.provider_id == provider_id,
            ProviderPayment.payment_date <= PurchaseInvoice.due_date
        ).count()
        
        total_payments = db.query(ProviderPayment).filter_by(
            provider_id=provider_id
        ).count()
        
        on_time_rate = (on_time_payments / total_payments * 100) if total_payments > 0 else 0
        
        return {
            "average_payment_days": float(avg_payment_days) if avg_payment_days else 0,
            "on_time_payment_rate": float(on_time_rate),
            "total_payments": total_payments,
            "on_time_payments": on_time_payments,
            "late_payments": total_payments - on_time_payments
        }