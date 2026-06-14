"""
Central dependencies module — single import source for all routers.
Consolidates config, security, database, and all shared business utilities.
"""
import re
import os
import json
import uuid
import time
import random
import asyncio
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Optional, List, Any

import httpx
import jwt as _jwt
import bcrypt as _bcrypt
from cryptography.fernet import Fernet
from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session
from dotenv import load_dotenv

# ─── Config ───────────────────────────────────────────────────────────────────
_env_file = os.environ.get("ENV_FILE", ".env.production")
load_dotenv(_env_file)
load_dotenv(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".env")), override=False)

SECRET_ENCRYPTION_KEY = os.environ["SECRET_ENCRYPTION_KEY"]
_fernet = Fernet(SECRET_ENCRYPTION_KEY.encode())

FRONTEND_URL = os.getenv("FRONTEND_URL", "https://kantorteman.my.id")
JWT_SECRET = os.getenv("JWT_SECRET")
if not JWT_SECRET or len(JWT_SECRET) < 16:
    raise RuntimeError("JWT_SECRET env var is required (min 16 chars)")
JWT_ALGORITHM = "HS256"
JWT_EXPIRE_HOURS = 24
GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY")
FONNTE_WEBHOOK_SECRET = os.environ.get("FONNTE_WEBHOOK_SECRET", "")
UPLOADS_DIR = os.path.join(os.path.dirname(__file__), "..", "uploads")
os.makedirs(UPLOADS_DIR, exist_ok=True)
ADMIN_WA = os.getenv("ADMIN_WA", "6281234567890")

# CORS
_DEFAULT_CORS = "https://kantorteman.my.id,https://www.kantorteman.my.id,https://office.kantorteman.my.id,https://office-kantor-teman.vercel.app,http://localhost:3000,http://localhost:3001,http://localhost:3002"
CORS_ORIGIN = os.getenv("CORS_ORIGIN", _DEFAULT_CORS)
_cors_list = [o.strip() for o in CORS_ORIGIN.split(",") if o.strip()]

# Hermes Gateway
HERMES_GATEWAY_URL = os.getenv("HERMES_GATEWAY_URL", "")
HERMES_GATEWAY_TOKEN = os.getenv("HERMES_GATEWAY_TOKEN", "")

# Google Calendar
GOOGLE_CALENDAR_ID = os.getenv("GOOGLE_CALENDAR_ID", "primary")
GOOGLE_SERVICE_ACCOUNT_FILE = os.getenv("GOOGLE_SERVICE_ACCOUNT_FILE", "")
GOOGLE_SERVICE_ACCOUNT_JSON = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON", "")

USD_TO_IDR = 17000

SENSITIVE_SETTING_KEYS = {
    "fonnte_token", "gemini_api_key", "claude_api_key", "openai_api_key",
    "ai_api_key", "google_api_key", "google_service_account_json",
    "cms_api_token", "external_lead_api_key", "smtp_password",
    "waha_api_key", "waha_webhook_secret", "autolead_api_key",
}

# ─── Database ─────────────────────────────────────────────────────────────────
from models import (  # noqa: E402
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
)
from schemas import *  # noqa: E402, F403
from workspace_templates import (  # noqa: E402
    build_sheets_for_service, build_sheets_for_days,
    WORKSPACE_TEMPLATES, _BASE_COLS,
)

# ─── Encryption ───────────────────────────────────────────────────────────────

def encrypt_password(plain: str) -> str:
    return _fernet.encrypt(plain.encode()).decode()

def decrypt_password(encrypted: str) -> str:
    return _fernet.decrypt(encrypted.encode()).decode()

# ─── Auth / bcrypt ────────────────────────────────────────────────────────────

def hash_password(plain: str) -> str:
    return _bcrypt.hashpw(plain.encode(), _bcrypt.gensalt()).decode()

def verify_password(plain: str, hashed: str) -> bool:
    return _bcrypt.checkpw(plain.encode(), hashed.encode())

# ─── JWT ──────────────────────────────────────────────────────────────────────

def create_token(user_id: int, email: str) -> str:
    payload = {
        "sub": str(user_id),
        "email": email,
        "exp": datetime.now(timezone.utc) + timedelta(hours=JWT_EXPIRE_HOURS),
    }
    return _jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

def get_current_user(
    request: Request,
    creds: Optional[HTTPAuthorizationCredentials] = Depends(HTTPBearer(auto_error=False)),
    db: Session = Depends(get_db),
) -> User:
    token = creds.credentials if creds else request.cookies.get("kt_token")
    if not token:
        raise HTTPException(status_code=401, detail="Token tidak ditemukan")
    try:
        payload = _jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        user_id = int(payload["sub"])
    except Exception:
        raise HTTPException(status_code=401, detail="Token tidak valid atau kadaluarsa")
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=401, detail="User tidak ditemukan")
    return user

def require_admin(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Akses ditolak: hanya admin")
    return current_user

# ─── Login Rate Limiter ───────────────────────────────────────────────────────

LOGIN_RATE_MAX = 5
LOGIN_RATE_WINDOW = 300
LOGIN_LOCKOUT_SECONDS = 900
_login_attempts: dict[str, list[float]] = defaultdict(list)
_login_locked_until: dict[str, float] = {}

def _check_login_rate_limit(ip: str):
    now = time.time()
    locked_until = _login_locked_until.get(ip)
    if locked_until and locked_until > now:
        retry = int(locked_until - now)
        raise HTTPException(
            status_code=429,
            detail=f"Terlalu banyak percobaan login. Coba lagi dalam {retry} detik.",
            headers={"Retry-After": str(retry)},
        )
    if locked_until and locked_until <= now:
        _login_locked_until.pop(ip, None)
        _login_attempts.pop(ip, None)

def _record_login_failure(ip: str):
    now = time.time()
    attempts = [t for t in _login_attempts[ip] if now - t < LOGIN_RATE_WINDOW]
    attempts.append(now)
    _login_attempts[ip] = attempts
    if len(attempts) >= LOGIN_RATE_MAX:
        _login_locked_until[ip] = now + LOGIN_LOCKOUT_SECONDS

def _record_login_success(ip: str):
    _login_attempts.pop(ip, None)
    _login_locked_until.pop(ip, None)

# ─── Generic Rate Limiter ─────────────────────────────────────────────────────

_rate_buckets: dict[str, list[float]] = defaultdict(list)

def _check_simple_rate_limit(key: str, max_requests: int, window_seconds: int):
    now = time.time()
    bucket = [t for t in _rate_buckets[key] if now - t < window_seconds]
    if len(bucket) >= max_requests:
        retry = int(window_seconds - (now - bucket[0]))
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit tercapai. Coba lagi dalam {retry} detik.",
            headers={"Retry-After": str(max(retry, 1))},
        )
    bucket.append(now)
    _rate_buckets[key] = bucket

search_semaphore = asyncio.Semaphore(1)

# ─── Settings helpers ─────────────────────────────────────────────────────────

def _mask_secret(value: str) -> str:
    if not value:
        return ""
    if len(value) <= 4:
        return "****"
    return "****" + value[-4:]

def _get_setting(key: str, default: str = "") -> str:
    db = SessionLocal()
    try:
        row = db.query(SystemSettings).filter_by(key=key).first()
        return row.value if row and row.value else default
    finally:
        db.close()

# ─── Slug helpers ─────────────────────────────────────────────────────────────

def slugify(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(
        r'[\U0001F600-\U0001F64F\U0001F300-\U0001F5FF\U0001F680-\U0001F6FF'
        r'\U0001F1E0-\U0001F1FF\U00002700-\U000027BF\U0001F900-\U0001F9FF'
        r'\U0001FA00-\U0001FA6F\U0001FA70-\U0001FAFF\U00002600-\U000026FF'
        r'\U0000FE00-\U0000FE0F\U0000200D]+', '', text)
    text = re.sub(r'[\s._/]+', '-', text)
    text = re.sub(r'[^\w-]', '', text)
    text = re.sub(r'-+', '-', text)
    return text.strip('-')

def generate_unique_slug(db: Session, base_text: str) -> str:
    slug = slugify(base_text)
    if not slug:
        slug = "proposal"
    existing = db.query(Proposal).filter(Proposal.slug == slug).first()
    if not existing:
        return slug
    counter = 1
    while True:
        candidate = f"{slug}-{counter}"
        if not db.query(Proposal).filter(Proposal.slug == candidate).first():
            return candidate
        counter += 1

# ─── Phone helpers ────────────────────────────────────────────────────────────

def normalize_phone(phone: str) -> Optional[str]:
    """Normalize to 62xx format (for WA API)."""
    if not phone:
        return None
    raw = str(phone).strip()
    digits = re.sub(r"\D", "", raw)
    if not digits:
        return None
    if digits.startswith("0"):
        digits = "62" + digits[1:]
    elif not digits.startswith("62"):
        digits = "62" + digits
    return digits

def normalize_phone_storage(phone: str) -> Optional[str]:
    """Normalize to 08xx format (for storage in DB)."""
    if not phone:
        return None
    raw = str(phone).strip()
    digits = re.sub(r"\D", "", raw)
    if not digits:
        return None
    # Convert 62xx to 08xx
    if digits.startswith("62"):
        digits = "0" + digits[2:]
    elif not digits.startswith("0"):
        digits = "0" + digits
    return digits

_normalize_phone = normalize_phone

def make_wa_url(phone_digits: str) -> str:
    return f"https://wa.me/{phone_digits}"

# ─── Lead scoring ─────────────────────────────────────────────────────────────

def calculate_lead_score(lead) -> tuple[int, dict]:
    from app.services.scoring_service import calculate_lead_score_from_settings
    return calculate_lead_score_from_settings(lead)

def _apply_decay(score: int, breakdown: dict, lead) -> tuple[int, dict]:
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
        id=str(uuid.uuid4()),
        lead_id=lead_id,
        activity_type=signal_type,
    ))
    db.commit()
    return True

def generate_batch_name(category: str, location: str) -> str:
    date_str = datetime.now().strftime("%d %b %Y")
    parts = [p for p in [category.strip(), location.strip()] if p]
    label = " - ".join(parts) if parts else "Scrape"
    return f"{label} · {date_str}"

# ─── Report generation ────────────────────────────────────────────────────────

def _generate_fallback_analysis(lead) -> dict:
    pain_points = []
    category = (lead.product_interest or "bisnis").lower()
    if lead.rating and lead.rating < 4:
        pain_points.append(f"Rating Google Maps {lead.business_name} saat ini hanya {lead.rating}/5 — calon pelanggan cenderung skip bisnis dengan rating di bawah 4.0 dan langsung pilih kompetitor.")
    elif not lead.rating or lead.rating == 0:
        pain_points.append(f"{lead.business_name} belum memiliki rating yang cukup di Google Maps — ini membuat calon pelanggan ragu dan memilih kompetitor yang sudah punya banyak review positif.")
    pain_points.append(f"Saat calon pelanggan mencari '{category}' di Google, bisnis tanpa optimasi digital akan tenggelam di halaman belakang — artinya ratusan calon pelanggan potensial setiap bulan tidak pernah tahu {lead.business_name} ada.")
    city = ""
    if lead.address:
        city = lead.address.split(",")[-1].strip() if "," in (lead.address or "") else lead.address
    if city:
        pain_points.append(f"Kompetitor di area {city} yang sudah teroptimasi secara digital sedang mengambil pelanggan yang seharusnya milik Anda setiap harinya — dan gap ini semakin lebar setiap bulan yang berlalu.")
    else:
        pain_points.append("Tanpa kehadiran digital yang kuat, bisnis Anda kehilangan peluang dari pelanggan yang mencari layanan Anda secara online setiap hari.")
    return {
        "analysis": f"Berdasarkan audit digital yang kami lakukan terhadap {lead.business_name}, kami menemukan beberapa area kritis yang perlu segera ditangani untuk mencegah kehilangan pelanggan potensial ke kompetitor.",
        "pain_points": pain_points,
        "suggested_product": lead.product_interest or "SEO & Google Maps Optimization",
    }

def _build_addons_from_products(db: Session) -> str:
    products = db.query(Product).filter(Product.is_active == True).all()
    addons = [{"id": p.id, "name": p.name, "price": p.base_price} for p in products]
    return json.dumps(addons)

def generate_report_for_lead(lead, db: Session, product_category: str = None) -> str:
    category = product_category or lead.product_interest or ""
    existing_reports = db.query(Proposal).filter(
        Proposal.lead_id == lead.id,
        Proposal.status == "Report",
    ).order_by(Proposal.created_at.desc()).all()
    for r in existing_reports:
        try:
            services = json.loads(r.services_detail) if r.services_detail else []
            report_products = " ".join(s.get("name", "") for s in services).lower()
            if category.lower() in report_products:
                return r.slug
        except Exception:
            pass
    if existing_reports and not product_category:
        return existing_reports[0].slug
    existing_analysis = db.query(LeadAnalysis).filter(LeadAnalysis.lead_id == lead.id).order_by(LeadAnalysis.id.desc()).first()
    if existing_analysis:
        analysis = existing_analysis
    else:
        fallback = _generate_fallback_analysis(lead)
        analysis = LeadAnalysis(
            lead_id=lead.id,
            analysis=fallback["analysis"],
            pain_points=json.dumps(fallback["pain_points"]),
            suggested_product=fallback["suggested_product"],
            analyzed_at=datetime.now(timezone.utc).isoformat(),
        )
        db.add(analysis)
        db.commit()
    products = db.query(Product).filter(Product.is_active == True).all()
    cat_lower = category.lower()
    matched_products = [p for p in products if cat_lower and cat_lower in (p.name or "").lower()] if cat_lower else []
    if not matched_products:
        matched_products = products[:3] if products else []
    services = [{"name": p.name, "price": p.base_price, "features": (p.description or "").split("\n")} for p in matched_products[:3]] if matched_products else [{"name": "SEO & Google Maps", "price": 0, "features": ["Optimasi ranking Google", "Setup Google Business Profile"]}]
    slug = generate_unique_slug(db, lead.business_name)
    report = Proposal(
        id=str(uuid.uuid4()),
        lead_id=lead.id,
        services_detail=json.dumps(services),
        total_price=sum(s["price"] for s in services),
        base_price=sum(s["price"] for s in services),
        discount_price=round(sum(s["price"] for s in services) * (1 - float(_get_setting("proposal_discount_percent", "15")) / 100)),
        discount_expires_at=None,
        additional_options=None,
        status="Report",
        created_at=datetime.now(timezone.utc).isoformat(),
        slug=slug,
        faqs=json.dumps([
            {"question": "Apakah audit ini gratis?", "answer": "Ya, audit digital ini 100% gratis dan tanpa kewajiban apapun. Kami ingin Anda melihat sendiri peluang yang selama ini terlewat."},
            {"question": "Berapa lama sampai terlihat hasilnya?", "answer": "Dengan optimasi yang tepat, peningkatan visibilitas di Google bisa terlihat dalam 14-30 hari kerja pertama."},
            {"question": "Apa bedanya dengan jasa SEO lain?", "answer": "Kami fokus pada hasil terukur — ranking naik, telepon masuk bertambah, dan pelanggan baru datang. Bukan sekadar laporan teknis yang membingungkan."},
        ]),
        selected_addons=_build_addons_from_products(db),
        timeline_data=None,
    )
    db.add(report)
    db.commit()
    return slug

# ─── Cost logging ─────────────────────────────────────────────────────────────

def log_outreach_cost(db: Session, campaign_id: str, messages_count: int):
    from app.core.whatsapp_provider import get_whatsapp_cost_provider_id

    provider = db.query(ProviderConfig).filter_by(id=get_whatsapp_cost_provider_id(db)).first()
    if not provider:
        return
    cost = provider.price_per_unit_idr * messages_count
    provider.remaining_quota = max(0, (provider.remaining_quota or 0) - messages_count)
    campaign = db.query(BlastCampaign).filter_by(id=campaign_id).first()
    if campaign:
        campaign.total_operational_cost_idr = (campaign.total_operational_cost_idr or 0) + cost
    db.commit()

def log_ai_cost(db: Session, campaign_id: str | None, model_name: str, input_tokens: int, output_tokens: int):
    provider_map = {"gemini": "GEMINI", "claude": "CLAUDE", "anthropic": "CLAUDE", "openai": "OPENAI"}
    provider_id = provider_map.get(model_name, model_name.upper())
    provider = db.query(ProviderConfig).filter_by(id=provider_id).first()
    if not provider:
        return
    cost_usd = (provider.price_input_token_usd * input_tokens / 1000) + (provider.price_output_token_usd * output_tokens / 1000)
    cost_idr = cost_usd * USD_TO_IDR
    provider.remaining_quota = (provider.remaining_quota or 0) + cost_idr
    if campaign_id:
        campaign = db.query(BlastCampaign).filter_by(id=campaign_id).first()
        if campaign:
            campaign.total_operational_cost_idr = (campaign.total_operational_cost_idr or 0) + cost_idr
    db.commit()

# ─── Fonnte helpers ──────────────────────────────────────────────────────────

def get_fonnte_token(db: Session) -> str:
    row = db.query(SystemSettings).filter_by(key="fonnte_token").first()
    return (row.value or "") if row else ""

async def send_fonnte_message(phone: str, message: str, token: str) -> bool:
    if not token:
        return False
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(
                "https://api.fonnte.com/send",
                headers={"Authorization": token},
                data={"target": phone, "message": message, "delay": "5"},
            )
            return resp.status_code == 200
    except Exception:
        return False

def _send_fonnte_sync(phone: str, message: str, token: str, _httpx) -> bool:
    if not token:
        return False
    try:
        with _httpx.Client(timeout=15) as client:
            resp = client.post(
                "https://api.fonnte.com/send",
                headers={"Authorization": token},
                data={"target": phone, "message": message, "delay": "5"},
            )
            return resp.status_code == 200 and resp.json().get("status") != False
    except Exception as e:
        print(f"[FONNTE ERROR] {e}", flush=True)
        return False

# ─── AI Config ────────────────────────────────────────────────────────────────

def _get_feature_defaults(db: Session) -> dict:
    row = db.query(SystemSettings).filter_by(key="ai_feature_defaults").first()
    if row and row.value:
        try:
            data = json.loads(row.value)
            if isinstance(data, dict):
                return data
        except Exception:
            pass
    return {}

def get_proxy_for_feature(db: Session, feature: str) -> Optional[AIProxy]:
    proxy = db.query(AIProxy).filter(AIProxy.feature == feature, AIProxy.is_active == True).first()
    if not proxy:
        proxy = db.query(AIProxy).filter(AIProxy.is_active == True, AIProxy.feature.is_(None)).first()
    return proxy

def get_default_model(db: Session, capability: str) -> Optional[AIModel]:
    field = f"is_default_{capability}"
    return db.query(AIModel).filter(getattr(AIModel, field) == 1, AIModel.is_active == 1).first()

def get_ai_config(db: Session, capability: str = "chat") -> dict:
    """Single source of truth: every AI feature resolves to 9router."""
    from app.services.ai_service import get_ai_config as _service_get_ai_config
    return _service_get_ai_config(db, capability)

def build_analysis_prompt(lead, product_list: str) -> str:
    return f"""Kamu adalah konsultan digital marketing untuk UMKM Indonesia. Analisa bisnis berikut dan berikan insight yang persuasif dan mudah dipahami pemilik usaha.

DATA BISNIS:
- Nama: {lead.business_name}
- Alamat: {lead.address or 'Tidak diketahui'}
- Rating Google: {lead.rating}/5
- Kategori: {lead.product_interest or 'Umum'}

PRODUK/LAYANAN YANG KAMI TAWARKAN:
{product_list}

INSTRUKSI:
Berikan output dalam format JSON berikut (Bahasa Indonesia, gaya bicara santai tapi profesional):
{{
  "pain_points": ["masalah 1 yang spesifik dan relatable untuk pemilik usaha", "masalah 2", "masalah 3"],
  "suggested_product": "nama produk kami yang paling cocok",
  "approach_message": "satu paragraf pendek pesan WA yang bisa langsung dikirim ke pemilik bisnis ini, persuasif tapi tidak memaksa, sebutkan masalah mereka dan solusi kita"
}}

PENTING: Pain points harus spesifik ke bisnis ini, bukan generik. Pesan pendekatan harus terasa personal."""

def _call_ai_sync(prompt: str, config: dict, _httpx) -> str:
    """Synchronous AI call — delegates to ai_service (single canonical path)."""
    from app.services.ai_service import call_ai_sync as _call
    return _call(prompt, config, _httpx)

async def call_ai_provider(prompt: str, config: dict) -> str:
    """Async AI call — delegates to ai_service.call_ai_provider_async (single canonical path)."""
    from app.services.ai_service import call_ai_provider_async
    try:
        return await call_ai_provider_async(prompt, config)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))

def parse_ai_response(text: str) -> dict:
    json_match = re.search(r'\{[\s\S]*\}', text)
    if json_match:
        try:
            return json.loads(json_match.group())
        except Exception:
            pass
    return {"pain_points": [text], "suggested_product": "", "approach_message": ""}

# ─── Proposal helpers ─────────────────────────────────────────────────────────

def _detect_project_type(services: list) -> str:
    for s in services:
        if s.get("is_retainer"):
            return "RETAINER"
        name = (s.get("name") or "").lower()
        if any(k in name for k in ["bulanan", "retainer", "maintenance", "kelola", "seo"]):
            return "RETAINER"
    return "FIXED"

def _detect_service_type(services: list) -> Optional[str]:
    for s in services:
        name = (s.get("name") or "").lower()
        if "web" in name or "website" in name or "landing page" in name or "company profile" in name:
            return "web_dev_bulanan" if "bulanan" in name else "web_dev"
        if any(k in name for k in ["seo", "google maps", "gmaps", "google business"]):
            return "seo_gmaps"
        if any(k in name for k in ["sosial media", "sosmed", "kelola", "instagram", "tiktok", "facebook"]):
            return "sosmed"
        if "maintenance" in name:
            return "maintenance"
        if any(k in name for k in ["logo", "branding", "desain", "identitas visual"]):
            return "branding"
    return None

def _months_between_dates(start_date: Optional[str], end_date: Optional[str]) -> Optional[int]:
    if not start_date or not end_date:
        return None
    try:
        from datetime import date as _date
        s = _date.fromisoformat(start_date[:10])
        e = _date.fromisoformat(end_date[:10])
        days = (e - s).days
        if days <= 0:
            return None
        return max(1, round(days / 30))
    except Exception:
        return None

def _detect_contract_months(proposal, services: list, project_start: Optional[str] = None, project_end: Optional[str] = None) -> int:
    months = _months_between_dates(project_start, project_end)
    if months:
        return months
    if proposal.roi_data:
        try:
            roi = json.loads(proposal.roi_data) if isinstance(proposal.roi_data, str) else proposal.roi_data
            if roi.get("retainer_period"):
                return int(roi["retainer_period"])
            if roi.get("comparison_period"):
                return int(roi["comparison_period"])
        except Exception:
            pass
    if proposal.timeline_data:
        try:
            tl = json.loads(proposal.timeline_data) if isinstance(proposal.timeline_data, str) else proposal.timeline_data
            if tl:
                return max(1, len(tl))
        except Exception:
            pass
    for s in services:
        name = (s.get("name") or "").lower()
        if "seo" in name or "sosmed" in name or "kelola" in name:
            return 6
        if "maintenance" in name:
            return 1
    return 2

def _build_roi_data(db: Session, services: list, roi_input: dict = None) -> str:
    if not roi_input or not roi_input.get("enabled", True):
        return json.dumps({"enabled": False})
    retainer_period = roi_input.get("retainer_period", 0)
    service_names = [s.get("name", "").lower() for s in services]
    products = db.query(Product).filter(Product.is_active == True).all()
    matched = [p for p in products if any(p.name.lower() in sn or sn in p.name.lower() for sn in service_names)]
    if not matched:
        matched = products[:3] if products else []
    if not matched:
        return json.dumps({"enabled": True, "monthly_ads_cost": 5000000, "roi_months": 3, "roi_multiplier": 3.5, "has_retainer": False, "retainer_period": 0})
    has_retainer = any(p.is_retainer for p in matched)
    total_ads_cost = sum(p.monthly_ads_cost or 5000000 for p in matched)
    comparison_period = retainer_period if retainer_period > 0 else 12
    weighted_roi_months = sum((p.roi_months or 3) * (p.base_price or 1) for p in matched) / max(1, sum(p.base_price or 1 for p in matched))
    roi_months = max(1, round(weighted_roi_months))
    best_multiplier = max(p.roi_multiplier or 3.5 for p in matched)
    multiplier = round(best_multiplier + (len(matched) - 1) * 0.3, 1)
    return json.dumps({
        "enabled": True, "monthly_ads_cost": total_ads_cost,
        "roi_months": roi_months, "roi_multiplier": multiplier,
        "has_retainer": has_retainer, "retainer_period": retainer_period,
        "comparison_period": comparison_period,
    })

# ─── Board sync ───────────────────────────────────────────────────────────────

_ROW_STATUS_MAP = {"Done": "✅ Selesai", "On Track": "✅ On Track", "In Progress": "🔄 In Progress", "Pending": "⏳ Pending"}
_TITLE_KEYS = ("task_name", "task", "title", "name")
_DUE_DATE_KEYS = ("due_date", "deadline", "tanggal", "date")

def _first_present(data: dict, keys: tuple[str, ...]):
    for key in keys:
        value = data.get(key)
        if value not in (None, ""):
            return value
    return None

def _ensure_board(project: Project, db: Session) -> Optional[Board]:
    board = db.query(Board).filter(Board.project_id == project.id).first()
    if board:
        return board
    board = Board(id=str(uuid.uuid4()), project_id=project.id, color=getattr(project, "color", None) or "gray")
    db.add(board)
    db.flush()
    for idx, (name, color) in enumerate((("To Do", "gray"), ("In Progress", "slate"), ("Review", "neutral"), ("Done", "stone"))):
        db.add(BoardColumn(id=str(uuid.uuid4()), board_id=board.id, name=name, position=idx, color=color))
    db.flush()
    return board

def _valid_lead_id(lead_id: Optional[int], db: Session) -> Optional[int]:
    if not lead_id:
        return None
    return lead_id if db.query(Lead.id).filter(Lead.id == lead_id).first() else None

def _default_board_column(board: Board, db: Session, data: dict) -> Optional[BoardColumn]:
    columns = db.query(BoardColumn).filter(BoardColumn.board_id == board.id).order_by(BoardColumn.position).all()
    if not columns:
        col = BoardColumn(id=str(uuid.uuid4()), board_id=board.id, name="To Do", position=0, color="gray")
        db.add(col)
        db.flush()
        return col
    status = str(data.get("status") or "").strip().lower()
    done = data.get("done") is True
    for col in columns:
        name = col.name.lower()
        if done and "done" in name:
            return col
        if status and (name in status or status in name):
            return col
    return columns[0]

def sync_row_to_board(row_id: str, db: Session):
    row = db.query(WorkspaceRow).filter(WorkspaceRow.id == row_id).first()
    if not row:
        return
    sheet = db.query(WorkspaceSheet).filter(WorkspaceSheet.id == row.sheet_id).first()
    if not sheet or not sheet.project_id:
        return
    project = db.query(Project).filter(Project.id == sheet.project_id).first()
    if not project:
        return
    cells = db.query(WorkspaceCell).filter(WorkspaceCell.row_id == row_id).all()
    col_ids = {c.column_id for c in cells}
    cols = db.query(WorkspaceColumn).filter(WorkspaceColumn.id.in_(col_ids)).all() if col_ids else []
    col_by_id = {c.id: c for c in cols}
    data = {}
    for cell in cells:
        col = col_by_id.get(cell.column_id)
        if not col or not col.column_key:
            continue
        key = col.column_key
        if col.column_type == "checkbox":
            data[key] = cell.value_bool
        elif col.column_type == "number":
            data[key] = cell.value_number
        elif col.column_type == "date":
            data[key] = cell.value_date
        else:
            data[key] = cell.value_text
    board = _ensure_board(project, db)
    if not board:
        return
    card = None
    if row.board_card_id:
        card = db.query(BoardCard).filter(BoardCard.id == row.board_card_id).first()
    if not card:
        default_col = _default_board_column(board, db, data)
        if not default_col:
            return
        due_date = _first_present(data, _DUE_DATE_KEYS)
        card = BoardCard(
            id=str(uuid.uuid4()),
            column_id=default_col.id,
            title=str(_first_present(data, _TITLE_KEYS) or "Untitled Task"),
            due_date=str(due_date) if due_date else None,
            position=db.query(BoardCard).filter(BoardCard.column_id == default_col.id, BoardCard.is_archived == False).count(),
            lead_id=_valid_lead_id(project.lead_id, db),
            color=getattr(project, "color", None) or "gray",
        )
        db.add(card)
        db.flush()
        row.board_card_id = card.id
    _sync_one_card(card, data, db)

def _sync_one_card(card, data: dict, db: Session):
    title_overrides = _ROW_STATUS_MAP
    new_title = _first_present(data, _TITLE_KEYS)
    new_due = _first_present(data, _DUE_DATE_KEYS)
    current_col = db.query(BoardColumn).filter(BoardColumn.id == card.column_id).first()
    if not current_col:
        return
    board = db.query(Board).filter(Board.id == current_col.board_id).first()
    if not board:
        return
    board_cols = db.query(BoardColumn).filter(BoardColumn.board_id == board.id).order_by(BoardColumn.position).all()
    col_map = {c.name.lower(): c for c in board_cols}
    done_value = data.get("done")
    matched_status_col = None
    for key, val in data.items():
        keyl = key.lower()
        if keyl == "status" and val:
            status_val = str(val).strip()
            for col_name, col_obj in col_map.items():
                if col_name in status_val.lower() or status_val.lower() in col_name:
                    matched_status_col = col_obj
                    card.column_id = col_obj.id
                    break
            mapped = title_overrides.get(status_val)
            if mapped and not new_title:
                new_title = mapped
        elif keyl == "done" and val is True:
            done_col = next((col for name, col in col_map.items() if "done" in name), None)
            if done_col:
                card.column_id = done_col.id
                card.is_archived = False
        elif keyl == "done" and val is False:
            done_col = next((col for name, col in col_map.items() if "done" in name), None)
            if done_col and card.column_id == done_col.id:
                fallback_col = matched_status_col or next((col for col in board_cols if "done" not in (col.name or "").lower()), None)
                if fallback_col:
                    card.column_id = fallback_col.id
                    card.is_archived = False
    if new_title:
        card.title = str(new_title)
    if new_due:
        card.due_date = str(new_due)
    card.updated_at = datetime.now(timezone.utc).isoformat()
    db.commit()

def sync_row_status_to_board(row_id: str, db: Session):
    return sync_row_to_board(row_id, db)

# ─── Google Calendar ──────────────────────────────────────────────────────────

def _get_google_calendar_service():
    try:
        from google.oauth2 import service_account
        from googleapiclient.discovery import build
        scopes = ["https://www.googleapis.com/auth/calendar"]
        sa_json = _get_setting("google_service_account_json", GOOGLE_SERVICE_ACCOUNT_JSON)
        if sa_json:
            info = json.loads(sa_json)
            credentials = service_account.Credentials.from_service_account_info(info, scopes=scopes)
        elif GOOGLE_SERVICE_ACCOUNT_FILE and os.path.exists(GOOGLE_SERVICE_ACCOUNT_FILE):
            credentials = service_account.Credentials.from_service_account_file(GOOGLE_SERVICE_ACCOUNT_FILE, scopes=scopes)
        else:
            return None
        return build("calendar", "v3", credentials=credentials)
    except Exception:
        return None

# ─── Hermes helpers ───────────────────────────────────────────────────────────

def _hermes_headers() -> dict:
    return {"X-Gateway-Token": HERMES_GATEWAY_TOKEN, "Content-Type": "application/json"}

def _office_profile(profile: str) -> str:
    return "default" if profile == "friday" else profile

# ─── Model helpers ────────────────────────────────────────────────────────────

def _ai_model_to_out(m):
    return {
        "id": m.id, "name": m.name, "model_id": m.model_id,
        "description": m.description, "capabilities": json.loads(m.capabilities) if m.capabilities else [],
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

# ─── Seed data ────────────────────────────────────────────────────────────────

def seed_data(db: Session):
    if not db.query(User).first():
        db.add(User(name="Admin", email="admin@temanumkmkita.com", hashed_password=hash_password("admin123")))
        db.commit()
    if not db.query(SystemSettings).filter_by(key="fonnte_token").first():
        db.add(SystemSettings(key="fonnte_token", value=os.getenv("FONNTE_TOKEN", "")))
        db.commit()
    default_settings = {
        "whatsapp_provider": os.getenv("WHATSAPP_PROVIDER", "fonnte"),
        "waha_base_url": os.getenv("WAHA_BASE_URL", "http://127.0.0.1:3000"),
        "waha_api_key": os.getenv("WAHA_API_KEY", ""),
        "waha_session": os.getenv("WAHA_SESSION", "default"),
        "waha_webhook_secret": os.getenv("WAHA_WEBHOOK_SECRET", ""),
        "autolead_base_url": os.getenv("AUTOLEAD_BASE_URL", ""),
        "autolead_api_key": os.getenv("AUTOLEAD_API_KEY", ""),
        "autolead_demo": os.getenv("AUTOLEAD_DEMO", "true"),
        "whatsapp_blast_delay_seconds": os.getenv("WHATSAPP_BLAST_DELAY_SECONDS", "5"),
    }
    for key, value in default_settings.items():
        if not db.query(SystemSettings).filter_by(key=key).first():
            db.add(SystemSettings(key=key, value=value))
    db.commit()
    if not db.query(ProviderConfig).first():
        providers = [
            ProviderConfig(id="FONNTE", provider_name="Fonnte WhatsApp", remaining_quota=10000, price_per_unit_idr=6.6, price_input_token_usd=0, price_output_token_usd=0),
            ProviderConfig(id="WAHA", provider_name="WAHA WhatsApp", remaining_quota=0, price_per_unit_idr=0, price_input_token_usd=0, price_output_token_usd=0),
            ProviderConfig(id="AUTOLEAD", provider_name="AutoLead Bridge", remaining_quota=0, price_per_unit_idr=0, price_input_token_usd=0, price_output_token_usd=0),
            ProviderConfig(id="GEMINI", provider_name="Gemini 2.5 Flash", remaining_quota=0, price_per_unit_idr=0, price_input_token_usd=0.000075, price_output_token_usd=0.0003),
            ProviderConfig(id="CLAUDE", provider_name="Claude 4.5 Haiku", remaining_quota=0, price_per_unit_idr=0, price_input_token_usd=0.00025, price_output_token_usd=0.0125),
            ProviderConfig(id="OPENAI", provider_name="GPT-5", remaining_quota=0, price_per_unit_idr=0, price_input_token_usd=0.0025, price_output_token_usd=0.010),
        ]
        db.add_all(providers)
        db.commit()
    elif not db.query(ProviderConfig).filter_by(id="WAHA").first():
        db.add(ProviderConfig(id="WAHA", provider_name="WAHA WhatsApp", remaining_quota=0, price_per_unit_idr=0, price_input_token_usd=0, price_output_token_usd=0))
        db.commit()
    if not db.query(ProviderConfig).filter_by(id="AUTOLEAD").first():
        db.add(ProviderConfig(id="AUTOLEAD", provider_name="AutoLead Bridge", remaining_quota=0, price_per_unit_idr=0, price_input_token_usd=0, price_output_token_usd=0))
        db.commit()
    if not db.query(DynamicTemplate).filter_by(type="TIMELINE_TEMPLATE").first():
        timeline_templates = [
            DynamicTemplate(id="timeline-seo-lokal", name="Timeline SEO Lokal", type="TIMELINE_TEMPLATE",
                content=json.dumps([
                    {"sequence": 1, "title": "Audit & Riset Kata Kunci", "description": "Analisis kompetitor, riset kata kunci lokal bervolume tinggi, dan audit teknis website existing."},
                    {"sequence": 2, "title": "Optimasi On-Page & Teknis", "description": "Perbaikan struktur website, meta tags, schema markup, dan kecepatan loading halaman."},
                    {"sequence": 3, "title": "Setup Google Business Profile", "description": "Optimasi profil Google Maps, kategori bisnis, foto, dan informasi NAP (Name, Address, Phone)."},
                    {"sequence": 4, "title": "Content & Link Building Lokal", "description": "Pembuatan konten lokal berkualitas dan backlink dari direktori bisnis terpercaya di wilayah target."},
                    {"sequence": 5, "title": "Monitoring & Reporting", "description": "Tracking peringkat, analisis trafik organik, dan laporan performa bulanan dengan rekomendasi lanjutan."},
                ]), is_active=True, category_id=None),
            DynamicTemplate(id="timeline-web-dev", name="Timeline Web Development", type="TIMELINE_TEMPLATE",
                content=json.dumps([
                    {"sequence": 1, "title": "Discovery & Wireframe", "description": "Diskusi kebutuhan bisnis, pembuatan sitemap, wireframe UI/UX, dan approval desain awal."},
                    {"sequence": 2, "title": "Desain Visual & Prototype", "description": "Pembuatan desain high-fidelity, pemilihan color scheme, typography, dan interactive prototype."},
                    {"sequence": 3, "title": "Development Frontend & Backend", "description": "Coding halaman responsif, integrasi CMS/database, dan pengembangan fitur custom sesuai kebutuhan."},
                    {"sequence": 4, "title": "Testing & Quality Assurance", "description": "Pengujian fungsional, responsivitas, kecepatan, keamanan, dan kompatibilitas lintas browser/device."},
                    {"sequence": 5, "title": "Launch & Deployment", "description": "Migrasi ke server produksi, setup domain & SSL, konfigurasi SEO dasar, dan go-live monitoring."},
                    {"sequence": 6, "title": "Maintenance & Support", "description": "Dukungan teknis pasca-launch, backup rutin, update keamanan, dan minor revision selama 30 hari."},
                ]), is_active=True, category_id=None),
        ]
        db.add_all(timeline_templates)
        db.commit()

# ─── Scheduler helpers ──────────────────────────────────────────────────────────

def _acquire_scheduler_lock(job_name: str, ttl_seconds: int) -> bool:
    db = SessionLocal()
    try:
        key = f"scheduler_lock:{job_name}"
        now = datetime.now(timezone.utc)
        expires_at = (now + timedelta(seconds=ttl_seconds)).isoformat()
        updated = db.query(SystemSettings).filter(
            SystemSettings.key == key,
            SystemSettings.value < now.isoformat(),
        ).update({"value": expires_at}, synchronize_session=False)
        db.commit()
        if updated:
            return True
        if db.query(SystemSettings).filter(SystemSettings.key == key).first():
            return False
        try:
            db.add(SystemSettings(key=key, value=expires_at))
            db.commit()
            return True
        except Exception:
            db.rollback()
            return False
    finally:
        db.close()

def _run_async_job(coro):
    import asyncio as _asyncio
    if not _acquire_scheduler_lock(coro.__name__, 3500 if coro.__name__ == "scheduled_followup_processor" else 55):
        return
    try:
        _asyncio.run(coro())
    except Exception as exc:
        print(f"[SCHEDULER] {coro.__name__} failed: {exc}", flush=True)

async def process_pending_blasts():
    db = SessionLocal()
    try:
        now = datetime.now(timezone.utc).isoformat()
        pending = db.query(BlastCampaign).filter(
            BlastCampaign.status == "PENDING",
            BlastCampaign.scheduled_for <= now,
        ).all()
        for campaign in pending:
            claimed = db.query(BlastCampaign).filter(
                BlastCampaign.id == campaign.id,
                BlastCampaign.status == "PENDING",
            ).update({"status": "PROCESSING"}, synchronize_session=False)
            db.commit()
            if not claimed:
                continue
            db.refresh(campaign)
            try:
                criteria = json.loads(campaign.filter_criteria) if campaign.filter_criteria else {}
                query = db.query(Lead).filter(Lead.is_archived == False, Lead.do_not_contact == False)
                if criteria.get("status"):
                    query = query.filter(Lead.status == criteria["status"])
                if criteria.get("batch_name"):
                    query = query.filter(Lead.batch_name == criteria["batch_name"])
                if criteria.get("min_rating") and int(criteria["min_rating"]) > 0:
                    query = query.filter(Lead.rating >= int(criteria["min_rating"]))
                leads = query.all()
                from app.core.whatsapp_provider import get_whatsapp_config, send_whatsapp_message

                whatsapp_config = get_whatsapp_config(db)
                template = None
                if campaign.template_id:
                    template = db.query(DynamicTemplate).filter(DynamicTemplate.id == campaign.template_id).first()
                if not template:
                    templates = db.query(DynamicTemplate).filter(DynamicTemplate.type == "WA_BLAST", DynamicTemplate.is_active == True).all()
                    if templates:
                        template = random.choice(templates)
                sent = 0
                failed = 0
                for lead in leads:
                    report_slug = generate_report_for_lead(lead, db)
                    report_link = f"{FRONTEND_URL}/r/{report_slug}"
                    if template:
                        product_name = criteria.get("product_category") or lead.product_interest or "layanan kami"
                        message = template.content.replace("{{client_name}}", lead.business_name).replace("{{business_name}}", lead.business_name).replace("{{product_name}}", product_name)
                    else:
                        message = f"Halo {lead.business_name}, kami menyiapkan audit digital singkat untuk bisnis Anda. Apakah kami boleh menjelaskan poin yang paling prioritas?\n\nLaporan ringkas: {report_link}"
                    message = message.replace("{{proposal_link}}", f"\n{report_link}\n")
                    result = await send_whatsapp_message(db, lead.phone_number, message, {
                        "lead_id": lead.id,
                        "campaign_id": campaign.id,
                        "template_id": template.id if template else None,
                        "batch_name": criteria.get("batch_name"),
                        "business_name": lead.business_name,
                    })
                    success = result.ok
                    db.add(BlastMessage(
                        id=str(uuid.uuid4()), campaign_id=campaign.id, lead_id=lead.id,
                        template_id=template.id if template else None,
                        phone_number=lead.phone_number,
                        sent_at=datetime.now(timezone.utc).isoformat(),
                        status="sent" if success else "failed",
                        error_message=None if success else (result.error or f"{result.provider} send failed"),
                    ))
                    if success:
                        lead.status = "WA Terkirim"
                        sent += 1
                    else:
                        failed += 1
                    db.commit()
                    await asyncio.sleep(whatsapp_config.blast_delay_seconds)
                campaign.sent_count = sent
                campaign.failed_count = failed
                campaign.status = "SUCCESS" if failed == 0 else "PARTIAL"
                log_outreach_cost(db, campaign.id, sent)
                db.commit()
            except Exception as exc:
                campaign.status = "FAILED"
                print(f"[SCHEDULED BLAST] campaign={campaign.id} failed: {exc}", flush=True)
                db.commit()
    finally:
        db.close()

async def scheduled_followup_processor():
    db = SessionLocal()
    try:
        enabled = db.query(SystemSettings).filter_by(key="followup_enabled").first()
        if not enabled or enabled.value != "true":
            return
        hour_setting = db.query(SystemSettings).filter_by(key="followup_hour").first()
        target_hour = int(hour_setting.value) if hour_setting and hour_setting.value else 9
        current_hour = datetime.now(timezone.utc).hour + 7
        if current_hour >= 24:
            current_hour -= 24
        if current_hour != target_hour:
            return
        now = datetime.now(timezone.utc)
        sequences = db.query(FollowUpSequence).filter(
            FollowUpSequence.status == "ACTIVE",
            FollowUpSequence.next_send_at <= now.isoformat(),
        ).all()
        from app.core.whatsapp_provider import send_whatsapp_message

        for seq in sequences:
            lead = db.query(Lead).filter(Lead.id == seq.lead_id).first()
            if not lead:
                seq.status = "STOPPED"; seq.stopped_reason = "lead_not_found"; db.commit(); continue
            if lead.do_not_contact:
                seq.status = "STOPPED"; seq.stopped_reason = "opt_out"; db.commit(); continue
            template_ids = json.loads(seq.template_ids) if seq.template_ids else []
            delays = json.loads(seq.delays) if seq.delays else []
            if seq.current_step >= len(delays):
                seq.status = "COMPLETED"; db.commit(); continue
            message = None
            if template_ids and seq.current_step < len(template_ids):
                tmpl = db.query(DynamicTemplate).filter(DynamicTemplate.id == template_ids[seq.current_step]).first()
                if tmpl:
                    message = tmpl.content.replace("{{business_name}}", lead.business_name).replace("{{client_name}}", lead.business_name)
            if not message:
                followup_defaults = [
                    f"Halo {lead.business_name}, saya ingin follow up terkait laporan audit digital yang sudah saya kirimkan sebelumnya. Apakah ada pertanyaan yang bisa saya bantu jawab?",
                    f"Pak, saya notice laporan audit untuk {lead.business_name} sudah dibuka tapi belum ada respons. Apakah ada kendala atau pertanyaan? Saya siap bantu jelaskan lebih detail.",
                    f"Halo Pak, ini follow up terakhir dari saya untuk {lead.business_name}. Jika memang belum berminat saat ini, tidak masalah. Tapi perlu diingat, slot optimasi wilayah Anda terbatas dan kompetitor terus bergerak.",
                ]
                message = followup_defaults[min(seq.current_step, len(followup_defaults) - 1)]
            result = await send_whatsapp_message(db, lead.phone_number, message, {
                "lead_id": lead.id,
                "request_id": f"followup:{seq.id}:{seq.current_step}",
                "business_name": lead.business_name,
            })
            if not result.ok:
                continue
            seq.current_step += 1
            if seq.current_step >= len(delays):
                seq.status = "COMPLETED"; seq.next_send_at = None
            else:
                next_delay = delays[seq.current_step] if seq.current_step < len(delays) else 7
                seq.next_send_at = (now + timedelta(days=next_delay)).isoformat()
            db.commit()
    finally:
        db.close()

def _deduct_due_subscriptions(db: Session) -> list[dict]:
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    subs = db.query(Subscription).filter(
        Subscription.is_active == True,
        Subscription.next_billing_date <= today,
    ).all()
    deducted = []
    for sub in subs:
        wallet = db.query(Wallet).filter(Wallet.id == sub.wallet_id).first()
        if not wallet:
            continue
        txn = Transaction(
            wallet_id=sub.wallet_id, type="expense", amount=sub.amount,
            category="Subscription", date=today, notes=f"Auto-deduct: {sub.name}",
        )
        db.add(txn)
        wallet.balance -= sub.amount
        next_date = datetime.strptime(sub.next_billing_date, "%Y-%m-%d")
        if sub.billing_cycle == "monthly":
            from calendar import monthrange
            next_month = next_date.month % 12 + 1
            next_year = next_date.year + (1 if next_date.month == 12 else 0)
            next_day = min(next_date.day, monthrange(next_year, next_month)[1])
            sub.next_billing_date = f"{next_year}-{next_month:02d}-{next_day:02d}"
        elif sub.billing_cycle == "yearly":
            sub.next_billing_date = f"{next_date.year + 1}-{next_date.month:02d}-{next_date.day:02d}"
        deducted.append({"subscription_id": sub.id, "name": sub.name, "amount": sub.amount})
    db.commit()
    return deducted

# ─── Job trackers ─────────────────────────────────────────────────────────────

_analysis_jobs: dict = {}
_blast_jobs: dict = {}
