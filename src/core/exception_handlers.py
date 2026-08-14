"""Global exception handlers.

Route-level try/except blocks already convert most known errors into
HTTPExceptions. These handlers are the safety net: anything that slips
through (a bug, an unexpected InventoryException, a raw unhandled error)
still gets a full traceback in error.log instead of vanishing into a bare
500, and the client still gets a well-formed JSON response.
"""
import logging

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from src.core.custom_exceptions import InventoryException

logger = logging.getLogger(__name__)


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(InventoryException)
    async def inventory_exception_handler(request: Request, exc: InventoryException):
        logger.warning(
            f"{request.method} {request.url.path} -> {exc.__class__.__name__}: {exc.message}",
            extra={"extra_fields": {
                "method": request.method,
                "path": request.url.path,
                "status_code": exc.status_code,
            }},
        )
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.message})

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception):
        logger.exception(
            f"{request.method} {request.url.path} -> unhandled {exc.__class__.__name__}",
            extra={"extra_fields": {
                "method": request.method,
                "path": request.url.path,
                "status_code": 500,
            }},
        )
        return JSONResponse(status_code=500, content={"detail": "Internal server error"})
