"""Timeline endpoints."""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException

from src.auth.middleware import verify_auth
from src.models.sync import TopicBinding
from src.services.profile_service import _iter_agent_profiles, resolve_profile
from src.services.queue_service import RUN_LOCK
from src.services.timeline_service import (
    _sync_db,
    ts_to_iso,
    string_value,
    metadata_string,
    json_dict,
    json_list,
)

router = APIRouter()

OFFICE_TOPIC_NAMES = [
    "general", "strategy", "errors", "approvals", "tech",
    "creative", "content", "growth", "projects", "inbox",
]


def _serialize_timeline(row) -> dict:
    metadata = json_dict(row["metadata"])
    chat_id = string_value(row["chat_id"], metadata_string(metadata, "chat_id", "telegram_chat_id"))
    message_id = string_value(
        row["message_id"],
        metadata_string(metadata, "message_id", "telegram_message_id", "platform_message_id"),
    )
    message_thread_id = string_value(
        row["message_thread_id"],
        metadata_string(metadata, "message_thread_id", "thread_id", "topic_id", "forum_topic_id"),
    )
    room_key = string_value(row["room_key"], metadata_string(metadata, "room_key"))
    chat_type = string_value(row["chat_type"], metadata_string(metadata, "chat_type", "type"))
    topic_title = string_value(
        row["topic_title"],
        metadata_string(metadata, "topic_title", "topic_name", "thread_title"),
    )
    return {
        "id": int(row["id"]),
        "profile": row["profile"],
        "kind": row["kind"],
        "role": row["role"],
        "content": row["content"],
        "metadata": metadata,
        "source": row["source"],
        "session_id": row["session_id"],
        "chat_id": chat_id or None,
        "message_id": message_id or None,
        "message_thread_id": message_thread_id or None,
        "topic_title": topic_title or None,
        "room_key": room_key or None,
        "chat_type": chat_type or None,
        "created_at": ts_to_iso(row["created_at"]),
    }


@router.get("/api/office/timeline/{profile}")
def timeline(profile: str, after: int = 0, limit: int = 200, _: str = Depends(verify_auth)):
    from src.util import validate_profile
    validate_profile(profile)
    profile = resolve_profile(profile)
    limit = max(1, min(limit, 500))
    con = _sync_db()
    latest = con.execute(
        "SELECT COALESCE(MAX(id), 0) FROM timeline_events WHERE profile = ?",
        (profile,),
    ).fetchone()[0]
    if after > int(latest or 0):
        after = 0
    if after < 0:
        latest = con.execute(
            "SELECT COALESCE(MAX(id), 0) FROM timeline_events WHERE profile = ?",
            (profile,),
        ).fetchone()[0]
        rows = []
        cursor = int(latest or 0)
    else:
        rows = con.execute(
            "SELECT * FROM timeline_events WHERE profile = ? AND id > ? ORDER BY id LIMIT ?",
            (profile, after, limit),
        ).fetchall()
        cursor = int(rows[-1]["id"]) if rows else after
    pending = con.execute(
        "SELECT COUNT(*) FROM approval_inbox WHERE profile = ? AND status = 'pending'",
        (profile,),
    ).fetchone()[0]
    con.close()
    return {
        "events": [_serialize_timeline(row) for row in rows],
        "next_cursor": cursor,
        "has_more": len(rows) == limit,
        "pending_approval_count": int(pending or 0),
    }


@router.get("/api/office/telegram/bindings")
def list_topic_bindings(_: str = Depends(verify_auth)):
    con = _sync_db()
    try:
        rows = con.execute(
            "SELECT chat_id, message_thread_id, topic_title, room_key FROM topic_bindings ORDER BY chat_id, message_thread_id"
        ).fetchall()
        return {
            "bindings": [
                {
                    "chat_id": row["chat_id"],
                    "message_thread_id": row["message_thread_id"],
                    "topic_title": row["topic_title"],
                    "room_key": row["room_key"],
                }
                for row in rows
            ]
        }
    finally:
        con.close()


@router.post("/api/office/telegram/bindings")
def create_topic_binding(binding: TopicBinding, _: str = Depends(verify_auth)):
    con = _sync_db()
    try:
        con.execute(
            """
            INSERT INTO topic_bindings (chat_id, message_thread_id, topic_title, room_key)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(chat_id, message_thread_id)
            DO UPDATE SET topic_title = excluded.topic_title, room_key = excluded.room_key
            """,
            (binding.chat_id, binding.message_thread_id, binding.topic_title, binding.room_key),
        )
        con.commit()
        return {"ok": True, "binding": binding.model_dump()}
    finally:
        con.close()


@router.delete("/api/office/telegram/bindings/{chat_id}/{message_thread_id}")
def delete_topic_binding(chat_id: str, message_thread_id: str, _: str = Depends(verify_auth)):
    con = _sync_db()
    try:
        con.execute(
            "DELETE FROM topic_bindings WHERE chat_id = ? AND message_thread_id = ?",
            (chat_id, message_thread_id),
        )
        con.commit()
        return {"ok": True}
    finally:
        con.close()
