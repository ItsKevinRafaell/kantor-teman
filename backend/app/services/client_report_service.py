"""Client report generation and tracking.

Reports are client-facing delivery/performance artifacts. They intentionally
live beside generated documents for archive/download, but use their own
snapshot model so monthly/project reporting is not mixed with invoice/contract
templates.
"""

from __future__ import annotations

import html
import json
import os
import re
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

import httpx
from sqlalchemy.orm import Session

from app.core.dependencies import UPLOADS_DIR, FRONTEND_URL
from app.services.document_service import _slugify_name, build_brand_context
from app.services.pdf_renderer import render_pdf_from_html
from app.services.sales_workflow_service import archive_generated_document
from models import (
    Board,
    BoardCard,
    BoardColumn,
    Contact,
    GeneratedDocument,
    Lead,
    Project,
    ReportSnapshot,
    WorkspaceAttachment,
    WorkspaceCell,
    WorkspaceColumn,
    WorkspaceRow,
    WorkspaceSheet,
)


DOCUMENTS_DIR = os.path.join(UPLOADS_DIR, "generated_documents")
os.makedirs(DOCUMENTS_DIR, exist_ok=True)

REPORT_SERVICE_LABELS = {
    "seo_gmaps": "SEO & Google Maps",
    "maintenance": "Maintenance Website",
    "sosmed": "Kelola Sosial Media",
    "web_dev": "Web Development",
    "web_dev_bulanan": "Web Development Bulanan",
    "branding": "Branding & Identitas Visual",
    "general": "Layanan Umum",
}

REPORT_TYPE_LABELS = {
    "monthly": "Laporan Bulanan",
    "completion": "Laporan Selesai Proyek",
    "internal": "Laporan Internal",
    "lead_audit": "Audit Lead",
}

SERVICE_COMPARISON_METRICS = {
    "seo_gmaps": [
        {"key": "gsc_clicks", "label": "GSC Clicks"},
        {"key": "gsc_impressions", "label": "GSC Impressions"},
        {"key": "gsc_ctr", "label": "CTR"},
        {"key": "gsc_average_position", "label": "Average position", "lower_is_better": True},
    ],
    "maintenance": [
        {"key": "uptime", "label": "Uptime"},
        {"key": "security_score", "label": "Security/site health score"},
        {"key": "incidents", "label": "Insiden", "lower_is_better": True},
        {"key": "resolved_issues", "label": "Issue terselesaikan"},
    ],
    "sosmed": [
        {"key": "posts", "label": "Konten publish"},
        {"key": "reach", "label": "Reach"},
        {"key": "engagement", "label": "Engagement"},
        {"key": "followers_delta", "label": "Perubahan followers"},
    ],
    "web_dev": [
        {"key": "pages_done_count", "label": "Halaman selesai"},
        {"key": "features_done_count", "label": "Fitur selesai"},
        {"key": "open_bugs", "label": "Bug terbuka", "lower_is_better": True},
        {"key": "qa_passed_count", "label": "QA passed"},
    ],
    "web_dev_bulanan": [
        {"key": "pages_done_count", "label": "Update/halaman selesai"},
        {"key": "features_done_count", "label": "Fitur/maintenance selesai"},
        {"key": "open_bugs", "label": "Bug terbuka", "lower_is_better": True},
        {"key": "qa_passed_count", "label": "QA passed"},
    ],
    "branding": [
        {"key": "deliverables_done_count", "label": "Deliverables selesai"},
        {"key": "approved_assets_count", "label": "Asset approved"},
        {"key": "revision_round", "label": "Putaran revisi", "lower_is_better": True},
    ],
    "general": [
        {"key": "progress_score", "label": "Progress score"},
        {"key": "completed_items", "label": "Item selesai"},
        {"key": "open_issues", "label": "Issue terbuka", "lower_is_better": True},
    ],
}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _safe_text(value: Any, fallback: str = "-") -> str:
    if value is None:
        return fallback
    text = str(value)
    return html.escape(text) if text else fallback


def _json_loads(value: Optional[str], fallback: Any) -> Any:
    if not value:
        return fallback
    try:
        return json.loads(value)
    except Exception:
        return fallback


def _clean_dict(data: Optional[dict]) -> dict:
    if not isinstance(data, dict):
        return {}
    return data


def _make_public_slug(db: Session, title: str) -> str:
    base = _slugify_name(title or "laporan").lower().replace("_", "-")
    base = re.sub(r"[^a-z0-9-]+", "-", base).strip("-") or "laporan"
    for _ in range(12):
        suffix = uuid.uuid4().hex[:7]
        slug = f"{base[:60]}-{suffix}"
        exists = db.query(ReportSnapshot.id).filter(ReportSnapshot.public_slug == slug).first()
        if not exists:
            return slug
    return uuid.uuid4().hex


def _metric_value(row: dict, *keys: str) -> Any:
    for key in keys:
        if key in row and row[key] not in (None, ""):
            return row[key]
    return None


def _cell_value(cell: WorkspaceCell, col: WorkspaceColumn) -> Any:
    if col.column_type == "checkbox":
        return bool(cell.value_bool)
    if col.column_type == "number":
        return cell.value_number
    if col.column_type == "date":
        return cell.value_date
    if cell.value_json:
        try:
            return json.loads(cell.value_json)
        except Exception:
            pass
    return cell.value_text


def _row_to_dict(db: Session, row: WorkspaceRow, col_by_id: dict[str, WorkspaceColumn]) -> dict:
    cells = db.query(WorkspaceCell).filter(WorkspaceCell.row_id == row.id).all()
    result = {"row_id": row.id, "board_card_id": row.board_card_id}
    for cell in cells:
        col = col_by_id.get(cell.column_id)
        if col:
            result[col.column_key] = _cell_value(cell, col)
            result[f"{col.column_key}_label"] = col.column_label

    attachments = db.query(WorkspaceAttachment).filter(WorkspaceAttachment.row_id == row.id).all()
    if attachments:
        result["attachments"] = [
            {
                "id": a.id,
                "file_name": a.file_name,
                "file_path": a.file_path,
                "file_type": a.file_type,
                "uploaded_at": a.uploaded_at,
            }
            for a in attachments
        ]
    return result


def _workspace_snapshot(db: Session, project_id: str, month_number: Optional[int]) -> dict:
    query = db.query(WorkspaceSheet).filter(WorkspaceSheet.project_id == project_id)
    if month_number:
        month_sheet = query.filter(WorkspaceSheet.month_number == month_number).first()
        sheets = [month_sheet] if month_sheet else []
    else:
        sheets = query.order_by(WorkspaceSheet.sheet_index).all()

    all_rows: list[dict] = []
    by_sheet: list[dict] = []
    by_status: dict[str, int] = {}
    completed = 0
    evidence: list[dict] = []

    for sheet in sheets:
        if not sheet:
            continue
        cols = db.query(WorkspaceColumn).filter(WorkspaceColumn.sheet_id == sheet.id).order_by(WorkspaceColumn.column_order).all()
        col_by_id = {c.id: c for c in cols}
        rows = db.query(WorkspaceRow).filter(WorkspaceRow.sheet_id == sheet.id).order_by(WorkspaceRow.row_order).all()
        sheet_rows = []
        for row in rows:
            item = _row_to_dict(db, row, col_by_id)
            sheet_rows.append(item)
            all_rows.append(item)
            status = str(_metric_value(item, "status", "Status") or "Belum diisi")
            by_status[status] = by_status.get(status, 0) + 1
            done = bool(_metric_value(item, "done", "selesai", "is_done"))
            if done or status.lower() in {"done", "selesai", "completed"}:
                completed += 1
            for key, value in item.items():
                if not value:
                    continue
                key_lower = key.lower()
                if any(marker in key_lower for marker in ("screenshot", "bukti", "url", "link", "attachment")):
                    if isinstance(value, list):
                        for attachment in value:
                            evidence.append({
                                "label": _metric_value(item, "task_name", "judul", "title") or sheet.sheet_label,
                                "url": attachment.get("file_path") or attachment.get("url") or "",
                                "file_name": attachment.get("file_name") or "",
                                "source": sheet.sheet_label,
                            })
                    elif isinstance(value, str):
                        evidence.append({
                            "label": _metric_value(item, "task_name", "judul", "title") or sheet.sheet_label,
                            "url": value,
                            "source": sheet.sheet_label,
                        })
        by_sheet.append({
            "id": sheet.id,
            "label": sheet.sheet_label,
            "month_number": sheet.month_number,
            "columns": [{"key": c.column_key, "label": c.column_label, "type": c.column_type} for c in cols],
            "rows": sheet_rows,
        })

    total = len(all_rows)
    return {
        "summary": {
            "total_tasks": total,
            "completed_tasks": completed,
            "completion_pct": round((completed / total) * 100, 1) if total else 0,
            "by_status": by_status,
        },
        "sheets": by_sheet,
        "tasks": all_rows,
        "evidence": evidence[:30],
    }


def _board_snapshot(db: Session, project_id: str) -> dict:
    board = db.query(Board).filter(Board.project_id == project_id).first()
    if not board:
        return {"columns": [], "total_cards": 0, "archived_cards": 0}
    columns = db.query(BoardColumn).filter(BoardColumn.board_id == board.id).order_by(BoardColumn.position).all()
    result = []
    total_cards = 0
    archived_cards = 0
    for col in columns:
        cards = db.query(BoardCard).filter(BoardCard.column_id == col.id).order_by(BoardCard.position).all()
        total_cards += len(cards)
        archived_cards += len([c for c in cards if c.is_archived])
        result.append({
            "name": col.name,
            "count": len([c for c in cards if not c.is_archived]),
            "cards": [
                {
                    "id": c.id,
                    "title": c.title,
                    "assignee": c.assignee,
                    "due_date": c.due_date,
                    "is_archived": c.is_archived,
                }
                for c in cards[:20]
            ],
        })
    return {"columns": result, "total_cards": total_cards, "archived_cards": archived_cards}


def _resolve_target(db: Session, target_type: str, target_id: Optional[str]) -> dict:
    project = None
    lead = None
    contact = None

    if target_type == "project" and target_id:
        project = db.query(Project).filter(Project.id == target_id).first()
        if not project:
            raise ValueError("Project tidak ditemukan")
        if project.lead_id:
            lead = db.query(Lead).filter(Lead.id == project.lead_id).first()
    elif target_type == "lead" and target_id and str(target_id).isdigit():
        lead = db.query(Lead).filter(Lead.id == int(target_id)).first()
        if not lead:
            raise ValueError("Lead tidak ditemukan")
    elif target_type == "contact" and target_id and str(target_id).isdigit():
        contact = db.query(Contact).filter(Contact.id == int(target_id)).first()
        if not contact:
            raise ValueError("Kontak tidak ditemukan")
        if contact.lead_id:
            lead = db.query(Lead).filter(Lead.id == contact.lead_id).first()
    elif target_type in {"empty", "internal", ""}:
        target_type = "empty"
    else:
        raise ValueError("Target laporan tidak valid")

    client_name = (
        (lead.business_name if lead else None)
        or (contact.business_name if contact else None)
        or "Internal"
    )
    service_type = project.service_type if project else None
    website_url = ""
    if lead:
        website_url = lead.website_url or lead.original_url or ""

    return {
        "target_type": target_type,
        "project": project,
        "lead": lead,
        "contact": contact,
        "client_name": client_name,
        "service_type": service_type,
        "website_url": website_url,
    }


def _extract_manual_metric(manual_metrics: dict, *keys: str) -> Any:
    for key in keys:
        if key in manual_metrics and manual_metrics[key] not in (None, ""):
            return manual_metrics[key]
    return None


def _manual_service_metrics(service_type: str, manual_metrics: dict) -> dict:
    manual_metrics = _clean_dict(manual_metrics)
    if service_type == "seo_gmaps":
        return {
            "gsc": {
                "clicks": _extract_manual_metric(manual_metrics, "gsc_clicks", "clicks"),
                "impressions": _extract_manual_metric(manual_metrics, "gsc_impressions", "impressions"),
                "ctr": _extract_manual_metric(manual_metrics, "gsc_ctr", "ctr"),
                "average_position": _extract_manual_metric(manual_metrics, "gsc_average_position", "average_position"),
                "clicks_previous": _extract_manual_metric(manual_metrics, "gsc_clicks_previous", "clicks_previous"),
                "impressions_previous": _extract_manual_metric(manual_metrics, "gsc_impressions_previous", "impressions_previous"),
                "ctr_previous": _extract_manual_metric(manual_metrics, "gsc_ctr_previous", "ctr_previous"),
                "average_position_previous": _extract_manual_metric(manual_metrics, "gsc_average_position_previous", "average_position_previous"),
                "clicks_baseline": _extract_manual_metric(manual_metrics, "gsc_clicks_baseline", "clicks_baseline"),
                "impressions_baseline": _extract_manual_metric(manual_metrics, "gsc_impressions_baseline", "impressions_baseline"),
                "ctr_baseline": _extract_manual_metric(manual_metrics, "gsc_ctr_baseline", "ctr_baseline"),
                "average_position_baseline": _extract_manual_metric(manual_metrics, "gsc_average_position_baseline", "average_position_baseline"),
                "clicks_target_next_month": _extract_manual_metric(manual_metrics, "gsc_clicks_target_next_month", "clicks_target_next_month"),
                "impressions_target_next_month": _extract_manual_metric(manual_metrics, "gsc_impressions_target_next_month", "impressions_target_next_month"),
                "ctr_target_next_month": _extract_manual_metric(manual_metrics, "gsc_ctr_target_next_month", "ctr_target_next_month"),
                "average_position_target_next_month": _extract_manual_metric(manual_metrics, "gsc_average_position_target_next_month", "average_position_target_next_month"),
                "comparison_notes": manual_metrics.get("gsc_comparison_notes") or manual_metrics.get("comparison_notes"),
                "next_month_target_notes": manual_metrics.get("seo_next_month_target_notes") or manual_metrics.get("next_month_target_notes"),
                "top_queries": manual_metrics.get("top_queries") or [],
                "top_pages": manual_metrics.get("top_pages") or [],
            },
            "google_business": {
                "views": _extract_manual_metric(manual_metrics, "gbp_views", "business_views"),
                "calls": _extract_manual_metric(manual_metrics, "gbp_calls", "calls"),
                "directions": _extract_manual_metric(manual_metrics, "gbp_directions", "directions"),
                "website_clicks": _extract_manual_metric(manual_metrics, "gbp_website_clicks", "website_clicks"),
            },
        }
    if service_type == "maintenance":
        return {
            "backup": {
                "last_backup_at": manual_metrics.get("last_backup_at"),
                "backup_status": manual_metrics.get("backup_status"),
                "backup_link": manual_metrics.get("backup_link"),
                "backup_size": manual_metrics.get("backup_size"),
            },
            "updates": {
                "core_updates": manual_metrics.get("core_updates"),
                "plugin_updates": manual_metrics.get("plugin_updates"),
                "theme_updates": manual_metrics.get("theme_updates"),
            },
            "health": {
                "security_status": manual_metrics.get("security_status"),
                "security_score": manual_metrics.get("security_score"),
                "uptime": manual_metrics.get("uptime"),
                "incidents": manual_metrics.get("incidents"),
                "resolved_issues": manual_metrics.get("resolved_issues"),
            },
        }
    if service_type == "sosmed":
        return {
            "social": {
                "posts": manual_metrics.get("posts"),
                "reach": manual_metrics.get("reach"),
                "engagement": manual_metrics.get("engagement"),
                "followers_delta": manual_metrics.get("followers_delta"),
                "top_content": manual_metrics.get("top_content") or [],
            }
        }
    if service_type in {"web_dev", "web_dev_bulanan"}:
        return {
            "delivery": {
                "pages_done": manual_metrics.get("pages_done"),
                "pages_done_count": manual_metrics.get("pages_done_count"),
                "features_done": manual_metrics.get("features_done"),
                "features_done_count": manual_metrics.get("features_done_count"),
                "qa_status": manual_metrics.get("qa_status"),
                "qa_passed_count": manual_metrics.get("qa_passed_count"),
                "open_bugs": manual_metrics.get("open_bugs"),
                "handover_link": manual_metrics.get("handover_link"),
            }
        }
    if service_type == "branding":
        return {
            "branding": {
                "deliverables": manual_metrics.get("deliverables"),
                "deliverables_done_count": manual_metrics.get("deliverables_done_count"),
                "revision_round": manual_metrics.get("revision_round"),
                "approved_assets_count": manual_metrics.get("approved_assets_count"),
                "asset_link": manual_metrics.get("asset_link"),
                "approval_status": manual_metrics.get("approval_status"),
            }
        }
    # Retainer-specific metrics (before/after tracking)
    if service_type in {"retainer", "kontrak_retainer"} or any(k in str(manual_metrics) for k in ["retainer_before", "retainer_after"]):
        return {
            "retainer": {
                "before": manual_metrics.get("retainer_before"),
                "after": manual_metrics.get("retainer_after"),
                "notes": manual_metrics.get("retainer_notes"),
            }
        }
    return {"manual": manual_metrics}


def _calculate_delta(current: Any, previous: Any) -> Optional[dict]:
    def parse_number(value: Any) -> float:
        if isinstance(value, str):
            value = value.strip().replace("%", "").replace(",", ".")
        return float(value)

    try:
        cur = parse_number(current)
        prev = parse_number(previous)
    except Exception:
        return None
    delta = cur - prev
    pct = round((delta / prev) * 100, 1) if prev else None
    return {"current": cur, "previous": prev, "delta": delta, "delta_pct": pct}


def _service_metric_defs(service_type: str) -> list[dict]:
    return SERVICE_COMPARISON_METRICS.get(service_type) or SERVICE_COMPARISON_METRICS["general"]


def _derive_comparisons(metrics: dict, service_type: str = "general", report_type: str = "monthly") -> dict:
    manual = metrics.get("manual", {})
    if report_type == "completion":
        reference_suffix = "baseline"
        reference_label = "data awal proyek"
    elif report_type == "monthly":
        reference_suffix = "previous"
        reference_label = "bulan lalu"
    else:
        reference_suffix = "previous"
        reference_label = "periode pembanding"

    metric_rows = []
    legacy = {}
    for definition in _service_metric_defs(service_type):
        key = definition["key"]
        current = _extract_manual_metric(manual, key)
        reference = _extract_manual_metric(manual, f"{key}_{reference_suffix}")
        delta = _calculate_delta(current, reference)
        metric_rows.append({
            "key": key,
            "label": definition["label"],
            "lower_is_better": bool(definition.get("lower_is_better")),
            "delta": delta,
        })
        if service_type == "seo_gmaps":
            legacy_key = key.replace("gsc_", "gsc_")
            legacy[legacy_key] = delta

    notes = (
        manual.get(f"{service_type}_comparison_notes")
        or manual.get("gsc_comparison_notes")
        or manual.get("comparison_notes")
    )
    result = {
        "reference_label": reference_label,
        "notes": notes,
        "metrics": metric_rows,
    }
    result.update(legacy)
    return result


def _derive_next_month_targets(metrics: dict, service_type: str = "general", report_type: str = "monthly") -> dict:
    if report_type != "monthly":
        return {"metrics": [], "notes": None}
    manual = metrics.get("manual", {})
    target_rows = []
    for definition in _service_metric_defs(service_type):
        key = definition["key"]
        target_rows.append({
            "key": key,
            "label": definition["label"],
            "value": _extract_manual_metric(manual, f"{key}_target_next_month"),
        })
    notes = (
        manual.get(f"{service_type}_next_month_target_notes")
        or manual.get("seo_next_month_target_notes")
        or manual.get("next_month_target_notes")
    )
    return {"metrics": target_rows, "notes": notes}


def _date_str(value: Any) -> str:
    """Normalize a date-ish value to a trimmed string, else ''."""
    if value in (None, ""):
        return ""
    if isinstance(value, datetime):
        return value.date().isoformat()
    return str(value).strip()


def _format_period_range(start: str, end: str) -> str:
    """Compose a human range label from optional start/end dates."""
    start = (start or "").strip()
    end = (end or "").strip()
    if start and end:
        return f"{start} s/d {end}" if start != end else start
    return start or end or ""


def _derive_comparison_groups(manual_metrics: Optional[dict]) -> list:
    """Derive arbitrary user-supplied comparison groups.

    Input shape (from admin form, inside manual_metrics["comparison_groups"]):
      [ { title, reference_label, current_label,
          rows: [ {label, previous, current, lower_is_better?} ] } ]
    Each row's delta is computed via _calculate_delta. Returns [] if absent.
    """
    groups_raw = (manual_metrics or {}).get("comparison_groups") or []
    if not isinstance(groups_raw, list):
        return []
    result = []
    for group in groups_raw:
        if not isinstance(group, dict):
            continue

        # Optional structured comparison periods. When a from/to date range is
        # supplied it auto-composes the column label (unless an explicit label
        # was given) and is echoed back so the renderer can show the range.
        before_start = _date_str(group.get("before_start"))
        before_end = _date_str(group.get("before_end"))
        after_start = _date_str(group.get("after_start"))
        after_end = _date_str(group.get("after_end"))
        before_period = _format_period_range(before_start, before_end)
        after_period = _format_period_range(after_start, after_end)

        rows_in = group.get("rows") or []
        rows_out = []
        for row in rows_in:
            if not isinstance(row, dict):
                continue
            label = row.get("label") or row.get("key") or "Metric"
            current = row.get("current")
            previous = row.get("previous")
            lower_is_better = bool(row.get("lower_is_better"))
            delta = _calculate_delta(current, previous)
            if delta is None and current in (None, "") and previous in (None, ""):
                continue  # skip fully-empty rows
            rows_out.append({
                "label": label,
                "current": current,
                "previous": previous,
                "lower_is_better": lower_is_better,
                "delta": delta,
            })
        if not rows_out:
            continue
        # Auto-compose labels from period ranges when the user left the label
        # blank but supplied dates. Explicit labels always win.
        ref_label = group.get("reference_label")
        cur_label = group.get("current_label")
        if not ref_label and before_period:
            ref_label = before_period
        if not cur_label and after_period:
            cur_label = after_period
        result.append({
            "title": group.get("title") or "Komparasi",
            "reference_label": ref_label or "Pembanding",
            "current_label": cur_label or "Sekarang",
            "before_period": before_period or None,
            "after_period": after_period or None,
            "before_start": before_start or None,
            "before_end": before_end or None,
            "after_start": after_start or None,
            "after_end": after_end or None,
            "notes": group.get("notes"),
            "rows": rows_out,
        })
    return result


def _derive_legacy_seo_comparisons(metrics: dict, report_type: str = "monthly") -> dict:
    gsc = metrics.get("service", {}).get("gsc", {})
    if report_type == "completion":
        clicks_reference = gsc.get("clicks_baseline")
        impressions_reference = gsc.get("impressions_baseline")
        ctr_reference = gsc.get("ctr_baseline")
        position_reference = gsc.get("average_position_baseline")
        reference_label = "data awal proyek"
    else:
        clicks_reference = gsc.get("clicks_previous")
        impressions_reference = gsc.get("impressions_previous")
        ctr_reference = gsc.get("ctr_previous")
        position_reference = gsc.get("average_position_previous")
        reference_label = "bulan lalu"
    return {
        "reference_label": reference_label,
        "notes": gsc.get("comparison_notes"),
        "gsc_clicks": _calculate_delta(gsc.get("clicks"), clicks_reference),
        "gsc_impressions": _calculate_delta(gsc.get("impressions"), impressions_reference),
        "gsc_ctr": _calculate_delta(gsc.get("ctr"), ctr_reference),
        "gsc_average_position": _calculate_delta(gsc.get("average_position"), position_reference),
    }


def _resolve_website_url(target: dict, metrics: dict) -> str:
    manual_url = metrics.get("website_url") or metrics.get("url")
    return str(manual_url or target.get("website_url") or "").strip()


def _fetch_pagespeed(website_url: str) -> dict:
    if not website_url:
        return {"status": "skipped", "reason": "URL website belum tersedia"}
    if not website_url.startswith(("http://", "https://")):
        website_url = f"https://{website_url}"
    try:
        response = httpx.get(
            "https://www.googleapis.com/pagespeedonline/v5/runPagespeed",
            params={"url": website_url, "strategy": "mobile", "category": "performance"},
            timeout=12,
        )
        if response.status_code >= 400:
            return {"status": "error", "url": website_url, "detail": f"HTTP {response.status_code}"}
        data = response.json()
        lighthouse = data.get("lighthouseResult", {})
        categories = lighthouse.get("categories", {})
        audits = lighthouse.get("audits", {})
        score = categories.get("performance", {}).get("score")
        return {
            "status": "ok",
            "url": website_url,
            "performance_score": round(float(score) * 100) if score is not None else None,
            "first_contentful_paint": audits.get("first-contentful-paint", {}).get("displayValue"),
            "largest_contentful_paint": audits.get("largest-contentful-paint", {}).get("displayValue"),
            "cumulative_layout_shift": audits.get("cumulative-layout-shift", {}).get("displayValue"),
            "speed_index": audits.get("speed-index", {}).get("displayValue"),
        }
    except Exception as exc:
        return {"status": "error", "url": website_url, "detail": str(exc)}


def _period_label(report_type: str, month_number: Optional[int], period_start: Optional[str], period_end: Optional[str]) -> str:
    if month_number:
        return f"Bulan ke-{month_number}"
    if period_start and period_end:
        return f"{period_start} sampai {period_end}"
    if report_type == "completion":
        return "Selesai proyek"
    return "Periode berjalan"


def _build_narrative(report_type: str, service_type: str, workspace: dict, manual: dict, narrative: dict) -> dict:
    narrative = _clean_dict(narrative)
    summary = workspace.get("summary", {})
    service_label = REPORT_SERVICE_LABELS.get(service_type, "layanan")
    default_summary = (
        f"Periode ini fokus pada eksekusi {service_label}. "
        f"{summary.get('completed_tasks', 0)} dari {summary.get('total_tasks', 0)} tugas tercatat selesai "
        f"({summary.get('completion_pct', 0)}%)."
    )
    if report_type == "completion":
        default_summary = (
            f"Proyek {service_label} sudah masuk tahap penutupan. Laporan ini merangkum pekerjaan, bukti, "
            "hasil utama, dan item yang perlu dipantau setelah handover."
        )
    return {
        "executive_summary": narrative.get("executive_summary") or default_summary,
        "highlights": narrative.get("highlights") or manual.get("highlights") or [],
        "issues": narrative.get("issues") or manual.get("issues") or [],
        "next_steps": narrative.get("next_steps") or manual.get("next_steps") or [],
        "notes": narrative.get("notes") or "",
    }


def build_report_payload(
    db: Session,
    target_type: str,
    target_id: Optional[str],
    report_type: str,
    month_number: Optional[int],
    period_start: Optional[str],
    period_end: Optional[str],
    manual_metrics: Optional[dict],
    evidence: Optional[dict],
    narrative: Optional[dict],
    run_pagespeed: bool = True,
) -> dict:
    target = _resolve_target(db, target_type, target_id)
    project = target["project"]
    service_type = (
        (project.service_type if project else None)
        or (manual_metrics or {}).get("service_type")
        or target.get("service_type")
        or "general"
    )

    workspace = _workspace_snapshot(db, project.id, month_number) if project else {
        "summary": {"total_tasks": 0, "completed_tasks": 0, "completion_pct": 0, "by_status": {}},
        "sheets": [],
        "tasks": [],
        "evidence": [],
    }
    board = _board_snapshot(db, project.id) if project else {"columns": [], "total_cards": 0, "archived_cards": 0}
    manual_metrics = _clean_dict(manual_metrics)
    service_metrics = _manual_service_metrics(service_type, manual_metrics)
    website_url = _resolve_website_url(target, manual_metrics)
    pagespeed = _fetch_pagespeed(website_url) if run_pagespeed else {"status": "skipped", "reason": "PageSpeed tidak dijalankan"}
    metrics = {
        "manual": manual_metrics,
        "service": service_metrics,
        "workspace": workspace.get("summary", {}),
        "board": board,
        "pagespeed": pagespeed,
    }
    metrics["comparisons"] = _derive_comparisons(metrics, service_type, report_type)
    metrics["next_month_targets"] = _derive_next_month_targets(metrics, service_type, report_type)
    metrics["comparison_groups"] = _derive_comparison_groups(manual_metrics)

    evidence_payload = {
        **_clean_dict(evidence),
        "workspace_evidence": workspace.get("evidence", []),
    }
    narrative_payload = _build_narrative(report_type, service_type, workspace, manual_metrics, _clean_dict(narrative))

    period = _period_label(report_type, month_number, period_start, period_end)
    service_label = REPORT_SERVICE_LABELS.get(service_type, service_type)
    report_label = REPORT_TYPE_LABELS.get(report_type, "Laporan Klien")
    project_name = project.name if project else manual_metrics.get("project_name") or report_label
    client_name = target["client_name"]
    title = f"{report_label} {service_label} - {client_name}"
    if month_number:
        title = f"{title} M{month_number:02d}"

    return {
        "title": title,
        "report_type": report_type,
        "target_type": target["target_type"],
        "target_id": target_id,
        "project": {
            "id": project.id if project else None,
            "name": project_name,
            "service_type": service_type,
            "type": project.type if project else None,
            "status": project.status if project else None,
            "nominal": project.nominal if project else None,
            "start_date": project.start_date if project else None,
            "end_date": project.end_date if project else None,
        },
        "client": {
            "name": client_name,
            "phone": target["lead"].phone_number if target.get("lead") else (target["contact"].phone_number if target.get("contact") else None),
            "address": target["lead"].address if target.get("lead") else None,
            "website_url": website_url,
        },
        "period": {
            "label": period,
            "start": period_start,
            "end": period_end,
            "month_number": month_number,
        },
        "service_type": service_type,
        "metrics": metrics,
        "workspace": workspace,
        "evidence": evidence_payload,
        "narrative": narrative_payload,
    }


def _format_number(value: Any) -> str:
    if value in (None, ""):
        return "-"
    try:
        number = float(value)
        if number.is_integer():
            return f"{int(number):,}".replace(",", ".")
        return f"{number:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except Exception:
        return str(value)


def _format_delta(delta: Optional[dict], lower_is_better: bool = False) -> str:
    if not delta:
        return "Komparasi belum diisi"
    raw_delta = delta.get("delta")
    pct = delta.get("delta_pct")
    try:
        direction_good = float(raw_delta or 0) < 0 if lower_is_better else float(raw_delta or 0) > 0
    except Exception:
        direction_good = False
    symbol = "membaik" if direction_good else "berubah"
    pct_text = f" ({pct:+.1f}%)" if isinstance(pct, (int, float)) else ""
    return f"{symbol}: {_format_number(raw_delta)}{pct_text}"


def _render_seo_targets(gsc: dict) -> str:
    targets = [
        ("Target clicks", gsc.get("clicks_target_next_month")),
        ("Target impressions", gsc.get("impressions_target_next_month")),
        ("Target CTR", gsc.get("ctr_target_next_month")),
        ("Target average position", gsc.get("average_position_target_next_month")),
    ]
    if not any(value not in (None, "") for _, value in targets) and not gsc.get("next_month_target_notes"):
        return '<p class="muted">Target bulan depan belum diisi.</p>'
    rows = "".join(f"<tr><th>{_safe_text(label)}</th><td>{_safe_text(_format_number(value))}</td></tr>" for label, value in targets)
    notes = gsc.get("next_month_target_notes")
    if notes:
        rows += f"<tr><th>Catatan target</th><td>{_safe_text(notes)}</td></tr>"
    return f"<table><tbody>{rows}</tbody></table>"


def _render_comparison_groups(payload: dict) -> str:
    groups = payload.get("metrics", {}).get("comparison_groups") or []
    if not groups:
        return ""
    blocks = []
    for group in groups:
        ref = group.get("reference_label") or "Pembanding"
        cur = group.get("current_label") or "Sekarang"
        before_period = group.get("before_period")
        after_period = group.get("after_period")
        # Show the structured period range under the column header when present
        # and not already identical to the (possibly auto-composed) label.
        ref_sub = (
            f'<div class="muted" style="font-weight:400;font-size:11px">{_safe_text(before_period)}</div>'
            if before_period and before_period != ref else ""
        )
        cur_sub = (
            f'<div class="muted" style="font-weight:400;font-size:11px">{_safe_text(after_period)}</div>'
            if after_period and after_period != cur else ""
        )
        rows = "".join(
            f"<tr><th>{_safe_text(item.get('label'))}</th>"
            f"<td>{_format_number(item.get('previous'))}</td>"
            f"<td>{_format_number(item.get('current'))}</td>"
            f"<td>{_format_delta(item.get('delta'), bool(item.get('lower_is_better')))}</td></tr>"
            for item in group.get("rows", [])
        )
        notes_html = ""
        if group.get("notes"):
            notes_html = f'<tr><th>Catatan</th><td colspan="3">{_safe_text(group.get("notes"))}</td></tr>'
        blocks.append(f"""
        <div class="section"><h2>{_safe_text(group.get('title') or 'Komparasi Performa')}</h2>
          <table>
            <thead><tr><th>Metric</th><th>{_safe_text(ref)}{ref_sub}</th><th>{_safe_text(cur)}{cur_sub}</th><th>Perubahan</th></tr></thead>
            <tbody>{rows}{notes_html}</tbody>
          </table>
        </div>""")
    return "".join(blocks)


def _render_comparison_section(payload: dict) -> str:
    comparisons = payload.get("metrics", {}).get("comparisons", {})
    rows = []
    for item in comparisons.get("metrics", []):
        delta = item.get("delta") or {}
        rows.append(
            f"<tr><th>{_safe_text(item.get('label'))}</th>"
            f"<td>{_safe_text(_format_delta(delta, bool(item.get('lower_is_better'))))}</td>"
            f"<td>{_safe_text(comparisons.get('reference_label') or 'Pembanding')}: {_format_number(delta.get('previous'))} - Sekarang: {_format_number(delta.get('current'))}</td></tr>"
        )
    if not rows:
        return '<div class="section"><h2>Komparasi Performa</h2><p class="muted">Komparasi belum diisi.</p></div>'
    rows.append(f"<tr><th>Catatan</th><td colspan=\"2\">{_safe_text(comparisons.get('notes'), 'Belum ada notes komparasi.')}</td></tr>")
    return f"""
    <div class="section"><h2>Komparasi Performa</h2>
      <table><tbody>
        <tr><th>Pembanding</th><td colspan="2">{_safe_text(comparisons.get('reference_label') or 'periode pembanding')}</td></tr>
        {''.join(rows)}
      </tbody></table>
    </div>
    """


def _render_next_month_targets(payload: dict) -> str:
    if payload.get("report_type") != "monthly":
        return ""
    targets = payload.get("metrics", {}).get("next_month_targets", {})
    rows = [
        f"<tr><th>{_safe_text(item.get('label'))}</th><td>{_safe_text(_format_number(item.get('value')))}</td></tr>"
        for item in targets.get("metrics", [])
        if item.get("value") not in (None, "")
    ]
    notes = targets.get("notes")
    if not rows and not notes:
        return '<div class="section"><h2>Target Bulan Depan</h2><p class="muted">Target bulan depan belum diisi.</p></div>'
    if notes:
        rows.append(f"<tr><th>Catatan target</th><td>{_safe_text(notes)}</td></tr>")
    return f"""
    <div class="section"><h2>Target Bulan Depan</h2>
      <table><tbody>{''.join(rows)}</tbody></table>
    </div>
    """


def _list_items(items: Any) -> str:
    if not items:
        return '<p class="muted">Belum ada catatan.</p>'
    if isinstance(items, str):
        items = [line.strip() for line in items.splitlines() if line.strip()]
    if not isinstance(items, list):
        items = [str(items)]
    return "<ul>" + "".join(f"<li>{_safe_text(item)}</li>" for item in items[:12]) + "</ul>"


def _render_metric_cards(payload: dict) -> str:
    summary = payload.get("workspace", {}).get("summary", {})
    board = payload.get("metrics", {}).get("board", {})
    pagespeed = payload.get("metrics", {}).get("pagespeed", {})
    cards = [
        ("Progress tugas", f"{summary.get('completion_pct', 0)}%"),
        ("Tugas selesai", f"{summary.get('completed_tasks', 0)} / {summary.get('total_tasks', 0)}"),
        ("Card aktif", _format_number(sum(col.get("count", 0) for col in board.get("columns", [])))),
        ("PageSpeed mobile", _format_number(pagespeed.get("performance_score")) if pagespeed.get("status") == "ok" else "Belum tersedia"),
    ]
    return '<div class="kpi-grid">' + "".join(
        f'<div class="kpi"><div class="label">{_safe_text(label)}</div><div class="value">{_safe_text(value)}</div></div>'
        for label, value in cards
    ) + "</div>"


def _render_service_section(payload: dict) -> str:
    service_type = payload.get("service_type") or "general"
    service = payload.get("metrics", {}).get("service", {})
    pagespeed = payload.get("metrics", {}).get("pagespeed", {})

    if service_type == "seo_gmaps":
        gsc = service.get("gsc", {})
        gbp = service.get("google_business", {})
        return f"""
        <div class="section"><h2>Performa SEO & Google Maps</h2>
          <table><tbody>
            <tr><th>GSC Clicks</th><td>{_format_number(gsc.get('clicks'))}</td><td>Impressions: {_format_number(gsc.get('impressions'))}</td></tr>
            <tr><th>CTR</th><td>{_safe_text(gsc.get('ctr'))}</td><td>Average position: {_safe_text(gsc.get('average_position'))}</td></tr>
            <tr><th>Google Business</th><td>Views: {_format_number(gbp.get('views'))}</td><td>Calls: {_format_number(gbp.get('calls'))}, Directions: {_format_number(gbp.get('directions'))}, Website clicks: {_format_number(gbp.get('website_clicks'))}</td></tr>
          </tbody></table>
        </div>
        """

    if service_type == "maintenance":
        backup = service.get("backup", {})
        updates = service.get("updates", {})
        health = service.get("health", {})
        return f"""
        <div class="section"><h2>Maintenance, Backup, dan Keamanan</h2>
          <table><tbody>
            <tr><th>Backup terakhir</th><td>{_safe_text(backup.get('last_backup_at'))}</td><td>Status: {_safe_text(backup.get('backup_status'))}</td></tr>
            <tr><th>Update</th><td>Core: {_safe_text(updates.get('core_updates'))}</td><td>Plugin: {_safe_text(updates.get('plugin_updates'))}, Theme: {_safe_text(updates.get('theme_updates'))}</td></tr>
            <tr><th>Health</th><td>{_safe_text(health.get('security_status'))}</td><td>Uptime: {_safe_text(health.get('uptime'))}, Insiden: {_safe_text(health.get('incidents'))}</td></tr>
          </tbody></table>
        </div>
        """

    if service_type == "sosmed":
        social = service.get("social", {})
        return f"""
        <div class="section"><h2>Performa Sosial Media</h2>
          <table><tbody>
            <tr><th>Konten publish</th><td>{_format_number(social.get('posts'))}</td><td>Reach: {_format_number(social.get('reach'))}</td></tr>
            <tr><th>Engagement</th><td>{_format_number(social.get('engagement'))}</td><td>Follower delta: {_format_number(social.get('followers_delta'))}</td></tr>
          </tbody></table>
        </div>
        """

    if service_type in {"web_dev", "web_dev_bulanan"}:
        delivery = service.get("delivery", {})
        return f"""
        <div class="section"><h2>Delivery Web Development</h2>
          <table><tbody>
            <tr><th>Halaman selesai</th><td>{_safe_text(delivery.get('pages_done'))}</td><td>Fitur selesai: {_safe_text(delivery.get('features_done'))}</td></tr>
            <tr><th>QA</th><td>{_safe_text(delivery.get('qa_status'))}</td><td>Handover: {_safe_text(delivery.get('handover_link'))}</td></tr>
          </tbody></table>
        </div>
        """

    if service_type == "branding":
        branding = service.get("branding", {})
        return f"""
        <div class="section"><h2>Deliverables Branding</h2>
          <table><tbody>
            <tr><th>Deliverables</th><td>{_safe_text(branding.get('deliverables'))}</td><td>Revisi: {_safe_text(branding.get('revision_round'))}</td></tr>
            <tr><th>Approval</th><td>{_safe_text(branding.get('approval_status'))}</td><td>Asset final: {_safe_text(branding.get('asset_link'))}</td></tr>
          </tbody></table>
        </div>
        """

    return f"""
    <div class="section"><h2>Performa Teknis</h2>
      <table><tbody>
        <tr><th>PageSpeed</th><td>{_safe_text(pagespeed.get('status'))}</td><td>Score: {_safe_text(pagespeed.get('performance_score'))}</td></tr>
      </tbody></table>
    </div>
    """


def _render_workspace_table(payload: dict) -> str:
    tasks = payload.get("workspace", {}).get("tasks", [])[:40]
    if not tasks:
        return '<div class="section"><h2>Aktivitas</h2><p class="muted">Belum ada task workspace untuk periode ini.</p></div>'
    rows = []
    for task in tasks:
        name = _metric_value(task, "task_name", "judul", "title", "nama_tugas") or "Task"
        status = _metric_value(task, "status") or ("Selesai" if task.get("done") else "Belum selesai")
        notes = _metric_value(task, "catatan", "notes", "deskripsi", "description") or ""
        rows.append(f"<tr><td>{_safe_text(name)}</td><td>{_safe_text(status)}</td><td>{_safe_text(notes, '')}</td></tr>")
    return """
    <div class="section"><h2>Aktivitas Periode Ini</h2>
      <table><thead><tr><th>Task</th><th>Status</th><th>Catatan</th></tr></thead>
      <tbody>""" + "".join(rows) + "</tbody></table></div>"


def _is_image_evidence(item: dict, url: str) -> bool:
    ftype = (item.get("file_type") or "").lower()
    if ftype.startswith("image/"):
        return True
    ext = os.path.splitext(url)[1].lower()
    return ext in {".png", ".jpg", ".jpeg", ".webp", ".gif"}


def _absolute_url(url: str) -> str:
    if url and url.startswith("/"):
        return f"{(FRONTEND_URL or '').rstrip('/')}{url}"
    return url


def _render_evidence(payload: dict) -> str:
    evidence = payload.get("evidence", {})
    items = evidence.get("items", []) or evidence.get("workspace_evidence", []) or []
    if not items:
        return '<div class="section"><h2>Bukti Pengerjaan</h2><p class="muted">Belum ada bukti/link yang dilampirkan.</p></div>'
    blocks = []
    for item in items[:20]:
        label = item.get("label") or item.get("title") or item.get("file_name") or "Bukti"
        url = item.get("url") or item.get("file_path") or item.get("link") or ""
        abs_url = _absolute_url(url)
        if url and _is_image_evidence(item, url):
            blocks.append(f"""
            <div class="evidence-item">
              <p class="evidence-label">{_safe_text(label)}</p>
              <img src="{_safe_text(abs_url)}" alt="{_safe_text(label)}"/>
            </div>""")
        elif url:
            blocks.append(f"""
            <div class="evidence-item">
              <p class="evidence-label">{_safe_text(label)}</p>
              <a href="{_safe_text(abs_url)}">{_safe_text(item.get('file_name') or url)}</a>
              <span class="muted">{_safe_text(item.get('source') or '')}</span>
            </div>""")
        else:
            blocks.append(f'<div class="evidence-item"><p class="evidence-label">{_safe_text(label)}</p><span class="muted">Tidak ada link</span></div>')
    return f"""
    <div class="section"><h2>Bukti Pengerjaan</h2>
      <div class="evidence-grid">{''.join(blocks)}</div>
    </div>"""


def render_report_html(payload: dict, brand: Optional[dict] = None) -> str:
    brand = brand or {}
    brand_name = brand.get("brand_name") or "Kantor Teman"
    narrative = payload.get("narrative", {})
    client = payload.get("client", {})
    project = payload.get("project", {})
    period = payload.get("period", {})
    service_label = REPORT_SERVICE_LABELS.get(payload.get("service_type"), payload.get("service_type") or "Layanan")
    title = payload.get("title") or "Laporan Klien"
    created_at = datetime.now(timezone.utc).strftime("%d/%m/%Y")
    return f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
* {{ box-sizing: border-box; }}
body {{ margin: 0; padding: 32px; color: #1f2937; font-family: Helvetica, Arial, sans-serif; background: #ffffff; }}
.header {{ border-bottom: 3px solid #f59e0b; padding-bottom: 18px; margin-bottom: 22px; }}
.brand {{ color: #b45309; font-size: 12px; font-weight: 700; text-transform: uppercase; letter-spacing: .08em; }}
h1 {{ margin: 6px 0 8px; font-size: 26px; line-height: 1.18; color: #111827; }}
h2 {{ margin: 0 0 12px; font-size: 16px; color: #111827; }}
.meta {{ color: #6b7280; font-size: 12px; line-height: 1.55; }}
.section {{ margin: 18px 0; padding: 16px; border: 1px solid #e5e7eb; border-radius: 8px; }}
.summary {{ font-size: 13px; line-height: 1.7; }}
.kpi-grid {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px; margin-top: 12px; }}
.kpi {{ border: 1px solid #fde68a; background: #fffbeb; border-radius: 8px; padding: 12px; }}
.kpi .label {{ font-size: 10px; text-transform: uppercase; color: #92400e; font-weight: 700; }}
.kpi .value {{ margin-top: 5px; font-size: 20px; color: #111827; font-weight: 800; }}
table {{ width: 100%; border-collapse: collapse; font-size: 12px; }}
th, td {{ padding: 8px; border-bottom: 1px solid #e5e7eb; text-align: left; vertical-align: top; }}
th {{ color: #374151; background: #f9fafb; font-weight: 700; }}
ul {{ margin: 0; padding-left: 18px; font-size: 12px; line-height: 1.7; }}
.muted {{ color: #6b7280; font-size: 12px; }}
.footer {{ margin-top: 28px; padding-top: 12px; border-top: 1px solid #e5e7eb; color: #9ca3af; font-size: 10px; text-align: center; }}
img {{ max-width: 100%; height: auto; border-radius: 8px; display: block; margin: 6px 0; }}
.evidence-grid {{ display: grid; grid-template-columns: 1fr; gap: 14px; }}
.evidence-item {{ border: 1px solid #e5e7eb; border-radius: 8px; padding: 10px; }}
.evidence-label {{ font-weight: 700; font-size: 12px; margin: 0 0 4px; color: #374151; }}
.evidence-item a {{ color: #b45309; font-size: 12px; }}
</style>
</head>
<body>
  <div class="header">
    <div class="brand">{_safe_text(brand_name)}</div>
    <h1>{_safe_text(title)}</h1>
    <div class="meta">
      Klien: <b>{_safe_text(client.get('name'))}</b><br>
      Proyek: {_safe_text(project.get('name'))} - Layanan: {_safe_text(service_label)}<br>
      Periode: {_safe_text(period.get('label'))} - Dibuat: {_safe_text(created_at)}
    </div>
  </div>

  <div class="section">
    <h2>Ringkasan Eksekutif</h2>
    <p class="summary">{_safe_text(narrative.get('executive_summary'), '')}</p>
    {_render_metric_cards(payload)}
  </div>

  {_render_service_section(payload)}
  {_render_comparison_groups(payload)}
  {_render_comparison_section(payload)}
  {_render_next_month_targets(payload)}
  {_render_workspace_table(payload)}

  <div class="section">
    <h2>Highlight</h2>
    {_list_items(narrative.get('highlights'))}
  </div>

  <div class="section">
    <h2>Issue dan Catatan</h2>
    {_list_items(narrative.get('issues'))}
  </div>

  <div class="section">
    <h2>Rencana Berikutnya</h2>
    {_list_items(narrative.get('next_steps'))}
  </div>

  {_render_evidence(payload)}

  <div class="footer">Laporan dibuat oleh {_safe_text(brand_name)}. Data eksternal manual/API ditampilkan sesuai input yang tersedia pada saat laporan dibuat.</div>
</body>
</html>"""


def create_report_snapshot(
    db: Session,
    *,
    target_type: str,
    target_id: Optional[str],
    report_type: str,
    month_number: Optional[int],
    period_start: Optional[str],
    period_end: Optional[str],
    manual_metrics: Optional[dict],
    evidence: Optional[dict],
    narrative: Optional[dict],
    run_pagespeed: bool,
    public_enabled: bool,
    actor: str,
) -> ReportSnapshot:
    payload = build_report_payload(
        db,
        target_type=target_type,
        target_id=target_id,
        report_type=report_type,
        month_number=month_number,
        period_start=period_start,
        period_end=period_end,
        manual_metrics=manual_metrics,
        evidence=evidence,
        narrative=narrative,
        run_pagespeed=run_pagespeed,
    )
    project_id = payload["project"]["id"]
    lead_id = None
    if payload["target_type"] == "lead" and target_id and str(target_id).isdigit():
        lead_id = int(target_id)
    elif project_id:
        project = db.query(Project).filter(Project.id == project_id).first()
        lead_id = project.lead_id if project else None

    snapshot = ReportSnapshot(
        id=str(uuid.uuid4()),
        report_type=report_type,
        target_type=payload["target_type"],
        target_id=target_id,
        project_id=project_id,
        lead_id=lead_id,
        service_type=payload["service_type"],
        title=payload["title"],
        period_start=period_start,
        period_end=period_end,
        month_number=month_number,
        metrics_json=json.dumps(payload["metrics"], ensure_ascii=False),
        evidence_json=json.dumps(payload["evidence"], ensure_ascii=False),
        narrative_json=json.dumps(payload["narrative"], ensure_ascii=False),
        public_slug=_make_public_slug(db, payload["title"]) if public_enabled else None,
        public_enabled=public_enabled,
        status="Draft",
        generated_by=actor,
        created_at=_now(),
        updated_at=_now(),
    )
    db.add(snapshot)
    db.flush()

    payload["snapshot"] = {"id": snapshot.id, "public_slug": snapshot.public_slug}
    brand = build_brand_context(db)
    rendered_html = render_report_html(payload, brand)
    pdf_bytes = render_pdf_from_html(rendered_html, UPLOADS_DIR)

    file_id = str(uuid.uuid4())
    pdf_filename = f"{file_id}.pdf"
    pdf_path = os.path.join(DOCUMENTS_DIR, pdf_filename)
    with open(pdf_path, "wb") as pdf_file:
        pdf_file.write(pdf_bytes)

    client_slug = _slugify_name(payload["client"]["name"] or "klien")
    service_slug = _slugify_name(payload["service_type"] or "umum")
    suffix = f"M{month_number:02d}" if month_number else datetime.now(timezone.utc).strftime("%Y%m")
    display_name = f"LAPORAN_{service_slug}_{client_slug}_{suffix}"
    file_url = f"/uploads/generated_documents/{pdf_filename}"

    doc = GeneratedDocument(
        id=file_id,
        template_id=None,
        template_name=f"Laporan Klien - {REPORT_SERVICE_LABELS.get(payload['service_type'], payload['service_type'])}",
        target_type=payload["target_type"] if payload["target_type"] != "empty" else None,
        target_id=target_id,
        variables_used=json.dumps(payload, ensure_ascii=False),
        file_url=file_url,
        display_filename=display_name,
        status="Draft",
        generated_by=actor,
    )
    db.add(doc)
    db.flush()
    snapshot.generated_document_id = doc.id

    try:
        archive_generated_document(
            db,
            doc,
            display_name,
            payload["client"]["name"] or "Internal",
            payload["project"]["name"] or "Laporan",
            "Laporan",
        )
    except Exception as exc:
        print(f"[REPORT_ARCHIVE] skip: {exc}", flush=True)

    db.commit()
    db.refresh(snapshot)
    return snapshot


def snapshot_payload(snapshot: ReportSnapshot) -> dict:
    return {
        "id": snapshot.id,
        "report_type": snapshot.report_type,
        "target_type": snapshot.target_type,
        "target_id": snapshot.target_id,
        "project_id": snapshot.project_id,
        "lead_id": snapshot.lead_id,
        "service_type": snapshot.service_type,
        "title": snapshot.title,
        "period_start": snapshot.period_start,
        "period_end": snapshot.period_end,
        "month_number": snapshot.month_number,
        "metrics": _json_loads(snapshot.metrics_json, {}),
        "evidence": _json_loads(snapshot.evidence_json, {}),
        "narrative": _json_loads(snapshot.narrative_json, {}),
        "public_slug": snapshot.public_slug,
        "public_enabled": snapshot.public_enabled,
        "public_url": f"/client-report/{snapshot.public_slug}" if snapshot.public_slug else None,
        "open_count": snapshot.open_count,
        "first_viewed_at": snapshot.first_viewed_at,
        "last_viewed_at": snapshot.last_viewed_at,
        "max_duration_seconds": snapshot.max_duration_seconds,
        "generated_document_id": snapshot.generated_document_id,
        "status": snapshot.status,
        "generated_by": snapshot.generated_by,
        "created_at": snapshot.created_at,
        "updated_at": snapshot.updated_at,
    }


def public_snapshot_payload(db: Session, slug: str) -> dict:
    snapshot = db.query(ReportSnapshot).filter(
        ReportSnapshot.public_slug == slug,
        ReportSnapshot.public_enabled == True,
    ).first()
    if not snapshot:
        raise ValueError("Laporan tidak ditemukan")
    now = _now()
    snapshot.open_count = (snapshot.open_count or 0) + 1
    snapshot.last_viewed_at = now
    if not snapshot.first_viewed_at:
        snapshot.first_viewed_at = now
    db.commit()
    db.refresh(snapshot)
    payload = snapshot_payload(snapshot)
    payload["download_document_id"] = snapshot.generated_document_id
    return payload


def track_public_duration(db: Session, slug: str, duration_seconds: int) -> ReportSnapshot:
    snapshot = db.query(ReportSnapshot).filter(
        ReportSnapshot.public_slug == slug,
        ReportSnapshot.public_enabled == True,
    ).first()
    if not snapshot:
        raise ValueError("Laporan tidak ditemukan")
    duration = max(0, min(int(duration_seconds or 0), 24 * 60 * 60))
    if duration > (snapshot.max_duration_seconds or 0):
        snapshot.max_duration_seconds = duration
    snapshot.last_viewed_at = _now()
    db.commit()
    db.refresh(snapshot)
    return snapshot
