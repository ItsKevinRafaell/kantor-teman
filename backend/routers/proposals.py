import re, html as html_mod, random, asyncio, uuid, json, csv, io, base64, hmac, time, httpx
import os
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv
from fastapi import APIRouter, Depends, HTTPException, Request, BackgroundTasks, UploadFile, File, Form, Query, Body
from fastapi.responses import StreamingResponse, RedirectResponse, HTMLResponse, Response
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session, joinedload
from typing import Optional, List, Any
from models import get_db, log_audit, User, Lead, Contact, Project, Proposal, ProposalAnalytics, Board, BoardColumn, BoardCard, WorkspaceSheet, WorkspaceColumn, WorkspaceRow, WorkspaceCell, Product, DynamicTemplate, LeadAnalysis, ReengagementAlert
from schemas import *
from app.core.dependencies import (get_current_user, require_admin, FRONTEND_URL,
    JWT_ALGORITHM, _get_setting, ADMIN_WA,
    generate_unique_slug, slugify,
    _build_addons_from_products, _build_roi_data,
    _apply_proposal_signal,
    _detect_project_type, _detect_service_type, _detect_contract_months,
    WORKSPACE_TEMPLATES, build_sheets_for_service,
    sync_row_to_board, sync_row_status_to_board,
    get_fonnte_token, _send_fonnte_sync, send_fonnte_message,
)
from app.services.report_tracking_service import (
    is_valid_report_viewer,
    record_report_activity,
    record_report_duration,
    record_report_open,
)
from app.services.sales_workflow_service import accept_proposal_workflow, archive_proposal_pdf_for_lead
from app.services.proposal_service import proposal_to_out as _proposal_to_out
from search_volume_data import get_monthly_search_volume

router = APIRouter()

@router.post("/api/proposals", response_model=ProposalOut, status_code=201)
def create_proposal(body: ProposalIn, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    lead = None
    if body.source == "contact":
        contact = db.query(Contact).filter(Contact.id == body.lead_id).first()
        if not contact:
            raise HTTPException(status_code=404, detail="Contact tidak ditemukan")
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
        lead = db.query(Lead).filter(Lead.id == body.lead_id).first()
        if not lead:
            raise HTTPException(status_code=404, detail="Lead tidak ditemukan")
    services_data = [s.model_dump() for s in body.services]
    total = sum(s.price for s in body.services)
    discount_pct = float(_get_setting("proposal_discount_percent", "15")) / 100
    discount_expires = (datetime.now(timezone.utc) + timedelta(hours=24)).isoformat()
    default_faqs = json.dumps([
        {"question": "Apakah audit ini gratis?", "answer": "Ya, audit digital ini 100% gratis dan tanpa kewajiban apapun. Kami ingin Anda melihat sendiri peluang yang selama ini terlewat."},
        {"question": "Berapa lama sampai terlihat hasilnya?", "answer": "Dengan optimasi yang tepat, peningkatan visibilitas bisa terlihat dalam 14-30 hari kerja pertama, tergantung tingkat kompetisi."},
        {"question": "Apa yang membedakan layanan ini?", "answer": "Kami fokus pada hasil terukur — peningkatan visibilitas, leads masuk, dan konversi. Bukan sekadar laporan tanpa aksi."},
    ])

    # Timeline Data: use provided data or fallback to default template
    timeline_json = None
    if body.timeline_data and len(body.timeline_data) > 0:
        sorted_timeline = sorted([t.model_dump() for t in body.timeline_data], key=lambda x: x["sequence"])
        timeline_json = json.dumps(sorted_timeline)
    else:
        # Fallback: pick timeline template based on product interest keywords
        category = (lead.product_interest or "").lower()
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
        if tmpl:
            timeline_json = tmpl.content

    proposal = Proposal(
        id=str(uuid.uuid4()),
        lead_id=lead.id,
        services_detail=json.dumps(services_data),
        total_price=total,
        base_price=total,
        discount_price=round(total * (1 - discount_pct)),
        discount_expires_at=discount_expires,
        additional_options=body.additional_options,
        status="sent",
        created_at=datetime.now(timezone.utc).isoformat(),
        slug=generate_unique_slug(db, lead.business_name),
        faqs=getattr(body, 'faqs', None) or default_faqs,
        selected_addons=_build_addons_from_products(db),
        timeline_data=timeline_json,
        roi_data=_build_roi_data(db, services_data, body.roi_data),
    )
    db.add(proposal)
    db.commit()
    db.refresh(proposal)
    try:
        archive_proposal_pdf_for_lead(db, proposal, lead, current_user.name)
        db.commit()
    except Exception as e:
        print(f"[PROPOSAL_ARCHIVE_PDF] skip: {e}", flush=True)
    log_audit(db, current_user.name, "CREATE", "proposals", proposal.id, {"lead": lead.business_name, "total": total})
    return _proposal_to_out(proposal, lead)



@router.get("/api/proposals/public/{proposal_id}")
def get_public_proposal(proposal_id: str, db: Session = Depends(get_db)):
    proposal = db.query(Proposal).filter((Proposal.id == proposal_id) | (Proposal.slug == proposal_id)).first()
    if not proposal:
        raise HTTPException(status_code=404, detail="Proposal tidak ditemukan")
    lead = db.query(Lead).filter(Lead.id == proposal.lead_id).first()
    out = _proposal_to_out(proposal, lead)
    if isinstance(out, dict):
        data = dict(out)
    elif hasattr(out, "model_dump"):
        data = out.model_dump()
    else:
        data = vars(out)
    data["admin_wa"] = _get_setting("admin_wa", ADMIN_WA)
    data["admin_name"] = _get_setting("admin_name", "Admin")
    data["accepted_at"] = proposal.accepted_at
    data["rejected_at"] = proposal.rejected_at
    data["discount_expires_at"] = proposal.discount_expires_at
    return data



@router.get("/api/proposals/{slug}/social-proof")
def get_proposal_social_proof(slug: str, db: Session = Depends(get_db)):
    count = db.query(Contact).count()
    # Return banded count to avoid disclosing exact business size
    if count >= 100:
        banded = "100+"
    elif count >= 50:
        banded = "50+"
    elif count >= 20:
        banded = "20+"
    elif count >= 10:
        banded = "10+"
    else:
        banded = str(count)
    return {"client_count": count, "client_count_display": banded}



@router.get("/r/{slug}")
def report_og_redirect(slug: str, request: Request, db: Session = Depends(get_db)):
    frontend_url = _get_setting("frontend_url", os.environ.get("FRONTEND_URL", "https://kantorteman.my.id"))
    report_url = f"{frontend_url}/report/{slug}"

    proposal = db.query(Proposal).filter(Proposal.slug == slug, Proposal.status == "Report").first()
    if not proposal:
        return RedirectResponse(url=report_url, status_code=307)

    lead = db.query(Lead).filter(Lead.id == proposal.lead_id).first()
    business_name = lead.business_name if lead else "Bisnis Anda"
    category = lead.product_interest if lead else ""

    title = f"Hasil Audit Digital: {html_mod.escape(business_name)}"
    description = f"Kami menemukan masalah kritis pada {html_mod.escape(business_name)} yang membuat calon pelanggan lari ke kompetitor. Lihat laporan lengkap dan solusi yang kami rekomendasikan."
    og_image = f"https://api.kantorteman.my.id/api/og-image/{slug}"

    ua = (request.headers.get("user-agent") or "").lower()
    is_bot = any(b in ua for b in ["whatsapp", "facebookexternalhit", "telegrambot", "twitterbot", "linkedinbot", "slackbot", "bot", "crawler", "spider"])

    if not is_bot:
        return RedirectResponse(url=report_url, status_code=307)

    html = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>{title}</title>
<meta property="og:title" content="{title}">
<meta property="og:description" content="{description}">
<meta property="og:image" content="{og_image}">
<meta property="og:url" content="https://api.kantorteman.my.id/r/{slug}">
<meta property="og:type" content="article">
<meta property="og:site_name" content="Kantor Teman">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{title}">
<meta name="twitter:description" content="{description}">
<meta name="twitter:image" content="{og_image}">
<meta http-equiv="refresh" content="0;url={report_url}">
</head>
<body><p>Redirecting to <a href="{report_url}">{report_url}</a>...</p></body>
</html>"""
    return HTMLResponse(content=html, status_code=200)



@router.get("/api/proposals/public/by-slug/{slug}")
def get_public_proposal_by_slug(slug: str, db: Session = Depends(get_db)):
    proposal = db.query(Proposal).filter(Proposal.slug == slug).first()
    if not proposal:
        raise HTTPException(status_code=404, detail="Proposal tidak ditemukan")
    lead = db.query(Lead).filter(Lead.id == proposal.lead_id).first()

    now = datetime.now(timezone.utc)
    is_discount_expired = False
    active_price = proposal.discount_price or proposal.total_price
    if proposal.discount_expires_at:
        try:
            expires = datetime.fromisoformat(proposal.discount_expires_at.replace("Z", "+00:00"))
            if now > expires:
                is_discount_expired = True
                active_price = proposal.base_price or proposal.total_price
        except Exception:
            pass

    competitor_count = 0
    city = ""
    if lead and lead.address:
        city = lead.address.split(",")[-1].strip() if "," in (lead.address or "") else lead.address
    if lead and lead.product_interest and city:
        competitor_count = db.query(Lead).filter(
            Lead.product_interest == lead.product_interest,
            Lead.address.contains(city),
            Lead.id != lead.id,
            Lead.is_archived == False,
        ).count()

    services = json.loads(proposal.services_detail) if proposal.services_detail else []

    return {
        "id": proposal.id,
        "slug": proposal.slug,
        "business_name": lead.business_name if lead else None,
        "phone_number": lead.phone_number if lead else None,
        "address": lead.address if lead else None,
        "category": lead.product_interest if lead else None,
        "google_rating": getattr(lead, "google_rating", None) if lead else (getattr(lead, "rating", None) if lead else None),
        "review_count": getattr(lead, "review_count", None) if lead else None,
        "website_url": getattr(lead, "website_url", None) if lead else None,
        "rating": (getattr(lead, "google_rating", None) or getattr(lead, "rating", None)) if lead else None,
        "services_detail": services,
        "total_price": proposal.total_price,
        "base_price": proposal.base_price,
        "discount_price": proposal.discount_price,
        "discount_expires_at": proposal.discount_expires_at,
        "is_discount_expired": is_discount_expired,
        "active_price": active_price,
        "additional_options": proposal.additional_options,
        "status": proposal.status,
        "created_at": proposal.created_at,
        "accepted_at": proposal.accepted_at,
        "rejected_at": proposal.rejected_at,
        "competitor_count": competitor_count,
        "timeline_data": sorted(json.loads(proposal.timeline_data), key=lambda x: x["sequence"]) if proposal.timeline_data else [],
    }


class ProposalAcceptIn(BaseModel):
    client_name: str
    client_phone: str
    accept_notes: Optional[str] = None


class ProposalRejectIn(BaseModel):
    reason: Optional[str] = None


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
        # Web detection: "Web Starter", "Website", "Web Pro", etc.
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
    # Priority 1: project start/end dates if both provided
    months = _months_between_dates(project_start, project_end)
    if months:
        return months
    # Priority 2: ROI retainer period / comparison period
    if proposal.roi_data:
        try:
            roi = json.loads(proposal.roi_data) if isinstance(proposal.roi_data, str) else proposal.roi_data
            if roi.get("retainer_period"):
                return int(roi["retainer_period"])
            if roi.get("comparison_period"):
                return int(roi["comparison_period"])
        except Exception:
            pass
    # Priority 3: timeline data length
    if proposal.timeline_data:
        try:
            tl = json.loads(proposal.timeline_data) if isinstance(proposal.timeline_data, str) else proposal.timeline_data
            if tl:
                return max(1, len(tl))
        except Exception:
            pass
    # Fallback: service-type defaults
    for s in services:
        name = (s.get("name") or "").lower()
        if "seo" in name or "sosmed" in name or "kelola" in name:
            return 6
        if "maintenance" in name:
            return 1
    return 2



@router.post("/api/proposals/public/{slug}/accept")
def accept_proposal(slug: str, body: ProposalAcceptIn, db: Session = Depends(get_db)):
    proposal = db.query(Proposal).filter(Proposal.slug == slug).first()
    if not proposal:
        raise HTTPException(status_code=404, detail="Proposal tidak ditemukan")
    try:
        return accept_proposal_workflow(db, proposal, body.client_name, body.client_phone, body.accept_notes)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))



@router.post("/api/proposals/public/{slug}/reject")
def reject_proposal(slug: str, body: ProposalRejectIn, db: Session = Depends(get_db)):
    proposal = db.query(Proposal).filter(Proposal.slug == slug).first()
    if not proposal:
        raise HTTPException(status_code=404, detail="Proposal tidak ditemukan")
    if proposal.status == "rejected":
        return {"success": True, "already_rejected": True}
    if proposal.status == "accepted":
        raise HTTPException(status_code=400, detail="Proposal sudah diterima")

    proposal.status = "rejected"
    proposal.rejected_at = datetime.now(timezone.utc).isoformat()
    db.commit()
    return {"success": True, "already_rejected": False}



@router.get("/api/proposals/public/report/{slug}")
def get_public_report_by_slug(slug: str, request: Request, db: Session = Depends(get_db)):
    proposal = db.query(Proposal).filter(Proposal.slug == slug).first()
    if not proposal:
        raise HTTPException(status_code=404, detail="Report tidak ditemukan")

    lead = db.query(Lead).filter(Lead.id == proposal.lead_id).first()
    record_report_open(db, proposal, lead, request)
    db.refresh(proposal)

    now = datetime.now(timezone.utc)
    is_discount_expired = False
    active_price = proposal.discount_price or proposal.total_price

    # Hitung deadline dari first_viewed_at + 24 jam
    discount_deadline = None
    if proposal.first_viewed_at:
        try:
            first_view = datetime.fromisoformat(proposal.first_viewed_at.replace("Z", "+00:00"))
            discount_deadline = (first_view + timedelta(hours=24)).isoformat()
            if now > first_view + timedelta(hours=24):
                is_discount_expired = True
                active_price = proposal.base_price or proposal.total_price
        except Exception:
            pass

    competitor_count = 0
    city = ""
    if lead and lead.address:
        city = lead.address.split(",")[-1].strip() if "," in (lead.address or "") else lead.address
    if lead and lead.product_interest and city:
        competitor_count = db.query(Lead).filter(
            Lead.product_interest == lead.product_interest,
            Lead.address.contains(city),
            Lead.id != lead.id,
            Lead.is_archived == False,
        ).count()

    # Data performa digital dari AI Scraper
    digital_analysis = None
    if lead:
        analysis_row = db.query(LeadAnalysis).filter(LeadAnalysis.lead_id == lead.id).order_by(LeadAnalysis.id.desc()).first()
        if analysis_row:
            digital_analysis = {
                "analysis": analysis_row.analysis,
                "pain_points": json.loads(analysis_row.pain_points) if analysis_row.pain_points else [],
                "suggested_product": analysis_row.suggested_product,
                "analyzed_at": analysis_row.analyzed_at,
            }

    services = json.loads(proposal.services_detail) if proposal.services_detail else []

    return {
        "id": proposal.id,
        "slug": proposal.slug,
        "nama_usaha": lead.business_name if lead else None,
        "phone_number": lead.phone_number if lead else None,
        "address": lead.address if lead else None,
        "category": lead.product_interest if lead else None,
        "services_detail": services,
        "total_price": proposal.total_price,
        "base_price": proposal.base_price,
        "discount_price": proposal.discount_price,
        "discount_expires_at": discount_deadline,
        "is_discount_expired": is_discount_expired,
        "active_price": active_price,
        "first_viewed_at": proposal.first_viewed_at,
        "report_open_count": proposal.report_open_count or 0,
        "last_report_viewed_at": proposal.last_report_viewed_at,
        "max_report_duration_seconds": proposal.max_report_duration_seconds or 0,
        "additional_options": proposal.additional_options,
        "status": proposal.status,
        "created_at": proposal.created_at,
        "competitor_count": competitor_count,
        "digital_analysis": digital_analysis,
        "faqs": json.loads(proposal.faqs) if proposal.faqs else [],
        "monthly_search_volume": get_monthly_search_volume(
            lead.product_interest or "",
            city if lead and lead.address else ""
        ) if lead else 500,
        "selected_addons": (
            json.loads(proposal.selected_addons)
            if proposal.selected_addons and proposal.selected_addons not in ("[]", "null", "")
            else [
                {"id": s.get("id") or f"svc-{i}", "name": s.get("name"), "price": s.get("price") or 0}
                for i, s in enumerate(services[:3])
                if s.get("name")
            ]
        ),
        "timeline_data": sorted(json.loads(proposal.timeline_data), key=lambda x: x["sequence"]) if proposal.timeline_data else [],
        "admin_wa": _get_setting("admin_wa", ADMIN_WA),
        "admin_name": _get_setting("admin_name", "Admin"),
    }



@router.post("/api/proposals/public/report/{slug}/engage")
def engage_report(slug: str, db: Session = Depends(get_db)):
    proposal = db.query(Proposal).filter(Proposal.slug == slug).first()
    if not proposal:
        raise HTTPException(status_code=404, detail="Report tidak ditemukan")
    lead = db.query(Lead).filter(Lead.id == proposal.lead_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead tidak ditemukan")
    record_report_activity(db, proposal, lead, "CTA_CLICKED")
    return {"success": True, "status": lead.status}


def is_valid_customer_request(request: Request) -> bool:
    ua = (request.headers.get("user-agent") or "").lower()
    bot_signatures = ["whatsapp", "facebookexternalhit", "googlebot", "telegrambot", "twitterbot"]
    for sig in bot_signatures:
        if sig in ua:
            return False
    auth_header = request.headers.get("authorization") or ""
    if auth_header.startswith("Bearer "):
        token = auth_header.split(" ", 1)[1]
        try:
            jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
            return False
        except Exception:
            pass
    return True


SCORE_MAP = {
    "LINK_CLICKED": 30,
    "ROI_SLIDER_VIEWED": 25,
    "SHARE_PARTNER_CLICKED": 20,
    "IS_MOBILE": 10,
}


class TrackActivityBody(BaseModel):
    activity_type: str



@router.post("/api/proposals/public/report/{slug}/track-activity")
def track_activity(slug: str, body: TrackActivityBody, request: Request, db: Session = Depends(get_db)):
    if not is_valid_report_viewer(request):
        return {"success": True, "filtered": True}
    proposal = db.query(Proposal).filter(Proposal.slug == slug).first()
    if not proposal:
        raise HTTPException(status_code=404, detail="Report tidak ditemukan")
    lead = db.query(Lead).filter(Lead.id == proposal.lead_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead tidak ditemukan")
    return record_report_activity(db, proposal, lead, body.activity_type)



@router.get("/api/proposals/client/{lead_id}", response_model=list[ProposalOut])
def get_proposals_by_client(lead_id: int, source: str = Query(None), current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    lead = None
    if source == "contact":
        contact = db.query(Contact).filter(Contact.id == lead_id).first()
        if contact:
            lead = db.query(Lead).filter(Lead.phone_number == contact.phone_number).first()
    else:
        lead = db.query(Lead).filter(Lead.id == lead_id).first()
        if not lead:
            contact = db.query(Contact).filter(Contact.id == lead_id).first()
            if contact:
                lead = db.query(Lead).filter(Lead.phone_number == contact.phone_number).first()
    if not lead:
        return []
    proposals = db.query(Proposal).filter(Proposal.lead_id == lead.id).all()
    return [_proposal_to_out(p, lead) for p in proposals]



@router.get("/api/proposals", response_model=list[ProposalOut])
def get_proposals(include_archived: bool = Query(False), current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    query = db.query(Proposal).options(joinedload(Proposal.lead))
    if not include_archived:
        query = query.filter(Proposal.is_archived == False)
    proposals = query.all()
    results = []
    for p in proposals:
        results.append(_proposal_to_out(p, p.lead))
    return results



@router.delete("/api/proposals/{proposal_id}", status_code=204)
def delete_proposal(proposal_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    proposal = db.query(Proposal).filter(Proposal.id == proposal_id).first()
    if not proposal:
        raise HTTPException(status_code=404, detail="Proposal tidak ditemukan")
    proposal.is_archived = True
    proposal.deleted_at = datetime.now(timezone.utc).isoformat()
    db.commit()
    log_audit(db, current_user.name, "DELETE", "proposals", proposal_id, {"total_price": proposal.total_price})



@router.post("/api/proposals/restore/{proposal_id}", response_model=ProposalOut)
def restore_proposal(proposal_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    proposal = db.query(Proposal).filter(Proposal.id == proposal_id).first()
    if not proposal:
        raise HTTPException(status_code=404, detail="Proposal tidak ditemukan")
    proposal.is_archived = False
    proposal.deleted_at = None
    db.commit()
    db.refresh(proposal)
    lead = db.query(Lead).filter(Lead.id == proposal.lead_id).first()
    log_audit(db, current_user.name, "RESTORE", "proposals", proposal_id, {})
    return _proposal_to_out(proposal, lead)


# ---------------------------------------------------------------------------
# Service Items (Daftar Jasa Dasar)
# ---------------------------------------------------------------------------


@router.post("/api/proposals/track/open")
async def track_open(body: TrackOpenIn, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):

    proposal = db.query(Proposal).filter(Proposal.id == body.proposal_id).first()
    if not proposal:
        raise HTTPException(status_code=404, detail="Proposal tidak ditemukan")
    lead = db.query(Lead).filter(Lead.id == proposal.lead_id).first()
    analytics = ProposalAnalytics(
        id=str(uuid.uuid4()),
        proposal_id=body.proposal_id,
        opened_at=datetime.now(timezone.utc).isoformat(),
        total_time_seconds=0,
        sections_viewed="[]",
    )
    db.add(analytics)
    db.commit()
    db.refresh(analytics)

    # Send WA notification to admin
    fonnte_token = get_fonnte_token(db)
    business_name = lead.business_name if lead else "Unknown"
    services = [s["name"] for s in json.loads(proposal.services_detail)]
    service_names = ", ".join(services) if services else "—"
    message = f"[ALERT] Mind Reader: Klien {business_name} sedang membuka proposal [{service_names}] SEKARANG!"
    admin_wa = _get_setting("admin_wa", ADMIN_WA)
    background_tasks.add_task(send_fonnte_message, admin_wa, message, fonnte_token)

    # Behavioral signal: proposal viewed +15 (idempotent)
    if lead:
        _apply_proposal_signal(lead.id, "score_proposal_viewed", 15, db)

    # Re-engagement alert: if first viewed > 7 days ago
    if proposal.first_viewed_at and lead:
        try:
            first_view = datetime.fromisoformat(proposal.first_viewed_at.replace("Z", "+00:00"))
            if (datetime.now(timezone.utc) - first_view).days >= 7:
                existing_alert = db.query(ReengagementAlert).filter(
                    ReengagementAlert.lead_id == lead.id,
                    ReengagementAlert.is_read == False,
                ).first()
                if not existing_alert:
                    db.add(ReengagementAlert(
                        id=str(uuid.uuid4()),
                        lead_id=lead.id,
                        proposal_id=proposal.id,
                        triggered_at=datetime.now(timezone.utc).isoformat(),
                    ))
                    db.commit()
        except Exception:
            pass

    return {"analytics_id": analytics.id}


class ViewDurationIn(BaseModel):
    duration_seconds: int

    @field_validator("duration_seconds")
    @classmethod
    def cap_duration(cls, v: int) -> int:
        return max(0, min(v, 3600))



@router.post("/api/proposals/{slug}/view-duration")
def track_view_duration(slug: str, body: ViewDurationIn, db: Session = Depends(get_db)):
    proposal = db.query(Proposal).filter(Proposal.slug == slug).first()
    if not proposal:
        raise HTTPException(status_code=404, detail="Proposal tidak ditemukan")
    lead = db.query(Lead).filter(Lead.id == proposal.lead_id).first()
    return record_report_duration(db, proposal, lead, body.duration_seconds)



@router.post("/api/proposals/track/ping")
def track_ping(body: TrackPingIn, db: Session = Depends(get_db)):

    analytics = db.query(ProposalAnalytics).filter(ProposalAnalytics.id == body.analytics_id).first()
    if not analytics:
        raise HTTPException(status_code=404, detail="Analytics record tidak ditemukan")
    analytics.last_ping = datetime.now(timezone.utc).isoformat()
    prev_total = analytics.total_time_seconds or 0
    analytics.total_time_seconds = prev_total + body.seconds
    existing_sections = json.loads(analytics.sections_viewed or "[]")
    for s in body.sections_viewed:
        if s not in existing_sections:
            existing_sections.append(s)
    analytics.sections_viewed = json.dumps(existing_sections)
    db.commit()

    # Apply engaged signal once when total crosses 180s
    if prev_total <= 180 and analytics.total_time_seconds > 180:
        proposal = db.query(Proposal).filter(Proposal.id == analytics.proposal_id).first()
        if proposal:
            lead = db.query(Lead).filter(Lead.id == proposal.lead_id).first()
            if lead:
                _apply_proposal_signal(
                    lead.id,
                    "score_proposal_engaged",
                    25,
                    db,
                    replace_signal="score_proposal_viewed",
                )

    return {"ok": True, "total_time_seconds": analytics.total_time_seconds}



@router.get("/api/proposals/{proposal_id}/analytics")
def get_proposal_analytics(proposal_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):

    records = db.query(ProposalAnalytics).filter(ProposalAnalytics.proposal_id == proposal_id).all()
    return [{
        "id": r.id,
        "proposal_id": r.proposal_id,
        "opened_at": r.opened_at,
        "last_ping": r.last_ping,
        "total_time_seconds": r.total_time_seconds,
        "sections_viewed": json.loads(r.sections_viewed or "[]"),
        "event": r.event,
        "duration_seconds": r.duration_seconds,
        "source": r.source,
    } for r in records]



@router.get("/api/proposals/analytics/all")
def get_all_proposal_analytics(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    results = []
    # Eager load proposals to avoid N+1 on analytics queries
    proposals = db.query(Proposal).all()
    proposal_ids = [p.id for p in proposals]

    # Bulk fetch all analytics records
    all_analytics = db.query(ProposalAnalytics).filter(
        ProposalAnalytics.proposal_id.in_(proposal_ids)
    ).all()

    # Group by proposal_id
    analytics_by_proposal = {}
    for record in all_analytics:
        if record.proposal_id not in analytics_by_proposal:
            analytics_by_proposal[record.proposal_id] = []
        analytics_by_proposal[record.proposal_id].append(record)

    for p in proposals:
        records = analytics_by_proposal.get(p.id, [])
        total_opens = len([r for r in records if (r.event or "proposal_opened") in ("proposal_opened", "report_opened", None)])
        total_time = sum(r.total_time_seconds or 0 for r in records)
        last_opened = max((r.opened_at for r in records), default=None) if records else None
        results.append({
            "proposal_id": p.id,
            "total_opens": total_opens,
            "total_time_seconds": total_time,
            "last_opened": last_opened,
        })
    return results


# ---------------------------------------------------------------------------
# Analytics
# ---------------------------------------------------------------------------
