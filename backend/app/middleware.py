import json
import logging
import time
import uuid
from collections import deque
from threading import Lock
from typing import Deque

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp

# ---------------------------------------------------------------------------
# Structured JSON logger
# ---------------------------------------------------------------------------

_json_handler = logging.StreamHandler()
_json_handler.setFormatter(logging.Formatter("%(message)s"))

logger = logging.getLogger("jarvis.access")
logger.setLevel(logging.INFO)
logger.addHandler(_json_handler)
logger.propagate = False


def _log(record: dict) -> None:
    logger.info(json.dumps(record, default=str))


# ---------------------------------------------------------------------------
# In-memory metrics store
# ---------------------------------------------------------------------------

_MAX_DURATION_SAMPLES = 1000  # ring-buffer cap


class _MetricsStore:
    def __init__(self) -> None:
        self._lock = Lock()
        self.total_requests: int = 0
        self.error_5xx: int = 0
        self.error_4xx: int = 0
        # Recent duration samples in milliseconds (capped ring-buffer)
        self._durations: Deque[float] = deque(maxlen=_MAX_DURATION_SAMPLES)

    def record(self, status_code: int, duration_ms: float) -> None:
        with self._lock:
            self.total_requests += 1
            if 500 <= status_code < 600:
                self.error_5xx += 1
            elif 400 <= status_code < 500:
                self.error_4xx += 1
            self._durations.append(duration_ms)

    def snapshot(self) -> dict:
        with self._lock:
            total = self.total_requests
            err5 = self.error_5xx
            err4 = self.error_4xx
            durations = sorted(self._durations)

        def percentile(data: list[float], p: float) -> float | None:
            if not data:
                return None
            idx = max(0, int(len(data) * p / 100) - 1)
            return round(data[idx], 2)

        error_rate_5xx = round(err5 / total, 4) if total else 0.0
        return {
            "total_requests": total,
            "error_4xx": err4,
            "error_5xx": err5,
            "error_rate_5xx": error_rate_5xx,
            "latency_ms": {
                "p50": percentile(durations, 50),
                "p95": percentile(durations, 95),
                "p99": percentile(durations, 99),
                "samples": len(durations),
            },
        }


metrics_store = _MetricsStore()


# ---------------------------------------------------------------------------
# Middleware
# ---------------------------------------------------------------------------


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Attaches a request ID to every request and emits structured JSON logs."""

    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app)

    async def dispatch(self, request: Request, call_next) -> Response:  # type: ignore[override]
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        request.state.request_id = request_id

        start = time.perf_counter()
        _log(
            {
                "event": "request_started",
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
            }
        )

        response: Response = await call_next(request)

        duration_ms = (time.perf_counter() - start) * 1000
        metrics_store.record(response.status_code, duration_ms)

        _log(
            {
                "event": "request_finished",
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "duration_ms": round(duration_ms, 2),
            }
        )

        response.headers["X-Request-ID"] = request_id
        return response
