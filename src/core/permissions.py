# src/core/permissions.py

from enum import Enum


class Permissions(str, Enum):

    # =========================
    # AUTH / SECURITY
    # =========================
    LOGIN = "auth:login"
    LOGOUT = "auth:logout"
    REFRESH_TOKEN = "auth:refresh_token"
    CHANGE_PASSWORD = "auth:change_password"
    CHANGE_PIN = "auth:change_pin"
    VERIFY_OTP = "auth:verify_otp"
    MANAGE_API_KEYS = "auth:manage_api_keys"
    BLACKLIST_TOKEN = "auth:blacklist_token"

    # =========================
    # ROLE MANAGEMENT
    # =========================
    CREATE_ROLE = "role:create"
    READ_ROLE = "role:read"
    UPDATE_ROLE = "role:update"
    DELETE_ROLE = "role:delete"

    # =========================
    # USER MANAGEMENT
    # =========================
    CREATE_USER = "user:create"
    READ_USER = "user:read"
    UPDATE_USER = "user:update"
    DELETE_USER = "user:delete"
    SUSPEND_USER = "user:suspend"
    ASSIGN_ROLE = "user:assign_role"

    # =========================
    # CLIENT MANAGEMENT
    # =========================
    CREATE_CLIENT = "client:create"
    READ_CLIENT = "client:read"
    UPDATE_CLIENT = "client:update"
    DELETE_CLIENT = "client:delete"
    APPROVE_CLIENT = "client:approve"
    RESET_CLIENT_PASSWORD = "client:reset_password"
    RESET_CLIENT_PIN = "client:reset_pin"
    CREATE_CLIENT_PAYMENT = "client_payment:create"
    READ_CLIENT_PAYMENT = "client_payment:read"
    CREATE_CLIENT_RETURN = "client_return:create"
    READ_CLIENT_RETURN = "client_return:read"
    APPROVE_CLIENT_RETURN = "client_return:approve"
    REJECT_CLIENT_RETURN = "client_return:reject"

    # =========================
    # COMPANY
    # =========================
    CREATE_COMPANY = "company:create"
    READ_COMPANY = "company:read"
    UPDATE_COMPANY = "company:update"
    DELETE_COMPANY = "company:delete"

    # =========================
    # PROVIDERS
    # =========================
    CREATE_PROVIDER = "provider:create"
    READ_PROVIDER = "provider:read"
    UPDATE_PROVIDER = "provider:update"
    DELETE_PROVIDER = "provider:delete"
    RETURN_PROVIDER = "provider:return"

    # =========================
    # PROCUREMENT
    # =========================
    CREATE_PROCUREMENT = "procurement:create"
    READ_PROCUREMENT = "procurement:read"
    UPDATE_PROCUREMENT = "procurement:update"
    CANCEL_PROCUREMENT = "procurement:cancel"
    RECEIVE_PROCUREMENT = "procurement:receive"
    RETURN_PROCUREMENT = "procurement:return"

    # =========================
    # PURCHASE INVOICE
    # =========================
    CREATE_PURCHASE_INVOICE = "purchase_invoice:create"
    READ_PURCHASE_INVOICE = "purchase_invoice:read"
    UPDATE_PURCHASE_INVOICE = "purchase_invoice:update"
    PAY_PURCHASE_INVOICE = "purchase_invoice:pay"
    CANCEL_PURCHASE_INVOICE = "purchase_invoice:cancel"

    # =========================
    # PROVIDER PAYMENT
    # =========================
    CREATE_PROVIDER_PAYMENT = "provider_payment:create"
    READ_PROVIDER_PAYMENT = "provider_payment:read"
    READ_PROVIDER_BALANCE = "provider_balance:read"

    # =========================
    # SALES
    # =========================
    CREATE_SALE = "sale:create"
    READ_SALE = "sale:read"
    UPDATE_SALE = "sale:update"
    CANCEL_SALE = "sale:cancel"
    PROCESS_SALE = "sale:process"
    RETURN_SALE = "sale:return"

    # =========================
    # POS
    # =========================
    CREATE_POS = "pos:create"
    READ_POS = "pos:read"
    UPDATE_POS = "pos:update"
    DELETE_POS = "pos:delete"
    READ_POS_REPORT = "pos:report"

    # =========================
    # POS USERS
    # =========================
    CREATE_POS_USER = "pos_user:create"
    READ_POS_USER = "pos_user:read"
    UPDATE_POS_USER = "pos_user:update"
    DELETE_POS_USER = "pos_user:delete"

    # =========================
    # POS EXPENSES
    # =========================
    CREATE_POS_EXPENSE = "pos_expense:create"
    READ_POS_EXPENSE = "pos_expense:read"
    UPDATE_POS_EXPENSE = "pos_expense:update"
    APPROVE_POS_EXPENSE = "pos_expense:approve"
    REJECT_POS_EXPENSE = "pos_expense:reject"
    DELETE_POS_EXPENSE = "pos_expense:delete"
    PAY_POS_EXPENSE = "pos_expense:pay"

    # =========================
    # INVENTORY
    # =========================
    CREATE_WAREHOUSE = "warehouse:create"
    READ_WAREHOUSE = "warehouse:read"
    UPDATE_WAREHOUSE = "warehouse:update"
    DELETE_WAREHOUSE = "warehouse:delete"
    
    CREATE_INVENTORY_ITEM = "inventory_item:create"
    READ_INVENTORY_ITEM = "inventory_item:read"
    UPDATE_INVENTORY_ITEM = "inventory_item:update"
    DELETE_INVENTORY_ITEM = "inventory_item:delete"

    INCREASE_STOCK = "inventory:increase"
    DECREASE_STOCK = "inventory:decrease"
    TRANSFER_STOCK = "inventory:transfer"
    RESERVE_STOCK = "inventory:reserve"
    RELEASE_STOCK = "inventory:release"

    # =========================
    # TAXES
    # =========================
    CREATE_TAX = "tax:create"
    READ_TAX = "tax:read"
    UPDATE_TAX = "tax:update"
    DELETE_TAX = "tax:delete"

    # =========================
    # GEOGRAPHY
    # =========================
    MANAGE_COUNTRY = "geography:country_manage"
    MANAGE_REGION = "geography:region_manage"
    MANAGE_CITY = "geography:city_manage"
    MANAGE_ADDRESS = "geography:address_manage"
    READ_ADDRESS = "geography:read_address"

    # =========================
    # EMPLOYEES
    # =========================
    CREATE_EMPLOYEE = "employee:create"
    READ_EMPLOYEE = "employee:read"
    UPDATE_EMPLOYEE = "employee:update"
    DELETE_EMPLOYEE = "employee:delete"

    MANAGE_CONTRACT = "employee:contract_manage"
    MANAGE_ATTENDANCE = "employee:attendance_manage"
    MANAGE_LEAVE = "employee:leave_manage"
    MANAGE_SALARY = "employee:salary_manage"
    MANAGE_PAYSLIP = "employee:payslip_manage"

    # =========================
    # CART / ORDERS
    # =========================
    CREATE_CATEGORY = "category:create"
    UPDATE_CATEGORY = "category:update"
    READ_CATEGORY = "category:read"
    DELETE_CATEGORY = "category:delete"

    CREATE_PRODUCT = "product:create"
    UPDATE_PRODUCT = "product:update"
    READ_PRODUCT = "product:read"
    DELETE_PRODUCT = "product:delete"

    CREATE_VARIANT = "variant:create"
    UPDATE_VARIANT = "variant:update"
    READ_VARIANT = "variant:read"
    DELETE_VARIANT = "variant:delete"

    CREATE_ORDER = "order:create"
    READ_ORDER = "order:read"
    UPDATE_ORDER = "order:update"
    CANCEL_ORDER = "order:cancel"
    RETURN_ORDER = "order:return"

    # =========================
    # REPORTS
    # =========================
    VIEW_SALES_REPORT = "report:sales_view"
    VIEW_EXPENSE_REPORT = "report:expense_view"
    VIEW_INVENTORY_REPORT = "report:inventory_view"
    VIEW_PROVIDER_REPORT = "report:provider_view"

    AUDIT_LOGS = "audit_logs:read"
    # =========================
    # ID TYPE
    # =========================
    ID_TYPE_CREATE = "id_type:create"
    ID_TYPE_UPDATE = "id_type:update"
    ID_TYPE_READ = "id_type:read"
    ID_TYPE_DELETE = "id_type:delete"

    # =========================
    # SUPER ADMIN
    # =========================
    SYSTEM_ADMIN = "system:admin"
