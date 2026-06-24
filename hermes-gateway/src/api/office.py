"""Workspace/office API endpoints — memory, cron, tasks, files, notifications, docs, activity."""
import json
import re
import sqlite3
import subprocess
import time
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

import config
from src.auth.middleware import verify_auth
from src.models.chat import ChatRequest
from src.services.profile_service import (
    _hermes_cmd,
    _existing_profile_dir,
    resolve_profile,
    _db_path,
    _iter_agent_profiles,
    _read_config,
)
from src.services.queue_service import RUN_LOCK, audit_ai_request, queue_wait_seconds
from src.services.timeline_service import _sync_db, ts_to_iso
from src.util import validate_profile, ALLOWED_FILE_EXTS

router = APIRouter()

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

SHARED_DIRS = [
    Path("/root/.hermes/memories"),
    Path("/root/.hermes/shared/teman-umkm-kita"),
]

OFFICE_TOPIC_NAMES = [
    "general", "strategy", "errors", "approvals", "tech",
    "creative", "content", "growth", "projects", "inbox",
]


# ── Auth ──────────────────────────────────────────────────────────────────────

class LoginRequest(BaseModel):
    email: str
    password: str


@router.post("/api/auth/login")
def login(req: LoginRequest):
    if not config.OFFICE_EMAIL or not config.OFFICE_PASSWORD:
        raise HTTPException(status_code=503, detail="Auth not configured on server")
    if req.email != config.OFFICE_EMAIL or req.password != config.OFFICE_PASSWORD:
        raise HTTPException(status_code=401, detail="Email atau password salah")
    return {
        "access_token": config.GATEWAY_TOKEN,
        "name": config.OFFICE_NAME,
        "email": config.OFFICE_EMAIL,
        "role": "admin",
    }


# ── memory (SOUL.md) ──────────────────────────────────────────────────────────

class MemoryUpdate(BaseModel):
    content: str = Field(..., max_length=50000)


@router.get("/api/office/workspace/{profile}/memory")
def get_memory(profile: str, _: str = Depends(verify_auth)):
    profile = resolve_profile(profile)
    soul_path = _existing_profile_dir(profile) / "SOUL.md"
    if not soul_path.exists():
        return {"content": ""}
    return {"content": soul_path.read_text(encoding="utf-8")}


@router.put("/api/office/workspace/{profile}/memory")
def update_memory(profile: str, payload: MemoryUpdate, _: str = Depends(verify_auth)):
    profile = resolve_profile(profile)
    soul_path = _existing_profile_dir(profile) / "SOUL.md"
    if not soul_path.parent.exists():
        raise HTTPException(status_code=404, detail="Profile not found")
    soul_path.write_text(payload.content, encoding="utf-8")
    return {"ok": True}


# ── cron ─────────────────────────────────────────────────────────────────────

@router.get("/api/office/workspace/{profile}/cron")
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


@router.post("/api/office/workspace/{profile}/cron/{job_id}/pause")
def pause_cron(profile: str, job_id: str, _: str = Depends(verify_auth)):
    validate_profile(profile)
    result = subprocess.run(
        _hermes_cmd(profile, "cron", "pause", job_id),
        capture_output=True, text=True, timeout=15,
    )
    if result.returncode != 0:
        raise HTTPException(status_code=500, detail=result.stderr.strip()[:200])
    return {"ok": True}


@router.post("/api/office/workspace/{profile}/cron/{job_id}/resume")
def resume_cron(profile: str, job_id: str, _: str = Depends(verify_auth)):
    validate_profile(profile)
    result = subprocess.run(
        _hermes_cmd(profile, "cron", "resume", job_id),
        capture_output=True, text=True, timeout=15,
    )
    if result.returncode != 0:
        raise HTTPException(status_code=500, detail=result.stderr.strip()[:200])
    return {"ok": True}


# ── tasks ─────────────────────────────────────────────────────────────────────

@router.get("/api/office/workspace/{profile}/tasks")
def get_tasks(profile: str, _: str = Depends(verify_auth)):
    validate_profile(profile)
    p = _tasks_path(profile)
    if not p.exists():
        return []
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return []


class TaskItem(BaseModel):
    id: str
    title: str
    status: str = "todo"
    assigned_by: str = "user"
    created_at: str = ""
    priority: str = "normal"


@router.put("/api/office/workspace/{profile}/tasks")
def update_tasks(profile: str, tasks: list[TaskItem], _: str = Depends(verify_auth)):
    validate_profile(profile)
    p = _tasks_path(profile)
    p.write_text(json.dumps([t.model_dump() for t in tasks], ensure_ascii=False, indent=2), encoding="utf-8")
    return {"ok": True}


# ── files ────────────────────────────────────────────────────────────────────

@router.get("/api/office/workspace/{profile}/files")
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
                    "modified": ts_to_iso(stat.st_mtime),
                    "ext": item.suffix,
                })
            except Exception:
                pass
    return files[:200]


# ── notifications ─────────────────────────────────────────────────────────────

@router.get("/api/office/workspace/{profile}/notifications")
def get_notifications(profile: str, _: str = Depends(verify_auth)):
    validate_profile(profile)
    return _get_notifications(profile)


# ── docs (memories) ─────────────────────────────────────────────────────────

class DocUpdate(BaseModel):
    content: str = Field(..., max_length=200000)


@router.get("/api/office/workspace/{profile}/docs")
def get_docs(profile: str, _: str = Depends(verify_auth)):
    validate_profile(profile)
    docs = _collect_docs(_memories_dir(profile))
    for shared_dir in SHARED_DIRS:
        docs += _collect_docs(shared_dir, id_prefix="shared__")
    return docs


@router.put("/api/office/workspace/{profile}/docs/{doc_id}")
def update_doc(profile: str, doc_id: str, payload: DocUpdate, _: str = Depends(verify_auth)):
    validate_profile(profile)
    mem_dir = _memories_dir(profile)
    if not mem_dir.exists():
        raise HTTPException(status_code=404, detail="Profile memories not found")
    doc_path = _safe_doc_path(profile, doc_id)
    doc_path.write_text(payload.content, encoding="utf-8")
    return {"ok": True}


# ── activity ─────────────────────────────────────────────────────────────────

@router.get("/api/office/workspace/{profile}/activity")
def get_activity(profile: str, _: str = Depends(verify_auth)):
    profile = resolve_profile(profile)
    return _get_activity(profile)


# ── helper functions ──────────────────────────────────────────────────────────

def _workspace_dir(profile: str) -> Path:
    d = _existing_profile_dir(resolve_profile(profile)) / "workspace"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _tasks_path(profile: str) -> Path:
    return _workspace_dir(profile) / "tasks.json"


def _memories_dir(profile: str) -> Path:
    return _existing_profile_dir(resolve_profile(profile)) / "memories"


def _safe_doc_path(profile: str, doc_id: str) -> Path:
    if not re.match(r"^[\w.\-]{1,80}$", doc_id):
        raise HTTPException(status_code=400, detail="Invalid doc id")
    return _memories_dir(profile) / f"{doc_id}.md"


def _parse_cron_output(text: str) -> list:
    jobs = []
    current: dict = {}
    for line in text.splitlines():
        line = line.strip()
        m = re.match(r'^([a-f0-9]{8,})\s+\[(.*?)\]$', line)
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
            m2 = re.match(rf'^{field}:\s+(.+)$', line)
            if m2:
                val = m2.group(1).strip()
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
                "started_at": ts_to_iso(started),
                "ended_at": ts_to_iso(ended) if ended else None,
                "message_count": msg_count or 0,
                "input_tokens": inp_tok or 0,
                "output_tokens": out_tok or 0,
                "end_reason": end_reason,
            })
        return result
    except Exception:
        return []


def _collect_docs(directory: Path, id_prefix: str = "") -> list:
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
                    "updated_at": ts_to_iso(stat.st_mtime),
                    "source": "shared" if id_prefix else "profile",
                })
            except Exception:
                pass
    return docs


def _get_tool_activity(profile: str, session_id: Optional[str] = None) -> Optional[dict]:
    from src.services.profile_service import _get_latest_session
    from src.services.chat_service import api_request
    session_id = session_id or _get_latest_session(profile)
    db = _db_path(profile)
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
            calls = json.loads(msg["tool_calls"])
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
            "last_activity": ts_to_iso(msg["timestamp"]),
        }
    except Exception:
        return None


def _get_activity(profile: str) -> dict:
    from src.services.profile_service import _get_latest_session
    from src.services.chat_service import api_request
    profile = resolve_profile(profile)
    db = _db_path(profile)
    if not db:
        return {"active": False, "stage": "offline", "label": "Offline", "tool": None}

    with RUN_LOCK:
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
