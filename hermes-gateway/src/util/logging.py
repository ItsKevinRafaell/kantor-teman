"""Structured logging utilities."""
import json
import re
import time
from typing import Any

SENSITIVE_KEYS = re.compile(r"(key|token|secret|password|authorization|cookie)", re.I)


def redact(data: Any) -> Any:
    """Redact sensitive fields and Bearer tokens."""
    if isinstance(data, dict):
        return {k: ("<redacted>" if SENSITIVE_KEYS.search(str(k)) else redact(v)) for k, v in data.items()}
    if isinstance(data, list):
        return [redact(item) for item in data]
    if isinstance(data, str) and len(data) > 16 and re.search(r"(sk-|Bearer |bot[0-9]|api[_-]?key)", data, re.I):
        return "<redacted>"
    return data


def safe_serialize(obj: Any) -> str:
    """JSON serialize with redaction."""
    return json.dumps(redact(obj), ensure_ascii=False, default=str)


def log_event(event: str, **kwargs) -> None:
    """Structured log to stderr for monitoring."""
    payload = {"ts": time.time(), "event": event, **redact(kwargs)}
    import sys
    sys.stderr.write(safe_serialize(payload) + "\n")
    sys.stderr.flush()
