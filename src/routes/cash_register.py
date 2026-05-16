from datetime import date
from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from src.core.database import get_db
from src.services.cash_register_service import CashRegisterService
from src.core.auth_dependencies import get_current_account, require_permission
from src.schemas.cash_register import (
    CashRegisterBalance,
    DailyCashRegister,
    WeeklyCashRegister,
    MonthlyCashRegister,
    CashRegisterComparison,
    CashRegisterReconciliation
)

cash_register_route = APIRouter(prefix="/api/cash-register", tags=["POS Cash Register"])


# ================================
# BALANCE ENDPOINT
# ================================
@cash_register_route.get("/pos/{pos_id}/balance", response_model=CashRegisterBalance)
def get_cash_register_balance(
    pos_id: int,
    start_date: Optional[date] = Query(None, description="Start date of period"),
    end_date: Optional[date] = Query(None, description="End date of period"),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_account)
):
    """
    Get cash register balance for a period
    
    Formula: POS Balance + Available Cash (CASH sales only) - POS Expenses (APPROVED/PAID)
    
    - **pos_id**: POS ID
    - **start_date**: Optional start date (defaults to period start)
    - **end_date**: Optional end date (defaults to today)
    """
    balance = CashRegisterService.calculate_cash_register_balance(
        db, pos_id, start_date, end_date
    )
    return balance


# ================================
# DAILY ENDPOINT
# ================================
@cash_register_route.get("/pos/{pos_id}/daily", response_model=DailyCashRegister)
def get_daily_cash_register(
    pos_id: int,
    report_date: Optional[date] = Query(None, description="Report date (defaults to today)"),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_account)
):
    """
    Get daily cash register summary (CASH sales only)
    
    Returns:
    - Opening balance
    - Cash sales for the day
    - Expenses for the day
    - Closing balance
    - Payment method breakdown
    
    - **pos_id**: POS ID
    - **report_date**: Optional specific date (defaults to today)
    """
    summary = CashRegisterService.get_daily_cash_register(db, pos_id, report_date)
    return summary


# ================================
# WEEKLY ENDPOINT
# ================================
@cash_register_route.get("/pos/{pos_id}/weekly", response_model=WeeklyCashRegister)
def get_weekly_cash_register(
    pos_id: int,
    week_start: Optional[date] = Query(None, description="Week start date (Monday)"),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_account)
):
    """
    Get weekly cash register summary (CASH sales only)
    
    Returns:
    - Weekly totals
    - Daily breakdown for each day
    - Opening and closing balances
    
    - **pos_id**: POS ID
    - **week_start**: Optional week start (Monday). Defaults to current week
    """
    summary = CashRegisterService.get_weekly_cash_register(db, pos_id, week_start)
    return summary


# ================================
# MONTHLY ENDPOINT
# ================================
@cash_register_route.get("/pos/{pos_id}/monthly", response_model=MonthlyCashRegister)
def get_monthly_cash_register(
    pos_id: int,
    year: int = Query(..., ge=2000, le=2099, description="Year (e.g., 2026)"),
    month: int = Query(..., ge=1, le=12, description="Month (1-12)"),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_account)
):
    """
    Get monthly cash register summary (CASH sales only)
    
    Returns:
    - Monthly totals
    - Expense summary by category
    - Opening and closing balances
    
    - **pos_id**: POS ID
    - **year**: Year (2000-2099)
    - **month**: Month (1-12)
    """
    summary = CashRegisterService.get_monthly_cash_register(db, pos_id, year, month)
    return summary


# ================================
# COMPARISON ENDPOINT
# ================================
@cash_register_route.get("/pos/{pos_id}/comparison", response_model=CashRegisterComparison)
def compare_cash_register(
    pos_id: int,
    period_type: str = Query("daily", pattern="^(daily|monthly)$", description="Comparison period type"),
    start_date: Optional[date] = Query(None, description="Start date"),
    end_date: Optional[date] = Query(None, description="End date"),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_account)
):
    """
    Compare cash register balances across periods
    
    Supports two comparison types:
    - **daily**: Compare daily balances (default: last 30 days)
    - **monthly**: Compare monthly balances (default: last 12 months)
    
    - **pos_id**: POS ID
    - **period_type**: 'daily' or 'monthly'
    - **start_date**: Optional start date
    - **end_date**: Optional end date
    """
    comparison = CashRegisterService.get_cash_register_comparison(
        db, pos_id, period_type, start_date, end_date
    )
    return comparison


# ================================
# RECONCILIATION ENDPOINT
# ================================
@cash_register_route.get("/pos/{pos_id}/reconciliation", response_model=CashRegisterReconciliation)
def get_cash_reconciliation(
    pos_id: int,
    report_date: Optional[date] = Query(None, description="Reconciliation date"),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_account)
):
    """
    Get detailed cash register reconciliation for auditing
    
    Returns:
    - Daily summary
    - Detailed list of all cash sales
    - Detailed list of all expenses
    
    Perfect for:
    - End-of-day reconciliation
    - Auditing
    - Discrepancy investigation
    
    - **pos_id**: POS ID
    - **report_date**: Optional specific date (defaults to today)
    """
    reconciliation = CashRegisterService.get_cash_register_reconciliation(
        db, pos_id, report_date
    )
    return reconciliation