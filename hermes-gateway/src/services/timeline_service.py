"""Timeline cache and persistence — shared state across threads."""
import json
import re
import sqlite3
import threading
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import config

# Global sync state
SYNC_DB = Path("/root/.hermes/state.db")
SYNC_STOP = threading.Event()
SYNC_WAKE = threading.Event()

# Run event capture
RUN_EVENTS: dict[str, list[dict]] = {}
RUN_EVENT_OFFSETS: dict[str, int] = {}
RUN_PARTIALS: dict[str, str] = {}
RUN_SEGMENTS: dict[str, int] = {}
RUN_AUDITS: dict[str, str] = {}
RUN_CONTEXTS: dict[str, dict] = {}
RUN_EVENT_LIMIT = 500
RUN_LOCK = threading.Lock()

# ── Deep context detection ────────────────────────────────────────────────────

DEEP_CONTEXT_KEYWORDS = re.compile(
    r"\b(project|projek|workspace|artifact|artefak|keuangan|finance|audit|debug|deploy|production|database|db|repo|kode|code|dokumen|proposal|campaign|konten|artikel|seo|laporan)\b",
    re.I,
)


def context_limit_for_message(text: str) -> int:
    if DEEP_CONTEXT_KEYWORDS.search(text):
        return 500
    if len(text) > 1600:
        return 240
    return 80


# ── Sync DB ────────────────────────────────────────────────────────────────────

def _sync_db() -> sqlite3.Connection:
    con = sqlite3.connect(SYNC_DB, timeout=10)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA journal_mode=WAL")
    return con


def init_sync_db() -> None:
    con = _sync_db()
    con.executescript(
        """
        CREATE TABLE IF NOT EXISTS timeline_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            profile TEXT NOT NULL,
            kind TEXT NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL DEFAULT '',
            metadata TEXT NOT NULL DEFAULT '{}',
            source TEXT NOT NULL,
            session_id TEXT,
            room_key TEXT,
            source_key TEXT NOT NULL UNIQUE,
            created_at REAL NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_timeline_profile_id ON timeline_events(profile, id);
        CREATE INDEX IF NOT EXISTS idx_timeline_session_id ON timeline_events(session_id, id);

        CREATE TABLE IF NOT EXISTS timeline_cursors (
            profile TEXT PRIMARY KEY,
            last_message_id INTEGER NOT NULL DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS timeline_backfills (
            profile TEXT PRIMARY KEY,
            completed_at REAL NOT NULL,
            last_message_id INTEGER NOT NULL DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS telegram_outbox (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            profile TEXT NOT NULL,
            text TEXT NOT NULL,
            dedupe_key TEXT NOT NULL UNIQUE,
            status TEXT NOT NULL DEFAULT 'pending',
            attempts INTEGER NOT NULL DEFAULT 0,
            next_attempt REAL NOT NULL DEFAULT 0,
            created_at REAL NOT NULL,
            delivered_at REAL,
            last_error TEXT
        );
        CREATE INDEX IF NOT EXISTS idx_outbox_pending ON telegram_outbox(status, next_attempt, id);

        CREATE TABLE IF NOT EXISTS approval_inbox (
            id TEXT PRIMARY KEY,
            profile TEXT NOT NULL,
            run_id TEXT NOT NULL,
            command TEXT NOT NULL,
            summary TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'pending',
            created_at REAL NOT NULL,
            resolved_at REAL,
            decision TEXT
        );
        CREATE INDEX IF NOT EXISTS idx_approval_status ON approval_inbox(status, created_at DESC);

        CREATE TABLE IF NOT EXISTS ai_audit_log (
            id TEXT PRIMARY KEY,
            app TEXT NOT NULL,
            channel TEXT NOT NULL,
            profile TEXT NOT NULL,
            model TEXT,
            base_url TEXT,
            request_payload TEXT NOT NULL DEFAULT '{}',
            response_payload TEXT NOT NULL DEFAULT '{}',
            status TEXT NOT NULL,
            error TEXT,
            created_at REAL NOT NULL,
            completed_at REAL
        );
        CREATE INDEX IF NOT EXISTS idx_ai_audit_profile_created ON ai_audit_log(profile, created_at DESC);

        CREATE TABLE IF NOT EXISTS chat_queue (
            id TEXT PRIMARY KEY,
            profile TEXT NOT NULL,
            channel TEXT NOT NULL,
            session_id TEXT,
            room_key TEXT,
            messages TEXT NOT NULL DEFAULT '[]',
            attachments TEXT NOT NULL DEFAULT '[]',
            status TEXT NOT NULL DEFAULT 'queued',
            last_message_at REAL NOT NULL,
            flush_at REAL NOT NULL,
            run_id TEXT,
            audit_id TEXT,
            error TEXT,
            created_at REAL NOT NULL,
            updated_at REAL NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_chat_queue_status_flush ON chat_queue(status, flush_at);
        CREATE INDEX IF NOT EXISTS idx_chat_queue_profile_channel ON chat_queue(profile, channel, updated_at DESC);
        """
    )
    con.execute("UPDATE telegram_outbox SET next_attempt = 0 WHERE status = 'pending'")
    _ensure_column(con, "timeline_events", "chat_id", "TEXT")
    _ensure_column(con, "timeline_events", "message_id", "TEXT")
    _ensure_column(con, "timeline_events", "message_thread_id", "TEXT")
    _ensure_column(con, "timeline_events", "topic_title", "TEXT")
    _ensure_column(con, "timeline_events", "room_key", "TEXT")
    _ensure_column(con, "timeline_events", "chat_type", "TEXT")
    _ensure_column(con, "telegram_outbox", "chat_id", "TEXT")
    _ensure_column(con, "telegram_outbox", "message_thread_id", "TEXT")
    _ensure_column(con, "telegram_outbox", "reply_to_message_id", "TEXT")
    _ensure_column(con, "chat_queue", "room_key", "TEXT")
    con.execute("CREATE INDEX IF NOT EXISTS idx_timeline_room_key ON timeline_events(room_key, id)")

    # topic_bindings for Telegram topics → office rooms
    con.execute("""
        CREATE TABLE IF NOT EXISTS topic_bindings (
            chat_id TEXT NOT NULL,
            message_thread_id TEXT NOT NULL,
            topic_title TEXT NOT NULL,
            room_key TEXT NOT NULL,
            chat_type TEXT NOT NULL DEFAULT 'private',
            PRIMARY KEY (chat_id, message_thread_id)
        )
    """)
    con.commit()
    con.close()


def _ensure_column(con: sqlite3.Connection, table: str, column: str, definition: str) -> None:
    existing = {row["name"] for row in con.execute(f"PRAGMA table_info({table})").fetchall()}
    if column not in existing:
        con.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")


# ── Helpers ────────────────────────────────────────────────────────────────────

def json_dict(raw: str) -> dict:
    try:
        value = json.loads(raw or "{}")
        return value if isinstance(value, dict) else {}
    except Exception:
        return {}


def json_list(raw: str) -> list:
    try:
        value = json.loads(raw or "[]")
        return value if isinstance(value, list) else []
    except Exception:
        return []


def string_value(*values) -> str:
    for value in values:
        if value is None:
            continue
        text = str(value).strip()
        if text:
            return text
    return ""


def metadata_string(metadata: Optional[dict], *keys: str) -> str:
    if not isinstance(metadata, dict):
        return ""
    for key in keys:
        value = metadata.get(key)
        if isinstance(value, dict):
            continue
        text = string_value(value)
        if text:
            return text
    return ""


def ts_to_iso(ts) -> str:
    if ts is None:
        return ""
    try:
        return datetime.fromtimestamp(float(ts), tz=timezone.utc).isoformat()
    except Exception:
        return str(ts)


# ── Run event capture ──────────────────────────────────────────────────────────

def append_run_event(run_id: str, event: dict) -> None:
    with RUN_LOCK:
        events = RUN_EVENTS.setdefault(run_id, [])
        offset = RUN_EVENT_OFFSETS.setdefault(run_id, 0)
        events.append(event)
        if len(events) > RUN_EVENT_LIMIT:
            RUN_EVENTS[run_id] = events[-RUN_EVENT_LIMIT:]
            RUN_EVENT_OFFSETS[run_id] = offset + len(events) - RUN_EVENT_LIMIT


def append_run_delta(run_id: str, delta: str) -> None:
    with RUN_LOCK:
        RUN_PARTIALS[run_id] = RUN_PARTIALS.get(run_id, "") + delta


def get_run_events(run_id: str, after: int = 0) -> tuple[list[dict], int]:
    with RUN_LOCK:
        events = RUN_EVENTS.get(run_id, [])
        offset = RUN_EVENT_OFFSETS.get(run_id, 0)
    start = max(0, after - offset)
    return list(events[start:]), len(events)


def run_context(run_id: str) -> dict:
    with RUN_LOCK:
        return dict(RUN_CONTEXTS.get(run_id, {}))


def set_run_context(run_id: str, ctx: dict) -> None:
    with RUN_LOCK:
        RUN_CONTEXTS[run_id] = ctx


def audit_for_run(run_id: str) -> Optional[str]:
    with RUN_LOCK:
        return RUN_AUDITS.get(run_id)


def set_run_audit(run_id: str, audit_id: str) -> None:
    with RUN_LOCK:
        RUN_AUDITS[run_id] = audit_id


def clear_run(run_id: str) -> None:
    with RUN_LOCK:
        RUN_EVENTS.pop(run_id, None)
        RUN_EVENT_OFFSETS.pop(run_id, None)
        RUN_PARTIALS.pop(run_id, None)
        RUN_SEGMENTS.pop(run_id, None)
        RUN_AUDITS.pop(run_id, None)
        RUN_CONTEXTS.pop(run_id, None)


# ── Sync worker ────────────────────────────────────────────────────────────────

def _sync_worker() -> None:
    """Background worker: ingest timeline events from all profiles."""
    while not SYNC_STOP.is_set():
        try:
            # Import here to avoid circular imports at module load time
            from src.services.profile_service import _iter_agent_profiles
            from src.api.chat import _ensure_profile_timeline, _drain_telegram_outbox
            for profile, _ in _iter_agent_profiles():
                _ensure_profile_timeline(profile)
            _drain_telegram_outbox()
        except Exception:
            pass
        SYNC_WAKE.wait(0.8)
        SYNC_WAKE.clear()
