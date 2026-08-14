"""Per-request context propagated into log records (request id, user)."""
import uuid
from contextvars import ContextVar

_request_id: ContextVar[str] = ContextVar("request_id", default="-")
_user_id: ContextVar[str] = ContextVar("user_id", default="-")


def new_request_id() -> str:
    return uuid.uuid4().hex[:16]


def set_request_id(value: str) -> None:
    _request_id.set(value)


def get_request_id() -> str:
    return _request_id.get()


def set_user_id(value: str) -> None:
    _user_id.set(value)


def get_user_id() -> str:
    return _user_id.get()
