"""In-app notification helpers."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session

from models import Notification


def create_notification(
    db: Session,
    title: str,
    message: str,
    notif_type: str = "info",
    target_type: Optional[str] = None,
    target_id: Optional[str] = None,
    action_url: Optional[str] = None,
    user_id: Optional[int] = None,
    commit: bool = False,
) -> Notification:
    notif = Notification(
        id=str(uuid.uuid4()),
        user_id=user_id,
        title=title,
        message=message,
        type=notif_type,
        target_type=target_type,
        target_id=str(target_id) if target_id is not None else None,
        action_url=action_url,
        created_at=datetime.now(timezone.utc).isoformat(),
    )
    db.add(notif)
    if commit:
        db.commit()
        db.refresh(notif)
    return notif


def notification_to_dict(notif: Notification) -> dict:
    return {
        "id": notif.id,
        "user_id": notif.user_id,
        "title": notif.title,
        "message": notif.message,
        "type": notif.type,
        "target_type": notif.target_type,
        "target_id": notif.target_id,
        "action_url": notif.action_url,
        "is_read": bool(notif.is_read),
        "created_at": notif.created_at,
        "read_at": notif.read_at,
    }


def mark_notification_read(db: Session, notification_id: str) -> Notification:
    notif = db.query(Notification).filter(Notification.id == notification_id).first()
    if not notif:
        raise ValueError("Notifikasi tidak ditemukan")
    notif.is_read = True
    notif.read_at = datetime.now(timezone.utc).isoformat()
    db.commit()
    db.refresh(notif)
    return notif
