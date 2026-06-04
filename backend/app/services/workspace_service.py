"""Workspace Service Layer — extracted business logic from routers/workspace.py"""
import json
import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session
from sqlalchemy import func

from models import Project, WorkspaceSheet, WorkspaceColumn, WorkspaceRow, WorkspaceCell, Lead
from schemas import WorkspaceInitIn


# ─── Workspace Init ──────────────────────────────────────────────────────────

def init_workspace_sheets(
    db: Session,
    project_id: str,
    service_type: str,
    contract_months: int,
    contract_days: Optional[int] = None,
) -> dict:
    """
    Initialize workspace sheets for a project using template definitions.
    Returns workspace data dict with sheets.
    """
    from workspace_templates import build_sheets_for_service, build_sheets_for_days, WORKSPACE_TEMPLATES

    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise ValueError("Project tidak ditemukan")

    existing = db.query(WorkspaceSheet).filter(WorkspaceSheet.project_id == project_id).first()
    if existing:
        return get_workspace_data(db, project_id)

    if service_type not in WORKSPACE_TEMPLATES:
        raise ValueError(f"service_type tidak valid: {service_type}")

    project.service_type = service_type
    project.contract_months = contract_months

    if contract_days and contract_days < 30:
        sheet_defs = build_sheets_for_days(contract_days, service_type)
    else:
        sheet_defs = build_sheets_for_service(service_type, contract_months)

    now = datetime.now(timezone.utc).isoformat()

    for idx, sdef in enumerate(sheet_defs):
        sheet = WorkspaceSheet(
            id=str(uuid.uuid4()),
            project_id=project_id,
            sheet_index=idx,
            sheet_label=sdef["label"],
            service_type=service_type,
            month_number=sdef.get("month"),
            created_at=now,
        )
        db.add(sheet)
        db.flush()

        col_map = {}
        for ci, cdef in enumerate(sdef["columns"]):
            col = WorkspaceColumn(
                id=str(uuid.uuid4()),
                sheet_id=sheet.id,
                column_key=cdef["key"],
                column_label=cdef["label"],
                column_type=cdef["type"],
                column_options=json.dumps(cdef.get("options", [])),
                column_order=ci,
                is_system=cdef.get("is_system", False),
                created_at=now,
            )
            db.add(col)
            db.flush()
            col_map[cdef["key"]] = col

        for ri, rdef in enumerate(sdef.get("default_rows", [])):
            row = WorkspaceRow(
                id=str(uuid.uuid4()),
                sheet_id=sheet.id,
                row_order=ri,
                is_template=True,
                created_at=now,
            )
            db.add(row)
            db.flush()

            for key, val in rdef.items():
                col = col_map.get(key)
                if not col:
                    continue
                cell = WorkspaceCell(
                    id=str(uuid.uuid4()),
                    row_id=row.id,
                    column_id=col.id,
                    updated_at=now,
                )
                if col.column_type == "checkbox":
                    cell.value_bool = bool(val)
                elif col.column_type == "number":
                    cell.value_number = float(val) if val else None
                else:
                    cell.value_text = str(val) if val else None
                db.add(cell)
            db.flush()
            _sync_row_to_board(row.id, db)

    db.commit()
    return get_workspace_data(db, project_id)


# ─── Workspace Data (GET) ────────────────────────────────────────────────────

def get_workspace_data(db: Session, project_id: str) -> dict:
    """Fetch all workspace data for a project (sheets, columns, rows, cells)."""
    sheets = db.query(WorkspaceSheet).filter(
        WorkspaceSheet.project_id == project_id
    ).order_by(WorkspaceSheet.sheet_index).all()

    result = {"project_id": project_id, "service_type": None, "sheets": []}
    if sheets:
        result["service_type"] = sheets[0].service_type

    for sheet in sheets:
        cols = db.query(WorkspaceColumn).filter(
            WorkspaceColumn.sheet_id == sheet.id
        ).order_by(WorkspaceColumn.column_order).all()

        rows = db.query(WorkspaceRow).filter(
            WorkspaceRow.sheet_id == sheet.id
        ).order_by(WorkspaceRow.row_order).all()

        cols_data = [{
            "id": c.id,
            "column_key": c.column_key,
            "column_label": c.column_label,
            "column_type": c.column_type,
            "column_options": json.loads(c.column_options or "[]"),
            "column_order": c.column_order,
            "is_system": c.is_system,
        } for c in cols]

        rows_data = []
        for row in rows:
            cells = db.query(WorkspaceCell).filter(WorkspaceCell.row_id == row.id).all()
            cells_map = {}
            for cell in cells:
                cells_map[cell.column_id] = {
                    "id": cell.id,
                    "value_text": cell.value_text,
                    "value_bool": cell.value_bool,
                    "value_number": cell.value_number,
                    "value_date": cell.value_date,
                    "value_json": cell.value_json,
                }
            rows_data.append({
                "id": row.id,
                "row_order": row.row_order,
                "board_card_id": row.board_card_id,
                "is_template": row.is_template,
                "cells": cells_map,
            })

        result["sheets"].append({
            "id": sheet.id,
            "sheet_index": sheet.sheet_index,
            "sheet_label": sheet.sheet_label,
            "month_number": sheet.month_number,
            "columns": cols_data,
            "rows": rows_data,
        })

    return result


# ─── Workspace Summary ───────────────────────────────────────────────────────

def get_workspace_summary(db: Session, project_id: str) -> dict:
    """Aggregate row/column/cell counts and progress for a workspace."""
    sheets = db.query(WorkspaceSheet).filter(
        WorkspaceSheet.project_id == project_id
    ).all()

    total_rows = 0
    total_cells = 0
    done_rows = 0

    done_col_ids = []
    for sheet in sheets:
        done_col = db.query(WorkspaceColumn).filter(
            WorkspaceColumn.sheet_id == sheet.id,
            WorkspaceColumn.column_key == "done",
        ).first()
        if done_col:
            done_col_ids.append(done_col.id)

    for sheet in sheets:
        rows = db.query(WorkspaceRow).filter(
            WorkspaceRow.sheet_id == sheet.id
        ).all()
        total_rows += len(rows)

        for row in rows:
            cells = db.query(WorkspaceCell).filter(
                WorkspaceCell.row_id == row.id
            ).all()
            total_cells += len(cells)

            # Check if done (done column has value_bool=True)
            if done_col_ids:
                done_cells = db.query(WorkspaceCell).filter(
                    WorkspaceCell.row_id == row.id,
                    WorkspaceCell.column_id.in_(done_col_ids),
                    WorkspaceCell.value_bool == True,
                ).count()
                if done_cells > 0:
                    done_rows += 1

    progress = round(done_rows / total_rows * 100) if total_rows > 0 else 0

    return {
        "project_id": project_id,
        "sheet_count": len(sheets),
        "total_rows": total_rows,
        "total_cells": total_cells,
        "done_rows": done_rows,
        "progress_percent": progress,
    }


# ─── Cell Update ─────────────────────────────────────────────────────────────

def update_cell(
    db: Session,
    cell_id: str,
    value_text: Optional[str] = None,
    value_bool: Optional[bool] = None,
    value_number: Optional[float] = None,
    value_date: Optional[str] = None,
    value_json: Optional[str] = None,
) -> WorkspaceCell:
    """Update a cell value and recalculate board card status."""
    cell = db.query(WorkspaceCell).filter(WorkspaceCell.id == cell_id).first()
    if not cell:
        raise ValueError("Cell tidak ditemukan")

    if value_text is not None:
        cell.value_text = value_text
    if value_bool is not None:
        cell.value_bool = value_bool
    if value_number is not None:
        cell.value_number = value_number
    if value_date is not None:
        cell.value_date = value_date
    if value_json is not None:
        cell.value_json = value_json

    cell.updated_at = datetime.now(timezone.utc).isoformat()
    db.commit()
    db.refresh(cell)

    # Sync row to board card
    _sync_row_to_board(cell.row_id, db)

    return cell


def add_row(
    db: Session,
    sheet_id: str,
    cells: dict,
    row_order: Optional[int] = None,
) -> WorkspaceRow:
    """Add a new row to a sheet with initial cell values."""
    now = datetime.now(timezone.utc).isoformat()

    # Get next row_order if not provided
    if row_order is None:
        max_order = db.query(func.max(WorkspaceRow.row_order)).filter(
            WorkspaceRow.sheet_id == sheet_id
        ).scalar()
        row_order = (max_order or 0) + 1

    row = WorkspaceRow(
        id=str(uuid.uuid4()),
        sheet_id=sheet_id,
        row_order=row_order,
        is_template=False,
        created_at=now,
    )
    db.add(row)
    db.flush()

    # Get column map
    cols = db.query(WorkspaceColumn).filter(
        WorkspaceColumn.sheet_id == sheet_id
    ).all()
    col_map = {c.id: c for c in cols}

    # Create cells
    for col_id_str, val in cells.items():
        col = col_map.get(col_id_str)
        if not col:
            continue
        cell = WorkspaceCell(
            id=str(uuid.uuid4()),
            row_id=row.id,
            column_id=col.id,
            updated_at=now,
        )
        if col.column_type == "checkbox":
            cell.value_bool = bool(val)
        elif col.column_type == "number":
            cell.value_number = float(val) if val else None
        else:
            cell.value_text = str(val) if val else None
        db.add(cell)

    db.commit()
    db.refresh(row)
    _sync_row_to_board(row.id, db)
    return row


# ─── Board Sync Helper ──────────────────────────────────────────────────────

def _sync_row_to_board(row_id: str, db: Session) -> None:
    """Update board card status based on workspace row progress."""
    row = db.query(WorkspaceRow).filter(WorkspaceRow.id == row_id).first()
    if not row or not row.board_card_id:
        return

    sheet = db.query(WorkspaceSheet).filter(WorkspaceSheet.id == row.sheet_id).first()
    if not sheet:
        return

    # Get done column
    done_col = db.query(WorkspaceColumn).filter(
        WorkspaceColumn.sheet_id == sheet.id,
        WorkspaceColumn.column_key == "done",
    ).first()

    if not done_col:
        return

    done_cell = db.query(WorkspaceCell).filter(
        WorkspaceCell.row_id == row_id,
        WorkspaceCell.column_id == done_col.id,
    ).first()

    # Update board card archive status based on done checkbox
    from models import BoardCard
    card = db.query(BoardCard).filter(BoardCard.id == row.board_card_id).first()
    if card and done_cell and done_cell.value_bool:
        card.is_archived = True
        db.commit()


# ─── Workspace List (for GET /api/workspace-list) ───────────────────────────

def get_workspace_list_data(db: Session) -> list[dict]:
    """Build workspace list with progress for all active projects."""
    projects = db.query(Project).filter(Project.is_archived == False).order_by(Project.status).all()
    project_ids = [p.id for p in projects]
    lead_ids = [p.lead_id for p in projects if p.lead_id]

    leads = {l.id: l for l in db.query(Lead).filter(Lead.id.in_(lead_ids)).all()} if lead_ids else {}
    sheets = {s.project_id: s for s in db.query(WorkspaceSheet).filter(
        WorkspaceSheet.project_id.in_(project_ids)
    ).all()}
    sheet_ids = [s.id for s in sheets.values()]

    rows_by_sheet = {}
    if sheet_ids:
        rows = db.query(WorkspaceRow).filter(WorkspaceRow.sheet_id.in_(sheet_ids)).all()
        for r in rows:
            rows_by_sheet.setdefault(r.sheet_id, []).append(r)

    done_cols = {
        c.sheet_id: c for c in db.query(WorkspaceColumn).filter(
            WorkspaceColumn.sheet_id.in_(sheet_ids),
            WorkspaceColumn.column_key == "done",
        ).all()
    }

    done_counts = {}
    if done_cols:
        done_col_ids = [c.id for c in done_cols.values()]
        counts = db.query(WorkspaceCell.column_id, func.count(WorkspaceCell.id)).filter(
            WorkspaceCell.column_id.in_(done_col_ids),
            WorkspaceCell.value_bool == True,
        ).group_by(WorkspaceCell.column_id).all()
        for col_id, count in counts:
            done_counts[col_id] = count

    result = []
    for p in projects:
        lead = leads.get(p.lead_id) if p.lead_id else None
        sheet = sheets.get(p.id)
        has_workspace = sheet is not None
        progress = None

        if has_workspace and sheet:
            rows = rows_by_sheet.get(sheet.id, [])
            if rows:
                done_col = done_cols.get(sheet.id)
                if done_col:
                    done_count = done_counts.get(done_col.id, 0)
                    progress = round(done_count / len(rows) * 100) if rows else 0

        result.append({
            "id": p.id,
            "name": p.name,
            "service_type": p.service_type,
            "contract_months": p.contract_months,
            "lead_name": lead.business_name if lead else None,
            "status": p.status,
            "has_workspace": has_workspace,
            "progress": progress,
        })

    return result