from __future__ import annotations

from typing import Optional

import os

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.core.dependencies import FRONTEND_URL, _get_setting, get_current_user
from app.services.client_report_service import (
    DOCUMENTS_DIR,
    REPORT_SERVICE_LABELS,
    REPORT_TYPE_LABELS,
    build_report_payload,
    create_report_snapshot,
    public_snapshot_payload,
    snapshot_payload,
    track_public_duration,
)
from models import GeneratedDocument, Project, ReportSnapshot, User, get_db

router = APIRouter()


class ReportGenerateIn(BaseModel):
    report_type: str = Field("monthly", pattern="^(monthly|completion|internal|lead_audit)$")
    target_type: str = Field("project", pattern="^(project|lead|contact|empty|internal)$")
    target_id: Optional[str] = None
    month_number: Optional[int] = Field(None, ge=1, le=60)
    period_start: Optional[str] = None
    period_end: Optional[str] = None
    metrics: dict = Field(default_factory=dict)
    evidence: dict = Field(default_factory=dict)
    narrative: dict = Field(default_factory=dict)
    run_pagespeed: bool = True
    public_enabled: bool = True


class DurationIn(BaseModel):
    duration_seconds: int = Field(0, ge=0, le=86400)


def _with_absolute_public_url(item: dict, db: Session) -> dict:
    public_url = item.get("public_url")
    if public_url and public_url.startswith("/"):
        frontend_url = (_get_setting("frontend_url", FRONTEND_URL) or FRONTEND_URL).rstrip("/")
        item["public_url"] = f"{frontend_url}{public_url}"
    return item


@router.get("/api/reports/config")
def report_config(current_user: User = Depends(get_current_user)):
    return {
        "report_types": REPORT_TYPE_LABELS,
        "service_labels": REPORT_SERVICE_LABELS,
        "target_types": {
            "empty": "Tanpa target - untuk laporan internal atau catatan umum",
            "lead": "Lead - untuk audit pre-sales dan prospek",
            "contact": "Klien/Kontak - untuk dokumen akun klien",
            "project": "Proyek - untuk laporan kerja bulanan/selesai proyek",
        },
    }


@router.get("/api/reports/draft")
def draft_report(
    target_type: str = Query("project"),
    target_id: Optional[str] = Query(None),
    report_type: str = Query("monthly"),
    month_number: Optional[int] = Query(None),
    period_start: Optional[str] = Query(None),
    period_end: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return build_report_payload(
            db,
            target_type=target_type,
            target_id=target_id,
            report_type=report_type,
            month_number=month_number,
            period_start=period_start,
            period_end=period_end,
            manual_metrics={},
            evidence={},
            narrative={},
            run_pagespeed=False,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.get("/api/reports")
def list_reports(
    lead_id: Optional[int] = Query(None),
    project_id: Optional[str] = Query(None),
    report_type: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    query = db.query(ReportSnapshot)
    if project_id:
        query = query.filter(ReportSnapshot.project_id == project_id)
    if lead_id:
        project_ids = [p.id for p in db.query(Project.id).filter(Project.lead_id == lead_id).all()]
        conditions = [ReportSnapshot.lead_id == lead_id]
        if project_ids:
            conditions.append(ReportSnapshot.project_id.in_(project_ids))
        query = query.filter(or_(*conditions))
    if report_type:
        query = query.filter(ReportSnapshot.report_type == report_type)
    reports = query.order_by(ReportSnapshot.created_at.desc()).limit(200).all()
    return [_with_absolute_public_url(snapshot_payload(item), db) for item in reports]


@router.get("/api/reports/{report_id}")
def get_report(report_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    snapshot = db.query(ReportSnapshot).filter(ReportSnapshot.id == report_id).first()
    if not snapshot:
        raise HTTPException(status_code=404, detail="Laporan tidak ditemukan")
    return _with_absolute_public_url(snapshot_payload(snapshot), db)


@router.post("/api/reports/generate")
def generate_report(body: ReportGenerateIn, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    try:
        snapshot = create_report_snapshot(
            db,
            target_type=body.target_type,
            target_id=body.target_id,
            report_type=body.report_type,
            month_number=body.month_number,
            period_start=body.period_start,
            period_end=body.period_end,
            manual_metrics=body.metrics,
            evidence=body.evidence,
            narrative=body.narrative,
            run_pagespeed=body.run_pagespeed,
            public_enabled=body.public_enabled,
            actor=current_user.name,
        )
        return _with_absolute_public_url(snapshot_payload(snapshot), db)
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc))
    except HTTPException:
        db.rollback()
        raise
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Gagal membuat laporan: {exc}")


@router.get("/api/reports/public/{slug}")
def get_public_report(slug: str, db: Session = Depends(get_db)):
    try:
        payload = public_snapshot_payload(db, slug)
        return _with_absolute_public_url(payload, db)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.post("/api/reports/public/{slug}/duration")
def track_report_duration(slug: str, body: DurationIn, db: Session = Depends(get_db)):
    try:
        snapshot = track_public_duration(db, slug, body.duration_seconds)
        return {"ok": True, "max_duration_seconds": snapshot.max_duration_seconds}
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.get("/api/reports/public/{slug}/download")
def download_public_report(slug: str, db: Session = Depends(get_db)):
    snapshot = db.query(ReportSnapshot).filter(
        ReportSnapshot.public_slug == slug,
        ReportSnapshot.public_enabled == True,
    ).first()
    if not snapshot or not snapshot.generated_document_id:
        raise HTTPException(status_code=404, detail="Laporan tidak ditemukan")
    doc = db.query(GeneratedDocument).filter(GeneratedDocument.id == snapshot.generated_document_id).first()
    if not doc or not doc.file_url:
        raise HTTPException(status_code=404, detail="PDF laporan tidak ditemukan")
    filename = os.path.basename(doc.file_url)
    fpath = os.path.join(DOCUMENTS_DIR, filename)
    if not os.path.exists(fpath):
        raise HTTPException(status_code=404, detail="File PDF tidak ada di disk")
    return FileResponse(fpath, media_type="application/pdf", filename=f"{doc.display_filename or snapshot.title}.pdf")
