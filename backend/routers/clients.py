import re, html as html_mod, random, asyncio, uuid, json, csv, io, base64, hmac, time, httpx
import os
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv
from fastapi import APIRouter, Depends, HTTPException, Request, BackgroundTasks, UploadFile, File, Form, Query, Body
from fastapi.responses import StreamingResponse, RedirectResponse, HTMLResponse, Response
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from typing import Optional, List, Any
from models import get_db, log_audit, User, Lead, Contact, Project, Transaction, ClientNote, Proposal, ProposalAnalytics, AuditLog, LeadActivityLog, ClientAttributionGBP
from schemas import *
from app.core.dependencies import get_current_user, require_admin

router = APIRouter()


GBP_UTM_PARAMETERS = (
    ("utm_source", "google"),
    ("utm_medium", "organic"),
    ("utm_campaign", "gbp"),
    ("utm_content", "website"),
)


def _canonical_gbp_url(url: str) -> tuple[str, str]:
    """Validate a canonical landing URL and derive the offline GBP UTM URL."""
    canonical = url.strip()
    if any(ord(char) < 32 or char.isspace() for char in canonical):
        raise HTTPException(status_code=400, detail="URL landing kanonik tidak boleh memuat spasi atau karakter kontrol")
    try:
        parsed = urlsplit(canonical)
        # Accessing port forces urllib to reject malformed port numbers.
        parsed.port
    except ValueError:
        raise HTTPException(status_code=400, detail="URL landing kanonik tidak valid")
    if parsed.scheme.lower() != "https" or not parsed.netloc or not parsed.hostname:
        raise HTTPException(status_code=400, detail="URL landing kanonik harus menggunakan HTTPS")
    if parsed.username or parsed.password:
        raise HTTPException(status_code=400, detail="URL landing kanonik tidak boleh memuat kredensial")
    if parsed.fragment:
        raise HTTPException(status_code=400, detail="URL landing kanonik tidak boleh memiliki fragment")
    try:
        query_pairs = parse_qsl(parsed.query, keep_blank_values=True)
    except ValueError:
        raise HTTPException(status_code=400, detail="Query URL landing kanonik tidak valid")
    if any(key.lower().startswith("utm_") for key, _ in query_pairs):
        raise HTTPException(status_code=400, detail="URL landing kanonik tidak boleh sudah memiliki parameter utm_*")
    generated = urlunsplit(("https", parsed.netloc, parsed.path, urlencode([*query_pairs, *GBP_UTM_PARAMETERS]), ""))
    return canonical, generated


def _attribution_response(record: ClientAttributionGBP | None, lead_id: int) -> dict:
    if not record:
        # Reads never create a record or infer evidence from a client identity.
        return {"lead_id": lead_id, "canonical_landing_url": None, "generated_url": None,
                "ga4_measurement_id": None, "conversion_event_name": None,
                "conversion_event_verified": False, "readiness_note": None,
                "created_at": None, "updated_at": None}
    _, generated_url = _canonical_gbp_url(record.canonical_landing_url)
    return {"lead_id": lead_id, "canonical_landing_url": record.canonical_landing_url,
            "generated_url": generated_url, "ga4_measurement_id": record.ga4_measurement_id,
            "conversion_event_name": record.conversion_event_name,
            "conversion_event_verified": record.conversion_event_verified,
            "readiness_note": record.readiness_note, "created_at": record.created_at,
            "updated_at": record.updated_at}


def _resolve_client_lead(client_id: int, db: Session) -> Lead:
    contact = db.query(Contact).filter(Contact.id == client_id).first()
    if not contact:
        raise HTTPException(status_code=404, detail="Klien tidak ditemukan")
    if not contact.lead_id:
        raise HTTPException(status_code=404, detail="Klien belum memiliki relasi lead")
    lead = db.query(Lead).filter(Lead.id == contact.lead_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead klien tidak ditemukan")
    return lead


@router.get("/api/clients/{client_id}/attribution-gbp")
def get_client_attribution_gbp(client_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    lead = _resolve_client_lead(client_id, db)
    record = db.query(ClientAttributionGBP).filter(ClientAttributionGBP.lead_id == lead.id).first()
    return _attribution_response(record, lead.id)


@router.put("/api/clients/{client_id}/attribution-gbp")
def put_client_attribution_gbp(client_id: int, body: ClientAttributionGBPIn, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    lead = _resolve_client_lead(client_id, db)
    canonical_url, _ = _canonical_gbp_url(body.canonical_landing_url)
    measurement_id = body.ga4_measurement_id.strip().upper() if body.ga4_measurement_id else None
    if measurement_id and not re.fullmatch(r"G-[A-Z0-9]+", measurement_id):
        raise HTTPException(status_code=400, detail="GA4 measurement ID harus berformat G-XXXXXXXX")
    record = db.query(ClientAttributionGBP).filter(ClientAttributionGBP.lead_id == lead.id).first()
    if not record:
        record = ClientAttributionGBP(lead_id=lead.id, canonical_landing_url=canonical_url)
        db.add(record)
    record.canonical_landing_url = canonical_url
    record.ga4_measurement_id = measurement_id
    record.conversion_event_name = body.conversion_event_name.strip() if body.conversion_event_name else None
    record.conversion_event_verified = body.conversion_event_verified
    record.readiness_note = body.readiness_note.strip() if body.readiness_note else None
    db.commit()
    db.refresh(record)
    # This endpoint only stores evidence and derives URL text; it makes no external calls.
    return _attribution_response(record, lead.id)


@router.get("/api/clients/detail/{client_id}")
def get_client_detail(client_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    contact = db.query(Contact).filter(Contact.id == client_id).first()
    if not contact:
        raise HTTPException(status_code=404, detail="Klien tidak ditemukan")

    # Resolve lead_id via FK (contact.lead_id)
    lead_id = contact.lead_id
    # Fallback: if lead_id not set, try phone lookup for backward compat
    if not lead_id:
        lead = db.query(Lead).filter(Lead.phone_number == contact.phone_number).first()
        lead_id = lead.id if lead else None

    # Projects (linked via lead_id, not contact_id)
    client_projects = db.query(Project).filter(Project.lead_id == lead_id).all() if lead_id else []
    client_name = contact.business_name if contact else None
    projects_out = [{
        "id": p.id, "name": p.name, "type": p.type, "status": p.status,
        "nominal": p.nominal, "start_date": p.start_date, "end_date": p.end_date,
        "service_type": p.service_type, "color": p.color,
    } for p in client_projects]

    # LTV: For FIXED = nominal, For RETAINER = nominal × months elapsed (start -> akhir kontrak)
    # RETAINER yang COMPLETED dihitung sampai end_date/completed_at (bukan sampai now),
    # yang ACTIVE dihitung sampai bulan berjalan.
    def _parse_dt(val):
        if not val:
            return None
        s = str(val)[:10]
        try:
            return datetime.strptime(s, "%Y-%m-%d")
        except Exception:
            return None

    ltv = 0
    for p in client_projects:
        if p.status not in ("ACTIVE", "COMPLETED"):
            continue
        if p.type == "RETAINER" and p.start_date:
            start = _parse_dt(p.start_date)
            if not start:
                ltv += p.nominal
                continue
            # tentukan titik akhir
            if p.status == "COMPLETED":
                end = _parse_dt(p.end_date) or _parse_dt(getattr(p, "completed_at", None)) or datetime.now()
            else:  # ACTIVE
                end = datetime.now()
            if end < start:
                end = start
            months_elapsed = (end.year - start.year) * 12 + (end.month - start.month) + 1
            if months_elapsed < 1:
                months_elapsed = 1
            ltv += p.nominal * months_elapsed
        else:
            ltv += p.nominal

    # Active billing (ACTIVE projects total)
    active_billing = sum(p.nominal for p in client_projects if p.status == "ACTIVE")

    # Dana Talangan (unbilled linked expenses) — also use lead_id
    unbilled_txns = db.query(Transaction).filter(
        Transaction.lead_id == lead_id,
        Transaction.type == "expense",
        Transaction.is_billed == False,
    ).all() if lead_id else []
    dana_talangan = sum(t.amount for t in unbilled_txns)

    # Notes (also via lead_id)
    notes = db.query(ClientNote).filter(ClientNote.lead_id == lead_id).order_by(ClientNote.id.desc()).all() if lead_id else []
    notes_out = [{
        "id": n.id, "category": n.category, "content": n.content,
        "actor": n.actor, "timestamp": n.timestamp,
    } for n in notes]

    return {
        "profile": {
            "id": contact.id,
            "lead_id": lead_id,
            "business_name": contact.business_name,
            "owner_name": contact.owner_name,
            "phone_number": contact.phone_number,
            "purchased_product": contact.purchased_product,
            "notes": contact.notes,
        },
        "lead_id": lead_id,
        "ltv": ltv,
        "active_billing": active_billing,
        "dana_talangan": dana_talangan,
        "projects": projects_out,
        "notes": notes_out,
    }



@router.get("/api/clients/{client_id}/activity-timeline")
def get_client_activity_timeline(client_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    contact = db.query(Contact).filter(Contact.id == client_id).first()
    if not contact:
        raise HTTPException(status_code=404, detail="Klien tidak ditemukan")

    lead = db.query(Lead).filter(Lead.phone_number == contact.phone_number).first()
    lead_id = lead.id if lead else None

    events = []

    # LeadActivityLog
    if lead_id:
        for log in db.query(LeadActivityLog).filter(LeadActivityLog.lead_id == lead_id).order_by(LeadActivityLog.created_at.desc()).limit(50).all():
            label_map = {
                "WA_REPLIED": "Membalas pesan WA",
                "pdf_opened": "Membuka dokumen PDF",
                "pdf_downloaded": "Mengunduh dokumen PDF",
                "PROPOSAL_VIEWED": "Membuka proposal",
                "PROPOSAL_ENGAGED": "Membaca proposal >3 menit",
                "HOT_PROSPECT": "Melihat bagian ROI proposal",
            }
            events.append({
                "type": "activity",
                "icon": "💬" if "WA" in log.activity_type else "📄",
                "label": label_map.get(log.activity_type, log.activity_type),
                "timestamp": log.created_at,
            })

    # ProposalAnalytics
    if lead_id:
        proposals = db.query(Proposal).filter(Proposal.lead_id == lead_id).all()
        proposal_ids = [p.id for p in proposals]
        if proposal_ids:
            from collections import defaultdict
            analytics = db.query(ProposalAnalytics).filter(ProposalAnalytics.proposal_id.in_(proposal_ids)).order_by(ProposalAnalytics.proposal_id, ProposalAnalytics.opened_at.desc()).all()
            analytics_by_proposal = defaultdict(list)
            for pa in analytics:
                analytics_by_proposal[pa.proposal_id].append(pa)
            
            for p in proposals:
                for pa in analytics_by_proposal[p.id][:10]:
                    secs = pa.total_time_seconds or 0
                    dur = f"{secs // 60}m {secs % 60}s" if secs >= 60 else f"{secs}s"
                    events.append({
                        "type": "proposal_view",
                        "icon": "👁️",
                        "label": f"Membuka proposal — durasi {dur}",
                        "timestamp": pa.opened_at,
                    })

    # Transactions tagged to lead
    if lead_id:
        for txn in db.query(Transaction).filter(Transaction.lead_id == lead_id, Transaction.deleted_at == None).order_by(Transaction.date.desc()).limit(20).all():
            sign = "+" if txn.type == "income" else "-"
            events.append({
                "type": "transaction",
                "icon": "💰",
                "label": f"{txn.category or txn.type} {sign}Rp {txn.amount:,.0f}" + (f" — {txn.notes}" if txn.notes else ""),
                "timestamp": txn.date,
            })

    # AuditLog for this contact record
    for al in db.query(AuditLog).filter(
        AuditLog.table_name.in_(["contacts", "leads", "projects"]),
        AuditLog.record_id == str(client_id),
    ).order_by(AuditLog.timestamp.desc()).limit(20).all():
        events.append({
            "type": "audit",
            "icon": "📝",
            "label": f"{al.action} oleh {al.actor}",
            "timestamp": al.timestamp,
        })

    events.sort(key=lambda e: e["timestamp"] or "", reverse=True)
    return events[:60]


# ---------------------------------------------------------------------------
# Audit Logs
# ---------------------------------------------------------------------------


@router.get("/api/clients/notes/{client_id}", response_model=list[ClientNoteOut])
def get_client_notes_by_path(client_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    # client_id may be a contact.id — resolve to lead_id first
    contact = db.query(Contact).filter(Contact.id == client_id).first()
    if contact:
        lead_id = contact.lead_id
        if not lead_id:
            lead = db.query(Lead).filter(Lead.phone_number == contact.phone_number).first()
            lead_id = lead.id if lead else None
        if lead_id:
            return db.query(ClientNote).filter(ClientNote.lead_id == lead_id).order_by(ClientNote.id.desc()).all()
    # Fallback: treat as direct lead_id
    return db.query(ClientNote).filter(ClientNote.lead_id == client_id).order_by(ClientNote.id.desc()).all()



@router.post("/api/clients/notes", response_model=ClientNoteOut, status_code=201)
def create_client_note_alias(body: ClientNoteIn, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if body.category not in ("BISNIS", "TEKNIS", "PENTING"):
        raise HTTPException(status_code=400, detail="Category harus 'BISNIS', 'TEKNIS', atau 'PENTING'")
    note = ClientNote(
        id=str(uuid.uuid4()),
        lead_id=body.lead_id,
        timestamp=datetime.now(timezone.utc).isoformat(),
        actor=current_user.name,
        category=body.category,
        content=body.content,
    )
    db.add(note)
    db.commit()
    db.refresh(note)
    return note


# ---------------------------------------------------------------------------
# Credentials Vault (Encrypted)
# ---------------------------------------------------------------------------


