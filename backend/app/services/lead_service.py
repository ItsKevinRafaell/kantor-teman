"""Lead Service Layer — extracted business logic from routers/leads.py"""
import csv
import io
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy.orm import Session
from sqlalchemy import func

from models import Lead, LeadActivityLog, BlastMessage, AuditLog
from schemas import LeadOut, StatusUpdate


# ─── State Transition Validators ────────────────────────────────────────────

VALID_STATUSES = [
    "Scraped", "Hot", "Replied", "Follow-up", "Qualified",
    "Negotiating", "Won", "Closed/Client", "Closed/Lost",
]


def _validate_status_transition(old_status: str, new_status: str) -> Optional[str]:
    """Return error message if transition is invalid, else None."""
    if new_status not in VALID_STATUSES:
        return f"Status tidak valid. Pilih dari: {', '.join(VALID_STATUSES)}"
    return None


# ─── Search / Filter Leads ───────────────────────────────────────────────────

def search_leads(
    db: Session,
    status: Optional[str] = None,
    batch_name: Optional[str] = None,
    include_archived: bool = False,
    archived_only: bool = False,
    limit: Optional[int] = None,
) -> list[Lead]:
    """Query leads with filters and optional limit."""
    query = db.query(Lead)

    if archived_only:
        query = query.filter(Lead.is_archived == True)
    elif not include_archived:
        query = query.filter(Lead.is_archived == False)

    if status:
        query = query.filter(Lead.status == status)
    if batch_name:
        query = query.filter(Lead.batch_name == batch_name)

    query = query.order_by(Lead.id.desc())

    if limit:
        query = query.limit(limit)

    return query.all()


def get_leads_with_ghost_viewer_flag(
    db: Session,
    status: Optional[str] = None,
    batch_name: Optional[str] = None,
    include_archived: bool = False,
    archived_only: bool = False,
) -> list[LeadOut]:
    """Return leads with ghost viewer aggregation (LINK_CLICKED >= 5 in 48h)."""
    leads = search_leads(db, status, batch_name, include_archived, archived_only)

    if not leads:
        return []

    # Ghost Viewer aggregation
    threshold_48h = (datetime.now(timezone.utc) - timedelta(hours=48)).isoformat()
    lead_ids = [l.id for l in leads]
    ghost_rows = db.query(
        LeadActivityLog.lead_id, func.count(LeadActivityLog.id).label("click_count")
    ).filter(
        LeadActivityLog.lead_id.in_(lead_ids),
        LeadActivityLog.activity_type == "LINK_CLICKED",
        LeadActivityLog.created_at >= threshold_48h,
    ).group_by(LeadActivityLog.lead_id).having(func.count(LeadActivityLog.id) >= 5).all()
    ghost_lead_ids = {row[0] for row in ghost_rows}

    results = []
    for lead in leads:
        results.append(LeadOut(
            id=lead.id, business_name=lead.business_name, phone_number=lead.phone_number,
            address=lead.address, original_url=lead.original_url, status=lead.status,
            product_interest=lead.product_interest, batch_name=lead.batch_name,
            rating=lead.rating or 0, is_archived=lead.is_archived, deleted_at=lead.deleted_at,
            lead_score=lead.lead_score or 0, is_ghost_viewer=(lead.id in ghost_lead_ids),
            action_recommendation=_score_to_action(lead.lead_score or 0),
            google_rating=lead.google_rating, review_count=lead.review_count,
            website_url=lead.website_url, sales_owner=lead.sales_owner,
            next_action_at=lead.next_action_at, loss_reason=lead.loss_reason,
            do_not_contact=bool(lead.do_not_contact),
        ))
    return results


# ─── Lead Status Update ─────────────────────────────────────────────────────

def update_lead_status(
    db: Session,
    lead_id: int,
    new_status: str,
    current_user_name: str,
    recalculate_score: bool = True,
) -> Lead:
    """
    Validate state transition, update status, mark replied BlastMessages,
    recalculate score, log audit.
    """
    if new_status not in VALID_STATUSES:
        raise ValueError(f"Status tidak valid. Pilih dari: {', '.join(VALID_STATUSES)}")

    lead = db.query(Lead).filter(Lead.id == lead_id).first()
    if not lead:
        raise ValueError("Lead tidak ditemukan")

    old_status = lead.status
    lead.status = new_status
    lead.last_followup_at = datetime.now(timezone.utc).isoformat()

    # Mark replied BlastMessages
    if new_status == "Replied":
        now_iso = datetime.now(timezone.utc).isoformat()
        pending = db.query(BlastMessage).filter(
            BlastMessage.lead_id == lead_id,
            BlastMessage.replied_at.is_(None),
        ).all()
        for bm in pending:
            bm.replied_at = now_iso
            bm.status = "replied"

    # Recalculate score
    if recalculate_score:
        # Import here to avoid circular dependency
        from app.core.dependencies import calculate_lead_score_full
        new_score, _ = calculate_lead_score_full(lead)
        lead.lead_score = new_score

    db.commit()
    db.refresh(lead)

    log_audit(db, current_user_name, "UPDATE", "leads", lead_id, {
        "field": "status",
        "old": old_status,
        "new": new_status,
    })

    return lead


# ─── Lead Score ──────────────────────────────────────────────────────────────

def recalculate_lead_score(db: Session, lead_id: int) -> tuple[int, dict]:
    """Recalculate score for a single lead. Returns (score, breakdown)."""
    from app.core.dependencies import calculate_lead_score_full
    lead = db.query(Lead).filter(Lead.id == lead_id).first()
    if not lead:
        raise ValueError("Lead tidak ditemukan")
    score, breakdown = calculate_lead_score_full(lead)
    lead.lead_score = score
    db.commit()
    return score, breakdown


def recalculate_all_lead_scores(db: Session) -> dict:
    """Batch recalculate scores for all non-archived leads."""
    from app.core.dependencies import calculate_lead_score_full
    leads = db.query(Lead).filter(Lead.is_archived == False).all()
    updated = 0
    for lead in leads:
        new_score, _ = calculate_lead_score_full(lead)
        if lead.lead_score != new_score:
            lead.lead_score = new_score
            updated += 1
    db.commit()
    return {"total": len(leads), "updated": updated}


# ─── CSV Export ──────────────────────────────────────────────────────────────

def export_leads_csv(
    db: Session,
    status: Optional[str] = None,
    batch_name: Optional[str] = None,
    include_archived: bool = False,
) -> io.StringIO:
    """Generate CSV export of leads with all relevant fields."""
    leads = search_leads(db, status, batch_name, include_archived, archived_only=False)

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "ID", "Business Name", "Phone", "Address", "Status",
        "Product Interest", "Batch Name", "Rating", "Lead Score",
        "Google Rating", "Review Count", "Website", "Sales Owner",
        "Next Action", "Archived", "Created At",
    ])

    for lead in leads:
        writer.writerow([
            lead.id, lead.business_name, lead.phone_number,
            lead.address or "", lead.status or "",
            lead.product_interest or "", lead.batch_name or "",
            lead.rating or 0, lead.lead_score or 0,
            lead.google_rating or "", lead.review_count or "",
            lead.website_url or "", lead.sales_owner or "",
            lead.next_action_at or "", lead.is_archived,
            lead.deleted_at or "",
        ])

    output.seek(0)
    return output


# ─── Action Recommendation ──────────────────────────────────────────────────

def _score_to_action(score: int) -> str:
    if score >= 80:
        return "Prioritas utama — follow-up sekarang!"
    elif score >= 60:
        return "Hot lead — jadwalkan follow-up"
    elif score >= 40:
        return "Mid lead — nurture bertahap"
    else:
        return "Low priority — pertimbangkan arsipkan"