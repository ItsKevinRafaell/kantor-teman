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
from models import get_db, log_audit, User, Lead, BlastCampaign, FollowUpSequence, DynamicTemplate, BlastMessage, LeadActivityLog, Transaction, WorkspaceSheet, WorkspaceColumn, WorkspaceRow, WorkspaceCell, Board, BoardColumn, BoardCard, Project, AdsCampaign
from schemas import *
from app.core.dependencies import (get_current_user, require_admin, FONNTE_WEBHOOK_SECRET,
    GOOGLE_CALENDAR_ID, GOOGLE_SERVICE_ACCOUNT_JSON, _get_google_calendar_service,
    get_fonnte_token, _ads_out, _send_fonnte_sync, send_fonnte_message,
    _get_setting, normalize_phone, _normalize_phone, log_outreach_cost,
    WORKSPACE_TEMPLATES, build_sheets_for_service, build_sheets_for_days,
    sync_row_to_board, sync_row_status_to_board, _check_simple_rate_limit,
    _run_async_job, process_pending_blasts, _blast_jobs,
)

router = APIRouter()

@router.post("/api/campaign/blast")
async def start_blast(
    body: BlastIn,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    _check_simple_rate_limit(f"blast:{current_user.id}", 10, 60)
    import threading
    campaign = BlastCampaign(
        id=str(uuid.uuid4()),
        name=f"Blast {body.batch_name} - {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M')}",
        template_id=body.template_id,
        filter_criteria=json.dumps({
            "status": "Scraped",
            "batch_name": body.batch_name,
            "min_rating": body.min_rating,
            "product_category": body.product_category,
        }),
        scheduled_for=datetime.now(timezone.utc).isoformat(),
        status="PENDING",
        created_at=datetime.now(timezone.utc).isoformat(),
    )
    db.add(campaign)
    db.commit()
    log_audit(db, current_user.name, "CREATE", "blast_campaigns", campaign.id, {"name": campaign.name, "mode": "instant"})
    threading.Thread(target=_run_async_job, args=(process_pending_blasts,), daemon=True).start()
    return {"message": "Campaign masuk antrean pengiriman.", "batch_name": body.batch_name, "campaign_id": campaign.id}


# ---------------------------------------------------------------------------
# Public Template Endpoint (for proposal page)
# ---------------------------------------------------------------------------


@router.post("/api/webhook/fonnte-incoming")
async def fonnte_incoming(request: Request, db: Session = Depends(get_db)):
    """
    Fonnte webhook for incoming WA messages.
    Auto-update lead status to 'Replied' and update BlastMessage.replied_at.
    Configure in Fonnte dashboard: webhook URL = https://api.kantorteman.my.id/api/webhook/fonnte-incoming
    """
    try:
        payload = await request.json()
    except Exception:
        try:
            form = await request.form()
            payload = dict(form)
        except Exception:
            payload = {}

    if FONNTE_WEBHOOK_SECRET and not hmac.compare_digest(
        request.headers.get("x-fonnte-webhook-secret", ""),
        FONNTE_WEBHOOK_SECRET,
    ):
        raise HTTPException(status_code=401, detail="Webhook secret tidak valid")

    sender = payload.get("sender") or payload.get("device") or payload.get("from") or ""
    sender_digits = normalize_phone(str(sender))
    if not sender_digits:
        return {"ok": True, "skipped": "no_sender"}

    # DB stores 08xx, but might have 62xx stored. Try both formats.
    sender_08xx = sender_digits
    if sender_digits.startswith("62"):
        sender_08xx = "0" + sender_digits[2:]

    # Try 08xx first (canonical storage format), fall back to 62xx
    lead = db.query(Lead).filter(Lead.phone_number == sender_08xx).first()
    if not lead:
        lead = db.query(Lead).filter(Lead.phone_number == sender_digits).first()
    if not lead:
        return {"ok": True, "skipped": "no_lead"}

    message = str(payload.get("message") or payload.get("text") or "").strip().lower()
    opt_out_terms = {"stop", "berhenti", "unsubscribe", "jangan hubungi", "hapus nomor"}
    if any(term in message for term in opt_out_terms):
        lead.do_not_contact = True
        db.query(FollowUpSequence).filter(
            FollowUpSequence.lead_id == lead.id,
            FollowUpSequence.status == "ACTIVE",
        ).update({"status": "STOPPED", "stopped_reason": "opt_out"}, synchronize_session=False)
        db.commit()
        log_audit(db, "fonnte-webhook", "UPDATE", "leads", lead.id, {"field": "do_not_contact", "new": True, "via": "wa_opt_out"})
        return {"ok": True, "lead_id": lead.id, "do_not_contact": True}

    # Update BlastMessage.replied_at for latest sent message (check both phone formats)
    now = datetime.now(timezone.utc).isoformat()
    latest_msg = db.query(BlastMessage).filter(
        BlastMessage.phone_number == sender_08xx,
        BlastMessage.sent_at.isnot(None),
    ).order_by(BlastMessage.sent_at.desc()).first()
    if not latest_msg:
        latest_msg = db.query(BlastMessage).filter(
            BlastMessage.phone_number == sender_digits,
            BlastMessage.sent_at.isnot(None),
        ).order_by(BlastMessage.sent_at.desc()).first()
    if latest_msg and not latest_msg.replied_at:
        latest_msg.replied_at = now
        latest_msg.status = "replied"

    # Only auto-promote Contacted → Replied. Don't downgrade other statuses.
    if lead.status == "Contacted":
        lead.status = "Replied"
        db.add(LeadActivityLog(
            lead_id=lead.id,
            activity_type="WA_REPLIED",
            created_at=now,
        ))
        # Stop active follow-up sequences
        db.query(FollowUpSequence).filter(
            FollowUpSequence.lead_id == lead.id,
            FollowUpSequence.status == "ACTIVE",
        ).update({"status": "STOPPED", "stopped_reason": "client_replied"}, synchronize_session=False)
        db.commit()
        log_audit(db, "fonnte-webhook", "UPDATE", "leads", lead.id, {"field": "status", "old": "Contacted", "new": "Replied", "via": "wa_reply"})
        return {"ok": True, "lead_id": lead.id, "new_status": "Replied"}

    db.commit()
    return {"ok": True, "lead_id": lead.id, "current_status": lead.status}



@router.post("/api/followup/start")
def start_followup(body: dict, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    _check_simple_rate_limit(f"followup_start:{current_user.id}", 10, 60)
    lead_id = body.get("lead_id")
    template_ids = body.get("template_ids", [])
    delays = body.get("delays", [1, 3, 7])

    lead = db.query(Lead).filter(Lead.id == lead_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead tidak ditemukan")
    if lead.do_not_contact:
        raise HTTPException(status_code=409, detail="Lead memilih opt-out. Sequence tidak dapat dimulai.")

    existing = db.query(FollowUpSequence).filter(
        FollowUpSequence.lead_id == lead_id,
        FollowUpSequence.status == "ACTIVE",
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Lead sudah punya sequence aktif")

    now = datetime.now(timezone.utc)
    next_send = (now + timedelta(days=delays[0])).isoformat() if delays else None

    seq = FollowUpSequence(
        id=str(uuid.uuid4()),
        lead_id=lead_id,
        template_ids=json.dumps(template_ids),
        delays=json.dumps(delays),
        current_step=0,
        status="ACTIVE",
        started_at=now.isoformat(),
        next_send_at=next_send,
    )
    db.add(seq)
    db.commit()
    db.refresh(seq)
    return {"id": seq.id, "status": seq.status, "next_send_at": seq.next_send_at}



@router.post("/api/followup/stop/{seq_id}")
def stop_followup(seq_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    seq = db.query(FollowUpSequence).filter(FollowUpSequence.id == seq_id).first()
    if not seq:
        raise HTTPException(status_code=404, detail="Sequence tidak ditemukan")
    seq.status = "STOPPED"
    seq.stopped_reason = "manual"
    db.commit()
    return {"ok": True}



@router.get("/api/followup/active")
def get_active_followups(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    sequences = db.query(FollowUpSequence, Lead).join(
        Lead, FollowUpSequence.lead_id == Lead.id
    ).filter(FollowUpSequence.status == "ACTIVE").order_by(FollowUpSequence.next_send_at).all()

    results = []
    for seq, lead in sequences:
        delays = json.loads(seq.delays) if seq.delays else []
        results.append({
            "id": seq.id,
            "lead_id": lead.id,
            "business_name": lead.business_name,
            "phone_number": lead.phone_number,
            "current_step": seq.current_step,
            "total_steps": len(delays),
            "next_send_at": seq.next_send_at,
            "started_at": seq.started_at,
        })
    return results



@router.post("/api/followup/process")
async def process_followups(current_user: User = Depends(require_admin), db: Session = Depends(get_db)):
    _check_simple_rate_limit(f"followup_process:{current_user.id}", 10, 60)
    now = datetime.now(timezone.utc)
    sequences = db.query(FollowUpSequence).filter(
        FollowUpSequence.status == "ACTIVE",
        FollowUpSequence.next_send_at <= now.isoformat(),
    ).all()

    token = get_fonnte_token(db)
    sent_count = 0

    for seq in sequences:
        lead = db.query(Lead).filter(Lead.id == seq.lead_id).first()
        if not lead:
            seq.status = "STOPPED"
            seq.stopped_reason = "lead_not_found"
            db.commit()
            continue
        if lead.do_not_contact:
            seq.status = "STOPPED"
            seq.stopped_reason = "opt_out"
            db.commit()
            continue

        # Stop if lead has already replied to any message
        has_replied = db.query(BlastMessage).filter(
            BlastMessage.lead_id == seq.lead_id,
            BlastMessage.replied_at.isnot(None),
        ).first()
        if has_replied:
            seq.status = "STOPPED"
            seq.stopped_reason = "lead_replied"
            db.commit()
            continue

        template_ids = json.loads(seq.template_ids) if seq.template_ids else []
        delays = json.loads(seq.delays) if seq.delays else []

        if seq.current_step >= len(delays):
            seq.status = "COMPLETED"
            db.commit()
            continue

        message = None
        if template_ids and seq.current_step < len(template_ids):
            tmpl = db.query(DynamicTemplate).filter(DynamicTemplate.id == template_ids[seq.current_step]).first()
            if tmpl:
                message = tmpl.content.replace("{{business_name}}", lead.business_name).replace("{{client_name}}", lead.business_name)

        if not message:
            followup_defaults = [
                f"Halo {lead.business_name}, saya ingin follow up terkait laporan audit digital yang sudah saya kirimkan sebelumnya. Apakah ada pertanyaan yang bisa saya bantu jawab?",
                f"Pak, saya notice laporan audit untuk {lead.business_name} sudah dibuka tapi belum ada respons. Apakah ada kendala atau pertanyaan? Saya siap bantu jelaskan lebih detail.",
                f"Halo Pak, ini follow up terakhir dari saya untuk {lead.business_name}. Jika memang belum berminat saat ini, tidak masalah. Tapi perlu diingat, slot optimasi wilayah Anda terbatas dan kompetitor terus bergerak. Kapanpun siap, saya di sini.",
            ]
            message = followup_defaults[min(seq.current_step, len(followup_defaults) - 1)]

        success = await send_fonnte_message(lead.phone_number, message, token)
        if not success:
            continue
        sent_count += 1

        seq.current_step += 1
        if seq.current_step >= len(delays):
            seq.status = "COMPLETED"
            seq.next_send_at = None
        else:
            next_delay = delays[seq.current_step] if seq.current_step < len(delays) else 7
            seq.next_send_at = (now + timedelta(days=next_delay)).isoformat()
        db.commit()

    return {"processed": sent_count}


# ---------------------------------------------------------------------------
# Win/Loss Pattern Analysis
# ---------------------------------------------------------------------------


@router.get("/api/campaign/blast-status")
def get_blast_status(
    batch_name: str = Query(...),
    current_user: User = Depends(get_current_user),
):
    job = _blast_jobs.get(batch_name)
    if not job:
        return {"status": "idle", "sent": 0, "total": 0}
    return job



@router.get("/api/ads/campaigns", response_model=list[AdsCampaignOut])
def get_ads_campaigns(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    campaigns = db.query(AdsCampaign).order_by(AdsCampaign.created_at.desc()).all()
    return [_ads_out(c) for c in campaigns]



@router.post("/api/ads/campaigns", response_model=AdsCampaignOut, status_code=201)
def create_ads_campaign(body: AdsCampaignIn, current_user: User = Depends(require_admin), db: Session = Depends(get_db)):
    campaign = AdsCampaign(
        id=str(uuid.uuid4()),
        name=body.name,
        target_audience=body.target_audience,
        budget=body.budget,
        drive_link=body.drive_link,
        status=body.status,
        created_at=datetime.now(timezone.utc).isoformat(),
    )
    db.add(campaign)
    db.commit()
    db.refresh(campaign)

    if body.status == "ACTIVE" and body.budget > 0:
        ads_wallet = db.query(Wallet).filter(Wallet.name == "Dompet Budget Ads").first()
        if not ads_wallet:
            ads_wallet = Wallet(name="Dompet Budget Ads", balance=0, icon="megaphone", color="#f59e0b")
            db.add(ads_wallet)
            db.commit()
            db.refresh(ads_wallet)
        txn = Transaction(
            wallet_id=ads_wallet.id,
            type="expense",
            amount=body.budget,
            category="Ads Campaign",
            date=datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            notes=f"Budget iklan: {body.name}",
            is_billed=False,
            is_archived=False,
        )
        db.add(txn)
        ads_wallet.balance -= body.budget
        db.commit()

    log_audit(db, current_user.name, "CREATE", "ads_campaigns", campaign.id, {"name": body.name})
    return _ads_out(campaign)



@router.put("/api/ads/campaigns/{campaign_id}", response_model=AdsCampaignOut)
def update_ads_campaign(campaign_id: str, body: AdsCampaignUpdate, current_user: User = Depends(require_admin), db: Session = Depends(get_db)):
    campaign = db.query(AdsCampaign).filter(AdsCampaign.id == campaign_id).first()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign tidak ditemukan")

    old_status = campaign.status

    if body.name is not None:
        campaign.name = body.name
    if body.target_audience is not None:
        campaign.target_audience = body.target_audience
    if body.budget is not None:
        campaign.budget = body.budget
    if body.drive_link is not None:
        campaign.drive_link = body.drive_link
    if body.leads_count is not None:
        campaign.leads_count = body.leads_count
    if body.conversions_count is not None:
        campaign.conversions_count = body.conversions_count
    if body.status is not None:
        campaign.status = body.status

    if old_status == "PLANNING" and body.status == "ACTIVE" and campaign.budget > 0:
        ads_wallet = db.query(Wallet).filter(Wallet.name == "Dompet Budget Ads").first()
        if not ads_wallet:
            ads_wallet = Wallet(name="Dompet Budget Ads", balance=0, icon="megaphone", color="#f59e0b")
            db.add(ads_wallet)
            db.commit()
            db.refresh(ads_wallet)
        txn = Transaction(
            wallet_id=ads_wallet.id,
            type="expense",
            amount=campaign.budget,
            category="Ads Campaign",
            date=datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            notes=f"Budget iklan: {campaign.name}",
            is_billed=False,
            is_archived=False,
        )
        db.add(txn)
        ads_wallet.balance -= campaign.budget
        db.commit()

    db.commit()
    db.refresh(campaign)
    log_audit(db, current_user.name, "UPDATE", "ads_campaigns", campaign_id, {"name": campaign.name})
    return _ads_out(campaign)



@router.delete("/api/ads/campaigns/{campaign_id}", status_code=204)
def delete_ads_campaign(campaign_id: str, current_user: User = Depends(require_admin), db: Session = Depends(get_db)):
    campaign = db.query(AdsCampaign).filter(AdsCampaign.id == campaign_id).first()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign tidak ditemukan")
    log_audit(db, current_user.name, "DELETE", "ads_campaigns", campaign_id, {"name": campaign.name})
    db.delete(campaign)
    db.commit()




def sync_to_google_calendar(title: str, date: str, event_id: str | None = None) -> str | None:
    service = _get_google_calendar_service()
    if not service:
        return event_id

    calendar_id = _get_setting("google_calendar_id", GOOGLE_CALENDAR_ID)

    event_body = {
        "summary": title,
        "start": {"date": date},
        "end": {"date": date},
    }

    try:
        if event_id:
            service.events().update(calendarId=calendar_id, eventId=event_id, body=event_body).execute()
            return event_id
        else:
            result = service.events().insert(calendarId=calendar_id, body=event_body).execute()
            return result.get("id")
    except Exception:
        return event_id



@router.put("/api/blast-campaigns/{campaign_id}/conversions")
def update_blast_conversions(campaign_id: str, body: dict, current_user: User = Depends(require_admin), db: Session = Depends(get_db)):
    campaign = db.query(BlastCampaign).filter_by(id=campaign_id).first()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign tidak ditemukan")
    if "converted_clients_count" in body:
        campaign.converted_clients_count = body["converted_clients_count"]
    db.commit()
    return {"ok": True}


class BlastCampaignIn(BaseModel):
    name: str
    template_id: Optional[str] = None
    filter_criteria: dict
    scheduled_for: str


class BlastCampaignOut(BaseModel):
    id: str
    name: str
    template_id: Optional[str] = None
    filter_criteria: dict
    scheduled_for: str
    status: str
    sent_count: int
    failed_count: int
    created_at: str
    model_config = {"from_attributes": True}



@router.get("/api/campaign/blast/schedule", response_model=list[BlastCampaignOut])
def get_blast_campaigns(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    campaigns = db.query(BlastCampaign).order_by(BlastCampaign.created_at.desc()).all()
    results = []
    for c in campaigns:
        results.append(BlastCampaignOut(
            id=c.id, name=c.name, template_id=c.template_id,
            filter_criteria=json.loads(c.filter_criteria) if c.filter_criteria else {},
            scheduled_for=c.scheduled_for, status=c.status,
            sent_count=c.sent_count or 0, failed_count=c.failed_count or 0,
            created_at=c.created_at,
        ))
    return results



@router.post("/api/campaign/blast/schedule", response_model=BlastCampaignOut, status_code=201)
def create_blast_campaign(body: BlastCampaignIn, current_user: User = Depends(require_admin), db: Session = Depends(get_db)):
    campaign = BlastCampaign(
        id=str(uuid.uuid4()),
        name=body.name,
        template_id=body.template_id,
        filter_criteria=json.dumps(body.filter_criteria),
        scheduled_for=body.scheduled_for,
        status="PENDING",
        created_at=datetime.now(timezone.utc).isoformat(),
    )
    db.add(campaign)
    db.commit()
    db.refresh(campaign)
    log_audit(db, current_user.name, "CREATE", "blast_campaigns", campaign.id, {"name": body.name, "scheduled_for": body.scheduled_for})
    return BlastCampaignOut(
        id=campaign.id, name=campaign.name, template_id=campaign.template_id,
        filter_criteria=body.filter_criteria, scheduled_for=campaign.scheduled_for,
        status=campaign.status, sent_count=0, failed_count=0, created_at=campaign.created_at,
    )



@router.delete("/api/campaign/blast/schedule/{campaign_id}", status_code=204)
def delete_blast_campaign(campaign_id: str, current_user: User = Depends(require_admin), db: Session = Depends(get_db)):
    campaign = db.query(BlastCampaign).filter(BlastCampaign.id == campaign_id).first()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign tidak ditemukan")
    log_audit(db, current_user.name, "DELETE", "blast_campaigns", campaign_id, {"name": campaign.name})
    db.delete(campaign)
    db.commit()


# ---------------------------------------------------------------------------
# Blast Message Tracking + Analytics
# ---------------------------------------------------------------------------

class FonnteWebhookIn(BaseModel):
    device: Optional[str] = None
    target: Optional[str] = None
    status: Optional[str] = None
    message: Optional[str] = None



@router.post("/api/blast/webhook/fonnte")
def fonnte_webhook(body: FonnteWebhookIn, request: Request, db: Session = Depends(get_db)):
    """Fonnte callback for delivery/read/replied status updates."""
    if FONNTE_WEBHOOK_SECRET and not hmac.compare_digest(
        request.headers.get("x-fonnte-webhook-secret", ""),
        FONNTE_WEBHOOK_SECRET,
    ):
        raise HTTPException(status_code=401, detail="Webhook secret tidak valid")
    try:
        if not body.target:
            return {"ok": True}
        # DB stores 08xx, but legacy records may have 62xx — check both formats
        phone_62 = _normalize_phone(body.target)
        if phone_62.startswith("62"):
            phone_08 = "0" + phone_62[2:]
        else:
            phone_08 = phone_62
        now = datetime.now(timezone.utc).isoformat()
        # Try 08xx first (canonical), fall back to 62xx
        msgs = db.query(BlastMessage).filter(
            BlastMessage.phone_number == phone_08
        ).order_by(BlastMessage.sent_at.desc()).limit(5).all()
        if not msgs:
            msgs = db.query(BlastMessage).filter(
                BlastMessage.phone_number == phone_62
            ).order_by(BlastMessage.sent_at.desc()).limit(5).all()
        # Track if any message was marked replied for lead side-effects
        replied_msg = None
        for msg in msgs:
            if body.status == "delivered" and not msg.delivered_at:
                msg.delivered_at = now
                msg.status = "delivered"
            elif body.status == "read" and not msg.read_at:
                msg.read_at = now
                msg.status = "read"
            elif body.status == "replied" and not msg.replied_at:
                msg.replied_at = now
                msg.status = "replied"
                replied_msg = msg
        # If status=replied, perform the same lead side-effects as fonnte-incoming
        if replied_msg and replied_msg.lead_id:
            lead = db.query(Lead).filter(Lead.id == replied_msg.lead_id).first()
            if lead and lead.status == "Contacted":
                lead.status = "Replied"
                db.add(LeadActivityLog(
                    lead_id=lead.id,
                    activity_type="WA_REPLIED",
                    created_at=now,
                ))
                db.query(FollowUpSequence).filter(
                    FollowUpSequence.lead_id == lead.id,
                    FollowUpSequence.status == "ACTIVE",
                ).update({"status": "STOPPED", "stopped_reason": "client_replied"}, synchronize_session=False)
        db.commit()
    except Exception as e:
        print(f"[FONNTE_WEBHOOK] {e}", flush=True)
    return {"ok": True}



@router.get("/api/blast/analytics")
def get_blast_analytics(days: int = 30, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    msgs = db.query(BlastMessage).filter(
        BlastMessage.sent_at >= cutoff,
        BlastMessage.status != "failed",
    ).all()

    total_sent = len(msgs)
    total_delivered = sum(1 for m in msgs if m.delivered_at)
    total_read = sum(1 for m in msgs if m.read_at)
    total_replied = sum(1 for m in msgs if m.replied_at)
    replied_lead_ids = [m.lead_id for m in msgs if m.replied_at]
    total_closed = db.query(Lead).filter(Lead.id.in_(replied_lead_ids), Lead.status == "Closed/Client").count() if replied_lead_ids else 0

    by_template: dict[str, dict] = {}
    closed_lead_ids = {
        lead_id for (lead_id,) in db.query(Lead.id).filter(Lead.status == "Closed/Client").all()
    }
    for m in msgs:
        tid = m.template_id or "unknown"
        if tid not in by_template:
            by_template[tid] = {"template_id": tid, "template_name": None, "sent": 0, "delivered": 0, "read": 0, "replied": 0, "closed": 0, "_closed_ids": set()}
        by_template[tid]["sent"] += 1
        if m.delivered_at: by_template[tid]["delivered"] += 1
        if m.read_at: by_template[tid]["read"] += 1
        if m.replied_at: by_template[tid]["replied"] += 1
        if m.replied_at and m.lead_id in closed_lead_ids:
            by_template[tid]["_closed_ids"].add(m.lead_id)

    templates = {t.id: t.name for t in db.query(DynamicTemplate).all()}
    for tid, row in by_template.items():
        row["template_name"] = templates.get(tid, "Unknown")
        row["closed"] = len(row.pop("_closed_ids"))
        s = row["sent"]
        row["reply_rate"] = round(row["replied"] / s * 100, 1) if s else 0.0
        row["conversion_rate"] = round(row["closed"] / s * 100, 1) if s else 0.0

    ranked = sorted(by_template.values(), key=lambda x: x["reply_rate"], reverse=True)
    top = ranked[0] if ranked else None

    return {
        "period_days": days,
        "total": {
            "sent": total_sent,
            "delivered": total_delivered,
            "read": total_read,
            "replied": total_replied,
            "closed": total_closed,
            "reply_rate": round(total_replied / total_sent * 100, 1) if total_sent else 0.0,
            "conversion_rate": round(total_closed / total_sent * 100, 1) if total_sent else 0.0,
        },
        "by_template": ranked,
        "top_performer": {"template_name": top["template_name"], "reply_rate": top["reply_rate"]} if top else None,
    }


# ---------------------------------------------------------------------------
# Workspace Klien
# ---------------------------------------------------------------------------

from workspace_templates import build_sheets_for_service, build_sheets_for_days, WORKSPACE_TEMPLATES


class WorkspaceInitIn(BaseModel):
    project_id: str
    service_type: str
    contract_months: int = 1
    contract_days: Optional[int] = None


class WorkspaceCellUpdate(BaseModel):
    value_text: Optional[str] = None
    value_bool: Optional[bool] = None
    value_number: Optional[float] = None
    value_date: Optional[str] = None
    value_json: Optional[str] = None


class WorkspaceRowIn(BaseModel):
    cells: dict = {}
    row_order: Optional[int] = None


class WorkspaceColumnIn(BaseModel):
    column_key: str
    column_label: str
    column_type: str = "text"
    column_options: Optional[List[str]] = None
    column_order: Optional[int] = None


def sync_row_to_board(row_id: str, db: Session):
    """Create board card for workspace row if not exists."""
    try:
        row = db.query(WorkspaceRow).filter(WorkspaceRow.id == row_id).first()
        if not row or row.board_card_id:
            return
        sheet = db.query(WorkspaceSheet).filter(WorkspaceSheet.id == row.sheet_id).first()
        if not sheet:
            return
        project = db.query(Project).filter(Project.id == sheet.project_id).first()
        if not project:
            return

        task_cell = db.query(WorkspaceCell).join(WorkspaceColumn).filter(
            WorkspaceCell.row_id == row_id,
            WorkspaceColumn.column_key == "task_name",
        ).first()
        title = task_cell.value_text if task_cell else f"Task {row.row_order}"

        board = db.query(Board).filter(Board.project_id == project.id).first()
        if not board:
            board = Board(id=str(uuid.uuid4()), project_id=project.id)
            db.add(board)
            db.flush()
            for i, (col_name, col_color) in enumerate([("To Do", "yellow"), ("In Progress", "blue"), ("Review", "purple"), ("Done", "green")]):
                db.add(BoardColumn(id=str(uuid.uuid4()), board_id=board.id, name=col_name, position=i, color=col_color))
            db.flush()

        todo_col = db.query(BoardColumn).filter(BoardColumn.board_id == board.id, BoardColumn.name == "To Do").first()
        if not todo_col:
            return

        # Validate lead exists before assigning FK
        valid_lead_id = None
        if project.lead_id:
            lead_exists = db.query(Lead).filter(Lead.id == project.lead_id).first()
            if lead_exists:
                valid_lead_id = project.lead_id

        card = BoardCard(
            id=str(uuid.uuid4()),
            column_id=todo_col.id,
            title=title,
            position=row.row_order or 0,
            lead_id=valid_lead_id,
        )
        db.add(card)
        db.flush()
        row.board_card_id = card.id
        db.commit()
    except Exception as e:
        print(f"[WORKSPACE_SYNC] sync_row_to_board error: {e}", flush=True)
        try:
            db.rollback()
        except Exception:
            pass


def sync_row_status_to_board(row_id: str, db: Session):
    """Move board card when workspace task status/done changes."""
    try:
        row = db.query(WorkspaceRow).filter(WorkspaceRow.id == row_id).first()
        if not row or not row.board_card_id:
            return
        card = db.query(BoardCard).filter(BoardCard.id == row.board_card_id).first()
        if not card:
            return

        sheet = db.query(WorkspaceSheet).filter(WorkspaceSheet.id == row.sheet_id).first()
        board = db.query(Board).filter(Board.project_id == sheet.project_id).first() if sheet else None
        if not board:
            return

        status_cell = db.query(WorkspaceCell).join(WorkspaceColumn).filter(
            WorkspaceCell.row_id == row_id,
            WorkspaceColumn.column_key == "status",
        ).first()
        done_cell = db.query(WorkspaceCell).join(WorkspaceColumn).filter(
            WorkspaceCell.row_id == row_id,
            WorkspaceColumn.column_key == "done",
        ).first()

        target_col_name = "To Do"
        if done_cell and done_cell.value_bool:
            target_col_name = "Done"
        elif status_cell and status_cell.value_text:
            sv = status_cell.value_text
            if sv in ("Done", "Published", "Posted"):
                target_col_name = "Done"
            elif sv in ("In Progress", "Draft", "Approved"):
                target_col_name = "In Progress"
            elif sv in ("Revision", "Review"):
                target_col_name = "Review"

        target_col = db.query(BoardColumn).filter(BoardColumn.board_id == board.id, BoardColumn.name == target_col_name).first()
        if target_col and card.column_id != target_col.id:
            card.column_id = target_col.id
            db.commit()
    except Exception as e:
        print(f"[WORKSPACE_SYNC] sync_row_status error: {e}", flush=True)



