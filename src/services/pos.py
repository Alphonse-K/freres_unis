from fastapi import HTTPException, status
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import or_
from typing import List, Tuple, Dict, Optional, Any
from decimal import Decimal
from datetime import datetime, timezone
from src.models.pos import POS, POSUser
from src.services.inventory import NotFoundException, ValidationException, BusinessRuleException, InventoryService
from src.schemas.pos import POSCreate, POSUpdate, POSUserCreate, POSUserUpdate, POSUserRole
from src.models.inventory import Warehouse
from src.core.security import SecurityUtils
from src.models.procurement import Procurement
import logging

logger = logging.getLogger(__name__)

# class POSService:

#     # ------------------------
#     # POS
#     # ------------------------
#     @staticmethod
#     def create_pos(db: Session, data: POSCreate) -> POS:
#         pos_business_name = db.query(POS).filter(POS.pos_business_name == data.pos_business_name).first()
#         if pos_business_name:
#             raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="POS names must be unique !")
#         pos = POS(**data.model_dump())
#         db.add(pos)
#         db.commit()
#         db.refresh(pos)

#         logger.info("POS created", extra={"pos_id": pos.id})
#         return pos

#     @staticmethod
#     def update_pos(db: Session, pos_id: int, data: POSUpdate) -> POS:
#         pos = db.query(POS).filter(POS.id == pos_id).first()
#         if not pos:
#             raise HTTPException(status.HTTP_404_NOT_FOUND, "POS not found")

#         for field, value in data.model_dump(exclude_unset=True).items():
#             setattr(pos, field, value)

#         db.commit()
#         db.refresh(pos)

#         logger.info("POS updated", extra={"pos_id": pos.id})
#         return pos

#     @staticmethod
#     def get_pos(db: Session, pos_id: int) -> POS:
#         pos = db.query(POS).filter(POS.id == pos_id).first()
#         if not pos:
#             raise HTTPException(status.HTTP_404_NOT_FOUND, "POS not found")
#         return pos

#     @staticmethod
#     def list_pos(
#         db: Session,
#         skip: int = 0,
#         limit: int = 20
#     ) -> Tuple[List[POS], int]:
#         """
#         List POS with pagination.
#         """
#         query = db.query(POS)

#         total = query.count()

#         items = (
#             query
#             .order_by(POS.id.desc())
#             .offset(skip)
#             .limit(limit)
#             .all()
#         )

#         return items, total    
class POSService:
    
    # ================================
    # POS CRUD OPERATIONS
    # ================================
    
    @staticmethod
    def create_pos(db: Session, data: POSCreate) -> POS:
        """Create a new POS with optional warehouse assignment"""
        try:
            # Check if POS name already exists
            existing = db.query(POS).filter(
                POS.pos_business_name == data.pos_business_name
            ).first()
            
            if existing:
                raise ValidationException("POS business name must be unique")
            
            # Check if phone already exists
            existing_phone = db.query(POS).filter(POS.phone == data.phone).first()
            if existing_phone:
                raise ValidationException("Phone number already registered")
            
            # Validate warehouse if provided
            warehouse = None
            if data.warehouse_id:
                warehouse = db.query(Warehouse).filter(Warehouse.id == data.warehouse_id).first()
                if not warehouse:
                    raise NotFoundException(f"Warehouse {data.warehouse_id} not found")
                
                # Check if warehouse is already assigned to another POS
                if warehouse.pos_id:
                    raise BusinessRuleException(f"Warehouse {data.warehouse_id} is already assigned to POS {warehouse.pos_id}")
            
            # Create POS
            pos = POS(
                type=data.type,
                pos_business_name=data.pos_business_name,
                phone=data.phone,
                balance=data.balance or Decimal('0'),
                status=data.status,
                warehouse_id=data.warehouse_id,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc)
            )
            
            db.add(pos)
            db.flush()  # Get POS ID
            
            # If warehouse was provided, update its pos_id
            if warehouse:
                warehouse.pos_id = pos.id
                warehouse.updated_at = datetime.now(timezone.utc)
            
            db.commit()
            db.refresh(pos)
            
            logger.info(f"POS created: {pos.id} - {pos.pos_business_name}")
            return pos
            
        except Exception as e:
            db.rollback()
            logger.error(f"Error creating POS: {str(e)}")
            raise
    
    @staticmethod
    def update_pos(db: Session, pos_id: int, data: POSUpdate) -> POS:
        """Update POS information"""
        pos = db.query(POS).filter(POS.id == pos_id).first()
        if not pos:
            raise NotFoundException(f"POS {pos_id} not found")
        
        try:
            # Check business name uniqueness if changing
            if data.pos_business_name and data.pos_business_name != pos.pos_business_name:
                existing = db.query(POS).filter(
                    POS.pos_business_name == data.pos_business_name,
                    POS.id != pos_id
                ).first()
                if existing:
                    raise ValidationException("POS business name must be unique")
            
            # Check phone uniqueness if changing
            if data.phone and data.phone != pos.phone:
                existing_phone = db.query(POS).filter(
                    POS.phone == data.phone,
                    POS.id != pos_id
                ).first()
                if existing_phone:
                    raise ValidationException("Phone number already registered")
            
            # Handle warehouse assignment
            if data.warehouse_id is not None:
                if data.warehouse_id != pos.warehouse_id:
                    # Remove from current warehouse
                    if pos.warehouse:
                        pos.warehouse.pos_id = None
                        pos.warehouse.updated_at = datetime.now(timezone.utc)
                    
                    # Assign to new warehouse
                    if data.warehouse_id:
                        new_warehouse = db.query(Warehouse).filter(
                            Warehouse.id == data.warehouse_id
                        ).first()
                        if not new_warehouse:
                            raise NotFoundException(f"Warehouse {data.warehouse_id} not found")
                        
                        if new_warehouse.pos_id and new_warehouse.pos_id != pos_id:
                            raise BusinessRuleException(
                                f"Warehouse {data.warehouse_id} is already assigned to POS {new_warehouse.pos_id}"
                            )
                        
                        new_warehouse.pos_id = pos_id
                        new_warehouse.updated_at = datetime.now(timezone.utc)
                        pos.warehouse_id = data.warehouse_id
                    else:
                        pos.warehouse_id = None
            
            # Update other fields
            if data.type is not None:
                pos.type = data.type
            if data.pos_business_name is not None:
                pos.pos_business_name = data.pos_business_name
            if data.phone is not None:
                pos.phone = data.phone
            if data.balance is not None:
                pos.balance = data.balance
            if data.status is not None:
                pos.status = data.status
            
            pos.updated_at = datetime.now(timezone.utc)
            db.commit()
            db.refresh(pos)
            
            logger.info(f"POS updated: {pos_id}")
            return pos
            
        except Exception as e:
            db.rollback()
            logger.error(f"Error updating POS {pos_id}: {str(e)}")
            raise
    
    @staticmethod
    def get_pos(db: Session, pos_id: int, include_warehouse: bool = True) -> POS:
        """Get POS by ID with relationships"""
        query = db.query(POS)
        
        if include_warehouse:
            query = query.options(
                joinedload(POS.warehouse),
                joinedload(POS.users),
                joinedload(POS.addresses)
            )
        
        pos = query.filter(POS.id == pos_id).first()
        
        if not pos:
            raise NotFoundException(f"POS {pos_id} not found")
        
        return pos
    
    @staticmethod
    def list_pos(
        db: Session,
        type: Optional[str] = None,
        status: Optional[str] = None,
        search: Optional[str] = None,
        with_warehouse: bool = False,
        skip: int = 0,
        limit: int = 20
    ) -> Tuple[List[POS], int]:
        """List POS with filtering and pagination"""
        query = db.query(POS)
        
        # Apply filters
        if type:
            query = query.filter(POS.type == type)
        
        if status:
            query = query.filter(POS.status == status)
        
        if search:
            search_term = f"%{search}%"
            query = query.filter(
                or_(
                    POS.pos_business_name.ilike(search_term),
                    POS.phone.ilike(search_term)
                )
            )
        
        if with_warehouse:
            query = query.options(joinedload(POS.warehouse))
        
        # Get total count
        total = query.count()
        
        # Apply pagination
        pos_list = query.order_by(POS.id.desc()).offset(skip).limit(limit).all()
        
        return pos_list, total
    
    @staticmethod
    def assign_warehouse(db: Session, pos_id: int, warehouse_id: int) -> POS:
        """Assign a warehouse to a POS"""
        pos = POSService.get_pos(db, pos_id, include_warehouse=False)
        
        # Check if warehouse exists
        warehouse = db.query(Warehouse).filter(Warehouse.id == warehouse_id).first()
        if not warehouse:
            raise NotFoundException(f"Warehouse {warehouse_id} not found")
        
        # Check if warehouse is already assigned
        if warehouse.pos_id and warehouse.pos_id != pos_id:
            raise BusinessRuleException(
                f"Warehouse {warehouse_id} is already assigned to POS {warehouse.pos_id}"
            )
        
        # Remove from current warehouse if any
        if pos.warehouse:
            old_warehouse = db.query(Warehouse).filter(Warehouse.id == pos.warehouse_id).first()
            if old_warehouse:
                old_warehouse.pos_id = None
                old_warehouse.updated_at = datetime.now(timezone.utc)
        
        # Assign to new warehouse
        warehouse.pos_id = pos_id
        warehouse.updated_at = datetime.now(timezone.utc)
        pos.warehouse_id = warehouse_id
        pos.updated_at = datetime.now(timezone.utc)
        
        db.commit()
        db.refresh(pos)
        
        logger.info(f"Warehouse {warehouse_id} assigned to POS {pos_id}")
        return pos
    
    @staticmethod
    def unassign_warehouse(db: Session, pos_id: int) -> POS:
        """Remove warehouse assignment from POS"""
        pos = POSService.get_pos(db, pos_id, include_warehouse=False)
        
        if not pos.warehouse_id:
            raise BusinessRuleException(f"POS {pos_id} has no warehouse assigned")
        
        # Get warehouse
        warehouse = db.query(Warehouse).filter(Warehouse.id == pos.warehouse_id).first()
        if warehouse:
            warehouse.pos_id = None
            warehouse.updated_at = datetime.now(timezone.utc)
        
        pos.warehouse_id = None
        pos.updated_at = datetime.now(timezone.utc)
        
        db.commit()
        db.refresh(pos)
        
        logger.info(f"Warehouse unassigned from POS {pos_id}")
        return pos
    
    @staticmethod
    def get_pos_stats(db: Session, pos_id: int) -> Dict[str, Any]:
        """Get comprehensive statistics for a POS"""
        pos = POSService.get_pos(db, pos_id, include_warehouse=False)
        
        # Import here to avoid circular imports
        from src.services.pos_sales import SaleService
        from src.services.pos_expenses import ExpenseService
        # from src.services.inventory import InventoryService
        from src.services.procurement_service import ProcurementService
        
        try:
            # Get sales summary
            sales_summary = SaleService.get_sales_summary(db, pos_id=pos_id)
            
            # Get expenses summary
            expenses_summary = ExpenseService.get_expenses_summary(db, pos_id=pos_id)
            
            # Get low stock items if warehouse exists
            low_stock_count = 0
            if pos.warehouse_id:
                low_stock_items = InventoryService.get_low_stock_items(db, pos.warehouse_id)
                low_stock_count = len(low_stock_items)
            
            # Get pending procurements
            from src.models.procurement import ProcurementStatus
            pending_procurements = db.query(POS).filter(
                POS.id == pos_id
            ).join(POS.procurements).filter(
                Procurement.status == ProcurementStatus.PENDING
            ).count()
            
            # Get active users count
            active_users = db.query(POSUser).filter(
                POSUser.pos_id == pos_id,
                POSUser.is_active == True
            ).count()
            
            return {
                "pos_id": pos_id,
                "pos_name": pos.pos_business_name,
                "total_sales": sales_summary.get("total_sales", 0),
                "total_revenue": sales_summary.get("total_revenue", 0),
                "total_expenses": expenses_summary.get("total_amount", 0),
                "net_balance": float(pos.balance or Decimal('0')),
                "active_users": active_users,
                "low_stock_items": low_stock_count,
                "pending_procurements": pending_procurements,
                "warehouse_id": pos.warehouse_id,
                "status": pos.status.value,
                "last_updated": pos.updated_at
            }
            
        except Exception as e:
            logger.error(f"Error getting POS stats for {pos_id}: {str(e)}")
            # Return basic stats even if some services fail
            return {
                "pos_id": pos_id,
                "pos_name": pos.pos_business_name,
                "net_balance": float(pos.balance or Decimal('0')),
                "warehouse_id": pos.warehouse_id,
                "status": pos.status.value
            }

class POSUserService:

    @staticmethod
    def create_pos_user(
        db: Session,
        pos_id: int,
        data: POSUserCreate
    ) -> POSUser:

        if db.query(POSUser).filter(POSUser.username == data.username).first():
            raise HTTPException(status.HTTP_406_NOT_ACCEPTABLE, "POS user username already exists")
        
        if db.query(POSUser).filter(POSUser.phone == data.phone).first():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="POS user phone already exists"
            )

        payload = data.model_dump(exclude={"password_hash", "pin_hash", "role"})

        user = POSUser(
            pos_id=pos_id,
            **payload,
            role=data.role or POSUserRole.CASHIER,
            password_hash=SecurityUtils.hash_password(data.password_hash),
            pin_hash=SecurityUtils.hash_password(data.pin_hash),
        )

        db.add(user)
        db.commit()
        db.refresh(user)

        logger.info(
            "POS user created",
            extra={"pos_id": pos_id, "pos_user_id": user.id}
        )

        return user

    @staticmethod
    def update_pos_user(
        db: Session,
        user_id: int,
        data: POSUserUpdate
    ) -> POSUser:

        user = db.query(POSUser).filter(POSUser.id == user_id).first()
        if not user:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "POS user not found")

        payload = data.model_dump(exclude_unset=True)

        if "password_hash" in payload:
            payload["password_hash"] = SecurityUtils.hash_password(payload["password_hash"])

        if "pin_hash" in payload:
            payload["pin_hash"] = SecurityUtils.hash_password(payload["pin_hash"])

        for field, value in payload.items():
            setattr(user, field, value)

        db.commit()
        db.refresh(user)

        logger.info(f"POS user updated", extra={"pos_user_id": str(user.id)})
        return user
