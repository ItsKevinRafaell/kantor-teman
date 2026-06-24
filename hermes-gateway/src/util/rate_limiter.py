"""Rate limiting middleware — in-memory token bucket per IP/endpoint."""
import threading
import time
from collections import defaultdict
from dataclasses import dataclass
from typing import Optional

from fastapi import HTTPException, Request
from starlette.middleware.base import BaseHTTPMiddleware

# ── Config ─────────────────────────────────────────────────────────────────────
RATE_LIMIT_ENABLED = True  # Set to False to disable globally
RATE_LIMIT_STORAGE: dict[str, list[float]] = defaultdict(list)
_RATE_LIMIT_LOCK = threading.Lock()

# ── Rate limit rules ─────────────────────────────────────────────────────────────
RATE_RULES: dict[str, tuple[int, int]] = {
    # (max_requests, window_seconds)
    "/api/auth/login": (5, 300),      # 5 attempts per 5 minutes
    "/api/office/chat": (30, 60),     # 30 messages per minute
    "/api/office/chat/flush": (10, 60), # 10 flushes per minute
    "/api/office/agents": (30, 60),    # 30 agent ops per minute
    "default": (100, 60),              # 100 requests per minute default
}


@dataclass
class RateLimitRule:
    max_requests: int
    window_seconds: int


def _get_rule(path: str) -> RateLimitRule:
    """Get rate limit rule for a path."""
    for pattern, rule in RATE_RULES.items():
        if pattern != "default" and path.startswith(pattern):
            return RateLimitRule(*rule)
    return RateLimitRule(*RATE_RULES["default"])


def _client_ip(request: Request) -> str:
    """Extract client IP from request."""
    forwarded = request.headers.get("x-forwarded-for", "")
    if forwarded:
        return forwarded.split(",")[0].strip()[:64]
    return request.client.host if request.client else "unknown"


def check_rate_limit(request: Request) -> Optional[dict]:
    """
    Check rate limit for request. Returns None if allowed, raises HTTPException if limited.
    """
    if not RATE_LIMIT_ENABLED:
        return None

    path = request.url.path
    ip = _client_ip(request)
    rule = _get_rule(path)
    now = time.time()
    cutoff = now - rule.window_seconds

    with _RATE_LIMIT_LOCK:
        key = f"{ip}:{path}"
        timestamps = RATE_LIMIT_STORAGE[key]

        # Clean old timestamps
        while timestamps and timestamps[0] < cutoff:
            timestamps.pop(0)

        # Check limit
        if len(timestamps) >= rule.max_requests:
            retry_after = int(timestamps[0] - cutoff)
            raise HTTPException(
                status_code=429,
                detail=f"Rate limit exceeded. Try again in {retry_after} seconds.",
                headers={"Retry-After": str(max(retry_after, 1))}
            )

        # Record this request
        timestamps.append(now)

    return None


def clear_rate_limit(ip: Optional[str] = None) -> int:
    """
    Clear rate limit data. If ip is provided, clear only that IP.
    Returns count of entries cleared.
    """
    with _RATE_LIMIT_LOCK:
        if ip is None:
            cleared = len(RATE_LIMIT_STORAGE)
            RATE_LIMIT_STORAGE.clear()
            return cleared

        keys_to_remove = [k for k in RATE_LIMIT_STORAGE if k.startswith(f"{ip}:")]
        for key in keys_to_remove:
            del RATE_LIMIT_STORAGE[key]
        return len(keys_to_remove)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Starlette middleware for automatic rate limiting."""

    async def dispatch(self, request: Request, call_next):
        # Skip rate limiting for health endpoints
        if request.url.path in ("/health", "/api/office/health"):
            return await call_next(request)

        # Check rate limit
        error = check_rate_limit(request)
        if error:
            from fastapi.responses import JSONResponse
            return JSONResponse(
                status_code=error.status_code,
                content={"detail": error.detail},
                headers={"Retry-After": error.headers.get("Retry-After", "1")}
            )

        return await call_next(request)
