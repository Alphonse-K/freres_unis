from fastapi import FastAPI
from .auth import auth_router
from .system_user import user_router
from .clients import client_router
from .pos import pos_router
from .address import address_router
from .id_types_routes import id_type_router
from .pos_inventory import inventory_router
from .pos_sales import sales_router
from .pos_expenses import expenses_router
from .procurements import procurement_router
from .provider import provider_router
from .catalog_route import product_router
from .role import role_router
from .tax import tax_router
from .company import company_router
from .employee import routers as employee_routers
from .partner_company import partner_company_router
from .notifications import notification_router
from .cash_register import cash_register_route
from .accounts import router as accounts_router
from . import files

API_PREFIX = "/api/v1"

def register_routers(app: FastAPI):
    app.include_router(auth_router, prefix=API_PREFIX)
    app.include_router(user_router, prefix=API_PREFIX)
    app.include_router(client_router, prefix=API_PREFIX)
    app.include_router(pos_router, prefix=API_PREFIX)
    app.include_router(cash_register_route, prefix=API_PREFIX)
    app.include_router(product_router, prefix=API_PREFIX)
    app.include_router(inventory_router, prefix=API_PREFIX)
    app.include_router(tax_router, prefix=API_PREFIX)
    app.include_router(sales_router, prefix=API_PREFIX)
    app.include_router(expenses_router, prefix=API_PREFIX)
    app.include_router(procurement_router, prefix=API_PREFIX)
    app.include_router(provider_router, prefix=API_PREFIX)
    app.include_router(address_router, prefix=API_PREFIX)
    app.include_router(id_type_router, prefix=API_PREFIX)
    app.include_router(role_router, prefix=API_PREFIX)
    app.include_router(files.router, prefix=API_PREFIX)
    app.include_router(company_router, prefix=API_PREFIX)
    app.include_router(partner_company_router, prefix=API_PREFIX)
    app.include_router(notification_router, prefix=API_PREFIX)
    app.include_router(accounts_router, prefix=API_PREFIX)
    for router in employee_routers:
        app.include_router(router, prefix=API_PREFIX)