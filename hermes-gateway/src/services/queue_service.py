"""Thread-safe queue management for chat runs."""
import json
import threading
import time
import uuid
from typing import Optional

import config
from src.services.timeline_service import _sync_db
from src.util import redact

# Global state
ACTIVE_RUNS: dict[str, str] = {}
RUN_LOCK = threading.Lock()


def get_active_run(profile: str) -> Optional[str]:
    with RUN_LOCK:
        return ACTIVE_RUNS.get(profile)


def set_active_run(profile: str, run_id: str) -> None:
    with RUN_LOCK:
        ACTIVE_RUNS[profile] = run_id


def clear_active_run(profile: str) -> None:
    with RUN_LOCK:
        ACTIVE_RUNS.pop(profile, None)


def queue_wait_seconds() -> int:
    return max(0, int(config.HERMES_MULTI_READ_SECONDS))


def audit_ai_request(
    audit_id: str,
    *,
    app_name: str,
    channel: str,
    profile: str,
    model: str = "",
    base_url: str = "",
    request_payload: Optional[dict] = None,
    response_payload: Optional[dict] = None,
    status: str = "queued",
    error: Optional[str] = None,
    completed: bool = False,
) -> None:
    con = _sync_db()
    now = time.time()
    con.execute(
        """
        INSERT INTO ai_audit_log
            (id, app, channel, profile, model, base_url, request_payload, response_payload, status, error, created_at, completed_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(id) DO UPDATE SET
            response_payload = excluded.response_payload,
            status = excluded.status,
            error = excluded.error,
            completed_at = excluded.completed_at
        """,
        (
            audit_id,
            app_name,
            channel,
            profile,
            model,
            base_url,
            json.dumps(redact(request_payload or {}), ensure_ascii=False),
            json.dumps(redact(response_payload or {}), ensure_ascii=False),
            status,
            error,
            now,
            now if completed else None,
        ),
    )
    con.commit()
    con.close()


def mark_queue_error(queue_id: str, error: str) -> None:
    con = _sync_db()
    con.execute(
        "UPDATE chat_queue SET status = 'failed', error = ?, updated_at = ? WHERE id = ?",
        (error[:500], time.time(), queue_id),
    )
    con.commit()
    con.close()


def reschedule_queue(queue_id: str, delay_seconds: int = 5) -> Optional[dict]:
    from src.services.timeline_service import json_list, ts_to_iso
    con = _sync_db()
    try:
        next_flush = time.time() + max(1, delay_seconds)
        con.execute(
            "UPDATE chat_queue SET status = 'queued', flush_at = ?, updated_at = ? WHERE id = ?",
            (next_flush, time.time(), queue_id),
        )
        con.commit()
        row = con.execute("SELECT * FROM chat_queue WHERE id = ?", (queue_id,)).fetchone()
        if not row:
            return None
        now = time.time()
        status = row["status"]
        if status == "starting":
            status = "running"
        real_run_id = row["run_id"]
        queued_id = row["id"]
        messages = json_list(row["messages"])
        return {
            "run_id": real_run_id or queued_id,
            "queue_id": queued_id,
            "status": status,
            "session_id": row["session_id"] or queued_id,
            "profile": row["profile"],
            "response": "",
            "output": "",
            "events": [],
            "next_event": 0,
            "queued_message_count": len(messages),
            "queued_until": ts_to_iso(row["flush_at"]),
            "seconds_remaining": max(0, int(float(row["flush_at"]) - now)),
            "error": row["error"],
        }
    finally:
        con.close()


def mark_queue_final(run_id: Optional[str], status: str, error: str = "") -> None:
    if not run_id:
        return
    con = _sync_db()
    try:
        con.execute(
            "UPDATE chat_queue SET status = ?, error = ?, updated_at = ? WHERE run_id = ?",
            (status, error[:500], time.time(), run_id),
        )
        con.commit()
    finally:
        con.close()


def queue_row_to_status(row) -> dict:
    from src.services.timeline_service import json_list, ts_to_iso
    now = time.time()
    status = row["status"]
    if status == "starting":
        status = "running"
    real_run_id = row["run_id"]
    queued_id = row["id"]
    messages = json_list(row["messages"])
    return {
        "run_id": real_run_id or queued_id,
        "queue_id": queued_id,
        "status": status,
        "session_id": row["session_id"] or queued_id,
        "profile": row["profile"],
        "response": "",
        "output": "",
        "events": [],
        "next_event": 0,
        "queued_message_count": len(messages),
        "queued_until": ts_to_iso(row["flush_at"]),
        "seconds_remaining": max(0, int(float(row["flush_at"]) - now)),
        "error": row["error"],
    }
