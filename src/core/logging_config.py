"""Centralized logging configuration.

Emits plain-text lines to rotating files (app.log = everything at LOG_LEVEL+,
error.log = ERROR+ only for fast triage) plus stdout (captured by
`docker logs`). Every record is tagged with the current request id / user
id (see request_context.py) so a single failing request can be grepped
out of the noise across all workers.
"""
import logging
import logging.config
from pathlib import Path

from src.core.config import settings
from src.core.request_context import get_request_id, get_user_id

IS_DOCKER = Path("/app").exists()
LOGS_DIR = Path("/app/logs") if IS_DOCKER else Path("logs")

_CONFIGURED = False


class RequestContextFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = get_request_id()
        record.user_id = get_user_id()
        return True


class PlainFormatter(logging.Formatter):
    """Human-readable single-line format, e.g.:

    2026-10-10 14:32:01 INFO  [src.access] req=abc123 user=42 GET /api/v1/sales/ 200 (duration_ms=12.3 client_ip=1.2.3.4)
    """

    def format(self, record: logging.LogRecord) -> str:
        base = (
            f"{self.formatTime(record, '%Y-%m-%d %H:%M:%S')} "
            f"{record.levelname:<5} [{record.name}] "
            f"req={getattr(record, 'request_id', '-')} user={getattr(record, 'user_id', '-')} "
            f"{record.getMessage()}"
        )
        extras = getattr(record, "extra_fields", None)
        if extras:
            base += " (" + " ".join(f"{k}={v}" for k, v in extras.items()) + ")"
        if record.exc_info:
            base += "\n" + self.formatException(record.exc_info)
        return base


def setup_logging() -> None:
    global _CONFIGURED
    if _CONFIGURED:
        return
    _CONFIGURED = True

    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    level = settings.LOG_LEVEL.upper()

    logging.config.dictConfig({
        "version": 1,
        "disable_existing_loggers": False,
        "filters": {
            "request_context": {"()": RequestContextFilter},
        },
        "formatters": {
            "plain": {"()": PlainFormatter},
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "formatter": "plain",
                "filters": ["request_context"],
            },
            "app_file": {
                "class": "logging.handlers.RotatingFileHandler",
                "formatter": "plain",
                "filters": ["request_context"],
                "filename": str(LOGS_DIR / "app.log"),
                "maxBytes": 10 * 1024 * 1024,
                "backupCount": 10,
                "encoding": "utf-8",
            },
            "error_file": {
                "class": "logging.handlers.RotatingFileHandler",
                "formatter": "plain",
                "filters": ["request_context"],
                "filename": str(LOGS_DIR / "error.log"),
                "level": "ERROR",
                "maxBytes": 10 * 1024 * 1024,
                "backupCount": 10,
                "encoding": "utf-8",
            },
        },
        "root": {
            "level": level,
            "handlers": ["console", "app_file", "error_file"],
        },
        "loggers": {
            # Route uvicorn's own logging through the same handlers/format
            # instead of its default stream-only config.
            "uvicorn": {"level": "INFO", "handlers": [], "propagate": True},
            "uvicorn.error": {"level": "INFO", "handlers": [], "propagate": True},
            "uvicorn.access": {"level": "INFO", "handlers": [], "propagate": True},
            "sqlalchemy.engine": {
                "level": "INFO" if settings.SQL_ECHO else "WARNING",
                "handlers": [],
                "propagate": True,
            },
        },
    })
