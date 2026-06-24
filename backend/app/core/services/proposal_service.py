"""
Proposal helpers — service type detection, ROI data, report generation.
"""
import uuid
import json
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
        "analysis": f"Berdasakan audit digital yang kami lakukan terhadap {lead.business_name}, kami menemukan beberapa area kritis yang perlu segera ditangani untuk mencegah kehilangan pelanggan potensial ke kompetitor.",
        "pain_points": pain_points,
        "suggested_product": lead.product_interest or "SEO & Google Maps Optimization",
    }


def _build_addons_from_products(db: Session) -> str:
    products = db.query(Product).filter(Product.is_active == True).all()
    addons = [{"id": p.id, "name": p.name, "price": p.base_price} for p in products]
    return json.dumps(addons)


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
