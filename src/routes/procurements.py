# src/routes/procurements.py
from fastapi import APIRouter, Depends, Query, status, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional

from src.core.database import get_db
from src.core.auth_dependencies import get_current_account
from src.models.pos import POSUser
from src.schemas.procurement import (
    ProcurementCreate,
    ProcurementUpdate,
    ProcurementResponse,
    ProcurementStatus
)
from src.services.procurement_service import (
    ProcurementService,
    NotFoundException, 
    ValidationException, 
    BusinessRuleException
)


procurement_router = APIRouter(prefix="/procurements", tags=["POS Procurements"])


@procurement_router.post("/", response_model=ProcurementResponse, status_code=status.HTTP_201_CREATED)
def create_procurement(
    data: ProcurementCreate,
    current_user: POSUser = Depends(get_current_account),
    db: Session = Depends(get_db)
):
    """
    Create a new procurement (purchase order)
    
    - Requires: POS user authentication
    - Automatically generates PO number
    - Sets procurement status to PENDING
    """
    return ProcurementService.create_procurement(
        db=db,
        data=data,
        pos_id=current_user.pos_id,
        user_id=current_user.id
    )


@procurement_router.get("/", response_model=List[ProcurementResponse])
def list_procurements(
    pos_id: Optional[int] = Query(None, description="Filter by POS"),
    provider_id: Optional[int] = Query(None, description="Filter by provider"),
    status: Optional[str] = Query(None, description="Filter by status"),
    limit: int = Query(100, ge=1, le=200),
    offset: int = Query(0, ge=0),
    current_user: POSUser = Depends(get_current_account),
    db: Session = Depends(get_db)
):
    """
    List procurements with filtering
    
    - POS users can only see their POS's procurements unless admin
    - Supports pagination
    """
    # For regular POS users, restrict to their POS
    if current_user.role != "manager":  # Add proper role check
        pos_id = current_user.pos_id
    
    # Convert status string to enum
    status_enum = None
    if status:
        try:
            status_enum = ProcurementStatus(status.lower())
        except ValueError:
            pass
    
    return ProcurementService.list_procurements(
        db=db,
        pos_id=pos_id,
        provider_id=provider_id,
        status=status_enum,
        limit=limit,
        offset=offset
    )


@procurement_router.get("/{procurement_id}", response_model=ProcurementResponse)
def get_procurement(
    procurement_id: int,
    current_user: POSUser = Depends(get_current_account),
    db: Session = Depends(get_db)
):
    """
    Get procurement details by ID
    """
    procurement = ProcurementService.get_procurement(db, procurement_id)
    
    if not procurement:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Procurement not found"
        )
    
    # Authorization: Check if user can access this procurement
    if current_user.role != "manager" and procurement.pos_id != current_user.pos_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to view this procurement"
        )
    
    return procurement


@procurement_router.put("/{procurement_id}", response_model=ProcurementResponse)
def update_procurement(
    procurement_id: int,
    data: ProcurementUpdate,
    current_user: POSUser = Depends(get_current_account),
    db: Session = Depends(get_db)
):
    """
    Update procurement (mainly delivery information)
    
    - Only certain fields can be updated
    - Mostly used for delivery information
    """
    procurement = ProcurementService.get_procurement(db, procurement_id, include_details=False)
    
    if not procurement:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Procurement not found"
        )
    
    # Authorization
    if current_user.role != "manager" and procurement.pos_id != current_user.pos_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to update this procurement"
        )
    
    return ProcurementService.update_procurement(db, procurement_id, data)


@procurement_router.post("/{procurement_id}/deliver", response_model=ProcurementResponse)
def mark_as_delivered(
    procurement_id: int,
    delivery_notes: Optional[str] = None,
    driver_name: Optional[str] = None,
    driver_phone: Optional[str] = None,
    current_user: POSUser = Depends(get_current_account),
    db: Session = Depends(get_db)
):
    """
    Mark procurement as delivered
    
    - Updates inventory automatically
    - Creates purchase invoice if not exists
    - Requires appropriate permissions
    """
    procurement = ProcurementService.get_procurement(db, procurement_id, include_details=False)
    
    if not procurement:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Procurement not found"
        )
    
    # Authorization: Only manager or storekeeper can mark as delivered
    if current_user.role not in ["manager", "storekeeper"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only managers or storekeepers can mark procurements as delivered"
        )
    
    return ProcurementService.mark_as_delivered(
        db=db,
        procurement_id=procurement_id,
        user_id=current_user.id,
        delivery_notes=delivery_notes,
        driver_name=driver_name,
        driver_phone=driver_phone
    )

@procurement_router.post("/{procurement_id}/cancel", response_model=ProcurementResponse)
def cancel_procurement(
    procurement_id: int,
    reason: Optional[str] = None,
    current_user: POSUser = Depends(get_current_account),
    db: Session = Depends(get_db)
):
    """
    Cancel a procurement
    
    - Cannot cancel delivered procurements
    - Requires manager role
    """
    procurement = ProcurementService.get_procurement(db, procurement_id, include_details=False)
    
    if not procurement:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Procurement not found"
        )
    
    # Authorization: Only manager can cancel
    if current_user.role != "manager":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only managers can cancel procurements"
        )
    
    return ProcurementService.cancel_procurement(
        db=db,
        procurement_id=procurement_id,
        reason=reason
    )


@procurement_router.get("/pos/{pos_id}/summary")
def get_pos_procurement_summary(
    pos_id: int,
    current_user: POSUser = Depends(get_current_account),
    db: Session = Depends(get_db)
):
    """
    Get procurement summary for a POS
    
    - Shows counts by status
    - Shows total amount
    """
    # Authorization
    if current_user.role != "manager" and current_user.pos_id != pos_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to view this POS summary"
        )
    
    return ProcurementService.get_procurement_summary(db, pos_id)
