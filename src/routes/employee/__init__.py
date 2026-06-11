# src/routes/employee/__init__.py
from .employees import employee_router
from .contracts import contract_router
from .attendances import attendance_router
from .leaves import leave_router
from .salaries import salary_router

routers = [
    contract_router,
    attendance_router,
    leave_router,
    salary_router,
    employee_router,  # LAST — has /{employee_id} root wildcard
]