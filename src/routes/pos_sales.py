# src/routes/sale.py
from fastapi import APIRouter, Depends, Query, HTTPException, status, Path
from sqlalchemy.orm import Session
from datetime import date, datetime
from decimal import Decimal
from typing import List, Optional

from src.core.database import get_db
from src.core.auth_dependencies import get_current_account
from src.models.pos import SaleStatus, PaymentMethod
from src.schemas.pos import (
    SaleCreate, SaleUpdate, SaleOut, SaleItemOut,
    SaleReturnCreate, SaleReturnOut, CustomerInfoOut,
    SaleSummary, DailySalesReport, SalesTrendItem, TopProductReport
)
from src.services.pos_sales import SaleService, SaleNotFoundException, SaleValidationException, SaleBusinessRuleException

sales_router = APIRouter(prefix="/sales", tags=["POS Sales"])


# ================================
# SALE CRUD ROUTES
# ================================

@sales_router.post("/",
    response_model=SaleOut,
    status_code=status.HTTP_201_CREATED,
    summary="Create sale",
    description="Create a new sale with inventory validation"
)
def create_sale(
    data: SaleCreate,
    current_account: dict = Depends(get_current_account),
    db: Session = Depends(get_db)
):
    """
    Create a new sale.
    
    - **pos_id**: POS ID (required)
    - **created_by_id**: dict ID who created sale (required)
    - **customer_id**: Optional customer ID
    - **payment_mode**: Payment method (required)
    - **items**: List of sale items (required)
    - **customer_info**: Customer info for walk-in sales (optional)
    - **tax_rate**: Tax rate percentage (default: 0)
    - **discount_amount**: Discount amount (default: 0)
    - **notes**: Optional notes
    """
    try:
        return SaleService.create_sale(db, data)
    except SaleNotFoundException as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)
    except SaleValidationException as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@sales_router.get("/{sale_id}",
    response_model=SaleOut,
    summary="Get sale details",
    description="Get detailed information about a sale"
)
def get_sale(
    sale_id: int = Path(..., description="Sale ID", gt=0),
    current_account: dict = Depends(get_current_account),
    db: Session = Depends(get_db)
):
    """
    Get sale by ID.
    
    - **sale_id**: ID of the sale to retrieve
    """
    try:
        return SaleService.get_sale(db, sale_id)
    except SaleNotFoundException as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@sales_router.put("/{sale_id}",
    response_model=SaleOut,
    summary="Update sale",
    description="Update sale information (limited updates allowed)"
)
def update_sale(
    sale_id: int = Path(..., description="Sale ID", gt=0),
    data: SaleUpdate = Depends(),
    current_account: dict = Depends(get_current_account),
    db: Session = Depends(get_db)
):
    """
    Update sale details.
    
    - **sale_id**: ID of sale to update
    - **status**: New status (cannot cancel completed sales)
    - **notes**: Updated notes
    """
    try:
        return SaleService.update_sale(db, sale_id, data)
    except SaleNotFoundException as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)
    except SaleBusinessRuleException as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@sales_router.post("/{sale_id}/cancel",
    response_model=SaleOut,
    summary="Cancel sale",
    description="Cancel a sale (only for pending/partial sales)"
)
def cancel_sale(
    sale_id: int = Path(..., description="Sale ID", gt=0),
    reason: Optional[str] = Query(None, description="Reason for cancellation"),
    current_account: dict = Depends(get_current_account),
    db: Session = Depends(get_db)
):
    """
    Cancel a sale.
    
    - **sale_id**: ID of sale to cancel
    - **reason**: Optional reason for cancellation
    - Note: Cannot cancel completed sales
    """
    try:
        return SaleService.cancel_sale(db, sale_id, reason)
    except SaleNotFoundException as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)
    except SaleBusinessRuleException as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@sales_router.get("/",
    response_model=List[SaleOut],
    summary="List sales",
    description="Get list of sales with filtering"
)
def list_sales(
    pos_id: Optional[int] = Query(None, description="Filter by POS"),
    customer_id: Optional[int] = Query(None, description="Filter by customer"),
    start_date: Optional[date] = Query(None, description="Filter by start date"),
    end_date: Optional[date] = Query(None, description="Filter by end date"),
    status: Optional[SaleStatus] = Query(None, description="Filter by status"),
    payment_mode: Optional[PaymentMethod] = Query(None, description="Filter by payment method"),
    skip: int = Query(0, ge=0, description="Pagination offset"),
    limit: int = Query(50, ge=1, le=100, description="Items per page"),
    current_account: dict = Depends(get_current_account),
    db: Session = Depends(get_db)
):
    """
    List sales with filtering.
    
    - **pos_id**: Filter by POS
    - **customer_id**: Filter by customer
    - **start_date**: Filter by start date
    - **end_date**: Filter by end date
    - **status**: Filter by sale status
    - **payment_mode**: Filter by payment method
    - **skip**: Pagination offset
    - **limit**: Items per page (1-100)
    """
    try:
        sales, total = SaleService.list_sales(
            db, pos_id, customer_id, start_date, end_date, status, payment_mode, skip, limit
        )
        return sales
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


# ================================
# SALE RETURNS ROUTES
# ================================


@sales_router.get("/returns/",
    response_model=List[SaleReturnOut],
    summary="List sale returns",
    description="Get list of sale returns with filtering"
)
def list_sale_returns(
    sale_id: Optional[int] = Query(None, description="Filter by sale"),
    pos_id: Optional[int] = Query(None, description="Filter by POS"),
    start_date: Optional[date] = Query(None, description="Filter by start date"),
    end_date: Optional[date] = Query(None, description="Filter by end date"),
    current_account: dict = Depends(get_current_account),
    db: Session = Depends(get_db)
):
    """
    List sale returns.
    
    - **sale_id**: Filter by sale ID
    - **pos_id**: Filter by POS ID
    - **start_date**: Filter by start date
    - **end_date**: Filter by end date
    """
    try:
        return SaleService.get_sale_returns(db, sale_id, pos_id, start_date, end_date)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


# ================================
# SALE REPORTS & ANALYTICS
# ================================

@sales_router.get("/reports/summary",
    response_model=SaleSummary,
    summary="Sales summary",
    description="Get sales summary statistics"
)
def get_sales_summary(
    pos_id: Optional[int] = Query(None, description="Filter by POS"),
    start_date: Optional[date] = Query(None, description="Start date for summary"),
    end_date: Optional[date] = Query(None, description="End date for summary"),
    current_account: dict = Depends(get_current_account),
    db: Session = Depends(get_db)
):
    """
    Get sales summary.
    
    - **pos_id**: Optional POS filter
    - **start_date**: Optional start date
    - **end_date**: Optional end date
    """
    try:
        return SaleService.get_sales_summary(db, pos_id, start_date, end_date)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@sales_router.get("/reports/daily",
    response_model=DailySalesReport,
    summary="Daily sales report",
    description="Get daily sales report for a specific date"
)
def get_daily_sales_report(
    pos_id: Optional[int] = Query(None, description="Filter by POS"),
    date: Optional[date] = Query(None, description="Report date (default: today)"),
    current_account: dict = Depends(get_current_account),
    db: Session = Depends(get_db)
):
    """
    Get daily sales report.
    
    - **pos_id**: Optional POS filter
    - **date**: Report date (default: today)
    """
    try:
        return SaleService.get_daily_sales_report(db, pos_id, date)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@sales_router.get("/reports/trend",
    response_model=List[SalesTrendItem],
    summary="Sales trend",
    description="Get sales trend over time"
)
def get_sales_trend(
    pos_id: Optional[int] = Query(None, description="Filter by POS"),
    days: int = Query(30, ge=1, le=365, description="Number of days for trend"),
    current_account: dict = Depends(get_current_account),
    db: Session = Depends(get_db)
):
    """
    Get sales trend.
    
    - **pos_id**: Optional POS filter
    - **days**: Number of days for trend (1-365, default: 30)
    """
    try:
        return SaleService.get_sales_trend(db, pos_id, days)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@sales_router.get("/reports/top-products",
    response_model=List[TopProductReport],
    summary="Top products report",
    description="Get top selling products report"
)
def get_top_products_report(
    pos_id: Optional[int] = Query(None, description="Filter by POS"),
    start_date: Optional[date] = Query(None, description="Start date for report"),
    end_date: Optional[date] = Query(None, description="End date for report"),
    limit: int = Query(10, ge=1, le=50, description="Number of top products"),
    current_account: dict = Depends(get_current_account),
    db: Session = Depends(get_db)
):
    """
    Get top products report.
    
    - **pos_id**: Optional POS filter
    - **start_date**: Optional start date
    - **end_date**: Optional end date
    - **limit**: Number of top products (1-50, default: 10)
    """
    try:
        return SaleService.get_top_products_report(db, pos_id, start_date, end_date, limit)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@sales_router.get("/pos/{pos_id}/recent",
    response_model=List[SaleOut],
    summary="Recent sales by POS",
    description="Get recent sales for a specific POS"
)
def get_recent_sales_by_pos(
    pos_id: int = Path(..., description="POS ID", gt=0),
    limit: int = Query(10, ge=1, le=50, description="Number of recent sales"),
    current_account: dict = Depends(get_current_account),
    db: Session = Depends(get_db)
):
    """
    Get recent sales for a POS.
    
    - **pos_id**: POS ID
    - **limit**: Number of recent sales (1-50, default: 10)
    """
    try:
        sales, _ = SaleService.list_sales(
            db, pos_id=pos_id, skip=0, limit=limit
        )
        return sales
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@sales_router.get("/customer/{customer_id}/history",
    response_model=List[SaleOut],
    summary="Customer sales history",
    description="Get sales history for a customer"
)
def get_customer_sales_history(
    customer_id: int = Path(..., description="Customer ID", gt=0),
    skip: int = Query(0, ge=0, description="Pagination offset"),
    limit: int = Query(20, ge=1, le=100, description="Items per page"),
    current_account: dict = Depends(get_current_account),
    db: Session = Depends(get_db)
):
    """
    Get customer sales history.
    
    - **customer_id**: Customer ID
    - **skip**: Pagination offset
    - **limit**: Items per page (1-100)
    """
    try:
        sales, _ = SaleService.list_sales(
            db, customer_id=customer_id, skip=skip, limit=limit
        )
        return sales
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
