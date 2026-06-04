"""TTL Cache Layer — in-memory cache with decorator for polling endpoints.

Thread-safe implementation using threading.Lock for Passenger WSGI compatibility.
"""
import threading
import time
import hashlib
import json
from functools import wraps
from typing import Optional, Callable, Any

from fastapi import Request


# ─── Cache Store ─────────────────────────────────────────────────────────────

_cache: dict[str, tuple[Any, float]] = {}  # key -> (value, expires_at)
_cache_lock = threading.Lock()


def get_cache(key: str) -> tuple[bool, Any]:
    """Return (hit, value). Thread-safe read."""
    with _cache_lock:
        entry = _cache.get(key)
        if entry is None:
            return False, None
        value, expires_at = entry
        if time.time() > expires_at:
            del _cache[key]
            return False, None
        return True, value


def set_cache(key: str, value: Any, ttl_seconds: int = 60) -> None:
    """Store value with TTL. Thread-safe write."""
    with _cache_lock:
        _cache[key] = (value, time.time() + ttl_seconds)


def delete_cache(key: str) -> None:
    """Delete a specific cache key. Thread-safe."""
    with _cache_lock:
        _cache.pop(key, None)


def clear_cache_prefix(prefix: str) -> int:
    """Delete all cache keys starting with prefix. Returns count deleted."""
    with _cache_lock:
        keys_to_delete = [k for k in _cache if k.startswith(prefix)]
        for k in keys_to_delete:
            del _cache[k]
        return len(keys_to_delete)


def get_cache_stats() -> dict:
    """Return cache stats for monitoring."""
    with _cache_lock:
        now = time.time()
        total = len(_cache)
        expired = sum(1 for _, exp in _cache.values() if exp < now)
        return {"total_entries": total, "expired_entries": expired}


# ─── Cache Key Builders ───────────────────────────────────────────────────────

def make_cache_key(*parts: str) -> str:
    """Build a cache key from parts, hashed if too long."""
    raw = ":".join(str(p) for p in parts)
    if len(raw) > 200:
        h = hashlib.md5(raw.encode()).hexdigest()[:16]
        return f"cache:{h}"
    return f"cache:{raw}"


def make_request_cache_key(
    request: Request,
    *extra: str,
) -> str:
    """Build a cache key from request path + query params + extra parts."""
    path = request.url.path
    query = str(request.url.query)
    return make_cache_key(path, query, *extra)


# ─── Decorator ───────────────────────────────────────────────────────────────

def cached(
    ttl_seconds: int = 60,
    key_func: Optional[Callable[[Request], str]] = None,
    skip_on_header: Optional[str] = None,
):
    """
    Decorator that caches FastAPI endpoint responses.

    Args:
        ttl_seconds: TTL in seconds (default 60).
        key_func: Optional function (Request) -> str for custom cache key.
        skip_on_header: Skip cache if this header is present with any value.

    Usage:
        @router.get("/api/finance/transactions")
        @cached(ttl_seconds=60, key_func=lambda r: f"txn:{r.url.query}")
        def get_transactions(...):
            ...
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            # Extract request from kwargs or last positional arg
            request: Optional[Request] = None
            if key_func:
                for v in list(kwargs.values()) + list(args):
                    if isinstance(v, Request):
                        request = v
                        break
            elif args:
                for v in args:
                    if isinstance(v, Request):
                        request = v
                        break

            # Check skip header
            if skip_on_header and request:
                if request.headers.get(skip_on_header):
                    return func(*args, **kwargs)

            # Build cache key
            if key_func and request:
                cache_key = key_func(request)
            elif request:
                cache_key = make_request_cache_key(request)
            else:
                # Fallback: use function name + args as key
                key_data = f"{func.__name__}:{str(args)}:{str(kwargs)}"
                cache_key = make_cache_key(key_data)

            # Try cache hit
            hit, value = get_cache(cache_key)
            if hit:
                return value

            # Execute function
            result = func(*args, **kwargs)

            # Cache result (don't cache None)
            if result is not None:
                set_cache(cache_key, result, ttl_seconds)

            return result

        return wrapper
    return decorator


def cached_simple(key: str, ttl_seconds: int = 60):
    """
    Simple decorator for functions with explicit cache key.
    No request object needed.
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            hit, value = get_cache(key)
            if hit:
                return value
            result = func(*args, **kwargs)
            if result is not None:
                set_cache(key, result, ttl_seconds)
            return result
        return wrapper
    return decorator


# ─── Manual Cache Operations ──────────────────────────────────────────────────

def invalidate_finance_cache() -> None:
    """Invalidate all finance-related cache entries."""
    clear_cache_prefix("cache:/api/finance")


def invalidate_workspace_cache() -> None:
    """Invalidate all workspace-related cache entries."""
    clear_cache_prefix("cache:/api/workspace")


def invalidate_transaction_cache(wallet_id: Optional[int] = None) -> None:
    """Invalidate transaction cache. If wallet_id provided, invalidate that specific key."""
    if wallet_id:
        # These will expire naturally with TTL, but we can force clear specific patterns
        delete_cache(f"cache:/api/finance/transactions?wallet_id={wallet_id}")
    # Always clear general transaction cache
    clear_cache_prefix("cache:/api/finance/transactions")


def invalidate_workspace_list_cache() -> None:
    """Invalidate workspace list cache."""
    delete_cache("cache:/api/workspace-list")