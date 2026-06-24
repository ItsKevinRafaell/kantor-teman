"""Hermes binary interaction — API requests to agent local servers."""
import json
import urllib.error
import urllib.request
from typing import Optional

import config
from src.services.profile_service import _api_server_url


def api_request(profile: str, path: str, method: str = "GET", payload: Optional[dict] = None) -> dict:
    """Make HTTP request to a profile's local Hermes API server."""
    from fastapi import HTTPException

    body = json.dumps(payload).encode("utf-8") if payload is not None else None
    request = urllib.request.Request(
        _api_server_url(profile, path),
        data=body,
        method=method,
        headers={
            "Authorization": f"Bearer {config.GATEWAY_TOKEN}",
            "Content-Type": "application/json",
            "X-Hermes-Session-Key": f"office-web:{profile}",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise HTTPException(status_code=exc.code, detail=detail[:500])
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Hermes gateway unavailable: {exc}")
