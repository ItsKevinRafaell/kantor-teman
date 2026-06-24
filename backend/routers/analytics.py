import re, html as html_mod, random, asyncio, uuid, json, csv, io, base64, hmac, time, httpx
import os
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv
from fastapi import APIRouter, Depends, HTTPException, Request, BackgroundTasks, UploadFile, File, Form, Query, Body
from fastapi.responses import StreamingResponse, RedirectResponse, HTMLResponse, Response
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from typing import Optional, List, Any
from models import get_db, log_audit, User, Lead, Contact, Project, ScrapeHistory, LeadActivityLog, Proposal, ReengagementAlert, Transaction, AuditLog, Notification
from schemas import *
from app.core.dependencies import get_current_user, require_admin, _check_simple_rate_limit, _analysis_jobs, _blast_jobs
from app.services.notification_service import mark_notification_read, notification_to_dict
from app.constants import CLIENT_STATUS_VALUES

router = APIRouter()


def _normalize_service_name(raw: Optional[str]) -> str:
    key = (raw or "").strip()
    if not key:
        return "Belum ditentukan"
    lower = key.lower()
    if "landing page" in lower:
        return "Landing Page"
    if "website" in lower or "web dev" in lower or lower == "web":
        return "Website Development"
    if "seo" in lower and ("google maps" in lower or "gmaps" in lower):
        return "SEO & Google Maps"
    if "seo" in lower:
        return "SEO"
    if "sosmed" in lower or "sosial media" in lower or "social media" in lower:
        return "Kelola Sosial Media"
    if "maintenance" in lower or "maintain" in lower:
        return "Maintenance Website"
    if "logo" in lower or "branding" in lower or "desain logo" in lower:
        return "Desain Logo & Branding"
    return key


_PROVINCE_WORDS = {
    "indonesia", "jawa barat", "jawa tengah", "jawa timur", "dki jakarta",
    "jakarta", "banten", "bali", "di yogyakarta", "yogyakarta",
    "sumatera utara", "sumatera barat", "sumatera selatan", "lampung",
    "kalimantan timur", "kalimantan barat", "kalimantan selatan",
    "sulawesi selatan", "sulawesi utara",
}


def _extract_city(address: Optional[str]) -> str:
    parts = [p.strip() for p in (address or "").split(",") if p.strip()]
    if not parts:
        return "Tidak diketahui"
    for part in reversed(parts):
        cleaned = re.sub(r"\b\d{4,}\b", "", part).strip()
        if cleaned and cleaned.lower() not in _PROVINCE_WORDS:
            return cleaned
    return parts[-1]


def _is_converted_lead(lead: Lead, contact_lead_ids: set[int]) -> bool:
    return lead.status in CLIENT_STATUS_VALUES or lead.id in contact_lead_ids

@router.get("/api/scrape-history")
def get_scrape_history(
    search: Optional[str] = Query(None),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    query = db.query(ScrapeHistory)
    if search:
        q = f"%{search}%"
        query = query.filter(
            (ScrapeHistory.category.ilike(q)) |
            (ScrapeHistory.location.ilike(q)) |
            (ScrapeHistory.batch_name.ilike(q))
        )
    if date_from:
        query = query.filter(ScrapeHistory.scraped_at >= date_from)
    if date_to:
        # Include the entire day by appending T23:59:59
        query = query.filter(ScrapeHistory.scraped_at <= f"{date_to}T23:59:59")
    total = query.count()
    history = query.order_by(ScrapeHistory.id.desc()).offset((page - 1) * page_size).limit(page_size).all()
    items = []
    for h in history:
        batch = h.batch_name or f"{h.category} - {h.location}"
        lead_count = db.query(Lead).filter(Lead.batch_name == batch).count() if batch else 0
        items.append({
            "id": h.id,
            "category": h.category,
            "location": h.location,
            "product_interest": h.product_interest,
            "results_count": h.results_count,
            "scraped_at": h.scraped_at,
            "batch_name": h.batch_name,
            "lead_count": lead_count,
        })
    return {"items": items, "total": total, "page": page, "page_size": page_size}


def _score_to_action(score: int) -> str:
    if score >= 80:
        return "personal_wa"
    if score >= 65:
        return "blast_ready"
    if score >= 50:
        return "warm"
    return "low_priority"



def get_leads(
    status: Optional[str] = Query(None),
    batch_name: Optional[str] = Query(None),
    include_archived: bool = Query(False),
    archived_only: bool = Query(False),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    query = db.query(Lead)
    if archived_only:
        query = query.filter(Lead.is_archived == True)
    elif not include_archived:
        query = query.filter(Lead.is_archived == False)
    if status:
        query = query.filter(Lead.status == status)
    if batch_name:
        query = query.filter(Lead.batch_name == batch_name)
    leads = query.order_by(Lead.lead_score.desc()).all()

    # Ghost Viewer aggregation: count LINK_CLICKED in last 48h
    threshold_48h = (datetime.now(timezone.utc) - timedelta(hours=48)).isoformat()
    ghost_lead_ids = set()
    if leads:
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
        lead_dict = {
            "id": lead.id,
            "business_name": lead.business_name,
            "phone_number": lead.phone_number,
            "address": lead.address,
            "original_url": lead.original_url,
            "status": lead.status,
            "product_interest": lead.product_interest,
            "batch_name": lead.batch_name,
            "rating": lead.rating or 0,
            "is_archived": lead.is_archived,
            "deleted_at": lead.deleted_at,
            "lead_score": lead.lead_score or 0,
            "action_recommendation": _score_to_action(lead.lead_score or 0),
            "is_ghost_viewer": lead.id in ghost_lead_ids,
            "google_rating": lead.google_rating,
            "review_count": lead.review_count,
            "website_url": lead.website_url,
            "sales_owner": lead.sales_owner,
            "next_action_at": lead.next_action_at,
            "loss_reason": lead.loss_reason,
            "do_not_contact": bool(lead.do_not_contact),
        }
        results.append(lead_dict)
    return results



@router.get("/api/analytics")
def get_analytics(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    active_leads = db.query(Lead).filter(Lead.is_archived == False).all()
    total_leads = len(active_leads)
    total_clients = db.query(func.count(Contact.id)).scalar() or 0
    contact_lead_ids = {row[0] for row in db.query(Contact.lead_id).filter(Contact.lead_id.isnot(None)).all()}
    converted_lead_count = sum(1 for lead in active_leads if _is_converted_lead(lead, contact_lead_ids))
    conversion_rate = round((converted_lead_count / total_leads * 100), 1) if total_leads > 0 else 0.0

    revenue_by_lead: dict[int, float] = defaultdict(float)
    projects = db.query(Project).filter(Project.is_archived == False).all()
    for project in projects:
        if project.lead_id:
            revenue_by_lead[project.lead_id] += float(project.nominal or 0)

    product_raw: dict = defaultdict(lambda: {"count": 0, "converted": 0, "revenue": 0.0})
    for lead in active_leads:
        key = _normalize_service_name(lead.product_interest)
        product_raw[key]["count"] += 1
        if _is_converted_lead(lead, contact_lead_ids):
            product_raw[key]["converted"] += 1
        product_raw[key]["revenue"] += revenue_by_lead.get(lead.id, 0.0)

    leads_by_product = [
        {
            "product": k,
            "count": v["count"],
            "converted": v["converted"],
            "conversion_rate": round((v["converted"] / v["count"] * 100), 1) if v["count"] else 0,
            "revenue": round(v["revenue"], 2),
        }
        for k, v in sorted(product_raw.items(), key=lambda x: (x[1]["converted"], x[1]["count"], x[1]["revenue"]), reverse=True)
    ]

    status_rows = db.execute(
        select(Lead.status, func.count(Lead.id).label("count")).filter(Lead.is_archived == False).group_by(Lead.status)
    ).all()
    leads_by_status = [{"status": r[0], "count": r[1]} for r in status_rows]

    return {
        "total_leads": total_leads,
        "total_clients": total_clients,
        "converted_leads": converted_lead_count,
        "conversion_rate": conversion_rate,
        "leads_by_product": leads_by_product,
        "leads_by_status": leads_by_status,
    }



@router.get("/api/alerts/reengagement")
def get_reengagement_alerts(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    alerts = db.query(ReengagementAlert, Lead, Proposal).join(
        Lead, ReengagementAlert.lead_id == Lead.id
    ).join(
        Proposal, ReengagementAlert.proposal_id == Proposal.id
    ).filter(ReengagementAlert.is_read == False).order_by(ReengagementAlert.triggered_at.desc()).limit(20).all()

    results = []
    for alert, lead, proposal in alerts:
        days_since = 0
        if proposal.first_viewed_at:
            try:
                first_view = datetime.fromisoformat(proposal.first_viewed_at.replace("Z", "+00:00"))
                days_since = (datetime.now(timezone.utc) - first_view).days
            except Exception:
                pass
        results.append({
            "id": alert.id,
            "lead_id": lead.id,
            "business_name": lead.business_name,
            "phone_number": lead.phone_number,
            "category": lead.product_interest,
            "triggered_at": alert.triggered_at,
            "days_since_first_view": days_since,
            "proposal_slug": proposal.slug,
        })
    return results



@router.post("/api/alerts/reengagement/{alert_id}/read")
def mark_alert_read(alert_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    alert = db.query(ReengagementAlert).filter(ReengagementAlert.id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert tidak ditemukan")
    alert.is_read = True
    db.commit()
    return {"ok": True}


@router.get("/api/notifications")
def list_notifications(
    include_read: bool = Query(False),
    limit: int = Query(30, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    query = db.query(Notification)
    if not include_read:
        query = query.filter(Notification.is_read == False)
    notifications = query.order_by(Notification.created_at.desc()).limit(limit).all()
    return [notification_to_dict(n) for n in notifications]


@router.post("/api/notifications/{notification_id}/read")
def read_notification(notification_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    try:
        notif = mark_notification_read(db, notification_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return notification_to_dict(notif)


# ---------------------------------------------------------------------------
# Follow-up Sequence
# ---------------------------------------------------------------------------


@router.get("/api/analytics/patterns")
def get_conversion_patterns(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    leads = db.query(Lead).filter(Lead.is_archived == False).all()
    contact_lead_ids = {row[0] for row in db.query(Contact.lead_id).filter(Contact.lead_id.isnot(None)).all()}

    by_category = {}
    by_city = {}
    by_rating = {"high": {"total": 0, "converted": 0}, "mid": {"total": 0, "converted": 0}, "low": {"total": 0, "converted": 0}}

    for lead in leads:
        is_converted = _is_converted_lead(lead, contact_lead_ids)
        category = _normalize_service_name(lead.product_interest)
        city = _extract_city(lead.address)

        if category not in by_category:
            by_category[category] = {"total": 0, "converted": 0}
        by_category[category]["total"] += 1
        if is_converted:
            by_category[category]["converted"] += 1

        if city not in by_city:
            by_city[city] = {"total": 0, "converted": 0}
        by_city[city]["total"] += 1
        if is_converted:
            by_city[city]["converted"] += 1

        rating = lead.rating or 0
        if rating >= 4:
            by_rating["high"]["total"] += 1
            if is_converted:
                by_rating["high"]["converted"] += 1
        elif rating >= 3:
            by_rating["mid"]["total"] += 1
            if is_converted:
                by_rating["mid"]["converted"] += 1
        else:
            by_rating["low"]["total"] += 1
            if is_converted:
                by_rating["low"]["converted"] += 1

    def calc_rate(d):
        return round((d["converted"] / d["total"] * 100), 1) if d["total"] > 0 else 0

    category_patterns = sorted([
        {"segment": k, "total": v["total"], "converted": v["converted"], "rate": calc_rate(v)}
        for k, v in by_category.items() if v["total"] >= 3
    ], key=lambda x: x["rate"], reverse=True)

    city_patterns = sorted([
        {"segment": k, "total": v["total"], "converted": v["converted"], "rate": calc_rate(v)}
        for k, v in by_city.items() if v["total"] >= 3
    ], key=lambda x: x["rate"], reverse=True)

    rating_patterns = [
        {"segment": "Rating 4-5", "total": by_rating["high"]["total"], "converted": by_rating["high"]["converted"], "rate": calc_rate(by_rating["high"])},
        {"segment": "Rating 3", "total": by_rating["mid"]["total"], "converted": by_rating["mid"]["converted"], "rate": calc_rate(by_rating["mid"])},
        {"segment": "Rating 0-2", "total": by_rating["low"]["total"], "converted": by_rating["low"]["converted"], "rate": calc_rate(by_rating["low"])},
    ]

    top_segment = category_patterns[0] if category_patterns else None
    recommendation = f"Fokus scrape lebih banyak di segment '{top_segment['segment']}' — conversion rate {top_segment['rate']}% (tertinggi)." if top_segment and top_segment["rate"] > 0 else "Belum cukup data untuk rekomendasi. Terus scrape dan blast untuk mengumpulkan pattern."

    return {
        "by_category": category_patterns[:10],
        "by_city": city_patterns[:10],
        "by_rating": rating_patterns,
        "recommendation": recommendation,
    }


# ---------------------------------------------------------------------------
# Finance - Wallets
# ---------------------------------------------------------------------------


@router.get("/api/audit-logs")
def get_audit_logs(
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    total = db.query(func.count(AuditLog.id)).scalar() or 0
    logs = db.query(AuditLog).order_by(AuditLog.id.desc()).offset(offset).limit(limit).all()
    return {
        "total": total,
        "logs": [{
            "id": log.id,
            "timestamp": log.timestamp,
            "actor": log.actor,
            "action": log.action,
            "table_name": log.table_name,
            "record_id": log.record_id,
            "details": json.loads(log.details) if log.details else None,
        } for log in logs],
    }


# ---------------------------------------------------------------------------
# Export CSV
# ---------------------------------------------------------------------------


@router.get("/api/export/leads")
def export_leads_csv(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    _check_simple_rate_limit(f"export_leads:{current_user.id}", 10, 60, db)
    leads = db.query(Lead).filter(Lead.is_archived == False).all()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["ID", "Nama Bisnis", "Nomor Telepon", "Alamat", "Status", "Produk", "Batch", "Rating"])
    for l in leads:
        writer.writerow([l.id, l.business_name, l.phone_number, l.address or "", l.status, l.product_interest or "", l.batch_name or "", l.rating])
    output.seek(0)
    from fastapi.responses import Response
    return Response(
        content=output.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=leads_export.csv"},
    )



@router.get("/api/export/finance")
def export_finance_csv(current_user: User = Depends(require_admin), db: Session = Depends(get_db)):
    _check_simple_rate_limit(f"export_finance:{current_user.id}", 10, 60, db)
    transactions = db.query(Transaction).filter(Transaction.is_archived == False).order_by(Transaction.date.desc()).all()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["ID", "Wallet ID", "Tipe", "Jumlah", "Kategori", "Tanggal", "Catatan", "Lead ID", "Sudah Ditagih"])
    for t in transactions:
        writer.writerow([t.id, t.wallet_id, t.type, t.amount, t.category or "", t.date, t.notes or "", t.lead_id or "", t.is_billed])
    output.seek(0)
    from fastapi.responses import Response
    return Response(
        content=output.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=finance_export.csv"},
    )


# ---------------------------------------------------------------------------
# Master Data - Categories
# ---------------------------------------------------------------------------


@router.get("/api/background-jobs")
def get_all_background_jobs(current_user: User = Depends(require_admin)):
    import os, json as _json
    jobs = []
    # Read from file for cross-worker visibility (different WSGI worker may have written it)
    job_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), "analysis_jobs.json")
    if os.path.exists(job_file):
        try:
            with open(job_file) as f:
                all_jobs = _json.load(f)
            for name, job in all_jobs.items():
                jobs.append({**job, "type": "analysis", "batch_name": name})
        except Exception:
            pass
    # Fallback to in-memory
    for name, job in _analysis_jobs.items():
        if not any(j["batch_name"] == name for j in jobs):
            jobs.append({**job, "type": "analysis", "batch_name": name})
    for name, job in _blast_jobs.items():
        jobs.append({**job, "type": "blast", "batch_name": name})
    return jobs


# ---------------------------------------------------------------------------
# Projects
# ---------------------------------------------------------------------------
