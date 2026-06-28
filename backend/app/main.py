import logging
import os
import re

from fastapi import FastAPI
from fastapi import Depends
from fastapi.middleware.cors import CORSMiddleware

from app.auth import require_api_key
from app.config import get_settings
from app.database import init_db
from app.routers import assistant, documents, logs, memory, reminders, tasks, today


class _SanitizingFilter(logging.Filter):
    """Strips sensitive credentials from log records before they are emitted."""

    _PATTERNS: list[tuple[re.Pattern[str], str]] = [
        (re.compile(r"(x-api-key[:\s=]+)\S+", re.IGNORECASE), r"\1[REDACTED]"),
        (re.compile(r"(authorization[:\s=]+)\S+", re.IGNORECASE), r"\1[REDACTED]"),
        (re.compile(r"(jarvis[_-]api[_-]key[:\s=]+)\S+", re.IGNORECASE), r"\1[REDACTED]"),
    ]

    def filter(self, record: logging.LogRecord) -> bool:
        record.msg = self._sanitize(str(record.msg))
        if record.args:
            if isinstance(record.args, dict):
                record.args = {
                    k: self._sanitize(v) if isinstance(v, str) else v
                    for k, v in record.args.items()
                }
            else:
                record.args = tuple(
                    self._sanitize(a) if isinstance(a, str) else a
                    for a in record.args
                )
        return True

    def _sanitize(self, text: str) -> str:
        for pattern, replacement in self._PATTERNS:
            text = pattern.sub(replacement, text)
        return text


def _configure_logging(log_level: str = "INFO") -> None:
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    for handler in root_logger.handlers:
        handler.addFilter(_SanitizingFilter())
    if not root_logger.handlers:
        handler = logging.StreamHandler()
        handler.addFilter(_SanitizingFilter())
        root_logger.addHandler(handler)


_configure_logging(os.getenv("LOG_LEVEL", "INFO"))

settings = get_settings()

app = FastAPI(
    title="Local LLM Jarvis API",
    version="0.1.0",
    description="Local-first personal assistant API for Android and web clients.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup() -> None:
    init_db()


@app.get("/health", tags=["system"])
def health() -> dict[str, str]:
    return {"status": "ok", "environment": settings.app_env}


protected_dependencies = [Depends(require_api_key)]
app.include_router(today.router, dependencies=protected_dependencies)
app.include_router(assistant.router, dependencies=protected_dependencies)
app.include_router(tasks.router, dependencies=protected_dependencies)
app.include_router(reminders.router, dependencies=protected_dependencies)
app.include_router(logs.router, dependencies=protected_dependencies)
app.include_router(memory.router, dependencies=protected_dependencies)
app.include_router(documents.router, dependencies=protected_dependencies)
