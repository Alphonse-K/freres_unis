# src/routes/expense.py
from fastapi import APIRouter, Depends, Query, HTTPException, status, Path
from sqlalchemy.orm import Session
from datetime import date, datetime
from decimal import Decimal
from typing import List, Optional

from src.core.database import get_db
from src.core.auth_dependencies import get_current_account
from src.models.pos import POSExpenseCategory, POSExpenseStatus
from src.schemas.pos import (
    POSExpenseCreate, POSExpenseUpdate, POSExpenseOut, POSExpenseFilter,
    ExpenseSummary, ExpensesTrendItem, CategoryBreakdown, MonthlyExpenseReport,
    ExpenseComparison, ExpenseApproveRequest, ExpenseRejectRequest
)
from src.services.pos_expenses import ExpenseService, ExpenseNotFoundException, ExpenseValidationException, ExpenseBusinessRuleException

expenses_router = APIRouter(prefix="/expenses", tags=["POS Expenses"])


# ================================
# EXPENSE CRUD ROUTES
# ================================

@expenses_router.post("/",
    response_model=POSExpenseOut,
    status_code=status.HTTP_201_CREATED,
    summary="Create expense",
    description="Create a new expense"
)
def create_expense(
    data: POSExpenseCreate,
    current_account: dict = Depends(get_current_account),
    db: Session = Depends(get_db)
):
    """
    Create a new expense.
    
    - **pos_id**: POS ID (required)
    - **created_by_id**: dict ID who created expense (required)
    - **category**: Expense category (required)
    - **amount**: Expense amount (required, positive)
    - **description**: Optional description
    - **expense_date**: Expense date (default: current date)
    - **status**: Expense status (default: draft)
    - **approved_by_id**: Optional approver ID
    """
    try:
        return ExpenseService.create_expense(db, data)
    except ExpenseNotFoundException as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)
    except ExpenseValidationException as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@expenses_router.get("/{expense_id}",
    response_model=POSExpenseOut,
    summary="Get expense details",
    description="Get detailed information about an expense"
)
def get_expense(
    expense_id: int = Path(..., description="Expense ID", gt=0),
    current_account: dict = Depends(get_current_account),
    db: Session = Depends(get_db)
):
    """
    Get expense by ID.
    
    - **expense_id**: ID of the expense to retrieve
    """
    try:
        return ExpenseService.get_expense(db, expense_id)
    except ExpenseNotFoundException as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@expenses_router.get("/reference/{reference}",
    response_model=POSExpenseOut,
    summary="Get expense by reference",
    description="Get expense by reference number"
)
def get_expense_by_reference(
    reference: str = Path(..., description="Expense reference number"),
    current_account: dict = Depends(get_current_account),
    db: Session = Depends(get_db)
):
    """
    Get expense by reference number.
    
    - **reference**: Expense reference number (format: EXP-XXXX-YYMM-NNNN)
    """
    try:
        return ExpenseService.get_expense_by_reference(db, reference)
    except ExpenseNotFoundException as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@expenses_router.put("/{expense_id}",
    response_model=POSExpenseOut,
    summary="Update expense",
    description="Update expense information"
)
def update_expense(
    expense_id: int = Path(..., description="Expense ID", gt=0),
    data: POSExpenseUpdate = Depends(),
    current_account: dict = Depends(get_current_account),
    db: Session = Depends(get_db)
):
    """
    Update expense details.
    
    - **expense_id**: ID of expense to update
    - **category**: Updated category
    - **amount**: Updated amount (must be positive)
    - **description**: Updated description
    - **expense_date**: Updated date
    - **status**: Updated status
    - **approved_by_id**: Updated approver ID
    - Note: Cannot update approved or paid expenses
    """
    try:
        return ExpenseService.update_expense(db, expense_id, data)
    except ExpenseNotFoundException as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)
    except ExpenseValidationException as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)
    except ExpenseBusinessRuleException as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@expenses_router.delete("/{expense_id}",
    summary="Delete expense",
    description="Delete an expense (only if in draft status)"
)
def delete_expense(
    expense_id: int = Path(..., description="Expense ID", gt=0),
    current_account: dict = Depends(get_current_account),
    db: Session = Depends(get_db)
):
    """
    Delete expense.
    
    - **expense_id**: ID of expense to delete
    - Note: Can only delete expenses in draft status
    """
    try:
        success = ExpenseService.delete_expense(db, expense_id)
        if success:
            return {"message": "Expense deleted successfully"}
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete expense"
        )
    except ExpenseNotFoundException as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)
    except ExpenseBusinessRuleException as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@expenses_router.get("/",
    response_model=List[POSExpenseOut],
    summary="List expenses",
    description="Get list of expenses with filtering"
)
def list_expenses(
    pos_id: Optional[int] = Query(None, description="Filter by POS"),
    category: Optional[POSExpenseCategory] = Query(None, description="Filter by category"),
    status: Optional[POSExpenseStatus] = Query(None, description="Filter by status"),
    start_date: Optional[date] = Query(None, description="Filter by start date"),
    end_date: Optional[date] = Query(None, description="Filter by end date"),
    created_by_id: Optional[int] = Query(None, description="Filter by creator"),
    approved_by_id: Optional[int] = Query(None, description="Filter by approver"),
    skip: int = Query(0, ge=0, description="Pagination offset"),
    limit: int = Query(50, ge=1, le=100, description="Items per page"),
    current_account: dict = Depends(get_current_account),
    db: Session = Depends(get_db)
):
    """
    List expenses with filtering.
    
    - **pos_id**: Filter by POS
    - **category**: Filter by category
    - **status**: Filter by status
    - **start_date**: Filter by start date
    - **end_date**: Filter by end date
    - **created_by_id**: Filter by creator
    - **approved_by_id**: Filter by approver
    - **skip**: Pagination offset
    - **limit**: Items per page (1-100)
    """
    try:
        expenses, total = ExpenseService.list_expenses(
            db, pos_id, category, status, start_date, end_date,
            created_by_id, approved_by_id, skip, limit
        )
        return expenses
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


# ================================
# EXPENSE WORKFLOW ROUTES
# ================================

@expenses_router.post("/{expense_id}/approve",
    response_model=POSExpenseOut,
    summary="Approve expense",
    description="Approve an expense (only draft expenses can be approved)"
)
def approve_expense(
    expense_id: int = Path(..., description="Expense ID", gt=0),
    data: ExpenseApproveRequest = Depends(),
    current_account: dict = Depends(get_current_account),
    db: Session = Depends(get_db)
):
    """
    Approve an expense.
    
    - **expense_id**: ID of expense to approve
    - **approver_id**: ID of dict approving the expense
    """
    try:
        return ExpenseService.approve_expense(db, expense_id, data.approver_id)
    except ExpenseNotFoundException as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)
    except ExpenseBusinessRuleException as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@expenses_router.post("/{expense_id}/reject",
    response_model=POSExpenseOut,
    summary="Reject expense",
    description="Reject an expense (only draft expenses can be rejected)"
)
def reject_expense(
    expense_id: int = Path(..., description="Expense ID", gt=0),
    data: ExpenseRejectRequest = Depends(),
    current_account: dict = Depends(get_current_account),
    db: Session = Depends(get_db)
):
    """
    Reject an expense.
    
    - **expense_id**: ID of expense to reject
    - **reason**: Optional reason for rejection
    """
    try:
        return ExpenseService.reject_expense(db, expense_id, data.reason)
    except ExpenseNotFoundException as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)
    except ExpenseBusinessRuleException as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@expenses_router.post("/{expense_id}/mark-paid",
    response_model=POSExpenseOut,
    summary="Mark expense as paid",
    description="Mark an expense as paid (only approved expenses can be marked paid)"
)
def mark_expense_as_paid(
    expense_id: int = Path(..., description="Expense ID", gt=0),
    current_account: dict = Depends(get_current_account),
    db: Session = Depends(get_db)
):
    """
    Mark expense as paid.
    
    - **expense_id**: ID of expense to mark as paid
    """
    try:
        return ExpenseService.mark_expense_as_paid(db, expense_id)
    except ExpenseNotFoundException as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)
    except ExpenseBusinessRuleException as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


# ================================
# EXPENSE REPORTS & ANALYTICS
# ================================

@expenses_router.get("/reports/summary",
    response_model=ExpenseSummary,
    summary="Expenses summary",
    description="Get expenses summary statistics"
)
def get_expenses_summary(
    pos_id: Optional[int] = Query(None, description="Filter by POS"),
    start_date: Optional[date] = Query(None, description="Start date for summary"),
    end_date: Optional[date] = Query(None, description="End date for summary"),
    current_account: dict = Depends(get_current_account),
    db: Session = Depends(get_db)
):
    """
    Get expenses summary.
    
    - **pos_id**: Optional POS filter
    - **start_date**: Optional start date
    - **end_date**: Optional end date
    """
    try:
        return ExpenseService.get_expenses_summary(db, pos_id, start_date, end_date)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@expenses_router.get("/reports/trend",
    response_model=List[ExpensesTrendItem],
    summary="Expenses trend",
    description="Get expenses trend over time"
)
def get_expenses_trend(
    pos_id: Optional[int] = Query(None, description="Filter by POS"),
    days: int = Query(30, ge=1, le=365, description="Number of days for trend"),
    current_account: dict = Depends(get_current_account),
    db: Session = Depends(get_db)
):
    """
    Get expenses trend.
    
    - **pos_id**: Optional POS filter
    - **days**: Number of days for trend (1-365, default: 30)
    """
    try:
        return ExpenseService.get_expenses_trend(db, pos_id, days)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@expenses_router.get("/reports/category-breakdown",
    response_model=CategoryBreakdown,
    summary="Category breakdown",
    description="Get detailed expense breakdown by category"
)
def get_category_breakdown(
    pos_id: Optional[int] = Query(None, description="Filter by POS"),
    start_date: Optional[date] = Query(None, description="Start date for breakdown"),
    end_date: Optional[date] = Query(None, description="End date for breakdown"),
    current_account: dict = Depends(get_current_account),
    db: Session = Depends(get_db)
):
    """
    Get expense category breakdown.
    
    - **pos_id**: Optional POS filter
    - **start_date**: Optional start date
    - **end_date**: Optional end date
    """
    try:
        return ExpenseService.get_category_breakdown(db, pos_id, start_date, end_date)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@expenses_router.get("/reports/monthly",
    response_model=MonthlyExpenseReport,
    summary="Monthly expense report",
    description="Get monthly expense report"
)
def get_monthly_expense_report(
    pos_id: Optional[int] = Query(None, description="Filter by POS"),
    year: Optional[int] = Query(None, description="Year for report"),
    month: Optional[int] = Query(None, description="Month for report (1-12)"),
    current_account: dict = Depends(get_current_account),
    db: Session = Depends(get_db)
):
    """
    Get monthly expense report.
    
    - **pos_id**: Optional POS filter
    - **year**: Report year (default: current year)
    - **month**: Report month (1-12, default: current month)
    """
    try:
        return ExpenseService.get_monthly_expense_report(db, pos_id, year, month)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@expenses_router.get("/reports/comparison",
    response_model=ExpenseComparison,
    summary="Expense comparison",
    description="Compare expenses with previous period"
)
def compare_with_previous_period(
    pos_id: Optional[int] = Query(None, description="Filter by POS"),
    days: int = Query(30, ge=1, le=90, description="Period length in days"),
    current_account: dict = Depends(get_current_account),
    db: Session = Depends(get_db)
):
    """
    Compare expenses with previous period.
    
    - **pos_id**: Optional POS filter
    - **days**: Period length in days (1-90, default: 30)
    """
    try:
        return ExpenseService.compare_with_previous_period(db, pos_id, days)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@expenses_router.get("/pos/{pos_id}/recent",
    response_model=List[POSExpenseOut],
    summary="Recent expenses by POS",
    description="Get recent expenses for a specific POS"
)
def get_recent_expenses_by_pos(
    pos_id: int = Path(..., description="POS ID", gt=0),
    limit: int = Query(10, ge=1, le=50, description="Number of recent expenses"),
    current_account: dict = Depends(get_current_account),
    db: Session = Depends(get_db)
):
    """
    Get recent expenses for a POS.
    
    - **pos_id**: POS ID
    - **limit**: Number of recent expenses (1-50, default: 10)
    """
    try:
        expenses, _ = ExpenseService.list_expenses(
            db, pos_id=pos_id, skip=0, limit=limit
        )
        return expenses
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@expenses_router.get("/categories/",
    summary="List expense categories",
    description="Get list of all expense categories"
)
def list_expense_categories(
    current_account: dict = Depends(get_current_account),
    db: Session = Depends(get_db)
):
    """
    Get all expense categories.
    """
    try:
        categories = [
            {"value": category.value, "label": category.value.replace("_", " ").title()}
            for category in POSExpenseCategory
        ]
        return categories
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@expenses_router.get("/statuses/",
    summary="List expense statuses",
    description="Get list of all expense statuses"
)
def list_expense_statuses(
    current_account: dict = Depends(get_current_account),
    db: Session = Depends(get_db)
):
    """
    Get all expense statuses.
    """
    try:
        statuses = [
            {"value": status.value, "label": status.value.replace("_", " ").title()}
            for status in POSExpenseStatus
        ]
        return statuses
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


# # ================================
# # ERROR HANDLING
# # ================================

# @expenses_router.exception_handler(ExpenseNotFoundException)
# async def expense_not_found_exception_handler(request, exc):
#     """Handle expense not found exceptions"""
#     from fastapi.responses import JSONResponse
#     return JSONResponse(
#         status_code=exc.status_code,
#         content={"error": exc.message}
#     )


# @expenses_router.exception_handler(ExpenseValidationException)
# async def expense_validation_exception_handler(request, exc):
#     """Handle expense validation exceptions"""
#     from fastapi.responses import JSONResponse
#     return JSONResponse(
#         status_code=exc.status_code,
#         content={"error": exc.message}
#     )


# @expenses_router.exception_handler(ExpenseBusinessRuleException)
# async def expense_business_rule_exception_handler(request, exc):
#     """Handle expense business rule exceptions"""
#     from fastapi.responses import JSONResponse
#     return JSONResponse(
#         status_code=exc.status_code,
#         content={"error": exc.message}
#     )