"""
Proposal helpers — service type detection, ROI data, report generation.
"""
import uuid
import json
import re
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session

from models import Proposal, LeadAnalysis, Product, Lead


def _detect_service_type(services: list) -> Optional[str]:
    """Detect FIRST matching service type (legacy, single-type)."""
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


def _detect_service_types(services: list) -> list[str]:
    """Detect ALL service types from a multi-service proposal. Returns deduplicated list."""
    seen: set[str] = set()
    for s in services:
        name = (s.get("name") or "").lower()
        if "web" in name or "website" in name or "landing page" in name or "company profile" in name:
            seen.add("web_dev_bulanan" if "bulanan" in name else "web_dev")
        if any(k in name for k in ["seo", "google maps", "gmaps", "google business"]):
            seen.add("seo_gmaps")
        if any(k in name for k in ["sosial media", "sosmed", "kelola", "instagram", "tiktok", "facebook"]):
            seen.add("sosmed")
        if "maintenance" in name:
            seen.add("maintenance")
        if any(k in name for k in ["logo", "branding", "desain", "identitas visual"]):
            seen.add("branding")
    return sorted(seen)


def _detect_service_type_from_name(name: str) -> Optional[str]:
    """Detect service type from a single name string."""
    if not name:
        return None
    n = name.lower()
    if "web" in n or "website" in n or "landing page" in n or "company profile" in n:
        return "web_dev_bulanan" if "bulanan" in n else "web_dev"
    if any(k in n for k in ["seo", "google maps", "gmaps", "google business"]):
        return "seo_gmaps"
    if any(k in n for k in ["sosial media", "sosmed", "kelola", "instagram", "tiktok", "facebook"]):
        return "sosmed"
    if "maintenance" in n:
        return "maintenance"
    if any(k in n for k in ["logo", "branding", "desain", "identitas visual"]):
        return "branding"
    return None


def _detect_service_type_single_lead(entity) -> Optional[str]:
    """Detect service type from a Lead or Contact entity."""
    name = getattr(entity, "product_interest", None) or getattr(entity, "purchased_product", None) or ""
    return _detect_service_type_from_name(name)


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


# ─── Report generation ────────────────────────────────────────────────────────

def _generate_fallback_analysis(lead) -> dict:
    """Deterministic, fact-based audit copy from lead fields — no hallucinated metrics."""
    pain_points = []
    name = lead.business_name or "Bisnis Anda"
    category = (lead.product_interest or "layanan Anda").strip() or "layanan Anda"
    rating = getattr(lead, "google_rating", None)
    if rating is None:
        rating = getattr(lead, "rating", None)
    reviews = getattr(lead, "review_count", None)
    website = (getattr(lead, "website_url", None) or "").strip()
    city = ""
    if lead.address:
        city = lead.address.split(",")[-1].strip() if "," in (lead.address or "") else (lead.address or "").strip()
    area = city or "area Anda"

    # Point 1: Maps / social proof
    if rating is not None and float(rating) > 0:
        if float(rating) < 4.0:
            pain_points.append(
                f"Rating Google Maps {name} saat ini {float(rating):.1f}/5"
                + (f" dari {int(reviews)} ulasan" if reviews else "")
                + " — banyak calon pelanggan membandingkan dulu, lalu pilih yang terlihat lebih dipercaya."
            )
        else:
            pain_points.append(
                f"Rating {name} di Maps {float(rating):.1f}/5"
                + (f" ({int(reviews)} ulasan)" if reviews else "")
                + f". Fondasi bagus, tapi tanpa optimasi pencarian lokal di {area}, rating saja belum cukup mengalahkan kompetitor yang lebih aktif."
            )
    else:
        pain_points.append(
            f"{name} belum menampilkan sinyal rating/ulasan yang kuat di Google Maps — tanpa bukti sosial, calon pelanggan di {area} cenderung ragu menghubungi."
        )

    # Point 2: discoverability
    pain_points.append(
        f"Saat orang mencari «{category}» di Google / Maps untuk {area}, bisnis tanpa profil lengkap + kata kunci yang rapi mudah tenggelam di bawah kompetitor yang sudah dioptimasi."
    )

    # Point 3: website / contact path
    if website:
        pain_points.append(
            f"Website terdeteksi ({website[:48]}{'…' if len(website) > 48 else ''}), tapi jalur dari pencarian → halaman penawaran → WhatsApp perlu dicek: banyak bisnis kehilangan prospek di langkah ini."
        )
    else:
        pain_points.append(
            f"{name} belum punya website yang terdeteksi di data kami. Untuk {category}, satu halaman penawaran + tombol WhatsApp saja sudah bisa menaikkan konversi dari penelusuran lokal."
        )

    facts = []
    if rating: facts.append(f"rating Maps {float(rating):.1f}")
    if reviews: facts.append(f"{int(reviews)} ulasan")
    if website: facts.append("website terdeteksi")
    else: facts.append("belum ada website terdeteksi")
    if city: facts.append(f"area {city}")
    fact_line = ", ".join(facts) if facts else "data profil masih minim"

    return {
        "analysis": (
            f"Ringkasan audit awal untuk {name}: {fact_line}. "
            f"Fokus perbaikan: kelengkapan profil digital, bukti sosial, dan jalur kontak yang mudah dari Google ke WhatsApp."
        ),
        "pain_points": pain_points[:3],
        "suggested_product": lead.product_interest or "SEO & Google Maps Optimization",
    }


def _build_addons_from_products(db: Session, matched_products: list | None = None) -> str:
    """Only expose 2–4 relevant upsells — never dump entire catalog into public report."""
    products = matched_products or []
    if not products:
        products = db.query(Product).filter(Product.is_active == True).order_by(Product.base_price.asc()).limit(4).all()
    # Prefer non-primary services as "addons" (skip first matched if many)
    pool = products[1:5] if len(products) > 1 else products[:3]
    addons = [{"id": p.id, "name": p.name, "price": float(p.base_price or 0)} for p in pool]
    return json.dumps(addons)


def _match_products_for_category(db: Session, category: str) -> list:
    """Match catalog products by interest keywords — avoid dumping unrelated SKUs."""
    products = db.query(Product).filter(Product.is_active == True).all()
    cat = (category or "").strip().lower()
    if not cat:
        # No interest known: pick core SEO/GMaps packages only if present, else top 2
        core = [p for p in products if any(k in (p.name or "").lower() for k in ("seo", "maps", "google", "gmaps"))]
        return (core or products)[:2]

    # Tokenize interest: "Web Development" -> web, development
    tokens = [t for t in re.split(r"[^a-z0-9]+", cat) if len(t) >= 3]
    keyword_map = {
        "web": ["web", "website", "landing"],
        "seo": ["seo", "maps", "google", "gmaps", "local"],
        "sosmed": ["sosmed", "social", "instagram", "tiktok", "konten"],
        "brand": ["brand", "logo", "desain", "design"],
        "mainten": ["mainten", "maintenance", "rawat"],
        "ads": ["ads", "iklan", "meta", "google ads"],
    }
    expanded = set(tokens)
    for token in tokens:
        for key, alts in keyword_map.items():
            if key in token or token in key:
                expanded.update(alts)

    scored = []
    for p in products:
        hay = f"{p.name or ''} {p.description or ''}".lower()
        score = sum(1 for k in expanded if k in hay)
        if score:
            scored.append((score, p))
    scored.sort(key=lambda x: (-x[0], x[1].base_price or 0))
    matched = [p for _, p in scored[:3]]
    if matched:
        return matched
    # Soft fallback: single cheapest starter-like product, not whole catalog
    starters = [p for p in products if "starter" in (p.name or "").lower() or "pro" in (p.name or "").lower()]
    return (starters or products)[:2]


def generate_report_for_lead(lead, db: Session, product_category: str = None) -> str:
    from app.core.services.settings_service import _get_setting
    from app.core.services.slug_service import generate_unique_slug

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
    matched_products = _match_products_for_category(db, category)
    def _features(p):
        raw = (p.description or "").strip()
        if not raw:
            return ["Solusi digital terukur untuk pertumbuhan bisnis Anda"]
        # Prefer short bullet-like lines; marketing paragraphs get truncated
        lines = [ln.strip(" -•\t") for ln in raw.split("\n") if ln.strip()]
        if len(lines) == 1 and len(lines[0]) > 140:
            return [lines[0][:140].rsplit(" ", 1)[0] + "…"]
        return lines[:4]
    services = [
        {"name": p.name, "price": float(p.base_price or 0), "features": _features(p)}
        for p in matched_products
    ] if matched_products else [{
        "name": "Paket Optimasi Digital",
        "price": 0,
        "features": ["Audit posisi digital", "Rencana prioritas 30 hari", "Setup jalur kontak WhatsApp"],
    }]
    base_total = sum(s["price"] for s in services)
    slug = generate_unique_slug(db, lead.business_name)
    # Prefer real city for slug context is handled by slug service; keep business name
    report = Proposal(
        id=str(uuid.uuid4()),
        lead_id=lead.id,
        services_detail=json.dumps(services),
        total_price=base_total,
        base_price=base_total,
        discount_price=round(base_total * (1 - float(_get_setting("proposal_discount_percent", "15")) / 100)) if base_total else 0,
        discount_expires_at=None,
        additional_options=None,
        status="Report",
        created_at=datetime.now(timezone.utc).isoformat(),
        slug=slug,
        faqs=json.dumps([
            {"question": "Apakah audit ini gratis?", "answer": "Ya, audit digital ini 100% gratis dan tanpa kewajiban apapun. Kami ingin Anda melihat sendiri peluang yang selama ini terlewat."},
            {"question": "Berapa lama sampai terlihat hasilnya?", "answer": "Dengan eksekusi yang tepat, sinyal awal (klik, arah, atau chat) biasanya mulai terbaca dalam 14–30 hari — tergantung kelengkapan data bisnis Anda."},
            {"question": "Apa yang kami butuhkan dari Anda?", "answer": "Akses singkat ke Google Business / website (jika ada) dan konfirmasi layanan utama + area kerja. Tanpa itu, optimasi hanya bisa setengah jalan."},
        ]),
        selected_addons=_build_addons_from_products(db, matched_products),
        timeline_data=None,
    )
    db.add(report)
    db.commit()
    return slug
