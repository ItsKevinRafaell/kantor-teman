"""Web preview service — generate landing page per-lead dari template bank.

Sumber template: backend/web_preview_templates/{key}.html (dibundle di repo,
bukan path eksternal) + aset di UPLOADS_DIR/web_preview_assets/{key}/
(diserve FastAPI via mount /uploads).

Aturan swap (mengikuti prinsip build_swap.py anti-halusinasi):
- Hanya replace string yang PERSIS ada di template (anchor per template
  di REGISTRY bawah). Tidak ada copy yang digenerate.
- Asset path relatif di-rewrite ke /uploads/web_preview_assets/{key}/<file>.
- Idempotent: lead + template yang sama → reuse row yang sudah ada.

Hook dipanggil dari campaign_service.execute_blast_campaign untuk lead
berstatus Prospek Panas; kegagalan generate TIDAK boleh memblokir blast.
"""
import os
import re
from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from app.core.config import FRONTEND_URL
from models import WebPreview, Lead, LeadActivityLog

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
TEMPLATES_DIR = os.path.join(BACKEND_DIR, "web_preview_templates")

# ── Registry template ────────────────────────────────────────────────────────
# brand/phone/wa anchor = string PERSIS yang ada di file template.
# keywords: dicocokkan ke product_interest + business_name (lowercase, "in").
DEFAULT_TEMPLATE_KEY = "kontraktor"
IMAGE_EXT = (".jpg", ".jpeg", ".png", ".webp", ".svg", ".avif")

REGISTRY: dict = {
    "klinik": {
        "title": "Landing klinik/praktik kesehatan",
        "keywords": ["klinik", "kesehatan", "medis", "dokter", "gigi", "puskesmas", "praktik", "apotek", "laboratorium"],
        "brand_anchor": "Klinik Pratama Harapan",
        "phone_display_anchor": "0812-555-1234",
        "wa_anchor": "628125551234",
    },
    "bengkel": {
        "title": "Landing bengkel/otomotif",
        "keywords": ["bengkel", "otomotif", "servis mobil", "servis motor", "oli", "tambal ban", "montir", "cuci mobil", "cuci motor"],
        "brand_anchor": "Garasi 88",
        "phone_display_anchor": "0812-5478-0088",
        "wa_anchor": "6281254780088",
    },
    "kontraktor": {
        "title": "Landing kontraktor/konstruksi (default)",
        "keywords": ["kontraktor", "konstruksi", "bangunan", "renovasi", "pembangunan", "material bangunan", "design interior"],
        "brand_anchor": "CV Cipta Griya Kontraktor",
        "phone_display_anchor": "",  # template ini tidak menampilkan nomor teks
        "wa_anchor": "6281256789012",
    },
}


# ── Normalisasi nomor ────────────────────────────────────────────────────────
def _digits(phone: str) -> str:
    return re.sub(r"\D", "", phone or "")


def normalize_wa(phone: str) -> str:
    d = _digits(phone)
    if not d:
        return ""
    if d.startswith("0"):
        d = "62" + d[1:]
    elif not d.startswith("62"):
        d = "62" + d
    return d


def format_phone_display(phone: str) -> str:
    """081234567890 → 0812-3456-7890 (4-digit prefix, sisanya dibagi rata).
    11 digit → 0812-345-6789 (pola umum template)."""
    d = _digits(phone)
    if d.startswith("62") and len(d) >= 10:
        d = "0" + d[2:]
    if len(d) < 9:
        return phone or ""
    rest = d[4:]
    mid = len(rest) // 2
    return f"{d[:4]}-{rest[:mid]}-{rest[mid:]}"


# ── Pilih template ───────────────────────────────────────────────────────────
def select_template_key(lead: Lead, explicit_key: Optional[str] = None) -> str:
    if explicit_key and explicit_key in REGISTRY:
        return explicit_key
    text = f"{lead.product_interest or ''} {lead.business_name or ''}".lower()
    best_key, best_score = "", 0
    for key, meta in REGISTRY.items():
        score = sum(1 for kw in meta["keywords"] if kw in text)
        if score > best_score:
            best_key, best_score = key, score
    return best_key or DEFAULT_TEMPLATE_KEY


# ── Swap engine ──────────────────────────────────────────────────────────────
# Grup 1 = prefix (termasuk kutip pembuka), grup 2 = path, grup 3 = kutip penutup
# + penutup (WAJIB di-emit ulang — kalau hilang, atribut HTML berikutnya rusak).
_ASSET_TAG_RE = re.compile(
    r"""((?:src|href|poster)\s*=\s*["'])([^"']*)(["'])""",
    re.IGNORECASE,
)
_CSS_URL_RE = re.compile(r"""(url\(\s*["']?)([^'")]*)(["']?\s*\))""", re.IGNORECASE)


def _rewrite_asset(match, key: str) -> str:
    prefix, path, suffix = match.group(1), match.group(2), match.group(3)
    low = path.lower()
    if low.startswith(("http://", "https://", "data:", "//", "#", "mailto:", "tel:", "wa.me")):
        return match.group(0)
    if not low.endswith(IMAGE_EXT):
        return match.group(0)
    base = os.path.basename(path)
    return f"{prefix}/uploads/web_preview_assets/{key}/{base}{suffix}"


def _render(template_key: str, lead: Lead) -> str:
    meta = REGISTRY[template_key]
    path = os.path.join(TEMPLATES_DIR, f"{template_key}.html")
    with open(path, encoding="utf-8") as f:
        html = f.read()

    # 1) Nama bisnis — hanya anchor persis (anti-halusinasi)
    brand = meta["brand_anchor"]
    if brand and brand in html:
        html = html.replace(brand, lead.business_name)

    # 2) Nomor WA link + nomor tampilan
    wa = normalize_wa(lead.phone_number)
    if wa and meta["wa_anchor"]:
        html = html.replace(f"wa.me/{meta['wa_anchor']}", f"wa.me/{wa}")
    disp = format_phone_display(lead.phone_number)
    if disp and meta.get("phone_display_anchor") and meta["phone_display_anchor"] in html:
        html = html.replace(meta["phone_display_anchor"], disp)

    # 3) Asset path → /uploads/web_preview_assets/{key}/
    html = _ASSET_TAG_RE.sub(lambda m: _rewrite_asset(m, template_key), html)
    html = _CSS_URL_RE.sub(lambda m: _rewrite_asset(m, template_key), html)
    return html


# ── Public API ───────────────────────────────────────────────────────────────
def generate_preview_for_lead(
    lead: Lead,
    db: Session,
    campaign_id: Optional[str] = None,
    template_key: Optional[str] = None,
    force_new: bool = False,
) -> dict:
    """Generate (atau reuse) web preview untuk lead. Return:
    {slug, template_key, reused}."""
    key = select_template_key(lead, template_key)

    if not force_new:
        existing = (
            db.query(WebPreview)
            .filter(WebPreview.lead_id == lead.id, WebPreview.template_key == key)
            .order_by(WebPreview.id.desc())
            .first()
        )
        if existing:
            return {"slug": existing.slug, "template_key": key, "reused": True}

    html = _render(key, lead)
    preview = WebPreview(
        slug=WebPreview.new_slug(),
        lead_id=lead.id,
        campaign_id=campaign_id,
        template_key=key,
        html=html,
        opened_count=0,
        created_at=datetime.utcnow().isoformat(),
    )
    db.add(preview)
    db.commit()
    return {"slug": preview.slug, "template_key": key, "reused": False}


def preview_public_url(db: Session, slug: str) -> str:
    """URL yang dikirim ke lead — lewat domain frontend (Vercel rewrite
    /wp/:slug → backend). Konsisten dengan pola laporan /r/{slug}."""
    from app.core.services.settings_service import _get_setting

    frontend = _get_setting("frontend_url", FRONTEND_URL) or FRONTEND_URL
    return f"{frontend.rstrip('/')}/wp/{slug}"


def record_open_and_get_html(db: Session, slug: str) -> Optional[str]:
    """Track pembukaan (1x per GET) + return HTML. None kalau slug ga ada."""
    preview = db.query(WebPreview).filter(WebPreview.slug == slug).first()
    if not preview:
        return None
    now = datetime.utcnow().isoformat()
    preview.opened_count = (preview.opened_count or 0) + 1
    if not preview.first_opened_at:
        preview.first_opened_at = now
    preview.last_opened_at = now
    db.add(LeadActivityLog(lead_id=preview.lead_id, activity_type="WEB_PREVIEW_OPENED", created_at=now))
    db.commit()
    return preview.html


def get_preview_info(db: Session, lead_id: int) -> Optional[dict]:
    """Info preview terakhir untuk lead (buat UI detail lead)."""
    p = (
        db.query(WebPreview)
        .filter(WebPreview.lead_id == lead_id)
        .order_by(WebPreview.id.desc())
        .first()
    )
    if not p:
        return None
    return {
        "slug": p.slug,
        "url": preview_public_url(db, p.slug),
        "template_key": p.template_key,
        "opened_count": p.opened_count,
        "first_opened_at": p.first_opened_at,
        "last_opened_at": p.last_opened_at,
        "created_at": p.created_at,
    }
