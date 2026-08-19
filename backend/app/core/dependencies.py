"""
Central dependencies module — thin re-export shim.

All symbols are re-exported from:
  - app.core.config   : config constants
  - app.core.security : auth/crypto helpers
  - app.core.services.* : business utilities
"""
from __future__ import annotations

# Config constants
from app.core.config import (  # noqa: E402, F403
    SECRET_ENCRYPTION_KEY,
    FRONTEND_URL,
    JWT_SECRET,
    JWT_ALGORITHM,
    JWT_EXPIRE_HOURS,
    GOOGLE_API_KEY,
    FONNTE_WEBHOOK_SECRET,
    UPLOADS_DIR,
    ADMIN_WA,
    CORS_ORIGIN,
    CORS_LIST,
    HERMES_GATEWAY_URL,
    HERMES_GATEWAY_TOKEN,
    GOOGLE_CALENDAR_ID,
    GOOGLE_SERVICE_ACCOUNT_FILE,
    GOOGLE_SERVICE_ACCOUNT_JSON,
    USD_TO_IDR,
    SENSITIVE_SETTING_KEYS,
    LOGIN_RATE_MAX,
    LOGIN_RATE_WINDOW,
    LOGIN_LOCKOUT_SECONDS,
    PLACES_NEW_SEARCH_URL,
    IS_PRODUCTION,
    AUTH_ALLOWED_EMAIL_DOMAINS,
)

# Backward-compat alias for main.py
_cors_list = CORS_LIST

# Security / auth helpers
from app.core.security import (  # noqa: E402, F403
    encrypt_password,
    decrypt_password,
    hash_password,
    verify_password,
    create_token,
)

# DB-backed rate limiters
from app.core.services.rate_limiter import (  # noqa: E402, F403
    check_login_rate_limit,
    record_login_failure,
    record_login_success,
    check_simple_rate_limit,
)

# Backward compat: underscore-prefixed names used by routers
_check_simple_rate_limit = check_simple_rate_limit


# Settings
from app.core.services.settings_service import (  # noqa: E402, F403
    _mask_secret,
    _get_setting,
)

# Slug
from app.core.services.slug_service import (  # noqa: E402, F403
    slugify,
    generate_unique_slug,
)

# Phone
from app.core.services.phone_service import (  # noqa: E402, F403
    normalize_phone,
    normalize_phone_storage,
    make_wa_url,
)
_normalize_phone = normalize_phone  # noqa: E402  # backward compat alias

# WhatsApp
from app.core.services.whatsapp_service import (  # noqa: E402, F403
    get_fonnte_token,
    send_fonnte_message,
    _send_fonnte_sync,
)

# Cost logging
from app.core.services.cost_service import (  # noqa: E402, F403
    log_outreach_cost,
    log_ai_cost,
)

# Board sync
from app.core.services.board_sync_service import (  # noqa: E402, F403
    sync_row_to_board,
    _sync_one_card,
    _ensure_board,
    _valid_lead_id,
    _default_board_column,
    _first_present,
    sync_row_status_to_board,
)

# Google Calendar
from app.core.services.google_calendar_service import (  # noqa: E402, F403
    sync_to_google_calendar,
    _get_google_calendar_service,
    _build_google_calendar_event_body,
)

# Seed
from app.core.services.seed_service import seed_data  # noqa: E402, F403

# Scheduler
from app.core.services.scheduler_service import (  # noqa: E402, F403
    process_pending_blasts,
    scheduled_followup_processor,
    _acquire_scheduler_lock,
    _run_async_job,
)

# Subscription
from app.core.services.subscription_service import _deduct_due_subscriptions  # noqa: E402, F403

# Proposal helpers (core)
from app.core.services.proposal_service import (  # noqa: E402, F403
    generate_report_for_lead,
    _detect_service_type,
    _detect_service_types,
    _detect_service_type_from_name,
    _detect_service_type_single_lead,
    _months_between_dates,
    _detect_contract_months,
    _build_roi_data,
    _generate_fallback_analysis,
    _build_addons_from_products,
)

# ─── DB models / schemas ──────────────────────────────────────────────────────

from models import (  # noqa: E402, F403
    Base, engine, SessionLocal, get_db, log_audit,
    User, Lead, Contact, Project, Proposal, ProposalAnalytics,
    Transaction, Wallet, Subscription, PaymentMethod, AuditLog,
    Board, BoardColumn, BoardCard, BoardCardComment, BoardCardChecklist, BoardCardActivity,
    WorkspaceSheet, WorkspaceColumn, WorkspaceRow, WorkspaceCell, WorkspaceAttachment,
    DynamicTemplate, Document, DocumentFolder, DocumentTemplate, GeneratedDocument,
    ReportSnapshot, BrandKit, BrandAsset, DocumentSequence,
    ServiceItem, Category, Product,
    ClientNote, ClientCredential, ClientDocument,
    AdsCampaign, BlastCampaign, BlastMessage, FollowUpSequence, MessageTemplate,
    ScrapeHistory, LeadActivityLog, LeadAnalysis,
    AIProxy, ContentProvider, ContentSession, ContentGeneration,
    SystemSettings, AIModel, ProviderConfig, ContentSchedule,
    RateLimit,
)
from schemas import *  # noqa: E402, F403
from workspace_templates import (  # noqa: E402
    build_sheets_for_service, build_sheets_for_days,
    WORKSPACE_TEMPLATES, _BASE_COLS,
    normalize_service_type,
)

# ─── Auth / user helpers ─────────────────────────────────────────────────────

from fastapi import Depends, HTTPException, Request  # noqa: E402
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402
from typing import Optional  # noqa: E402

security = HTTPBearer(auto_error=False)


def get_current_user(
    request: Request,
    creds: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db),
) -> User:
    token = creds.credentials if creds else request.cookies.get("kt_token")
    if not token:
        raise HTTPException(status_code=401, detail="Token tidak ditemukan")
    import jwt as _jwt  # noqa: E402
    try:
        payload = _jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        user_id = int(payload["sub"])
        token_version = payload.get("v", 1)
    except Exception:
        raise HTTPException(status_code=401, detail="Token tidak valid atau kadaluarsa")
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=401, detail="User tidak ditemukan")
    # P1-4: validate token_version for revocation
    if hasattr(user, "token_version") and user.token_version != token_version:
        raise HTTPException(status_code=401, detail="Token sudah tidak valid")
    return user


def require_admin(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Akses ditolak: hanya admin")
    return current_user


# ─── Hermes helpers ───────────────────────────────────────────────────────────

def _hermes_headers() -> dict:
    return {"X-Gateway-Token": HERMES_GATEWAY_TOKEN, "Content-Type": "application/json"}


def _office_profile(profile: str) -> str:
    return "default" if profile == "friday" else profile


# ─── AI helpers ──────────────────────────────────────────────────────────────

def _get_feature_defaults(db: Session) -> dict:
    row = db.query(SystemSettings).filter_by(key="ai_feature_defaults").first()
    if row and row.value:
        try:
            import json as _json  # noqa: E402
            data = _json.loads(row.value)
            if isinstance(data, dict):
                return data
        except Exception:
            pass
    return {}


def get_proxy_for_feature(db: Session, feature: str):
    proxy = db.query(AIProxy).filter(AIProxy.feature == feature, AIProxy.is_active == True).first()
    if not proxy:
        proxy = db.query(AIProxy).filter(AIProxy.is_active == True, AIProxy.feature.is_(None)).first()
    return proxy


def get_default_model(db: Session, capability: str):
    field = f"is_default_{capability}"
    return db.query(AIModel).filter(getattr(AIModel, field) == 1, AIModel.is_active == 1).first()


def get_ai_config(db: Session, capability: str = "chat") -> dict:
    from app.services.ai_service import get_ai_config as _svc  # noqa: E402
    return _svc(db, capability)


def build_analysis_prompt(lead, product_list: str) -> str:
    # Single source of truth di ai_service (mitigasi AI halu / anti klaim-palsu).
    from app.services.ai_service import build_analysis_prompt as _svc  # noqa: E402
    return _svc(lead, product_list)


def _call_ai_sync(prompt: str, config: dict, _httpx) -> str:
    from app.services.ai_service import call_ai_sync as _call  # noqa: E402
    return _call(prompt, config, _httpx)


async def call_ai_provider(prompt: str, config: dict) -> str:
    from app.services.ai_service import call_ai_provider_async  # noqa: E402
    try:
        return await call_ai_provider_async(prompt, config)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))


def parse_ai_response(text: str) -> dict:
    import re as _re  # noqa: E402
    import json as _json  # noqa: E402
    json_match = _re.search(r'\{[\s\S]*\}', text)
    if json_match:
        try:
            return _json.loads(json_match.group())
        except Exception:
            pass
    return {"pain_points": [text], "suggested_product": "", "approach_message": ""}


# ─── Lead helpers ─────────────────────────────────────────────────────────────

def calculate_lead_score(lead):
    from app.services.scoring_service import calculate_lead_score_from_settings  # noqa: E402
    return calculate_lead_score_from_settings(lead)


def _apply_decay(score: int, breakdown: dict, lead) -> tuple[int, dict]:
    from datetime import datetime, timezone  # noqa: E402
    ref = lead.last_followup_at
    if not ref:
        return score, breakdown
    try:
        ref_dt = datetime.fromisoformat(str(ref).replace("Z", "+00:00"))
        days_since = (datetime.now(timezone.utc) - ref_dt).days
        if days_since > 30:
            weeks_over = (days_since - 30) // 7
            decay = weeks_over * 5
            if decay > 0:
                score -= decay
                breakdown[f"Decay ({days_since}d, -{decay})"] = -decay
    except Exception:
        pass
    return max(0, min(100, score)), breakdown


def calculate_lead_score_full(lead) -> tuple[int, dict]:
    score, breakdown = calculate_lead_score(lead)
    score, breakdown = _apply_decay(score, breakdown, lead)
    return score, breakdown


def _apply_proposal_signal(lead_id: int, signal_type: str, points: int, db: Session, replace_signal: Optional[str] = None) -> bool:
    import uuid as _uuid  # noqa: E402
    existing = db.query(LeadActivityLog).filter(
        LeadActivityLog.lead_id == lead_id,
        LeadActivityLog.activity_type == signal_type,
    ).first()
    if existing:
        return False
    lead = db.query(Lead).filter(Lead.id == lead_id).first()
    if not lead:
        return False
    if replace_signal:
        replaced = db.query(LeadActivityLog).filter(
            LeadActivityLog.lead_id == lead_id,
            LeadActivityLog.activity_type == replace_signal,
        ).first()
        if replaced:
            lead.lead_score = max(0, (lead.lead_score or 0) - 15)
    lead.lead_score = min(100, (lead.lead_score or 0) + points)
    db.add(LeadActivityLog(
        id=str(_uuid.uuid4()),
        lead_id=lead_id,
        activity_type=signal_type,
    ))
    db.commit()
    return True


def generate_batch_name(category: str, location: str) -> str:
    from datetime import datetime  # noqa: E402
    date_str = datetime.now().strftime("%d %b %Y")
    parts = [p for p in [category.strip(), location.strip()] if p]
    label = " - ".join(parts) if parts else "Scrape"
    return f"{label} · {date_str}"


def _detect_project_type(services: list) -> str:
    for s in services:
        if s.get("is_retainer"):
            return "RETAINER"
        name = (s.get("name") or "").lower()
        if any(k in name for k in ["bulanan", "retainer", "maintenance", "kelola", "seo"]):
            return "RETAINER"
    return "FIXED"


# ─── Model output helpers ─────────────────────────────────────────────────────

def _ai_model_to_out(m):
    import json as _json  # noqa: E402
    return {
        "id": m.id, "name": m.name, "model_id": m.model_id,
        "description": m.description,
        "capabilities": _json.loads(m.capabilities) if m.capabilities else [],
        "is_active": m.is_active,
        "is_default_chat": bool(m.is_default_chat),
        "is_default_image": bool(m.is_default_image),
        "is_default_article": bool(m.is_default_article),
        "is_default_analysis": bool(m.is_default_analysis),
    }


def _ads_out(c: AdsCampaign):
    cac = (c.budget / c.conversions_count) if c.conversions_count and c.conversions_count > 0 else None
    cpl = (c.budget / c.leads_count) if c.leads_count and c.leads_count > 0 else None
    return {
        "id": c.id, "name": c.name, "target_audience": c.target_audience,
        "budget": c.budget, "drive_link": c.drive_link,
        "leads_count": c.leads_count or 0, "conversions_count": c.conversions_count or 0,
        "status": c.status, "created_at": c.created_at, "cac": cac, "cost_per_lead": cpl,
    }


# ─── Job trackers (in-memory, process-scoped) ─────────────────────────────────

_analysis_jobs: dict = {}
_blast_jobs: dict = {}

import asyncio
search_semaphore = asyncio.Semaphore(1)

# ─── Backward-compat aliases (for routers using underscore-prefixed names) ───────
_check_login_rate_limit = check_login_rate_limit
_record_login_failure = record_login_failure
_record_login_success = record_login_success
_check_simple_rate_limit = check_simple_rate_limit
