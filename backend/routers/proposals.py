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
    get_fonnte_token, _send_fonnte_sync,
)

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
        roi_data=_build_roi_data(db, body.services, body.roi_data),
    )
    db.add(proposal)
    db.commit()
    db.refresh(proposal)
    log_audit(db, current_user.name, "CREATE", "proposals", proposal.id, {"lead": lead.business_name, "total": total})
    return _proposal_to_out(proposal, lead)



@router.get("/api/proposals/public/{proposal_id}")
def get_public_proposal(proposal_id: str, db: Session = Depends(get_db)):
    proposal = db.query(Proposal).filter(Proposal.id == proposal_id).first()
    if not proposal:
        raise HTTPException(status_code=404, detail="Proposal tidak ditemukan")
    lead = db.query(Lead).filter(Lead.id == proposal.lead_id).first()
    out = _proposal_to_out(proposal, lead)
    data = out.model_dump() if hasattr(out, "model_dump") else out.__dict__
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
    import threading, httpx as _httpx

    proposal = db.query(Proposal).filter(Proposal.slug == slug).first()
    if not proposal:
        raise HTTPException(status_code=404, detail="Proposal tidak ditemukan")
    if proposal.status == "accepted":
        project = db.query(Project).filter(Project.lead_id == proposal.lead_id).order_by(Project.id.desc()).first()
        return {"success": True, "project_id": project.id if project else None, "already_accepted": True}
    if proposal.status == "rejected":
        raise HTTPException(status_code=400, detail="Proposal sudah ditolak")

    lead = db.query(Lead).filter(Lead.id == proposal.lead_id).first()
    now = datetime.now(timezone.utc).isoformat()

    proposal.status = "accepted"
    proposal.accepted_at = now

    if lead and lead.status not in ("Closed/Client", "Active Client"):
        lead.status = "Closed/Client"

    services = json.loads(proposal.services_detail) if proposal.services_detail else []
    project_type = _detect_project_type(services)
    detected_service_type = _detect_service_type(services)
    detected_months = _detect_contract_months(proposal, services, now[:10], None)
    active_price = proposal.discount_price or proposal.total_price
    business_name = lead.business_name if lead else body.client_name
    service_names = ", ".join(s.get("name", "") for s in services[:2])
    project_name = f"{service_names} — {business_name}" if service_names else f"Project {business_name}"

    project = Project(
        id=str(uuid.uuid4()),
        lead_id=proposal.lead_id,
        name=project_name,
        type=project_type,
        status="ACTIVE",
        nominal=active_price,
        start_date=now[:10],
        color="yellow",
        service_type=detected_service_type,
        contract_months=detected_months,
    )
    db.add(project)
    db.flush()

    board = Board(id=str(uuid.uuid4()), project_id=project.id)
    db.add(board)
    db.flush()

    todo_col_id = None
    for i, (col_name, col_color) in enumerate([("To Do", "yellow"), ("In Progress", "blue"), ("Review", "purple"), ("Done", "green")]):
        col = BoardColumn(id=str(uuid.uuid4()), board_id=board.id, name=col_name, position=i, color=col_color)
        db.add(col)
        if col_name == "To Do":
            todo_col_id = col.id

    _ONBOARDING_BASE = [
        "Kick-off call dengan klien",
        "Kumpulkan requirement & brief",
        "Approval timeline & milestone",
        "Kirim deliverable pertama",
    ]
    _ONBOARDING_SERVICE = {
        "web_dev":   ["Setup domain & hosting", "Wireframe approval", "Development sprint 1"],
        "seo_gmaps": ["Audit website awal", "Riset keyword", "On-page optimization"],
        "sosmed":    ["Content calendar approval", "Desain template feed", "Posting perdana"],
        "maintenance": ["Inventarisasi aset klien", "Setup monitoring", "Laporan kondisi awal"],
    }
    if todo_col_id:
        now_cards = datetime.now(timezone.utc).isoformat()
        card_titles = _ONBOARDING_BASE + _ONBOARDING_SERVICE.get(detected_service_type or "", [])
        for pos, title in enumerate(card_titles):
            db.add(BoardCard(
                id=str(uuid.uuid4()),
                column_id=todo_col_id,
                title=title,
                labels=json.dumps(["onboarding"]),
                position=pos,
                updated_at=now_cards,
            ))

    db.commit()

    # Auto-init workspace if service_type detected
    if detected_service_type and detected_service_type in WORKSPACE_TEMPLATES:
        try:
            sheet_defs = build_sheets_for_service(detected_service_type, detected_months)
            now_ws = datetime.now(timezone.utc).isoformat()
            for idx, sdef in enumerate(sheet_defs):
                sheet = WorkspaceSheet(
                    id=str(uuid.uuid4()), project_id=project.id,
                    sheet_index=idx, sheet_label=sdef["label"],
                    service_type=detected_service_type, month_number=sdef.get("month"),
                    created_at=now_ws,
                )
                db.add(sheet)
                db.flush()
                col_map = {}
                for ci, cdef in enumerate(sdef["columns"]):
                    col = WorkspaceColumn(
                        id=str(uuid.uuid4()), sheet_id=sheet.id,
                        column_key=cdef["key"], column_label=cdef["label"],
                        column_type=cdef["type"], column_options=json.dumps(cdef.get("options", [])),
                        column_order=ci, is_system=cdef.get("is_system", False), created_at=now_ws,
                    )
                    db.add(col)
                    db.flush()
                    col_map[cdef["key"]] = col
                for ri, rdef in enumerate(sdef.get("default_rows", [])):
                    row = WorkspaceRow(id=str(uuid.uuid4()), sheet_id=sheet.id, row_order=ri, is_template=True, created_at=now_ws)
                    db.add(row)
                    db.flush()
                    for key, val in rdef.items():
                        col = col_map.get(key)
                        if not col:
                            continue
                        cell = WorkspaceCell(id=str(uuid.uuid4()), row_id=row.id, column_id=col.id, updated_at=now_ws)
                        if col.column_type == "checkbox":
                            cell.value_bool = bool(val)
                        elif col.column_type == "number":
                            cell.value_number = float(val) if val else None
                        else:
                            cell.value_text = str(val) if val else None
                        db.add(cell)
                    db.flush()
                    sync_row_to_board(row.id, db)
            db.commit()
        except Exception as e:
            print(f"[ACCEPT_AUTO_WORKSPACE] error: {e}", flush=True)
            try: db.rollback()
            except Exception: pass

    fonnte_token = get_fonnte_token(db)
    admin_wa = _get_setting("admin_wa", ADMIN_WA)
    msg = (
        f"✅ *Proposal Diterima!*\n\n"
        f"Klien: *{business_name}*\n"
        f"Nama: {body.client_name}\n"
        f"WA: {body.client_phone}\n"
        f"Layanan: {service_names or '-'}\n"
        f"Nilai: Rp {int(active_price):,}\n"
        f"Tipe: {project_type}\n"
        f"Project ID: {project.id[:8]}...\n\n"
        f"Project & board sudah dibuat otomatis."
    )
    if body.accept_notes:
        msg += f"\n\nCatatan klien: {body.accept_notes}"

    threading.Thread(
        target=_send_fonnte_sync,
        args=(admin_wa, msg, fonnte_token, _httpx),
        daemon=True,
    ).start()

    return {"success": True, "project_id": project.id, "already_accepted": False}



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
def get_public_report_by_slug(slug: str, db: Session = Depends(get_db)):
    proposal = db.query(Proposal).filter(Proposal.slug == slug).first()
    if not proposal:
        raise HTTPException(status_code=404, detail="Report tidak ditemukan")

    # Set first_viewed_at on first open (lock di database)
    if not proposal.first_viewed_at:
        proposal.first_viewed_at = datetime.now(timezone.utc).isoformat()
        db.commit()
        db.refresh(proposal)

    lead = db.query(Lead).filter(Lead.id == proposal.lead_id).first()

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
        "selected_addons": json.loads(proposal.selected_addons) if proposal.selected_addons and proposal.selected_addons != "[]" else [{"id": p.id, "name": p.name, "price": p.base_price} for p in db.query(Product).filter(Product.is_active == True).all()],
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
    non_upgrade_statuses = {"HOT_PROSPECT", "CLOSED"}
    if lead.status not in non_upgrade_statuses:
        lead.status = "HOT_PROSPECT"
        db.commit()
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
    if not is_valid_customer_request(request):
        return {"success": True, "filtered": True}
    proposal = db.query(Proposal).filter(Proposal.slug == slug).first()
    if not proposal:
        raise HTTPException(status_code=404, detail="Report tidak ditemukan")
    lead = db.query(Lead).filter(Lead.id == proposal.lead_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead tidak ditemukan")

    # Log activity ke LeadActivityLog (selalu insert untuk LINK_CLICKED)
    if body.activity_type == "LINK_CLICKED":
        db.add(LeadActivityLog(
            lead_id=lead.id,
            activity_type="LINK_CLICKED",
            created_at=datetime.now(timezone.utc).isoformat(),
        ))
        db.commit()

    points = SCORE_MAP.get(body.activity_type, 0)
    if points == 0:
        return {"success": True, "lead_score": lead.lead_score}
    # LINK_CLICKED score hanya ditambahkan sekali (jika score sudah >= 30, skip)
    if body.activity_type == "LINK_CLICKED" and (lead.lead_score or 0) >= 30:
        return {"success": True, "lead_score": lead.lead_score}
    new_score = min(100, (lead.lead_score or 0) + points)
    lead.lead_score = new_score
    db.commit()
    return {"success": True, "lead_score": new_score}



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

    latest = db.query(ProposalAnalytics).filter(
        ProposalAnalytics.proposal_id == proposal.id
    ).order_by(ProposalAnalytics.opened_at.desc()).first()
    if latest:
        latest.duration_seconds = max(latest.duration_seconds or 0, body.duration_seconds)
        db.commit()

    return {"success": True}



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
        total_opens = len(records)
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


