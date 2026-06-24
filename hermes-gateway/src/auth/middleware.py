"""Authentication middleware — timing-safe token comparison."""
import hmac
from typing import Optional

from fastapi import HTTPException, Request, Security
from fastapi.security import APIKeyHeader, HTTPAuthorizationCredentials, HTTPBearer

import config

api_key_header = APIKeyHeader(name="X-Gateway-Token", auto_error=False)
bearer_scheme = HTTPBearer(auto_error=False)


def verify_auth(
    request: Request,
    key: Optional[str] = Security(api_key_header),
    bearer: Optional[HTTPAuthorizationCredentials] = Security(bearer_scheme),
) -> str:
    """Verify bearer token using constant-time comparison to prevent timing attacks."""
    token = key or (bearer.credentials if bearer else None)
    if not token:
        raise HTTPException(status_code=401, detail="Unauthorized")
    # Use hmac.compare_digest for timing-safe comparison
    if hmac.compare_digest(token, config.GATEWAY_TOKEN):
        return token
    raise HTTPException(status_code=401, detail="Unauthorized")
