"""Per-IP request throttle so a stranger cannot burn our GitHub quota."""

from __future__ import annotations

import threading
import time
from collections import defaultdict, deque

from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.api.errors import error_body

WINDOW_SECONDS = 60.0
MAX_REQUESTS = 60
_EXEMPT_PATHS = {"/api/health"}

_lock = threading.Lock()
_hits: dict[str, deque[float]] = defaultdict(deque)


def reset_throttle_for_tests() -> None:
    with _lock:
        _hits.clear()


def _client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip() or "unknown"
    if request.client:
        return request.client.host
    return "unknown"


def allow(ip: str, *, limit: int | None = None, now: float | None = None) -> bool:
    cap = MAX_REQUESTS if limit is None else limit
    ts = time.monotonic() if now is None else now
    cutoff = ts - WINDOW_SECONDS
    with _lock:
        queue = _hits[ip]
        while queue and queue[0] < cutoff:
            queue.popleft()
        if len(queue) >= cap:
            return False
        queue.append(ts)
        return True


class IPThrottleMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        if request.url.path in _EXEMPT_PATHS:
            return await call_next(request)
        if not allow(_client_ip(request)):
            return JSONResponse(
                status_code=429,
                content=error_body(
                    "RATE_LIMITED",
                    "Too many requests from this IP, try again in a minute",
                ),
            )
        return await call_next(request)
