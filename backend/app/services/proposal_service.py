"""Proposal Service Layer — extracted from routers/proposals.py and app/core/dependencies.py"""
import json
import uuid
import threading
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy.orm import Session, joinedload

from models import (
    Proposal, ProposalAnalytics, Lead, Contact, Project, Product, DynamicTemplate,
    Board, BoardColumn, BoardCard, WorkspaceSheet, WorkspaceColumn, WorkspaceRow,
    WorkspaceCell, BoardCardActivity, FollowUpSequence,
    log_audit, LeadActivityLog, ReengagementAlert,
)
from app.core.dependencies import (
    _get_setting, get_fonnte_token, _send_fonnte_sync, send_fonnte_message,
    FRONTEND_URL, ADMIN_WA, generate_unique_slug,
    WORKSPACE_TEMPLATES, build_sheets_for_service, sync_row_to_board,
    _apply_proposal_signal,
)


# ─── Proposal creation helpers ────────────────────────────────────────────────

def generate_proposal_slug(db: Session, lead_name: str) -> str:
    return generate_unique_slug(db, lead_name)


def _build_services_from_products(db: Session, service_type: str) -> list[dict]:
    products = db.query(Product).filter(Product.is_active == True).all()
    if not products:
        return []
    matched = [p for p in products if service_type.lower() in (p.name or "").lower()]
    return [
        {"name": p.name, "price": p.base_price, "features": (p.description or "").split("\n")}
        for p in (matched[:3] if matched else products[:3])
    ]


def _build_timeline_from_template(db: Session, service_type: str, contract_months: int) -> Optional[str]:
    category = service_type.lower()
    seo_keywords = ["seo", "google", "maps", "lokal", "local", "ranking", "peringkat"]
    web_keywords = ["web", "website", "landing", "development", "dev", "frontend", "fullstack"]
    template_id = None
    if any(kw in category for kw in seo_keywords):
        template_id = "timeline-seo-lokal"
    elif any(kw in category for kw in web_keywords):
        template_id = "timeline-web-dev"
    else:
        template_id = "timeline-seo-lokal"
    tmpl = db.query(DynamicTemplate).filter_by(id=template_id, type="TIMELINE_TEMPLATE", is_active=True).first()
    return tmpl.content if tmpl else None


# ─── Project type / service type detection ───────────────────────────────────

def detect_project_type(services: list) -> str:
    for s in services:
        if s.get("is_retainer"):
            return "RETAINER"
        name = (s.get("name") or "").lower()
        if any(k in name for k in ["bulanan", "retainer", "maintenance", "kelola", "seo"]):
            return "RETAINER"
    return "FIXED"


def detect_service_type(services: list) -> Optional[str]:
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


def months_between_dates(start_date: Optional[str], end_date: Optional[str]) -> Optional[int]:
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


def detect_contract_months(proposal, services: list, project_start: Optional[str] = None, project_end: Optional[str] = None) -> int:
    months = months_between_dates(project_start, project_end)
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


# ─── ROI data builder ─────────────────────────────────────────────────────────

def build_roi_data(db: Session, services: list, roi_input: Optional[dict] = None) -> str:
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


def _build_addons_from_products(db: Session) -> str:
    products = db.query(Product).filter(Product.is_active == True).all()
    addons = [{"id": p.id, "name": p.name, "price": p.base_price} for p in products]
    return json.dumps(addons)


# ─── Proposal creation ────────────────────────────────────────────────────────

def create_proposal(
    db: Session,
    lead_id: int,
    services: list[dict],
    additional_options: Optional[str],
    timeline_data: Optional[str],
    source: str,
    roi_data: Optional[dict],
    actor: str,
) -> tuple[Proposal, Lead]:
    """Create a proposal from given data. Returns (proposal, lead)."""
    lead = None
    if source == "contact":
        contact = db.query(Contact).filter(Contact.id == lead_id).first()
        if not contact:
            raise ValueError("Contact tidak ditemukan")
        lead = db.query(Lead).filter(Lead.phone_number == contact.phone_number).first()
        if not lead:
            lead = Lead(
                business_name=contact.business_name,
                phone_number=contact.phone_number,
                status="Closed/Client",
                product_interest=contact.purchased_product,
            )
            db.add(lead)
            db.commit()
            db.refresh(lead)
    else:
        lead = db.query(Lead).filter(Lead.id == lead_id).first()
        if not lead:
            raise ValueError("Lead tidak ditemukan")

    services_data = [s if isinstance(s, dict) else s.model_dump() for s in services]
    total = sum(s.get("price", 0) for s in services_data)
    discount_pct = float(_get_setting("proposal_discount_percent", "15")) / 100
    discount_expires = (datetime.now(timezone.utc) + timedelta(hours=24)).isoformat()
    default_faqs = json.dumps([
        {"question": "Apakah audit ini gratis?", "answer": "Ya, audit digital ini 100% gratis dan tanpa kewajiban apapun. Kami ingin Anda melihat sendiri peluang yang selama ini terlewat."},
        {"question": "Berapa lama sampai terlihat hasilnya?", "answer": "Dengan optimasi yang tepat, peningkatan visibilitas bisa terlihat dalam 14-30 hari kerja pertama, tergantung tingkat kompetisi."},
        {"question": "Apa yang membedakan layanan ini?", "answer": "Kami fokus pada hasil terukur — peningkatan visibilitas, leads masuk, dan konversi. Bukan sekadar laporan tanpa aksi."},
    ])

    # Timeline: use provided data or fallback to default template
    timeline_json = timeline_data
    if not timeline_json or timeline_json == "null":
        timeline_json = _build_timeline_from_template(db, lead.product_interest or "", 0)

    proposal = Proposal(
        id=str(uuid.uuid4()),
        lead_id=lead.id,
        services_detail=json.dumps(services_data),
        total_price=total,
        base_price=total,
        discount_price=round(total * (1 - discount_pct)),
        discount_expires_at=discount_expires,
        additional_options=additional_options,
        status="sent",
        created_at=datetime.now(timezone.utc).isoformat(),
        slug=generate_unique_slug(db, lead.business_name),
        faqs=default_faqs,
        selected_addons=_build_addons_from_products(db),
        timeline_data=timeline_json,
        roi_data=build_roi_data(db, services_data, roi_data),
    )
    db.add(proposal)
    db.commit()
    try:
        from app.services.sales_workflow_service import archive_proposal_pdf_for_lead
        archive_proposal_pdf_for_lead(db, proposal, lead, actor)
        db.commit()
    except Exception as e:
        print(f"[PROPOSAL_ARCHIVE_PDF] skip: {e}", flush=True)
    log_audit(db, actor, "CREATE", "proposals", proposal.id, {"lead": lead.business_name, "total": total})
    return proposal, lead


# ─── Proposal output builder ─────────────────────────────────────────────────

def proposal_to_out(proposal: Proposal, lead: Optional[Lead]) -> dict:
    timeline = None
    if proposal.timeline_data:
        timeline = sorted(json.loads(proposal.timeline_data), key=lambda x: x["sequence"])
    roi = None
    if proposal.roi_data:
        roi = json.loads(proposal.roi_data) if isinstance(proposal.roi_data, str) else proposal.roi_data
    return {
        "id": proposal.id,
        "lead_id": proposal.lead_id,
        "services_detail": [s for s in json.loads(proposal.services_detail)],
        "total_price": proposal.total_price,
        "additional_options": proposal.additional_options,
        "status": proposal.status,
        "created_at": proposal.created_at,
        "business_name": lead.business_name if lead else None,
        "phone_number": lead.phone_number if lead else None,
        "slug": proposal.slug,
        "timeline_data": timeline,
        "roi_data": roi,
    }


# ─── Template fetchers ────────────────────────────────────────────────────────

def get_proposal_templates(db: Session) -> dict:
    intro = db.query(DynamicTemplate).filter(
        DynamicTemplate.type.in_(["PROPOSAL_INTRO", "PROPOSAL_TEXT"]),
        DynamicTemplate.is_active == True,
    ).first()
    outro = db.query(DynamicTemplate).filter(
        DynamicTemplate.type == "PROPOSAL_OUTRO",
        DynamicTemplate.is_active == True,
    ).first()
    return {
        "intro": intro.content if intro else None,
        "outro": outro.content if outro else None,
    }


def get_timeline_templates(db: Session) -> list[dict]:
    templates = db.query(DynamicTemplate).filter(
        DynamicTemplate.type == "TIMELINE_TEMPLATE",
        DynamicTemplate.is_active == True,
    ).all()
    result = []
    for t in templates:
        items = json.loads(t.content) if t.content else []
        sorted_items = sorted(items, key=lambda x: x.get("sequence", 0))
        result.append({
            "id": t.id,
            "name": t.name,
            "category_id": t.category_id,
            "timeline_data": sorted_items,
        })
    return result


# ─── Analytics logging (thread-safe) ─────────────────────────────────────────

def log_proposal_open(proposal_id: str, SessionLocal, Lead, Proposal) -> str:
    """Thread-safe open logging. Returns analytics_id."""
    db = SessionLocal()
    try:
        now = datetime.now(timezone.utc).isoformat()
        analytics = ProposalAnalytics(
            id=str(uuid.uuid4()),
            proposal_id=proposal_id,
            opened_at=now,
            total_time_seconds=0,
            sections_viewed="[]",
        )
        db.add(analytics)
        db.commit()
        return analytics.id
    finally:
        db.close()


def log_proposal_ping(
    analytics_id: str,
    seconds: int,
    sections_viewed: list,
    SessionLocal,
    ProposalAnalytics,
) -> None:
    """Thread-safe ping update."""
    db = SessionLocal()
    try:
        analytics = db.query(ProposalAnalytics).filter(ProposalAnalytics.id == analytics_id).first()
        if not analytics:
            return
        analytics.last_ping = datetime.now(timezone.utc).isoformat()
        prev_total = analytics.total_time_seconds or 0
        analytics.total_time_seconds = prev_total + seconds
        existing_sections = json.loads(analytics.sections_viewed or "[]")
        for s in sections_viewed:
            if s not in existing_sections:
                existing_sections.append(s)
        analytics.sections_viewed = json.dumps(existing_sections)
        db.commit()
    finally:
        db.close()


def log_proposal_duration(
    proposal_id: str,
    duration_seconds: int,
    SessionLocal,
    ProposalAnalytics,
) -> None:
    """Thread-safe duration update."""
    db = SessionLocal()
    try:
        latest = db.query(ProposalAnalytics).filter(
            ProposalAnalytics.proposal_id == proposal_id
        ).order_by(ProposalAnalytics.opened_at.desc()).first()
        if latest:
            latest.duration_seconds = max(latest.duration_seconds or 0, duration_seconds)
            db.commit()
    finally:
        db.close()


def get_proposal_analytics(db: Session, proposal_id: str) -> list[dict]:
    records = db.query(ProposalAnalytics).filter(
        ProposalAnalytics.proposal_id == proposal_id
    ).all()
    return [{
        "id": r.id,
        "proposal_id": r.proposal_id,
        "opened_at": r.opened_at,
        "last_ping": r.last_ping,
        "total_time_seconds": r.total_time_seconds,
        "sections_viewed": json.loads(r.sections_viewed or "[]"),
    } for r in records]


# ─── Accept / Reject ──────────────────────────────────────────────────────────

def accept_proposal(
    db: Session,
    proposal_id: str,
    client_name: str,
    client_phone: str,
    accept_notes: Optional[str],
) -> dict:
    """Accept a proposal through the canonical sales workflow."""
    from app.services.sales_workflow_service import accept_proposal_workflow
    proposal = db.query(Proposal).filter(Proposal.id == proposal_id).first()
    if not proposal:
        raise ValueError("Proposal tidak ditemukan")
    return accept_proposal_workflow(db, proposal, client_name, client_phone, accept_notes)


def reject_proposal(db: Session, proposal_id: str, reason: Optional[str]) -> dict:
    proposal = db.query(Proposal).filter(Proposal.id == proposal_id).first()
    if not proposal:
        raise ValueError("Proposal tidak ditemukan")
    if proposal.status == "rejected":
        return {"success": True, "already_rejected": True}
    if proposal.status == "accepted":
        raise ValueError("Proposal sudah diterima")
    proposal.status = "rejected"
    proposal.rejected_at = datetime.now(timezone.utc).isoformat()
    db.commit()
    return {"success": True, "already_rejected": False}
