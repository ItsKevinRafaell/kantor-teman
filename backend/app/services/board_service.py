"""Board Service Layer — extracted from routers/other.py"""
import json
import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session

from models import (
    BoardColumn, BoardCard, BoardCardComment, BoardCardChecklist,
    BoardCardActivity, WorkspaceRow, Board, Lead, Project,
)


# ─── Board Column helpers ─────────────────────────────────────────────────────

def _board_column_to_out(col) -> dict:
    return {
        "id": col.id,
        "board_id": col.board_id,
        "name": col.name,
        "position": col.position,
        "color": col.color,
        "cards": [],
    }


# ─── Board Card helpers ──────────────────────────────────────────────────────

def card_to_out(card, workspace_linked_ids: Optional[set] = None) -> dict:
    """Convert BoardCard model to BoardCardOut dict."""
    comments = card.comments if hasattr(card, "comments") else []
    checklist = card.checklist if hasattr(card, "checklist") else []
    activities = card.activities if hasattr(card, "activities") else []
    return {
        "id": card.id,
        "column_id": card.column_id,
        "title": card.title,
        "description": card.description,
        "assignee": card.assignee,
        "due_date": card.due_date,
        "labels": json.loads(card.labels) if card.labels else [],
        "position": card.position,
        "lead_id": card.lead_id,
        "color": card.color,
        "is_archived": card.is_archived,
        "board_card_id": card.board_card_id if hasattr(card, "board_card_id") else None,
        "updated_at": card.updated_at,
        "comments": [_board_card_comment_to_out(c) for c in comments],
        "checklist": [_board_card_checklist_to_out(i) for i in checklist],
        "activities": [_board_card_activity_to_out(a) for a in activities],
    }


def _board_card_comment_to_out(comment) -> dict:
    return {
        "id": comment.id,
        "card_id": comment.card_id,
        "author": comment.author,
        "content": comment.content,
        "created_at": comment.created_at,
    }


def _board_card_checklist_to_out(item) -> dict:
    return {
        "id": item.id,
        "card_id": item.card_id,
        "text": item.text,
        "is_done": item.is_done,
        "position": item.position,
    }


def _board_card_activity_to_out(activity) -> dict:
    return {
        "id": activity.id,
        "card_id": activity.card_id,
        "action": activity.action,
        "description": activity.description,
        "actor": activity.actor,
        "created_at": activity.created_at,
    }


# ─── Board Column operations ──────────────────────────────────────────────────

def create_board_column(db: Session, board_id: str, name: str, position: int, color: str) -> dict:
    col = BoardColumn(
        id=str(uuid.uuid4()),
        board_id=board_id,
        name=name,
        position=position,
        color=color,
    )
    db.add(col)
    db.commit()
    db.refresh(col)
    return _board_column_to_out(col)


def update_board_column(db: Session, column_id: str, name: str, position: int, color: str) -> dict:
    col = db.query(BoardColumn).filter(BoardColumn.id == column_id).first()
    if not col:
        raise ValueError("Column tidak ditemukan")
    col.name = name
    col.position = position
    col.color = color
    db.commit()
    db.refresh(col)
    return _board_column_to_out(col)


def delete_board_column(db: Session, column_id: str) -> None:
    col = db.query(BoardColumn).filter(BoardColumn.id == column_id).first()
    if not col:
        raise ValueError("Column tidak ditemukan")
    # Cascade delete cards and related data
    card_ids = [c.id for c in db.query(BoardCard.id).filter(BoardCard.column_id == column_id).all()]
    if card_ids:
        db.query(BoardCardActivity).filter(BoardCardActivity.card_id.in_(card_ids)).delete(synchronize_session=False)
        db.query(BoardCardChecklist).filter(BoardCardChecklist.card_id.in_(card_ids)).delete(synchronize_session=False)
        db.query(BoardCardComment).filter(BoardCardComment.card_id.in_(card_ids)).delete(synchronize_session=False)
    db.query(BoardCard).filter(BoardCard.column_id == column_id).delete()
    db.delete(col)
    db.commit()


# ─── Board Card operations ────────────────────────────────────────────────────

def create_board_card(
    db: Session,
    column_id: str,
    title: str,
    description: Optional[str],
    assignee: Optional[str],
    due_date: Optional[str],
    labels: Optional[list],
    lead_id: Optional[int],
    color: str,
    actor: str,
) -> dict:
    col = db.query(BoardColumn).filter(BoardColumn.id == column_id).first()
    if not col:
        raise ValueError("Column tidak ditemukan")

    max_pos = db.query(BoardCard).filter(BoardCard.column_id == column_id).count()
    card = BoardCard(
        id=str(uuid.uuid4()),
        column_id=column_id,
        title=title,
        description=description,
        assignee=assignee or actor,
        due_date=due_date,
        labels=json.dumps(labels) if labels else None,
        position=max_pos,
        lead_id=lead_id,
        color=color or "yellow",
    )
    db.add(card)

    # Add activity
    activity = BoardCardActivity(
        id=str(uuid.uuid4()),
        card_id=card.id,
        action="created",
        description=f"Card created: {title}",
        actor=actor,
    )
    db.add(activity)
    db.commit()
    db.refresh(card)

    return card_to_out(card)


def get_board_card(db: Session, card_id: str) -> dict:
    card = db.query(BoardCard).filter(BoardCard.id == card_id).first()
    if not card:
        raise ValueError("Card tidak ditemukan")
    return card_to_out(card)


def update_board_card(db: Session, card_id: str, updates: dict, actor: str) -> dict:
    card = db.query(BoardCard).filter(BoardCard.id == card_id).first()
    if not card:
        raise ValueError("Card tidak ditemukan")

    # Block title edit if card is linked to workspace row (1-way sync)
    if "title" in updates:
        workspace_linked = db.query(WorkspaceRow).filter(WorkspaceRow.board_card_id == card_id).first()
        if workspace_linked:
            pass  # ignore title change — managed by workspace
        else:
            card.title = updates["title"]

    if "description" in updates:
        card.description = updates["description"]
    if "assignee" in updates:
        card.assignee = updates["assignee"]
    if "due_date" in updates:
        card.due_date = updates["due_date"]
    if "labels" in updates:
        card.labels = json.dumps(updates["labels"])
    if "column_id" in updates:
        card.column_id = updates["column_id"]
    if "position" in updates:
        card.position = updates["position"]
    if "lead_id" in updates:
        card.lead_id = updates["lead_id"]
    if "color" in updates:
        card.color = updates["color"]
    if "is_archived" in updates:
        card.is_archived = updates["is_archived"]
        # Add activity for archive/unarchive
        action = "archived" if updates["is_archived"] else "unarchived"
        activity = BoardCardActivity(
            id=str(uuid.uuid4()),
            card_id=card.id,
            action=action,
            description=f"Card {action}",
            actor=actor,
        )
        db.add(activity)

    card.updated_at = datetime.now(timezone.utc).isoformat()

    # Add update activity
    activity = BoardCardActivity(
        id=str(uuid.uuid4()),
        card_id=card.id,
        action="updated",
        description="Card updated",
        actor=actor,
    )
    db.add(activity)

    db.commit()
    db.refresh(card)
    return card_to_out(card)


def delete_board_card(db: Session, card_id: str) -> None:
    card = db.query(BoardCard).filter(BoardCard.id == card_id).first()
    if not card:
        raise ValueError("Card tidak ditemukan")
    if db.query(WorkspaceRow).filter(WorkspaceRow.board_card_id == card_id).first():
        raise ValueError("Card terhubung ke workspace. Hapus task dari workspace agar sinkronisasi tetap konsisten.")
    db.query(BoardCardActivity).filter(BoardCardActivity.card_id == card_id).delete()
    db.query(BoardCardChecklist).filter(BoardCardChecklist.card_id == card_id).delete()
    db.query(BoardCardComment).filter(BoardCardComment.card_id == card_id).delete()
    db.delete(card)
    db.commit()


def move_board_card(
    db: Session,
    card_id: str,
    target_column_id: str,
    position: Optional[int],
    actor: str,
    current_user_role: Optional[str] = None,
) -> dict:
    card = db.query(BoardCard).filter(BoardCard.id == card_id).first()
    if not card:
        raise ValueError("Card tidak ditemukan")

    # Admin-only rule: moves to Done/Revisi columns require admin role
    target_column = db.query(BoardColumn).filter(BoardColumn.id == target_column_id).first()
    if target_column:
        target_name = (target_column.name or "").strip().lower()
        if target_name in {"done", "revisi", "selesai"} and (current_user_role or "").lower() != "admin":
            raise ValueError(f"Hanya admin yang bisa pindahin card ke '{target_column.name}'.")

    card.column_id = target_column_id
    if position is not None:
        card.position = position
    else:
        max_pos = db.query(BoardCard).filter(BoardCard.column_id == target_column_id).count()
        card.position = max_pos

    # Add activity
    activity = BoardCardActivity(
        id=str(uuid.uuid4()),
        card_id=card.id,
        action="moved",
        description="Card moved to another column",
        actor=actor,
    )
    db.add(activity)

    db.commit()
    db.refresh(card)
    return card_to_out(card)


# ─── Board Card Comment operations ────────────────────────────────────────────

def create_card_comment(
    db: Session,
    card_id: str,
    author: str,
    content: str,
) -> dict:
    card = db.query(BoardCard).filter(BoardCard.id == card_id).first()
    if not card:
        raise ValueError("Card tidak ditemukan")

    comment = BoardCardComment(
        id=str(uuid.uuid4()),
        card_id=card_id,
        author=author,
        content=content,
    )
    db.add(comment)

    # Add activity
    activity = BoardCardActivity(
        id=str(uuid.uuid4()),
        card_id=card_id,
        action="commented",
        description=f"Comment added: {content[:50]}...",
        actor=author,
    )
    db.add(activity)
    db.commit()
    db.refresh(comment)
    return _board_card_comment_to_out(comment)


# ─── Board Card Checklist operations ─────────────────────────────────────────

def create_card_checklist(
    db: Session,
    card_id: str,
    text: str,
    actor: str,
) -> dict:
    card = db.query(BoardCard).filter(BoardCard.id == card_id).first()
    if not card:
        raise ValueError("Card tidak ditemukan")

    max_pos = db.query(BoardCardChecklist).filter(BoardCardChecklist.card_id == card_id).count()
    item = BoardCardChecklist(
        id=str(uuid.uuid4()),
        card_id=card_id,
        text=text,
        position=max_pos,
    )
    db.add(item)
    activity = BoardCardActivity(
        id=str(uuid.uuid4()),
        card_id=card_id,
        action="checklist",
        description=f'Checklist "{text}" ditambahkan',
        actor=actor,
    )
    db.add(activity)
    db.commit()
    db.refresh(item)
    return _board_card_checklist_to_out(item)


def toggle_checklist_item(
    db: Session,
    card_id: str,
    item_id: str,
    is_done: bool,
    actor: str,
) -> dict:
    item = db.query(BoardCardChecklist).filter(
        BoardCardChecklist.id == item_id,
        BoardCardChecklist.card_id == card_id,
    ).first()
    if not item:
        raise ValueError("Checklist item tidak ditemukan")
    item.is_done = is_done
    status_text = "selesai" if is_done else "belum selesai"
    activity = BoardCardActivity(
        id=str(uuid.uuid4()),
        card_id=card_id,
        action="checklist",
        description=f'Checklist "{item.text}" ditandai {status_text}',
        actor=actor,
    )
    db.add(activity)
    db.commit()
    db.refresh(item)
    return _board_card_checklist_to_out(item)