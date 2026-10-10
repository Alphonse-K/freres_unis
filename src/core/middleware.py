"""ASGI middleware: assigns a request id and logs one line per request.

Implemented as raw ASGI (not BaseHTTPMiddleware) so the request id lands in
the same task/thread as the route handler -- contextvars set here are then
visible from every logger call made while handling the request, including
sync handlers run in FastAPI's threadpool.
"""
import logging
import time

from starlette.datastructures import MutableHeaders
from starlette.types import ASGIApp, Receive, Scope, Send

from src.core.request_context import new_request_id, set_request_id, set_user_id

logger = logging.getLogger("src.access")


class RequestLoggingMiddleware:
    def __init__(self, app: ASGIApp):
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request_id = None
        for name, value in scope.get("headers", []):
            if name == b"x-request-id":
                request_id = value.decode()
                break
        request_id = request_id or new_request_id()
        set_request_id(request_id)
        set_user_id("-")

        method = scope.get("method")
        path = scope.get("path")
        client = scope.get("client")
        client_ip = client[0] if client else None

        status_code = 500

        async def send_wrapper(message):
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = message["status"]
                headers = MutableHeaders(scope=message)
                headers.append("X-Request-ID", request_id)
            await send(message)

        start = time.monotonic()
        try:
            await self.app(scope, receive, send_wrapper)
        except Exception:
            duration_ms = round((time.monotonic() - start) * 1000, 2)
            logger.exception(
                f"{method} {path} -> unhandled exception",
                extra={"extra_fields": {
                    "duration_ms": duration_ms,
                    "client_ip": client_ip,
                }},
            )
            raise

        duration_ms = round((time.monotonic() - start) * 1000, 2)
        log_fn = logger.warning if status_code >= 500 else logger.info
        log_fn(
            f"{method} {path} {status_code}",
            extra={"extra_fields": {
                "duration_ms": duration_ms,
                "client_ip": client_ip,
            }},
        )
