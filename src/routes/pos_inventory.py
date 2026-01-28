# src/routes/inventory.py
from fastapi import APIRouter, Depends, Query, HTTPException, status, Path
from sqlalchemy.orm import Session
from datetime import date, datetime
from decimal import Decimal
from typing import List, Optional

from src.core.database import get_db
from src.core.auth_dependencies import get_current_account
# from src.models.dicts import dict
from src.schemas.inventory import (
    WarehouseCreate, WarehouseUpdate, WarehouseOut,
    InventoryCreate, InventoryUpdate, InventoryOut,
    StockIncreaseRequest, StockDecreaseRequest, StockReserveRequest,
    StockReleaseRequest, StockTransferRequest, StockCheckRequest, StockCheckResponse,
    ProcurementReceiveRequest, SaleProcessRequest, SaleProcessResponse,
    InventorySummary, LowStockItem, StockLevelReportItem
)
from src.services.inventory import InventoryService, NotFoundException, ValidationException, BusinessRuleException, InsufficientStockException


inventory_router = APIRouter(prefix="/inventory", tags=["POS Inventory"])


# ================================
# WAREHOUSE ROUTES
# ================================

@inventory_router.post("/warehouses/",
    response_model=WarehouseOut,
    status_code=status.HTTP_201_CREATED,
    summary="Create warehouse",
    description="Create a new warehouse"
)
def create_warehouse(
    data: WarehouseCreate,
    current_account: dict = Depends(get_current_account),
    db: Session = Depends(get_db)
):
    """
    Create a new warehouse.
    
    - **name**: Warehouse name (required, unique)
    - **location**: Optional location description
    - **is_active**: Active status (default: true)
    """
    try:
        return InventoryService.create_warehouse(db, data)
    except ValidationException as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@inventory_router.get("/warehouses/",
    response_model=List[WarehouseOut],
    summary="List warehouses",
    description="Get list of warehouses with optional filtering"
)
def list_warehouses(
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    search: Optional[str] = Query(None, description="Search by name or location"),
    has_pos: Optional[bool] = Query(None, description="Filter warehouses with/without POS"),
    skip: int = Query(0, ge=0, description="Pagination offset"),
    limit: int = Query(20, ge=1, le=100, description="Items per page"),
    current_account: dict = Depends(get_current_account),
    db: Session = Depends(get_db)
):
    """
    List warehouses with search and filtering.
    
    - **is_active**: Filter by active/inactive
    - **search**: Search in name and location
    - **has_pos**: Filter warehouses with POS assignment
    - **skip**: Pagination offset
    - **limit**: Items per page (1-100)
    """
    try:
        warehouses, total = InventoryService.list_warehouses(
            db, is_active=is_active, search=search, has_pos=has_pos, skip=skip, limit=limit
        )
        return warehouses
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@inventory_router.get("/warehouses/{warehouse_id}",
    response_model=WarehouseOut,
    summary="Get warehouse details",
    description="Get detailed information about a warehouse including inventory"
)
def get_warehouse(
    warehouse_id: int = Path(..., description="Warehouse ID", gt=0),
    current_account: dict = Depends(get_current_account),
    db: Session = Depends(get_db)
):
    """
    Get warehouse by ID.
    
    - **warehouse_id**: ID of the warehouse to retrieve
    """
    try:
        return InventoryService.get_warehouse(db, warehouse_id)
    except NotFoundException as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@inventory_router.put("/warehouses/{warehouse_id}",
    response_model=WarehouseOut,
    summary="Update warehouse",
    description="Update warehouse information"
)
def update_warehouse(
    warehouse_id: int = Path(..., description="Warehouse ID", gt=0),
    data: WarehouseUpdate = Depends(),
    current_account: dict = Depends(get_current_account),
    db: Session = Depends(get_db)
):
    """
    Update warehouse details.
    
    - **warehouse_id**: ID of warehouse to update
    - **data**: Updated warehouse fields
    """
    try:
        return InventoryService.update_warehouse(db, warehouse_id, data)
    except NotFoundException as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)
    except ValidationException as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@inventory_router.post("/warehouses/{warehouse_id}/assign-to-pos/{pos_id}",
    response_model=WarehouseOut,
    summary="Assign warehouse to POS",
    description="Assign a warehouse to a POS location"
)
def assign_warehouse_to_pos(
    warehouse_id: int = Path(..., description="Warehouse ID", gt=0),
    pos_id: int = Path(..., description="POS ID", gt=0),
    current_account: dict = Depends(get_current_account),
    db: Session = Depends(get_db)
):
    """
    Assign warehouse to a POS.
    
    - **warehouse_id**: ID of warehouse to assign
    - **pos_id**: ID of POS to assign to
    """
    try:
        return InventoryService.assign_warehouse_to_pos(db, warehouse_id, pos_id)
    except NotFoundException as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)
    except BusinessRuleException as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@inventory_router.post("/warehouses/{warehouse_id}/unassign-from-pos",
    response_model=WarehouseOut,
    summary="Unassign warehouse from POS",
    description="Remove warehouse assignment from POS"
)
def unassign_warehouse_from_pos(
    warehouse_id: int = Path(..., description="Warehouse ID", gt=0),
    current_account: dict = Depends(get_current_account),
    db: Session = Depends(get_db)
):
    """
    Unassign warehouse from POS.
    
    - **warehouse_id**: ID of warehouse to unassign
    """
    try:
        return InventoryService.unassign_warehouse_from_pos(db, warehouse_id)
    except NotFoundException as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


# ================================
# INVENTORY ITEM ROUTES
# ================================

@inventory_router.post("/items/",
    response_model=InventoryOut,
    status_code=status.HTTP_201_CREATED,
    summary="Create inventory item",
    description="Add product to warehouse inventory or update existing"
)
def create_inventory_item(
    data: InventoryCreate,
    current_account: dict = Depends(get_current_account),
    db: Session = Depends(get_db)
):
    """
    Create or update inventory item.
    
    - **product_variant_id**: Product variant ID (required)
    - **warehouse_id**: Warehouse ID (required)
    - **quantity**: Initial quantity (default: 0)
    - **reserved_quantity**: Reserved quantity (default: 0)
    """
    try:
        return InventoryService.create_inventory_item(db, data)
    except NotFoundException as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)
    except ValidationException as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@inventory_router.get("/items/{inventory_id}",
    response_model=InventoryOut,
    summary="Get inventory item",
    description="Get inventory item details"
)
def get_inventory_item(
    inventory_id: int = Path(..., description="Inventory item ID", gt=0),
    current_account: dict = Depends(get_current_account),
    db: Session = Depends(get_db)
):
    """
    Get inventory item by ID.
    
    - **inventory_id**: ID of inventory item
    """
    try:
        return InventoryService.get_inventory_item(db, inventory_id)
    except NotFoundException as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@inventory_router.put("/items/{inventory_id}",
    response_model=InventoryOut,
    summary="Update inventory item",
    description="Update inventory item information"
)
def update_inventory_item(
    inventory_id: int = Path(..., description="Inventory item ID", gt=0),
    data: InventoryUpdate = Depends(),
    current_account: dict = Depends(get_current_account),
    db: Session = Depends(get_db)
):
    """
    Update inventory item.
    
    - **inventory_id**: ID of inventory item to update
    - **data**: Updated fields
    """
    try:
        return InventoryService.update_inventory_item(db, inventory_id, data)
    except NotFoundException as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)
    except ValidationException as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@inventory_router.get("/warehouses/{warehouse_id}/items",
    response_model=List[InventoryOut],
    summary="Get warehouse inventory",
    description="Get all inventory items for a warehouse"
)
def get_warehouse_inventory(
    warehouse_id: int = Path(..., description="Warehouse ID", gt=0),
    product_id: Optional[int] = Query(None, description="Filter by product ID"),
    low_stock_threshold: Optional[Decimal] = Query(None, description="Show items below threshold"),
    skip: int = Query(0, ge=0, description="Pagination offset"),
    limit: int = Query(100, ge=1, le=200, description="Items per page"),
    current_account: dict = Depends(get_current_account),
    db: Session = Depends(get_db)
):
    """
    Get inventory items for a warehouse.
    
    - **warehouse_id**: Warehouse ID
    - **product_id**: Filter by product
    - **low_stock_threshold**: Show low stock items
    - **skip**: Pagination offset
    - **limit**: Items per page (1-200)
    """
    try:
        items, total = InventoryService.get_inventory_by_warehouse(
            db, warehouse_id, product_id, low_stock_threshold, skip, limit
        )
        return items
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@inventory_router.get("/products/{product_variant_id}/stock",
    summary="Get stock across warehouses",
    description="Get inventory for a product variant across all warehouses"
)
def get_product_variant_stock(
    product_variant_id: int = Path(..., description="Product variant ID", gt=0),
    warehouse_id: Optional[int] = Query(None, description="Filter by warehouse"),
    current_account: dict = Depends(get_current_account),
    db: Session = Depends(get_db)
):
    """
    Get stock locations for a product variant.
    
    - **product_variant_id**: Product variant ID
    - **warehouse_id**: Optional warehouse filter
    """
    try:
        items = InventoryService.get_inventory_by_product_variant(db, product_variant_id, warehouse_id)
        return items
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


# ================================
# STOCK OPERATION ROUTES
# ================================

@inventory_router.post("/stock/increase",
    response_model=InventoryOut,
    summary="Increase stock",
    description="Increase stock quantity for a product in a warehouse"
)
def increase_stock(
    data: StockIncreaseRequest,
    current_account: dict = Depends(get_current_account),
    db: Session = Depends(get_db)
):
    """
    Increase stock quantity.
    
    - **warehouse_id**: Warehouse ID
    - **product_variant_id**: Product variant ID
    - **quantity**: Quantity to add (must be positive)
    - **source**: Source of increase (default: manual)
    """
    try:
        return InventoryService.increase_stock(
            db, data.warehouse_id, data.product_variant_id, data.quantity, data.source
        )
    except NotFoundException as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)
    except ValidationException as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@inventory_router.post("/stock/decrease",
    response_model=InventoryOut,
    summary="Decrease stock",
    description="Decrease stock quantity for a product in a warehouse"
)
def decrease_stock(
    data: StockDecreaseRequest,
    current_account: dict = Depends(get_current_account),
    db: Session = Depends(get_db)
):
    """
    Decrease stock quantity.
    
    - **warehouse_id**: Warehouse ID
    - **product_variant_id**: Product variant ID
    - **quantity**: Quantity to remove (must be positive)
    - **reserve_first**: Use reserved stock first (default: false)
    """
    try:
        return InventoryService.decrease_stock(
            db, data.warehouse_id, data.product_variant_id, data.quantity, data.reserve_first
        )
    except NotFoundException as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)
    except ValidationException as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)
    except InsufficientStockException as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@inventory_router.post("/stock/reserve",
    response_model=InventoryOut,
    summary="Reserve stock",
    description="Reserve stock for future sale/order"
)
def reserve_stock(
    data: StockReserveRequest,
    current_account: dict = Depends(get_current_account),
    db: Session = Depends(get_db)
):
    """
    Reserve stock.
    
    - **warehouse_id**: Warehouse ID
    - **product_variant_id**: Product variant ID
    - **quantity**: Quantity to reserve (must be positive)
    - **reference_type**: Reference type (default: sale)
    - **reference_id**: Optional reference ID
    """
    try:
        return InventoryService.reserve_stock(
            db, data.warehouse_id, data.product_variant_id, data.quantity,
            data.reference_type, data.reference_id
        )
    except NotFoundException as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)
    except ValidationException as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)
    except InsufficientStockException as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@inventory_router.post("/stock/release",
    response_model=InventoryOut,
    summary="Release reserved stock",
    description="Release previously reserved stock"
)
def release_reserved_stock(
    data: StockReleaseRequest,
    current_account: dict = Depends(get_current_account),
    db: Session = Depends(get_db)
):
    """
    Release reserved stock.
    
    - **warehouse_id**: Warehouse ID
    - **product_variant_id**: Product variant ID
    - **quantity**: Quantity to release (must be positive)
    """
    try:
        return InventoryService.release_reserved_stock(
            db, data.warehouse_id, data.product_variant_id, data.quantity
        )
    except NotFoundException as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)
    except ValidationException as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


# @inventory_router.post("/stock/transfer",
#     summary="Transfer stock",
#     description="Transfer stock between warehouses"
# )
# def transfer_stock(
#     data: StockTransferRequest,
#     current_account: dict = Depends(get_current_account),
#     db: Session = Depends(get_db)
# ):
#     """
#     Transfer stock between warehouses.
    
#     - **from_warehouse_id**: Source warehouse ID
#     - **to_warehouse_id**: Destination warehouse ID
#     - **product_variant_id**: Product variant ID
#     - **quantity**: Quantity to transfer (must be positive)
#     - **notes**: Optional notes
#     """
#     try:
#         return InventoryService.transfer_stock(
#             db, data.from_warehouse_id, data.to_warehouse_id,
#             data.product_variant_id, data.quantity, data.notes
#         )
#     except NotFoundException as e:
#         raise HTTPException(status_code=e.status_code, detail=e.message)
#     except ValidationException as e:
#         raise HTTPException(status_code=e.status_code, detail=e.message)
#     except InsufficientStockException as e:
#         raise HTTPException(status_code=e.status_code, detail=e.message)
#     except Exception as e:
#         raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@inventory_router.post("/stock/check",
    response_model=StockCheckResponse,
    summary="Check stock availability",
    description="Check if sufficient stock is available"
)
def check_stock_availability(
    data: StockCheckRequest,
    current_account: dict = Depends(get_current_account),
    db: Session = Depends(get_db)
):
    """
    Check stock availability.
    
    - **warehouse_id**: Warehouse ID
    - **product_variant_id**: Product variant ID
    - **quantity**: Required quantity (must be positive)
    """
    try:
        return InventoryService.check_stock_availability(
            db, data.warehouse_id, data.product_variant_id, data.quantity
        )
    except NotFoundException as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


# ================================
# PROCUREMENT INTEGRATION
# ================================

@inventory_router.post("/procurements/receive",
    summary="Receive procurement",
    description="Receive procurement items into warehouse inventory"
)
def receive_procurement(
    data: ProcurementReceiveRequest,
    current_account: dict = Depends(get_current_account),
    db: Session = Depends(get_db)
):
    """
    Receive procurement into inventory.
    
    - **procurement_id**: Procurement ID
    - **warehouse_id**: Warehouse ID to receive into
    """
    try:
        return InventoryService.receive_procurement(db, data.procurement_id, data.warehouse_id)
    except NotFoundException as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)
    except ValidationException as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


# ================================
# SALE PROCESSING INTEGRATION
# ================================

@inventory_router.post("/sales/process",
    response_model=SaleProcessResponse,
    summary="Process sale items",
    description="Process sale items and update inventory (reserve stock)"
)
def process_sale_items(
    data: SaleProcessRequest,
    current_account: dict = Depends(get_current_account),
    db: Session = Depends(get_db)
):
    """
    Process sale items for inventory.
    
    - **pos_id**: POS ID
    - **items**: List of sale items with product variant and quantity
    """
    try:
        return InventoryService.process_sale_items(db, data.pos_id, data.items)
    except NotFoundException as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)
    except ValidationException as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)
    except InsufficientStockException as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@inventory_router.post("/sales/{sale_id}/finalize",
    summary="Finalize sale",
    description="Finalize sale and deduct reserved stock from inventory"
)
def finalize_sale(
    sale_id: int = Path(..., description="Sale ID", gt=0),
    pos_id: int = Query(..., description="POS ID", gt=0),
    items: List[dict] = Depends(),
    current_account: dict = Depends(get_current_account),
    db: Session = Depends(get_db)
):
    """
    Finalize sale inventory.
    
    - **sale_id**: Sale ID
    - **pos_id**: POS ID
    - **items**: List of sale items (from sale creation)
    """
    try:
        return InventoryService.finalize_sale(db, sale_id, pos_id, items)
    except NotFoundException as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)
    except ValidationException as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@inventory_router.post("/sales/cancel-reservations",
    summary="Cancel sale reservations",
    description="Cancel sale reservations and release stock"
)
def cancel_sale_reservations(
    pos_id: int = Query(..., description="POS ID", gt=0),
    items: List[dict] = Depends(),
    current_account: dict = Depends(get_current_account),
    db: Session = Depends(get_db)
):
    """
    Cancel sale reservations.
    
    - **pos_id**: POS ID
    - **items**: List of items to cancel
    """
    try:
        return InventoryService.cancel_sale_reservations(db, pos_id, items)
    except NotFoundException as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)
    except ValidationException as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


# ================================
# INVENTORY REPORTS
# ================================

@inventory_router.get("/reports/summary",
    response_model=InventorySummary,
    summary="Inventory summary",
    description="Get inventory summary statistics"
)
def get_inventory_summary(
    warehouse_id: Optional[int] = Query(None, description="Filter by warehouse"),
    current_account: dict = Depends(get_current_account),
    db: Session = Depends(get_db)
):
    """
    Get inventory summary.
    
    - **warehouse_id**: Optional warehouse filter
    """
    try:
        return InventoryService.get_inventory_summary(db, warehouse_id)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@inventory_router.get("/reports/low-stock",
    response_model=List[LowStockItem],
    summary="Low stock report",
    description="Get items with low stock (below threshold)"
)
def get_low_stock_items(
    warehouse_id: Optional[int] = Query(None, description="Filter by warehouse"),
    threshold: Decimal = Query(10, gt=0, description="Low stock threshold"),
    current_account: dict = Depends(get_current_account),
    db: Session = Depends(get_db)
):
    """
    Get low stock items.
    
    - **warehouse_id**: Optional warehouse filter
    - **threshold**: Low stock threshold (default: 10)
    """
    try:
        return InventoryService.get_low_stock_items(db, warehouse_id, threshold)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@inventory_router.get("/reports/stock-levels",
    response_model=List[StockLevelReportItem],
    summary="Stock level report",
    description="Get comprehensive stock level report"
)
def get_stock_level_report(
    warehouse_id: Optional[int] = Query(None, description="Filter by warehouse"),
    product_id: Optional[int] = Query(None, description="Filter by product"),
    current_account: dict = Depends(get_current_account),
    db: Session = Depends(get_db)
):
    """
    Get stock level report.
    
    - **warehouse_id**: Optional warehouse filter
    - **product_id**: Optional product filter
    """
    try:
        return InventoryService.get_stock_level_report(db, warehouse_id, product_id)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@inventory_router.get("/reports/value",
    summary="Inventory value report",
    description="Calculate total inventory value"
)
def get_inventory_value_report(
    warehouse_id: Optional[int] = Query(None, description="Filter by warehouse"),
    current_account: dict = Depends(get_current_account),
    db: Session = Depends(get_db)
):
    """
    Get inventory value.
    
    - **warehouse_id**: Optional warehouse filter
    """
    try:
        return InventoryService.get_inventory_value_report(db, warehouse_id)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
