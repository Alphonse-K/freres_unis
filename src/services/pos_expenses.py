# src/services/expense_service.py
from datetime import datetime, date, timedelta, timezone
from decimal import Decimal
from typing import List, Optional, Dict, Any, Tuple
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, desc, asc, and_, or_, extract
import logging

from src.models.pos import POSExpense, POSUser, POS, POSExpenseCategory, POSExpenseStatus
from src.schemas.pos import (
    POSExpenseCreate, POSExpenseUpdate, POSExpenseFilter
)
from src.services.pos import POSService, POSUserService

logger = logging.getLogger(__name__)


# ================================
# CUSTOM EXCEPTIONS
# ================================
class ExpenseException(Exception):
    """Base exception for expense operations"""
    def __init__(self, message: str, status_code: int = 400):
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)


class ExpenseNotFoundException(ExpenseException):
    """Raised when an expense is not found"""
    def __init__(self, message: str = "Expense not found"):
        super().__init__(message, status_code=404)


class ExpenseValidationException(ExpenseException):
    """Raised when expense validation fails"""
    def __init__(self, message: str = "Expense validation failed"):
        super().__init__(message, status_code=400)


class ExpenseBusinessRuleException(ExpenseException):
    """Raised when an expense business rule is violated"""
    def __init__(self, message: str = "Expense business rule violation"):
        super().__init__(message, status_code=422)


# ================================
# EXPENSE SERVICE
# ================================
class ExpenseService:
    
    # ================================
    # EXPENSE CRUD OPERATIONS
    # ================================
    
    @staticmethod
    def generate_expense_reference(db: Session, pos_id: int) -> str:
        """Generate unique expense reference number"""
        today = datetime.utcnow().date()
        year = today.year % 100
        month = today.month
        
        # Count expenses for this POS this month
        count = db.query(POSExpense).filter(
            POSExpense.pos_id == pos_id,
            extract('year', POSExpense.created_at) == today.year,
            extract('month', POSExpense.created_at) == today.month
        ).count()
        
        next_number = count + 1
        return f"EXP-{pos_id:04d}-{year:02d}{month:02d}-{next_number:04d}"
    
    @staticmethod
    def create_expense(db: Session, data: POSExpenseCreate) -> POSExpense:
        """Create a new expense"""
        try:
            # Verify POS exists
            pos = POSService.get_pos(db, data.pos_id)
            if not pos:
                raise ExpenseNotFoundException(f"POS {data.pos_id} not found")
            
            # Verify created_by user exists
            created_by = POSUserService.get_pos_user_by_id(db, data.created_by_id)
            if not created_by:
                raise ExpenseNotFoundException(f"User {data.created_by_id} not found")
            
            # Verify approved_by user exists if provided
            approved_by = None
            if data.approved_by_id:
                approved_by = POSUserService.get_pos_user_by_id(db, data.approved_by_id)
                if not approved_by:
                    raise ExpenseNotFoundException(f"User {data.approved_by_id} not found")
            
            # Generate reference number
            reference = ExpenseService.generate_expense_reference(db, data.pos_id)
            
            # Check for duplicate reference (shouldn't happen, but just in case)
            existing = db.query(POSExpense).filter(POSExpense.reference == reference).first()
            if existing:
                # Regenerate if duplicate (extremely rare)
                reference = ExpenseService.generate_expense_reference(db, data.pos_id)
            
            # Create expense
            expense = POSExpense(
                reference=reference,
                pos_id=data.pos_id,
                category=data.category,
                amount=data.amount,
                description=data.description,
                expense_date=data.expense_date or datetime.now(timezone.utc),
                status=data.status or POSExpenseStatus.DRAFT,
                created_by_id=data.created_by_id,
                approved_by_id=data.approved_by_id,
                created_at=datetime.now(timezone.utc)
            )
            
            db.add(expense)
            db.commit()
            db.refresh(expense)
            
            logger.info(f"Expense created: {expense.reference} for POS {data.pos_id}")
            return expense
            
        except ExpenseException:
            db.rollback()
            raise
        except Exception as e:
            db.rollback()
            logger.error(f"Error creating expense: {str(e)}")
            raise ExpenseValidationException(f"Error creating expense: {str(e)}")
    
    @staticmethod
    def get_expense(db: Session, expense_id: int) -> POSExpense:
        """Get expense by ID with all relationships"""
        expense = db.query(POSExpense).options(
            joinedload(POSExpense.pos),
            joinedload(POSExpense.created_by),
            joinedload(POSExpense.approved_by)
        ).filter(
            POSExpense.id == expense_id
        ).first()
        
        if not expense:
            raise ExpenseNotFoundException(f"Expense {expense_id} not found")
        
        return expense
    
    @staticmethod
    def get_expense_by_reference(db: Session, reference: str) -> POSExpense:
        """Get expense by reference number"""
        expense = db.query(POSExpense).options(
            joinedload(POSExpense.pos),
            joinedload(POSExpense.created_by),
            joinedload(POSExpense.approved_by)
        ).filter(
            POSExpense.reference == reference
        ).first()
        
        if not expense:
            raise ExpenseNotFoundException(f"Expense with reference {reference} not found")
        
        return expense
    
    @staticmethod
    def update_expense(db: Session, expense_id: int, data: POSExpenseUpdate) -> POSExpense:
        """Update expense information"""
        expense = ExpenseService.get_expense(db, expense_id)
        
        # Check if expense can be modified
        if expense.status in [POSExpenseStatus.APPROVED, POSExpenseStatus.PAID]:
            raise ExpenseBusinessRuleException(f"Cannot update expense with status {expense.status.value}")
        
        try:
            # Update fields
            if data.category is not None:
                expense.category = data.category
            
            if data.amount is not None:
                if data.amount <= Decimal('0'):
                    raise ExpenseValidationException("Amount must be positive")
                expense.amount = data.amount
            
            if data.description is not None:
                expense.description = data.description
            
            if data.expense_date is not None:
                expense.expense_date = data.expense_date
            
            if data.status is not None:
                # Validate status transition
                if data.status == POSExpenseStatus.APPROVED and not expense.approved_by_id:
                    raise ExpenseValidationException("Cannot approve expense without approver")
                
                expense.status = data.status
            
            if data.approved_by_id is not None:
                # Verify approver exists
                approver = POSUserService.get_pos_user_by_id(db, data.approved_by_id)
                if not approver:
                    raise ExpenseNotFoundException(f"Approver user {data.approved_by_id} not found")
                expense.approved_by_id = data.approved_by_id
            
            db.commit()
            db.refresh(expense)
            
            logger.info(f"Expense updated: {expense_id}")
            return expense
            
        except ExpenseException:
            db.rollback()
            raise
        except Exception as e:
            db.rollback()
            logger.error(f"Error updating expense {expense_id}: {str(e)}")
            raise ExpenseValidationException(f"Error updating expense: {str(e)}")
    
    @staticmethod
    def delete_expense(db: Session, expense_id: int) -> bool:
        """Delete an expense (only if in draft status)"""
        expense = ExpenseService.get_expense(db, expense_id)
        
        if expense.status != POSExpenseStatus.DRAFT:
            raise ExpenseBusinessRuleException("Can only delete expenses in draft status")
        
        try:
            db.delete(expense)
            db.commit()
            
            logger.info(f"Expense deleted: {expense_id}")
            return True
            
        except Exception as e:
            db.rollback()
            logger.error(f"Error deleting expense {expense_id}: {str(e)}")
            raise ExpenseValidationException(f"Error deleting expense: {str(e)}")
    
    @staticmethod
    def approve_expense(db: Session, expense_id: int, approver_id: int) -> POSExpense:
        """Approve an expense"""
        expense = ExpenseService.get_expense(db, expense_id)
        
        if expense.status != POSExpenseStatus.DRAFT:
            raise ExpenseBusinessRuleException("Can only approve expenses in draft status")
        
        # Verify approver exists
        approver = POSUserService.get_pos_user_by_id(db, approver_id)
        if not approver:
            raise ExpenseNotFoundException(f"Approver user {approver_id} not found")
        
        try:
            expense.status = POSExpenseStatus.APPROVED
            expense.approved_by_id = approver_id
            
            db.commit()
            db.refresh(expense)
            
            logger.info(f"Expense approved: {expense_id} by user {approver_id}")
            return expense
            
        except Exception as e:
            db.rollback()
            logger.error(f"Error approving expense {expense_id}: {str(e)}")
            raise ExpenseValidationException(f"Error approving expense: {str(e)}")
    
    @staticmethod
    def reject_expense(db: Session, expense_id: int, reason: str = None) -> POSExpense:
        """Reject an expense"""
        expense = ExpenseService.get_expense(db, expense_id)
        
        if expense.status != POSExpenseStatus.DRAFT:
            raise ExpenseBusinessRuleException("Can only reject expenses in draft status")
        
        try:
            expense.status = POSExpenseStatus.REJECTED
            if reason:
                expense.description = f"{expense.description or ''}\nRejected: {reason}".strip()
            
            db.commit()
            db.refresh(expense)
            
            logger.info(f"Expense rejected: {expense_id}")
            return expense
            
        except Exception as e:
            db.rollback()
            logger.error(f"Error rejecting expense {expense_id}: {str(e)}")
            raise ExpenseValidationException(f"Error rejecting expense: {str(e)}")
    
    @staticmethod
    def mark_expense_as_paid(db: Session, expense_id: int) -> POSExpense:
        """Mark an expense as paid"""
        expense = ExpenseService.get_expense(db, expense_id)
        
        if expense.status != POSExpenseStatus.APPROVED:
            raise ExpenseBusinessRuleException("Can only mark approved expenses as paid")
        
        try:
            expense.status = POSExpenseStatus.PAID
            
            db.commit()
            db.refresh(expense)
            
            logger.info(f"Expense marked as paid: {expense_id}")
            return expense
            
        except Exception as e:
            db.rollback()
            logger.error(f"Error marking expense as paid: {expense_id}: {str(e)}")
            raise ExpenseValidationException(f"Error marking expense as paid: {str(e)}")
    
    @staticmethod
    def list_expenses(
        db: Session,
        pos_id: Optional[int] = None,
        category: Optional[POSExpenseCategory] = None,
        status: Optional[POSExpenseStatus] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        created_by_id: Optional[int] = None,
        approved_by_id: Optional[int] = None,
        skip: int = 0,
        limit: int = 50
    ) -> Tuple[List[POSExpense], int]:
        """List expenses with filtering"""
        query = db.query(POSExpense).options(
            joinedload(POSExpense.pos),
            joinedload(POSExpense.created_by)
        )
        
        # Apply filters
        if pos_id:
            query = query.filter(POSExpense.pos_id == pos_id)
        
        if category:
            query = query.filter(POSExpense.category == category)
        
        if status:
            query = query.filter(POSExpense.status == status)
        
        if start_date:
            query = query.filter(POSExpense.expense_date >= start_date)
        
        if end_date:
            query = query.filter(POSExpense.expense_date <= end_date)
        
        if created_by_id:
            query = query.filter(POSExpense.created_by_id == created_by_id)
        
        if approved_by_id:
            query = query.filter(POSExpense.approved_by_id == approved_by_id)
        
        # Get total count
        total = query.count()
        
        # Apply pagination
        expenses = query.order_by(desc(POSExpense.expense_date)).offset(skip).limit(limit).all()
        
        return expenses, total
    
    # ================================
    # EXPENSE REPORTS & ANALYTICS
    # ================================
    
    @staticmethod
    def get_expenses_summary(
        db: Session,
        pos_id: Optional[int] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
    ) -> Dict[str, Any]:
        from sqlalchemy import func, desc
        from src.models.pos import POSExpense

        base_query = db.query(POSExpense)

        if pos_id:
            base_query = base_query.filter(POSExpense.pos_id == pos_id)

        if start_date:
            base_query = base_query.filter(POSExpense.expense_date >= start_date)

        if end_date:
            base_query = base_query.filter(POSExpense.expense_date <= end_date)

        # Total expenses count
        total_expenses = base_query.count()

        # Totals by status
        by_status = (
            db.query(
                POSExpense.status,
                func.count(POSExpense.id),
                func.coalesce(func.sum(POSExpense.amount), 0)
            )
            .filter(POSExpense.pos_id == pos_id if pos_id else True)
            .filter(POSExpense.expense_date >= start_date if start_date else True)
            .filter(POSExpense.expense_date <= end_date if end_date else True)
            .group_by(POSExpense.status)
            .all()
        )

        # Totals by category
        by_category = (
            db.query(
                POSExpense.category,
                func.count(POSExpense.id),
                func.coalesce(func.sum(POSExpense.amount), 0)
            )
            .filter(POSExpense.pos_id == pos_id if pos_id else True)
            .filter(POSExpense.expense_date >= start_date if start_date else True)
            .filter(POSExpense.expense_date <= end_date if end_date else True)
            .group_by(POSExpense.category)
            .all()
        )

        # Recent expenses
        recent_expenses = (
            base_query
            .order_by(desc(POSExpense.expense_date))
            .limit(5)
            .all()
        )

        # Total amount
        total_amount = sum(total for _, _, total in by_status)

        return {
            "total_expenses": total_expenses,
            "total_amount": float(total_amount),
            "by_status": [
                {
                    "status": status.value,
                    "count": count,
                    "total": float(total)
                }
                for status, count, total in by_status
            ],
            "by_category": [
                {
                    "category": category.value,
                    "count": count,
                    "total": float(total),
                    "percentage": float((total / total_amount) * 100) if total_amount > 0 else 0
                }
                for category, count, total in by_category
            ],
            "recent_expenses": [
                {
                    "id": expense.id,
                    "reference": expense.reference,
                    "date": expense.expense_date,
                    "amount": float(expense.amount),
                    "category": expense.category.value,
                    "status": expense.status.value
                }
                for expense in recent_expenses
            ]
        }
    
    @staticmethod
    def get_expenses_trend(
        db: Session,
        pos_id: Optional[int] = None,
        days: int = 30
    ) -> List[Dict[str, Any]]:
        """Get expenses trend over time"""
        end_date = datetime.utcnow().date()
        start_date = end_date - timedelta(days=days - 1)
        
        # Generate date range
        date_range = []
        current_date = start_date
        while current_date <= end_date:
            date_range.append(current_date)
            current_date += timedelta(days=1)
        
        # Get daily expenses
        daily_expenses = db.session.execute(
            db.query(
                func.date(POSExpense.expense_date).label('expense_date'),
                func.count(POSExpense.id).label('expense_count'),
                func.sum(POSExpense.amount).label('daily_total')
            ).filter(
                POSExpense.expense_date >= start_date,
                POSExpense.expense_date <= end_date,
                POSExpense.pos_id == pos_id if pos_id else True
            ).group_by(func.date(POSExpense.expense_date))
            .order_by(func.date(POSExpense.expense_date))
        ).all()
        
        # Create trend data
        trend_map = {row.expense_date: row for row in daily_expenses}
        
        trend_data = []
        for date in date_range:
            expense_data = trend_map.get(date)
            trend_data.append({
                "date": date,
                "expenses_count": expense_data.expense_count if expense_data else 0,
                "total_amount": float(expense_data.daily_total or Decimal('0')) if expense_data else 0.0
            })
        
        return trend_data
    
    @staticmethod
    def get_category_breakdown(
        db: Session,
        pos_id: Optional[int] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
    ) -> Dict[str, Any]:
        """Get detailed expense breakdown by category"""
        # Get expenses by category
        category_data = db.session.execute(
            db.query(
                POSExpense.category,
                func.count(POSExpense.id).label('count'),
                func.sum(POSExpense.amount).label('total'),
                func.avg(POSExpense.amount).label('average')
            ).filter(
                POSExpense.pos_id == pos_id if pos_id else True,
                POSExpense.expense_date >= start_date if start_date else True,
                POSExpense.expense_date <= end_date if end_date else True
            ).group_by(POSExpense.category)
            .order_by(desc(func.sum(POSExpense.amount)))
        ).all()
        
        # Calculate totals
        total_expenses = sum(row.count for row in category_data)
        total_amount = sum(row.total or Decimal('0') for row in category_data)
        
        # Prepare breakdown
        breakdown = []
        for category, count, total, average in category_data:
            percentage = float((total or Decimal('0')) / total_amount * 100) if total_amount > 0 else 0
            breakdown.append({
                "category": category.value,
                "count": count,
                "total": float(total or Decimal('0')),
                "average": float(average or Decimal('0')),
                "percentage": percentage
            })
        
        return {
            "total_expenses": total_expenses,
            "total_amount": float(total_amount),
            "breakdown": breakdown,
            "top_category": breakdown[0]["category"] if breakdown else None,
            "period": {
                "start_date": start_date,
                "end_date": end_date
            }
        }
    
    @staticmethod
    def get_monthly_expense_report(
        db: Session,
        pos_id: Optional[int] = None,
        year: Optional[int] = None,
        month: Optional[int] = None
    ) -> Dict[str, Any]:
        """Get monthly expense report"""
        current_date = datetime.now(timezone.utc)
        report_year = year or current_date.year
        report_month = month or current_date.month
        
        # Calculate date range for the month
        start_date = date(report_year, report_month, 1)
        if report_month == 12:
            end_date = date(report_year + 1, 1, 1) - timedelta(days=1)
        else:
            end_date = date(report_year, report_month + 1, 1) - timedelta(days=1)
        
        # Get expenses for the month
        expenses = db.query(POSExpense).filter(
            POSExpense.expense_date >= start_date,
            POSExpense.expense_date <= end_date,
            POSExpense.pos_id == pos_id if pos_id else True
        ).order_by(POSExpense.expense_date).all()
        
        # Calculate totals
        total_expenses = len(expenses)
        total_amount = sum(expense.amount for expense in expenses)
        
        # Group by week
        weekly_data = {}
        for expense in expenses:
            week_num = expense.expense_date.isocalendar()[1]
            if week_num not in weekly_data:
                weekly_data[week_num] = {
                    "count": 0,
                    "total": Decimal('0'),
                    "expenses": []
                }
            
            weekly_data[week_num]["count"] += 1
            weekly_data[week_num]["total"] += expense.amount
            weekly_data[week_num]["expenses"].append({
                "id": expense.id,
                "reference": expense.reference,
                "date": expense.expense_date,
                "amount": float(expense.amount),
                "category": expense.category.value,
                "status": expense.status.value
            })
        
        # Convert weekly data to list
        weekly_breakdown = []
        for week_num, data in sorted(weekly_data.items()):
            weekly_breakdown.append({
                "week": week_num,
                "count": data["count"],
                "total": float(data["total"]),
                "expenses": data["expenses"][:5]  # Limit to 5 expenses per week for brevity
            })
        
        return {
            "month": report_month,
            "year": report_year,
            "start_date": start_date,
            "end_date": end_date,
            "total_expenses": total_expenses,
            "total_amount": float(total_amount),
            "weekly_breakdown": weekly_breakdown,
            "daily_average": float(total_amount / (end_date - start_date).days) if (end_date - start_date).days > 0 else 0.0
        }
    
    @staticmethod
    def compare_with_previous_period(
        db: Session,
        pos_id: Optional[int] = None,
        days: int = 30
    ) -> Dict[str, Any]:
        """Compare expenses with previous period"""
        end_date = datetime.now(timezone.utc).date()
        start_date = end_date - timedelta(days=days - 1)
        
        previous_end_date = start_date - timedelta(days=1)
        previous_start_date = previous_end_date - timedelta(days=days - 1)
        
        # Get current period data
        current_expenses = db.query(POSExpense).filter(
            POSExpense.expense_date >= start_date,
            POSExpense.expense_date <= end_date,
            POSExpense.pos_id == pos_id if pos_id else True
        ).all()
        
        current_total = sum(expense.amount for expense in current_expenses)
        current_count = len(current_expenses)
        
        # Get previous period data
        previous_expenses = db.query(POSExpense).filter(
            POSExpense.expense_date >= previous_start_date,
            POSExpense.expense_date <= previous_end_date,
            POSExpense.pos_id == pos_id if pos_id else True
        ).all()
        
        previous_total = sum(expense.amount for expense in previous_expenses)
        previous_count = len(previous_expenses)
        
        # Calculate changes
        amount_change = current_total - previous_total
        count_change = current_count - previous_count
        
        # Calculate percentages
        amount_change_percentage = (amount_change / previous_total * 100) if previous_total > 0 else 0
        count_change_percentage = (count_change / previous_count * 100) if previous_count > 0 else 0
        
        return {
            "current_period": {
                "start_date": start_date,
                "end_date": end_date,
                "total_amount": float(current_total),
                "expense_count": current_count
            },
            "previous_period": {
                "start_date": previous_start_date,
                "end_date": previous_end_date,
                "total_amount": float(previous_total),
                "expense_count": previous_count
            },
            "comparison": {
                "amount_change": float(amount_change),
                "amount_change_percentage": float(amount_change_percentage),
                "count_change": count_change,
                "count_change_percentage": float(count_change_percentage),
                "trend": "increase" if amount_change > 0 else "decrease" if amount_change < 0 else "stable"
            }
        }