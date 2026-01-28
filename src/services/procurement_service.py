# src/services/procurement_service.py
from datetime import datetime, date, timedelta, timezone
from decimal import Decimal
from typing import List, Optional, Dict, Any, Tuple
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, desc, asc, and_, or_, extract
import logging

from src.models.procurement import (
    Procurement, ProcurementItem, ProcurementStatus
)
from src.models.pos import POS, POSUser
from src.models.providers import Provider
from src.models.catalog import ProductVariant
from src.models.inventory import Inventory
from src.schemas.procurement import (
    ProcurementCreate, ProcurementUpdate, ProcurementItemCreate
)
from src.services.inventory import InventoryService, NotFoundException, ValidationException, BusinessRuleException

logger = logging.getLogger(__name__)


class ProcurementService:
    
    # ================================
    # PROCUREMENT CRUD
    # ================================
    
    @staticmethod
    def generate_po_number(db: Session, pos_id: int) -> str:
        """Generate unique PO number: PO-{POS_ID}-{YYYYMM}-{SEQ}"""
        today = datetime.now(timezone.utc)
        year_month = today.strftime("%Y%m")
        
        # Count procurements for this POS this month
        count = db.query(Procurement).filter(
            Procurement.pos_id == pos_id,
            extract('year', Procurement.created_at) == today.year,
            extract('month', Procurement.created_at) == today.month
        ).count()
        
        next_number = count + 1
        return f"PO-{pos_id:04d}-{year_month}-{next_number:04d}"
    
    @staticmethod
    def create_procurement(
        db: Session,
        data: ProcurementCreate,
        pos_id: int,
        user_id: int
    ) -> Procurement:
        """Create a new procurement (purchase order)"""
        try:
            # Verify POS exists
            pos = db.query(POS).filter(POS.id == pos_id).first()
            if not pos:
                raise NotFoundException(f"POS {pos_id} not found")
            
            # Verify provider exists
            provider = db.query(Provider).filter(Provider.id == data.provider_id).first()
            if not provider:
                raise NotFoundException(f"Provider {data.provider_id} not found")
            
            # Verify all product variants exist
            for item in data.items:
                product_variant = db.query(ProductVariant).filter(
                    ProductVariant.id == item.product_variant_id
                ).first()
                if not product_variant:
                    raise NotFoundException(f"Product variant {item.product_variant_id} not found")
            
            # Generate PO number
            po_number = ProcurementService.generate_po_number(db, pos_id)
            
            # Calculate totals
            subtotal = sum(item.quantity * item.unit_price for item in data.items)
            tax = subtotal * (data.tax_rate or Decimal('0')) / 100
            total_amount = subtotal + tax
            
            # Create procurement
            procurement = Procurement(
                po_number=po_number,
                pos_id=pos_id,
                provider_id=data.provider_id,
                created_by_id=user_id,
                expected_delivery_date=data.expected_delivery_date,
                delivery_address=data.delivery_address,
                notes=data.notes,
                subtotal_amount=subtotal,
                tax_amount=tax,
                total_amount=total_amount,
                status=ProcurementStatus.PENDING,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc)
            )
            db.add(procurement)
            db.flush()  # Get procurement ID
            
            # Create procurement items
            for item_data in data.items:
                procurement_item = ProcurementItem(
                    procurement_id=procurement.id,
                    product_variant_id=item_data.product_variant_id,
                    quantity=item_data.quantity,
                    unit_price=item_data.unit_price,
                    created_at=datetime.now(timezone.utc)
                )
                db.add(procurement_item)
            
            db.commit()
            db.refresh(procurement)
            
            logger.info(f"Procurement created: {procurement.po_number} for POS {pos_id}")
            return procurement
            
        except Exception as e:
            db.rollback()
            logger.error(f"Error creating procurement: {str(e)}")
            raise
    
    @staticmethod
    def get_procurement(
        db: Session,
        procurement_id: int,
        include_details: bool = True
    ) -> Optional[Procurement]:
        """Get procurement by ID with optional details"""
        query = db.query(Procurement)
        
        if include_details:
            query = query.options(
                joinedload(Procurement.pos),
                joinedload(Procurement.provider),
                joinedload(Procurement.created_by),
                joinedload(Procurement.items).joinedload(ProcurementItem.product_variant)
                .joinedload(ProductVariant.product)
            )
        
        return query.filter(Procurement.id == procurement_id).first()
    
    @staticmethod
    def list_procurements(
        db: Session,
        pos_id: Optional[int] = None,
        provider_id: Optional[int] = None,
        status: Optional[ProcurementStatus] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Procurement]:
        """List procurements with filtering"""
        query = db.query(Procurement).options(
            joinedload(Procurement.pos),
            joinedload(Procurement.provider)
        )
        
        # Apply filters
        if pos_id:
            query = query.filter(Procurement.pos_id == pos_id)
        
        if provider_id:
            query = query.filter(Procurement.provider_id == provider_id)
        
        if status:
            query = query.filter(Procurement.status == status)
        
        # Apply pagination and ordering
        query = query.order_by(desc(Procurement.created_at)).offset(offset).limit(limit)
        
        return query.all()
    
    @staticmethod
    def update_procurement(
        db: Session,
        procurement_id: int,
        data: ProcurementUpdate
    ) -> Procurement:
        """Update procurement information"""
        procurement = ProcurementService.get_procurement(db, procurement_id, include_details=False)
        if not procurement:
            raise NotFoundException(f"Procurement {procurement_id} not found")
        
        # Check if procurement can be modified
        if procurement.status in [ProcurementStatus.DELIVERED, ProcurementStatus.CANCELLED]:
            raise BusinessRuleException(
                f"Cannot update procurement with status {procurement.status.value}"
            )
        
        try:
            # Update fields
            if data.expected_delivery_date is not None:
                procurement.expected_delivery_date = data.expected_delivery_date
            
            if data.delivery_address is not None:
                procurement.delivery_address = data.delivery_address
            
            if data.notes is not None:
                procurement.notes = data.notes
            
            procurement.updated_at = datetime.now(timezone.utc)
            db.commit()
            db.refresh(procurement)
            
            logger.info(f"Procurement updated: {procurement_id}")
            return procurement
            
        except Exception as e:
            db.rollback()
            logger.error(f"Error updating procurement {procurement_id}: {str(e)}")
            raise
    
    # ================================
    # PROCUREMENT WORKFLOW
    # ================================
    
    @staticmethod
    def mark_as_delivered(
        db: Session,
        procurement_id: int,
        user_id: int,
        delivery_notes: Optional[str] = None,
        driver_name: Optional[str] = None,
        driver_phone: Optional[str] = None
    ) -> Procurement:
        """
        Mark procurement as delivered and update inventory.
        """
        # Get procurement with lock for update
        procurement = db.query(Procurement).filter(
            Procurement.id == procurement_id
        ).with_for_update().first()
        
        if not procurement:
            raise NotFoundException(f"Procurement {procurement_id} not found")
        
        # Check if already delivered
        if procurement.status == ProcurementStatus.DELIVERED:
            raise BusinessRuleException("Procurement is already delivered")
        
        # Check if cancelled
        if procurement.status == ProcurementStatus.CANCELLED:
            raise BusinessRuleException("Cannot deliver cancelled procurement")
        
        try:
            # Update procurement status
            procurement.status = ProcurementStatus.DELIVERED
            procurement.delivered_at = datetime.now(timezone.utc)
            procurement.delivered_by_id = user_id
            procurement.delivery_notes = delivery_notes
            procurement.driver_name = driver_name
            procurement.driver_phone = driver_phone
            procurement.warehouse_id = procurement.pos.warehouse_id  # Link to POS warehouse
            procurement.updated_at = datetime.now(timezone.utc)
            
            # Get procurement items
            items = db.query(ProcurementItem).filter(
                ProcurementItem.procurement_id == procurement_id
            ).all()
            
            # Check if POS has warehouse
            if not procurement.pos.warehouse_id:
                raise BusinessRuleException(f"POS {procurement.pos_id} has no associated warehouse")
            
            # Update inventory for each item
            for item in items:
                # Increase stock in warehouse
                inventory_item = InventoryService.increase_stock(
                    db,
                    procurement.pos.warehouse_id,
                    item.product_variant_id,
                    item.quantity,
                    source=f"procurement_{procurement.po_number}"
                )
                
                logger.debug(
                    f"Stock increased: {item.quantity} units of product {item.product_variant_id}"
                )
            
            db.commit()
            db.refresh(procurement)
            
            logger.info(f"Procurement delivered: {procurement.po_number}")
            return procurement
            
        except Exception as e:
            db.rollback()
            logger.error(f"Error delivering procurement {procurement_id}: {str(e)}")
            raise
    
    @staticmethod
    def cancel_procurement(
        db: Session,
        procurement_id: int,
        reason: Optional[str] = None
    ) -> Procurement:
        """Cancel a procurement"""
        procurement = db.query(Procurement).filter(
            Procurement.id == procurement_id
        ).with_for_update().first()
        
        if not procurement:
            raise NotFoundException(f"Procurement {procurement_id} not found")
        
        # Check if already cancelled
        if procurement.status == ProcurementStatus.CANCELLED:
            raise BusinessRuleException("Procurement is already cancelled")
        
        # Check if already delivered
        if procurement.status == ProcurementStatus.DELIVERED:
            raise BusinessRuleException("Cannot cancel delivered procurement")
        
        try:
            procurement.status = ProcurementStatus.CANCELLED
            procurement.cancelled_at = datetime.now(timezone.utc)
            if reason:
                procurement.notes = f"{procurement.notes or ''}\nCancelled: {reason}".strip()
            procurement.updated_at = datetime.now(timezone.utc)
            
            db.commit()
            db.refresh(procurement)
            
            logger.info(f"Procurement cancelled: {procurement.po_number}")
            return procurement
            
        except Exception as e:
            db.rollback()
            logger.error(f"Error cancelling procurement {procurement_id}: {str(e)}")
            raise
    
    # ================================
    # REPORTS & ANALYTICS
    # ================================
    
    @staticmethod
    def get_procurement_summary(
        db: Session,
        pos_id: int
    ) -> Dict[str, Any]:
        """
        Get procurement summary for a POS.
        This method matches the route requirement.
        """
        # Count by status
        status_counts = db.execute(
            db.query(
                Procurement.status,
                func.count(Procurement.id).label('count')
            ).filter(Procurement.pos_id == pos_id)
            .group_by(Procurement.status)
        ).all()
        
        # Total amount by status
        amount_by_status = db.execute(
            db.query(
                Procurement.status,
                func.sum(Procurement.total_amount).label('total')
            ).filter(Procurement.pos_id == pos_id)
            .group_by(Procurement.status)
        ).all()
        
        # Total counts
        total_count = sum(count for _, count in status_counts)
        total_amount = sum(amount for _, amount in amount_by_status)
        
        # Convert to dict
        summary = {
            "pos_id": pos_id,
            "total_procurements": total_count,
            "total_amount": float(total_amount) if total_amount else 0.0,
            "by_status": {},
            "amount_by_status": {}
        }
        
        # Fill status dictionaries
        for status, count in status_counts:
            summary["by_status"][status.value] = count
        
        for status, amount in amount_by_status:
            summary["amount_by_status"][status.value] = float(amount) if amount else 0.0
        
        # Get recent procurements (last 5)
        recent_procurements = db.query(Procurement).filter(
            Procurement.pos_id == pos_id
        ).order_by(desc(Procurement.created_at)).limit(5).all()
        
        summary["recent_procurements"] = [
            {
                "id": p.id,
                "po_number": p.po_number,
                "provider_id": p.provider_id,
                "status": p.status.value,
                "total_amount": float(p.total_amount),
                "created_at": p.created_at,
                "expected_delivery_date": p.expected_delivery_date
            } for p in recent_procurements
        ]
        
        return summary
    
    @staticmethod
    def get_provider_performance(
        db: Session,
        provider_id: Optional[int] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
    ) -> Dict[str, Any]:
        """Get provider performance metrics"""
        query = db.query(Procurement)
        
        if provider_id:
            query = query.filter(Procurement.provider_id == provider_id)
        
        if start_date:
            query = query.filter(Procurement.created_at >= start_date)
        
        if end_date:
            query = query.filter(Procurement.created_at <= end_date)
        
        # Get delivered procurements
        delivered = query.filter(Procurement.status == ProcurementStatus.DELIVERED).all()
        
        # Calculate metrics
        total_procurements = len(delivered)
        total_amount = sum(p.total_amount for p in delivered)
        
        # Calculate average delivery time
        avg_delivery_days = None
        if delivered:
            total_days = 0
            count = 0
            for p in delivered:
                if p.expected_delivery_date and p.delivered_at:
                    delivery_date = p.delivered_at.date()
                    expected_date = p.expected_delivery_date
                    if isinstance(expected_date, datetime):
                        expected_date = expected_date.date()
                    days = (delivery_date - expected_date).days
                    total_days += days
                    count += 1
            
            if count > 0:
                avg_delivery_days = total_days / count
        
        return {
            "total_procurements": total_procurements,
            "total_amount": float(total_amount),
            "average_order_value": float(total_amount / total_procurements) if total_procurements > 0 else 0,
            "average_delivery_days": avg_delivery_days,
            "on_time_rate": None  # Would need more data
        }
    
    @staticmethod
    def get_procurement_trend(
        db: Session,
        pos_id: Optional[int] = None,
        days: int = 30
    ) -> List[Dict[str, Any]]:
        """Get procurement trend over time"""
        end_date = datetime.now(timezone.utc).date()
        start_date = end_date - timedelta(days=days - 1)
        
        # Generate date range
        date_range = []
        current_date = start_date
        while current_date <= end_date:
            date_range.append(current_date)
            current_date += timedelta(days=1)
        
        # Get daily procurements
        daily_procurements = db.execute(
            db.query(
                func.date(Procurement.created_at).label('procurement_date'),
                func.count(Procurement.id).label('count'),
                func.sum(Procurement.total_amount).label('daily_total')
            ).filter(
                Procurement.created_at >= start_date,
                Procurement.created_at <= end_date,
                Procurement.pos_id == pos_id if pos_id else True
            ).group_by(func.date(Procurement.created_at))
            .order_by(func.date(Procurement.created_at))
        ).all()
        
        # Create trend data
        trend_map = {row.procurement_date: row for row in daily_procurements}
        
        trend_data = []
        for date in date_range:
            procurement_data = trend_map.get(date)
            trend_data.append({
                "date": date,
                "procurement_count": procurement_data.count if procurement_data else 0,
                "total_amount": float(procurement_data.daily_total or Decimal('0')) if procurement_data else 0.0
            })
        
        return trend_data
    
    # ================================
    # VALIDATION METHODS
    # ================================
    
    @staticmethod
    def validate_procurement_delivery(
        db: Session,
        procurement_id: int
    ) -> Dict[str, Any]:
        """Validate if procurement can be delivered (pre-check)"""
        procurement = ProcurementService.get_procurement(db, procurement_id, include_details=False)
        if not procurement:
            raise NotFoundException(f"Procurement {procurement_id} not found")
        
        # Check current status
        if procurement.status == ProcurementStatus.DELIVERED:
            return {
                "can_deliver": False,
                "reason": "Already delivered",
                "current_status": procurement.status.value
            }
        
        if procurement.status == ProcurementStatus.CANCELLED:
            return {
                "can_deliver": False,
                "reason": "Procurement is cancelled",
                "current_status": procurement.status.value
            }
        
        # Check if POS has warehouse
        pos = db.query(POS).filter(POS.id == procurement.pos_id).first()
        if not pos or not pos.warehouse_id:
            return {
                "can_deliver": False,
                "reason": f"POS {procurement.pos_id} has no associated warehouse",
                "current_status": procurement.status.value
            }
        
        # Get items
        items = db.query(ProcurementItem).filter(
            ProcurementItem.procurement_id == procurement_id
        ).all()
        
        # All checks passed
        return {
            "can_deliver": True,
            "procurement_id": procurement_id,
            "po_number": procurement.po_number,
            "pos_id": procurement.pos_id,
            "warehouse_id": pos.warehouse_id,
            "item_count": len(items),
            "current_status": procurement.status.value
        }