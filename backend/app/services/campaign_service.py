"""Campaign Service Layer — extracted from routers/campaign.py and app/core/dependencies.py"""
import json
import uuid
import asyncio
import random
import threading
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy.orm import Session

from models import (
    BlastCampaign, BlastMessage, FollowUpSequence, Lead,
    DynamicTemplate, Transaction, Wallet, Product,
    log_audit, LeadActivityLog,
)
from app.core.dependencies import (
    _get_setting, FRONTEND_URL, ADMIN_WA, generate_report_for_lead,
    log_outreach_cost, log_ai_cost,
    WORKSPACE_TEMPLATES, build_sheets_for_service,
    sync_row_to_board, sync_row_status_to_board,
    _acquire_scheduler_lock, _run_async_job,
)
from app.core.whatsapp_provider import get_whatsapp_config, get_whatsapp_cost_provider_id, send_whatsapp_message
from app.services.web_preview_service import generate_preview_for_lead, preview_public_url
from app.constants import CLIENT_STATUS_VALUES
from app.constants import LeadStatus


# ─── Module-level job state ───────────────────────────────────────────────────

_analysis_jobs: dict = {}
_blast_jobs: dict = {}


# ─── Cost logging ────────────────────────────────────────────────────────────

def log_outreach_cost(db: Session, campaign_id: Optional[str], messages_count: int):
    """Log outreach cost to the active WhatsApp ProviderConfig."""
    from models import ProviderConfig
    provider = db.query(ProviderConfig).filter_by(id=get_whatsapp_cost_provider_id(db)).first()
    if not provider:
        return
    cost = provider.price_per_unit_idr * messages_count
    provider.remaining_quota = max(0, (provider.remaining_quota or 0) - messages_count)
    campaign = db.query(BlastCampaign).filter_by(id=campaign_id).first() if campaign_id else None
    if campaign:
        campaign.total_operational_cost_idr = (campaign.total_operational_cost_idr or 0) + cost
    db.commit()


def log_ai_cost(
    db: Session,
    campaign_id: Optional[str],
    model_name: str,
    input_tokens: int,
    output_tokens: int,
) -> None:
    """Log AI cost to the single 9router ProviderConfig."""
    from models import ProviderConfig
    from app.core.dependencies import USD_TO_IDR
    provider = db.query(ProviderConfig).filter_by(id="9ROUTER").first()
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


# ─── Template stats ──────────────────────────────────────────────────────────

def get_template_stats(db: Session, template_id: str, days: int = 30) -> dict:
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    msgs = db.query(BlastMessage).filter(
        BlastMessage.template_id == template_id,
        BlastMessage.sent_at >= cutoff,
        BlastMessage.status != "failed",
    ).all()
    sent = len(msgs)
    delivered = sum(1 for m in msgs if m.delivered_at)
    read = sum(1 for m in msgs if m.read_at)
    replied = sum(1 for m in msgs if m.replied_at)
    lead_ids = [m.lead_id for m in msgs if m.replied_at]
    closed = db.query(Lead).filter(Lead.id.in_(lead_ids), Lead.status.in_(CLIENT_STATUS_VALUES)).count() if lead_ids else 0
    reply_rate = round(replied / sent * 100, 1) if sent else 0.0
    conversion_rate = round(closed / sent * 100, 1) if sent else 0.0
    return {
        "template_id": template_id,
        "sent": sent,
        "delivered": delivered,
        "read": read,
        "replied": replied,
        "closed": closed,
        "reply_rate": reply_rate,
        "conversion_rate": conversion_rate,
    }


# ─── Blast Campaign CRUD ──────────────────────────────────────────────────────

def create_blast_campaign(
    db: Session,
    name: str,
    template_id: Optional[str],
    filter_criteria: dict,
    scheduled_for: str,
    actor: str,
) -> dict:
    campaign = BlastCampaign(
        id=str(uuid.uuid4()),
        name=name,
        template_id=template_id,
        filter_criteria=json.dumps(filter_criteria),
        scheduled_for=scheduled_for,
        status="PENDING",
        created_at=datetime.now(timezone.utc).isoformat(),
    )
    db.add(campaign)
    db.commit()
    db.refresh(campaign)
    log_audit(db, actor, "CREATE", "blast_campaigns", campaign.id, {"name": name, "scheduled_for": scheduled_for})
    return {
        "id": campaign.id,
        "name": campaign.name,
        "template_id": campaign.template_id,
        "filter_criteria": filter_criteria,
        "scheduled_for": campaign.scheduled_for,
        "status": campaign.status,
        "sent_count": 0,
        "failed_count": 0,
        "created_at": campaign.created_at,
    }


def list_blast_campaigns(db: Session, actor: str, status: Optional[str] = None) -> list[dict]:
    q = db.query(BlastCampaign).order_by(BlastCampaign.created_at.desc())
    campaigns = q.all()
    results = []
    for c in campaigns:
        results.append({
            "id": c.id,
            "name": c.name,
            "template_id": c.template_id,
            "filter_criteria": json.loads(c.filter_criteria) if c.filter_criteria else {},
            "scheduled_for": c.scheduled_for,
            "status": c.status,
            "sent_count": c.sent_count or 0,
            "failed_count": c.failed_count or 0,
            "created_at": c.created_at,
        })
    return results


def get_blast_campaign(db: Session, campaign_id: str) -> Optional[dict]:
    c = db.query(BlastCampaign).filter(BlastCampaign.id == campaign_id).first()
    if not c:
        return None
    return {
        "id": c.id,
        "name": c.name,
        "template_id": c.template_id,
        "filter_criteria": json.loads(c.filter_criteria) if c.filter_criteria else {},
        "scheduled_for": c.scheduled_for,
        "status": c.status,
        "sent_count": c.sent_count or 0,
        "failed_count": c.failed_count or 0,
        "created_at": c.created_at,
    }


def cancel_blast_campaign(db: Session, campaign_id: str, actor: str) -> dict:
    campaign = db.query(BlastCampaign).filter_by(id=campaign_id).first()
    if not campaign:
        raise ValueError("Campaign tidak ditemukan")
    if campaign.status in ("SUCCESS", "FAILED"):
        raise ValueError("Tidak bisa cancel campaign yang sudah selesai")
    campaign.status = "CANCELLED"
    db.commit()
    log_audit(db, actor, "CANCEL", "blast_campaigns", campaign_id, {"name": campaign.name})
    return {"ok": True}


def delete_blast_campaign(db: Session, campaign_id: str, actor: str) -> None:
    campaign = db.query(BlastCampaign).filter(BlastCampaign.id == campaign_id).first()
    if not campaign:
        raise ValueError("Campaign tidak ditemukan")
    log_audit(db, actor, "DELETE", "blast_campaigns", campaign_id, {"name": campaign.name})
    db.delete(campaign)
    db.commit()


# ─── Blast execution engine ───────────────────────────────────────────────────

async def execute_blast_campaign(campaign: BlastCampaign, db: Session, SessionLocal) -> None:
    """Async execution of a single blast campaign."""
    now = datetime.now(timezone.utc).isoformat()
    criteria = json.loads(campaign.filter_criteria) if campaign.filter_criteria else {}
    query = db.query(Lead).filter(Lead.is_archived == False, Lead.do_not_contact == False)
    if criteria.get("status"):
        query = query.filter(Lead.status == criteria["status"])
    if criteria.get("batch_name"):
        query = query.filter(Lead.batch_name == criteria["batch_name"])
    if criteria.get("min_rating") and int(criteria["min_rating"]) > 0:
        query = query.filter(Lead.rating >= int(criteria["min_rating"]))
    leads = query.all()

    try:
        whatsapp_config = get_whatsapp_config(db, campaign.whatsapp_number_id or None)
    except ValueError as exc:
        # Nomor WA terpilih ga valid -> GAGALKAN campaign, JANGAN fallback
        # kirim dari nomor utama diam-diam (bahaya kirim dari nomor salah).
        campaign.sent_count = 0
        campaign.failed_count = 0
        campaign.status = "FAILED"
        print(f"[BLAST] campaign={campaign.id} gagal resolve nomor WA: {exc}", flush=True)
        db.commit()
        return
    template = None
    if campaign.template_id:
        template = db.query(DynamicTemplate).filter(DynamicTemplate.id == campaign.template_id).first()
    if not template:
        templates = db.query(DynamicTemplate).filter(
            DynamicTemplate.type == "WA_BLAST",
            DynamicTemplate.is_active == True,
        ).all()
        if templates:
            template = random.choice(templates)

    sent = 0
    failed = 0
    criteria_product = (criteria.get("product_category") or "").strip()
    for lead in leads:
        product_name = criteria_product or lead.product_interest or "layanan kami"
        report_slug = generate_report_for_lead(lead, db, product_category=product_name)
        report_link = f"{FRONTEND_URL}/r/{report_slug}"

        # ── Web preview: lead "Prospek Panas" dapat simulasi web per-industri ──
        # Default ON untuk lead panas; kegagalan generate TIDAK memblokir blast.
        web_preview_url = None
        if criteria.get("web_preview", True) and lead.status == LeadStatus.HOT_PROSPECT:
            try:
                _pv = generate_preview_for_lead(lead, db, campaign_id=campaign.id)
                web_preview_url = preview_public_url(db, _pv["slug"])
            except Exception as exc:
                web_preview_url = None
                print(f"[WEB_PREVIEW] lead={lead.id} gagal generate: {exc}", flush=True)

        if template:
            message = template.content.replace("{{client_name}}", lead.business_name).replace("{{business_name}}", lead.business_name).replace("{{product_name}}", product_name)
        else:
            message = f"Halo {lead.business_name}, kami menyiapkan audit digital singkat untuk bisnis Anda. Apakah kami boleh menjelaskan poin yang paling prioritas?\n\nLaporan ringkas: {report_link}"
        message = message.replace("{{proposal_link}}", f"\n{report_link}\n")

        # Sisipkan link web preview (placeholder eksplisit, atau ditambahkan di akhir)
        if "{{web_preview_link}}" in message:
            message = message.replace("{{web_preview_link}}", web_preview_url or "")
        elif web_preview_url:
            message += (
                f"\n\nKami juga sudah menyiapkan simulasi tampilan web untuk "
                f"{lead.business_name}: {web_preview_url}"
            )

        result = await send_whatsapp_message(db, lead.phone_number, message, {
            "lead_id": lead.id,
            "campaign_id": campaign.id,
            "template_id": template.id if template else None,
            "batch_name": criteria.get("batch_name"),
            "business_name": lead.business_name,
        }, number_id=campaign.whatsapp_number_id or None)
        success = result.ok
        db.add(BlastMessage(
            id=str(uuid.uuid4()),
            campaign_id=campaign.id,
            lead_id=lead.id,
            template_id=template.id if template else None,
            phone_number=lead.phone_number,
            sent_at=datetime.now(timezone.utc).isoformat(),
            status="sent" if success else "failed",
            error_message=None if success else (result.error or f"{result.provider} send failed"),
            whatsapp_number_id=campaign.whatsapp_number_id or None,
        ))
        if success:
            lead.status = LeadStatus.WA_SENT
            lead.last_followup_at = datetime.now(timezone.utc).isoformat()
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


# ─── Scheduled task: process pending blasts ─────────────────────────────────

async def process_pending_blasts(SessionLocal, BlastCampaign, Lead, DynamicTemplate) -> None:
    """Process all PENDING blast campaigns that are due."""
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
                await execute_blast_campaign(campaign, db, SessionLocal)
            except Exception as exc:
                campaign.status = "FAILED"
                print(f"[SCHEDULED BLAST] campaign={campaign.id} failed: {exc}", flush=True)
                db.commit()
    finally:
        db.close()


# ─── Scheduled task: followup processor ──────────────────────────────────────

async def scheduled_followup_processor(
    SessionLocal,
    SystemSettings,
    FollowUpSequence,
    Lead,
    DynamicTemplate,
) -> None:
    """Process scheduled followup sequences. Called by scheduler."""
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

            # Stop if lead has already replied
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
            lead.last_followup_at = datetime.now(timezone.utc).isoformat()

            seq.current_step += 1
            if seq.current_step >= len(delays):
                seq.status = "COMPLETED"
                seq.next_send_at = None
            else:
                next_delay = delays[seq.current_step] if seq.current_step < len(delays) else 7
                seq.next_send_at = (now + timedelta(days=next_delay)).isoformat()
            db.commit()
    finally:
        db.close()
