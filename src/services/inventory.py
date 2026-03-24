# src/services/inventory_service.py
from datetime import datetime, date, timezone
from decimal import Decimal
from fastapi import HTTPException, status
from typing import List, Optional, Dict, Any, Tuple
from sqlalchemy.orm import Session, joinedload, selectinload
from sqlalchemy import func, desc, asc, and_, or_, case, text, select
import logging

from src.models.inventory import Inventory, Warehouse
from src.models.pos import POS
from src.models.procurement import Procurement, ProcurementItem, ProcurementStatus
from src.models.pos import SaleItem
from src.models.catalog import ProductVariant, Product
from src.schemas.inventory import (
    InventoryBulkCreate, InventoryUpdate, WarehouseCreate, WarehouseUpdate
)

logger = logging.getLogger(__name__)


# ================================
# CUSTOM EXCEPTIONS
# ================================
class InventoryException(Exception):
    """Base exception for inventory operations"""
    def __init__(self, message: str, status_code: int = 400):
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)


class NotFoundException(InventoryException):
    """Raised when a resource is not found"""
    def __init__(self, message: str = "Resource not found"):
        super().__init__(message, status_code=404)


class ValidationException(InventoryException):
    """Raised when validation fails"""
    def __init__(self, message: str = "Validation failed"):
        super().__init__(message, status_code=400)


class BusinessRuleException(InventoryException):
    """Raised when a business rule is violated"""
    def __init__(self, message: str = "Business rule violation"):
        super().__init__(message, status_code=422)


class InsufficientStockException(InventoryException):
    """Raised when there's insufficient stock"""
    def __init__(self, message: str = "Insufficient stock"):
        super().__init__(message, status_code=400)


# ================================
# INVENTORY SERVICE
# ================================
class InventoryService:
    
    # ================================
    # WAREHOUSE MANAGEMENT
    # ================================
    
    @staticmethod
    def create_warehouse(db: Session, data: WarehouseCreate) -> Warehouse:
        """Create a new warehouse"""
        try:
            # Check for duplicate name
            existing = db.query(Warehouse).filter(
                Warehouse.name == data.name
            ).first()
            
            if existing:
                raise ValidationException(f"Warehouse with name '{data.name}' already exists")
            
            # Create warehouse
            warehouse = Warehouse(
                name=data.name,
                location=data.location,
                is_active=data.is_active if data.is_active is not None else True,
            )
            
            db.add(warehouse)
            db.commit()
            db.refresh(warehouse)
            
            logger.info(f"Warehouse created: {warehouse.id} - {warehouse.name}")
            return warehouse
            
        except InventoryException:
            db.rollback()
            raise
        except Exception as e:
            db.rollback()
            logger.error(f"Error creating warehouse: {str(e)}")
            raise HTTPException(status.HTTP_510_NOT_EXTENDED, detail=f"Error creating warehouse: {str(e)}")
    
    @staticmethod
    def update_warehouse(db: Session, warehouse_id: int, data: WarehouseUpdate) -> Warehouse:
        """Update warehouse information"""
        warehouse = db.query(Warehouse).filter(Warehouse.id == warehouse_id).first()
        if not warehouse:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail=f"Warehouse {warehouse_id} not found")
        
        try:
            # Check name uniqueness if changing
            if data.name and data.name != warehouse.name:
                existing = db.query(Warehouse).filter(
                    Warehouse.name == data.name,
                    Warehouse.id != warehouse_id
                ).first()
                if existing:
                    raise HTTPException(status.HTTP_406_NOT_ACCEPTABLE, detail=f"Warehouse with name '{data.name}' already exists")
            
            # Update fields
            if data.name is not None:
                warehouse.name = data.name
            if data.location is not None:
                warehouse.location = data.location
            if data.is_active is not None:
                warehouse.is_active = data.is_active
            
            warehouse.updated_at = datetime.now(timezone.utc)
            db.commit()
            db.refresh(warehouse)
            
            logger.info(f"Warehouse updated: {warehouse_id}")
            return warehouse
            
        except InventoryException:
            db.rollback()
            raise
        except Exception as e:
            db.rollback()
            logger.error(f"Error updating warehouse {warehouse_id}: {str(e)}")
            raise HTTPException(status.HTTP_510_NOT_EXTENDED, detail=f"Error updating warehouse: {str(e)}")
    
    @staticmethod
    def get_warehouse(db: Session, warehouse_id: int) -> Warehouse:
        """Get warehouse by ID with inventory"""
        warehouse = db.query(Warehouse).options(
            joinedload(Warehouse.inventory_items).joinedload(Inventory.product_variant)
            .joinedload(ProductVariant.product)
        ).filter(
            Warehouse.id == warehouse_id
        ).first()
        
        if not warehouse:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail=f"Warehouse {warehouse_id} not found")
        
        return warehouse
    
    @staticmethod
    def get_warehouse_by_pos(db: Session, pos_id: int) -> Warehouse:
        warehouse = db.query(Warehouse).join(POS).filter(POS.id == pos_id).first()
        if not warehouse:
            raise HTTPException(
                status.HTTP_404_NOT_FOUND,
                detail=f"No warehouse associated with POS {pos_id}"
            )
        return warehouse    
    

    @staticmethod
    def list_warehouses(
        db: Session,
        is_active: Optional[bool] = None,
        search: Optional[str] = None,
        has_pos: Optional[bool] = None,
        skip: int = 0,
        limit: int = 20
    ) -> Tuple[List[Warehouse], int]:
        """List warehouses with filtering and pagination"""
        query = db.query(Warehouse)
        
        # Apply filters
        if is_active is not None:
            query = query.filter(Warehouse.is_active == is_active)
        
        if search:
            search_term = f"%{search}%"
            query = query.filter(
                or_(
                    Warehouse.name.ilike(search_term),
                    Warehouse.location.ilike(search_term)
                )
            )
        
        if has_pos is not None:
            if has_pos:
                query = query.filter(Warehouse.pos.id.isnot(None))
            else:
                query = query.filter(Warehouse.pos.id.is_(None))
        
        # Get total count
        total = query.count()
        
        # Apply pagination
        warehouses = query.order_by(Warehouse.name).offset(skip).limit(limit).all()
        
        return warehouses, total
    
    @staticmethod
    def assign_warehouse_to_pos(db: Session, warehouse_id: int, pos_id: int) -> Warehouse:
        """Assign a warehouse to a POS"""
        warehouse = db.get_warehouse(db, warehouse_id)
        if not warehouse:
            raise NotFoundException(f"Warehouse {warehouse_id} not found")
        
        # Check if POS exists
        pos = db.query(POS).filter(POS.id == pos_id).first()
        if not pos:
            raise NotFoundException(f"POS {pos_id} not found")
        
        # Check if POS already has a warehouse
        existing_pos_warehouse = db.query(Warehouse).filter(Warehouse.pos_id == pos_id).first()
        if existing_pos_warehouse:
            raise BusinessRuleException(f"POS {pos_id} already has warehouse {existing_pos_warehouse.id}")
        
        # Check if warehouse is already assigned
        if warehouse.pos_id and warehouse.pos_id != pos_id:
            raise BusinessRuleException(f"Warehouse {warehouse_id} is already assigned to POS {warehouse.pos_id}")
        
        try:
            warehouse.pos_id = pos_id
            warehouse.updated_at = datetime.now(timezone.utc)
            
            db.commit()
            db.refresh(warehouse)
            
            logger.info(f"Warehouse {warehouse_id} assigned to POS {pos_id}")
            return warehouse
            
        except Exception as e:
            db.rollback()
            logger.error(f"Error assigning warehouse to POS: {str(e)}")
            raise ValidationException(f"Error assigning warehouse to POS: {str(e)}")
    
    @staticmethod
    def unassign_warehouse_from_pos(db: Session, warehouse_id: int) -> Warehouse:
        """Remove warehouse assignment from POS"""
        warehouse = db.get_warehouse(db, warehouse_id)
        if not warehouse:
            raise NotFoundException(f"Warehouse {warehouse_id} not found")
        
        try:
            warehouse.pos_id = None
            warehouse.updated_at = datetime.now(timezone.utc)
            
            db.commit()
            db.refresh(warehouse)
            
            logger.info(f"Warehouse {warehouse_id} unassigned from POS")
            return warehouse
            
        except Exception as e:
            db.rollback()
            logger.error(f"Error unassigning warehouse from POS: {str(e)}")
            raise ValidationException(f"Error unassigning warehouse from POS: {str(e)}")
    
    # ================================
    # INVENTORY ITEM MANAGEMENT
    # ================================
    
    @staticmethod
    def bulk_create_inventory_items(db: Session, data: InventoryBulkCreate) -> List[Inventory]:
        """Add products to warehouse inventory or update existing"""
        try:
            # Validate warehouse
            warehouse = db.query(Warehouse).filter(
                Warehouse.id == data.warehouse_id
            ).first()          
            if not warehouse:
                raise NotFoundException(
                    f"Warehouse with {data.warehouse_id} not found"
                )
            
            variant_ids = [variant.product_variant_id for variant in data.items]
            variants = db.query(ProductVariant).filter(
                ProductVariant.id.in_(variant_ids)
            ).all()
            found_items_id = {item.id for item in variants}

            missing = set(variant_ids) - found_items_id
            if missing:
                raise NotFoundException(
                    f"products variants not found: {missing}"
                )
            
            # Fetch existing items at once
            existing_items = db.query(Inventory).filter(
                Inventory.warehouse_id == data.warehouse_id,
                Inventory.product_variant_id.in_(variant_ids)
            ).all()

            existing_map = {
                item.product_variant_id: item
                for item in existing_items
            }

            result_items = []

            for entry in data.items:
                existing = existing_map.get(entry.product_variant_id)
                if existing:
                    existing.quantity = entry.quantity or Decimal("0")
                    existing.reserved_quantity = entry.reserved_quantity or Decimal("0")
                    existing.updated_at = datetime.now(timezone.utc)
                    result_items.append(existing)
                else:
                    new_item = Inventory(
                        warehouse_id=data.warehouse_id,
                        product_variant_id=entry.product_variant_id,
                        quantity=entry.quantity or Decimal('0'),
                        reserved_quantity=entry.reserved_quantity,
                        created_at=datetime.now(timezone.utc)                      
                    )
                    db.add(new_item)
                    result_items.append(new_item)
            
            db.commit()
            return result_items
        except InventoryException:
            db.rollback()
            raise
        except Exception as e:
            db.rollback()
            logger.error(f"Error creating inventory item: {str(e)}")
            raise ValidationException(f"Error creating inventory item: {str(e)}")
    
    @staticmethod
    def _validate_inventory_update(
            db: Session,
            item: Inventory,
            update_data: dict
    ):
        new_quantity = update_data.get('quantity', item.quantity)
        new_reserved_quantity = update_data.get('reserved_quantity', item.reserved_quantity)
        new_variant = update_data.get('product_variant_id', item.product_variant_id)
        new_warehouse = update_data.get('warehouse_id', item.warehouse_id)

        if new_quantity is None:
            raise ValidationException('Quantity cannot be null')
        
        if new_reserved_quantity is None:
            raise ValidationException('Reserved quantity cannot be null')

        if new_quantity < Decimal('0'):
            raise ValidationException('Quantity cannot be negative')
        
        if new_reserved_quantity < Decimal('0'):
            raise ValidationException('Reserved quantity cannot be negative')
        
        if new_reserved_quantity > new_quantity:
            raise ValidationException('Reserved quantity cannot exceed quantity')
        
        if 'product_variant_id' in update_data:
            exists = db.query(ProductVariant).filter(
                ProductVariant.id == new_variant
            ).first()
            if not exists:
                raise NotFoundException(f"Product variant {new_variant} not found")
            
        if 'warehouse_id' in update_data:
            exists = db.query(Warehouse).filter(
                Warehouse.id == new_warehouse
            ).first()
            if not exists:
                raise NotFoundException(f"Warehouse {new_warehouse} not found")
            
        duplicate = db.query(Inventory).filter(
            Inventory.product_variant_id == new_variant,
            Inventory.warehouse_id == new_warehouse,
            Inventory.id != item.id
        )

    @staticmethod
    def update_inventory_item(
        db: Session,
        inventory_id: int,
        data: InventoryUpdate
    ) -> Inventory:
        """Update inventory item"""
        item = db.query(Inventory).filter(
            Inventory.id == inventory_id
        ).first()

        if not item:
            raise NotFoundException(f"Inventory {inventory_id} not found")
        try:
            update_data = data.model_dump(exclude_unset=True)
            InventoryService._validate_inventory_update(db, item, update_data)
            for field, value in update_data.items():
                setattr(item, field, value)
            
            item.updated_at = datetime.now(timezone.utc)
            db.commit()
            db.refresh(item)
            logger.info(f"Inventory item {inventory_id} updated successfully")
            return item
        except InventoryException:
            db.rollback()
            raise
        except Exception as e:
            db.rollback()
            logger.error(f"Error updating inventory item {inventory_id}: {str(e)}")
            raise ValidationException(
                f"Error updating inventory item {str(e)}"
            )
        pass
    
    @staticmethod
    def get_inventory_item(db: Session, inventory_id: int) -> Inventory:
        """Get inventory item with details"""
        item = db.query(Inventory).options(
            joinedload(Inventory.warehouse),
            joinedload(Inventory.product_variant).joinedload(ProductVariant.product)
        ).filter(
            Inventory.id == inventory_id
        ).first()
        
        if not item:
            raise NotFoundException(f"Inventory item {inventory_id} not found")
    
        return item
    
    @staticmethod
    def get_inventory_item_by_variant_and_warehouse(
        db: Session, 
        product_variant_id: int, 
        warehouse_id: int
    ) -> Optional[Inventory]:
        """Get inventory item by product variant and warehouse"""
        return db.query(Inventory).filter(
            Inventory.product_variant_id == product_variant_id,
            Inventory.warehouse_id == warehouse_id
        ).first()
    
    def has_role(user, role_name: str) -> bool:
        return any(role.name == role_name for role in user.roles)
    
    @staticmethod
    def get_inventory_by_warehouse(
        db: Session,
        warehouse_id: int,
        current_account,
        product_id: Optional[int] = None,
        low_stock_threshold: Optional[Decimal] = None,
        skip: int = 0,
        limit: int = 100
    ) -> Tuple[List[Inventory], int]:
        """Get inventory items for a warehouse"""

        client =  getattr(current_account, "magnetic_card_status", None)
        if not client:
            is_super_admin = any(role.name == "SUPER_ADMIN" for role in current_account.roles)
            if not is_super_admin:
                user_warehouse_id = getattr(getattr(current_account, "pos", None), "warehouse_id", None)
                if user_warehouse_id and warehouse_id != user_warehouse_id:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Not authorized to view these inventories"
                    )            
            
        query = db.query(Inventory).filter(
            Inventory.warehouse_id == warehouse_id
        ).options(
            joinedload(Inventory.product_variant).joinedload(ProductVariant.product)
        )
        
        # Apply filters
        if product_id:
            query = query.join(ProductVariant).filter(
                ProductVariant.product_id == product_id
            )
        
        if low_stock_threshold is not None:
            query = query.filter(
                Inventory.quantity <= low_stock_threshold
            )
        
        # Get total count
        total = query.count()
        
        # Apply pagination
        items = query.order_by(
            desc(Inventory.quantity)
        ).offset(skip).limit(limit).all()
        return items, total
    
    @staticmethod
    def get_inventory_by_product_variant(
        db: Session,
        product_variant_id: int,
        current_account,
        warehouse_id: Optional[int] = None
    ) -> List[Inventory]:
        
        """Get inventory across all warehouses for a product variant"""
        is_super_admin = any(role.name == "SUPER_ADMIN" for role in current_account.roles)
        if not is_super_admin:
            user_warehouse_id = getattr(getattr(current_account, "pos", None), "warehouse_id", None)
            if user_warehouse_id and warehouse_id != user_warehouse_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Not authorized to view these inventories"
                )            
        
        query = db.query(Inventory).filter(
            Inventory.product_variant_id == product_variant_id
        ).options(
            joinedload(Inventory.warehouse)
        )
        
        if warehouse_id:
            query = query.filter(Inventory.warehouse_id == warehouse_id)    

        return query.all()
    
    @staticmethod
    def check_stock_availability(
            db: Session,
            warehouse_id: int,
            product_variant_id: int,
            quantity: Decimal,
            current_user
    ) -> Dict[str, Any]:
        """Check if sufficient stock is available for sale"""
        user_warehouse_id = getattr(
            getattr(current_user, 'pos', None),
            'warehouse_id',
            None
        )
        if user_warehouse_id and user_warehouse_id != warehouse_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Not authorized to access this warehouse inventory"
            )
        
        item = (
            db.query(Inventory)
            .filter(
                Inventory.warehouse_id == warehouse_id,
                Inventory.product_variant_id == product_variant_id
            )
            .first()
        )

        if not item:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Product variant with ID {product_variant_id} not found"
            )
        
        available = item.quantity - item.reserved_quantity
        shortage = max(Decimal('0'), available - quantity)

        return {
            "inventory_item_id": item.id,
            "available": available,
            "required": quantity,
            "shortage": shortage,
            "is_available": available >= quantity,
            "total_quantity": item.quantity,
            "reserved_quantity": item.reserved_quantity,
            "product_variant_id": item.product_variant_id,
            "warehouse_id": item.warehouse_id

        }
    
    # ================================
    # STOCK OPERATIONS
    # ================================
    
    @staticmethod
    def increase_stock(
        db: Session,
        warehouse_id: int,
        product_variant_id: int,
        quantity: Decimal,
        source: str = "manual"
    ) -> Inventory:
        """Increase stock quantity"""
        if quantity <= Decimal('0'):
            raise ValidationException("Quantity must be positive")
        
        item = InventoryService.get_inventory_item_by_variant_and_warehouse(
            db, product_variant_id, warehouse_id
        )
        
        try:
            if item:
                item.quantity += quantity
                item.updated_at = datetime.now(timezone.utc)
            else:
                # Create new inventory item
                item = Inventory(
                    warehouse_id=warehouse_id,
                    product_variant_id=product_variant_id,
                    quantity=quantity,
                    reserved_quantity=Decimal('0'),
                    created_at=datetime.now(timezone.utc),
                    updated_at=datetime.now(timezone.utc)
                )
                db.add(item)
            
            db.commit()
            db.refresh(item)
            
            logger.info(f"Stock increased: {quantity} for product variant {product_variant_id} in warehouse {warehouse_id} ({source})")
            return item
            
        except Exception as e:
            db.rollback()
            logger.error(f"Error increasing stock: {str(e)}")
            raise ValidationException(f"Error increasing stock: {str(e)}")
    
    @staticmethod
    def decrease_stock(
        db: Session,
        warehouse_id: int,
        product_variant_id: int,
        quantity: Decimal,
        reserve_first: bool = False
    ) -> Inventory:
        """Decrease stock quantity, optionally from reserved stock"""
        if quantity <= Decimal('0'):
            raise ValidationException("Quantity must be positive")
        
        item = InventoryService.get_inventory_item_by_variant_and_warehouse(
            db, product_variant_id, warehouse_id
        )
        
        if not item:
            raise NotFoundException(f"Product variant {product_variant_id} not found in warehouse {warehouse_id}")
        
        try:
            if reserve_first:
                # First try to deduct from reserved quantity
                if item.reserved_quantity >= quantity:
                    item.reserved_quantity -= quantity
                    item.quantity -= quantity
                elif item.quantity - item.reserved_quantity >= quantity:
                    # Use remaining quantity after reserved
                    remaining_needed = quantity - item.reserved_quantity
                    item.reserved_quantity = Decimal('0')
                    item.quantity -= remaining_needed
                else:
                    available = item.quantity - item.reserved_quantity
                    raise InsufficientStockException(
                        f"Insufficient available stock. Available: {available}, Required: {quantity}"
                    )
            else:
                # Check total available quantity
                available = item.quantity - item.reserved_quantity
                if available < quantity:
                    raise InsufficientStockException(
                        f"Insufficient available stock. Available: {available}, Required: {quantity}"
                    )
                item.quantity -= quantity
            
            if item.quantity < Decimal('0'):
                item.quantity = Decimal('0')
            
            item.updated_at = datetime.now(timezone.utc)
            db.commit()
            db.refresh(item)
            
            logger.info(f"Stock decreased: {quantity} for product variant {product_variant_id} in warehouse {warehouse_id}")
            return item
            
        except InventoryException:
            db.rollback()
            raise
        except Exception as e:
            db.rollback()
            logger.error(f"Error decreasing stock: {str(e)}")
            raise ValidationException(f"Error decreasing stock: {str(e)}")
    
    @staticmethod
    def reserve_stock(
        db: Session,
        warehouse_id: int,
        product_variant_id: int,
        quantity: Decimal,
        reference_type: str = "sale",
        reference_id: Optional[int] = None
    ) -> Inventory:
        """Reserve stock for future sale/order"""
        if quantity <= Decimal('0'):
            raise ValidationException("Quantity must be positive")
        
        item = InventoryService.get_inventory_item_by_variant_and_warehouse(
            db, product_variant_id, warehouse_id
        )
        
        if not item:
            raise NotFoundException(f"Product variant {product_variant_id} not found in warehouse {warehouse_id}")
        
        # Check available quantity
        available = item.quantity - item.reserved_quantity
        if available < quantity:
            raise InsufficientStockException(
                f"Cannot reserve {quantity} units. Only {available} units available."
            )
        
        try:
            item.reserved_quantity += quantity
            item.updated_at = datetime.now(timezone.utc)
            
            db.commit()
            db.refresh(item)
            
            logger.info(f"Stock reserved: {quantity} for product variant {product_variant_id} in warehouse {warehouse_id} ({reference_type}: {reference_id})")
            return item
            
        except Exception as e:
            db.rollback()
            logger.error(f"Error reserving stock: {str(e)}")
            raise ValidationException(f"Error reserving stock: {str(e)}")
    
    @staticmethod
    def release_reserved_stock(
        db: Session,
        warehouse_id: int,
        product_variant_id: int,
        quantity: Decimal
    ) -> Inventory:
        """Release previously reserved stock"""
        if quantity <= Decimal('0'):
            raise ValidationException("Quantity must be positive")
        
        item = InventoryService.get_inventory_item_by_variant_and_warehouse(
            db, product_variant_id, warehouse_id
        )
        
        if not item:
            raise NotFoundException(f"Product variant {product_variant_id} not found in warehouse {warehouse_id}")
        
        if item.reserved_quantity < quantity:
            raise ValidationException(
                f"Cannot release {quantity} units. Only {item.reserved_quantity} units are reserved."
            )
        
        try:
            item.reserved_quantity -= quantity
            item.updated_at = datetime.now(timezone.utc)
            
            db.commit()
            db.refresh(item)
            
            logger.info(f"Reserved stock released: {quantity} for product variant {product_variant_id} in warehouse {warehouse_id}")
            return item
            
        except Exception as e:
            db.rollback()
            logger.error(f"Error releasing reserved stock: {str(e)}")
            raise ValidationException(f"Error releasing reserved stock: {str(e)}")
    
    @staticmethod
    def transfer_stock(
        db: Session,
        from_warehouse_id: int,
        to_warehouse_id: int,
        product_variant_id: int,
        quantity: Decimal,
        notes: Optional[str] = None
    ) -> Dict[str, Any]:
        """Transfer stock between warehouses"""
        if from_warehouse_id == to_warehouse_id:
            raise ValidationException("Source and destination warehouses cannot be the same")
        
        if quantity <= Decimal('0'):
            raise ValidationException("Transfer quantity must be positive")
        
        # Check source warehouse exists
        from_warehouse = db.query(Warehouse).filter(Warehouse.id == from_warehouse_id).first()
        if not from_warehouse:
            raise NotFoundException(f"Source warehouse {from_warehouse_id} not found")
        
        # Check destination warehouse exists
        to_warehouse = db.query(Warehouse).filter(Warehouse.id == to_warehouse_id).first()
        if not to_warehouse:
            raise NotFoundException(f"Destination warehouse {to_warehouse_id} not found")
        
        # Check stock availability in source
        source_item = InventoryService.get_inventory_item_by_variant_and_warehouse(
            db, product_variant_id, from_warehouse_id
        )
        
        if not source_item:
            raise NotFoundException(f"Product variant {product_variant_id} not found in source warehouse")
        
        available = source_item.quantity - source_item.reserved_quantity
        if available < quantity:
            raise InsufficientStockException(
                f"Insufficient stock for transfer. Available: {available}, Required: {quantity}"
            )
        
        try:
            # Decrease stock in source warehouse
            source_item.quantity -= quantity
            source_item.updated_at = datetime.now(timezone.utc)
            
            # Increase stock in destination warehouse
            dest_item = InventoryService.get_inventory_item_by_variant_and_warehouse(
                db, product_variant_id, to_warehouse_id
            )
            
            if dest_item:
                dest_item.quantity += quantity
                dest_item.updated_at = datetime.now(timezone.utc)
            else:
                # Create new inventory item in destination
                dest_item = Inventory(
                    warehouse_id=to_warehouse_id,
                    product_variant_id=product_variant_id,
                    quantity=quantity,
                    reserved_quantity=Decimal('0'),
                    created_at=datetime.now(timezone.utc),
                    updated_at=datetime.now(timezone.utc)
                )
                db.add(dest_item)
            
            db.commit()
            
            result = {
                "transfer_successful": True,
                "quantity": quantity,
                "product_variant_id": product_variant_id,
                "from_warehouse": {
                    "id": from_warehouse_id,
                    "name": from_warehouse.name,
                    "remaining_stock": source_item.quantity
                },
                "to_warehouse": {
                    "id": to_warehouse_id,
                    "name": to_warehouse.name,
                    "new_stock": dest_item.quantity
                },
                "notes": notes
            }
            
            logger.info(f"Stock transferred: {quantity} units of product variant {product_variant_id} from warehouse {from_warehouse_id} to {to_warehouse_id}")
            return result
            
        except Exception as e:
            db.rollback()
            logger.error(f"Error transferring stock: {str(e)}")
            raise ValidationException(f"Error transferring stock: {str(e)}")
    
    # ================================
    # PROCUREMENT TO INVENTORY
    # ================================
    @staticmethod
    def receive_procurement(
        db: Session,
        procurement_id: int,
        warehouse_id: int,
        received_by_id: int
    ) -> Dict[str, Any]:

        procurement = (
            db.query(Procurement)
            .options(selectinload(Procurement.items))
            .filter(Procurement.id == procurement_id)
            .with_for_update()
            .first()
        )
        if not procurement:
            raise NotFoundException(f"Procurement with {procurement_id} not found.")

        if procurement.status == ProcurementStatus.CANCELLED:
            raise BusinessRuleException("Cannot receive cancelled procurement.")

        if procurement.status != ProcurementStatus.SHIPPED:
            raise BusinessRuleException(
                "Procurement must be SHIPPED before it's received."
            )

        warehouse = db.query(Warehouse).filter(
            Warehouse.id == warehouse_id
        ).first()

        if not warehouse:
            raise NotFoundException(
                f"Warehouse with ID {warehouse_id} not found"
            )

        results = []

        try:
            for proc_item in procurement.items:

                item = InventoryService.increase_stock(
                    db,
                    warehouse_id,
                    proc_item.product_variant_id,
                    proc_item.qty,
                    source=f"procurement_{procurement_id}"
                )

                results.append({
                    "product_variant_id": proc_item.product_variant_id,
                    "quantity": proc_item.qty,
                    "inventory_item_id": item.id
                })

            procurement.status = ProcurementStatus.RECEIVED
            procurement.updated_at = datetime.now(timezone.utc)
            procurement.received_by_id = received_by_id
            db.commit()

            return {
                "procurement_id": procurement_id,
                "warehouse_id": warehouse_id,
                "items_received": len(results),
                "details": results
            }

        except Exception as e:
            db.rollback()
            logger.error(
                f"Error receiving procurement with ID {procurement_id}: {str(e)}"
            )
            raise ValidationException(
                f"Error receiving procurement: {str(e)}"
            )
        
    # ================================
    # SALE STOCK OPERATIONS
    # ================================
    
    @staticmethod
    def process_sale_items(
        db: Session,
        pos_id: int,
        sale_items: List[Dict[str, Any]], 
        current_user: int
    ) -> Dict[str, Any]:
        """Process sale items and update inventory"""
        try:
            # Get POS warehouse
            warehouse = InventoryService.get_warehouse_by_pos(db, pos_id)
            results = []

            for item in sale_items:
                product_variant_id = item["product_variant_id"]
                quantity = item["quantity"]
                
                # Check stock availability
                stock_check = InventoryService.check_stock_availability(
                    db, warehouse.id, product_variant_id, quantity, current_user
                )
                if not stock_check["is_available"]:
                    raise InsufficientStockException(
                        f"Insufficient stock for product variant {product_variant_id}. "
                        f"Available: {stock_check['available']}, Required: {quantity}"
                    )
                
                # Reserve stock for sale
                inventory_item = InventoryService.reserve_stock(
                    db,
                    warehouse.id,
                    product_variant_id,
                    quantity,
                    reference_type="sale",
                    reference_id=None  # Will be updated after sale creation
                )
                
                results.append({
                    "product_variant_id": product_variant_id,
                    "quantity": quantity,
                    "inventory_item_id": inventory_item.id,
                    "available_after_reserve": inventory_item.quantity - inventory_item.reserved_quantity
                })
            
            return {
                "pos_id": pos_id,
                "warehouse_id": warehouse.id,
                "items_processed": len(results),
                "details": results
            }
            
        except InventoryException:
            raise
        except Exception as e:
            logger.error(f"Error processing sale items: {str(e)}")
            raise ValidationException(f"Error processing sale items: {str(e)}")
    
    @staticmethod
    def finalize_sale(
        db: Session,
        sale_id: int,
        pos_id: int,
        sale_items: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Finalize sale and update inventory (deduct reserved stock)"""
        try:
            # Get POS warehouse
            warehouse = InventoryService.get_warehouse_by_pos(db, pos_id)
            
            results = []
            for item in sale_items:
                product_variant_id = item["product_variant_id"]
                quantity = item["quantity"]           

                # Decrease stock (deduct from reserved)
                inventory_item = InventoryService.decrease_stock(
                    db,
                    warehouse.id,
                    product_variant_id,
                    quantity,
                    reserve_first=True
                )
                
                results.append({
                    "product_variant_id": product_variant_id,
                    "quantity": quantity,
                    "inventory_item_id": inventory_item.id,
                    "remaining_stock": inventory_item.quantity,
                    "remaining_reserved": inventory_item.reserved_quantity
                })
            
            logger.info(f"Sale {sale_id} finalized, inventory updated")
            return {
                "sale_id": sale_id,
                "pos_id": pos_id,
                "warehouse_id": warehouse.id,
                "items_updated": len(results),
                "details": results
            }
            
        except Exception as e:
            logger.error(f"Error finalizing sale {sale_id}: {str(e)}")
            raise ValidationException(f"Error finalizing sale: {str(e)}")
    
    @staticmethod
    def cancel_sale_reservations(
        db: Session,
        pos_id: int,
        sale_items: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Cancel sale reservations and release stock"""
        try:
            # Get POS warehouse
            warehouse = InventoryService.get_warehouse_by_pos(db, pos_id)
            
            results = []
            for item in sale_items:
                product_variant_id = item["product_variant_id"]
                quantity = item["quantity"]
                
                # Release reserved stock
                inventory_item = InventoryService.release_reserved_stock(
                    db,
                    warehouse.id,
                    product_variant_id,
                    quantity
                )
                
                results.append({
                    "product_variant_id": product_variant_id,
                    "quantity": quantity,
                    "inventory_item_id": inventory_item.id,
                    "remaining_reserved": inventory_item.reserved_quantity
                })
            
            logger.info(f"Sale reservations cancelled for POS {pos_id}")
            return {
                "pos_id": pos_id,
                "warehouse_id": warehouse.id,
                "items_updated": len(results),
                "details": results
            }
            
        except Exception as e:
            logger.error(f"Error cancelling sale reservations: {str(e)}")
            raise ValidationException(f"Error cancelling sale reservations: {str(e)}")
    
    # ================================
    # INVENTORY REPORTS & ANALYTICS
    # ================================
    
    @staticmethod
    def get_inventory_summary(
        db: Session,
        warehouse_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """Get inventory summary statistics"""
        
        # -------------------------
        # Aggregate totals & counts
        # -------------------------
        query = db.query(
            func.count(Inventory.id).label("total_items"),
            func.coalesce(func.sum(Inventory.quantity), 0).label("total_quantity"),
            func.coalesce(func.sum(Inventory.reserved_quantity), 0).label("total_reserved"),
            func.coalesce(
                func.sum(Inventory.quantity - Inventory.reserved_quantity), 0
            ).label("total_available"),
            func.count().filter(
                Inventory.quantity - Inventory.reserved_quantity < 10
            ).label("low_stock_items"),
            func.count().filter(
                Inventory.quantity == 0
            ).label("out_of_stock_items")
        )

        if warehouse_id:
            query = query.filter(Inventory.warehouse_id == warehouse_id)

        result = query.first()

        # -------------------------
        # Recent updates (last 5 items)
        # -------------------------
        recent_query = db.query(Inventory)
        if warehouse_id:
            recent_query = recent_query.filter(Inventory.warehouse_id == warehouse_id)

        recent_updates = recent_query.order_by(desc(Inventory.updated_at)).limit(5).all()

        # -------------------------
        # Build response
        # -------------------------
        return {
            "total_items": result.total_items,
            "total_quantity": float(result.total_quantity),
            "total_reserved": float(result.total_reserved),
            "total_available": float(result.total_available),
            "low_stock_items": result.low_stock_items,
            "out_of_stock_items": result.out_of_stock_items,
            "recent_updates": [
                {
                    "id": item.id,
                    "product_variant_id": item.product_variant_id,
                    "quantity": float(item.quantity),
                    "reserved_quantity": float(item.reserved_quantity),
                    "updated_at": item.updated_at
                }
                for item in recent_updates
            ]
        }
    
    @staticmethod
    def get_low_stock_items(
        db: Session,
        warehouse_id: Optional[int] = None,
        threshold: Decimal = Decimal('10')
    ) -> List[Dict[str, Any]]:
        """Get items with low stock (below threshold)"""
        query = db.query(Inventory).options(
            joinedload(Inventory.product_variant).joinedload(ProductVariant.product),
            joinedload(Inventory.warehouse)
        ).filter(
            Inventory.quantity - Inventory.reserved_quantity < threshold
        )
        
        if warehouse_id:
            query = query.filter(Inventory.warehouse_id == warehouse_id)
        
        items = query.all()
        
        result = []
        for item in items:
            available = item.quantity - item.reserved_quantity
            result.append({
                "inventory_item_id": item.id,
                "warehouse_id": item.warehouse_id,
                "warehouse_name": item.warehouse.name,
                "product_variant_id": item.product_variant_id,
                "product_name": item.product_variant.product.name,
                "variant_name": item.product_variant.name,
                "current_stock": item.quantity,
                "reserved_stock": item.reserved_quantity,
                "available_stock": available,
                "threshold": threshold,
                "shortage": max(Decimal('0'), threshold - available)
            })
        
        return result
    
    @staticmethod
    def get_stock_level_report(
        db: Session,
        warehouse_id: Optional[int] = None,
        product_id: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Generate comprehensive stock level report"""
        query = db.query(
            Inventory,
            ProductVariant,
            Product,
            Warehouse
        ).join(
            ProductVariant, Inventory.product_variant_id == ProductVariant.id
        ).join(
            Product, ProductVariant.product_id == Product.id
        ).join(
            Warehouse, Inventory.warehouse_id == Warehouse.id
        )
        
        if warehouse_id:
            query = query.filter(Inventory.warehouse_id == warehouse_id)
        
        if product_id:
            query = query.filter(Product.id == product_id)
        
        results = query.all()
        
        report = []
        for inventory, variant, product, warehouse in results:
            available = inventory.quantity - inventory.reserved_quantity
            status = "out_of_stock" if inventory.quantity == 0 else "low_stock" if available < 10 else "in_stock"
            
            report.append({
                "inventory_id": inventory.id,
                "product_id": product.id,
                "product_name": product.name,
                "variant_id": variant.id,
                "variant_name": variant.name,
                "warehouse_id": warehouse.id,
                "warehouse_name": warehouse.name,
                "total_quantity": inventory.quantity,
                "reserved_quantity": inventory.reserved_quantity,
                "available_quantity": available,
                "status": status,
                "last_updated": inventory.updated_at
            })
        
        return report
    
    @staticmethod
    def get_inventory_value_report(
        db: Session,
        warehouse_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """Calculate total inventory value"""
        # This would require product cost information
        # For now, return basic counts
        query = db.query(Inventory)
        
        if warehouse_id:
            query = query.filter(Inventory.warehouse_id == warehouse_id)
        
        total_items = query.count()
        total_quantity = db.execute(
            select(func.coalesce(func.sum(Inventory.quantity), Decimal('0')))
            .where(Inventory.warehouse_id == warehouse_id if warehouse_id else True)
        ).scalar() or Decimal('0')

        return {
            "total_items": total_items,
            "total_quantity": float(total_quantity),
            "estimated_value": 0.0,  # Would need product cost data
            "warehouse_id": warehouse_id
        }