# src/routes/providers.py
from fastapi import APIRouter, Depends, Query, HTTPException, status, Path
from sqlalchemy.orm import Session
from datetime import date, datetime
from decimal import Decimal
from typing import List, Optional

from src.core.database import get_db
from src.core.auth_dependencies import get_current_account
from src.models.users import User
from src.models.providers import PurchaseInvoiceStatus, PaymentMethod
from starlette.responses import JSONResponse
from src.schemas.providers import (
    # Provider
    ProviderCreate, ProviderUpdate, ProviderResponse, ProviderSummaryResponse,
    # Invoice
    PurchaseInvoiceCreate, PurchaseInvoiceUpdate, PurchaseInvoiceResponse,
    # Payment
    ProviderPaymentCreate, ProviderPaymentResponse,
    # Returns
    PurchaseReturnCreate, PurchaseReturnResponse
)
from src.schemas.location import AddressCreate, AddressUpdate, AddressOut
from src.services.provider_service import ProviderService


provider_router = APIRouter(prefix="/providers", tags=["providers"])


# ================================
# PROVIDER CRUD ROUTES
# ================================
@provider_router.post("/", 
    response_model=ProviderResponse, 
    status_code=status.HTTP_201_CREATED,
    summary="Create a new provider",
    description="Create a new provider with optional addresses. Returns the created provider."
)
def create_provider(
    data: ProviderCreate,
    current_account: dict = Depends(get_current_account),
    db: Session = Depends(get_db)
):
    """
    Create a new provider with optional addresses.
    
    - **name**: Provider name (required, 2-255 chars)
    - **phone**: Phone number (optional)
    - **email**: Email address (optional)
    - **is_active**: Active status (default: true)
    - **opening_balance**: Initial balance (default: 0)
    - **addresses**: List of addresses (optional)
    """
    return ProviderService.create_provider(db, data)


@provider_router.get("/", 
    response_model=List[ProviderResponse],
    summary="List all providers",
    description="Get a list of all providers with optional filtering and search."
)
def list_providers(
    search: Optional[str] = Query(None, description="Search by name, phone, or email"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    country_id: Optional[int] = Query(None, description="Filter by country"),
    limit: int = Query(100, ge=1, le=200, description="Number of results per page"),
    offset: int = Query(0, ge=0, description="Page offset for pagination"),
    current_account: dict = Depends(get_current_account),
    db: Session = Depends(get_db)
):
    """
    List providers with search and filtering.
    
    - **search**: Search across name, phone, and email
    - **is_active**: Filter by active/inactive status
    - **country_id**: Filter by country
    - **limit**: Pagination limit (1-200)
    - **offset**: Pagination offset
    """
    return ProviderService.list_providers(
        db=db,
        search=search,
        is_active=is_active,
        country_id=country_id,
        limit=limit,
        offset=offset
    )


@provider_router.get("/{provider_id}", 
    response_model=ProviderResponse,
    summary="Get provider details",
    description="Get detailed information about a specific provider including addresses."
)
def get_provider(
    provider_id: int = Path(..., description="Provider ID", gt=0),
    current_account: dict = Depends(get_current_account),
    db: Session = Depends(get_db)
):
    """
    Get provider details by ID.
    
    - **provider_id**: ID of the provider to retrieve
    - Returns: Provider details with addresses and relationships
    """
    provider = ProviderService.get_provider(db, provider_id)
    
    if not provider:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Provider not found"
        )
    
    return provider


@provider_router.put("/{provider_id}", 
    response_model=ProviderResponse,
    summary="Update provider information",
    description="Update provider details such as name, phone, email, or active status."
)
def update_provider(
    provider_id: int = Path(..., description="Provider ID", gt=0),
    data: ProviderUpdate = Depends(),
    current_account: dict = Depends(get_current_account),
    db: Session = Depends(get_db)
):
    """
    Update provider information.
    
    - **provider_id**: ID of the provider to update
    - **data**: Updated provider fields
    - Returns: Updated provider
    """
    return ProviderService.update_provider(db, provider_id, data)


@provider_router.delete("/{provider_id}", 
    summary="Deactivate provider",
    description="Soft delete a provider by setting is_active=False. Cannot delete providers with outstanding invoices."
)
def delete_provider(
    provider_id: int = Path(..., description="Provider ID", gt=0),
    current_account: dict = Depends(get_current_account),
    db: Session = Depends(get_db)
):
    """
    Deactivate a provider (soft delete).
    
    - **provider_id**: ID of the provider to deactivate
    - Returns: Success message
    - Note: Cannot deactivate providers with outstanding unpaid invoices
    """
    success = ProviderService.delete_provider(db, provider_id)
    
    if success:
        return {"message": "Provider deactivated successfully"}
    
    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="Failed to delete provider"
    )


# ================================
# PROVIDER ADDRESS ROUTES
# ================================

@provider_router.post("/{provider_id}/addresses", 
    response_model=AddressOut,
    status_code=status.HTTP_201_CREATED,
    summary="Add address to provider",
    description="Add a new address to an existing provider."
)
def add_provider_address(
    provider_id: int = Path(..., description="Provider ID", gt=0),
    address_data: AddressCreate = Depends(),
    current_account: dict = Depends(get_current_account),
    db: Session = Depends(get_db)
):
    """
    Add an address to a provider.
    
    - **provider_id**: ID of the provider
    - **address_data**: Address details including geography references
    - Returns: Created address with geography relationships
    """
    return ProviderService.add_provider_address(db, provider_id, address_data)


@provider_router.get("/{provider_id}/addresses", 
    response_model=List[AddressOut],
    summary="Get provider addresses",
    description="Get all addresses for a specific provider."
)
def get_provider_addresses(
    provider_id: int = Path(..., description="Provider ID", gt=0),
    current_account: dict = Depends(get_current_account),
    db: Session = Depends(get_db)
):
    """
    Get all addresses for a provider.
    
    - **provider_id**: ID of the provider
    - Returns: List of addresses with full geography details
    """
    return ProviderService.get_provider_addresses(db, provider_id)


@provider_router.get("/{provider_id}/addresses/default", 
    response_model=AddressOut,
    summary="Get default address",
    description="Get the default address for a provider."
)
def get_provider_default_address(
    provider_id: int = Path(..., description="Provider ID", gt=0),
    current_account: dict = Depends(get_current_account),
    db: Session = Depends(get_db)
):
    """
    Get provider's default address.
    
    - **provider_id**: ID of the provider
    - Returns: Default address if exists
    """
    address = ProviderService.get_provider_default_address(db, provider_id)
    
    if not address:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No default address found for this provider"
        )
    
    return address


@provider_router.put("/{provider_id}/addresses/{address_id}", 
    response_model=AddressOut,
    summary="Update provider address",
    description="Update an existing address for a provider."
)
def update_provider_address(
    provider_id: int = Path(..., description="Provider ID", gt=0),
    address_id: int = Path(..., description="Address ID", gt=0),
    address_data: AddressUpdate = Depends(),
    current_account: dict = Depends(get_current_account),
    db: Session = Depends(get_db)
):
    """
    Update a provider's address.
    
    - **provider_id**: ID of the provider
    - **address_id**: ID of the address to update
    - **address_data**: Updated address fields
    - Returns: Updated address
    """
    return ProviderService.update_provider_address(
        db, provider_id, address_id, address_data
    )


@provider_router.delete("/{provider_id}/addresses/{address_id}", 
    summary="Delete provider address",
    description="Remove an address from a provider."
)
def delete_provider_address(
    provider_id: int = Path(..., description="Provider ID", gt=0),
    address_id: int = Path(..., description="Address ID", gt=0),
    current_account: dict = Depends(get_current_account),
    db: Session = Depends(get_db)
):
    """
    Delete a provider's address.
    
    - **provider_id**: ID of the provider
    - **address_id**: ID of the address to delete
    - Returns: Success message
    """
    success = ProviderService.delete_provider_address(db, provider_id, address_id)
    
    if success:
        return {"message": "Address deleted successfully"}
    
    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="Failed to delete address"
    )


# ================================
# PROVIDER BALANCE & FINANCE ROUTES
# ================================

@provider_router.get("/{provider_id}/balance", 
    summary="Get provider balance",
    description="Get detailed balance breakdown for a provider."
)
def get_provider_balance(
    provider_id: int = Path(..., description="Provider ID", gt=0),
    current_account: dict = Depends(get_current_account),
    db: Session = Depends(get_db)
):
    """
    Get provider's current balance breakdown.
    
    - **provider_id**: ID of the provider
    - Returns: Balance calculation (opening + invoices - payments - returns)
    """
    return ProviderService.calculate_provider_balance(db, provider_id)


@provider_router.get("/{provider_id}/balance-history", 
    summary="Get balance history",
    description="Get balance history and payment trends over time."
)
def get_provider_balance_history(
    provider_id: int = Path(..., description="Provider ID", gt=0),
    start_date: Optional[date] = Query(None, description="Start date for history"),
    end_date: Optional[date] = Query(None, description="End date for history"),
    current_account: dict = Depends(get_current_account),
    db: Session = Depends(get_db)
):
    """
    Get provider balance history over time.
    
    - **provider_id**: ID of the provider
    - **start_date**: Optional start date filter
    - **end_date**: Optional end date filter
    - Returns: Payment trends by month
    """
    return ProviderService.get_provider_balance_history(
        db, provider_id, start_date, end_date
    )


# ================================
# PURCHASE INVOICE ROUTES
# ================================

@provider_router.post("/{provider_id}/invoices", 
    response_model=PurchaseInvoiceResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create purchase invoice",
    description="Create a new purchase invoice for a provider."
)
def create_purchase_invoice(
    provider_id: int = Path(..., description="Provider ID", gt=0),
    data: PurchaseInvoiceCreate = Depends(),
    current_account: dict = Depends(get_current_account),
    db: Session = Depends(get_db)
):
    """
    Create a purchase invoice for a provider.
    
    - **provider_id**: ID of the provider
    - **data**: Invoice details
    - Returns: Created invoice
    - Note: Automatically updates provider balance
    """
    if data.provider_id != provider_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Provider ID mismatch"
        )
    
    return ProviderService.create_purchase_invoice(db, data)


@provider_router.get("/{provider_id}/invoices", 
    response_model=List[PurchaseInvoiceResponse],
    summary="List provider invoices",
    description="Get all invoices for a provider with optional filtering."
)
def list_provider_invoices(
    provider_id: int = Path(..., description="Provider ID", gt=0),
    status: Optional[str] = Query(None, description="Filter by invoice status"),
    overdue_only: bool = Query(False, description="Show only overdue invoices"),
    limit: int = Query(100, ge=1, le=200, description="Number of results per page"),
    offset: int = Query(0, ge=0, description="Page offset for pagination"),
    current_account: dict = Depends(get_current_account),
    db: Session = Depends(get_db)
):
    """
    List invoices for a provider.
    
    - **provider_id**: ID of the provider
    - **status**: Filter by status (pending, partially_paid, paid, cancelled)
    - **overdue_only**: Show only overdue invoices
    - **limit**: Pagination limit
    - **offset**: Pagination offset
    """
    status_enum = None
    if status:
        try:
            status_enum = PurchaseInvoiceStatus(status.lower())
        except ValueError:
            pass
    
    invoices = ProviderService.list_provider_invoices(
        db=db,
        provider_id=provider_id,
        status=status_enum,
        overdue_only=overdue_only,
        limit=limit,
        offset=offset
    )
    
    return invoices


@provider_router.get("/invoices/{invoice_id}", 
    response_model=PurchaseInvoiceResponse,
    summary="Get invoice details",
    description="Get detailed information about a specific purchase invoice."
)
def get_purchase_invoice(
    invoice_id: int = Path(..., description="Invoice ID", gt=0),
    current_account: dict = Depends(get_current_account),
    db: Session = Depends(get_db)
):
    """
    Get purchase invoice details.
    
    - **invoice_id**: ID of the invoice
    - Returns: Invoice details with provider and procurement info
    """
    invoice = ProviderService.get_purchase_invoice(db, invoice_id)
    
    if not invoice:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invoice not found"
        )
    
    return invoice


@provider_router.put("/invoices/{invoice_id}", 
    response_model=PurchaseInvoiceResponse,
    summary="Update invoice",
    description="Update invoice details, mainly payment status and amounts."
)
def update_purchase_invoice(
    invoice_id: int = Path(..., description="Invoice ID", gt=0),
    data: PurchaseInvoiceUpdate = Depends(),
    current_account: dict = Depends(get_current_account),
    db: Session = Depends(get_db)
):
    """
    Update purchase invoice.
    
    - **invoice_id**: ID of the invoice to update
    - **data**: Updated invoice fields (status, paid_amount, notes)
    - Returns: Updated invoice
    - Note: Automatically updates provider balance
    """
    return ProviderService.update_purchase_invoice(db, invoice_id, data)


@provider_router.post("/invoices/{invoice_id}/cancel", 
    response_model=PurchaseInvoiceResponse,
    summary="Cancel invoice",
    description="Cancel a purchase invoice. Cannot cancel paid invoices."
)
def cancel_purchase_invoice(
    invoice_id: int = Path(..., description="Invoice ID", gt=0),
    reason: Optional[str] = Query(None, description="Reason for cancellation"),
    current_account: dict = Depends(get_current_account),
    db: Session = Depends(get_db)
):
    """
    Cancel a purchase invoice.
    
    - **invoice_id**: ID of the invoice to cancel
    - **reason**: Optional reason for cancellation
    - Returns: Cancelled invoice
    - Note: Cannot cancel paid invoices
    """
    return ProviderService.cancel_purchase_invoice(db, invoice_id, reason)


# ================================
# PAYMENT ROUTES
# ================================

@provider_router.post("/{provider_id}/payments", 
    response_model=ProviderPaymentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Record payment",
    description="Record a payment to a provider. Can be linked to an invoice or general payment."
)
def create_payment(
    provider_id: int = Path(..., description="Provider ID", gt=0),
    data: ProviderPaymentCreate = Depends(),
    current_account: dict = Depends(get_current_account),
    db: Session = Depends(get_db)
):
    """
    Record a payment to provider.
    
    - **provider_id**: ID of the provider
    - **data**: Payment details
    - Returns: Created payment record
    - Note: Updates invoice status and provider balance automatically
    """
    if data.provider_id != provider_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Provider ID mismatch"
        )
    
    return ProviderService.create_payment(db, data)


@provider_router.get("/{provider_id}/payments", 
    response_model=List[ProviderPaymentResponse],
    summary="List provider payments",
    description="Get all payments made to a provider with optional date filtering."
)
def get_provider_payments(
    provider_id: int = Path(..., description="Provider ID", gt=0),
    start_date: Optional[date] = Query(None, description="Start date for payments"),
    end_date: Optional[date] = Query(None, description="End date for payments"),
    limit: int = Query(100, ge=1, le=200, description="Number of results per page"),
    offset: int = Query(0, ge=0, description="Page offset for pagination"),
    current_account: dict = Depends(get_current_account),
    db: Session = Depends(get_db)
):
    """
    Get payments for a provider.
    
    - **provider_id**: ID of the provider
    - **start_date**: Optional start date filter
    - **end_date**: Optional end date filter
    - **limit**: Pagination limit
    - **offset**: Pagination offset
    """
    return ProviderService.get_provider_payments(
        db=db,
        provider_id=provider_id,
        start_date=start_date,
        end_date=end_date,
        limit=limit,
        offset=offset
    )


@provider_router.get("/payments/{payment_id}", 
    response_model=ProviderPaymentResponse,
    summary="Get payment details",
    description="Get detailed information about a specific payment."
)
def get_payment(
    payment_id: int = Path(..., description="Payment ID", gt=0),
    current_account: dict = Depends(get_current_account),
    db: Session = Depends(get_db)
):
    """
    Get payment details.
    
    - **payment_id**: ID of the payment
    - Returns: Payment details with provider and invoice info
    """
    payment = ProviderService.get_payment(db, payment_id)
    
    if not payment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payment not found"
        )
    
    return payment


# ================================
# PURCHASE RETURN ROUTES
# ================================

@provider_router.post("/{provider_id}/returns", 
    response_model=PurchaseReturnResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Record purchase return",
    description="Record a purchase return for goods returned to a provider."
)
def create_purchase_return(
    provider_id: int = Path(..., description="Provider ID", gt=0),
    invoice_id: int = Query(..., description="Invoice ID for the return", gt=0),
    return_date: date = Query(..., description="Date of return"),
    amount: Decimal = Query(..., gt=0, description="Return amount"),
    reason: str = Query(..., min_length=2, max_length=255, description="Reason for return"),
    current_account: dict = Depends(get_current_account),
    db: Session = Depends(get_db)
):
    """
    Record a purchase return.
    
    - **provider_id**: ID of the provider
    - **invoice_id**: ID of the related invoice
    - **return_date**: Date when return occurred
    - **amount**: Amount of the return
    - **reason**: Reason for the return
    - Returns: Created return record
    - Note: Updates provider balance automatically
    """
    return ProviderService.create_purchase_return(
        db, provider_id, invoice_id, return_date, amount, reason
    )


@provider_router.get("/{provider_id}/returns", 
    response_model=List[PurchaseReturnResponse],
    summary="List purchase returns",
    description="Get all purchase returns for a provider."
)
def get_provider_returns(
    provider_id: int = Path(..., description="Provider ID", gt=0),
    start_date: Optional[date] = Query(None, description="Start date for returns"),
    end_date: Optional[date] = Query(None, description="End date for returns"),
    current_account: dict = Depends(get_current_account),
    db: Session = Depends(get_db)
):
    """
    Get purchase returns for a provider.
    
    - **provider_id**: ID of the provider
    - **start_date**: Optional start date filter
    - **end_date**: Optional end date filter
    """
    return ProviderService.get_provider_returns(
        db, provider_id, start_date, end_date
    )


# ================================
# REPORTING & ANALYTICS ROUTES
# ================================

@provider_router.get("/{provider_id}/summary", 
    response_model=ProviderSummaryResponse,
    summary="Get provider summary",
    description="Get comprehensive summary including statistics, recent activity, and aging analysis."
)
def get_provider_summary(
    provider_id: int = Path(..., description="Provider ID", gt=0),
    current_account: dict = Depends(get_current_account),
    db: Session = Depends(get_db)
):
    """
    Get comprehensive provider summary.
    
    - **provider_id**: ID of the provider
    - Returns: Statistics, recent procurements/payments, invoice aging, etc.
    """
    return ProviderService.get_provider_summary(db, provider_id)


@provider_router.get("/reports/overdue-invoices", 
    summary="Get overdue invoices report",
    description="Get all overdue invoices across all providers."
)
def get_overdue_invoices(
    days_overdue: int = Query(30, ge=0, description="Minimum days overdue"),
    current_account: dict = Depends(get_current_account),
    db: Session = Depends(get_db)
):
    """
    Get all overdue invoices across all providers.
    
    - **days_overdue**: Minimum days overdue (default: 30)
    - Returns: List of overdue invoices with provider info
    """
    return ProviderService.get_overdue_invoices(db, days_overdue)


@provider_router.get("/reports/top-providers", 
    summary="Get top providers report",
    description="Get top providers by purchase amount for a given period."
)
def get_top_providers_by_purchases(
    start_date: Optional[date] = Query(None, description="Start date for analysis"),
    end_date: Optional[date] = Query(None, description="End date for analysis"),
    limit: int = Query(10, ge=1, le=50, description="Number of top providers to return"),
    current_account: dict = Depends(get_current_account),
    db: Session = Depends(get_db)
):
    """
    Get top providers by purchase amount.
    
    - **start_date**: Optional start date for period
    - **end_date**: Optional end date for period
    - **limit**: Number of top providers to return (1-50)
    - Returns: List of providers with purchase statistics
    """
    return ProviderService.get_top_providers_by_purchases(
        db, start_date, end_date, limit
    )


@provider_router.get("/{provider_id}/performance", 
    summary="Get provider performance metrics",
    description="Get performance metrics including payment timeliness and rates."
)
def get_provider_performance_metrics(
    provider_id: int = Path(..., description="Provider ID", gt=0),
    start_date: Optional[date] = Query(None, description="Start date for metrics"),
    end_date: Optional[date] = Query(None, description="End date for metrics"),
    current_account: dict = Depends(get_current_account),
    db: Session = Depends(get_db)
):
    """
    Get provider performance metrics.
    
    - **provider_id**: ID of the provider
    - **start_date**: Optional start date for period
    - **end_date**: Optional end date for period
    - Returns: Performance metrics (avg payment days, on-time rate, etc.)
    """
    return ProviderService.get_provider_performance_metrics(
        db, provider_id, start_date, end_date
    )


@provider_router.get("/reports/aging-analysis", 
    summary="Get aging analysis report",
    description="Get accounts payable aging analysis for all providers."
)
def get_aging_analysis(
    current_account: dict = Depends(get_current_account),
    db: Session = Depends(get_db)
):
    """
    Get aging analysis for all providers.
    
    - Returns: Summary of outstanding invoices by aging buckets
    """
    # This would be a more complex report - implement as needed
    providers = ProviderService.list_providers(db, is_active=True)
    
    aging_summary = {
        "total_outstanding": Decimal('0'),
        "aging_buckets": {
            "0_30": Decimal('0'),
            "31_60": Decimal('0'),
            "61_90": Decimal('0'),
            "90_plus": Decimal('0')
        },
        "providers": []
    }
    
    for provider in providers:
        aging = ProviderService._calculate_invoice_aging(db, provider.id)
        aging_summary["total_outstanding"] += aging["total"]
        aging_summary["aging_buckets"]["0_30"] += aging["0_30"]
        aging_summary["aging_buckets"]["31_60"] += aging["31_60"]
        aging_summary["aging_buckets"]["61_90"] += aging["61_90"]
        aging_summary["aging_buckets"]["90_plus"] += aging["90_plus"]
        
        if aging["total"] > 0:
            aging_summary["providers"].append({
                "id": provider.id,
                "name": provider.name,
                "outstanding": aging["total"],
                "aging": aging
            })
    
    return aging_summary
