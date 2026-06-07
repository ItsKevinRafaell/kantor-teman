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
from models import get_db, log_audit, User, Lead, Contact, Project, Board, BoardColumn, BoardCard, BoardCardComment, BoardCardChecklist, BoardCardActivity, WorkspaceSheet, WorkspaceColumn, WorkspaceRow, WorkspaceCell, WorkspaceAttachment, DocumentTemplate, GeneratedDocument, Category
from schemas import *
from app.core.dependencies import (get_current_user, require_admin, FRONTEND_URL, UPLOADS_DIR,
    _get_setting, get_fonnte_token, get_9router_config, build_analysis_prompt,
    _call_ai_sync, parse_ai_response, log_ai_cost, get_ai_config,
    generate_report_for_lead, send_fonnte_message, log_outreach_cost, call_ai_provider,
    WORKSPACE_TEMPLATES, build_sheets_for_service, build_sheets_for_days, _BASE_COLS,
    sync_row_to_board, sync_row_status_to_board,
)
from app.services.workspace_service import (
    get_workspace_data,
    get_workspace_list_data,
)
from app.core.cache import invalidate_workspace_list_cache, cached

router = APIRouter()

@router.get("/api/projects", response_model=list[ProjectOut])
def get_projects(
    lead_id: Optional[int] = Query(None),
    status: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    query = db.query(Project)
    if lead_id:
        query = query.filter(Project.lead_id == lead_id)
    if status:
        query = query.filter(Project.status == status)
    return query.all()



@router.post("/api/projects", response_model=ProjectOut, status_code=201)
def create_project(body: ProjectIn, current_user: User = Depends(require_admin), db: Session = Depends(get_db)):
    if body.type not in ("FIXED", "RETAINER"):
        raise HTTPException(status_code=400, detail="Type harus 'FIXED' atau 'RETAINER'")
    if body.status not in ("ACTIVE", "COMPLETED", "HOLD"):
        raise HTTPException(status_code=400, detail="Status harus 'ACTIVE', 'COMPLETED', atau 'HOLD'")

    # Resolve lead_id: from contact_id if provided, or use lead_id directly
    resolved_lead_id = body.lead_id
    if body.contact_id and not resolved_lead_id:
        contact = db.query(Contact).filter(Contact.id == body.contact_id).first()
        if not contact:
            raise HTTPException(status_code=404, detail="Kontak tidak ditemukan")
        resolved_lead_id = contact.lead_id
        if not resolved_lead_id:
            raise HTTPException(status_code=400, detail="Kontak belum memiliki relasi Lead")

    # Validate lead_id exists if provided
    if resolved_lead_id:
        lead = db.query(Lead).filter(Lead.id == resolved_lead_id).first()
        if not lead:
            raise HTTPException(status_code=400, detail="Lead tidak ditemukan")

    # Auto-calculate contract_months and contract_days from dates
    months = body.contract_months
    contract_days = None
    if body.start_date and body.end_date:
        try:
            from datetime import date as _date
            sd = _date.fromisoformat(body.start_date)
            ed = _date.fromisoformat(body.end_date)
            contract_days = (ed - sd).days
            if not months or months <= 0:
                months = max(1, (ed.year - sd.year) * 12 + (ed.month - sd.month))
        except Exception:
            pass
    if not months or months <= 0:
        months = WORKSPACE_TEMPLATES.get(body.service_type or "", {}).get("default_months", 1) if body.service_type else 1

    project = Project(
        id=str(uuid.uuid4()),
        lead_id=resolved_lead_id,
        name=body.name,
        type=body.type,
        status=body.status,
        nominal=body.nominal,
        start_date=body.start_date,
        end_date=body.end_date,
        color=body.color or "gray",
        service_type=body.service_type,
        contract_months=months,
    )
    db.add(project)
    db.flush()  # Get project.id without committing

    # Auto-create board with default columns
    board = Board(id=str(uuid.uuid4()), project_id=project.id)
    db.add(board)
    db.flush()

    # Default columns: To Do, In Progress, Review, Done (neutral colors)
    default_columns = [
        ("To Do", "gray"),
        ("In Progress", "slate"),
        ("Review", "neutral"),
        ("Done", "stone"),
    ]
    for i, (name, color) in enumerate(default_columns):
        col = BoardColumn(id=str(uuid.uuid4()), board_id=board.id, name=name, position=i, color=color)
        db.add(col)

    db.commit()
    db.refresh(project)
    log_audit(db, current_user.name, "CREATE", "projects", project.id, {"name": body.name, "lead_id": body.lead_id})
    invalidate_workspace_list_cache()

    # Auto-init workspace always — use service_type template or fallback to general
    _svc = body.service_type if (body.service_type and body.service_type in WORKSPACE_TEMPLATES) else "general"
    if _svc:
        try:
            if contract_days and contract_days < 30:
                sheet_defs = build_sheets_for_days(contract_days, _svc)
            else:
                sheet_defs = build_sheets_for_service(_svc, months)
            now_ws = datetime.now(timezone.utc).isoformat()
            for idx, sdef in enumerate(sheet_defs):
                sheet = WorkspaceSheet(
                    id=str(uuid.uuid4()), project_id=project.id,
                    sheet_index=idx, sheet_label=sdef["label"],
                    service_type=_svc, month_number=sdef.get("month"),
                    created_at=now_ws,
                )
                db.add(sheet)
                db.flush()
                col_map = {}
                for ci, cdef in enumerate(sdef["columns"]):
                    col = WorkspaceColumn(
                        id=str(uuid.uuid4()), sheet_id=sheet.id,
                        column_key=cdef["key"], column_label=cdef["label"],
                        column_type=cdef["type"], column_options=json.dumps(cdef.get("options", [])),
                        column_order=ci, is_system=cdef.get("is_system", False), created_at=now_ws,
                    )
                    db.add(col)
                    db.flush()
                    col_map[cdef["key"]] = col
                for ri, rdef in enumerate(sdef.get("default_rows", [])):
                    row = WorkspaceRow(
                        id=str(uuid.uuid4()), sheet_id=sheet.id,
                        row_order=ri, is_template=True, created_at=now_ws,
                    )
                    db.add(row)
                    db.flush()
                    for key, val in rdef.items():
                        col = col_map.get(key)
                        if not col:
                            continue
                        cell = WorkspaceCell(id=str(uuid.uuid4()), row_id=row.id, column_id=col.id, updated_at=now_ws)
                        if col.column_type == "checkbox":
                            cell.value_bool = bool(val)
                        elif col.column_type == "number":
                            cell.value_number = float(val) if val else None
                        else:
                            cell.value_text = str(val) if val else None
                        db.add(cell)
                    db.flush()
                    sync_row_to_board(row.id, db)
            db.commit()
        except Exception as e:
            print(f"[AUTO_WORKSPACE] error: {e}", flush=True)

    return project



@router.get("/api/projects/{project_id}", response_model=ProjectOut)
def get_project(project_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project tidak ditemukan")
    return project



@router.put("/api/projects/{project_id}", response_model=ProjectOut)
def update_project(project_id: str, body: ProjectIn, current_user: User = Depends(require_admin), db: Session = Depends(get_db)):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project tidak ditemukan")

    # Resolve lead_id: from contact_id if provided, or use lead_id directly
    resolved_lead_id = body.lead_id
    if body.contact_id and not resolved_lead_id:
        contact = db.query(Contact).filter(Contact.id == body.contact_id).first()
        if not contact:
            raise HTTPException(status_code=404, detail="Kontak tidak ditemukan")
        resolved_lead_id = contact.lead_id
        if not resolved_lead_id:
            raise HTTPException(status_code=400, detail="Kontak belum memiliki relasi Lead")

    # Validate lead_id exists if provided
    if resolved_lead_id:
        lead = db.query(Lead).filter(Lead.id == resolved_lead_id).first()
        if not lead:
            raise HTTPException(status_code=400, detail="Lead tidak ditemukan")

    project.lead_id = resolved_lead_id
    project.name = body.name
    project.type = body.type
    project.status = body.status
    project.nominal = body.nominal
    project.start_date = body.start_date
    project.end_date = body.end_date
    project.color = body.color or "gray"
    project.service_type = body.service_type
    project.contract_months = body.contract_months
    db.commit()
    db.refresh(project)
    log_audit(db, current_user.name, "UPDATE", "projects", project_id, {"name": body.name})
    invalidate_workspace_list_cache()
    return project



@router.delete("/api/projects/{project_id}", status_code=204)
def delete_project(project_id: str, current_user: User = Depends(require_admin), db: Session = Depends(get_db)):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project tidak ditemukan")
    # Cascade delete: workspace → sheets → columns → rows → cells → attachments
    ws_sheets = db.query(WorkspaceSheet).filter(WorkspaceSheet.project_id == project_id).all()
    for sheet in ws_sheets:
        row_ids = [r.id for r in db.query(WorkspaceRow.id).filter(WorkspaceRow.sheet_id == sheet.id).all()]
        col_ids = [c.id for c in db.query(WorkspaceColumn.id).filter(WorkspaceColumn.sheet_id == sheet.id).all()]
        if row_ids:
            db.query(WorkspaceAttachment).filter(WorkspaceAttachment.row_id.in_(row_ids)).delete(synchronize_session=False)
            db.query(WorkspaceCell).filter(WorkspaceCell.row_id.in_(row_ids)).delete(synchronize_session=False)
        if col_ids:
            db.query(WorkspaceCell).filter(WorkspaceCell.column_id.in_(col_ids)).delete(synchronize_session=False)
        db.query(WorkspaceRow).filter(WorkspaceRow.sheet_id == sheet.id).delete(synchronize_session=False)
        db.query(WorkspaceColumn).filter(WorkspaceColumn.sheet_id == sheet.id).delete(synchronize_session=False)
    db.query(WorkspaceSheet).filter(WorkspaceSheet.project_id == project_id).delete(synchronize_session=False)
    # Cascade delete: board → columns → cards → children
    board = db.query(Board).filter(Board.project_id == project_id).first()
    if board:
        col_ids = [c.id for c in db.query(BoardColumn.id).filter(BoardColumn.board_id == board.id).all()]
        if col_ids:
            card_ids = [c.id for c in db.query(BoardCard.id).filter(BoardCard.column_id.in_(col_ids)).all()]
            if card_ids:
                db.query(BoardCardActivity).filter(BoardCardActivity.card_id.in_(card_ids)).delete(synchronize_session=False)
                db.query(BoardCardChecklist).filter(BoardCardChecklist.card_id.in_(card_ids)).delete(synchronize_session=False)
                db.query(BoardCardComment).filter(BoardCardComment.card_id.in_(card_ids)).delete(synchronize_session=False)
            db.query(BoardCard).filter(BoardCard.column_id.in_(col_ids)).delete(synchronize_session=False)
        db.query(BoardColumn).filter(BoardColumn.board_id == board.id).delete(synchronize_session=False)
        db.delete(board)
    project_name = project.name
    db.delete(project)
    db.commit()
    log_audit(db, current_user.name, "DELETE", "projects", project_id, {"name": project_name})
    invalidate_workspace_list_cache()



@router.patch("/api/projects/{project_id}/archive")
def archive_project(
    project_id: str,
    is_archived: bool = Body(..., embed=True),
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project tidak ditemukan")
    project.is_archived = is_archived
    db.commit()
    invalidate_workspace_list_cache()
    return {"id": project_id, "is_archived": is_archived}



@router.patch("/api/projects/{project_id}/color")
def update_project_color(
    project_id: str,
    color: str = Body(..., embed=True),
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project tidak ditemukan")
    project.color = color
    db.commit()
    invalidate_workspace_list_cache()
    return {"id": project_id, "color": color}


# ---------------------------------------------------------------------------
# Board API (Trello-like)
# ---------------------------------------------------------------------------

def card_to_out(card: BoardCard, workspace_linked_ids: set = None) -> BoardCardOut:
    """Convert BoardCard to BoardCardOut with related data"""
    labels_list = []
    if card.labels:
        try:
            labels_list = json.loads(card.labels) if isinstance(card.labels, str) else card.labels
        except:
            labels_list = []

    lead_out = None
    if card.lead_id and card.lead:
        lead_out = LeadMin(id=card.lead.id, business_name=card.lead.business_name)

    return BoardCardOut(
        id=card.id,
        column_id=card.column_id,
        title=card.title,
        description=card.description,
        assignee=card.assignee,
        due_date=card.due_date,
        labels=labels_list,
        position=card.position,
        is_archived=card.is_archived,
        created_at=card.created_at,
        updated_at=card.updated_at,
        lead_id=card.lead_id,
        lead=lead_out,
        color=card.color or "gray",
        is_workspace_linked=bool(workspace_linked_ids and card.id in workspace_linked_ids),
        comments=[BoardCardCommentOut.model_validate(c) for c in card.comments] if hasattr(card, 'comments') else [],
        checklist=[BoardCardChecklistOut.model_validate(c) for c in card.checklist] if hasattr(card, 'checklist') else [],
        activity=[BoardCardActivityOut.model_validate(a) for a in card.activity] if hasattr(card, 'activity') else [],
    )



@router.get("/api/boards/overview")
def get_boards_overview(show_archived: bool = Query(False), current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Get overview of all boards across projects using batch queries."""
    if show_archived:
        projects = db.query(Project).filter(Project.is_archived == True).all()
    else:
        projects = db.query(Project).filter(Project.is_archived == False).all()

    if not projects:
        return []

    project_ids = [p.id for p in projects]
    lead_ids = [p.lead_id for p in projects if p.lead_id]

    # Batch 1: all leads
    leads = {l.id: l for l in db.query(Lead).filter(Lead.id.in_(lead_ids)).all()} if lead_ids else {}

    # Batch 2: all boards for these projects
    boards = {b.project_id: b for b in db.query(Board).filter(Board.project_id.in_(project_ids)).all()}
    board_ids = [b.id for b in boards.values()]

    # Batch 3: all columns for all boards
    all_columns = db.query(BoardColumn).filter(BoardColumn.board_id.in_(board_ids)).all()
    cols_by_board = defaultdict(list)
    for col in all_columns:
        cols_by_board[col.board_id].append(col)
    col_ids = [c.id for c in all_columns]

    # Batch 4: all cards (only non-archived)
    all_cards = db.query(BoardCard).filter(
        BoardCard.column_id.in_(col_ids),
        BoardCard.is_archived == False,
    ).all()

    # Group cards by column_id
    cards_by_col = defaultdict(list)
    for card in all_cards:
        cards_by_col[card.column_id].append(card)

    # Build result
    today = datetime.now(timezone.utc).date()
    result = []
    for p in projects:
        board = boards.get(p.id)
        if not board:
            continue
        columns = cols_by_board.get(board.id, [])
        cards_count = 0
        overdue_cards = []
        due_soon_cards = []
        for col in columns:
            cards = cards_by_col.get(col.id, [])
            cards_count += len(cards)
            for c in cards:
                if c.due_date:
                    try:
                        due = datetime.fromisoformat(c.due_date.replace('Z', '+00:00')).date()
                        if due < today:
                            overdue_cards.append(c.title)
                        elif due <= today + timedelta(days=3):
                            due_soon_cards.append(c.title)
                    except Exception:
                        pass
        result.append({
            "project_id": p.id,
            "project_name": p.name,
            "board_id": board.id,
            "cards_count": cards_count,
            "columns_count": len(columns),
            "client_name": leads.get(p.lead_id).business_name if p.lead_id and p.lead_id in leads else None,
            "overdue_cards": overdue_cards,
            "due_soon_cards": due_soon_cards,
            "color": p.color or "gray",
            "project_lead_id": p.lead_id,
            "is_archived": p.is_archived,
        })
    return result



@router.get("/api/projects/{project_id}/board", response_model=BoardOut)
def get_project_board(project_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Get board for a project"""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project tidak ditemukan")

    board = db.query(Board).filter(Board.project_id == project_id).first()
    if not board:
        # Create board if not exists
        board = Board(id=str(uuid.uuid4()), project_id=project_id)
        db.add(board)
        db.flush()
        # Create default columns
        default_columns = [("To Do", "gray"), ("In Progress", "slate"), ("Review", "neutral"), ("Done", "stone")]
        for i, (name, color) in enumerate(default_columns):
            col = BoardColumn(id=str(uuid.uuid4()), board_id=board.id, name=name, position=i, color=color)
            db.add(col)
        db.commit()
        db.refresh(board)

    columns = db.query(BoardColumn).filter(BoardColumn.board_id == board.id).order_by(BoardColumn.position).all()
    # Get workspace-linked card IDs for this project
    sheet_ids = [s.id for s in db.query(WorkspaceSheet.id).filter(WorkspaceSheet.project_id == project_id).all()]
    workspace_linked_ids = set()
    if sheet_ids:
        rows = db.query(WorkspaceRow.board_card_id).filter(WorkspaceRow.sheet_id.in_(sheet_ids), WorkspaceRow.board_card_id.isnot(None)).all()
        workspace_linked_ids = {r[0] for r in rows if r[0]}
    column_outs = []
    for col in columns:
        cards = db.query(BoardCard).filter(BoardCard.column_id == col.id, BoardCard.is_archived == False).order_by(BoardCard.position).all()
        card_outs = [card_to_out(c, workspace_linked_ids) for c in cards]
        column_outs.append(BoardColumnOut(
            id=col.id, board_id=col.board_id, name=col.name, position=col.position, color=col.color, cards=card_outs
        ))

    return BoardOut(id=board.id, project_id=board.project_id, created_at=board.created_at, color=board.color or "gray", columns=column_outs)



@router.post("/api/boards/{board_id}/columns", response_model=BoardColumnOut, status_code=201)
def create_board_column(board_id: str, body: BoardColumnIn, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Create a new column in board"""
    board = db.query(Board).filter(Board.id == board_id).first()
    if not board:
        raise HTTPException(status_code=404, detail="Board tidak ditemukan")
    max_pos = db.query(BoardColumn).filter(BoardColumn.board_id == board_id).count()
    col = BoardColumn(id=str(uuid.uuid4()), board_id=board_id, name=body.name, position=body.position if body.position is not None else max_pos, color=body.color or "gray")
    db.add(col)
    db.commit()
    db.refresh(col)
    return BoardColumnOut(id=col.id, board_id=col.board_id, name=col.name, position=col.position, color=col.color, cards=[])



@router.get("/api/workspace/service-types")
def get_workspace_service_types(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    categories = db.query(Category).filter(Category.is_active == True).all()
    cat_map = {c.name.lower(): c.name for c in categories}
    result = []
    type_to_label = {
        "web_dev": "Web Development",
        "seo_gmaps": "SEO & Google Maps",
        "sosmed": "Kelola Sosial Media",
        "maintenance": "Maintenance Website",
        "web_dev_bulanan": "Web Development (Bulanan)",
        "branding": "Desain Logo & Identitas Visual",
    }
    for key, tmpl in WORKSPACE_TEMPLATES.items():
        label = type_to_label.get(key, key)
        for cat in categories:
            if key == "web_dev" and "web" in cat.name.lower() and "bulanan" not in cat.name.lower():
                label = cat.name
            elif key == "seo_gmaps" and ("seo" in cat.name.lower() or "google" in cat.name.lower()):
                label = cat.name
            elif key == "sosmed" and ("sosial" in cat.name.lower() or "kelola" in cat.name.lower()):
                label = cat.name
            elif key == "maintenance" and "maintenance" in cat.name.lower():
                label = cat.name
            elif key == "branding" and ("logo" in cat.name.lower() or "desain" in cat.name.lower()):
                label = cat.name
        result.append({"value": key, "label": label, "default_months": tmpl.get("default_months", 1)})
    return result



@router.post("/api/workspace/init")
def init_workspace(body: WorkspaceInitIn, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    project = db.query(Project).filter(Project.id == body.project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project tidak ditemukan")

    existing = db.query(WorkspaceSheet).filter(WorkspaceSheet.project_id == body.project_id).first()
    if existing:
        return {"message": "Workspace sudah ada", "sheets": get_workspace_data(db, body.project_id)["sheets"]}

    if body.service_type not in WORKSPACE_TEMPLATES:
        raise HTTPException(status_code=400, detail=f"service_type tidak valid: {body.service_type}")

    project.service_type = body.service_type
    project.contract_months = body.contract_months

    if body.contract_days and body.contract_days < 30:
        sheet_defs = build_sheets_for_days(body.contract_days, body.service_type)
    else:
        sheet_defs = build_sheets_for_service(body.service_type, body.contract_months)
    now = datetime.now(timezone.utc).isoformat()

    for idx, sdef in enumerate(sheet_defs):
        sheet = WorkspaceSheet(
            id=str(uuid.uuid4()),
            project_id=body.project_id,
            sheet_index=idx,
            sheet_label=sdef["label"],
            service_type=body.service_type,
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
            sync_row_to_board(row.id, db)

    db.commit()
    return {"message": "Workspace initialized", "sheets": _get_workspace_data(body.project_id, db)["sheets"]}


def _get_workspace_data(project_id: str, db: Session) -> dict:
    sheets = db.query(WorkspaceSheet).filter(WorkspaceSheet.project_id == project_id).order_by(WorkspaceSheet.sheet_index).all()
    result = {"project_id": project_id, "service_type": None, "sheets": []}
    if sheets:
        result["service_type"] = sheets[0].service_type

    for sheet in sheets:
        cols = db.query(WorkspaceColumn).filter(WorkspaceColumn.sheet_id == sheet.id).order_by(WorkspaceColumn.column_order).all()
        rows = db.query(WorkspaceRow).filter(WorkspaceRow.sheet_id == sheet.id).order_by(WorkspaceRow.row_order).all()

        cols_data = [{"id": c.id, "column_key": c.column_key, "column_label": c.column_label, "column_type": c.column_type, "column_options": json.loads(c.column_options or "[]"), "column_order": c.column_order, "is_system": c.is_system} for c in cols]

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



@router.get("/api/workspace-list")
@cached(ttl_seconds=30, key_func=lambda r: "cache:/api/workspace-list")
def get_workspace_list(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return get_workspace_list_data(db)



@router.get("/api/workspace/{project_id}")
def get_workspace(project_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project tidak ditemukan")
    return get_workspace_data(db, project_id)



@router.patch("/api/workspace/cell/{row_id}/{column_id}")
def update_workspace_cell(row_id: str, column_id: str, body: WorkspaceCellUpdate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    row = db.query(WorkspaceRow).filter(WorkspaceRow.id == row_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Row tidak ditemukan")
    col = db.query(WorkspaceColumn).filter(WorkspaceColumn.id == column_id).first()
    if not col:
        raise HTTPException(status_code=404, detail="Column tidak ditemukan")

    cell = db.query(WorkspaceCell).filter(WorkspaceCell.row_id == row_id, WorkspaceCell.column_id == column_id).first()
    if not cell:
        cell = WorkspaceCell(id=str(uuid.uuid4()), row_id=row_id, column_id=column_id)
        db.add(cell)

    if body.value_text is not None:
        cell.value_text = body.value_text
    if body.value_bool is not None:
        cell.value_bool = body.value_bool
    if body.value_number is not None:
        cell.value_number = body.value_number
    if body.value_date is not None:
        cell.value_date = body.value_date
    if body.value_json is not None:
        cell.value_json = body.value_json
    cell.updated_at = datetime.now(timezone.utc).isoformat()
    row.updated_at = cell.updated_at
    db.commit()

    if col.column_key in ("status", "done"):
        sync_row_status_to_board(row_id, db)

        # Billing milestone detection
        new_val = body.value_text or ""
        is_done = new_val.lower() in ("done", "selesai") or body.value_bool is True
        if is_done:
            task_name_col = db.query(WorkspaceColumn).filter(
                WorkspaceColumn.sheet_id == col.sheet_id,
                WorkspaceColumn.column_key == "task_name",
            ).first()
            if task_name_col:
                task_cell = db.query(WorkspaceCell).filter(
                    WorkspaceCell.row_id == row_id,
                    WorkspaceCell.column_id == task_name_col.id,
                ).first()
                task_name = task_cell.value_text if task_cell else ""
                m = re.search(r"Invoice\s+pembayaran\s+(\d+)%", task_name or "", re.IGNORECASE)
                if m:
                    percent = int(m.group(1))
                    sheet = db.query(WorkspaceSheet).filter(WorkspaceSheet.id == col.sheet_id).first()
                    project = db.query(Project).filter(Project.id == sheet.project_id).first() if sheet else None
                    lead = db.query(Lead).filter(Lead.id == project.lead_id).first() if project and project.lead_id else None
                    amount = (project.nominal or 0) * percent / 100 if project else 0
                    invoice_template = db.query(DocumentTemplate).filter(DocumentTemplate.type == "invoice", DocumentTemplate.is_active == True).first()
                    return {
                        "id": cell.id, "value_text": cell.value_text, "value_bool": cell.value_bool,
                        "value_number": cell.value_number, "value_date": cell.value_date,
                        "billing_milestone_triggered": True,
                        "milestone_data": {
                            "percent": percent,
                            "amount": amount,
                            "amount_formatted": f"Rp {amount:,.0f}",
                            "task_name": task_name,
                            "project_name": project.name if project else "",
                            "client_name": lead.business_name if lead else "",
                            "lead_id": lead.id if lead else None,
                            "project_id": project.id if project else None,
                            "template_id": invoice_template.id if invoice_template else None,
                        },
                    }
    elif col.column_key == "task_name" and row.board_card_id:
        card = db.query(BoardCard).filter(BoardCard.id == row.board_card_id).first()
        if card:
            card.title = cell.value_text or f"Task {row.row_order}"
            db.commit()

    # G6: Auto-complete project when all tasks done
    if col.column_key == "done" and body.value_bool is True:
        sheet = db.query(WorkspaceSheet).filter(WorkspaceSheet.id == col.sheet_id).first()
        if sheet:
            all_sheets = db.query(WorkspaceSheet).filter(WorkspaceSheet.project_id == sheet.project_id).all()
            all_done = True
            for s in all_sheets:
                done_col = db.query(WorkspaceColumn).filter(WorkspaceColumn.sheet_id == s.id, WorkspaceColumn.column_key == "done").first()
                if not done_col:
                    continue
                total_rows = db.query(WorkspaceRow).filter(WorkspaceRow.sheet_id == s.id).count()
                done_count = db.query(WorkspaceCell).join(WorkspaceRow).filter(
                    WorkspaceRow.sheet_id == s.id,
                    WorkspaceCell.column_id == done_col.id,
                    WorkspaceCell.value_bool == True,
                ).count()
                if total_rows > 0 and done_count < total_rows:
                    all_done = False
                    break
            if all_done:
                project = db.query(Project).filter(Project.id == sheet.project_id).first()
                if project and project.status == "ACTIVE":
                    project.status = "COMPLETED"
                    db.commit()

    return {"id": cell.id, "value_text": cell.value_text, "value_bool": cell.value_bool, "value_number": cell.value_number, "value_date": cell.value_date}



@router.post("/api/workspace/sheet/{sheet_id}/row")
def add_workspace_row(sheet_id: str, body: WorkspaceRowIn, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    sheet = db.query(WorkspaceSheet).filter(WorkspaceSheet.id == sheet_id).first()
    if not sheet:
        raise HTTPException(status_code=404, detail="Sheet tidak ditemukan")

    max_order = db.query(func.max(WorkspaceRow.row_order)).filter(WorkspaceRow.sheet_id == sheet_id).scalar() or 0
    row = WorkspaceRow(
        id=str(uuid.uuid4()),
        sheet_id=sheet_id,
        row_order=body.row_order if body.row_order is not None else max_order + 1,
        is_template=False,
        created_at=datetime.now(timezone.utc).isoformat(),
    )
    db.add(row)
    db.flush()

    cols = db.query(WorkspaceColumn).filter(WorkspaceColumn.sheet_id == sheet_id).all()
    col_by_key = {c.column_key: c for c in cols}
    for key, val in body.cells.items():
        col = col_by_key.get(key)
        if not col:
            continue
        cell = WorkspaceCell(id=str(uuid.uuid4()), row_id=row.id, column_id=col.id, updated_at=row.created_at)
        if col.column_type == "checkbox":
            cell.value_bool = bool(val)
        elif col.column_type == "number":
            try:
                cell.value_number = float(val)
            except (ValueError, TypeError):
                cell.value_text = str(val)
        else:
            cell.value_text = str(val) if val else None
        db.add(cell)

    db.commit()
    sync_row_to_board(row.id, db)

    cells = db.query(WorkspaceCell).filter(WorkspaceCell.row_id == row.id).all()
    cells_map = {c.column_id: {"id": c.id, "value_text": c.value_text, "value_bool": c.value_bool, "value_number": c.value_number, "value_date": c.value_date} for c in cells}
    return {"id": row.id, "row_order": row.row_order, "board_card_id": row.board_card_id, "is_template": row.is_template, "cells": cells_map}



@router.delete("/api/workspace/row/{row_id}", status_code=204)
def delete_workspace_row(row_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    row = db.query(WorkspaceRow).filter(WorkspaceRow.id == row_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Row tidak ditemukan")
    if row.is_template:
        raise HTTPException(status_code=400, detail="Row template tidak dapat dihapus")
    if row.board_card_id:
        card = db.query(BoardCard).filter(BoardCard.id == row.board_card_id).first()
        if card:
            db.delete(card)
    db.query(WorkspaceCell).filter(WorkspaceCell.row_id == row_id).delete()
    db.query(WorkspaceAttachment).filter(WorkspaceAttachment.row_id == row_id).delete()
    db.delete(row)
    db.commit()



@router.post("/api/workspace/{project_id}/sheets")
def add_workspace_sheet(project_id: str, body: dict, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project tidak ditemukan")
    label = (body.get("label") or "").strip()
    if not label:
        raise HTTPException(status_code=400, detail="Nama sheet wajib diisi")
    max_idx = db.query(WorkspaceSheet).filter(WorkspaceSheet.project_id == project_id).count()
    svc = project.service_type or "general"
    now = datetime.now(timezone.utc).isoformat()
    sheet = WorkspaceSheet(
        id=str(uuid.uuid4()),
        project_id=project_id,
        sheet_index=max_idx,
        sheet_label=label,
        service_type=svc,
        month_number=None,
        created_at=now,
    )
    db.add(sheet)
    db.flush()
    from workspace_templates import _BASE_COLS
    for ci, cdef in enumerate(_BASE_COLS):
        col = WorkspaceColumn(
            id=str(uuid.uuid4()), sheet_id=sheet.id,
            column_key=cdef["key"], column_label=cdef["label"],
            column_type=cdef["type"], column_options=json.dumps(cdef.get("options", [])),
            column_order=ci, is_system=cdef.get("is_system", False), created_at=now,
        )
        db.add(col)
    db.commit()
    return {"id": sheet.id, "sheet_label": label, "sheet_index": max_idx}



@router.delete("/api/workspace/sheet/{sheet_id}", status_code=204)
def delete_workspace_sheet(sheet_id: str, current_user: User = Depends(require_admin), db: Session = Depends(get_db)):
    sheet = db.query(WorkspaceSheet).filter(WorkspaceSheet.id == sheet_id).first()
    if not sheet:
        raise HTTPException(status_code=404, detail="Sheet tidak ditemukan")
    # Block deletion of auto-generated sheets (have month_number tied to contract)
    if sheet.month_number is not None:
        raise HTTPException(status_code=400, detail="Sheet auto-generated tidak bisa dihapus")
    # Cascade: rows → cells → attachments → linked board cards
    rows = db.query(WorkspaceRow).filter(WorkspaceRow.sheet_id == sheet_id).all()
    row_ids = [r.id for r in rows]
    card_ids = [r.board_card_id for r in rows if r.board_card_id]
    if row_ids:
        db.query(WorkspaceCell).filter(WorkspaceCell.row_id.in_(row_ids)).delete(synchronize_session=False)
        db.query(WorkspaceAttachment).filter(WorkspaceAttachment.row_id.in_(row_ids)).delete(synchronize_session=False)
        db.query(WorkspaceRow).filter(WorkspaceRow.sheet_id == sheet_id).delete(synchronize_session=False)
    if card_ids:
        db.query(BoardCard).filter(BoardCard.id.in_(card_ids)).delete(synchronize_session=False)
    db.query(WorkspaceColumn).filter(WorkspaceColumn.sheet_id == sheet_id).delete(synchronize_session=False)
    db.delete(sheet)
    db.commit()



@router.post("/api/workspace/sheet/{sheet_id}/column")
def add_workspace_column(sheet_id: str, body: WorkspaceColumnIn, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    sheet = db.query(WorkspaceSheet).filter(WorkspaceSheet.id == sheet_id).first()
    if not sheet:
        raise HTTPException(status_code=404, detail="Sheet tidak ditemukan")
    existing = db.query(WorkspaceColumn).filter(WorkspaceColumn.sheet_id == sheet_id, WorkspaceColumn.column_key == body.column_key).first()
    if existing:
        raise HTTPException(status_code=400, detail=f"column_key '{body.column_key}' sudah ada")

    max_order = db.query(func.max(WorkspaceColumn.column_order)).filter(WorkspaceColumn.sheet_id == sheet_id).scalar() or 0
    col = WorkspaceColumn(
        id=str(uuid.uuid4()),
        sheet_id=sheet_id,
        column_key=body.column_key,
        column_label=body.column_label,
        column_type=body.column_type,
        column_options=json.dumps(body.column_options or []),
        column_order=body.column_order if body.column_order is not None else max_order + 1,
        is_system=False,
        created_at=datetime.now(timezone.utc).isoformat(),
    )
    db.add(col)
    db.flush()

    rows = db.query(WorkspaceRow).filter(WorkspaceRow.sheet_id == sheet_id).all()
    for row in rows:
        db.add(WorkspaceCell(id=str(uuid.uuid4()), row_id=row.id, column_id=col.id))
    db.commit()

    return {"id": col.id, "column_key": col.column_key, "column_label": col.column_label, "column_type": col.column_type, "column_order": col.column_order}



@router.delete("/api/workspace/column/{column_id}", status_code=204)
def delete_workspace_column(column_id: str, current_user: User = Depends(require_admin), db: Session = Depends(get_db)):
    col = db.query(WorkspaceColumn).filter(WorkspaceColumn.id == column_id).first()
    if not col:
        raise HTTPException(status_code=404, detail="Column tidak ditemukan")
    if col.is_system:
        raise HTTPException(status_code=400, detail="Kolom sistem tidak dapat dihapus")
    db.query(WorkspaceCell).filter(WorkspaceCell.column_id == column_id).delete()
    db.query(WorkspaceAttachment).filter(WorkspaceAttachment.column_id == column_id).delete()
    db.delete(col)
    db.commit()



@router.patch("/api/workspace/sheet/{sheet_id}/reorder-rows")
def reorder_workspace_rows(sheet_id: str, body: dict, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    row_ids = body.get("row_ids", [])
    for i, rid in enumerate(row_ids):
        row = db.query(WorkspaceRow).filter(WorkspaceRow.id == rid, WorkspaceRow.sheet_id == sheet_id).first()
        if row:
            row.row_order = i
    db.commit()
    return {"success": True}



@router.post("/api/workspace/row/{row_id}/attachment")
async def upload_workspace_attachment(
    row_id: str,
    column_id: str = Form(...),
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    row = db.query(WorkspaceRow).filter(WorkspaceRow.id == row_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Row tidak ditemukan")
    sheet = db.query(WorkspaceSheet).filter(WorkspaceSheet.id == row.sheet_id).first()

    allowed_ext = {".jpg", ".jpeg", ".png", ".pdf", ".webp"}
    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in allowed_ext:
        raise HTTPException(status_code=400, detail=f"Format tidak diizinkan: {ext}. Gunakan: jpg, png, pdf, webp")

    contents = await file.read()
    if len(contents) > 5 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File terlalu besar (max 5MB)")

    ws_dir = os.path.join(UPLOADS_DIR, "workspace", sheet.project_id, row_id)
    os.makedirs(ws_dir, exist_ok=True)
    ext = os.path.splitext(file.filename or "")[1].lower()
    fname = f"{uuid.uuid4().hex}{ext}"
    fpath = os.path.join(ws_dir, fname)
    with open(fpath, "wb") as f:
        f.write(contents)

    file_url = f"/uploads/workspace/{sheet.project_id}/{row_id}/{fname}"
    att = WorkspaceAttachment(
        id=str(uuid.uuid4()),
        row_id=row_id,
        column_id=column_id,
        file_path=file_url,
        file_name=file.filename or fname,
        file_type=file.content_type,
    )
    db.add(att)

    cell = db.query(WorkspaceCell).filter(WorkspaceCell.row_id == row_id, WorkspaceCell.column_id == column_id).first()
    if cell:
        cell.value_text = file_url
    else:
        db.add(WorkspaceCell(id=str(uuid.uuid4()), row_id=row_id, column_id=column_id, value_text=file_url))
    db.commit()

    return {"id": att.id, "file_url": file_url, "file_name": att.file_name}



@router.get("/api/workspace/{project_id}/report-data")
def get_workspace_report_data(project_id: str, month: int = 1, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project tidak ditemukan")
    lead = db.query(Lead).filter(Lead.id == project.lead_id).first() if project.lead_id else None

    sheet = db.query(WorkspaceSheet).filter(WorkspaceSheet.project_id == project_id, WorkspaceSheet.month_number == month).first()
    if not sheet:
        raise HTTPException(status_code=404, detail=f"Sheet bulan {month} tidak ditemukan")

    rows = db.query(WorkspaceRow).filter(WorkspaceRow.sheet_id == sheet.id).order_by(WorkspaceRow.row_order).all()
    cols = db.query(WorkspaceColumn).filter(WorkspaceColumn.sheet_id == sheet.id).all()
    col_by_id = {c.id: c for c in cols}

    tasks = []
    screenshots = []
    total_tasks = len(rows)
    completed = 0

    for row in rows:
        cells = db.query(WorkspaceCell).filter(WorkspaceCell.row_id == row.id).all()
        task = {}
        for cell in cells:
            col = col_by_id.get(cell.column_id)
            if not col:
                continue
            if col.column_type == "checkbox":
                task[col.column_key] = cell.value_bool
            elif col.column_type == "number":
                task[col.column_key] = cell.value_number
            else:
                task[col.column_key] = cell.value_text
        if task.get("done"):
            completed += 1
        tasks.append(task)
        if task.get("screenshot"):
            screenshots.append({"task_name": task.get("task_name", ""), "url": task["screenshot"]})

    by_status: dict[str, int] = {}
    for t in tasks:
        s = t.get("status", "To Do") or "To Do"
        by_status[s] = by_status.get(s, 0) + 1

    artikel_tracker = []
    if project.service_type == "seo_gmaps":
        art_sheet = db.query(WorkspaceSheet).filter(WorkspaceSheet.project_id == project_id, WorkspaceSheet.sheet_label == "Artikel Tracker").first()
        if art_sheet:
            art_rows = db.query(WorkspaceRow).filter(WorkspaceRow.sheet_id == art_sheet.id).all()
            art_cols = {c.id: c for c in db.query(WorkspaceColumn).filter(WorkspaceColumn.sheet_id == art_sheet.id).all()}
            for ar in art_rows:
                art_cells = db.query(WorkspaceCell).filter(WorkspaceCell.row_id == ar.id).all()
                art_task = {}
                for ac in art_cells:
                    acol = art_cols.get(ac.column_id)
                    if acol:
                        art_task[acol.column_key] = ac.value_text or ac.value_number
                artikel_tracker.append(art_task)

    return {
        "project": {"name": project.name, "service_type": project.service_type, "start_date": project.start_date, "end_date": project.end_date},
        "contact": {"name": lead.business_name if lead else None, "phone": lead.phone_number if lead else None},
        "month_number": month,
        "sheet_label": sheet.sheet_label,
        "summary": {"total_tasks": total_tasks, "completed_tasks": completed, "completion_pct": round(completed / total_tasks * 100, 1) if total_tasks else 0, "by_status": by_status},
        "tasks": tasks,
        "screenshots": screenshots,
        "artikel_tracker": artikel_tracker,
    }


# ---------------------------------------------------------------------------
# Monthly Report Generator (per service type)
# ---------------------------------------------------------------------------

_REPORT_BASE_CSS = """
@page { size: A4; margin: 1.5cm; }
body { font-family: 'Noto Sans', Arial, Helvetica, sans-serif; color: #1f2937; line-height: 1.5; }
* { font-family: 'Noto Sans', Arial, Helvetica, sans-serif; }
.header { border-bottom: 3px solid #f59e0b; padding-bottom: 12px; margin-bottom: 20px; }
.header .brand { font-size: 11px; color: #6b7280; text-transform: uppercase; letter-spacing: 1.5px; }
.header h1 { margin: 4px 0 2px; font-size: 22px; color: #111827; }
.header .meta { font-size: 11px; color: #6b7280; }
.section { margin: 18px 0; }
.section h2 { font-size: 13px; color: #f59e0b; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 8px; padding-bottom: 4px; border-bottom: 1px solid #e5e7eb; }
.kpi-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px; margin: 12px 0; }
.kpi { background: #fef3c7; padding: 10px 12px; border-radius: 8px; }
.kpi .label { font-size: 9px; color: #92400e; text-transform: uppercase; letter-spacing: 1px; font-weight: 600; }
.kpi .value { font-size: 20px; color: #78350f; font-weight: bold; margin-top: 2px; }
table { width: 100%; border-collapse: collapse; font-size: 11px; margin-top: 6px; }
th { background: #f3f4f6; padding: 7px 8px; text-align: left; font-size: 10px; text-transform: uppercase; color: #4b5563; letter-spacing: 0.5px; }
td { padding: 6px 8px; border-bottom: 1px solid #f3f4f6; vertical-align: top; }
.badge { display: inline-block; padding: 2px 8px; border-radius: 10px; font-size: 9px; font-weight: 600; }
.badge-done { background: #d1fae5; color: #065f46; }
.badge-progress { background: #fef3c7; color: #92400e; }
.badge-todo { background: #e5e7eb; color: #374151; }
.screenshot-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 8px; margin-top: 8px; }
.screenshot-grid .item { font-size: 10px; }
.screenshot-grid img { width: 100%; border: 1px solid #e5e7eb; border-radius: 4px; }
.footer { margin-top: 30px; padding-top: 12px; border-top: 1px solid #e5e7eb; font-size: 10px; color: #9ca3af; text-align: center; }
"""

def _badge_for_task(task: dict) -> str:
    if task.get("done"):
        return '<span class="badge badge-done">Selesai</span>'
    s = (task.get("status") or "").lower()
    if "progress" in s or "doing" in s or "review" in s:
        return '<span class="badge badge-progress">Berjalan</span>'
    return '<span class="badge badge-todo">Belum</span>'


def _render_monthly_report_html(data: dict, brand: dict) -> str:
    project = data["project"]
    contact = data["contact"]
    summary = data["summary"]
    tasks = data["tasks"]
    screenshots = data["screenshots"]
    artikel_tracker = data.get("artikel_tracker", [])
    service_type = project.get("service_type") or "general"
    month = data["month_number"]

    brand_name = brand.get("brand_name") or "Teman UMKM Kita"

    service_label_map = {
        "seo_gmaps": "Laporan Bulanan SEO & Google Maps",
        "maintenance": "Laporan Bulanan Maintenance Website",
        "sosmed": "Laporan Bulanan Kelola Sosial Media",
        "web_dev": "Laporan Progres Web Development",
        "web_dev_bulanan": "Laporan Bulanan Web Development",
        "branding": "Laporan Branding & Identitas Visual",
    }
    title = service_label_map.get(service_type, "Laporan Bulanan Layanan")

    html_parts = [f"""<!DOCTYPE html><html><head><meta charset="utf-8"><style>{_REPORT_BASE_CSS}</style></head><body>
<div class="header">
  <div class="brand">{brand_name}</div>
  <h1>{title}</h1>
  <div class="meta">Klien: <b>{contact.get('name') or '—'}</b> &middot; Proyek: {project.get('name') or '—'} &middot; Bulan ke-{month}</div>
</div>

<div class="section">
  <h2>Ringkasan Bulan Ini</h2>
  <div class="kpi-grid">
    <div class="kpi"><div class="label">Total Tugas</div><div class="value">{summary['total_tasks']}</div></div>
    <div class="kpi"><div class="label">Selesai</div><div class="value">{summary['completed_tasks']}</div></div>
    <div class="kpi"><div class="label">Progress</div><div class="value">{summary['completion_pct']}%</div></div>
  </div>
</div>
"""]

    # Service-specific sections
    if service_type == "seo_gmaps":
        html_parts.append("""<div class="section"><h2>Aktivitas SEO &amp; Google Maps</h2><table>
<thead><tr><th>Aktivitas</th><th>Status</th><th>Catatan</th></tr></thead><tbody>""")
        for t in tasks:
            html_parts.append(f"<tr><td>{t.get('task_name','—')}</td><td>{_badge_for_task(t)}</td><td>{t.get('catatan','') or t.get('notes','') or ''}</td></tr>")
        html_parts.append("</tbody></table></div>")

        if artikel_tracker:
            html_parts.append("""<div class="section"><h2>Artikel yang Dipublikasi</h2><table>
<thead><tr><th>Judul</th><th>Keyword</th><th>URL</th><th>Status</th></tr></thead><tbody>""")
            for a in artikel_tracker:
                html_parts.append(f"<tr><td>{a.get('judul','—')}</td><td>{a.get('keyword','—')}</td><td>{a.get('url','—')}</td><td>{a.get('status','—')}</td></tr>")
            html_parts.append("</tbody></table></div>")

    elif service_type == "maintenance":
        html_parts.append("""<div class="section"><h2>Aktivitas Maintenance</h2><table>
<thead><tr><th>Tugas</th><th>Status</th><th>Catatan / Resolusi</th></tr></thead><tbody>""")
        for t in tasks:
            html_parts.append(f"<tr><td>{t.get('task_name','—')}</td><td>{_badge_for_task(t)}</td><td>{t.get('catatan','') or t.get('notes','') or ''}</td></tr>")
        html_parts.append("</tbody></table></div>")

    elif service_type == "sosmed":
        html_parts.append("""<div class="section"><h2>Konten &amp; Posting Sosial Media</h2><table>
<thead><tr><th>Tanggal</th><th>Konten / Tugas</th><th>Platform</th><th>Status</th></tr></thead><tbody>""")
        for t in tasks:
            html_parts.append(f"<tr><td>{t.get('tanggal','') or t.get('value_date','')}</td><td>{t.get('task_name','—')}</td><td>{t.get('platform','—')}</td><td>{_badge_for_task(t)}</td></tr>")
        html_parts.append("</tbody></table></div>")

    elif service_type in ("web_dev", "web_dev_bulanan"):
        html_parts.append("""<div class="section"><h2>Milestone &amp; Deliverables</h2><table>
<thead><tr><th>Milestone / Tugas</th><th>Status</th><th>Catatan</th></tr></thead><tbody>""")
        for t in tasks:
            html_parts.append(f"<tr><td>{t.get('task_name','—')}</td><td>{_badge_for_task(t)}</td><td>{t.get('catatan','') or t.get('notes','') or ''}</td></tr>")
        html_parts.append("</tbody></table></div>")

    elif service_type == "branding":
        html_parts.append("""<div class="section"><h2>Deliverables Branding</h2><table>
<thead><tr><th>Deliverable</th><th>Status</th><th>Catatan</th></tr></thead><tbody>""")
        for t in tasks:
            html_parts.append(f"<tr><td>{t.get('task_name','—')}</td><td>{_badge_for_task(t)}</td><td>{t.get('catatan','') or t.get('notes','') or ''}</td></tr>")
        html_parts.append("</tbody></table></div>")

    else:  # general / fallback
        html_parts.append("""<div class="section"><h2>Aktivitas Bulan Ini</h2><table>
<thead><tr><th>Tugas</th><th>Status</th><th>Catatan</th></tr></thead><tbody>""")
        for t in tasks:
            html_parts.append(f"<tr><td>{t.get('task_name','—')}</td><td>{_badge_for_task(t)}</td><td>{t.get('catatan','') or t.get('notes','') or ''}</td></tr>")
        html_parts.append("</tbody></table></div>")

    if screenshots:
        html_parts.append('<div class="section"><h2>Bukti Pengerjaan</h2><div class="screenshot-grid">')
        for s in screenshots[:8]:
            url = s.get("url", "")
            if url and not url.startswith("http"):
                base = _get_setting("app_base_url", "") or os.getenv("APP_BASE_URL", "")
                url = f"{base.rstrip('/')}{url}" if base else url
            html_parts.append(f'<div class="item"><img src="{url}" alt="" /><div>{s.get("task_name","")}</div></div>')
        html_parts.append("</div></div>")

    today_str = datetime.now(timezone.utc).strftime("%d %B %Y")
    html_parts.append(f'<div class="footer">Dibuat {today_str} oleh {brand_name}</div></body></html>')
    return "".join(html_parts)



@router.post("/api/workspace/{project_id}/generate-monthly-report")
def generate_monthly_report(
    project_id: str,
    month: int = 1,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project tidak ditemukan")
    lead = db.query(Lead).filter(Lead.id == project.lead_id).first() if project.lead_id else None

    sheet = db.query(WorkspaceSheet).filter(WorkspaceSheet.project_id == project_id, WorkspaceSheet.month_number == month).first()
    if not sheet:
        raise HTTPException(status_code=404, detail=f"Sheet bulan {month} tidak ditemukan")

    rows = db.query(WorkspaceRow).filter(WorkspaceRow.sheet_id == sheet.id).order_by(WorkspaceRow.row_order).all()
    cols = db.query(WorkspaceColumn).filter(WorkspaceColumn.sheet_id == sheet.id).all()
    col_by_id = {c.id: c for c in cols}

    tasks = []
    screenshots = []
    completed = 0
    for row in rows:
        cells = db.query(WorkspaceCell).filter(WorkspaceCell.row_id == row.id).all()
        task = {}
        for cell in cells:
            col = col_by_id.get(cell.column_id)
            if not col:
                continue
            if col.column_type == "checkbox":
                task[col.column_key] = cell.value_bool
            elif col.column_type == "number":
                task[col.column_key] = cell.value_number
            else:
                task[col.column_key] = cell.value_text
        if task.get("done"):
            completed += 1
        tasks.append(task)
        if task.get("screenshot"):
            screenshots.append({"task_name": task.get("task_name", ""), "url": task["screenshot"]})

    by_status: dict[str, int] = {}
    for t in tasks:
        s = t.get("status", "To Do") or "To Do"
        by_status[s] = by_status.get(s, 0) + 1

    artikel_tracker = []
    if project.service_type == "seo_gmaps":
        art_sheet = db.query(WorkspaceSheet).filter(WorkspaceSheet.project_id == project_id, WorkspaceSheet.sheet_label == "Artikel Tracker").first()
        if art_sheet:
            art_rows = db.query(WorkspaceRow).filter(WorkspaceRow.sheet_id == art_sheet.id).all()
            art_cols = {c.id: c for c in db.query(WorkspaceColumn).filter(WorkspaceColumn.sheet_id == art_sheet.id).all()}
            for ar in art_rows:
                art_cells = db.query(WorkspaceCell).filter(WorkspaceCell.row_id == ar.id).all()
                art_task = {}
                for ac in art_cells:
                    acol = art_cols.get(ac.column_id)
                    if acol:
                        art_task[acol.column_key] = ac.value_text or ac.value_number
                artikel_tracker.append(art_task)

    total_tasks = len(rows)
    data = {
        "project": {"name": project.name, "service_type": project.service_type, "start_date": project.start_date, "end_date": project.end_date},
        "contact": {"name": lead.business_name if lead else None, "phone": lead.phone_number if lead else None},
        "month_number": month,
        "sheet_label": sheet.sheet_label,
        "summary": {"total_tasks": total_tasks, "completed_tasks": completed, "completion_pct": round(completed / total_tasks * 100, 1) if total_tasks else 0, "by_status": by_status},
        "tasks": tasks,
        "screenshots": screenshots,
        "artikel_tracker": artikel_tracker,
    }

    brand = _build_brand_context(db)
    rendered_html = _render_monthly_report_html(data, brand)

    file_id = str(uuid.uuid4())
    pdf_filename = f"{file_id}.pdf"
    pdf_path = os.path.join(DOCUMENTS_DIR, pdf_filename)

    try:
        from weasyprint import HTML
        HTML(string=rendered_html, url_fetcher=_pdf_url_fetcher).write_pdf(pdf_path)
    except ImportError:
        raise HTTPException(status_code=500, detail="WeasyPrint tidak terinstall. Jalankan: pip install weasyprint")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"PDF generation gagal: {e}")

    file_url = f"/uploads/documents/{pdf_filename}"
    safe_client = _slugify_name(lead.business_name if lead else "klien")
    display_name = f"LAPORAN_{(project.service_type or 'umum').upper()}_{safe_client}_M{month:02d}"

    doc = GeneratedDocument(
        id=file_id,
        template_id=None,
        template_name=f"Laporan Bulanan — {project.service_type or 'umum'}",
        target_type="project",
        target_id=project_id,
        variables_used=json.dumps({"month": month, "service_type": project.service_type}),
        file_url=file_url,
        display_filename=display_name,
        generated_by=current_user.name,
    )
    db.add(doc)
    db.commit()

    return {"document_id": doc.id, "file_url": file_url, "display_filename": display_name, "summary": data["summary"]}

