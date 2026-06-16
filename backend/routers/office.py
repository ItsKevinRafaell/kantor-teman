import re, html as html_mod, random, asyncio, uuid, json, csv, io, base64, hmac, time, httpx
import os
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv
from fastapi import APIRouter, Depends, HTTPException, Request, BackgroundTasks, UploadFile, File, Form, Query, Body
from fastapi.responses import StreamingResponse, RedirectResponse, HTMLResponse, Response
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from typing import Optional, List, Any
from models import get_db, User
from schemas import *
from app.core.dependencies import (get_current_user, require_admin, UPLOADS_DIR,
    HERMES_GATEWAY_URL, _hermes_headers, _office_profile)

router = APIRouter()


@router.get("/api/office/health")
async def office_health():
    return {"ok": True, "source": "kantor-teman"}


@router.post("/api/office/chat/{profile}")
async def office_chat(profile: str, body: OfficeChatRequest, current_user: User = Depends(get_current_user)):
    if not HERMES_GATEWAY_URL:
        raise HTTPException(status_code=503, detail="Hermes gateway not configured")
    profile = _office_profile(profile)
    payload = {"message": body.message, "session_id": body.session_id}
    if body.attachments:
        payload["attachments"] = [a.model_dump() for a in body.attachments]
    async with httpx.AsyncClient(timeout=130) as client:
        resp = await client.post(
            f"{HERMES_GATEWAY_URL}/api/office/chat/{profile}",
            headers=_hermes_headers(),
            json=payload,
        )
    if resp.status_code != 200:
        raise HTTPException(status_code=502, detail=f"Hermes error: {resp.text[:200]}")
    return resp.json()



@router.get("/api/office/status")
async def office_status(current_user: User = Depends(get_current_user)):
    if not HERMES_GATEWAY_URL:
        return {}
    async with httpx.AsyncClient(timeout=10) as client:
        try:
            resp = await client.get(f"{HERMES_GATEWAY_URL}/api/office/status", headers=_hermes_headers())
            return resp.json()
        except Exception:
            return {}



@router.get("/api/office/history/{profile}")
async def office_history(profile: str, request: Request, current_user: User = Depends(get_current_user)):
    if not HERMES_GATEWAY_URL:
        return []
    profile = _office_profile(profile)
    async with httpx.AsyncClient(timeout=120) as client:
        resp = await client.get(
            f"{HERMES_GATEWAY_URL}/api/office/history/{profile}",
            params=dict(request.query_params),
            headers=_hermes_headers(),
        )
    if resp.status_code != 200:
        raise HTTPException(status_code=502, detail=f"Hermes error: {resp.text[:200]}")
    return resp.json()



@router.get("/api/office/timeline/{profile}")
async def office_timeline(profile: str, after: int = -1, current_user: User = Depends(get_current_user)):
    if not HERMES_GATEWAY_URL:
        return {"events": [], "next_cursor": after, "has_more": False, "pending_approval_count": 0}
    profile = _office_profile(profile)
    async with httpx.AsyncClient(timeout=10) as client:
        try:
            resp = await client.get(
                f"{HERMES_GATEWAY_URL}/api/office/timeline/{profile}",
                params={"after": after},
                headers=_hermes_headers()
            )
            return resp.json()
        except Exception:
            return {"events": [], "next_cursor": after, "has_more": False, "pending_approval_count": 0}



@router.get("/api/office/conversations/{profile}")
async def office_conversations(profile: str, current_user: User = Depends(get_current_user)):
    if not HERMES_GATEWAY_URL:
        return []
    profile = _office_profile(profile)
    async with httpx.AsyncClient(timeout=10) as client:
        try:
            resp = await client.get(f"{HERMES_GATEWAY_URL}/api/office/conversations/{profile}", headers=_hermes_headers())
            return resp.json()
        except Exception:
            return []



@router.get("/api/office/conversations/{profile}/{session_id}")
async def office_conversation_messages(profile: str, session_id: str, current_user: User = Depends(get_current_user)):
    if not HERMES_GATEWAY_URL:
        return []
    profile = _office_profile(profile)
    async with httpx.AsyncClient(timeout=10) as client:
        try:
            resp = await client.get(f"{HERMES_GATEWAY_URL}/api/office/conversations/{profile}/{session_id}", headers=_hermes_headers())
            return resp.json()
        except Exception:
            return []


# ---------- HR Desk: agent CRUD proxy ----------

class OfficeAgentCreate(BaseModel):
    name: str
    display_name: Optional[str] = None
    description: Optional[str] = None
    model: Optional[str] = None
    base_url: Optional[str] = None
    api_key: Optional[str] = None
    soul: Optional[str] = None
    telegram_token: Optional[str] = None
    telegram_allowed_users: Optional[str] = None


class OfficeSoulUpdate(BaseModel):
    soul: str


class OfficeEnvUpdate(BaseModel):
    telegram_token: Optional[str] = None
    telegram_allowed_users: Optional[str] = None


class OfficeConfigUpdate(BaseModel):
    model: Optional[str] = None
    base_url: Optional[str] = None
    api_key: Optional[str] = None


def _require_gateway():
    if not HERMES_GATEWAY_URL:
        raise HTTPException(status_code=503, detail="Hermes gateway not configured")


def _office_proxy_requires_admin(method: str, path: str) -> bool:
    if method.upper() in {"GET", "HEAD", "OPTIONS"}:
        return False
    admin_prefixes = (
        "agents/",
        "hermes/agents/",
    )
    return any(path == prefix.rstrip("/") or path.startswith(prefix) for prefix in admin_prefixes)


async def _office_proxy(request: Request, path: str, timeout: float = 60.0) -> Response:
    _require_gateway()
    body = await request.body() if request.method.upper() not in {"GET", "HEAD"} else None
    headers = _hermes_headers()
    content_type = request.headers.get("content-type")
    if content_type:
        headers["Content-Type"] = content_type
    upstream = f"{HERMES_GATEWAY_URL}/api/office/{path}"
    params = dict(request.query_params)
    async with httpx.AsyncClient(timeout=timeout) as client:
        try:
            resp = await client.request(
                request.method,
                upstream,
                params=params,
                headers=headers,
                content=body,
            )
        except httpx.RequestError as exc:
            raise HTTPException(status_code=502, detail=f"Hermes gateway unreachable: {exc}") from exc

    excluded = {"connection", "content-length", "content-encoding", "transfer-encoding"}
    response_headers = {
        name: value
        for name, value in resp.headers.items()
        if name.lower() not in excluded
    }
    return Response(
        content=resp.content,
        status_code=resp.status_code,
        headers=response_headers,
        media_type=resp.headers.get("content-type"),
    )


async def _office_stream_proxy(request: Request, path: str) -> StreamingResponse:
    _require_gateway()
    body = await request.body() if request.method.upper() not in {"GET", "HEAD"} else None
    headers = _hermes_headers()
    content_type = request.headers.get("content-type")
    if content_type:
        headers["Content-Type"] = content_type
    upstream = f"{HERMES_GATEWAY_URL}/api/office/{path}"
    params = dict(request.query_params)
    client = httpx.AsyncClient(timeout=httpx.Timeout(60.0, read=None))
    stream = client.stream(
        request.method,
        upstream,
        params=params,
        headers=headers,
        content=body,
    )
    try:
        resp = await stream.__aenter__()
    except httpx.RequestError as exc:
        await client.aclose()
        raise HTTPException(status_code=502, detail=f"Hermes gateway unreachable: {exc}") from exc

    excluded = {"connection", "content-length", "content-encoding", "transfer-encoding"}
    response_headers = {
        name: value
        for name, value in resp.headers.items()
        if name.lower() not in excluded
    }

    async def event_chunks():
        try:
            async for chunk in resp.aiter_bytes():
                if await request.is_disconnected():
                    break
                yield chunk
        finally:
            await stream.__aexit__(None, None, None)
            await client.aclose()

    return StreamingResponse(
        event_chunks(),
        status_code=resp.status_code,
        headers=response_headers,
        media_type=resp.headers.get("content-type", "text/event-stream"),
    )


async def _office_telegram_mirror_stream(request: Request) -> StreamingResponse:
    _require_gateway()
    params = dict(request.query_params)
    after = int(params.get("after", 0) or 0)
    limit = max(1, min(int(params.get("limit", 200) or 200), 500))
    requested = params.get("profiles") or params.get("profile") or ""

    async def stream():
        cursor = after
        while not await request.is_disconnected():
            try:
                mirror_params = {"after": cursor, "limit": limit}
                if requested:
                    key = "profiles" if "," in requested else "profile"
                    mirror_params[key] = requested
                async with httpx.AsyncClient(timeout=30) as client:
                    resp = await client.get(
                        f"{HERMES_GATEWAY_URL}/api/office/telegram/mirror",
                        params=mirror_params,
                        headers=_hermes_headers(),
                    )
                resp.raise_for_status()
                payload = resp.json()
                next_cursor = int(payload.get("next_cursor", cursor) or cursor)
                events = payload.get("events") or []
                if events:
                    cursor = next_cursor
                    yield f"id: {cursor}\nevent: mirror\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"
                else:
                    cursor = next_cursor
                    yield f": keepalive {int(time.time())}\n\n"
            except Exception as exc:
                yield f"event: error\ndata: {json.dumps({'detail': str(exc)[:500], 'next_cursor': cursor}, ensure_ascii=False)}\n\n"
            await asyncio.sleep(0.8)

    return StreamingResponse(
        stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )



@router.get("/api/office/agents")
async def office_list_agents(current_user: User = Depends(get_current_user)):
    _require_gateway()
    async with httpx.AsyncClient(timeout=15) as client:
        try:
            resp = await client.get(f"{HERMES_GATEWAY_URL}/api/office/agents", headers=_hermes_headers())
            return resp.json()
        except Exception as e:
            raise HTTPException(status_code=502, detail=str(e))



@router.post("/api/office/agents")
async def office_create_agent(body: OfficeAgentCreate, current_user: User = Depends(require_admin)):
    _require_gateway()
    async with httpx.AsyncClient(timeout=90) as client:
        resp = await client.post(
            f"{HERMES_GATEWAY_URL}/api/office/agents",
            headers=_hermes_headers(),
            json=body.model_dump(exclude_none=True),
        )
    if resp.status_code not in (200, 201):
        raise HTTPException(status_code=resp.status_code, detail=resp.text[:300])
    return resp.json()



@router.delete("/api/office/agents/{profile}")
async def office_delete_agent(profile: str, current_user: User = Depends(require_admin)):
    _require_gateway()
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.delete(
            f"{HERMES_GATEWAY_URL}/api/office/agents/{profile}",
            headers=_hermes_headers(),
        )
    if resp.status_code not in (200, 204):
        raise HTTPException(status_code=resp.status_code, detail=resp.text[:300])
    return resp.json()



@router.put("/api/office/agents/{profile}/soul")
async def office_update_soul(profile: str, body: OfficeSoulUpdate, current_user: User = Depends(require_admin)):
    _require_gateway()
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.put(
            f"{HERMES_GATEWAY_URL}/api/office/agents/{profile}/soul",
            headers=_hermes_headers(),
            json={"soul": body.soul},
        )
    if resp.status_code != 200:
        raise HTTPException(status_code=resp.status_code, detail=resp.text[:300])
    return resp.json()



@router.put("/api/office/agents/{profile}/env")
async def office_update_env(profile: str, body: OfficeEnvUpdate, current_user: User = Depends(require_admin)):
    _require_gateway()
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.put(
            f"{HERMES_GATEWAY_URL}/api/office/agents/{profile}/env",
            headers=_hermes_headers(),
            json=body.model_dump(exclude_none=True),
        )
    if resp.status_code != 200:
        raise HTTPException(status_code=resp.status_code, detail=resp.text[:300])
    return resp.json()



@router.put("/api/office/agents/{profile}/config")
async def office_update_config(profile: str, body: OfficeConfigUpdate, current_user: User = Depends(require_admin)):
    _require_gateway()
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.put(
            f"{HERMES_GATEWAY_URL}/api/office/agents/{profile}/config",
            headers=_hermes_headers(),
            json=body.model_dump(exclude_none=True),
        )
    if resp.status_code != 200:
        raise HTTPException(status_code=resp.status_code, detail=resp.text[:300])
    return resp.json()


@router.api_route(
    "/api/office/{path:path}",
    methods=["GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"],
)
async def office_gateway_proxy(
    path: str,
    request: Request,
    current_user: User = Depends(get_current_user),
):
    if _office_proxy_requires_admin(request.method, path) and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Akses ditolak: hanya admin")
    if path == "telegram/mirror/stream":
        return await _office_telegram_mirror_stream(request)
    timeout = 180.0 if path == "telegram/mirror" else 130.0 if path.startswith("chat/") else 60.0
    return await _office_proxy(request, path, timeout=timeout)
