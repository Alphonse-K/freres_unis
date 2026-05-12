from datetime import datetime, date, timedelta, timezone
from decimal import Decimal
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
import logging

from src.models.pos import Sale, SaleReturn, SaleStatus, PaymentMethod, POS, POSExpense, POSExpenseStatus
from src.services.pos_expenses import ExpenseService

logger = logging.getLogger(__name__)


class CashRegisterService:
    """
    Cash Register Service for POS
    Formula: Cash Register Balance = POS Balance + Available Cash (CASH sales only) - POS Expenses (APPROVED/PAID only)
    Available Cash = Sum of all completed CASH sales in the period
    POS Expenses = Sum of all APPROVED or PAID expenses in the period
    """

    @staticmethod
    def get_pos_balance(db: Session, pos_id: int) -> Decimal:
        """Get current POS balance from database"""
        pos = db.query(POS).filter(POS.id == pos_id).first()
        if not pos:
            return Decimal("0")
        return pos.balance or Decimal("0")

    @staticmethod
    def calculate_available_cash(
        db: Session,
        pos_id: int,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
    ) -> Decimal:
        """
        Calculate available cash from CASH SALES ONLY
        Available Cash = Sum of all completed CASH sales in the period
        """
        query = db.query(func.coalesce(func.sum(Sale.total_amount), 0)).filter(
            Sale.pos_id == pos_id,
            Sale.status == SaleStatus.COMPLETED,
            Sale.payment_mode == PaymentMethod.CASH  # Only CASH payments
        )

        if start_date:
            query = query.filter(Sale.transaction_date >= start_date)

        if end_date:
            query = query.filter(Sale.transaction_date <= end_date)

        total_cash_sales = query.scalar() or Decimal("0")
        return Decimal(str(total_cash_sales))

    @staticmethod
    def calculate_pos_expenses(
        db: Session,
        pos_id: int,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
    ) -> Decimal:
        """
        Calculate total POS expenses in the period (APPROVED or PAID only)
        Uses the existing ExpenseService list_expenses method
        """
        expenses, total = ExpenseService.list_expenses(
            db=db,
            pos_id=pos_id,
            status=POSExpenseStatus.APPROVED,  # Only approved expenses
            start_date=start_date,
            end_date=end_date,
            skip=0,
            limit=10000  # Get all approved expenses
        )
        
        approved_total = sum(expense.amount for expense in expenses)
        
        # Also get PAID expenses
        paid_expenses, _ = ExpenseService.list_expenses(
            db=db,
            pos_id=pos_id,
            status=POSExpenseStatus.PAID,
            start_date=start_date,
            end_date=end_date,
            skip=0,
            limit=10000
        )
        
        paid_total = sum(expense.amount for expense in paid_expenses)
        
        total_expenses = approved_total + paid_total
        return Decimal(str(total_expenses))

    @staticmethod
    def calculate_cash_register_balance(
        db: Session,
        pos_id: int,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
    ) -> Dict[str, Any]:
        """
        Calculate Cash Register Balance
        Formula: POS Balance + Available Cash (CASH sales) - POS Expenses (APPROVED/PAID)
        """
        pos_balance = CashRegisterService.get_pos_balance(db, pos_id)
        available_cash = CashRegisterService.calculate_available_cash(
            db, pos_id, start_date, end_date
        )
        pos_expenses = CashRegisterService.calculate_pos_expenses(
            db, pos_id, start_date, end_date
        )

        cash_register_balance = pos_balance + available_cash - pos_expenses

        return {
            "pos_id": pos_id,
            "pos_balance": float(pos_balance),
            "available_cash": float(available_cash),
            "pos_expenses": float(pos_expenses),
            "cash_register_balance": float(cash_register_balance),
            "period": {
                "start_date": start_date,
                "end_date": end_date
            }
        }

    @staticmethod
    def get_daily_cash_register(
        db: Session,
        pos_id: int,
        report_date: Optional[date] = None
    ) -> Dict[str, Any]:
        """Get daily cash register summary"""
        report_date = report_date or date.today()
        
        start_datetime = datetime.combine(report_date, datetime.min.time()).replace(tzinfo=timezone.utc)
        end_datetime = datetime.combine(report_date, datetime.max.time()).replace(tzinfo=timezone.utc)

        # Get CASH sales for the day
        daily_cash_sales = db.query(func.coalesce(func.sum(Sale.total_amount), 0)).filter(
            Sale.pos_id == pos_id,
            Sale.status == SaleStatus.COMPLETED,
            Sale.payment_mode == PaymentMethod.CASH,
            Sale.transaction_date >= start_datetime,
            Sale.transaction_date <= end_datetime
        ).scalar() or Decimal("0")

        # Get daily expenses (APPROVED or PAID only)
        daily_expenses = CashRegisterService.calculate_pos_expenses(
            db, pos_id, report_date, report_date
        )

        # Get POS balance
        pos_balance = CashRegisterService.get_pos_balance(db, pos_id)

        # Calculate daily balance
        daily_balance = pos_balance + Decimal(str(daily_cash_sales)) - Decimal(str(daily_expenses))

        # Get payment method breakdown (all payment methods, not just cash)
        payment_breakdown = db.query(
            Sale.payment_mode,
            func.count(Sale.id).label('count'),
            func.coalesce(func.sum(Sale.total_amount), 0).label('total')
        ).filter(
            Sale.pos_id == pos_id,
            Sale.status == SaleStatus.COMPLETED,
            Sale.transaction_date >= start_datetime,
            Sale.transaction_date <= end_datetime
        ).group_by(Sale.payment_mode).all()

        # Get cash sales count
        cash_sales_count = db.query(func.count(Sale.id)).filter(
            Sale.pos_id == pos_id,
            Sale.status == SaleStatus.COMPLETED,
            Sale.payment_mode == PaymentMethod.CASH,
            Sale.transaction_date >= start_datetime,
            Sale.transaction_date <= end_datetime
        ).scalar()

        return {
            "date": report_date,
            "opening_balance": float(pos_balance),
            "cash_sales": float(daily_cash_sales),
            "cash_sales_count": cash_sales_count,
            "total_expenses": float(daily_expenses),
            "closing_balance": float(daily_balance),
            "payment_methods": [
                {
                    "method": method.value if method else "unknown",
                    "count": count,
                    "total": float(total)
                }
                for method, count, total in payment_breakdown
            ]
        }

    @staticmethod
    def get_weekly_cash_register(
        db: Session,
        pos_id: int,
        week_start: Optional[date] = None
    ) -> Dict[str, Any]:
        """Get weekly cash register summary"""
        if week_start is None:
            today = date.today()
            week_start = today - timedelta(days=today.weekday())

        week_end = week_start + timedelta(days=6)
        
        start_datetime = datetime.combine(week_start, datetime.min.time()).replace(tzinfo=timezone.utc)
        end_datetime = datetime.combine(week_end, datetime.max.time()).replace(tzinfo=timezone.utc)

        # Get opening balance
        opening_balance = CashRegisterService.get_pos_balance(db, pos_id)

        # Get CASH sales for the week
        weekly_cash_sales = db.query(func.coalesce(func.sum(Sale.total_amount), 0)).filter(
            Sale.pos_id == pos_id,
            Sale.status == SaleStatus.COMPLETED,
            Sale.payment_mode == PaymentMethod.CASH,
            Sale.transaction_date >= start_datetime,
            Sale.transaction_date <= end_datetime
        ).scalar() or Decimal("0")

        # Get expenses for the week
        weekly_expenses = CashRegisterService.calculate_pos_expenses(
            db, pos_id, week_start, week_end
        )

        closing_balance = opening_balance + Decimal(str(weekly_cash_sales)) - Decimal(str(weekly_expenses))

        # Daily breakdown
        daily_data = []
        current_date = week_start
        while current_date <= week_end:
            daily_summary = CashRegisterService.get_daily_cash_register(db, pos_id, current_date)
            daily_data.append(daily_summary)
            current_date += timedelta(days=1)

        # Cash sales count
        weekly_cash_count = db.query(func.count(Sale.id)).filter(
            Sale.pos_id == pos_id,
            Sale.status == SaleStatus.COMPLETED,
            Sale.payment_mode == PaymentMethod.CASH,
            Sale.transaction_date >= start_datetime,
            Sale.transaction_date <= end_datetime
        ).scalar()

        return {
            "period": "weekly",
            "week_start": week_start,
            "week_end": week_end,
            "opening_balance": float(opening_balance),
            "total_cash_sales": float(weekly_cash_sales),
            "total_cash_sales_count": weekly_cash_count,
            "total_expenses": float(weekly_expenses),
            "closing_balance": float(closing_balance),
            "daily_breakdown": daily_data
        }

    @staticmethod
    def get_monthly_cash_register(
        db: Session,
        pos_id: int,
        year: int,
        month: int
    ) -> Dict[str, Any]:
        """Get monthly cash register summary"""
        from calendar import monthrange

        days_in_month = monthrange(year, month)[1]
        month_start = date(year, month, 1)
        month_end = date(year, month, days_in_month)
        
        start_datetime = datetime.combine(month_start, datetime.min.time()).replace(tzinfo=timezone.utc)
        end_datetime = datetime.combine(month_end, datetime.max.time()).replace(tzinfo=timezone.utc)

        # Get opening balance
        opening_balance = CashRegisterService.get_pos_balance(db, pos_id)

        # Get CASH sales for the month
        monthly_cash_sales = db.query(func.coalesce(func.sum(Sale.total_amount), 0)).filter(
            Sale.pos_id == pos_id,
            Sale.status == SaleStatus.COMPLETED,
            Sale.payment_mode == PaymentMethod.CASH,
            Sale.transaction_date >= start_datetime,
            Sale.transaction_date <= end_datetime
        ).scalar() or Decimal("0")

        # Get expenses for the month
        monthly_expenses = CashRegisterService.calculate_pos_expenses(
            db, pos_id, month_start, month_end
        )

        closing_balance = opening_balance + Decimal(str(monthly_cash_sales)) - Decimal(str(monthly_expenses))

        # Get expense summary using existing ExpenseService
        expense_summary = ExpenseService.get_expenses_summary(
            db, pos_id, month_start, month_end
        )

        # Cash sales count
        monthly_cash_count = db.query(func.count(Sale.id)).filter(
            Sale.pos_id == pos_id,
            Sale.status == SaleStatus.COMPLETED,
            Sale.payment_mode == PaymentMethod.CASH,
            Sale.transaction_date >= start_datetime,
            Sale.transaction_date <= end_datetime
        ).scalar()

        return {
            "period": "monthly",
            "year": year,
            "month": month,
            "month_start": month_start,
            "month_end": month_end,
            "opening_balance": float(opening_balance),
            "total_cash_sales": float(monthly_cash_sales),
            "total_cash_sales_count": monthly_cash_count,
            "total_expenses": float(monthly_expenses),
            "closing_balance": float(closing_balance),
            "expense_summary": expense_summary
        }

    @staticmethod
    def get_cash_register_comparison(
        db: Session,
        pos_id: int,
        period_type: str = "daily",
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
    ) -> Dict[str, Any]:
        """
        Compare cash register balances across periods
        period_type: 'daily', 'weekly', 'monthly'
        """
        if period_type == "daily":
            end_date = end_date or date.today()
            start_date = start_date or (end_date - timedelta(days=30))

            comparisons = []
            current_date = start_date
            while current_date <= end_date:
                summary = CashRegisterService.get_daily_cash_register(db, pos_id, current_date)
                comparisons.append(summary)
                current_date += timedelta(days=1)

            return {
                "period_type": "daily",
                "start_date": start_date,
                "end_date": end_date,
                "data": comparisons
            }

        elif period_type == "monthly":
            if not start_date or not end_date:
                today = date.today()
                start_date = date(today.year - 1, today.month, 1)
                end_date = today

            comparisons = []
            current_date = start_date
            while current_date <= end_date:
                summary = CashRegisterService.get_monthly_cash_register(
                    db, pos_id, current_date.year, current_date.month
                )
                comparisons.append(summary)
                
                # Move to next month
                if current_date.month == 12:
                    current_date = current_date.replace(year=current_date.year + 1, month=1)
                else:
                    current_date = current_date.replace(month=current_date.month + 1)

            return {
                "period_type": "monthly",
                "start_date": start_date,
                "end_date": end_date,
                "data": comparisons
            }

    @staticmethod
    def get_cash_register_reconciliation(
        db: Session,
        pos_id: int,
        report_date: Optional[date] = None
    ) -> Dict[str, Any]:
        """
        Get detailed cash register reconciliation for the day
        Shows all cash sales and expenses with details
        """
        report_date = report_date or date.today()
        
        start_datetime = datetime.combine(report_date, datetime.min.time()).replace(tzinfo=timezone.utc)
        end_datetime = datetime.combine(report_date, datetime.max.time()).replace(tzinfo=timezone.utc)

        # Get daily summary
        daily_summary = CashRegisterService.get_daily_cash_register(db, pos_id, report_date)

        # Get detailed cash sales
        cash_sales = db.query(Sale).filter(
            Sale.pos_id == pos_id,
            Sale.status == SaleStatus.COMPLETED,
            Sale.payment_mode == PaymentMethod.CASH,
            Sale.transaction_date >= start_datetime,
            Sale.transaction_date <= end_datetime
        ).order_by(Sale.transaction_date).all()

        # Get detailed expenses
        expenses, _ = ExpenseService.list_expenses(
            db=db,
            pos_id=pos_id,
            start_date=report_date,
            end_date=report_date,
            skip=0,
            limit=10000
        )

        return {
            "date": report_date,
            "summary": daily_summary,
            "cash_sales_detail": [
                {
                    "id": sale.id,
                    "amount": float(sale.total_amount),
                    "time": sale.transaction_date,
                    "customer_id": sale.customer_id,
                    "operator": sale.created_by_id
                }
                for sale in cash_sales
            ],
            "expenses_detail": [
                {
                    "id": expense.id,
                    "reference": expense.reference,
                    "amount": float(expense.amount),
                    "category": expense.category.value,
                    "status": expense.status.value
                }
                for expense in expenses
            ]
        }