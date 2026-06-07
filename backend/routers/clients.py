import re, html as html_mod, random, asyncio, uuid, json, csv, io, base64, hmac, time, httpx
import os
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv
from fastapi import APIRouter, Depends, HTTPException, Request, BackgroundTasks, UploadFile, File, Form, Query, Body
from fastapi.responses import StreamingResponse, RedirectResponse, HTMLResponse, Response
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from typing import Optional, List, Any
from models import get_db, log_audit, User, Lead, Contact, Project, Transaction, ClientNote, Proposal, ProposalAnalytics, AuditLog, LeadActivityLog
from schemas import *
from app.core.dependencies import get_current_user, require_admin

router = APIRouter()

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
    projects_out = [{
        "id": p.id, "name": p.name, "type": p.type, "status": p.status,
        "nominal": p.nominal, "start_date": p.start_date, "end_date": p.end_date,
    } for p in client_projects]

    # LTV: For FIXED = nominal, For RETAINER = nominal × months elapsed since start
    ltv = 0
    for p in client_projects:
        if p.status not in ("ACTIVE", "COMPLETED"):
            continue
        if p.type == "RETAINER" and p.start_date:
            start = datetime.strptime(p.start_date, "%Y-%m-%d")
            now = datetime.now()
            months_elapsed = (now.year - start.year) * 12 + (now.month - start.month) + 1
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
            "business_name": contact.business_name,
            "owner_name": contact.owner_name,
            "phone_number": contact.phone_number,
            "purchased_product": contact.purchased_product,
            "notes": contact.notes,
        },
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


