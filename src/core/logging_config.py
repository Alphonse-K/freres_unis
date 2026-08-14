"""Centralized logging configuration.

Emits JSON-lines to rotating files (app.log = everything at LOG_LEVEL+,
error.log = ERROR+ only for fast triage) plus stdout (captured by
`docker logs`). Every record is tagged with the current request id / user
id (see request_context.py) so a single failing request can be grepped
out of the noise across all workers.
"""
import json
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


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": self.formatTime(record, "%Y-%m-%dT%H:%M:%S%z"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "request_id": getattr(record, "request_id", "-"),
            "user_id": getattr(record, "user_id", "-"),
            "module": record.module,
            "func": record.funcName,
            "line": record.lineno,
        }
        if record.process:
            payload["process"] = record.process
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        extras = getattr(record, "extra_fields", None)
        if extras:
            payload.update(extras)
        return json.dumps(payload, default=str)


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
            "json": {"()": JsonFormatter},
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "formatter": "json",
                "filters": ["request_context"],
            },
            "app_file": {
                "class": "logging.handlers.RotatingFileHandler",
                "formatter": "json",
                "filters": ["request_context"],
                "filename": str(LOGS_DIR / "app.log"),
                "maxBytes": 10 * 1024 * 1024,
                "backupCount": 10,
                "encoding": "utf-8",
            },
            "error_file": {
                "class": "logging.handlers.RotatingFileHandler",
                "formatter": "json",
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
