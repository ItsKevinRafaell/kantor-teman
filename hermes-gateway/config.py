"""Environment configuration — loaded once at startup."""
import os
import hmac
from pathlib import Path

# ── Auth ────────────────────────────────────────────────────────────────────────
_GATEWAY_TOKEN_RAW = os.getenv("HERMES_GATEWAY_TOKEN")
if not _GATEWAY_TOKEN_RAW:
    raise RuntimeError("HERMES_GATEWAY_TOKEN environment variable is required")
GATEWAY_TOKEN: str = _GATEWAY_TOKEN_RAW  # intentionally not configurable for auth comparison

# ── Hermes ──────────────────────────────────────────────────────────────────────
HERMES_BIN = os.getenv("HERMES_BIN", "/usr/local/bin/hermes")
HERMES_TIMEOUT_SECONDS = int(os.getenv("HERMES_TIMEOUT_SECONDS", "900"))
HERMES_MULTI_READ_SECONDS = int(os.getenv("HERMES_MULTI_READ_SECONDS", "30"))
HERMES_HOME = Path("/root/.hermes")
PROFILES_DIR = Path("/root/.hermes/profiles")

# ── API server ports ────────────────────────────────────────────────────────────
API_SERVER_PORTS = {
    "nara": 8646,
    "rafi": 8643,
    "sena": 8644,
    "dimas": 8645,
    "mika": 8647,
    "raka": 8648,
    "tara": 8649,
}

# ── Profile aliases ─────────────────────────────────────────────────────────────
LEGACY_PROFILE_ALIASES = {
    "friday": "nara",
    "tony": "rafi",
    "banner": "dimas",
    "vision": "sena",
    "default": "nara",
    "manager": "nara",
}
LEGACY_PROFILE_DIRS = {
    "nara": "friday",
    "manager": "friday",
    "rafi": "tony",
    "dimas": "banner",
    "sena": "vision",
}
PROFILE_ALIASES = LEGACY_PROFILE_ALIASES

# ── Router (9router) ───────────────────────────────────────────────────────────
ROUTER_INTERNAL_BASE_URL = os.getenv(
    "ROUTER_INTERNAL_BASE_URL",
    os.getenv("NINE_ROUTER_INTERNAL_BASE_URL", "http://127.0.0.1:20128/v1"),
).rstrip("/")
ROUTER_EXTERNAL_BASE_URL = os.getenv(
    "ROUTER_EXTERNAL_BASE_URL",
    os.getenv("NINE_ROUTER_EXTERNAL_BASE_URL", "https://9router.kantorteman.my.id"),
).rstrip("/")
ROUTER_KEY_FILES = [
    Path("/home/kevin/.9router/auth/hermes-router-key"),
    Path("/root/.9router/auth/hermes-router-key"),
]

# ── Office auth ────────────────────────────────────────────────────────────────
OFFICE_EMAIL = os.getenv("OFFICE_EMAIL", "")
OFFICE_PASSWORD = os.getenv("OFFICE_PASSWORD", "")
OFFICE_NAME = os.getenv("OFFICE_NAME", "Admin")

# ── CORS ───────────────────────────────────────────────────────────────────────
_CORS_ORIGINS_RAW = os.getenv("CORS_ORIGINS", "")
CORS_ORIGINS: list[str] = (
    [o.strip() for o in _CORS_ORIGINS_RAW.split(",") if o.strip()]
    if _CORS_ORIGINS_RAW
    else []
)
if not CORS_ORIGINS:
    raise RuntimeError("CORS_ORIGINS environment variable is required (comma-separated)")
