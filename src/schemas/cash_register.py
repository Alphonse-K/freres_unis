from datetime import date, datetime
from decimal import Decimal
from typing import Optional, List
from pydantic import BaseModel, Field, ConfigDict


# ================================
# PAYMENT METHOD BREAKDOWN
# ================================
class PaymentMethodBreakdown(BaseModel):
    """Payment method breakdown for a period"""
    model_config = ConfigDict(from_attributes=True)
    
    method: str = Field(..., description="Payment method (cash, card, etc.)")
    count: int = Field(..., ge=0, description="Number of transactions")
    total: float = Field(..., ge=0, description="Total amount")


# ================================
# DAILY CASH REGISTER
# ================================
class DailyCashRegister(BaseModel):
    """Daily cash register summary"""
    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "date": "2026-05-12",
                "opening_balance": 10000.00,
                "cash_sales": 5500.50,
                "cash_sales_count": 45,
                "total_expenses": 1200.00,
                "closing_balance": 14300.50,
                "payment_methods": [
                    {"method": "cash", "count": 45, "total": 5500.50},
                    {"method": "card", "count": 12, "total": 3200.00}
                ]
            }
        }
    )
    
    report_date: date = Field(..., alias="date", description="Report date")
    opening_balance: float = Field(..., ge=0, description="Opening balance for the day")
    cash_sales: float = Field(..., ge=0, description="Total cash sales")
    cash_sales_count: int = Field(..., ge=0, description="Number of cash sales")
    total_expenses: float = Field(..., ge=0, description="Total expenses (APPROVED/PAID)")
    closing_balance: float = Field(..., description="Closing balance (can be negative)")
    payment_methods: List[PaymentMethodBreakdown] = Field(
        default_factory=list,
        description="Breakdown by payment method"
    )


# ================================
# WEEKLY CASH REGISTER
# ================================
class WeeklyCashRegister(BaseModel):
    """Weekly cash register summary"""
    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "period": "weekly",
                "week_start": "2026-05-11",
                "week_end": "2026-05-17",
                "opening_balance": 10000.00,
                "total_cash_sales": 38500.00,
                "total_cash_sales_count": 315,
                "total_expenses": 8400.00,
                "closing_balance": 40100.00
            }
        }
    )
    
    period: str = Field(default="weekly", description="Period type")
    week_start: date = Field(..., description="Start of the week (Monday)")
    week_end: date = Field(..., description="End of the week (Sunday)")
    opening_balance: float = Field(..., ge=0, description="Opening balance")
    total_cash_sales: float = Field(..., ge=0, description="Total cash sales for the week")
    total_cash_sales_count: int = Field(..., ge=0, description="Total number of cash sales")
    total_expenses: float = Field(..., ge=0, description="Total expenses for the week")
    closing_balance: float = Field(..., description="Closing balance")
    daily_breakdown: List[DailyCashRegister] = Field(
        default_factory=list,
        description="Daily breakdown for each day of the week"
    )


# ================================
# MONTHLY CASH REGISTER
# ================================
class MonthlyCashRegister(BaseModel):
    """Monthly cash register summary"""
    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "period": "monthly",
                "year": 2026,
                "month": 5,
                "month_start": "2026-05-01",
                "month_end": "2026-05-31",
                "opening_balance": 10000.00,
                "total_cash_sales": 165000.00,
                "total_cash_sales_count": 1350,
                "total_expenses": 35000.00,
                "closing_balance": 140000.00
            }
        }
    )
    
    period: str = Field(default="monthly", description="Period type")
    year: int = Field(..., ge=2000, le=2099, description="Year")
    month: int = Field(..., ge=1, le=12, description="Month (1-12)")
    month_start: date = Field(..., description="Start of the month")
    month_end: date = Field(..., description="End of the month")
    opening_balance: float = Field(..., ge=0, description="Opening balance")
    total_cash_sales: float = Field(..., ge=0, description="Total cash sales for the month")
    total_cash_sales_count: int = Field(..., ge=0, description="Total number of cash sales")
    total_expenses: float = Field(..., ge=0, description="Total expenses for the month")
    closing_balance: float = Field(..., description="Closing balance")
    expense_summary: Optional[dict] = Field(
        default=None,
        description="Expense summary breakdown by category and status"
    )


# ================================
# CASH REGISTER BALANCE
# ================================
class CashRegisterBalance(BaseModel):
    """Cash register balance calculation"""
    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "pos_id": 1,
                "pos_balance": 10000.00,
                "available_cash": 45000.00,
                "pos_expenses": 8000.00,
                "cash_register_balance": 47000.00,
                "period": {
                    "start_date": "2026-05-01",
                    "end_date": "2026-05-12"
                }
            }
        }
    )
    
    pos_id: int = Field(..., ge=1, description="POS ID")
    pos_balance: float = Field(..., description="Current POS balance")
    available_cash: float = Field(..., ge=0, description="Available cash from CASH sales")
    pos_expenses: float = Field(..., ge=0, description="POS expenses (APPROVED/PAID)")
    cash_register_balance: float = Field(
        ...,
        description="Final cash register balance = POS Balance + Available Cash - POS Expenses"
    )
    period: dict = Field(
        ...,
        description="Period information (start_date, end_date)"
    )


# ================================
# PERIOD INFORMATION
# ================================
class PeriodInfo(BaseModel):
    """Period information"""
    model_config = ConfigDict(from_attributes=True)
    
    start_date: date | None = Field(None, description="Start date of the period")
    end_date: date | None = Field(None, description="End date of the period")


# ================================
# CASH SALES DETAIL
# ================================
class CashSaleDetail(BaseModel):
    """Detailed cash sale information"""
    model_config = ConfigDict(from_attributes=True)
    
    id: int = Field(..., ge=1, description="Sale ID")
    amount: float = Field(..., ge=0, description="Sale amount")
    time: datetime = Field(..., description="Transaction time")
    customer_id: int | None = Field(None, ge=1, description="Customer ID")
    operator: int = Field(..., ge=1, description="Operator/POS User ID")


# ================================
# EXPENSE DETAIL
# ================================
class ExpenseDetail(BaseModel):
    """Detailed expense information"""
    model_config = ConfigDict(from_attributes=True)
    
    id: int = Field(..., ge=1, description="Expense ID")
    reference: str = Field(..., min_length=1, description="Expense reference number")
    amount: float = Field(..., ge=0, description="Expense amount")
    category: str = Field(..., min_length=1, description="Expense category")
    status: str = Field(..., description="Expense status (DRAFT, APPROVED, PAID, REJECTED)")


# ================================
# CASH REGISTER RECONCILIATION
# ================================
class CashRegisterReconciliation(BaseModel):
    """Detailed cash register reconciliation"""
    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "date": "2026-05-12",
                "summary": {
                    "date": "2026-05-12",
                    "opening_balance": 10000.00,
                    "cash_sales": 5500.50,
                    "cash_sales_count": 45,
                    "total_expenses": 1200.00,
                    "closing_balance": 14300.50
                },
                "cash_sales_detail": [
                    {
                        "id": 1001,
                        "amount": 125.50,
                        "time": "2026-05-12T09:30:00Z",
                        "customer_id": 5,
                        "operator": 2
                    }
                ],
                "expenses_detail": [
                    {
                        "id": 1,
                        "reference": "EXP-0001-2605-0001",
                        "amount": 1200.00,
                        "category": "maintenance",
                        "status": "approved"
                    }
                ]
            }
        }
    )
    
    reconciliation_date: date = Field(..., alias="date",  description="Reconciliation date")
    summary: DailyCashRegister = Field(..., description="Daily summary")
    cash_sales_detail: List[CashSaleDetail] = Field(
        default_factory=list,
        description="Detailed cash sales"
    )
    expenses_detail: List[ExpenseDetail] = Field(
        default_factory=list,
        description="Detailed expenses"
    )


# ================================
# CASH REGISTER COMPARISON
# ================================
class CashRegisterComparison(BaseModel):
    """Cash register comparison across periods"""
    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "period_type": "daily",
                "start_date": "2026-05-01",
                "end_date": "2026-05-12",
                "data": [
                    {
                        "date": "2026-05-01",
                        "opening_balance": 10000.00,
                        "total_cash_sales": 5000.00,
                        "total_cash_sales_count": 42,
                        "total_expenses": 800.00,
                        "closing_balance": 14200.00
                    }
                ]
            }
        }
    )
    
    period_type: str = Field(..., pattern="^(daily|monthly)$", description="Period type: 'daily' or 'monthly'")
    start_date: date = Field(..., description="Start date of comparison range")
    end_date: date = Field(..., description="End date of comparison range")
    data: List[dict] = Field(
        default_factory=list,
        description="Comparison data for each period"
    )


# ================================
# REQUEST QUERY SCHEMAS
# ================================
class CashRegisterDailyQuery(BaseModel):
    """Query for daily cash register"""
    model_config = ConfigDict(from_attributes=True)
    
    report_date: date | None = Field(None, description="Specific date for report (defaults to today)")


class CashRegisterWeeklyQuery(BaseModel):
    """Query for weekly cash register"""
    model_config = ConfigDict(from_attributes=True)
    
    week_start: date | None = Field(None, description="Start of the week (Monday)")


class CashRegisterMonthlyQuery(BaseModel):
    """Query for monthly cash register"""
    model_config = ConfigDict(from_attributes=True)
    
    year: int = Field(..., ge=2000, le=2099, description="Year")
    month: int = Field(..., ge=1, le=12, description="Month (1-12)")


class CashRegisterBalanceQuery(BaseModel):
    """Query for cash register balance"""
    model_config = ConfigDict(from_attributes=True)
    
    start_date: date | None = Field(None, description="Start date of the period")
    end_date: date | None = Field(None, description="End date of the period")


class CashRegisterComparisonQuery(BaseModel):
    """Query for comparison endpoint"""
    model_config = ConfigDict(from_attributes=True)
    
    period_type: str = Field(
        default="daily",
        pattern="^(daily|monthly)$",
        description="Period type: 'daily' or 'monthly'"
    )
    start_date: date | None = Field(None, description="Start date")
    end_date: date | None = Field(None, description="End date")