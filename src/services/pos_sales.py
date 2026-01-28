# src/services/sale_service.py
from datetime import datetime, date, timedelta
from decimal import Decimal
from typing import List, Optional, Dict, Any, Tuple
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, desc, asc, and_, or_, extract
import logging

from src.models.pos import (
    Sale, SaleItem, SaleReturn, SaleCustomerInfo, SaleStatus, PaymentMethod
)
from src.models.pos import POS, POSUser
from src.models.clients import Client
from src.models.catalog import ProductVariant
from src.schemas.pos import (
    SaleCreate, SaleItemCreate, SaleUpdate, 
    SaleReturnCreate, CustomerInfoCreate
)
from src.services.inventory import InventoryService
from src.services.pos import POSService, POSUserService

logger = logging.getLogger(__name__)


# ================================
# CUSTOM EXCEPTIONS
# ================================
class SaleException(Exception):
    """Base exception for sale operations"""
    def __init__(self, message: str, status_code: int = 400):
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)


class SaleNotFoundException(SaleException):
    """Raised when a sale is not found"""
    def __init__(self, message: str = "Sale not found"):
        super().__init__(message, status_code=404)


class SaleValidationException(SaleException):
    """Raised when sale validation fails"""
    def __init__(self, message: str = "Sale validation failed"):
        super().__init__(message, status_code=400)


class SaleBusinessRuleException(SaleException):
    """Raised when a sale business rule is violated"""
    def __init__(self, message: str = "Sale business rule violation"):
        super().__init__(message, status_code=422)


# ================================
# SALE SERVICE
# ================================
class SaleService:
    
    # ================================
    # SALE CREATION & MANAGEMENT
    # ================================
    
    @staticmethod
    def create_sale(db: Session, data: SaleCreate) -> Sale:
        """Create a new sale with inventory validation"""
        try:
            # Verify POS exists and get warehouse
            pos = POSService.get_pos(db, data.pos_id)
            if not pos:
                raise SaleNotFoundException(f"POS {data.pos_id} not found")
            
            # Get warehouse for inventory validation
            try:
                warehouse = InventoryService.get_warehouse_by_pos(db, data.pos_id)
            except Exception:
                raise SaleValidationException(f"POS {data.pos_id} has no associated warehouse")
            
            # Verify user exists
            user = POSUserService.get_pos_user_by_id(db, data.created_by_id)
            if not user:
                raise SaleNotFoundException(f"User {data.created_by_id} not found")
            
            # Verify customer if provided
            customer = None
            if data.customer_id:
                customer = db.query(Client).filter(Client.id == data.customer_id).first()
                if not customer:
                    raise SaleNotFoundException(f"Customer {data.customer_id} not found")
            
            # Check stock availability for all items
            for item in data.items:
                stock_check = InventoryService.check_stock_availability(
                    db, warehouse.id, item.product_variant_id, item.qty
                )
                if not stock_check["is_available"]:
                    raise SaleValidationException(
                        f"Insufficient stock for product variant {item.product_variant_id}. "
                        f"Available: {stock_check['available']}, Required: {item.qty}"
                    )
            
            # Calculate totals
            subtotal = sum(item.qty * item.unit_price for item in data.items)
            tax = subtotal * (data.tax_rate or Decimal('0')) / 100
            discount = data.discount_amount or Decimal('0')
            total_amount = subtotal + tax - discount
            
            # Create sale
            sale = Sale(
                pos_id=data.pos_id,
                created_by_id=data.created_by_id,
                customer_id=data.customer_id,
                subtotal_amount=subtotal,
                tax_amount=tax,
                discount_amount=discount,
                total_amount=total_amount,
                payment_mode=data.payment_mode,
                status=SaleStatus.COMPLETED,
                transaction_date=data.transaction_date or datetime.utcnow(),
                notes=data.notes,
                created_at=datetime.utcnow()
            )
            db.add(sale)
            db.flush()  # Get sale ID
            
            # Create sale items
            sale_items_data = []
            for item_data in data.items:
                sale_item = SaleItem(
                    sale_id=sale.id,
                    product_variant_id=item_data.product_variant_id,
                    qty=item_data.qty,
                    unit_price=item_data.unit_price
                )
                db.add(sale_item)
                sale_items_data.append({
                    "product_variant_id": item_data.product_variant_id,
                    "quantity": item_data.qty
                })
            
            # Create customer info if provided (for counter sales)
            if data.customer_info:
                customer_info = SaleCustomerInfo(
                    sale_id=sale.id,
                    first_name=data.customer_info.first_name,
                    last_name=data.customer_info.last_name,
                    phone=data.customer_info.phone
                )
                db.add(customer_info)
            
            # Update inventory (reserve and then deduct)
            try:
                # Process sale items in inventory
                InventoryService.process_sale_items(db, data.pos_id, sale_items_data)
                
                # Finalize sale (deduct from reserved)
                InventoryService.finalize_sale(db, sale.id, data.pos_id, sale_items_data)
                
            except Exception as e:
                # If inventory update fails, cancel the sale
                db.rollback()
                raise SaleValidationException(f"Inventory update failed: {str(e)}")
            
            db.commit()
            db.refresh(sale)
            
            logger.info(f"Sale created: {sale.id} at POS {data.pos_id}")
            return sale
            
        except SaleException:
            db.rollback()
            raise
        except Exception as e:
            db.rollback()
            logger.error(f"Error creating sale: {str(e)}")
            raise SaleValidationException(f"Error creating sale: {str(e)}")
    
    @staticmethod
    def get_sale(db: Session, sale_id: int) -> Sale:
        """Get sale by ID with all relationships"""
        sale = db.query(Sale).options(
            joinedload(Sale.pos),
            joinedload(Sale.created_by),
            joinedload(Sale.customer),
            joinedload(Sale.items).joinedload(SaleItem.product_variant).joinedload(ProductVariant.product),
            joinedload(Sale.counter_customer),
            joinedload(Sale.returns)
        ).filter(
            Sale.id == sale_id
        ).first()
        
        if not sale:
            raise SaleNotFoundException(f"Sale {sale_id} not found")
        
        return sale
    
    @staticmethod
    def update_sale(db: Session, sale_id: int, data: SaleUpdate) -> Sale:
        """Update sale information (limited updates allowed)"""
        sale = SaleService.get_sale(db, sale_id)
        
        # Check if sale can be modified
        if sale.status == SaleStatus.CANCELLED:
            raise SaleBusinessRuleException("Cannot update cancelled sale")
        
        try:
            # Only allow updating notes and status
            if data.notes is not None:
                sale.notes = data.notes
            
            if data.status is not None:
                # Validate status transition
                if data.status == SaleStatus.CANCELLED:
                    # Cannot cancel completed sales (would need return flow)
                    if sale.status == SaleStatus.COMPLETED:
                        raise SaleBusinessRuleException("Cannot cancel completed sale. Create a return instead.")
                    sale.status = data.status
                else:
                    sale.status = data.status
            
            db.commit()
            db.refresh(sale)
            
            logger.info(f"Sale updated: {sale_id}")
            return sale
            
        except SaleException:
            db.rollback()
            raise
        except Exception as e:
            db.rollback()
            logger.error(f"Error updating sale {sale_id}: {str(e)}")
            raise SaleValidationException(f"Error updating sale: {str(e)}")
    
    @staticmethod
    def cancel_sale(db: Session, sale_id: int, reason: str = None) -> Sale:
        """Cancel a sale (only for pending/partial sales)"""
        sale = SaleService.get_sale(db, sale_id)
        
        if sale.status == SaleStatus.CANCELLED:
            raise SaleBusinessRuleException("Sale is already cancelled")
        
        if sale.status == SaleStatus.COMPLETED:
            raise SaleBusinessRuleException("Cannot cancel completed sale. Create a return instead.")
        
        try:
            # Get sale items for inventory restoration
            sale_items = db.query(SaleItem).filter(SaleItem.sale_id == sale_id).all()
            
            # Prepare items data for inventory release
            items_data = []
            for item in sale_items:
                items_data.append({
                    "product_variant_id": item.product_variant_id,
                    "quantity": item.qty
                })
            
            # Release reserved stock if any
            if items_data:
                InventoryService.cancel_sale_reservations(db, sale.pos_id, items_data)
            
            # Update sale status
            sale.status = SaleStatus.CANCELLED
            if reason:
                sale.notes = f"{sale.notes or ''}\nCancelled: {reason}".strip()
            
            db.commit()
            db.refresh(sale)
            
            logger.info(f"Sale cancelled: {sale_id}")
            return sale
            
        except SaleException:
            db.rollback()
            raise
        except Exception as e:
            db.rollback()
            logger.error(f"Error cancelling sale {sale_id}: {str(e)}")
            raise SaleValidationException(f"Error cancelling sale: {str(e)}")
    
    @staticmethod
    def list_sales(
        db: Session,
        pos_id: Optional[int] = None,
        customer_id: Optional[int] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        status: Optional[SaleStatus] = None,
        payment_mode: Optional[PaymentMethod] = None,
        skip: int = 0,
        limit: int = 50
    ) -> Tuple[List[Sale], int]:
        """List sales with filtering"""
        query = db.query(Sale).options(
            joinedload(Sale.pos),
            joinedload(Sale.customer),
            joinedload(Sale.created_by)
        )
        
        # Apply filters
        if pos_id:
            query = query.filter(Sale.pos_id == pos_id)
        
        if customer_id:
            query = query.filter(Sale.customer_id == customer_id)
        
        if start_date:
            query = query.filter(Sale.transaction_date >= start_date)
        
        if end_date:
            query = query.filter(Sale.transaction_date <= end_date)
        
        if status:
            query = query.filter(Sale.status == status)
        
        if payment_mode:
            query = query.filter(Sale.payment_mode == payment_mode)
        
        # Get total count
        total = query.count()
        
        # Apply pagination
        sales = query.order_by(desc(Sale.transaction_date)).offset(skip).limit(limit).all()
        
        return sales, total
    
    @staticmethod
    def get_sales_summary(
        db: Session,
        pos_id: Optional[int] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
    ) -> Dict[str, Any]:
        """Get sales summary statistics"""
        query = db.query(Sale)
        
        if pos_id:
            query = query.filter(Sale.pos_id == pos_id)
        
        if start_date:
            query = query.filter(Sale.transaction_date >= start_date)
        
        if end_date:
            query = query.filter(Sale.transaction_date <= end_date)
        
        # Total sales count
        total_sales = query.count()
        
        # Total revenue
        total_revenue_result = db.session.execute(
            func.sum(Sale.total_amount).filter(
                Sale.status == SaleStatus.COMPLETED,
                Sale.pos_id == pos_id if pos_id else True,
                Sale.transaction_date >= start_date if start_date else True,
                Sale.transaction_date <= end_date if end_date else True
            )
        ).scalar() or Decimal('0')
        
        # Average sale value
        avg_sale_value = total_revenue_result / total_sales if total_sales > 0 else Decimal('0')
        
        # Sales by payment method
        payment_methods = db.session.execute(
            db.query(
                Sale.payment_mode,
                func.count(Sale.id).label('count'),
                func.sum(Sale.total_amount).label('total')
            ).filter(
                Sale.status == SaleStatus.COMPLETED,
                Sale.pos_id == pos_id if pos_id else True,
                Sale.transaction_date >= start_date if start_date else True,
                Sale.transaction_date <= end_date if end_date else True
            ).group_by(Sale.payment_mode)
        ).all()
        
        # Recent sales
        recent_sales = query.filter(
            Sale.status == SaleStatus.COMPLETED
        ).order_by(desc(Sale.transaction_date)).limit(5).all()
        
        return {
            "total_sales": total_sales,
            "total_revenue": float(total_revenue_result),
            "average_sale_value": float(avg_sale_value),
            "payment_methods": [
                {
                    "method": method.value,
                    "count": count,
                    "total": float(total or Decimal('0'))
                } for method, count, total in payment_methods
            ],
            "recent_sales": [
                {
                    "id": sale.id,
                    "date": sale.transaction_date,
                    "amount": float(sale.total_amount),
                    "customer": sale.customer.name if sale.customer else "Walk-in"
                } for sale in recent_sales
            ]
        }
    
    # ================================
    # SALE RETURNS
    # ================================
    
    @staticmethod
    def create_sale_return(db: Session, data: SaleReturnCreate) -> SaleReturn:
        """Create a sale return with inventory restoration"""
        try:
            # Verify sale exists
            sale = SaleService.get_sale(db, data.sale_id)
            if not sale:
                raise SaleNotFoundException(f"Sale {data.sale_id} not found")
            
            # Check if sale is eligible for return
            if sale.status == SaleStatus.CANCELLED:
                raise SaleBusinessRuleException("Cannot return items from cancelled sale")
            
            # Verify return items exist in the sale
            returned_items = []
            for return_item in data.items:
                sale_item = db.query(SaleItem).filter(
                    SaleItem.sale_id == data.sale_id,
                    SaleItem.product_variant_id == return_item.product_variant_id
                ).first()
                
                if not sale_item:
                    raise SaleValidationException(
                        f"Product variant {return_item.product_variant_id} not found in sale {data.sale_id}"
                    )
                
                if return_item.quantity > sale_item.qty:
                    raise SaleValidationException(
                        f"Return quantity ({return_item.quantity}) exceeds sold quantity ({sale_item.qty}) "
                        f"for product variant {return_item.product_variant_id}"
                    )
                
                returned_items.append({
                    "sale_item": sale_item,
                    "return_item": return_item
                })
            
            # Create return record
            sale_return = SaleReturn(
                sale_id=data.sale_id,
                date=data.date or datetime.utcnow(),
                reason=data.reason,
                created_at=datetime.utcnow()
            )
            db.add(sale_return)
            db.flush()  # Get return ID
            
            # Restore inventory for returned items
            for item_data in returned_items:
                sale_item = item_data["sale_item"]
                return_item = item_data["return_item"]
                
                # Increase stock in warehouse
                try:
                    InventoryService.increase_stock(
                        db,
                        sale.pos.warehouse_id,
                        return_item.product_variant_id,
                        return_item.quantity,
                        source=f"sale_return_{sale_return.id}"
                    )
                except Exception as e:
                    raise SaleValidationException(
                        f"Failed to restore inventory for product variant {return_item.product_variant_id}: {str(e)}"
                    )
            
            # Update sale status if all items returned
            total_returned = sum(item.quantity for item in data.items)
            total_sold = sum(item.qty for item in sale.items)
            
            if total_returned == total_sold:
                sale.status = SaleStatus.CANCELLED
            elif total_returned > 0:
                sale.status = SaleStatus.PARTIAL
            
            db.commit()
            db.refresh(sale_return)
            
            logger.info(f"Sale return created: {sale_return.id} for sale {data.sale_id}")
            return sale_return
            
        except SaleException:
            db.rollback()
            raise
        except Exception as e:
            db.rollback()
            logger.error(f"Error creating sale return: {str(e)}")
            raise SaleValidationException(f"Error creating sale return: {str(e)}")
    
    @staticmethod
    def get_sale_returns(
        db: Session,
        sale_id: Optional[int] = None,
        pos_id: Optional[int] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
    ) -> List[SaleReturn]:
        """Get sale returns with filtering"""
        query = db.query(SaleReturn).options(
            joinedload(SaleReturn.sale).joinedload(Sale.pos)
        )
        
        if sale_id:
            query = query.filter(SaleReturn.sale_id == sale_id)
        
        if pos_id:
            query = query.join(Sale).filter(Sale.pos_id == pos_id)
        
        if start_date:
            query = query.filter(SaleReturn.date >= start_date)
        
        if end_date:
            query = query.filter(SaleReturn.date <= end_date)
        
        returns = query.order_by(desc(SaleReturn.date)).all()
        
        return returns
    
    # ================================
    # REPORTING & ANALYTICS
    # ================================
    
    @staticmethod
    def get_daily_sales_report(
        db: Session,
        pos_id: Optional[int] = None,
        date: Optional[date] = None
    ) -> Dict[str, Any]:
        """Get daily sales report"""
        report_date = date or datetime.utcnow().date()
        
        # Get sales for the day
        sales = db.query(Sale).filter(
            func.date(Sale.transaction_date) == report_date,
            Sale.status == SaleStatus.COMPLETED,
            Sale.pos_id == pos_id if pos_id else True
        ).all()
        
        # Calculate totals
        total_sales = len(sales)
        total_revenue = sum(sale.total_amount for sale in sales)
        
        # Get top selling products
        top_products = db.session.execute(
            db.query(
                ProductVariant.product_id,
                func.sum(SaleItem.qty).label('total_qty'),
                func.sum(SaleItem.qty * SaleItem.unit_price).label('total_value')
            ).join(SaleItem, Sale.id == SaleItem.sale_id)
            .join(ProductVariant, SaleItem.product_variant_id == ProductVariant.id)
            .filter(
                func.date(Sale.transaction_date) == report_date,
                Sale.status == SaleStatus.COMPLETED,
                Sale.pos_id == pos_id if pos_id else True
            ).group_by(ProductVariant.product_id)
            .order_by(desc('total_qty'))
            .limit(5)
        ).all()
        
        return {
            "date": report_date,
            "total_sales": total_sales,
            "total_revenue": float(total_revenue),
            "top_products": [
                {
                    "product_id": product_id,
                    "total_quantity": float(total_qty),
                    "total_value": float(total_value or Decimal('0'))
                } for product_id, total_qty, total_value in top_products
            ],
            "sales": [
                {
                    "id": sale.id,
                    "time": sale.transaction_date.time(),
                    "amount": float(sale.total_amount),
                    "payment_method": sale.payment_mode.value,
                    "customer": sale.customer.name if sale.customer else "Walk-in"
                } for sale in sales
            ]
        }
    
    @staticmethod
    def get_sales_trend(
        db: Session,
        pos_id: Optional[int] = None,
        days: int = 30
    ) -> List[Dict[str, Any]]:
        """Get sales trend over time"""
        end_date = datetime.utcnow().date()
        start_date = end_date - timedelta(days=days - 1)
        
        # Generate date range
        date_range = []
        current_date = start_date
        while current_date <= end_date:
            date_range.append(current_date)
            current_date += timedelta(days=1)
        
        # Get daily sales
        daily_sales = db.session.execute(
            db.query(
                func.date(Sale.transaction_date).label('sale_date'),
                func.count(Sale.id).label('sale_count'),
                func.sum(Sale.total_amount).label('daily_total')
            ).filter(
                Sale.transaction_date >= start_date,
                Sale.transaction_date <= end_date,
                Sale.status == SaleStatus.COMPLETED,
                Sale.pos_id == pos_id if pos_id else True
            ).group_by(func.date(Sale.transaction_date))
            .order_by(func.date(Sale.transaction_date))
        ).all()
        
        # Create trend data
        trend_map = {row.sale_date: row for row in daily_sales}
        
        trend_data = []
        for date in date_range:
            sales_data = trend_map.get(date)
            trend_data.append({
                "date": date,
                "sales_count": sales_data.sale_count if sales_data else 0,
                "total_amount": float(sales_data.daily_total or Decimal('0')) if sales_data else 0.0
            })
        
        return trend_data
    
    @staticmethod
    def get_top_products_report(
        db: Session,
        pos_id: Optional[int] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Get top selling products report"""
        query = db.query(
            ProductVariant,
            func.sum(SaleItem.qty).label('total_qty'),
            func.sum(SaleItem.qty * SaleItem.unit_price).label('total_value')
        ).join(SaleItem, SaleItem.product_variant_id == ProductVariant.id).join(Sale, SaleItem.sale_id == Sale.id).filter(
            Sale.status == SaleStatus.COMPLETED,
            Sale.pos_id == pos_id if pos_id else True
        )
        
        if start_date:
            query = query.filter(Sale.transaction_date >= start_date)
        
        if end_date:
            query = query.filter(Sale.transaction_date <= end_date)
        
        results = query.group_by(ProductVariant.id).order_by(desc('total_qty')).limit(limit).all()
        
        top_products = []
        for variant, total_qty, total_value in results:
            top_products.append({
                "product_variant_id": variant.id,
                "variant_name": variant.name,
                "product_id": variant.product_id,
                "total_quantity": float(total_qty or Decimal('0')),
                "total_value": float(total_value or Decimal('0'))
            })
        
        return top_products