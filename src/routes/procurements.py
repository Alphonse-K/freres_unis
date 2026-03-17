# src/routes/procurements.py
from fastapi import APIRouter, Depends, Query, status, HTTPException, UploadFile
from sqlalchemy.orm import Session
from typing import List, Optional

from src.core.database import get_db
from src.core.auth_dependencies import get_current_account, require_permission
from src.core.permissions import Permissions
from src.models.pos import POSUser
from src.schemas.procurement import (
    ProcurementCreate,
    ProcurementUpdate,
    ProcurementResponse,
    ProcurementStatus,
    ProcurementUpdateStatus,
    ReturnItem,
    CreateReturnRequest,
    UpdateReturn
)
from src.services.procurement_service import (
    ProcurementService,
)


procurement_router = APIRouter(prefix="/procurements", tags=["POS Procurements"])


@procurement_router.post("/", response_model=ProcurementResponse, status_code=status.HTTP_201_CREATED)
def create_procurement(
    data: ProcurementCreate,
    current_user: POSUser = Depends(require_permission(Permissions.CREATE_PROCUREMENT)),
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
    procurement_status: Optional[str] = Query(None, description="Filter by status"),
    limit: int = Query(100, ge=1, le=200),
    offset: int = Query(0, ge=0),
    current_user: POSUser = Depends(require_permission(Permissions.READ_PROCUREMENT)),
    db: Session = Depends(get_db)
):
    """
    List procurements with filtering   
    - POS users can only see their POS's procurements unless admin
    - Supports pagination
    """
    # Convert status string to enum
    status_enum = None
    if procurement_status:
        try:
            status_enum = ProcurementStatus(status.lower())
        except ValueError:
            pass
    
    return ProcurementService.list_procurements(
        db=db,
        current_user=current_user,
        pos_id=pos_id,
        provider_id=provider_id,
        procurement_status=status_enum,
        limit=limit,
        offset=offset
    )

@procurement_router.get("/{procurement_id}", response_model=ProcurementResponse)
def get_procurement(
    procurement_id: int,
    current_user: POSUser = Depends(require_permission(Permissions.READ_PROCUREMENT)),
    db: Session = Depends(get_db)
):
    """
    Get procurement details by ID
    """
    procurement = ProcurementService.get_procurement(db, procurement_id, current_user)
    
    if not procurement:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Procurement not found"
        )
        
    return procurement


@procurement_router.put("/{procurement_id}", response_model=ProcurementResponse)
def update_procurement(
    procurement_id: int,
    data: ProcurementUpdate,
    current_user: POSUser = Depends(require_permission(Permissions.UPDATE_PROCUREMENT)),
    db: Session = Depends(get_db)
):
    """
    Update procurement (mainly delivery information)
    
    - Only certain fields can be updated
    - Mostly used for delivery information
    """
    procurement = ProcurementService.get_procurement(db, procurement_id, current_user, include_details=False)
    
    if not procurement:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Procurement not found"
        )
    
    return ProcurementService.update_procurement(db, procurement_id, current_user, data)


@procurement_router.put(
    "/{procurement_id}/add/receipt",
    response_model=ProcurementResponse
)
def attach_procurement_receipt(
    procurement_id: int,
    file: UploadFile,
    current_user: POSUser = Depends(
        require_permission(Permissions.ADD_PROCUREMENT_RECEIPT)
    ),
    db: Session = Depends(get_db)
):
    """
    Change procurement status
    """
    return ProcurementService.attach_procurement_receipt(
        db, procurement_id, file, current_user
    )


@procurement_router.post("/{procurement_id}/cancel", response_model=ProcurementResponse)
def cancel_procurement(
    procurement_id: int,
    reason: Optional[str] = None,
    current_user: POSUser = Depends(require_permission(Permissions.CANCEL_PROCUREMENT)),
    db: Session = Depends(get_db)
):
    """
    Cancel a procurement
    
    - Cannot cancel delivered procurements
    - Requires manager role
    """
    procurement = ProcurementService.get_procurement(db, procurement_id, current_user, include_details=False)
    
    if not procurement:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Procurement not found"
        )
        
    return ProcurementService.cancel_procurement(
        db=db,
        procurement_id=procurement_id,
        reason=reason
    )
@procurement_router.post(
    "/return/{procurement_id}/create",
    status_code=status.HTTP_201_CREATED
)
def create_return(
    procurement_id: int,
    data: CreateReturnRequest,
    current_user = Depends(require_permission(Permissions.RETURN_PROCUREMENT)),
    db: Session = Depends(get_db)
):
    return ProcurementService.create_return(
        db, 
        procurement_id, 
        current_user, 
        data.items, 
        data.reason
    )


@procurement_router.get(
    "/{procurement_id}/returns",
)
def list_returns(
    procurement_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(require_permission(Permissions.READ_PROCUREMENT_RETURN))
):
    return ProcurementService.list_returns(
        db,
        procurement_id,
        current_user
    )

@procurement_router.patch(
    "/{return_id}/review",
)
def review_return(
    return_id: int,
    approve: bool,
    note: str,
    db: Session = Depends(get_db),
    current_user = Depends(require_permission(Permissions.APPROVE_PROCUREMEMNT_RETURN))
):
    return ProcurementService.review_return(
        db,
        return_id,
        current_user,
        approve,
        note
    )

@procurement_router.put(
    "/{return_id}/return",
)
def update_return(
    return_id: int,
    data: UpdateReturn,
    db: Session = Depends(get_db),
    current_user = Depends(require_permission(Permissions.UPDATE_PROCUREMENT_RETURN))
):
    return ProcurementService.update_return(
        db=db,
        return_id=return_id,
        initiator_pos=current_user,
        items=data.items,
        reason=data.reason
    )

@procurement_router.patch(
    "/{return_id}/cancel",
)
def cancel_return(
    return_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(require_permission(Permissions.CANCEL_PROCUREMENT_RETURN))
):
    return ProcurementService.cancel_return(
        db=db,
        return_id=return_id,
        initiator_pos=current_user
    )


@procurement_router.get("/pos/{pos_id}/summary")
def get_pos_procurement_summary(
    pos_id: int,
    current_user: POSUser = Depends(require_permission(Permissions.READ_PROCUREMENT)),
    db: Session = Depends(get_db)
):
    """
    Get procurement summary for a POS
    
    - Shows counts by status
    - Shows total amount
    """
    # Authorization
    is_super_admin = any(
        role.name == "SUPER_ADMIN"
        for role in current_user.roles
    )
    if not is_super_admin and current_user.pos.id != pos_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to view this POS summary"
        )
    
    return ProcurementService.get_procurement_summary(db, pos_id)
