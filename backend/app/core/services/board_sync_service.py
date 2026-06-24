"""
Board sync — syncs workspace rows to kanban board cards.
"""
import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session

from models import (
    Board, BoardColumn, BoardCard,
    WorkspaceRow, WorkspaceCell, WorkspaceColumn,
    WorkspaceSheet, Project, Lead,
)


_ROW_STATUS_MAP = {"Done": "✅ Selesai", "On Track": "✅ On Track", "In Progress": "🔄 In Progress", "Pending": "⏳ Pending"}
_TITLE_KEYS = ("task_name", "task", "title", "name")
_DUE_DATE_KEYS = ("due_date", "deadline", "tanggal", "date")


def _first_present(data: dict, keys: tuple[str, ...]):
    for key in keys:
        value = data.get(key)
        if value not in (None, ""):
            return value
    return None


def _ensure_board(project: Project, db: Session) -> Optional[Board]:
    board = db.query(Board).filter(Board.project_id == project.id).first()
    if board:
        return board
    board = Board(id=str(uuid.uuid4()), project_id=project.id, color=getattr(project, "color", None) or "gray")
    db.add(board)
    db.flush()
    for idx, (name, color) in enumerate((("To Do", "gray"), ("In Progress", "slate"), ("Review", "neutral"), ("Done", "stone"))):
        db.add(BoardColumn(id=str(uuid.uuid4()), board_id=board.id, name=name, position=idx, color=color))
    db.flush()
    return board


def _valid_lead_id(lead_id: Optional[int], db: Session) -> Optional[int]:
    if not lead_id:
        return None
    return lead_id if db.query(Lead.id).filter(Lead.id == lead_id).first() else None


def _default_board_column(board: Board, db: Session, data: dict) -> Optional[BoardColumn]:
    columns = db.query(BoardColumn).filter(BoardColumn.board_id == board.id).order_by(BoardColumn.position).all()
    if not columns:
        col = BoardColumn(id=str(uuid.uuid4()), board_id=board.id, name="To Do", position=0, color="gray")
        db.add(col)
        db.flush()
        return col
    status = str(data.get("status") or "").strip().lower()
    done = data.get("done") is True
    for col in columns:
        name = col.name.lower()
        if done and "done" in name:
            return col
        if status and (name in status or status in name):
            return col
    return columns[0]


def sync_row_to_board(row_id: str, db: Session):
    row = db.query(WorkspaceRow).filter(WorkspaceRow.id == row_id).first()
    if not row:
        return
    sheet = db.query(WorkspaceSheet).filter(WorkspaceSheet.id == row.sheet_id).first()
    if not sheet or not sheet.project_id:
        return
    project = db.query(Project).filter(Project.id == sheet.project_id).first()
    if not project:
        return
    cells = db.query(WorkspaceCell).filter(WorkspaceCell.row_id == row_id).all()
    col_ids = {c.column_id for c in cells}
    cols = db.query(WorkspaceColumn).filter(WorkspaceColumn.id.in_(col_ids)).all() if col_ids else []
    col_by_id = {c.id: c for c in cols}
    data = {}
    for cell in cells:
        col = col_by_id.get(cell.column_id)
        if not col or not col.column_key:
            continue
        key = col.column_key
        if col.column_type == "checkbox":
            data[key] = cell.value_bool
        elif col.column_type == "number":
            data[key] = cell.value_number
        elif col.column_type == "date":
            data[key] = cell.value_date
        else:
            data[key] = cell.value_text
    board = _ensure_board(project, db)
    if not board:
        return
    card = None
    if row.board_card_id:
        card = db.query(BoardCard).filter(BoardCard.id == row.board_card_id).first()
    if not card:
        default_col = _default_board_column(board, db, data)
        if not default_col:
            return
        due_date = _first_present(data, _DUE_DATE_KEYS)
        card = BoardCard(
            id=str(uuid.uuid4()),
            column_id=default_col.id,
            title=str(_first_present(data, _TITLE_KEYS) or "Untitled Task"),
            due_date=str(due_date) if due_date else None,
            position=db.query(BoardCard).filter(BoardCard.column_id == default_col.id, BoardCard.is_archived == False).count(),
            lead_id=_valid_lead_id(project.lead_id, db),
            color=getattr(project, "color", None) or "gray",
        )
        db.add(card)
        db.flush()
        row.board_card_id = card.id
    _sync_one_card(card, data, db)


def _sync_one_card(card, data: dict, db: Session):
    title_overrides = _ROW_STATUS_MAP
    new_title = _first_present(data, _TITLE_KEYS)
    new_due = _first_present(data, _DUE_DATE_KEYS)
    current_col = db.query(BoardColumn).filter(BoardColumn.id == card.column_id).first()
    if not current_col:
        return
    board = db.query(Board).filter(Board.id == current_col.board_id).first()
    if not board:
        return
    board_cols = db.query(BoardColumn).filter(BoardColumn.board_id == board.id).order_by(BoardColumn.position).all()
    col_map = {c.name.lower(): c for c in board_cols}
    done_value = data.get("done")
    matched_status_col = None
    for key, val in data.items():
        keyl = key.lower()
        if keyl == "status" and val:
            status_val = str(val).strip()
            for col_name, col_obj in col_map.items():
                if col_name in status_val.lower() or status_val.lower() in col_name:
                    matched_status_col = col_obj
                    card.column_id = col_obj.id
                    break
            mapped = title_overrides.get(status_val)
            if mapped and not new_title:
                new_title = mapped
        elif keyl == "done" and val is True:
            done_col = next((col for name, col in col_map.items() if "done" in name), None)
            if done_col:
                card.column_id = done_col.id
                card.is_archived = False
        elif keyl == "done" and val is False:
            done_col = next((col for name, col in col_map.items() if "done" in name), None)
            if done_col and card.column_id == done_col.id:
                fallback_col = matched_status_col or next((col for col in board_cols if "done" not in (col.name or "").lower()), None)
                if fallback_col:
                    card.column_id = fallback_col.id
                    card.is_archived = False
    if new_title:
        card.title = str(new_title)
    if new_due:
        card.due_date = str(new_due)
    card.updated_at = datetime.now(timezone.utc).isoformat()
    db.commit()


def sync_row_status_to_board(row_id: str, db: Session):
    return sync_row_to_board(row_id, db)
