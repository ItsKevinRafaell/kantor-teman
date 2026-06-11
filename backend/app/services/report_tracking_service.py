"""Public report tracking and scoring signals."""

from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import Request
from sqlalchemy.orm import Session

from app.constants import LeadStatus
from app.services.notification_service import create_notification
from app.services.scoring_service import recalculate_lead_score_with_context
from models import Lead, LeadActivityLog, Proposal, ProposalAnalytics


BOT_SIGNATURES = {"whatsapp", "facebookexternalhit", "googlebot", "telegrambot", "twitterbot"}


def is_valid_report_viewer(request: Request) -> bool:
    ua = (request.headers.get("user-agent") or "").lower()
    if any(sig in ua for sig in BOT_SIGNATURES):
        return False
    auth_header = request.headers.get("authorization") or ""
    if auth_header.startswith("Bearer "):
        return False
    return True


def _visitor_hash(request: Request) -> str:
    raw = "|".join([
        request.headers.get("x-forwarded-for", request.client.host if request.client else ""),
        request.headers.get("user-agent", ""),
    ])
    return hashlib.sha256(raw.encode("utf-8", errors="ignore")).hexdigest()


def _log_signal_once(db: Session, lead_id: int, signal: str) -> bool:
    existing = db.query(LeadActivityLog.id).filter(
        LeadActivityLog.lead_id == lead_id,
        LeadActivityLog.activity_type == signal,
    ).first()
    if existing:
        return False
    db.add(LeadActivityLog(
        id=str(uuid.uuid4()),
        lead_id=lead_id,
        activity_type=signal,
        created_at=datetime.now(timezone.utc).isoformat(),
    ))
    return True


def record_report_open(db: Session, proposal: Proposal, lead: Optional[Lead], request: Request) -> Optional[ProposalAnalytics]:
    if not is_valid_report_viewer(request):
        return None

    now = datetime.now(timezone.utc).isoformat()
    if not proposal.first_viewed_at:
        proposal.first_viewed_at = now
    proposal.report_open_count = (proposal.report_open_count or 0) + 1
    proposal.last_report_viewed_at = now

    analytics = ProposalAnalytics(
        id=str(uuid.uuid4()),
        proposal_id=proposal.id,
        opened_at=now,
        total_time_seconds=0,
        sections_viewed="[]",
        event="report_opened",
        visitor_hash=_visitor_hash(request),
        source="public_report",
    )
    db.add(analytics)

    if lead:
        if lead.status not in {LeadStatus.HOT_PROSPECT, LeadStatus.CLOSED_CLIENT, LeadStatus.ACTIVE_CLIENT}:
            lead.status = LeadStatus.REPORT_OPENED
        _log_signal_once(db, lead.id, "report_opened")
        recalculate_lead_score_with_context(db, lead)
        if proposal.report_open_count == 1:
            create_notification(
                db,
                title="Laporan dibuka",
                message=f"{lead.business_name} membuka laporan audit digital.",
                notif_type="report",
                target_type="lead",
                target_id=str(lead.id),
                action_url=f"/contacts?lead={lead.id}",
            )

    db.commit()
    return analytics


def record_report_duration(db: Session, proposal: Proposal, lead: Optional[Lead], duration_seconds: int) -> dict:
    duration = max(0, min(int(duration_seconds), 3600))
    latest = db.query(ProposalAnalytics).filter(
        ProposalAnalytics.proposal_id == proposal.id,
        ProposalAnalytics.event == "report_opened",
    ).order_by(ProposalAnalytics.opened_at.desc()).first()
    if latest:
        latest.duration_seconds = max(latest.duration_seconds or 0, duration)
        latest.total_time_seconds = max(latest.total_time_seconds or 0, duration)

    proposal.max_report_duration_seconds = max(proposal.max_report_duration_seconds or 0, duration)

    applied_signal = None
    new_status = None
    if lead:
        if duration >= 60:
            applied_signal = "report_reading_seriously"
            new_status = LeadStatus.READING_SERIOUSLY
        elif duration >= 15:
            applied_signal = "report_started_reading"
            new_status = LeadStatus.STARTED_READING
        if applied_signal:
            _log_signal_once(db, lead.id, applied_signal)
            if lead.status not in {LeadStatus.HOT_PROSPECT, LeadStatus.CLOSED_CLIENT, LeadStatus.ACTIVE_CLIENT}:
                lead.status = new_status
            recalculate_lead_score_with_context(db, lead)
    db.commit()
    return {
        "success": True,
        "duration_seconds": duration,
        "status": lead.status if lead else None,
        "score": lead.lead_score if lead else None,
    }


def record_report_activity(db: Session, proposal: Proposal, lead: Lead, activity_type: str) -> dict:
    now = datetime.now(timezone.utc).isoformat()
    db.add(LeadActivityLog(
        id=str(uuid.uuid4()),
        lead_id=lead.id,
        activity_type=activity_type,
        created_at=now,
    ))
    db.add(ProposalAnalytics(
        id=str(uuid.uuid4()),
        proposal_id=proposal.id,
        opened_at=now,
        event=activity_type,
        source="public_report",
        metadata_json=json.dumps({"activity_type": activity_type}),
    ))

    hot_events = {"LINK_CLICKED", "CTA_CLICKED", "SHARE_PARTNER_CLICKED", "ROI_SLIDER_VIEWED"}
    if activity_type in hot_events:
        _log_signal_once(db, lead.id, "report_hot_action")
        lead.status = LeadStatus.HOT_PROSPECT
        create_notification(
            db,
            title="Prospek panas",
            message=f"{lead.business_name} melakukan aksi penting di laporan.",
            notif_type="hot_lead",
            target_type="lead",
            target_id=str(lead.id),
            action_url=f"/contacts?lead={lead.id}",
        )
    recalculate_lead_score_with_context(db, lead)
    db.commit()
    return {"success": True, "lead_score": lead.lead_score, "status": lead.status}
