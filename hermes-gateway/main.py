import base64
import os
import re
import sqlite3
import subprocess
import tempfile
from pathlib import Path
from typing import List, Optional

import yaml
from fastapi import FastAPI, HTTPException, Security
from fastapi.security import APIKeyHeader
from pydantic import BaseModel, Field

app = FastAPI(title="Hermes Gateway", version="1.1.0")

GATEWAY_TOKEN = os.getenv("HERMES_GATEWAY_TOKEN", "change-me")
HERMES_BIN = os.getenv("HERMES_BIN", "/usr/local/bin/hermes")
PROFILES_DIR = Path("/root/.hermes/profiles")
DB_TEMPLATE = str(PROFILES_DIR / "{profile}" / "state.db")

PROFILE_RE = re.compile(r"^[a-z][a-z0-9_-]{1,30}$")

api_key_header = APIKeyHeader(name="X-Gateway-Token", auto_error=True)


def verify_token(key: str = Security(api_key_header)) -> str:
    if key != GATEWAY_TOKEN:
        raise HTTPException(status_code=401, detail="Invalid gateway token")
    return key


def validate_profile(profile: str) -> str:
    if not PROFILE_RE.match(profile):
        raise HTTPException(status_code=400, detail="Invalid profile name (must match ^[a-z][a-z0-9_-]{1,30}$)")
    return profile


# ---------- chat ----------

class ChatAttachment(BaseModel):
    name: str
    type: str
    data: str  # base64 data URL


class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None
    attachments: Optional[List[ChatAttachment]] = None


def _get_latest_session(profile: str) -> Optional[str]:
    db_path = DB_TEMPLATE.format(profile=profile)
    if not os.path.exists(db_path):
        return None
    try:
        con = sqlite3.connect(db_path)
        row = con.execute("SELECT id FROM sessions ORDER BY started_at DESC LIMIT 1").fetchone()
        con.close()
        return row[0] if row else None
    except Exception:
        return None


def _get_history(profile: str, limit: int = 20) -> list:
    db_path = DB_TEMPLATE.format(profile=profile)
    if not os.path.exists(db_path):
        return []
    try:
        con = sqlite3.connect(db_path)
        try:
            rows = con.execute(
                "SELECT m.role, m.content, m.created_at FROM messages m JOIN sessions s ON m.session_id = s.id ORDER BY m.created_at DESC LIMIT ?",
                (limit,),
            ).fetchall()
        except Exception:
            rows = []
        con.close()
        result = [{"role": r[0], "content": r[1], "created_at": r[2]} for r in rows]
        result.reverse()
        return result
    except Exception:
        return []


def _save_attachments(attachments: List[ChatAttachment], profile: str) -> List[str]:
    """Save base64 attachments to profile uploads dir, return file paths."""
    upload_dir = PROFILES_DIR / profile / "uploads"
    upload_dir.mkdir(parents=True, exist_ok=True)
    paths = []
    for att in attachments:
        data = att.data
        if "," in data:
            data = data.split(",", 1)[1]
        try:
            raw = base64.b64decode(data)
        except Exception:
            continue
        ext = Path(att.name).suffix or ".bin"
        tmp = tempfile.NamedTemporaryFile(
            dir=str(upload_dir), suffix=ext, prefix=f"{att.name.split('.')[0]}_", delete=False
        )
        tmp.write(raw)
        tmp.close()
        paths.append(tmp.name)
    return paths


@app.post("/chat/{profile}")
def chat(profile: str, req: ChatRequest, _: str = Security(verify_token)):
    validate_profile(profile)

    # Build message with attachment references
    message = req.message
    file_paths: List[str] = []
    if req.attachments:
        file_paths = _save_attachments(req.attachments, profile)
        if file_paths:
            file_list = "\n".join(f"- {p}" for p in file_paths)
            message = f"{req.message}\n\n[Attached files]\n{file_list}"

    cmd = [HERMES_BIN, "--profile", profile]
    if req.session_id:
        cmd += ["--resume", req.session_id]
    cmd += ["-z", message]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=504, detail="Hermes timed out (120s)")
    except FileNotFoundError:
        raise HTTPException(status_code=503, detail=f"Hermes binary not found: {HERMES_BIN}")
    if result.returncode != 0:
        raise HTTPException(status_code=500, detail=f"Hermes error: {result.stderr.strip()[:300]}")
    return {
        "response": result.stdout.strip(),
        "session_id": _get_latest_session(profile),
        "profile": profile,
    }


@app.get("/status")
def status(_: str = Security(verify_token)):
    if not PROFILES_DIR.exists():
        return {}
    out = {}
    for p in PROFILES_DIR.iterdir():
        if not p.is_dir():
            continue
        out[p.name] = "idle" if (p / "state.db").exists() else "offline"
    return out


@app.get("/history/{profile}")
def history(profile: str, limit: int = 20, _: str = Security(verify_token)):
    validate_profile(profile)
    return _get_history(profile, limit)


@app.get("/conversations/{profile}")
def list_conversations(profile: str, _: str = Security(verify_token)):
    """List all conversation sessions for a profile with preview."""
    validate_profile(profile)
    db_path = DB_TEMPLATE.format(profile=profile)
    if not os.path.exists(db_path):
        return []
    try:
        con = sqlite3.connect(db_path)
        sessions = con.execute(
            "SELECT id, started_at FROM sessions ORDER BY started_at DESC"
        ).fetchall()
        result = []
        for sid, started_at in sessions:
            first_msg = con.execute(
                "SELECT content FROM messages WHERE session_id = ? AND role = 'user' ORDER BY created_at ASC LIMIT 1",
                (sid,),
            ).fetchone()
            msg_count = con.execute(
                "SELECT COUNT(*) FROM messages WHERE session_id = ?", (sid,)
            ).fetchone()
            result.append({
                "session_id": sid,
                "started_at": started_at,
                "preview": (first_msg[0][:80] if first_msg else ""),
                "message_count": msg_count[0] if msg_count else 0,
            })
        con.close()
        return result
    except Exception:
        return []


@app.get("/conversations/{profile}/{session_id}")
def get_conversation(profile: str, session_id: str, _: str = Security(verify_token)):
    """Get all messages for a specific conversation session."""
    validate_profile(profile)
    db_path = DB_TEMPLATE.format(profile=profile)
    if not os.path.exists(db_path):
        return []
    try:
        con = sqlite3.connect(db_path)
        rows = con.execute(
            "SELECT role, content, created_at FROM messages WHERE session_id = ? ORDER BY created_at ASC",
            (session_id,),
        ).fetchall()
        con.close()
        return [{"role": r[0], "content": r[1], "created_at": r[2]} for r in rows]
    except Exception:
        return []


@app.get("/health")
def health():
    return {"ok": True}


# ---------- HR Desk: agent CRUD ----------

class AgentCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=31)
    display_name: str = Field("", max_length=64)
    description: str = Field("", max_length=200)
    model: str = Field("test-mimo/mimo-v2.5-pro", max_length=128)
    base_url: str = Field("http://localhost:20128/v1", max_length=256)
    api_key: str = Field("dummy-9router", max_length=256)
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


def _read_soul_preview(profile_dir: Path, max_chars: int = 200) -> str:
    soul = profile_dir / "SOUL.md"
    if not soul.exists():
        return ""
    try:
        text = soul.read_text(encoding="utf-8")
        return text[:max_chars]
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
    if "model" in updates and updates["model"]:
        model_section["default"] = updates["model"]
    if "base_url" in updates and updates["base_url"]:
        model_section["base_url"] = updates["base_url"]
    if "api_key" in updates and updates["api_key"]:
        model_section["api_key"] = updates["api_key"]
    if model_section:
        cfg["model"] = model_section
    cfg_path.write_text(yaml.safe_dump(cfg, sort_keys=False), encoding="utf-8")


def _read_env_keys(profile_dir: Path) -> list[str]:
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
    """Update specific env vars, preserve others. Never log values."""
    env_path = profile_dir / ".env"
    existing: dict[str, str] = {}
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.rstrip("\n")
            if line and not line.lstrip().startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                existing[k.strip()] = v
    for k, v in updates.items():
        if v is None or v == "":
            continue
        existing[k] = v
    lines = [f"{k}={v}" for k, v in existing.items()]
    env_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    os.chmod(env_path, 0o600)


@app.get("/agents")
def list_agents(_: str = Security(verify_token)):
    if not PROFILES_DIR.exists():
        return []
    out = []
    for p in PROFILES_DIR.iterdir():
        if not p.is_dir():
            continue
        cfg = _read_config(p)
        model_section = cfg.get("model", {}) if isinstance(cfg.get("model"), dict) else {}
        # Read description from .description file if it exists (hermes profile describe)
        desc_path = p / ".description"
        description = desc_path.read_text(encoding="utf-8").strip() if desc_path.exists() else ""
        out.append({
            "profile": p.name,
            "name": p.name.capitalize(),
            "role": description,
            "model": model_section.get("default", ""),
            "soul_preview": _read_soul_preview(p),
            "env_keys": _read_env_keys(p),  # keys only, no values
            "online": (p / "state.db").exists(),
        })
    return out


@app.post("/agents")
def create_agent(payload: AgentCreate, _: str = Security(verify_token)):
    profile = payload.name
    validate_profile(profile)
    profile_dir = PROFILES_DIR / profile
    if profile_dir.exists():
        raise HTTPException(status_code=409, detail=f"Profile '{profile}' already exists")

    # Run hermes profile create
    cmd = [HERMES_BIN, "profile", "create", profile]
    if payload.description:
        cmd += ["--description", payload.description]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=504, detail="hermes profile create timed out")
    except FileNotFoundError:
        raise HTTPException(status_code=503, detail=f"Hermes binary not found: {HERMES_BIN}")
    if result.returncode != 0:
        raise HTTPException(status_code=500, detail=f"profile create failed: {result.stderr.strip()[:300]}")

    if not profile_dir.exists():
        raise HTTPException(status_code=500, detail="Profile dir not created — check hermes installation")

    # Write SOUL.md (display name shown to agent)
    if payload.soul:
        (profile_dir / "SOUL.md").write_text(payload.soul, encoding="utf-8")

    # Write config.yaml model section
    _write_config(profile_dir, {
        "model": payload.model,
        "base_url": payload.base_url,
        "api_key": payload.api_key,
    })

    # Write .env (telegram + base provider keys)
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


@app.delete("/agents/{profile}")
def delete_agent(profile: str, _: str = Security(verify_token)):
    validate_profile(profile)
    profile_dir = PROFILES_DIR / profile
    if not profile_dir.exists():
        raise HTTPException(status_code=404, detail=f"Profile '{profile}' not found")
    cmd = [HERMES_BIN, "profile", "delete", profile, "--yes"]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=504, detail="profile delete timed out")
    if result.returncode != 0:
        # Some hermes versions use -y instead of --yes; try fallback
        cmd2 = [HERMES_BIN, "profile", "delete", profile, "-y"]
        result = subprocess.run(cmd2, capture_output=True, text=True, timeout=60)
        if result.returncode != 0:
            raise HTTPException(status_code=500, detail=f"profile delete failed: {result.stderr.strip()[:300]}")
    return {"ok": True}


@app.put("/agents/{profile}/soul")
def update_soul(profile: str, payload: SoulUpdate, _: str = Security(verify_token)):
    validate_profile(profile)
    profile_dir = PROFILES_DIR / profile
    if not profile_dir.exists():
        raise HTTPException(status_code=404, detail=f"Profile '{profile}' not found")
    (profile_dir / "SOUL.md").write_text(payload.soul, encoding="utf-8")
    return {"ok": True}


@app.put("/agents/{profile}/env")
def update_env(profile: str, payload: EnvUpdate, _: str = Security(verify_token)):
    validate_profile(profile)
    profile_dir = PROFILES_DIR / profile
    if not profile_dir.exists():
        raise HTTPException(status_code=404, detail=f"Profile '{profile}' not found")
    updates = {}
    if payload.telegram_token is not None:
        updates["TELEGRAM_BOT_TOKEN"] = payload.telegram_token
    if payload.telegram_allowed_users is not None:
        updates["TELEGRAM_ALLOWED_USERS"] = payload.telegram_allowed_users
    if updates:
        _write_env(profile_dir, updates)
    return {"ok": True}


@app.put("/agents/{profile}/config")
def update_agent_config(profile: str, payload: ConfigUpdate, _: str = Security(verify_token)):
    validate_profile(profile)
    profile_dir = PROFILES_DIR / profile
    if not profile_dir.exists():
        raise HTTPException(status_code=404, detail=f"Profile '{profile}' not found")
    _write_config(profile_dir, payload.dict(exclude_none=True))
    return {"ok": True}
