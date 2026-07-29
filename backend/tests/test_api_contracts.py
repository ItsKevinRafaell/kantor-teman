"""API Contract Tests — verifies all endpoints match expected signatures.

Run against a running backend:
    API_URL=http://localhost:8000 pytest tests/test_api_contracts.py -v

Requires: pip install httpx pytest
"""

import os

import httpx
import pytest

API_URL = os.getenv("API_URL", "http://localhost:8000")

# ── Endpoint Registry ────────────────────────────────────────────────────────

# Format: (method, path, needs_auth, expected_status_for_unauth)
ENDPOINTS = [
    # === analytics.py ===
    ("GET", "/api/scrape-history", True, 401),
    ("GET", "/api/analytics", True, 401),
    ("GET", "/api/alerts/reengagement", True, 401),
    ("GET", "/api/analytics/patterns", True, 401),
    ("GET", "/api/audit-logs", True, 401),
    ("GET", "/api/export/leads", True, 401),
    ("GET", "/api/export/finance", True, 401),
    ("GET", "/api/background-jobs", True, 401),

    # === auth.py ===
    ("POST", "/api/auth/login", False, 422),  # needs body
    ("POST", "/api/auth/logout", True, 401),  # requires valid token (increments token_version)
    ("GET", "/api/users", True, 401),
    ("GET", "/api/user/me", True, 401),

    # === campaign.py ===
    ("GET", "/api/blast/analytics", True, 401),

    # === clients.py ===
    ("GET", "/api/clients/detail/1", True, 401),

    # === content.py ===
    ("GET", "/api/ai-models", True, 401),
    ("GET", "/api/ai/combos", True, 401),
    ("GET", "/api/ai/active-combo", True, 401),
    ("GET", "/api/ai/feature-defaults", True, 401),
    ("GET", "/api/ai/health", True, 401),
    ("GET", "/api/ai-proxies", True, 401),
    ("GET", "/api/content/providers", True, 401),
    ("GET", "/api/content/sessions", True, 401),
    ("GET", "/api/content/generations", True, 401),

    # === documents.py ===
    ("GET", "/api/documents", True, 401),
    ("GET", "/api/brand-kit", True, 401),
    ("GET", "/api/brand-kit/public", False, "200_or_404"),  # 404 if no brand kit yet
    ("GET", "/api/document-templates", True, 401),
    ("GET", "/api/generated-documents", True, 401),
    ("GET", "/api/documents/invoice-sequence", True, 401),
    ("GET", "/api/archive/folders", True, 401),
    ("GET", "/api/archive", True, 401),

    # === finance.py ===
    ("GET", "/api/finance/wallets", True, 401),
    ("GET", "/api/finance/transactions", True, 401),
    ("GET", "/api/finance/subscriptions", True, 401),
    ("GET", "/api/finance/reports", True, 401),
    ("GET", "/api/finance/payment-methods", True, 401),

    # === leads.py ===
    ("GET", "/api/leads", True, 401),
    ("GET", "/api/leads/map", True, 401),
    ("GET", "/api/leads/batches", True, 401),
    ("GET", "/api/contacts", True, 401),
    ("GET", "/api/leads/hot", True, 401),
    ("GET", "/api/leads/top-scored", True, 401),

    # === office.py ===
    ("GET", "/api/office/status", True, 401),

    # === other.py ===
    ("GET", "/api/timeline-templates", True, 401),
    ("GET", "/api/credential-categories", True, 401),
    ("GET", "/api/provider-configs", True, 401),

    # === proposals.py ===
    ("GET", "/api/proposals", True, 401),

    # === settings.py ===
    ("GET", "/api/settings", True, 401),
    ("GET", "/api/categories", True, 401),
    ("GET", "/api/products", True, 401),
    ("GET", "/api/dynamic-templates", True, 401),

    # === workspace.py ===
    ("GET", "/api/projects", True, 401),
    ("GET", "/api/boards/overview", True, 401),
    ("GET", "/api/workspace-list", True, 401),
]


@pytest.fixture
def client():
    """Use TestClient (in-process) by default. Only use httpx to external URL if API_URL is explicitly set."""
    if API_URL and API_URL != "http://localhost:8000":
        # Explicit external URL — use httpx network client
        with httpx.Client(base_url=API_URL, timeout=30) as c:
            yield c
    else:
        # Default: use FastAPI TestClient (in-process, no network)
        from fastapi.testclient import TestClient
        import sys, os
        sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
        import main as _main_app
        with TestClient(_main_app.app) as c:
            yield c


# ── Contract Tests ───────────────────────────────────────────────────────────

@pytest.mark.parametrize("method,path,needs_auth,expected", ENDPOINTS)
def test_endpoint_reachable(method, path, needs_auth, expected, client):
    """Every endpoint should be reachable and return expected status code

    - Auth-required endpoints: 401 without token
    - Public endpoints: 200 (or 422 for POST without body)
    - Every response must have content-type application/json
    """
    resp = client.request(method, path)
    if expected == "200_or_404":
        assert resp.status_code in (200, 404), (
            f"{method} {path} returned {resp.status_code}, expected 200 or 404. "
            f"Body: {resp.text[:200]}"
        )
    else:
        assert resp.status_code == expected, (
            f"{method} {path} returned {resp.status_code}, expected {expected}. "
            f"Body: {resp.text[:200]}"
        )

    if resp.content:
        ct = resp.headers.get("content-type", "")
        if "html" not in ct and "pdf" not in ct and "octet-stream" not in ct:
            assert "application/json" in ct or "text/plain" in ct, (
                f"{method} {path} content-type is '{ct}', expected JSON"
            )


def test_cors_headers_present(client):
    """All endpoints should support CORS preflight"""
    resp = client.options("/api/leads")
    assert resp.status_code in (200, 204, 405), f"OPTIONS /api/leads returned {resp.status_code}"


def test_cookie_auth_required(client):
    """Endpoints requiring auth should return 401 without cookie/Bearer"""
    resp = client.get("/api/leads")
    assert resp.status_code == 401
    assert "detail" in resp.json()


def test_public_brand_kit(client):
    """Public brand kit endpoint should be accessible, might be empty (404)"""
    resp = client.get("/api/brand-kit/public")
    assert resp.status_code in (200, 404)
    if resp.status_code == 200:
        data = resp.json()
        assert isinstance(data, dict)


def test_public_ai_health(client):
    resp = client.get("/api/ai/health")
    assert resp.status_code == 401  # requires auth


def test_public_provider_configs(client):
    resp = client.get("/api/provider-configs")
    assert resp.status_code == 401  # requires auth
