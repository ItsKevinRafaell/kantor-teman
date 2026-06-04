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
from models import Base, engine, SessionLocal, get_db, log_audit, User, Lead, Contact, Project, Proposal, ProposalAnalytics, Transaction, Wallet, Subscription, PaymentMethod, AuditLog, Board, BoardColumn, BoardCard, BoardCardComment, BoardCardChecklist, BoardCardActivity, WorkspaceSheet, WorkspaceColumn, WorkspaceRow, WorkspaceCell, WorkspaceAttachment, DynamicTemplate, Document, DocumentFolder, DocumentTemplate, GeneratedDocument, BrandKit, BrandAsset, DocumentSequence, ServiceItem, Category, Product, ClientNote, ClientCredential, ClientDocument, AdsCampaign, BlastCampaign, BlastMessage, FollowUpSequence, MessageTemplate, ScrapeHistory, LeadActivityLog, LeadAnalysis, AIProxy, ContentProvider, ContentSession, ContentGeneration, SystemSettings, AIModel, ProviderConfig, ContentSchedule
from schemas import *
from app.core.dependencies import get_current_user, require_admin

router = APIRouter()

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
    total_leads = db.query(func.count(Lead.id)).scalar() or 0
    total_clients = db.query(func.count(Contact.id)).scalar() or 0
    conversion_rate = round((total_clients / total_leads * 100), 1) if total_leads > 0 else 0.0

    rows = db.execute(
        select(func.lower(Lead.product_interest).label("product"), func.count(Lead.id).label("count"))
        .where(Lead.product_interest.isnot(None))
        .group_by(func.lower(Lead.product_interest))
        .order_by(func.count(Lead.id).desc())
    ).all()
    leads_by_product = [{"product": r[0].title() if r[0] else r[0], "count": r[1]} for r in rows]

    status_rows = db.execute(
        select(Lead.status, func.count(Lead.id).label("count")).group_by(Lead.status)
    ).all()
    leads_by_status = [{"status": r[0], "count": r[1]} for r in status_rows]

    return {
        "total_leads": total_leads,
        "total_clients": total_clients,
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


# ---------------------------------------------------------------------------
# Follow-up Sequence
# ---------------------------------------------------------------------------


@router.get("/api/analytics/patterns")
def get_conversion_patterns(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    leads = db.query(Lead).filter(Lead.is_archived == False).all()

    by_category = {}
    by_city = {}
    by_rating = {"high": {"total": 0, "converted": 0}, "mid": {"total": 0, "converted": 0}, "low": {"total": 0, "converted": 0}}

    for lead in leads:
        is_converted = lead.status == "Closed/Client"
        category = lead.product_interest or "Lainnya"
        city = lead.address.split(",")[-1].strip() if lead.address and "," in lead.address else (lead.address or "Unknown")

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
    jobs = []
    for name, job in _analysis_jobs.items():
        jobs.append({**job, "type": "analysis", "batch_name": name})
    for name, job in _blast_jobs.items():
        jobs.append({**job, "type": "blast", "batch_name": name})
    return jobs


# ---------------------------------------------------------------------------
# Projects
# ---------------------------------------------------------------------------


