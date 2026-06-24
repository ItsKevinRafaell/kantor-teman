"""Chat API endpoints — POST /api/chat/{profile}, runs, streaming."""
import asyncio
import base64
import json
import re
import sqlite3
import threading
import time
import uuid
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

import config
from src.auth.middleware import verify_auth
from src.models.chat import (
    ChatRequest,
    TelegramMirrorMessage,
    RunApproval,
    ApprovalDecision,
    ForwardRequest,
)
from src.services.chat_service import api_request
from src.services.profile_service import (
    resolve_profile,
    _existing_profile_dir,
    _iter_agent_profiles,
    _db_path,
    read_agent_ai_config,
    _profile_display_name,
    _read_config,
    _get_latest_session,
    _latest_session_for_room,
    _office_topic_from_room_key,
    _office_room_key_from_topic,
    _telegram_binding_summary,
)
from src.services.queue_service import (
    audit_ai_request,
    queue_wait_seconds,
    mark_queue_error,
    reschedule_queue,
    mark_queue_final,
    queue_row_to_status,
    get_active_run,
    set_active_run,
    clear_active_run,
    RUN_LOCK,
)
from src.services.timeline_service import (
    _sync_db,
    ts_to_iso,
    string_value,
    metadata_string,
    json_dict,
    json_list,
    append_run_event,
    append_run_delta,
    get_run_events,
    run_context,
    set_run_context,
    audit_for_run,
    set_run_audit,
    clear_run,
    context_limit_for_message,
)
from src.util import validate_profile

router = APIRouter()

# ── constants ──────────────────────────────────────────────────────────────────

TOOL_LABELS = {
    "terminal": "menjalankan terminal",
    "bash": "menjalankan bash",
    "python": "menjalankan python",
    "memory": "menyimpan memori",
    "session_search": "mencari riwayat",
    "skill_view": "membaca skill",
    "web_search": "mencari web",
    "web_fetch": "mengakses web",
    "file_write": "menulis file",
    "file_read": "membaca file",
    "read_file": "membaca file",
    "write_file": "menulis file",
    "google_calendar": "mengakses kalender",
    "delegate_task": "mendelegasikan tugas",
    "think": "sedang berpikir",
}

OFFICE_TOPIC_NAMES = [
    "general", "strategy", "errors", "approvals", "tech",
    "creative", "content", "growth", "projects", "inbox",
]

SHARED_DIRS = [
    Path("/root/.hermes/memories"),
    Path("/root/.hermes/shared/teman-umkm-kita"),
]

# ── helper functions ───────────────────────────────────────────────────────────

def _strip_now_command(text: str) -> tuple[str, bool]:
    """Strip /now command prefix from message. Returns (cleaned_text, was_now)."""
    if text.lstrip().startswith("/now"):
        return text.lstrip()[4:].lstrip(), True
    return text, False


def _combined_queue_message(messages: list[dict]) -> str:
    """Combine queued messages into a single message string."""
    if not messages:
        return ""
    parts = []
    for msg in messages:
        role = msg.get("role", "")
        content = msg.get("content", "")
        if content:
            parts.append(f"[{role}]: {content}")
    return "\n\n".join(parts)


def _attachment_text(att: dict) -> str:
    """Convert a base64 attachment to inline text the model can read."""
    name = att.get("name", "file")
    mime = att.get("type", "")
    data_url: str = att.get("data", "")
    if "," in data_url:
        data_url = data_url.split(",", 1)[1]
    try:
        raw = base64.b64decode(data_url)
    except Exception:
        return f"[attachment: {name}]"

    text_types = ("text/", "application/json", "application/xml", "application/yaml")
    if any(mime.startswith(t) for t in text_types) or mime == "":
        try:
            content = raw.decode("utf-8", errors="replace")
            return f"\n\n[Attached file: {name}]\n```\n{content[:8000]}\n```"
        except Exception:
            pass
    if mime.startswith("image/"):
        return f"\n\n[Attached image: {name}]"
    return f"\n\n[Attached file: {name} ({mime})]"


def _sanitize_agent_output(content: str) -> str:
    """Remove tool call artifacts from assistant output."""
    if not content:
        return content
    # Remove think tags
    content = re.sub(r"<think>.*?</think>", "", content, flags=re.DOTALL)
    # Remove tool use annotations that sneak through
    content = re.sub(r"<!--.*?-->", "", content, flags=re.DOTALL)
    return content.strip()


def _append_timeline(
    profile: str,
    kind: str,
    role: str,
    content: str,
    source: str,
    source_key: str,
    *,
    session_id: Optional[str] = None,
    room_key: Optional[str] = None,
    topic_title: Optional[str] = None,
    chat_id: Optional[str] = None,
    message_id: Optional[str] = None,
    message_thread_id: Optional[str] = None,
    chat_type: Optional[str] = None,
    metadata: Optional[dict] = None,
) -> Optional[int]:
    """Append an event to the timeline. Returns row id or None."""
    if role == "assistant" and content:
        content = _sanitize_agent_output(content)
    con = _sync_db()
    try:
        meta_json = json.dumps(metadata or {})
        now = time.time()
        cur = con.execute(
            """
            INSERT INTO timeline_events
                (profile, kind, role, content, source, source_key, session_id,
                 room_key, topic_title, chat_id, message_id, message_thread_id,
                 chat_type, metadata, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(source_key) DO UPDATE SET content = excluded.content
            """,
            (
                profile, kind, role, content, source, source_key, session_id,
                room_key, topic_title, chat_id, message_id, message_thread_id,
                chat_type, meta_json, now,
            ),
        )
        con.commit()
        return cur.lastrowid
    except Exception:
        return None
    finally:
        con.close()


def _serialize_timeline(row) -> dict:
    """Serialize a timeline row to dict."""
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


def _enqueue_chat(profile: str, req: ChatRequest) -> dict:
    """Enqueue a chat message for delayed processing."""
    con = _sync_db()
    queue_id = str(uuid.uuid4())
    now = time.time()
    wait = queue_wait_seconds()
    flush_at = now + wait

    # Build messages list
    messages = []
    if req.message:
        msg_text = req.message.strip()
        if msg_text.startswith("/now"):
            msg_text = msg_text[len("/now"):].strip()
        messages.append({"role": "user", "content": msg_text})

    # Process attachments
    attachments = []
    if req.attachments:
        for att in req.attachments:
            att_dict = dict(att) if hasattr(att, "dict") else att
            att_text = _attachment_text(att_dict)
            if att_text and att_dict.get("name"):
                messages.append({"role": "system", "content": f"[file] {att_text}"})
                attachments.append(att_dict)

    messages_json = json.dumps(messages, ensure_ascii=False)
    attachments_json = json.dumps(attachments, ensure_ascii=False)

    # Extract metadata fields
    meta = req.metadata or {}
    room_key = req.room_key or meta.get("room_key")
    topic_title = req.topic_title or meta.get("topic_title") or _office_topic_from_room_key(room_key)
    chat_id = meta.get("chat_id")
    message_thread_id = meta.get("message_thread_id")

    con.execute(
        """
        INSERT INTO chat_queue
            (id, profile, channel, session_id, room_key, messages, attachments,
             status, last_message_at, flush_at, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            queue_id, profile, "web", req.session_id, room_key,
            messages_json, attachments_json, "queued", now, flush_at, now, now,
        ),
    )
    con.commit()
    con.close()

    # Start the queued run
    return _start_queued_chat({"id": queue_id, "profile": profile, "run_id": None})


def _start_chat_run_now(
    profile: str,
    messages: list[dict],
    session_id: Optional[str] = None,
    room_key: Optional[str] = None,
    topic_title: Optional[str] = None,
    metadata: Optional[dict] = None,
) -> dict:
    """Start a chat run immediately."""
    meta = metadata or {}
    topic_title = topic_title or meta.get("topic_title") or _office_topic_from_room_key(room_key)
    audit_id = f"chat-{uuid.uuid4().hex}"

    # Check for multi-message batch
    if len(messages) > 1:
        combined = _combined_queue_message(messages)
        payload = {"message": combined, "session_id": session_id, "metadata": meta}
    else:
        msg = messages[0] if messages else {}
        payload = {
            "message": msg.get("content", ""),
            "session_id": session_id,
            "metadata": meta,
        }

    audit_ai_request(
        audit_id,
        app_name="office",
        channel="web",
        profile=profile,
        model="",
        base_url="",
        request_payload={"messages": messages, "session_id": session_id},
        status="running",
    )

    try:
        run = api_request(profile, "/v1/runs", method="POST", payload=payload)
        run_id = run.get("run_id")
        if run_id:
            set_active_run(profile, run_id)
            set_run_audit(run_id, audit_id)
            _start_run_event_capture(profile, run_id)
        return run
    except HTTPException:
        raise
    except Exception as exc:
        mark_queue_error(audit_id, str(exc))
        raise HTTPException(status_code=503, detail=f"Failed to start chat: {exc}")


def _start_queued_chat(row) -> dict:
    """Start processing a queued chat."""
    queue_id = row["id"]
    profile = row["profile"]
    run_id = row["run_id"]

    if run_id:
        return queue_row_to_status(row)

    con = _sync_db()
    try:
        queue_row = con.execute("SELECT * FROM chat_queue WHERE id = ?", (queue_id,)).fetchone()
        if not queue_row:
            return {"run_id": queue_id, "status": "failed", "error": "Queue entry not found"}

        messages = json_list(queue_row["messages"])
        session_id = queue_row["session_id"]
        room_key = queue_row["room_key"]
        topic_title = _office_topic_from_room_key(room_key)

        # Mark as starting
        con.execute(
            "UPDATE chat_queue SET status = 'starting', updated_at = ? WHERE id = ?",
            (time.time(), queue_id),
        )
        con.commit()
    finally:
        con.close()

    # Start the run
    try:
        run = _start_chat_run_now(profile, messages, session_id, room_key, topic_title)
        real_run_id = run.get("run_id")

        con = _sync_db()
        try:
            con.execute(
                "UPDATE chat_queue SET status = 'running', run_id = ?, updated_at = ? WHERE id = ?",
                (real_run_id, time.time(), queue_id),
            )
            con.commit()
        finally:
            con.close()

        return queue_row_to_status({
            **dict(queue_row), "run_id": real_run_id, "status": "running"
        })
    except HTTPException as exc:
        mark_queue_error(queue_id, str(exc.detail))
        return {"run_id": queue_id, "status": "failed", "error": str(exc.detail)}


def _queue_or_run_status(profile: str, run_id: str, after: int = 0) -> Optional[dict]:
    """Check if a run is queued or return None to fall through to run status."""
    con = _sync_db()
    try:
        row = con.execute(
            "SELECT * FROM chat_queue WHERE id = ? OR run_id = ?",
            (run_id, run_id),
        ).fetchone()
        if not row:
            return None

        status = row["status"]
        if status == "queued":
            now = time.time()
            flush_at = float(row["flush_at"])
            if now >= flush_at:
                return _start_queued_chat(dict(row))
            return queue_row_to_status(dict(row))

        if status in {"starting", "failed"}:
            return queue_row_to_status(dict(row))

        # If there's a redirect run_id, follow it
        redirect_run_id = row.get("run_id")
        if redirect_run_id and redirect_run_id != run_id:
            return {"redirect_run_id": redirect_run_id}

        return None
    finally:
        con.close()


def _flush_run_partial(profile: str, run_id: str, session_id: Optional[str]) -> Optional[int]:
    """Flush partial run output to timeline and return timeline row id."""
    try:
        partial = api_request(profile, f"/v1/runs/{run_id}/partial")
        content = partial.get("content", "")
        if content:
            source_key = f"partial:{run_id}"
            row_id = _append_timeline(
                profile, "message", "assistant", content, "web-run",
                source_key, session_id=session_id,
            )
            return row_id
    except Exception:
        pass
    return None


def _timeline_event_from_run(profile: str, run_id: str, event: dict) -> Optional[int]:
    """Convert a run event to a timeline event."""
    event_type = event.get("event", "")
    session_id = event.get("session_id")
    room_key = event.get("room_key")

    # Map run events to timeline
    if event_type == "message.delta":
        content = event.get("text", "")
        if content:
            return _append_timeline(
                profile, "message", "assistant", content, "web-run",
                f"run:{run_id}:{event.get('index', '')}",
                session_id=session_id, room_key=room_key,
            )
    elif event_type in {"run.completed", "run.failed", "run.cancelled"}:
        output = event.get("output", event.get("response", ""))
        if output:
            return _append_timeline(
                profile, "message", "assistant", str(output), "web-run",
                f"run-final:{run_id}",
                session_id=session_id, room_key=room_key,
            )

    return None


def _start_run_event_capture(profile: str, run_id: str) -> None:
    """Start background thread to capture run events."""
    def _capture():
        while True:
            try:
                run = api_request(profile, f"/v1/runs/{run_id}")
                status = run.get("status", "")

                if status in {"completed", "failed", "cancelled"}:
                    _normalize_run_response(profile, run)
                    clear_active_run(profile)
                    clear_run(run_id)
                    break

                # Capture events
                try:
                    events_data = api_request(profile, f"/v1/runs/{run_id}/events")
                    events = events_data.get("events", [])
                except Exception:
                    events = []

                for event in events:
                    append_run_event(run_id, event)
                    _timeline_event_from_run(profile, run_id, event)
                    if event.get("event") == "message.delta":
                        append_run_delta(run_id, event.get("text", ""))
                    elif event.get("event") == "run.completed":
                        _flush_run_partial(profile, run_id, run.get("session_id"))

                time.sleep(0.5)
            except Exception:
                time.sleep(1)

    threading.Thread(target=_capture, daemon=True).start()


def _persist_web_message_to_profile(
    profile: str,
    role: str,
    content: str,
    session_id: str,
    metadata: Optional[dict] = None,
) -> bool:
    """Persist a web message to the profile's state.db."""
    db = _db_path(profile)
    if not db:
        return False
    try:
        con = sqlite3.connect(db)
        now = time.time()
        meta_json = json.dumps(metadata or {})
        con.execute(
            """
            INSERT INTO messages (session_id, role, content, timestamp, metadata)
            VALUES (?, ?, ?, ?, ?)
            """,
            (session_id, role, content, now, meta_json),
        )
        con.commit()
        con.close()
        return True
    except Exception:
        return False


def _persist_run_final(profile: str, run_id: str, response: str, session_id: Optional[str]) -> None:
    """Persist final run response to timeline and profile."""
    if not response:
        return

    # Append to timeline
    _append_timeline(
        profile, "message", "assistant", response, "web-run",
        f"run-final:{run_id}", session_id=session_id,
    )

    # Persist to profile state.db
    if session_id:
        _persist_web_message_to_profile(profile, "assistant", response, session_id)

    # Update audit
    audit_id = audit_for_run(run_id)
    if audit_id:
        audit_ai_request(
            audit_id,
            app_name="office",
            channel="web",
            profile=profile,
            model="",
            base_url="",
            request_payload={},
            response_payload={"response": response},
            status="completed",
            completed=True,
        )


def _resolve_approval_rows(run_id: str, choice: str) -> None:
    """Update approval inbox rows for a resolved run."""
    con = _sync_db()
    try:
        now = time.time()
        con.execute(
            """
            UPDATE approval_inbox
            SET status = 'resolved', resolved_at = ?, decision = ?
            WHERE run_id = ?
            """,
            (now, choice, run_id),
        )
        con.commit()
    finally:
        con.close()


def _drain_telegram_outbox() -> None:
    """Send pending Telegram messages from outbox."""
    con = _sync_db()
    try:
        rows = con.execute(
            """
            SELECT * FROM telegram_outbox
            WHERE status = 'pending' AND next_attempt <= ?
            ORDER BY id LIMIT 10
            """,
            (time.time(),),
        ).fetchall()

        for row in rows:
            outbox_id = row["id"]
            profile = row["profile"]
            text = row["text"]
            chat_id = row.get("chat_id")
            message_thread_id = row.get("message_thread_id")
            reply_to = row.get("reply_to_message_id")

            try:
                payload = {
                    "text": text,
                    "chat_id": chat_id,
                }
                if message_thread_id:
                    payload["message_thread_id"] = message_thread_id
                if reply_to:
                    payload["reply_to_message_id"] = reply_to

                result = api_request(profile, "/v1/telegram/send", method="POST", payload=payload)

                con.execute(
                    "UPDATE telegram_outbox SET status = 'delivered', delivered_at = ? WHERE id = ?",
                    (time.time(), outbox_id),
                )
            except Exception as exc:
                attempts = row["attempts"] + 1
                next_attempt = time.time() + min(300, 2 ** attempts)
                con.execute(
                    """
                    UPDATE telegram_outbox
                    SET attempts = ?, next_attempt = ?, last_error = ?
                    WHERE id = ?
                    """,
                    (attempts, next_attempt, str(exc)[:200], outbox_id),
                )
            con.commit()
    finally:
        con.close()


def _queue_telegram(
    profile: str,
    text: str,
    dedupe_key: str,
    chat_id: Optional[str] = None,
    message_thread_id: Optional[str] = None,
    reply_to_message_id: Optional[str] = None,
) -> None:
    """Queue a Telegram message for delivery."""
    con = _sync_db()
    try:
        con.execute(
            """
            INSERT INTO telegram_outbox
                (profile, text, dedupe_key, status, attempts, next_attempt,
                 created_at, chat_id, message_thread_id, reply_to_message_id)
            VALUES (?, ?, ?, 'pending', 0, 0, ?, ?, ?, ?)
            ON CONFLICT(dedupe_key) DO UPDATE SET
                text = excluded.text,
                next_attempt = 0,
                status = 'pending'
            """,
            (profile, text, dedupe_key, time.time(),
             chat_id, message_thread_id, reply_to_message_id),
        )
        con.commit()
    finally:
        con.close()


def _get_timeline_history(profile: str, limit: int = 500, session_id: Optional[str] = None) -> list:
    """Get timeline history for a profile."""
    con = _sync_db()
    try:
        if session_id:
            rows = con.execute(
                """
                SELECT * FROM timeline_events
                WHERE profile = ? AND session_id = ?
                ORDER BY id LIMIT ?
                """,
                (profile, session_id, limit),
            ).fetchall()
        else:
            rows = con.execute(
                """
                SELECT * FROM timeline_events
                WHERE profile = ? AND kind = 'message'
                ORDER BY id DESC LIMIT ?
                """,
                (profile, limit),
            ).fetchall()
        return [_serialize_timeline(row) for row in rows]
    finally:
        con.close()


def _get_history(profile: str, limit: int = 500) -> list:
    """Get message history from profile state.db."""
    db = _db_path(profile)
    if not db:
        return []
    try:
        con = sqlite3.connect(db)
        rows = con.execute(
            """
            SELECT m.role, m.content, m.timestamp
            FROM messages m
            ORDER BY m.timestamp DESC LIMIT ?
            """,
            (limit,),
        ).fetchall()
        con.close()
        result = [
            {"role": r[0], "content": r[1], "created_at": ts_to_iso(r[2])}
            for r in rows
        ]
        result.reverse()
        return result
    except Exception:
        return []


def _normalize_run_response(profile: str, run: dict) -> dict:
    """Normalize a run response and persist results."""
    result = dict(run)
    result["profile"] = profile
    result["response"] = result.get("output", "")

    if result.get("status") == "completed":
        run_id = result.get("run_id")
        _persist_run_final(profile, run_id, result["response"], result.get("session_id"))
    elif result.get("status") in {"failed", "cancelled"}:
        run_id = result.get("run_id")
        mark_queue_final(run_id, result["status"], str(result.get("error") or ""))
        with RUN_LOCK:
            if get_active_run(profile) == run_id:
                clear_active_run(profile)

    return result


def _get_session_history(profile: str, session_id: str, limit: int = 1000) -> list:
    """Get message history for a specific session."""
    db = _db_path(profile)
    if not db:
        return []
    try:
        con = sqlite3.connect(db)
        rows = con.execute(
            """
            SELECT role, content, timestamp
            FROM messages
            WHERE session_id = ? AND role IN ('user', 'assistant')
              AND content IS NOT NULL AND content != ''
            ORDER BY timestamp
            LIMIT ?
            """,
            (session_id, limit),
        ).fetchall()
        con.close()
        return [
            {"role": r[0], "content": r[1], "created_at": ts_to_iso(r[2])}
            for r in rows
        ]
    except Exception:
        return []


def _timeline_rows_for_profiles(
    profiles: list[str],
    after: int,
    limit: int,
    source_filter: Optional[list] = None,
) -> tuple[list, int, bool]:
    """Get timeline rows for multiple profiles."""
    con = _sync_db()
    try:
        placeholders = ",".join("?" * len(profiles))
        latest = con.execute(
            f"SELECT COALESCE(MAX(id), 0) FROM timeline_events WHERE profile IN ({placeholders})",
            profiles,
        ).fetchone()[0]

        if after > int(latest or 0):
            after = 0

        if source_filter:
            src_placeholders = ",".join("?" * len(source_filter))
            rows = con.execute(
                f"""
                SELECT * FROM timeline_events
                WHERE profile IN ({placeholders}) AND id > ? AND source IN ({src_placeholders})
                ORDER BY id LIMIT ?
                """,
                [*profiles, after, *source_filter, limit],
            ).fetchall()
        else:
            rows = con.execute(
                f"""
                SELECT * FROM timeline_events
                WHERE profile IN ({placeholders}) AND id > ?
                ORDER BY id LIMIT ?
                """,
                [*profiles, after, limit],
            ).fetchall()

        cursor = int(rows[-1]["id"]) if rows else after
        return list(rows), cursor, len(rows) == limit
    finally:
        con.close()


def _rooms_for_events(events: list[dict], profile_names: list[str]) -> list[dict]:
    """Extract unique rooms from timeline events."""
    rooms: dict[str, dict] = {}
    for event in events:
        room_key = event.get("room_key")
        if room_key:
            rooms[room_key] = _office_topic_room(room_key, profile_names)
    return list(rooms.values())


def _office_topic_room(topic: str, profile_names: list[str]) -> dict:
    """Get room info for an office topic."""
    chat_id = None
    message_thread_id = None
    topic_title = topic

    # Look up binding
    con = _sync_db()
    try:
        row = con.execute(
            "SELECT chat_id, message_thread_id FROM topic_bindings WHERE room_key = ?",
            (topic,),
        ).fetchone()
        if row:
            chat_id = row["chat_id"]
            message_thread_id = row["message_thread_id"]
            topic_title = _lookup_topic_title(chat_id, message_thread_id) or topic
    finally:
        con.close()

    return {
        "room_key": topic,
        "topic_title": topic_title,
        "chat_id": chat_id,
        "message_thread_id": message_thread_id,
        "profiles": profile_names,
    }


def _lookup_topic_title(chat_id: str, message_thread_id: str) -> str:
    """Look up topic title from Telegram."""
    con = _sync_db()
    try:
        row = con.execute(
            "SELECT topic_title FROM topic_bindings WHERE chat_id = ? AND message_thread_id = ?",
            (chat_id, message_thread_id),
        ).fetchone()
        return row["topic_title"] if row else ""
    finally:
        con.close()


def _lookup_room_key(chat_id: str, message_thread_id: str) -> str:
    """Look up room key from Telegram identifiers."""
    return _office_room_key_from_topic(_lookup_topic_title(chat_id, message_thread_id))


def _office_room_key_from_topic(topic: str) -> str:
    """Convert office topic to room key."""
    return f"office:{topic}"


def _iter_profile_telegram_messages(profile: str, after_id: int, limit: int) -> list:
    """Iterate Telegram messages from a profile."""
    db = _db_path(profile)
    if not db:
        return []
    try:
        con = sqlite3.connect(db)
        rows = con.execute(
            """
            SELECT m.*, s.source as session_source
            FROM messages m
            LEFT JOIN sessions s ON m.session_id = s.id
            WHERE m.id > ? AND m.role IN ('user', 'assistant')
            ORDER BY m.id ASC LIMIT ?
            """,
            (after_id, limit),
        ).fetchall()
        con.close()
        return [dict(row) for row in rows]
    except Exception:
        return []


def _append_profile_message_to_timeline(profile: str, row: dict) -> Optional[int]:
    """Append a profile message to timeline."""
    meta = json_dict(row.get("metadata") or "{}")
    session_id = row.get("session_id")
    content = row.get("content", "")

    if not content:
        return None

    role = row.get("role", "user")
    source = row.get("session_source", "telegram-db")

    # Determine source_key
    msg_id = row.get("id")
    source_key = f"profile:{profile}:{msg_id}"

    # Extract room info from metadata
    room_key = string_value(
        meta.get("room_key"),
        meta.get("chat_id"),
    )
    chat_id = string_value(meta.get("chat_id"), meta.get("telegram_chat_id"))
    message_id = string_value(meta.get("message_id"), meta.get("telegram_message_id"))
    message_thread_id = string_value(
        meta.get("message_thread_id"),
        meta.get("thread_id"),
        meta.get("topic_id"),
    )
    topic_title = string_value(
        meta.get("topic_title"),
        meta.get("topic_name"),
        meta.get("thread_title"),
    )
    chat_type = string_value(meta.get("chat_type"), meta.get("type"), "private")

    if not room_key and chat_id:
        room_key = f"telegram:{chat_id}:{message_thread_id or 'main'}"

    return _append_timeline(
        profile, "message", role, content, source, source_key,
        session_id=session_id, room_key=room_key, topic_title=topic_title,
        chat_id=chat_id, message_id=message_id, message_thread_id=message_thread_id,
        chat_type=chat_type, metadata=meta,
    )


def _max_profile_message_id(profile: str) -> int:
    """Get max message id from profile timeline."""
    db = _db_path(profile)
    if not db:
        return 0
    con = _sync_db()
    try:
        row = con.execute(
            """
            SELECT MAX(CAST(message_id AS INTEGER)) as max_id
            FROM timeline_events WHERE profile = ?
            """,
            (profile,),
        ).fetchone()
        return int(row["max_id"] or 0) if row else 0
    finally:
        con.close()


def _mark_timeline_cursor(profile: str, last_id: int) -> None:
    """Mark the timeline cursor for a profile."""
    con = _sync_db()
    try:
        con.execute(
            """
            INSERT INTO timeline_cursors(profile, last_message_id) VALUES (?, ?)
            ON CONFLICT(profile) DO UPDATE SET last_message_id = excluded.last_message_id
            """,
            (profile, int(last_id or 0)),
        )
        con.commit()
    finally:
        con.close()


def _ingest_profile_messages(profile: str) -> None:
    """Ingest new messages from profile to timeline."""
    db = _db_path(profile)
    if not db:
        return
    con = _sync_db()
    cursor = con.execute(
        "SELECT last_message_id FROM timeline_cursors WHERE profile = ?",
        (profile,),
    ).fetchone()
    last_id = int(cursor["last_message_id"]) if cursor else 0
    con.close()

    rows = _iter_profile_telegram_messages(profile, last_id, 500)
    if not rows:
        return

    for row in rows:
        _append_profile_message_to_timeline(profile, row)
        last_id = int(row["id"])

    _mark_timeline_cursor(profile, last_id)


def _backfill_profile_messages(profile: str) -> None:
    """Backfill all historical messages from profile."""
    con = _sync_db()
    try:
        marker = con.execute(
            "SELECT last_message_id FROM timeline_backfills WHERE profile = ?",
            (profile,),
        ).fetchone()
        if marker:
            return
    finally:
        con.close()

    last_id = 0
    while True:
        rows = _iter_profile_telegram_messages(profile, last_id, 1000)
        if not rows:
            break
        for row in rows:
            _append_profile_message_to_timeline(profile, row)
            last_id = int(row["id"])

    max_id = max(last_id, _max_profile_message_id(profile))
    con = _sync_db()
    try:
        con.execute(
            """
            INSERT INTO timeline_backfills(profile, completed_at, last_message_id) VALUES (?, ?, ?)
            ON CONFLICT(profile) DO UPDATE
              SET completed_at = excluded.completed_at,
                  last_message_id = excluded.last_message_id
            """,
            (profile, time.time(), max_id),
        )
        con.execute(
            """
            INSERT INTO timeline_cursors(profile, last_message_id) VALUES (?, ?)
            ON CONFLICT(profile) DO UPDATE SET
                last_message_id = MAX(timeline_cursors.last_message_id, excluded.last_message_id)
            """,
            (profile, max_id),
        )
        con.commit()
    finally:
        con.close()


def _ensure_profile_timeline(profile: str, backfill: bool = False) -> None:
    """Ensure timeline is populated for a profile."""
    if backfill:
        _backfill_profile_messages(profile)
    _ingest_profile_messages(profile)


def _serialize_approval(row) -> dict:
    """Serialize an approval row."""
    return {
        "id": row["id"],
        "profile": row["profile"],
        "run_id": row["run_id"],
        "command": row["command"],
        "summary": row["summary"],
        "status": row["status"],
        "created_at": ts_to_iso(row["created_at"]),
        "resolved_at": ts_to_iso(row["resolved_at"]) if row["resolved_at"] else None,
        "decision": row["decision"],
    }


def _get_activity(profile: str) -> dict:
    """Get current activity status for a profile."""
    profile = resolve_profile(profile)
    db = _db_path(profile)
    if not db:
        return {"active": False, "stage": "offline", "label": "Offline", "tool": None}

    active_run = get_active_run(profile)
    if active_run:
        try:
            run = api_request(profile, f"/v1/runs/{active_run}")
            if run.get("status") not in {"completed", "failed", "cancelled"}:
                events, _ = get_run_events(active_run)
                for event in reversed(events):
                    if event.get("event") == "tool.started":
                        tool_name = event.get("tool") or "tool"
                        label = TOOL_LABELS.get(tool_name, f"Menjalankan {tool_name}")
                        return {"active": True, "stage": "tool", "label": label + "…", "tool": tool_name}
                    if event.get("event") in {"tool.completed", "approval.responded"}:
                        break

                if run.get("status") == "waiting_for_approval":
                    return {"active": True, "stage": "tool", "label": "Menunggu approval…", "tool": None}
                return {"active": True, "stage": "thinking", "label": "Sedang berpikir…", "tool": None}
        except Exception:
            pass

    gateway_state = _existing_profile_dir(profile) / "gateway_state.json"
    try:
        if gateway_state.exists():
            state = json.loads(gateway_state.read_text(encoding="utf-8"))
            if int(state.get("active_agents") or 0) > 0:
                return {"active": True, "stage": "thinking", "label": "Sedang berpikir…", "tool": None}
    except Exception:
        pass

    return {"active": False, "stage": "idle", "label": "Idle", "tool": None}


# ── endpoints ──────────────────────────────────────────────────────────────────

@router.post("/api/office/chat/{profile}")
def chat(profile: str, req: ChatRequest, _: str = Depends(verify_auth)):
    """Enqueue a chat message for processing."""
    profile = resolve_profile(profile)
    queued = _enqueue_chat(profile, req)
    return {
        **queued,
        "status": "started",
        "queued": True,
    }


@router.get("/api/office/chat/{profile}/runs/{run_id}")
def get_chat_run(
    profile: str,
    run_id: str,
    after: int = 0,
    _: str = Depends(verify_auth),
):
    """Get run status and events."""
    profile = resolve_profile(profile)
    queued = _queue_or_run_status(profile, run_id, after)
    if queued:
        if queued.get("redirect_run_id"):
            run_id = queued["redirect_run_id"]
        elif queued.get("run_id") != run_id and queued.get("status") not in {"queued", "failed"}:
            run_id = queued["run_id"]
        else:
            return queued

    events, next_event = get_run_events(run_id, max(0, after))

    try:
        run = _normalize_run_response(profile, api_request(profile, f"/v1/runs/{run_id}"))
    except HTTPException as exc:
        completed = next(
            (event for event in reversed(events) if event.get("event") == "run.completed"),
            None,
        )
        failed = next(
            (event for event in reversed(events) if event.get("event") in {"run.failed", "run.cancelled"}),
            None,
        )
        if completed:
            output = str(completed.get("output") or completed.get("response") or "")
            return {
                "run_id": run_id,
                "status": "completed",
                "response": output,
                "output": output,
                "session_id": completed.get("session_id") or _get_latest_session(profile) or run_id,
                "profile": profile,
                "events": events,
                "next_event": next_event,
            }
        if failed:
            return {
                "run_id": run_id,
                "status": "failed" if failed.get("event") == "run.failed" else "cancelled",
                "error": str(failed.get("error") or failed.get("message") or exc.detail),
                "session_id": failed.get("session_id") or _get_latest_session(profile) or run_id,
                "profile": profile,
                "events": events,
                "next_event": next_event,
            }
        with RUN_LOCK:
            active = get_active_run(profile) == run_id
        if active:
            return {
                "run_id": run_id,
                "status": "running",
                "session_id": _get_latest_session(profile) or run_id,
                "profile": profile,
                "events": events,
                "next_event": next_event,
            }
        raise

    return {**run, "events": events, "next_event": next_event}


@router.post("/api/office/chat/{profile}/runs/{run_id}/stop")
def stop_chat_run(profile: str, run_id: str, _: str = Depends(verify_auth)):
    """Stop a running or queued chat."""
    profile = resolve_profile(profile)
    con = _sync_db()
    try:
        row = con.execute(
            "SELECT * FROM chat_queue WHERE id = ? AND profile = ? AND status IN ('queued', 'starting')",
            (run_id, profile),
        ).fetchone()
        if row and not row["run_id"]:
            con.execute(
                "UPDATE chat_queue SET status = 'cancelled', updated_at = ? WHERE id = ?",
                (time.time(), run_id),
            )
            con.commit()
            return {"ok": True, "status": "cancelled"}
    finally:
        con.close()
    return api_request(profile, f"/v1/runs/{run_id}/stop", method="POST", payload={})


@router.post("/api/office/chat/{profile}/runs/{run_id}/approval")
def approve_chat_run(
    profile: str,
    run_id: str,
    req: RunApproval,
    _: str = Depends(verify_auth),
):
    """Approve a pending run action."""
    profile = resolve_profile(profile)
    result = api_request(profile, f"/v1/runs/{run_id}/approval", method="POST", payload={"choice": req.choice})
    _resolve_approval_rows(run_id, req.choice)
    return result


@router.get("/api/office/approvals")
def approval_inbox(
    profile: Optional[str] = None,
    status: str = "pending",
    _: str = Depends(verify_auth),
):
    """List pending approvals."""
    if profile:
        validate_profile(profile)
    if status not in {"pending", "resolved", "all"}:
        raise HTTPException(status_code=400, detail="Invalid approval status")

    clauses = []
    params: list = []
    if profile:
        clauses.append("profile = ?")
        params.append(profile)
    if status != "all":
        clauses.append("status = ?")
        params.append(status)

    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    con = _sync_db()
    rows = con.execute(
        f"SELECT * FROM approval_inbox {where} ORDER BY created_at DESC LIMIT 200",
        params,
    ).fetchall()
    con.close()
    return [_serialize_approval(row) for row in rows]


@router.post("/api/office/approvals/{approval_id}")
def decide_approval(
    approval_id: str,
    req: ApprovalDecision,
    _: str = Depends(verify_auth),
):
    """Decide on an approval request."""
    con = _sync_db()
    row = con.execute("SELECT * FROM approval_inbox WHERE id = ?", (approval_id,)).fetchone()
    con.close()
    if not row:
        raise HTTPException(status_code=404, detail="Approval not found")
    choice = "once" if req.decision in {"approve", "once"} else "deny"
    return approve_chat_run(row["profile"], row["run_id"], RunApproval(choice=choice), _)


@router.get("/api/office/outbox")
def outbox_status(_: str = Depends(verify_auth)):
    """Get telegram outbox status."""
    con = _sync_db()
    rows = con.execute(
        "SELECT status, COUNT(*) AS count FROM telegram_outbox GROUP BY status"
    ).fetchall()
    con.close()
    return {row["status"]: int(row["count"]) for row in rows}


@router.post("/api/office/forward")
def forward_messages(req: ForwardRequest, _: str = Depends(verify_auth)):
    """Forward messages from one profile to another."""
    target = validate_profile(req.target_profile)
    if req.source_profile:
        validate_profile(req.source_profile)
    messages = [message.strip() for message in req.messages if message.strip()]
    if not messages:
        raise HTTPException(status_code=400, detail="No messages to forward")
    source = req.source_profile.title() if req.source_profile else "Web"
    content = f"[Forwarded from {source}]\n\n" + "\n\n---\n\n".join(messages)
    return chat(target, ChatRequest(message=content), _)


@router.get("/api/office/status")
def status(_: str = Depends(verify_auth)):
    """Get status of all profiles."""
    out = {}
    for profile, profile_dir in _iter_agent_profiles():
        if not (profile_dir / "state.db").exists():
            out[profile] = "offline"
            continue
        try:
            act = _get_activity(profile)
            out[profile] = "busy" if act["active"] else "idle"
        except Exception:
            out[profile] = "idle"
    return out


@router.get("/api/office/history/{profile}")
def history(profile: str, limit: int = 500, _: str = Depends(verify_auth)):
    """Get message history for a profile."""
    profile = resolve_profile(profile)
    return _get_history(profile, limit)


@router.get("/api/office/conversations/{profile}")
def conversations(profile: str, _: str = Depends(verify_auth)):
    """List all conversation sessions for a profile."""
    profile = resolve_profile(profile)
    db = _db_path(profile)
    if not db:
        return []
    try:
        con = sqlite3.connect(db)
        rows = con.execute(
            """
            SELECT
                s.id,
                s.started_at,
                (
                    SELECT content FROM messages
                    WHERE session_id = s.id AND role = 'user' AND content IS NOT NULL AND content != ''
                    ORDER BY timestamp LIMIT 1
                ) as preview,
                COALESCE(s.message_count, (SELECT COUNT(*) FROM messages WHERE session_id = s.id)) as msg_count
            FROM sessions s
            WHERE s.source != 'cron'
            ORDER BY s.started_at DESC
            LIMIT 100
            """
        ).fetchall()
        con.close()
        return [
            {
                "session_id": r[0],
                "started_at": ts_to_iso(r[1]),
                "preview": (r[2] or "")[:120],
                "message_count": r[3] or 0,
            }
            for r in rows
            if r[2]
        ]
    except Exception:
        return []


@router.get("/api/office/conversations/{profile}/{session_id}")
def conversation_messages(profile: str, session_id: str, _: str = Depends(verify_auth)):
    """Get all messages for a specific session."""
    profile = resolve_profile(profile)
    db = _db_path(profile)
    if not db:
        return []
    try:
        timeline = _get_timeline_history(profile, limit=1000, session_id=session_id)
        if timeline:
            return timeline
    except Exception:
        pass
    try:
        return _get_session_history(profile, session_id, 1000)
    except Exception:
        return []


@router.delete("/api/office/conversations/{profile}/{session_id}")
def delete_conversation(profile: str, session_id: str, _: str = Depends(verify_auth)):
    """Delete a conversation session."""
    profile = resolve_profile(profile)
    db = _db_path(profile)
    if not db:
        raise HTTPException(status_code=404, detail="Profile state not found")
    try:
        con = sqlite3.connect(db, timeout=10)
        exists = con.execute("SELECT 1 FROM sessions WHERE id = ?", (session_id,)).fetchone()
        if not exists:
            con.close()
            raise HTTPException(status_code=404, detail="Conversation not found")

        platform_rows = con.execute(
            """
            SELECT platform_message_id FROM messages
            WHERE session_id = ? AND platform_message_id IS NOT NULL
            """,
            (session_id,),
        ).fetchall()

        source_keys = []
        for row in platform_rows:
            platform_id = str(row[0] or "")
            if platform_id.startswith("office-backfill:"):
                source_keys.append(platform_id.removeprefix("office-backfill:"))
            elif platform_id.startswith("office:"):
                source_keys.append(platform_id.removeprefix("office:"))

        con.execute("DELETE FROM messages WHERE session_id = ?", (session_id,))
        con.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
        con.commit()
        con.close()

        sync = _sync_db()
        sync.execute(
            "DELETE FROM timeline_events WHERE profile = ? AND session_id = ?",
            (profile, session_id),
        )
        if source_keys:
            placeholders = ",".join("?" for _ in source_keys)
            sync.execute(
                f"DELETE FROM timeline_events WHERE profile = ? AND source_key IN ({placeholders})",
                [profile, *source_keys],
            )
        sync.commit()
        sync.close()
        return {"ok": True}
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)[:240])


# ── legacy aliases ─────────────────────────────────────────────────────────────

@router.post("/chat/{profile}")
def chat_legacy(profile: str, req: ChatRequest, _: str = Depends(verify_auth)):
    """Legacy chat endpoint alias."""
    return chat(profile, req, _)


@router.get("/status")
def status_legacy(_: str = Depends(verify_auth)):
    """Legacy status endpoint alias."""
    return status(_)


@router.get("/history/{profile}")
def history_legacy(profile: str, limit: int = 40, _: str = Depends(verify_auth)):
    """Legacy history endpoint alias."""
    profile = resolve_profile(profile)
    return _get_history(profile, limit)


# ── telegram mirror ─────────────────────────────────────────────────────────────

@router.get("/api/office/telegram/mirror")
def telegram_mirror(
    after: int = 0,
    limit: int = 200,
    profile: Optional[str] = None,
    profiles: Optional[str] = None,
    _: str = Depends(verify_auth),
):
    """Get Telegram mirror events for profiles."""
    requested = profiles or profile
    if requested:
        profile_names = [resolve_profile(item.strip()) for item in requested.split(",") if item.strip()]
    else:
        profile_names = [item[0] for item in _iter_agent_profiles()]

    for profile_name in profile_names:
        _ensure_profile_timeline(profile_name, backfill=after < 0)

    rows, cursor, has_more = _timeline_rows_for_profiles(
        profile_names, after, max(1, min(limit, 500)),
        source_filter=["telegram-db", "web", "web-run"],
    )

    events = [_serialize_timeline(row) for row in rows]
    grouped: dict[str, list[dict]] = {}
    for event in events:
        grouped.setdefault(event["room_key"], []).append(event)

    return {
        "profiles": [_telegram_binding_summary(profile_name) for profile_name in profile_names],
        "events": events,
        "groups": grouped,
        "rooms": _rooms_for_events(events, profile_names),
        "next_cursor": cursor,
        "has_more": has_more,
    }


@router.get("/api/office/telegram/mirror/stream")
async def telegram_mirror_stream(
    request: Request,
    after: int = 0,
    limit: int = 200,
    profile: Optional[str] = None,
    profiles: Optional[str] = None,
    _: str = Depends(verify_auth),
):
    """SSE stream for Telegram mirror events."""
    requested = profiles or profile
    if requested:
        profile_names = [resolve_profile(item.strip()) for item in requested.split(",") if item.strip()]
    else:
        profile_names = [item[0] for item in _iter_agent_profiles()]
    limit = max(1, min(limit, 500))

    async def stream():
        cursor = after
        while not await request.is_disconnected():
            try:
                for profile_name in profile_names:
                    _ensure_profile_timeline(profile_name)
                rows, next_cursor, has_more = _timeline_rows_for_profiles(
                    profile_names, cursor, limit,
                    source_filter=["telegram-db", "web", "web-run"],
                )
                events = [_serialize_timeline(row) for row in rows]
                if events:
                    grouped: dict[str, list[dict]] = {}
                    for event in events:
                        grouped.setdefault(event["room_key"], []).append(event)
                    payload = {
                        "profiles": [_telegram_binding_summary(profile_name) for profile_name in profile_names],
                        "events": events,
                        "groups": grouped,
                        "rooms": _rooms_for_events(events, profile_names),
                        "next_cursor": next_cursor,
                        "has_more": has_more,
                    }
                    cursor = next_cursor
                    yield f"id: {cursor}\nevent: mirror\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"
                else:
                    cursor = next_cursor
                    yield f": keepalive {int(time.time())}\n\n"
            except Exception as exc:
                payload = {"detail": str(exc)[:500], "next_cursor": cursor}
                yield f"event: error\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"
            await asyncio.sleep(0.8)

    return StreamingResponse(stream(), media_type="text/event-stream")


@router.post("/api/office/telegram/mirror")
def telegram_mirror_send(req: TelegramMirrorMessage, _: str = Depends(verify_auth)):
    """Send a message via Telegram mirror."""
    content = req.message.strip()
    attachments = list(req.attachments or [])
    if not content and not attachments:
        raise HTTPException(status_code=400, detail="Message kosong")

    # Parse @mentions from message content
    mentioned_profiles = set()
    if content:
        mention_pattern = re.compile(r"@(\w+)", re.IGNORECASE)
        mentions = mention_pattern.findall(content)
        for mention in mentions:
            mention_lower = mention.lower()
            for profile, _ in _iter_agent_profiles():
                if profile == mention_lower:
                    mentioned_profiles.add(profile)
                    break
                profile_dir = _existing_profile_dir(profile)
                cfg = _read_config(profile_dir)
                display_name = cfg.get("display_name", profile) if cfg else profile
                if display_name.lower() == mention_lower:
                    mentioned_profiles.add(profile)
                    break

    # Determine targets
    if mentioned_profiles:
        targets = list(mentioned_profiles)
    else:
        targets = [resolve_profile(profile) for profile in (req.profiles or []) if profile]
        if not targets:
            targets = [profile for profile, _ in _iter_agent_profiles()]

    results = []
    for target in targets:
        session_id = (
            req.session_id
            or _latest_session_for_room(
                target,
                room_key=req.room_key,
                chat_id=req.chat_id,
                message_thread_id=req.message_thread_id,
            )
        )
        topic_title = string_value(req.topic_title, _office_topic_from_room_key(req.room_key))
        results.append(chat(
            target,
            ChatRequest(
                message=content,
                session_id=session_id,
                attachments=attachments,
                room_key=req.room_key,
                topic_title=topic_title,
                metadata={
                    "room_key": req.room_key,
                    "chat_id": req.chat_id,
                    "message_thread_id": req.message_thread_id,
                    "topic_title": topic_title,
                    "source": "office-group",
                },
            ),
            _,
        ))
    return {"ok": True, "targets": targets, "results": results}
