import os
import sqlite3
import subprocess
from typing import Optional

from fastapi import FastAPI, HTTPException, Security
from fastapi.security import APIKeyHeader
from pydantic import BaseModel

app = FastAPI(title="Hermes Gateway", version="1.0.0")

GATEWAY_TOKEN = os.getenv("HERMES_GATEWAY_TOKEN", "change-me")
DB_TEMPLATE = "/root/.hermes/profiles/{profile}/state.db"
HERMES_BIN = os.getenv("HERMES_BIN", "/usr/bin/hermes")

api_key_header = APIKeyHeader(name="X-Gateway-Token", auto_error=True)


def verify_token(key: str = Security(api_key_header)) -> str:
    if key != GATEWAY_TOKEN:
        raise HTTPException(status_code=401, detail="Invalid gateway token")
    return key


class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None


def _get_latest_session(profile: str) -> Optional[str]:
    db_path = DB_TEMPLATE.format(profile=profile)
    if not os.path.exists(db_path):
        return None
    try:
        con = sqlite3.connect(db_path)
        row = con.execute(
            "SELECT id FROM sessions ORDER BY started_at DESC LIMIT 1"
        ).fetchone()
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
        # Try messages table — schema may vary by hermes version
        try:
            rows = con.execute(
                """
                SELECT m.role, m.content, m.created_at
                FROM messages m
                JOIN sessions s ON m.session_id = s.id
                ORDER BY m.created_at DESC
                LIMIT ?
                """,
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


@app.post("/chat/{profile}")
def chat(profile: str, req: ChatRequest, _: str = Security(verify_token)):
    cmd = [HERMES_BIN, "--profile", profile]
    if req.session_id:
        cmd += ["--resume", req.session_id]
    cmd += ["-z", req.message]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=120,
        )
    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=504, detail="Hermes timed out (120s)")
    except FileNotFoundError:
        raise HTTPException(status_code=503, detail=f"Hermes binary not found: {HERMES_BIN}")

    if result.returncode != 0:
        raise HTTPException(
            status_code=500,
            detail=f"Hermes error: {result.stderr.strip()[:300]}",
        )

    session_id = _get_latest_session(profile)

    return {
        "response": result.stdout.strip(),
        "session_id": session_id,
        "profile": profile,
    }


@app.get("/status")
def status(_: str = Security(verify_token)):
    profiles_dir = "/root/.hermes/profiles"
    if not os.path.exists(profiles_dir):
        return {}
    statuses = {}
    for profile in os.listdir(profiles_dir):
        db_path = DB_TEMPLATE.format(profile=profile)
        if os.path.exists(db_path):
            statuses[profile] = "idle"
        else:
            statuses[profile] = "offline"
    return statuses


@app.get("/history/{profile}")
def history(profile: str, limit: int = 20, _: str = Security(verify_token)):
    return _get_history(profile, limit)


@app.get("/health")
def health():
    return {"ok": True}
