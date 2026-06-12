import base64
import json
import os
import re
import sqlite3
import subprocess
import threading
import time
import urllib.error
import urllib.request
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import yaml
from fastapi import Depends, FastAPI, HTTPException, Security
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import APIKeyHeader, HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field

app = FastAPI(title="Hermes Office API", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

GATEWAY_TOKEN = os.getenv("HERMES_GATEWAY_TOKEN", "change-me")
HERMES_BIN = os.getenv("HERMES_BIN", "/usr/local/bin/hermes")
HERMES_TIMEOUT_SECONDS = int(os.getenv("HERMES_TIMEOUT_SECONDS", "900"))
HERMES_MULTI_READ_SECONDS = int(os.getenv("HERMES_MULTI_READ_SECONDS", "30"))
HERMES_HOME = Path("/root/.hermes")
PROFILES_DIR = Path("/root/.hermes/profiles")
API_SERVER_PORTS = {
    "nara": 8646,
    "rafi": 8643,
    "sena": 8644,
    "dimas": 8645,
    "mika": 8647,
    "raka": 8648,
    "tara": 8649,
}
LEGACY_PROFILE_ALIASES = {
    "friday": "nara",
    "tony": "rafi",
    "banner": "dimas",
    "vision": "sena",
    "default": "nara",
    "manager": "nara",
}
LEGACY_PROFILE_DIRS = {
    "nara": "friday",
    "manager": "friday",
    "rafi": "tony",
    "dimas": "banner",
    "sena": "vision",
}
ROUTER_INTERNAL_BASE_URL = os.getenv("ROUTER_INTERNAL_BASE_URL", os.getenv("NINE_ROUTER_INTERNAL_BASE_URL", "http://127.0.0.1:20128/v1")).rstrip("/")
ROUTER_EXTERNAL_BASE_URL = os.getenv("ROUTER_EXTERNAL_BASE_URL", os.getenv("NINE_ROUTER_EXTERNAL_BASE_URL", "http://9router.kantorteman.my.id/")).rstrip("/")
ROUTER_KEY_FILES = [
    Path("/home/kevin/.9router/auth/hermes-router-key"),
    Path("/root/.9router/auth/hermes-router-key"),
]
DEEP_CONTEXT_KEYWORDS = re.compile(
    r"\b(project|projek|workspace|artifact|artefak|keuangan|finance|audit|debug|deploy|production|database|db|repo|kode|code|dokumen|proposal|campaign|konten|artikel|seo|laporan)\b",
    re.I,
)
ACTIVE_RUNS: dict[str, str] = {}
MIRRORED_RUNS: set[str] = set()
RUN_EVENTS: dict[str, list[dict]] = {}
RUN_EVENT_OFFSETS: dict[str, int] = {}
RUN_PARTIALS: dict[str, str] = {}
RUN_SEGMENTS: dict[str, int] = {}
RUN_AUDITS: dict[str, str] = {}
QUEUED_CHATS: dict[str, dict] = {}
QUEUED_RUNS: dict[str, dict] = {}
RUN_LOCK = threading.Lock()
RUN_EVENT_LIMIT = 500
SYNC_DB = Path("/root/.hermes/state.db")
SYNC_STOP = threading.Event()
SYNC_WAKE = threading.Event()

OFFICE_EMAIL = os.getenv("OFFICE_EMAIL", "")
OFFICE_PASSWORD = os.getenv("OFFICE_PASSWORD", "")
OFFICE_NAME = os.getenv("OFFICE_NAME", "Admin")

PROFILE_RE = re.compile(r"^[a-z][a-z0-9_-]{1,30}$")

api_key_header = APIKeyHeader(name="X-Gateway-Token", auto_error=False)
bearer_scheme = HTTPBearer(auto_error=False)


def verify_auth(
    key: Optional[str] = Security(api_key_header),
    bearer: Optional[HTTPAuthorizationCredentials] = Security(bearer_scheme),
) -> str:
    token = key or (bearer.credentials if bearer else None)
    if token and token == GATEWAY_TOKEN:
        return token
    raise HTTPException(status_code=401, detail="Unauthorized")


def validate_profile(profile: str) -> str:
    if not PROFILE_RE.match(profile):
        raise HTTPException(status_code=400, detail="Invalid profile name")
    return profile


PROFILE_ALIASES = LEGACY_PROFILE_ALIASES


def resolve_profile(profile: str) -> str:
    profile = validate_profile(profile)
    return PROFILE_ALIASES.get(profile, profile)


# ── helpers ──────────────────────────────────────────────────────────────────

def _profile_dir(profile: str) -> Path:
    if profile == "default":
        return HERMES_HOME
    return PROFILES_DIR / profile


def _canonical_profile(profile: str) -> str:
    return LEGACY_PROFILE_ALIASES.get(profile, profile)


def _existing_profile_dir(profile: str) -> Path:
    direct = _profile_dir(profile)
    if direct.exists():
        return direct
    legacy_name = LEGACY_PROFILE_DIRS.get(profile)
    if legacy_name:
        legacy_dir = _profile_dir(legacy_name)
        if legacy_dir.exists():
            return legacy_dir
    for legacy, current in LEGACY_PROFILE_ALIASES.items():
        if current == profile:
            legacy_dir = _profile_dir(legacy)
            if legacy_dir.exists():
                return legacy_dir
    return direct


def _runtime_profile(profile: str) -> str:
    """Return the installed Hermes profile name until legacy dirs are renamed."""
    profile = resolve_profile(profile)
    if _profile_dir(profile).exists():
        return profile
    legacy_name = LEGACY_PROFILE_DIRS.get(profile)
    if legacy_name and _profile_dir(legacy_name).exists():
        return legacy_name
    for legacy, current in LEGACY_PROFILE_ALIASES.items():
        if current == profile and _profile_dir(legacy).exists():
            return legacy
    return profile


def _iter_agent_profiles() -> list[tuple[str, Path]]:
    profiles: dict[str, Path] = {}
    for profile in API_SERVER_PORTS:
        profiles[profile] = _existing_profile_dir(profile)
    if PROFILES_DIR.exists():
        for p in PROFILES_DIR.iterdir():
            if not p.is_dir():
                continue
            current = _canonical_profile(p.name)
            profiles.setdefault(current, _existing_profile_dir(current))
    if HERMES_HOME.exists():
        profiles.setdefault(_canonical_profile("default"), _existing_profile_dir(_canonical_profile("default")))
    ordered = []
    for profile in [*API_SERVER_PORTS.keys(), *sorted(profiles.keys())]:
        if profile in profiles and profile not in {item[0] for item in ordered}:
            ordered.append((profile, profiles[profile]))
    return ordered


def _profile_display_name(profile: str, cfg: Optional[dict] = None) -> str:
    cfg = cfg or _read_config(_existing_profile_dir(profile))
    value = cfg.get("display_name") if isinstance(cfg, dict) else ""
    if value:
        return str(value)
    names = {
        "manager": "Manager",
        "nara": "Nara",
        "rafi": "Rafi",
        "dimas": "Dimas",
        "sena": "Sena",
        "mika": "Mika",
        "raka": "Raka",
        "tara": "Tara",
    }
    return names.get(profile, profile.capitalize())


def _hermes_cmd(profile: str, *args: str) -> list[str]:
    runtime_profile = _runtime_profile(profile)
    command = [HERMES_BIN]
    if runtime_profile != "default":
        command += ["--profile", runtime_profile]
    return command + list(args)


def _db_path(profile: str) -> Optional[str]:
    p = _existing_profile_dir(profile) / "state.db"
    return str(p) if p.exists() else None


def _sync_db() -> sqlite3.Connection:
    con = sqlite3.connect(SYNC_DB, timeout=10)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA journal_mode=WAL")
    return con


def _init_sync_db() -> None:
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
            source_key TEXT NOT NULL UNIQUE,
            created_at REAL NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_timeline_profile_id ON timeline_events(profile, id);

        CREATE TABLE IF NOT EXISTS timeline_cursors (
            profile TEXT PRIMARY KEY,
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
    con.commit()
    con.close()


def _json_dict(raw: str) -> dict:
    try:
        value = json.loads(raw or "{}")
        return value if isinstance(value, dict) else {}
    except Exception:
        return {}


SENSITIVE_KEYS = re.compile(r"(key|token|secret|password|authorization|cookie)", re.I)


def _redact(value):
    if isinstance(value, dict):
        return {k: ("<redacted>" if SENSITIVE_KEYS.search(str(k)) else _redact(v)) for k, v in value.items()}
    if isinstance(value, list):
        return [_redact(item) for item in value]
    if isinstance(value, str) and len(value) > 16 and re.search(r"(sk-|Bearer |bot[0-9]|api[_-]?key)", value, re.I):
        return "<redacted>"
    return value


def _router_base_url(for_external: bool = False) -> str:
    base = ROUTER_EXTERNAL_BASE_URL if for_external else ROUTER_INTERNAL_BASE_URL
    return base.rstrip("/")


def _router_v1_url(for_external: bool = False) -> str:
    base = _router_base_url(for_external)
    return base if base.endswith("/v1") else f"{base}/v1"


def _router_models_url() -> str:
    return f"{_router_v1_url(False)}/models"


def _router_default_api_key() -> str:
    env_value = (
        os.getenv("ROUTER_API_KEY")
        or os.getenv("NINE_ROUTER_API_KEY")
        or os.getenv("OPENAI_API_KEY")
        or ""
    ).strip()
    if env_value:
        return env_value
    for key_file in ROUTER_KEY_FILES:
        try:
            if key_file.exists():
                value = key_file.read_text(encoding="utf-8").strip()
                if value:
                    return value
        except Exception:
            continue
    return ""


def _router_headers() -> dict[str, str]:
    headers = {"Accept": "application/json"}
    api_key = _router_default_api_key()
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    return headers


def _fetch_router_models() -> list[dict]:
    request = urllib.request.Request(_router_models_url(), headers=_router_headers())
    try:
        with urllib.request.urlopen(request, timeout=12) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"9router model registry unavailable: {exc}")
    raw_models = payload.get("data", payload) if isinstance(payload, dict) else payload
    if not isinstance(raw_models, list):
        raise HTTPException(status_code=502, detail="9router model registry returned invalid data")
    models = []
    for item in raw_models:
        if isinstance(item, str):
            model_id = item
            owned_by = "unknown"
            raw = {"id": item}
        elif isinstance(item, dict):
            model_id = str(item.get("id") or item.get("name") or "").strip()
            owned_by = str(item.get("owned_by") or item.get("provider") or "unknown")
            raw = item
        else:
            continue
        if not model_id:
            continue
        models.append({
            "id": model_id,
            "name": str(raw.get("name") or model_id),
            "owned_by": owned_by,
            "type": "combo" if model_id.startswith("combo-") or owned_by == "combo" else "model",
            "raw": _redact(raw),
        })
    return models


def _read_agent_ai_config(profile: str) -> dict:
    profile = resolve_profile(profile)
    profile_dir = _existing_profile_dir(profile)
    cfg = _read_config(profile_dir)
    model_section = cfg.get("model", {}) if isinstance(cfg.get("model"), dict) else {}
    env_values = _load_profile_env(profile)
    base_url = (
        model_section.get("base_url")
        or env_values.get("OPENAI_BASE_URL")
        or env_values.get("ROUTER_BASE_URL")
        or _router_v1_url(False)
    )
    model = (
        model_section.get("default")
        or env_values.get("API_SERVER_MODEL_NAME")
        or env_values.get("OPENAI_MODEL")
        or ""
    )
    api_key_present = bool(model_section.get("api_key") or env_values.get("OPENAI_API_KEY") or _router_default_api_key())
    return {
        "profile": profile,
        "runtime_profile": _runtime_profile(profile),
        "display_name": _profile_display_name(profile, cfg),
        "model": str(model or ""),
        "combo": str(model or "") if str(model or "").startswith("combo-") else "",
        "base_url": str(base_url or ""),
        "api_key_configured": api_key_present,
        "config_path": str(profile_dir / "config.yaml"),
        "state": "online" if (profile_dir / "state.db").exists() else "offline",
    }


def _write_agent_ai_config(profile: str, updates: dict) -> dict:
    profile = resolve_profile(profile)
    profile_dir = _existing_profile_dir(profile)
    if not profile_dir.exists():
        raise HTTPException(status_code=404, detail=f"Profile '{profile}' not found")
    model = str(updates.get("model") or updates.get("combo") or "").strip()
    base_url = str(updates.get("base_url") or "").strip()
    api_key = str(updates.get("api_key") or "").strip()
    config_updates = {}
    if model:
        config_updates["model"] = model
    if base_url:
        config_updates["base_url"] = base_url.rstrip("/")
    if api_key:
        config_updates["api_key"] = api_key
    if config_updates:
        _write_config(profile_dir, config_updates)
    env_updates = {}
    if model:
        env_updates["API_SERVER_MODEL_NAME"] = model
        env_updates["OPENAI_MODEL"] = model
    if base_url:
        env_updates["OPENAI_BASE_URL"] = base_url.rstrip("/")
        env_updates["ROUTER_BASE_URL"] = base_url.rstrip("/")
    if api_key:
        env_updates["OPENAI_API_KEY"] = api_key
        env_updates["ROUTER_API_KEY"] = api_key
    if env_updates:
        _write_env(profile_dir, env_updates)
    return _read_agent_ai_config(profile)


def _service_name_for_profile(profile: str) -> str:
    runtime = _runtime_profile(profile)
    return f"hermes-gateway-{runtime}.service"


def _restart_agent_service(profile: str) -> dict:
    profile = resolve_profile(profile)
    service = _service_name_for_profile(profile)
    result = subprocess.run(
        ["systemctl", "--user", "restart", service],
        capture_output=True,
        text=True,
        timeout=30,
    )
    return {
        "profile": profile,
        "service": service,
        "ok": result.returncode == 0,
        "error": (result.stderr or result.stdout).strip()[:300] if result.returncode != 0 else "",
    }


def _queue_wait_seconds() -> int:
    return max(0, int(HERMES_MULTI_READ_SECONDS))


def _strip_now_command(text: str) -> tuple[str, bool]:
    lines = []
    flush = False
    for line in text.splitlines():
        if line.strip().lower() == ".now":
            flush = True
            continue
        lines.append(line)
    return "\n".join(lines).strip(), flush


def _queue_row_to_status(row: sqlite3.Row) -> dict:
    now = time.time()
    status = row["status"]
    if status == "starting":
        status = "running"
    real_run_id = row["run_id"]
    queued_id = row["id"]
    messages = _json_list(row["messages"])
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
        "queued_until": _ts_to_iso(row["flush_at"]),
        "seconds_remaining": max(0, int(float(row["flush_at"]) - now)),
        "error": row["error"],
    }


def _json_list(raw: str) -> list:
    try:
        value = json.loads(raw or "[]")
        return value if isinstance(value, list) else []
    except Exception:
        return []


def _context_limit_for_message(text: str) -> int:
    if DEEP_CONTEXT_KEYWORDS.search(text):
        return 500
    if len(text) > 1600:
        return 240
    return 80


def _combined_queue_message(messages: list[dict]) -> str:
    cleaned = [str(item.get("text") or "").strip() for item in messages if str(item.get("text") or "").strip()]
    if not cleaned:
        return ""
    if len(cleaned) == 1:
        return cleaned[0]
    return "\n\n".join(f"[Pesan {idx + 1}]\n{text}" for idx, text in enumerate(cleaned))


def _enqueue_chat(profile: str, req: "ChatRequest") -> dict:
    profile = resolve_profile(profile)
    full_message = req.message or ""
    attachments = list(req.attachments or [])
    cleaned_message, flush_now = _strip_now_command(full_message)
    now = time.time()
    flush_at = now if flush_now or _queue_wait_seconds() == 0 else now + _queue_wait_seconds()
    if not cleaned_message.strip() and not attachments:
        if flush_now:
            con = _sync_db()
            try:
                row = con.execute(
                    """
                    SELECT * FROM chat_queue
                    WHERE profile = ? AND channel = 'web' AND status = 'queued'
                    ORDER BY updated_at DESC LIMIT 1
                    """,
                    (profile,),
                ).fetchone()
                if not row:
                    raise HTTPException(status_code=400, detail="No queued message to flush")
                con.execute(
                    "UPDATE chat_queue SET flush_at = ?, updated_at = ? WHERE id = ?",
                    (now, now, row["id"]),
                )
                con.commit()
                row = con.execute("SELECT * FROM chat_queue WHERE id = ?", (row["id"],)).fetchone()
                return _queue_row_to_status(row)
            finally:
                con.close()
        raise HTTPException(status_code=400, detail="Message cannot be empty")
    message_entry = {
        "text": cleaned_message,
        "created_at": now,
        "attachment_count": len(attachments),
    }
    pending_audit: Optional[tuple[str, int, int]] = None
    con = _sync_db()
    try:
        row = con.execute(
            """
            SELECT * FROM chat_queue
            WHERE profile = ? AND channel = 'web' AND status = 'queued'
            ORDER BY updated_at DESC LIMIT 1
            """,
            (profile,),
        ).fetchone()
        if row:
            queue_id = row["id"]
            messages = _json_list(row["messages"])
            queued_attachments = _json_list(row["attachments"])
            messages.append(message_entry)
            queued_attachments.extend(attachments)
            con.execute(
                """
                UPDATE chat_queue
                SET messages = ?, attachments = ?, session_id = COALESCE(?, session_id),
                    last_message_at = ?, flush_at = ?, updated_at = ?
                WHERE id = ?
                """,
                (
                    json.dumps(messages, ensure_ascii=False),
                    json.dumps(queued_attachments, ensure_ascii=False),
                    req.session_id,
                    now,
                    flush_at,
                    now,
                    queue_id,
                ),
            )
        else:
            queue_id = f"queue-{uuid.uuid4().hex}"
            audit_id = f"audit-{uuid.uuid4().hex}"
            con.execute(
                """
                INSERT INTO chat_queue
                    (id, profile, channel, session_id, messages, attachments, status,
                     last_message_at, flush_at, audit_id, created_at, updated_at)
                VALUES (?, ?, 'web', ?, ?, ?, 'queued', ?, ?, ?, ?, ?)
                """,
                (
                    queue_id,
                    profile,
                    req.session_id,
                    json.dumps([message_entry], ensure_ascii=False),
                    json.dumps(attachments, ensure_ascii=False),
                    now,
                    flush_at,
                    audit_id,
                    now,
                    now,
                ),
            )
            pending_audit = (audit_id, 1, len(attachments))
        con.commit()
        row = con.execute("SELECT * FROM chat_queue WHERE id = ?", (queue_id,)).fetchone()
        status = _queue_row_to_status(row)
    finally:
        con.close()
    if pending_audit:
        audit_id, message_count, attachment_count = pending_audit
        _audit_ai_request(
            audit_id,
            app_name="office",
            channel="web",
            profile=profile,
            request_payload={"queued": True, "message_count": message_count, "attachment_count": attachment_count},
            status="queued",
        )
    return status


def _mark_queue_error(queue_id: str, error: str) -> None:
    con = _sync_db()
    con.execute(
        "UPDATE chat_queue SET status = 'failed', error = ?, updated_at = ? WHERE id = ?",
        (error[:500], time.time(), queue_id),
    )
    con.commit()
    con.close()


def _reschedule_queue(queue_id: str, delay_seconds: int = 5) -> Optional[dict]:
    con = _sync_db()
    try:
        next_flush = time.time() + max(1, delay_seconds)
        con.execute(
            "UPDATE chat_queue SET status = 'queued', flush_at = ?, updated_at = ? WHERE id = ?",
            (next_flush, time.time(), queue_id),
        )
        con.commit()
        row = con.execute("SELECT * FROM chat_queue WHERE id = ?", (queue_id,)).fetchone()
        return _queue_row_to_status(row) if row else None
    finally:
        con.close()


def _start_chat_run_now(
    profile: str,
    full_message: str,
    *,
    session_id: Optional[str],
    source_key: str,
    audit_id: str,
    channel: str = "web",
    mirror_user_to_telegram: bool = True,
) -> dict:
    profile = resolve_profile(profile)
    with RUN_LOCK:
        active_run = ACTIVE_RUNS.get(profile)
    if active_run:
        active = _api_request(profile, f"/v1/runs/{active_run}")
        if active.get("status") not in {"completed", "failed", "cancelled"}:
            raise HTTPException(status_code=409, detail="Agent masih mengerjakan pesan sebelumnya")

    target_session = _get_latest_session(profile) or session_id
    context_limit = _context_limit_for_message(full_message)
    payload = {
        "input": full_message,
        "session_id": target_session,
        "conversation_history": _get_timeline_history(profile, limit=context_limit, session_id=None),
    }
    config = _read_agent_ai_config(profile)
    _audit_ai_request(
        audit_id,
        app_name="office",
        channel=channel,
        profile=profile,
        model=config.get("model", ""),
        base_url=config.get("base_url", ""),
        request_payload={"input_preview": full_message[:500], "context_limit": context_limit, "session_id": target_session},
        status="running",
    )
    run = _api_request(profile, "/v1/runs", method="POST", payload=payload)
    run_id = run.get("run_id")
    if not run_id:
        _audit_ai_request(
            audit_id,
            app_name="office",
            channel=channel,
            profile=profile,
            model=config.get("model", ""),
            base_url=config.get("base_url", ""),
            response_payload=run,
            status="failed",
            error="Hermes did not return a run id",
            completed=True,
        )
        raise HTTPException(status_code=502, detail="Hermes did not return a run id")
    with RUN_LOCK:
        ACTIVE_RUNS[profile] = run_id
        RUN_AUDITS[run_id] = audit_id
    created_at = time.time()
    _append_timeline(
        profile,
        "message",
        "user",
        full_message.strip(),
        channel,
        source_key,
        session_id=target_session,
        dedupe_content=True,
        created_at=created_at,
    )
    _persist_web_message_to_profile(
        profile,
        "user",
        full_message.strip(),
        source_key,
        session_id=target_session,
        created_at=created_at,
    )
    if mirror_user_to_telegram:
        _queue_telegram(profile, f"[Web · You]\n{full_message.strip()}", source_key)
    _start_run_event_capture(profile, run_id)
    return {**run, "session_id": target_session or run_id, "profile": profile}


def _start_queued_chat(row: sqlite3.Row) -> dict:
    queue_id = row["id"]
    con = _sync_db()
    try:
        cur = con.execute(
            "UPDATE chat_queue SET status = 'starting', updated_at = ? WHERE id = ? AND status = 'queued'",
            (time.time(), queue_id),
        )
        con.commit()
        if cur.rowcount != 1:
            current = con.execute("SELECT * FROM chat_queue WHERE id = ?", (queue_id,)).fetchone()
            return _queue_row_to_status(current) if current else {"run_id": queue_id, "status": "failed", "error": "Queue not found"}
    finally:
        con.close()
    profile = row["profile"]
    messages = _json_list(row["messages"])
    attachments = _json_list(row["attachments"])
    full_message = _combined_queue_message(messages)
    for att in attachments:
        full_message += _attachment_text(att)
    if not full_message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty")
    audit_id = row["audit_id"] or f"audit-{uuid.uuid4().hex}"
    run = _start_chat_run_now(
        profile,
        full_message,
        session_id=row["session_id"],
        source_key=f"queue-user:{queue_id}",
        audit_id=audit_id,
        channel=row["channel"] or "web",
        mirror_user_to_telegram=True,
    )
    con = _sync_db()
    con.execute(
        """
        UPDATE chat_queue
        SET status = 'running', run_id = ?, audit_id = ?, updated_at = ?
        WHERE id = ?
        """,
        (run["run_id"], audit_id, time.time(), queue_id),
    )
    con.commit()
    con.close()
    return run


def _queue_or_run_status(profile: str, run_id: str, after: int = 0) -> Optional[dict]:
    con = _sync_db()
    row = con.execute(
        "SELECT * FROM chat_queue WHERE id = ? OR run_id = ?",
        (run_id, run_id),
    ).fetchone()
    con.close()
    if not row:
        return None
    if row["profile"] != profile:
        raise HTTPException(status_code=404, detail="Run not found for profile")
    if row["status"] == "queued":
        if time.time() < float(row["flush_at"]):
            return _queue_row_to_status(row)
        try:
            return _start_queued_chat(row)
        except HTTPException as exc:
            if exc.status_code == 409:
                rescheduled = _reschedule_queue(row["id"])
                if rescheduled:
                    return rescheduled
            _mark_queue_error(row["id"], str(exc.detail))
            raise
        except Exception as exc:
            _mark_queue_error(row["id"], str(exc))
            raise HTTPException(status_code=500, detail=str(exc)[:300])
    if row["status"] == "failed":
        return _queue_row_to_status(row)
    if row["status"] == "cancelled":
        return _queue_row_to_status(row)
    if row["status"] in {"starting", "running"} and not row["run_id"]:
        return _queue_row_to_status(row)
    if row["run_id"] and row["run_id"] != run_id:
        return {"redirect_run_id": row["run_id"]}
    return None


def _audit_ai_request(
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
            json.dumps(_redact(request_payload or {}), ensure_ascii=False),
            json.dumps(_redact(response_payload or {}), ensure_ascii=False),
            status,
            error,
            now,
            now if completed else None,
        ),
    )
    con.commit()
    con.close()


def _append_timeline(
    profile: str,
    kind: str,
    role: str,
    content: str,
    source: str,
    source_key: str,
    *,
    session_id: Optional[str] = None,
    metadata: Optional[dict] = None,
    dedupe_content: bool = False,
    dedupe_across_sessions: bool = False,
    created_at: Optional[float] = None,
) -> Optional[int]:
    created_at = float(created_at or time.time())
    con = _sync_db()
    try:
        if dedupe_content and content:
            session_clause = "" if dedupe_across_sessions else """
                  AND COALESCE(session_id, '') = COALESCE(?, '')
            """
            params = [profile, role, content]
            if not dedupe_across_sessions:
                params.append(session_id)
            params.extend([created_at - 15, created_at + 15])
            row = con.execute(
                f"""
                SELECT id FROM timeline_events
                WHERE profile = ? AND role = ? AND content = ?
                  {session_clause}
                  AND created_at BETWEEN ? AND ?
                ORDER BY id DESC LIMIT 1
                """,
                params,
            ).fetchone()
            if row:
                return int(row["id"])
        cur = con.execute(
            """
            INSERT OR IGNORE INTO timeline_events
                (profile, kind, role, content, metadata, source, session_id, source_key, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                profile, kind, role, content, json.dumps(metadata or {}, ensure_ascii=False),
                source, session_id, source_key, created_at,
            ),
        )
        con.commit()
        if cur.lastrowid:
            return int(cur.lastrowid)
        row = con.execute("SELECT id FROM timeline_events WHERE source_key = ?", (source_key,)).fetchone()
        return int(row["id"]) if row else None
    finally:
        con.close()


def _serialize_timeline(row: sqlite3.Row) -> dict:
    return {
        "id": int(row["id"]),
        "profile": row["profile"],
        "kind": row["kind"],
        "role": row["role"],
        "content": row["content"],
        "metadata": _json_dict(row["metadata"]),
        "source": row["source"],
        "session_id": row["session_id"],
        "created_at": _ts_to_iso(row["created_at"]),
    }


def _profiles_for_sync() -> list[str]:
    return [profile for profile, _ in _iter_agent_profiles()]


def _telegram_binding(profile: str) -> Optional[dict]:
    sessions_file = _existing_profile_dir(profile) / "sessions" / "sessions.json"
    if not sessions_file.exists():
        return None
    try:
        entries = json.loads(sessions_file.read_text(encoding="utf-8")).values()
        matches = []
        for entry in entries:
            origin = entry.get("origin") or {}
            if (origin.get("platform") or entry.get("platform")) != "telegram":
                continue
            if not origin.get("chat_id") or not entry.get("session_id"):
                continue
            matches.append(entry)
        return max(matches, key=lambda entry: entry.get("updated_at", "")) if matches else None
    except Exception:
        return None


def _get_latest_session(profile: str) -> Optional[str]:
    binding = _telegram_binding(profile)
    if binding:
        return binding["session_id"]
    db = _db_path(profile)
    if not db:
        return None
    try:
        con = sqlite3.connect(db)
        row = con.execute(
            "SELECT id FROM sessions WHERE source != 'cron' ORDER BY started_at DESC LIMIT 1"
        ).fetchone()
        con.close()
        return row[0] if row else None
    except Exception:
        return None


def _ts_to_iso(ts) -> str:
    if ts is None:
        return ""
    try:
        return datetime.fromtimestamp(float(ts), tz=timezone.utc).isoformat()
    except Exception:
        return str(ts)


def _get_session_history(profile: str, session_id: str, limit: Optional[int] = 40) -> list:
    db = _db_path(profile)
    if not db:
        return []
    try:
        con = sqlite3.connect(db)
        limit_clause = "LIMIT ?" if limit else ""
        params = (session_id, limit) if limit else (session_id,)
        rows = con.execute(
            f"""
            SELECT m.role, m.content, m.timestamp
            FROM messages m
            WHERE m.session_id = ?
              AND m.role IN ('user','assistant')
              AND m.content IS NOT NULL AND m.content != ''
            ORDER BY m.timestamp DESC
            {limit_clause}
            """,
            params,
        ).fetchall()
        con.close()
        result = [{"role": r[0], "content": r[1], "created_at": _ts_to_iso(r[2])} for r in rows]
        result.reverse()
        return result
    except Exception:
        return []


def _get_timeline_history(profile: str, limit: int = 500, session_id: Optional[str] = None) -> list:
    limit = max(1, min(int(limit or 500), 1000))
    try:
        _ingest_profile_messages(profile)
    except Exception:
        pass
    con = _sync_db()
    try:
        params: list = [profile, "message", "user", "assistant", ""]
        session_clause = ""
        if session_id:
            session_clause = "AND (session_id = ? OR session_id IS NULL)"
            params.append(session_id)
        params.append(limit)
        rows = con.execute(
            f"""
            SELECT role, content, created_at, id
            FROM timeline_events
            WHERE profile = ?
              AND kind = ?
              AND role IN (?, ?)
              AND content IS NOT NULL AND content != ?
              {session_clause}
            ORDER BY created_at DESC, id DESC
            LIMIT ?
            """,
            params,
        ).fetchall()
    finally:
        con.close()
    result = [
        {"role": row["role"], "content": row["content"], "created_at": _ts_to_iso(row["created_at"])}
        for row in rows
    ]
    result.reverse()
    return result


def _persist_web_message_to_profile(
    profile: str,
    role: str,
    content: str,
    source_key: str,
    *,
    session_id: Optional[str] = None,
    created_at: Optional[float] = None,
) -> Optional[int]:
    if role not in {"user", "assistant"} or not content.strip():
        return None
    db = _db_path(profile)
    target_session = _get_latest_session(profile) or session_id
    if not db or not target_session:
        return None
    created_at = float(created_at or time.time())
    platform_message_id = f"office:{source_key}"
    try:
        con = sqlite3.connect(db, timeout=10)
        con.row_factory = sqlite3.Row
        session = con.execute("SELECT id FROM sessions WHERE id = ?", (target_session,)).fetchone()
        if not session:
            con.close()
            return None
        cur = con.execute(
            """
            INSERT OR IGNORE INTO messages
                (session_id, role, content, timestamp, platform_message_id, observed)
            VALUES (?, ?, ?, ?, ?, 1)
            """,
            (target_session, role, content.strip(), created_at, platform_message_id),
        )
        message_id = cur.lastrowid if cur.rowcount else None
        if cur.rowcount:
            con.execute(
                """
                UPDATE sessions
                SET message_count = COALESCE(message_count, 0) + 1
                WHERE id = ?
                """,
                (target_session,),
            )
        con.commit()
        con.close()
        return int(message_id) if message_id else None
    except Exception:
        return None


def _get_history(profile: str, limit: int = 500) -> list:
    timeline = _get_timeline_history(profile, limit)
    if timeline:
        return timeline
    session_id = _get_latest_session(profile)
    return _get_session_history(profile, session_id, limit) if session_id else []


def _api_server_url(profile: str, path: str) -> str:
    port = API_SERVER_PORTS.get(profile)
    if not port:
        raise HTTPException(status_code=503, detail=f"Async chat is not configured for {profile}")
    return f"http://127.0.0.1:{port}{path}"


def _api_request(profile: str, path: str, method: str = "GET", payload: Optional[dict] = None) -> dict:
    body = json.dumps(payload).encode("utf-8") if payload is not None else None
    request = urllib.request.Request(
        _api_server_url(profile, path),
        data=body,
        method=method,
        headers={
            "Authorization": f"Bearer {GATEWAY_TOKEN}",
            "Content-Type": "application/json",
            "X-Hermes-Session-Key": f"office-web:{profile}",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise HTTPException(status_code=exc.code, detail=detail[:500])
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Hermes gateway unavailable: {exc}")


def _append_run_event(run_id: str, event: dict) -> None:
    with RUN_LOCK:
        events = RUN_EVENTS.setdefault(run_id, [])
        offset = RUN_EVENT_OFFSETS.setdefault(run_id, 0)
        events.append(event)
        if len(events) > RUN_EVENT_LIMIT:
            RUN_EVENTS[run_id] = events[-RUN_EVENT_LIMIT:]
            RUN_EVENT_OFFSETS[run_id] = offset + len(events) - RUN_EVENT_LIMIT


def _timeline_event_from_run(profile: str, run_id: str, event: dict) -> Optional[int]:
    event_type = event.get("event", "")
    if event_type in {"message.delta", "reasoning.available", "run.completed"}:
        return None
    metadata = dict(event)
    metadata.pop("event", None)
    metadata.pop("run_id", None)
    content = (
        event.get("preview")
        or event.get("text")
        or event.get("output")
        or event.get("description")
        or event.get("choice")
        or event_type
    )
    kind = "activity"
    if event_type == "tool.completed":
        kind = "terminal"
    elif event_type == "approval.request":
        kind = "approval"
    timeline_id = _append_timeline(
        profile,
        kind,
        "assistant",
        str(content or ""),
        "web-run",
        f"run-event:{run_id}:{event_type}:{event.get('timestamp', time.time())}",
        session_id=event.get("session_id"),
        metadata={"event": event_type, "run_id": run_id, **metadata},
    )
    if event_type == "approval.request" and timeline_id:
        approval_id = f"approval:{run_id}:{timeline_id}"
        con = _sync_db()
        con.execute(
            """
            INSERT OR IGNORE INTO approval_inbox
                (id, profile, run_id, command, summary, status, created_at)
            VALUES (?, ?, ?, ?, ?, 'pending', ?)
            """,
            (
                approval_id,
                profile,
                run_id,
                str(event.get("command") or "Command details unavailable"),
                str(event.get("description") or "Hermes meminta izin sebelum menjalankan command ini."),
                float(event.get("timestamp") or time.time()),
            ),
        )
        con.commit()
        con.close()
        event["approval_id"] = approval_id
    if event_type == "approval.responded":
        _resolve_approval_rows(run_id, str(event.get("choice") or ""))
    return timeline_id


def _append_run_delta(run_id: str, delta: str) -> None:
    with RUN_LOCK:
        RUN_PARTIALS[run_id] = RUN_PARTIALS.get(run_id, "") + delta


def _flush_run_partial(profile: str, run_id: str, session_id: Optional[str] = None) -> Optional[int]:
    with RUN_LOCK:
        content = RUN_PARTIALS.pop(run_id, "").strip()
        segment = RUN_SEGMENTS.get(run_id, 0)
        RUN_SEGMENTS[run_id] = segment + 1
    if not content:
        return None
    return _append_timeline(
        profile,
        "message",
        "assistant",
        content,
        "web-run",
        f"run-segment:{run_id}:{segment}",
        session_id=session_id,
        dedupe_content=True,
    )


def _persist_run_final(profile: str, run_id: str, response: str, session_id: Optional[str] = None) -> None:
    with RUN_LOCK:
        should_mirror = bool(run_id and run_id not in MIRRORED_RUNS)
        if should_mirror:
            MIRRORED_RUNS.add(run_id)
        if ACTIVE_RUNS.get(profile) == run_id:
            ACTIVE_RUNS.pop(profile, None)
    if not should_mirror or not response:
        return
    audit_id = RUN_AUDITS.get(run_id)
    if audit_id:
        config = _read_agent_ai_config(profile)
        _audit_ai_request(
            audit_id,
            app_name="office",
            channel="web",
            profile=profile,
            model=config.get("model", ""),
            base_url=config.get("base_url", ""),
            response_payload={"output_preview": response[:1000], "session_id": session_id},
            status="completed",
            completed=True,
        )
    created_at = time.time()
    target_session_id = _get_latest_session(profile) or session_id
    _append_timeline(
        profile,
        "message",
        "assistant",
        response,
        "web",
        f"run-final:{run_id}",
        session_id=target_session_id,
        dedupe_content=True,
        created_at=created_at,
    )
    _persist_web_message_to_profile(
        profile,
        "assistant",
        response,
        f"run-final:{run_id}",
        session_id=target_session_id,
        created_at=created_at,
    )
    _queue_telegram(
        profile,
        f"[Web · {profile.title()}]\n{response}",
        f"run-final:{run_id}",
    )


def _get_run_events(run_id: str, after: int = 0) -> tuple[list[dict], int]:
    with RUN_LOCK:
        events = RUN_EVENTS.get(run_id, [])
        offset = RUN_EVENT_OFFSETS.get(run_id, 0)
        start = max(0, after - offset)
        return list(events[start:]), offset + len(events)


def _capture_run_events(profile: str, run_id: str) -> None:
    request = urllib.request.Request(
        _api_server_url(profile, f"/v1/runs/{run_id}/events"),
        headers={
            "Authorization": f"Bearer {GATEWAY_TOKEN}",
            "X-Hermes-Session-Key": f"office-web:{profile}",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=HERMES_TIMEOUT_SECONDS) as response:
            for raw_line in response:
                line = raw_line.decode("utf-8", errors="replace").strip()
                if not line.startswith("data:"):
                    continue
                try:
                    event = json.loads(line[5:].strip())
                    if event.get("event") == "message.delta" and event.get("delta"):
                        _append_run_delta(run_id, str(event["delta"]))
                    elif event.get("event") == "tool.started":
                        _flush_run_partial(profile, run_id)
                    elif event.get("event") == "run.completed":
                        _persist_run_final(
                            profile,
                            run_id,
                            str(event.get("output") or event.get("response") or ""),
                            event.get("session_id"),
                        )
                    elif event.get("event") in {"run.failed", "run.cancelled"}:
                        _flush_run_partial(profile, run_id)
                        audit_id = RUN_AUDITS.get(run_id)
                        if audit_id:
                            config = _read_agent_ai_config(profile)
                            _audit_ai_request(
                                audit_id,
                                app_name="office",
                                channel="web",
                                profile=profile,
                                model=config.get("model", ""),
                                base_url=config.get("base_url", ""),
                                response_payload=event,
                                status="failed" if event.get("event") == "run.failed" else "cancelled",
                                error=str(event.get("error") or event.get("message") or ""),
                                completed=True,
                            )
                        with RUN_LOCK:
                            if ACTIVE_RUNS.get(profile) == run_id:
                                ACTIVE_RUNS.pop(profile, None)
                    timeline_id = _timeline_event_from_run(profile, run_id, event)
                    if timeline_id:
                        event["timeline_id"] = timeline_id
                    if event.get("event") == "tool.started":
                        tool = str(event.get("tool") or "tool")
                        preview = str(event.get("preview") or "").strip()
                        _queue_telegram(
                            profile,
                            f"[Web · {profile.title()}]\n{tool}{': ' + preview if preview else ''}",
                            f"run-tool:{run_id}:{event.get('timestamp')}",
                        )
                    elif event.get("event") == "approval.request":
                        _queue_telegram(
                            profile,
                            f"[Web · {profile.title()}]\nApproval dibutuhkan di web:\n{event.get('command') or event.get('description') or ''}",
                            f"run-approval:{run_id}:{event.get('timestamp')}",
                        )
                    _append_run_event(run_id, event)
                except Exception:
                    continue
    except Exception:
        return


def _start_run_event_capture(profile: str, run_id: str) -> None:
    with RUN_LOCK:
        RUN_EVENTS.setdefault(run_id, [])
        RUN_EVENT_OFFSETS.setdefault(run_id, 0)
    threading.Thread(target=_capture_run_events, args=(profile, run_id), daemon=True).start()


def _load_profile_env(profile: str) -> dict[str, str]:
    env_path = _existing_profile_dir(profile) / ".env"
    values = {}
    if not env_path.exists():
        return values
    for line in env_path.read_text(encoding="utf-8", errors="replace").splitlines():
        if "=" not in line or line.lstrip().startswith("#"):
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip("\"'")
    return values


def _queue_telegram(profile: str, text: str, dedupe_key: Optional[str] = None) -> None:
    if not text.strip():
        return
    dedupe_key = dedupe_key or f"telegram:{profile}:{uuid.uuid4().hex}"
    con = _sync_db()
    con.execute(
        """
        INSERT OR IGNORE INTO telegram_outbox
            (profile, text, dedupe_key, status, attempts, next_attempt, created_at)
        VALUES (?, ?, ?, 'pending', 0, 0, ?)
        """,
        (profile, text, dedupe_key, time.time()),
    )
    con.commit()
    con.close()
    SYNC_WAKE.set()


def _send_telegram(profile: str, text: str) -> None:
    binding = _telegram_binding(profile)
    profile_env = _load_profile_env(profile)
    token = profile_env.get("TELEGRAM_BOT_TOKEN")
    chat_id = (binding.get("origin") or {}).get("chat_id") if binding else None
    if not chat_id:
        allowed_users = re.split(r"[\s,]+", profile_env.get("TELEGRAM_ALLOWED_USERS", "").strip())
        chat_id = next((user for user in allowed_users if user), None)
    if not token or not chat_id or not text.strip():
        raise RuntimeError(f"Telegram binding unavailable for {profile}")
    for offset in range(0, len(text), 3900):
        payload = json.dumps({"chat_id": str(chat_id), "text": text[offset:offset + 3900]}).encode("utf-8")
        request = urllib.request.Request(
            f"https://api.telegram.org/bot{token}/sendMessage",
            data=payload,
            method="POST",
            headers={"Content-Type": "application/json"},
        )
        try:
            with urllib.request.urlopen(request, timeout=8):
                pass
        except Exception as exc:
            raise RuntimeError(str(exc)) from exc


def _drain_telegram_outbox() -> None:
    con = _sync_db()
    rows = con.execute(
        """
        SELECT id, profile, text, attempts FROM telegram_outbox
        WHERE status = 'pending' AND next_attempt <= ?
        ORDER BY id LIMIT 20
        """,
        (time.time(),),
    ).fetchall()
    con.close()
    for row in rows:
        try:
            _send_telegram(row["profile"], row["text"])
            con = _sync_db()
            con.execute(
                "UPDATE telegram_outbox SET status = 'delivered', delivered_at = ?, last_error = NULL WHERE id = ?",
                (time.time(), row["id"]),
            )
            con.commit()
            con.close()
        except Exception as exc:
            attempts = int(row["attempts"] or 0) + 1
            delay = min(300, 2 ** min(attempts, 8))
            con = _sync_db()
            con.execute(
                """
                UPDATE telegram_outbox
                SET attempts = ?, next_attempt = ?, last_error = ?
                WHERE id = ?
                """,
                (attempts, time.time() + delay, str(exc)[:500], row["id"]),
            )
            con.commit()
            con.close()


def _resolve_approval_rows(run_id: str, decision: str) -> None:
    con = _sync_db()
    con.execute(
        """
        UPDATE approval_inbox
        SET status = 'resolved', decision = ?, resolved_at = ?
        WHERE run_id = ? AND status = 'pending'
        """,
        (decision, time.time(), run_id),
    )
    con.commit()
    con.close()


def _ingest_profile_messages(profile: str) -> None:
    db = _db_path(profile)
    if not db:
        return
    con = _sync_db()
    cursor = con.execute(
        "SELECT last_message_id FROM timeline_cursors WHERE profile = ?",
        (profile,),
    ).fetchone()
    if not cursor:
        source = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
        row = source.execute("SELECT COALESCE(MAX(id), 0) FROM messages").fetchone()
        source.close()
        con.execute(
            "INSERT INTO timeline_cursors(profile, last_message_id) VALUES (?, ?)",
            (profile, int(row[0] or 0)),
        )
        con.commit()
        con.close()
        return
    last_id = int(cursor["last_message_id"])
    con.close()

    source = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    source.row_factory = sqlite3.Row
    rows = source.execute(
        """
        SELECT m.id, m.session_id, m.role, m.content, m.tool_name, m.tool_calls,
               m.timestamp, m.platform_message_id, s.source AS session_source
        FROM messages m
        JOIN sessions s ON s.id = m.session_id
        WHERE m.id > ? AND s.source = 'telegram'
          AND (
            m.platform_message_id IS NULL
            OR (
              m.platform_message_id NOT LIKE 'office:%'
              AND m.platform_message_id NOT LIKE 'office-backfill:%'
            )
          )
        ORDER BY m.id
        LIMIT 500
        """,
        (last_id,),
    ).fetchall()
    source.close()
    if not rows:
        return

    for row in rows:
        content = str(row["content"] or "")
        role = str(row["role"])
        kind = "terminal" if role == "tool" else "message"
        if not content.strip() and role != "tool":
            last_id = int(row["id"])
            continue
        _append_timeline(
            profile,
            kind,
            "assistant" if role == "tool" else role,
            content,
            "telegram-db",
            f"db-message:{profile}:{row['id']}",
            session_id=row["session_id"],
            metadata={
                "db_message_id": int(row["id"]),
                "tool": row["tool_name"],
                "tool_calls": _json_dict(row["tool_calls"]) if row["tool_calls"] else None,
                "platform_message_id": row["platform_message_id"],
            },
            dedupe_content=role in {"user", "assistant"},
            dedupe_across_sessions=role == "assistant",
            created_at=float(row["timestamp"]),
        )
        last_id = int(row["id"])

    con = _sync_db()
    con.execute(
        """
        INSERT INTO timeline_cursors(profile, last_message_id) VALUES (?, ?)
        ON CONFLICT(profile) DO UPDATE SET last_message_id = excluded.last_message_id
        """,
        (profile, last_id),
    )
    con.commit()
    con.close()


def _sync_worker() -> None:
    while not SYNC_STOP.is_set():
        try:
            for profile in _profiles_for_sync():
                _ingest_profile_messages(profile)
            _drain_telegram_outbox()
        except Exception:
            pass
        SYNC_WAKE.wait(0.8)
        SYNC_WAKE.clear()


@app.on_event("startup")
def start_sync_worker() -> None:
    _init_sync_db()
    SYNC_STOP.clear()
    threading.Thread(target=_sync_worker, daemon=True).start()


@app.on_event("shutdown")
def stop_sync_worker() -> None:
    SYNC_STOP.set()
    SYNC_WAKE.set()


def _normalize_run_response(profile: str, run: dict) -> dict:
    result = dict(run)
    result["profile"] = profile
    result["response"] = result.get("output", "")
    if result.get("status") == "completed":
        run_id = result.get("run_id")
        _persist_run_final(profile, run_id, result["response"], result.get("session_id"))
    elif result.get("status") in {"failed", "cancelled"}:
        with RUN_LOCK:
            if ACTIVE_RUNS.get(profile) == result.get("run_id"):
                ACTIVE_RUNS.pop(profile, None)
    return result


def _attachment_text(att: dict) -> str:
    """Convert a base64 attachment to inline text the model can read."""
    name = att.get("name", "file")
    mime = att.get("type", "")
    data_url: str = att.get("data", "")
    # strip data URL prefix
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


# ── auth ─────────────────────────────────────────────────────────────────────

class LoginRequest(BaseModel):
    email: str
    password: str


@app.post("/api/auth/login")
def login(req: LoginRequest):
    if not OFFICE_EMAIL or not OFFICE_PASSWORD:
        raise HTTPException(status_code=503, detail="Auth not configured on server")
    if req.email != OFFICE_EMAIL or req.password != OFFICE_PASSWORD:
        raise HTTPException(status_code=401, detail="Email atau password salah")
    return {
        "access_token": GATEWAY_TOKEN,
        "name": OFFICE_NAME,
        "email": OFFICE_EMAIL,
        "role": "admin",
    }


# ── chat ──────────────────────────────────────────────────────────────────────

class ChatRequest(BaseModel):
    message: str = ""
    session_id: Optional[str] = None
    attachments: Optional[list] = None


@app.post("/api/office/chat/{profile}")
def chat(profile: str, req: ChatRequest, _: str = Depends(verify_auth)):
    profile = resolve_profile(profile)
    queued = _enqueue_chat(profile, req)
    return {
        **queued,
        "status": "started",
        "queued": True,
    }


@app.get("/api/office/chat/{profile}/runs/{run_id}")
def get_chat_run(profile: str, run_id: str, after: int = 0, _: str = Depends(verify_auth)):
    profile = resolve_profile(profile)
    queued = _queue_or_run_status(profile, run_id, after)
    if queued:
        if queued.get("redirect_run_id"):
            run_id = queued["redirect_run_id"]
        elif queued.get("run_id") != run_id and queued.get("status") not in {"queued", "failed"}:
            run_id = queued["run_id"]
        else:
            return queued
    events, next_event = _get_run_events(run_id, max(0, after))
    try:
        run = _normalize_run_response(profile, _api_request(profile, f"/v1/runs/{run_id}"))
    except HTTPException as exc:
        completed = next((event for event in reversed(events) if event.get("event") == "run.completed"), None)
        failed = next((event for event in reversed(events) if event.get("event") in {"run.failed", "run.cancelled"}), None)
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
            active = ACTIVE_RUNS.get(profile) == run_id
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


@app.post("/api/office/chat/{profile}/runs/{run_id}/stop")
def stop_chat_run(profile: str, run_id: str, _: str = Depends(verify_auth)):
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
    return _api_request(profile, f"/v1/runs/{run_id}/stop", method="POST", payload={})


class RunApproval(BaseModel):
    choice: str


@app.post("/api/office/chat/{profile}/runs/{run_id}/approval")
def approve_chat_run(profile: str, run_id: str, req: RunApproval, _: str = Depends(verify_auth)):
    profile = resolve_profile(profile)
    result = _api_request(profile, f"/v1/runs/{run_id}/approval", method="POST", payload={"choice": req.choice})
    _resolve_approval_rows(run_id, req.choice)
    return result


def _serialize_approval(row: sqlite3.Row) -> dict:
    return {
        "id": row["id"],
        "profile": row["profile"],
        "run_id": row["run_id"],
        "command": row["command"],
        "summary": row["summary"],
        "status": row["status"],
        "created_at": _ts_to_iso(row["created_at"]),
        "resolved_at": _ts_to_iso(row["resolved_at"]) if row["resolved_at"] else None,
        "decision": row["decision"],
    }


@app.get("/api/office/timeline/{profile}")
def timeline(profile: str, after: int = 0, limit: int = 200, _: str = Depends(verify_auth)):
    requested_profile = validate_profile(profile)
    profile = resolve_profile(profile)
    _ingest_profile_messages(profile)
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
            """
            SELECT * FROM timeline_events
            WHERE profile = ? AND id > ?
            ORDER BY id LIMIT ?
            """,
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


@app.get("/api/office/approvals")
def approval_inbox(profile: Optional[str] = None, status: str = "pending", _: str = Depends(verify_auth)):
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


class ApprovalDecision(BaseModel):
    decision: str


@app.post("/api/office/approvals/{approval_id}")
def decide_approval(approval_id: str, req: ApprovalDecision, _: str = Depends(verify_auth)):
    con = _sync_db()
    row = con.execute("SELECT * FROM approval_inbox WHERE id = ?", (approval_id,)).fetchone()
    con.close()
    if not row:
        raise HTTPException(status_code=404, detail="Approval not found")
    choice = "once" if req.decision in {"approve", "once"} else "deny"
    return approve_chat_run(row["profile"], row["run_id"], RunApproval(choice=choice), _)


@app.get("/api/office/outbox")
def outbox_status(_: str = Depends(verify_auth)):
    con = _sync_db()
    rows = con.execute(
        "SELECT status, COUNT(*) AS count FROM telegram_outbox GROUP BY status"
    ).fetchall()
    con.close()
    return {row["status"]: int(row["count"]) for row in rows}


class ForwardRequest(BaseModel):
    source_profile: Optional[str] = None
    target_profile: str
    messages: list[str]


@app.post("/api/office/forward")
def forward_messages(req: ForwardRequest, _: str = Depends(verify_auth)):
    target = validate_profile(req.target_profile)
    if req.source_profile:
        validate_profile(req.source_profile)
    messages = [message.strip() for message in req.messages if message.strip()]
    if not messages:
        raise HTTPException(status_code=400, detail="No messages to forward")
    source = req.source_profile.title() if req.source_profile else "Web"
    content = f"[Forwarded from {source}]\n\n" + "\n\n---\n\n".join(messages)
    return chat(target, ChatRequest(message=content), _)


# ── status & history ──────────────────────────────────────────────────────────

@app.get("/api/office/status")
def status(_: str = Depends(verify_auth)):
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


@app.get("/api/office/history/{profile}")
def history(profile: str, limit: int = 500, _: str = Depends(verify_auth)):
    profile = resolve_profile(profile)
    return _get_history(profile, limit)


# ── conversations ─────────────────────────────────────────────────────────────

@app.get("/api/office/conversations/{profile}")
def conversations(profile: str, _: str = Depends(verify_auth)):
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
                "started_at": _ts_to_iso(r[1]),
                "preview": (r[2] or "")[:120],
                "message_count": r[3] or 0,
            }
            for r in rows
            if r[2]  # skip sessions with no user messages
        ]
    except Exception as e:
        return []


@app.get("/api/office/conversations/{profile}/{session_id}")
def conversation_messages(profile: str, session_id: str, _: str = Depends(verify_auth)):
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
        con = sqlite3.connect(db)
        rows = con.execute(
            """
            SELECT role, content, timestamp
            FROM messages
            WHERE session_id = ? AND role IN ('user','assistant')
              AND content IS NOT NULL AND content != ''
            ORDER BY timestamp
            """,
            (session_id,),
        ).fetchall()
        con.close()
        return [{"role": r[0], "content": r[1], "created_at": _ts_to_iso(r[2])} for r in rows]
    except Exception:
        return []


@app.delete("/api/office/conversations/{profile}/{session_id}")
def delete_conversation(profile: str, session_id: str, _: str = Depends(verify_auth)):
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


# ── agents CRUD ───────────────────────────────────────────────────────────────

class AgentCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=31)
    display_name: str = Field("", max_length=64)
    description: str = Field("", max_length=200)
    model: str = Field("", max_length=128)
    base_url: str = Field("", max_length=256)
    api_key: str = Field("", max_length=256)
    soul: str = Field("", max_length=20000)
    telegram_token: str = Field("", max_length=128)
    telegram_allowed_users: str = Field("", max_length=512)


class SoulUpdate(BaseModel):
    soul: str = Field(..., max_length=20000)


class EnvUpdate(BaseModel):
    telegram_token: Optional[str] = Field(None, max_length=128)
    telegram_allowed_users: Optional[str] = Field(None, max_length=512)


class ConfigUpdate(BaseModel):
    model: Optional[str] = None
    base_url: Optional[str] = None
    api_key: Optional[str] = None


class HermesAgentConfigUpdate(BaseModel):
    model: Optional[str] = Field(None, max_length=200)
    combo: Optional[str] = Field(None, max_length=200)
    base_url: Optional[str] = Field(None, max_length=300)
    api_key: Optional[str] = Field(None, max_length=500)
    restart: bool = False


class HermesApplyAllRequest(BaseModel):
    model: Optional[str] = Field(None, max_length=200)
    combo: Optional[str] = Field(None, max_length=200)
    base_url: Optional[str] = Field(None, max_length=300)
    api_key: Optional[str] = Field(None, max_length=500)
    restart: bool = False


def _read_soul_preview(profile_dir: Path, max_chars: int = 200) -> str:
    soul = profile_dir / "SOUL.md"
    if not soul.exists():
        return ""
    try:
        return soul.read_text(encoding="utf-8")[:max_chars]
    except Exception:
        return ""


def _read_config(profile_dir: Path) -> dict:
    cfg = profile_dir / "config.yaml"
    if not cfg.exists():
        return {}
    try:
        return yaml.safe_load(cfg.read_text(encoding="utf-8")) or {}
    except Exception:
        return {}


def _write_config(profile_dir: Path, updates: dict):
    cfg_path = profile_dir / "config.yaml"
    cfg = _read_config(profile_dir)
    model_section = cfg.get("model", {}) if isinstance(cfg.get("model"), dict) else {}
    if updates.get("model"):
        model_section["default"] = updates["model"]
    if updates.get("base_url"):
        model_section["base_url"] = updates["base_url"]
    if updates.get("api_key"):
        model_section["api_key"] = updates["api_key"]
    if model_section:
        cfg["model"] = model_section
    cfg_path.write_text(yaml.safe_dump(cfg, sort_keys=False), encoding="utf-8")


def _read_env_keys(profile_dir: Path) -> list:
    env = profile_dir / ".env"
    if not env.exists():
        return []
    keys = []
    for line in env.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            keys.append(line.split("=", 1)[0])
    return keys


def _write_env(profile_dir: Path, updates: dict):
    env_path = profile_dir / ".env"
    existing: dict = {}
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.rstrip("\n")
            if line and not line.lstrip().startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                existing[k.strip()] = v
    for k, v in updates.items():
        if v:
            existing[k] = v
    env_path.write_text("\n".join(f"{k}={v}" for k, v in existing.items()) + "\n", encoding="utf-8")
    os.chmod(env_path, 0o600)


@app.get("/api/office/agents")
def list_agents(_: str = Depends(verify_auth)):
    out = []
    for profile, p in _iter_agent_profiles():
        cfg = _read_config(p)
        model_section = cfg.get("model", {}) if isinstance(cfg.get("model"), dict) else {}
        desc_path = p / ".description"
        description = desc_path.read_text(encoding="utf-8").strip() if desc_path.exists() else ""
        out.append({
            "profile": profile,
            "apiProfile": profile,
            "name": _profile_display_name(profile, cfg),
            "role": description,
            "model": model_section.get("default", ""),
            "soul_preview": _read_soul_preview(p),
            "env_keys": _read_env_keys(p),
            "online": (p / "state.db").exists(),
        })
    return out


@app.post("/api/office/agents")
def create_agent(payload: AgentCreate, _: str = Depends(verify_auth)):
    profile = payload.name
    validate_profile(profile)
    profile_dir = PROFILES_DIR / profile
    if profile_dir.exists():
        raise HTTPException(status_code=409, detail=f"Profile '{profile}' already exists")
    cmd = [HERMES_BIN, "profile", "create", profile]
    if payload.description:
        cmd += ["--description", payload.description]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    except (subprocess.TimeoutExpired, FileNotFoundError) as e:
        raise HTTPException(status_code=503, detail=str(e))
    if result.returncode != 0:
        raise HTTPException(status_code=500, detail=f"profile create failed: {result.stderr.strip()[:300]}")
    if not profile_dir.exists():
        raise HTTPException(status_code=500, detail="Profile dir not created")
    if payload.soul:
        (profile_dir / "SOUL.md").write_text(payload.soul, encoding="utf-8")
    _write_config(profile_dir, {"model": payload.model, "base_url": payload.base_url, "api_key": payload.api_key})
    env_updates = {}
    if payload.telegram_token:
        env_updates["TELEGRAM_BOT_TOKEN"] = payload.telegram_token
    if payload.telegram_allowed_users:
        env_updates["TELEGRAM_ALLOWED_USERS"] = payload.telegram_allowed_users
    if payload.api_key:
        env_updates["OPENAI_API_KEY"] = payload.api_key
    if payload.base_url:
        env_updates["OPENAI_BASE_URL"] = payload.base_url
    if env_updates:
        _write_env(profile_dir, env_updates)
    return {"ok": True, "profile": profile}


@app.delete("/api/office/agents/{profile}")
def delete_agent(profile: str, _: str = Depends(verify_auth)):
    validate_profile(profile)
    profile_dir = PROFILES_DIR / profile
    if not profile_dir.exists():
        raise HTTPException(status_code=404, detail=f"Profile '{profile}' not found")
    for flag in ["--yes", "-y"]:
        result = subprocess.run(
            [HERMES_BIN, "profile", "delete", profile, flag],
            capture_output=True, text=True, timeout=60,
        )
        if result.returncode == 0:
            return {"ok": True}
    raise HTTPException(status_code=500, detail=f"profile delete failed: {result.stderr.strip()[:300]}")


@app.put("/api/office/agents/{profile}/soul")
def update_soul(profile: str, payload: SoulUpdate, _: str = Depends(verify_auth)):
    profile = resolve_profile(profile)
    profile_dir = _existing_profile_dir(profile)
    if not profile_dir.exists():
        raise HTTPException(status_code=404, detail="Not found")
    (profile_dir / "SOUL.md").write_text(payload.soul, encoding="utf-8")
    return {"ok": True}


@app.put("/api/office/agents/{profile}/env")
def update_env(profile: str, payload: EnvUpdate, _: str = Depends(verify_auth)):
    profile = resolve_profile(profile)
    profile_dir = _existing_profile_dir(profile)
    if not profile_dir.exists():
        raise HTTPException(status_code=404, detail="Not found")
    updates = {}
    if payload.telegram_token is not None:
        updates["TELEGRAM_BOT_TOKEN"] = payload.telegram_token
    if payload.telegram_allowed_users is not None:
        updates["TELEGRAM_ALLOWED_USERS"] = payload.telegram_allowed_users
    if updates:
        _write_env(profile_dir, updates)
    return {"ok": True}


@app.put("/api/office/agents/{profile}/config")
def update_agent_config(profile: str, payload: ConfigUpdate, _: str = Depends(verify_auth)):
    validate_profile(profile)
    profile_dir = _existing_profile_dir(resolve_profile(profile))
    if not profile_dir.exists():
        raise HTTPException(status_code=404, detail="Not found")
    _write_config(profile_dir, payload.dict(exclude_none=True))
    return {"ok": True}


@app.get("/api/office/hermes/models")
def hermes_models(_: str = Depends(verify_auth)):
    models = _fetch_router_models()
    return {
        "base_url": _router_v1_url(False),
        "external_base_url": _router_v1_url(True),
        "models": models,
        "combos": [model for model in models if model.get("type") == "combo"],
        "count": len(models),
    }


@app.get("/api/office/hermes/agents/config")
def hermes_agent_configs(_: str = Depends(verify_auth)):
    return {
        "router": {
            "base_url": _router_v1_url(False),
            "external_base_url": _router_v1_url(True),
            "api_key_configured": bool(_router_default_api_key()),
        },
        "multi_read_seconds": _queue_wait_seconds(),
        "agents": [_read_agent_ai_config(profile) for profile, _ in _iter_agent_profiles()],
    }


@app.patch("/api/office/hermes/agents/{profile}/config")
def patch_hermes_agent_config(profile: str, payload: HermesAgentConfigUpdate, _: str = Depends(verify_auth)):
    profile = resolve_profile(profile)
    updates = payload.dict(exclude_none=True)
    config = _write_agent_ai_config(profile, updates)
    restart = _restart_agent_service(profile) if payload.restart else None
    _audit_ai_request(
        f"config-{uuid.uuid4().hex}",
        app_name="office",
        channel="web-admin",
        profile=profile,
        model=config.get("model", ""),
        base_url=config.get("base_url", ""),
        request_payload={"action": "update_agent_config", "updates": updates},
        response_payload={"config": config, "restart": restart},
        status="completed" if not restart or restart.get("ok") else "failed",
        error=restart.get("error") if restart and not restart.get("ok") else None,
        completed=True,
    )
    return {"ok": True, "agent": config, "restart": restart}


@app.post("/api/office/hermes/agents/apply-all")
def apply_all_hermes_agent_config(payload: HermesApplyAllRequest, _: str = Depends(verify_auth)):
    updates = payload.dict(exclude_none=True)
    results = []
    for profile, _profile_dir_value in _iter_agent_profiles():
        config = _write_agent_ai_config(profile, updates)
        restart = _restart_agent_service(profile) if payload.restart else None
        results.append({"profile": profile, "agent": config, "restart": restart})
    _audit_ai_request(
        f"config-{uuid.uuid4().hex}",
        app_name="office",
        channel="web-admin",
        profile="all",
        model=str(updates.get("model") or updates.get("combo") or ""),
        base_url=str(updates.get("base_url") or ""),
        request_payload={"action": "apply_all_agent_config", "updates": updates},
        response_payload={"count": len(results), "restart": payload.restart},
        status="completed",
        completed=True,
    )
    return {"ok": True, "results": results}


# ── legacy routes (keep for backwards compat) ─────────────────────────────────

@app.post("/chat/{profile}")
def chat_legacy(profile: str, req: ChatRequest, _: str = Depends(verify_auth)):
    return chat(profile, req, _)


@app.get("/status")
def status_legacy(_: str = Depends(verify_auth)):
    return status(_)


@app.get("/history/{profile}")
def history_legacy(profile: str, limit: int = 40, _: str = Depends(verify_auth)):
    return history(profile, limit, _)


@app.get("/health")
@app.get("/api/office/health")
def health():
    return {"ok": True}

# ══════════════════════════════════════════════════════════════════
# WORKSPACE API — Tasks, Cron, Memory, Files, Notifications
# ══════════════════════════════════════════════════════════════════

import json as _json
import re as _re

# ── helpers ──────────────────────────────────────────────────────

def _workspace_dir(profile: str) -> Path:
    d = _existing_profile_dir(resolve_profile(profile)) / "workspace"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _tasks_path(profile: str) -> Path:
    return _workspace_dir(profile) / "tasks.json"


def _parse_cron_output(text: str) -> list:
    jobs = []
    current: dict = {}
    for line in text.splitlines():
        line = line.strip()
        m = _re.match(r'^([a-f0-9]{8,})\s+\[(.*?)\]$', line)
        if m:
            if current.get("id"):
                jobs.append(current)
            current = {"id": m.group(1), "status": m.group(2)}
            continue
        for field, key in [
            ("Name", "name"),
            ("Schedule", "schedule"),
            ("Repeat", "repeat"),
            ("Next run", "next_run"),
            ("Deliver", "deliver"),
            ("Last run", "last_run"),
        ]:
            m2 = _re.match(rf'^{field}:\s+(.+)$', line)
            if m2:
                val = m2.group(1).strip()
                # "Last run" may trail "  ok" or "  error"
                if key == "last_run":
                    parts = val.rsplit(None, 1)
                    current["last_run"] = parts[0].strip()
                    if len(parts) > 1:
                        current["last_run_status"] = parts[1]
                else:
                    current[key] = val
                break
    if current.get("id"):
        jobs.append(current)
    return jobs


def _get_notifications(profile: str, limit: int = 20) -> list:
    db = _db_path(profile)
    if not db:
        return []
    try:
        con = sqlite3.connect(db)
        rows = con.execute(
            """
            SELECT id, started_at, ended_at, message_count,
                   input_tokens, output_tokens, end_reason, title
            FROM sessions
            ORDER BY started_at DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
        con.close()
        result = []
        for r in rows:
            sid, started, ended, msg_count, inp_tok, out_tok, end_reason, title = r
            result.append({
                "id": sid,
                "type": "session_end" if ended else "session_active",
                "title": title or "Untitled session",
                "started_at": _ts_to_iso(started),
                "ended_at": _ts_to_iso(ended) if ended else None,
                "message_count": msg_count or 0,
                "input_tokens": inp_tok or 0,
                "output_tokens": out_tok or 0,
                "end_reason": end_reason,
            })
        return result
    except Exception:
        return []


# ── memory (SOUL.md) ──────────────────────────────────────────────

@app.get("/api/office/workspace/{profile}/memory")
def get_memory(profile: str, _: str = Depends(verify_auth)):
    profile = resolve_profile(profile)
    soul_path = _existing_profile_dir(profile) / "SOUL.md"
    if not soul_path.exists():
        return {"content": ""}
    return {"content": soul_path.read_text(encoding="utf-8")}


class MemoryUpdate(BaseModel):
    content: str = Field(..., max_length=50000)


@app.put("/api/office/workspace/{profile}/memory")
def update_memory(profile: str, payload: MemoryUpdate, _: str = Depends(verify_auth)):
    profile = resolve_profile(profile)
    soul_path = _existing_profile_dir(profile) / "SOUL.md"
    if not soul_path.parent.exists():
        raise HTTPException(status_code=404, detail="Profile not found")
    soul_path.write_text(payload.content, encoding="utf-8")
    return {"ok": True}


# ── cron ─────────────────────────────────────────────────────────

@app.get("/api/office/workspace/{profile}/cron")
def get_cron(profile: str, _: str = Depends(verify_auth)):
    validate_profile(profile)
    try:
        result = subprocess.run(
            _hermes_cmd(profile, "cron", "list"),
            capture_output=True, text=True, timeout=15,
        )
        return _parse_cron_output(result.stdout)
    except Exception:
        return []


@app.post("/api/office/workspace/{profile}/cron/{job_id}/pause")
def pause_cron(profile: str, job_id: str, _: str = Depends(verify_auth)):
    validate_profile(profile)
    result = subprocess.run(
        _hermes_cmd(profile, "cron", "pause", job_id),
        capture_output=True, text=True, timeout=15,
    )
    if result.returncode != 0:
        raise HTTPException(status_code=500, detail=result.stderr.strip()[:200])
    return {"ok": True}


@app.post("/api/office/workspace/{profile}/cron/{job_id}/resume")
def resume_cron(profile: str, job_id: str, _: str = Depends(verify_auth)):
    validate_profile(profile)
    result = subprocess.run(
        _hermes_cmd(profile, "cron", "resume", job_id),
        capture_output=True, text=True, timeout=15,
    )
    if result.returncode != 0:
        raise HTTPException(status_code=500, detail=result.stderr.strip()[:200])
    return {"ok": True}


# ── tasks ─────────────────────────────────────────────────────────

@app.get("/api/office/workspace/{profile}/tasks")
def get_tasks(profile: str, _: str = Depends(verify_auth)):
    validate_profile(profile)
    p = _tasks_path(profile)
    if not p.exists():
        return []
    try:
        return _json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return []


class TaskItem(BaseModel):
    id: str
    title: str
    status: str = "todo"
    assigned_by: str = "user"
    created_at: str = ""
    priority: str = "normal"


@app.put("/api/office/workspace/{profile}/tasks")
def update_tasks(profile: str, tasks: list[TaskItem], _: str = Depends(verify_auth)):
    validate_profile(profile)
    p = _tasks_path(profile)
    p.write_text(_json.dumps([t.dict() for t in tasks], ensure_ascii=False, indent=2), encoding="utf-8")
    return {"ok": True}


# ── files ─────────────────────────────────────────────────────────

ALLOWED_FILE_EXTS = {".md", ".yaml", ".yml", ".json", ".txt", ".env", ".log", ".py", ".sh"}

@app.get("/api/office/workspace/{profile}/files")
def get_files(profile: str, _: str = Depends(verify_auth)):
    profile = resolve_profile(profile)
    profile_dir = _existing_profile_dir(profile)
    if not profile_dir.exists():
        raise HTTPException(status_code=404, detail="Profile not found")
    files = []
    for item in sorted(profile_dir.rglob("*")):
        if item.is_file() and item.suffix in ALLOWED_FILE_EXTS:
            rel = item.relative_to(profile_dir)
            try:
                stat = item.stat()
                files.append({
                    "path": str(rel),
                    "name": item.name,
                    "size": stat.st_size,
                    "modified": _ts_to_iso(stat.st_mtime),
                    "ext": item.suffix,
                })
            except Exception:
                pass
    return files[:200]


# ── notifications ─────────────────────────────────────────────────

@app.get("/api/office/workspace/{profile}/notifications")
def get_notifications(profile: str, _: str = Depends(verify_auth)):
    validate_profile(profile)
    return _get_notifications(profile)


# ── docs (memories) ───────────────────────────────────────────────

def _memories_dir(profile: str):
    return _existing_profile_dir(resolve_profile(profile)) / "memories"


def _doc_id_from_path(p) -> str:
    return p.stem


def _safe_doc_path(profile: str, doc_id: str):
    import re as _re2
    if not _re2.match(r"^[\w.\-]{1,80}$", doc_id):
        raise HTTPException(status_code=400, detail="Invalid doc id")
    return _memories_dir(profile) / f"{doc_id}.md"


SHARED_DIRS = [
    Path("/root/.hermes/memories"),
    Path("/root/.hermes/shared/teman-umkm-kita"),
]

def _collect_docs(directory, id_prefix=""):
    docs = []
    if not directory.exists():
        return docs
    for f in sorted(directory.iterdir()):
        if f.is_file() and f.suffix == ".md" and not f.name.endswith(".lock"):
            try:
                stat = f.stat()
                doc_id = (id_prefix + f.stem) if id_prefix else f.stem
                docs.append({
                    "id": doc_id,
                    "title": f.stem.replace("_", " ").replace("-", " ").title(),
                    "content": f.read_text(encoding="utf-8", errors="replace"),
                    "updated_at": _ts_to_iso(stat.st_mtime),
                    "source": "shared" if id_prefix else "profile",
                })
            except Exception:
                pass
    return docs

@app.get("/api/office/workspace/{profile}/docs")
def get_docs(profile: str, _: str = Depends(verify_auth)):
    validate_profile(profile)
    docs = _collect_docs(_memories_dir(profile))
    for shared_dir in SHARED_DIRS:
        docs += _collect_docs(shared_dir, id_prefix="shared__")
    return docs


class DocUpdate(BaseModel):
    content: str = Field(..., max_length=200000)


@app.put("/api/office/workspace/{profile}/docs/{doc_id}")
def update_doc(profile: str, doc_id: str, payload: DocUpdate, _: str = Depends(verify_auth)):
    validate_profile(profile)
    mem_dir = _memories_dir(profile)
    if not mem_dir.exists():
        raise HTTPException(status_code=404, detail="Profile memories not found")
    doc_path = _safe_doc_path(profile, doc_id)
    doc_path.write_text(payload.content, encoding="utf-8")
    return {"ok": True}


# ── activity ───────────────────────────────────────────────────────

import time as _time
import json as _json

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

def _get_tool_activity(profile: str, session_id: Optional[str] = None) -> Optional[dict]:
    db = _db_path(profile)
    session_id = session_id or _get_latest_session(profile)
    if not db or not session_id:
        return None
    try:
        con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
        con.row_factory = sqlite3.Row
        msg = con.execute(
            "SELECT tool_name, tool_calls, timestamp FROM messages "
            "WHERE session_id = ? ORDER BY timestamp DESC LIMIT 1",
            (session_id,),
        ).fetchone()
        con.close()
        if not msg:
            return None
        tool_name = msg["tool_name"]
        if not tool_name and msg["tool_calls"]:
            calls = _json.loads(msg["tool_calls"])
            if calls and isinstance(calls, list):
                fn = calls[0].get("function", {})
                tool_name = fn.get("name") or calls[0].get("name")
        if not tool_name:
            return None
        label = TOOL_LABELS.get(tool_name, f"Menjalankan {tool_name}")
        return {
            "active": True,
            "stage": "tool",
            "label": label + "…",
            "tool": tool_name,
            "last_activity": _ts_to_iso(msg["timestamp"]),
        }
    except Exception:
        return None


def _get_activity(profile: str) -> dict:
    profile = resolve_profile(profile)
    db = _db_path(profile)
    if not db:
        return {"active": False, "stage": "offline", "label": "Offline", "tool": None}

    with RUN_LOCK:
        active_run = ACTIVE_RUNS.get(profile)
    if active_run:
        try:
            run = _normalize_run_response(profile, _api_request(profile, f"/v1/runs/{active_run}"))
            if run.get("status") not in {"completed", "failed", "cancelled"}:
                events, _ = _get_run_events(active_run)
                for event in reversed(events):
                    if event.get("event") == "tool.started":
                        tool_name = event.get("tool") or "tool"
                        label = TOOL_LABELS.get(tool_name, f"Menjalankan {tool_name}")
                        return {"active": True, "stage": "tool", "label": label + "…", "tool": tool_name}
                    if event.get("event") in {"tool.completed", "approval.responded"}:
                        break
                tool_activity = _get_tool_activity(profile, run.get("session_id"))
                if tool_activity:
                    return tool_activity
                last_event = run.get("last_event")
                if last_event == "tool.started":
                    return {"active": True, "stage": "tool", "label": "Menjalankan tool…", "tool": None}
                if run.get("status") == "waiting_for_approval":
                    return {"active": True, "stage": "tool", "label": "Menunggu approval…", "tool": None}
                return {"active": True, "stage": "thinking", "label": "Sedang berpikir…", "tool": None}
        except Exception:
            pass

    gateway_state = _existing_profile_dir(profile) / "gateway_state.json"
    try:
        state = json.loads(gateway_state.read_text(encoding="utf-8")) if gateway_state.exists() else {}
        if int(state.get("active_agents") or 0) > 0:
            tool_activity = _get_tool_activity(profile)
            if tool_activity:
                return tool_activity
            return {"active": True, "stage": "thinking", "label": "Sedang berpikir…", "tool": None}
    except Exception:
        pass
    return {"active": False, "stage": "idle", "label": "Idle", "tool": None}


@app.get("/api/office/workspace/{profile}/activity")
def get_activity(profile: str, _: str = Depends(verify_auth)):
    profile = resolve_profile(profile)
    return _get_activity(profile)
