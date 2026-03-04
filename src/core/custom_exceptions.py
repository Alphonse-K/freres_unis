# ================================
# CUSTOM EXCEPTIONS
# ================================
class InventoryException(Exception):
    """Base exception for inventory operations"""
    def __init__(self, message: str, status_code: int = 400):
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)


class NotFoundException(InventoryException):
    """Raised when a resource is not found"""
    def __init__(self, message: str = "Resource not found"):
        super().__init__(message, status_code=404)


class ValidationException(InventoryException):
    """Raised when validation fails"""
    def __init__(self, message: str = "Validation failed"):
        super().__init__(message, status_code=400)


class BusinessRuleException(InventoryException):
    """Raised when a business rule is violated"""
    def __init__(self, message: str = "Business rule violation"):
        super().__init__(message, status_code=422)


class InsufficientStockException(InventoryException):
    """Raised when there's insufficient stock"""
    def __init__(self, message: str = "Insufficient stock"):
        super().__init__(message, status_code=400)
