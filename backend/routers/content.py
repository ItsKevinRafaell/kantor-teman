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
from models import get_db, log_audit, User, AIModel, SystemSettings, ContentSchedule, ContentProvider, ContentSession, ContentGeneration, AIProxy
from schemas import *
from app.core.dependencies import (get_current_user, require_admin,
    _ai_model_to_out, _get_google_calendar_service, _get_setting,
    _get_feature_defaults, get_proxy_for_feature,
    get_default_model, get_ai_config, sync_to_google_calendar,
)
from app.services.ai_service import (
    _canonical_provider,
    _router_api_key,
    _router_base_url,
    _is_9router_url,
    _router_model,
    fetch_9router_models_async,
)

router = APIRouter()

@router.get("/api/ai-models")
def list_ai_models(active_only: bool = Query(False), capability: Optional[str] = Query(None), current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    query = db.query(AIModel)
    if active_only:
        query = query.filter(AIModel.is_active == 1)
    models = query.order_by(AIModel.name).all()
    out = [_ai_model_to_out(m) for m in models]
    if capability:
        out = [m for m in out if capability in m["capabilities"]]
    return out



@router.post("/api/ai-models", response_model=dict, status_code=201)
def create_ai_model(body: AIModelIn, current_user: User = Depends(require_admin), db: Session = Depends(get_db)):
    body.capabilities = [c for c in body.capabilities if c in ("article", "analysis")]
    if not body.capabilities:
        raise HTTPException(status_code=400, detail="Pilih minimal satu fitur: article atau analysis")
    m = AIModel(
        name=body.name,
        model_id=body.model_id,
        description=body.description,
        capabilities=json.dumps(body.capabilities),
        is_active=1 if body.is_active else 0,
    )
    db.add(m)
    db.commit()
    db.refresh(m)
    return _ai_model_to_out(m)



@router.put("/api/ai-models/{model_id}")
def update_ai_model(model_id: str, body: AIModelIn, current_user: User = Depends(require_admin), db: Session = Depends(get_db)):
    m = db.query(AIModel).filter(AIModel.id == model_id).first()
    if not m:
        raise HTTPException(status_code=404, detail="Model tidak ditemukan")
    body.capabilities = [c for c in body.capabilities if c in ("article", "analysis")]
    if not body.capabilities:
        raise HTTPException(status_code=400, detail="Pilih minimal satu fitur: article atau analysis")
    m.name = body.name
    m.model_id = body.model_id
    m.description = body.description
    m.capabilities = json.dumps(body.capabilities)
    m.is_active = 1 if body.is_active else 0
    db.commit()
    db.refresh(m)
    return _ai_model_to_out(m)



@router.delete("/api/ai-models/{model_id}", status_code=204)
def delete_ai_model(model_id: str, current_user: User = Depends(require_admin), db: Session = Depends(get_db)):
    m = db.query(AIModel).filter(AIModel.id == model_id).first()
    if not m:
        raise HTTPException(status_code=404, detail="Model tidak ditemukan")
    db.delete(m)
    db.commit()



@router.post("/api/ai-models/{model_id}/set-default")
def set_default_ai_model(model_id: str, capability: str = Query(...), current_user: User = Depends(require_admin), db: Session = Depends(get_db)):
    """Set this model as default for an active AI capability."""
    if capability not in ("article", "analysis"):
        raise HTTPException(status_code=400, detail="Capability tidak valid")
    m = db.query(AIModel).filter(AIModel.id == model_id).first()
    if not m:
        raise HTTPException(status_code=404, detail="Model tidak ditemukan")
    field = f"is_default_{capability}"
    # Reset all defaults for this capability
    db.query(AIModel).update({field: 0})
    setattr(m, field, 1)
    db.commit()
    return {"ok": True, "default_for": capability, "model_id": m.id}


def get_default_model(db: Session, capability: str) -> Optional[AIModel]:
    """Get the default AI model for a given capability."""
    field = f"is_default_{capability}"
    return db.query(AIModel).filter(getattr(AIModel, field) == 1, AIModel.is_active == 1).first()


# ---------------------------------------------------------------------------
# 9router AI Config
# ---------------------------------------------------------------------------

def _get_system_ai_config(db: Session) -> dict:
    """Return 9router config for content generation."""
    return get_ai_config(db, "chat")


def _call_text_gen(messages: list, api_key: str, base_url: str, model: str, max_tokens: int) -> str:
    """Call 9router /chat/completions endpoint for text generation."""
    url = f"{base_url.rstrip('/')}/chat/completions"
    with httpx.Client(timeout=120) as client:
        resp = client.post(
            url,
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={"model": model, "max_tokens": max_tokens, "messages": messages},
        )
        if resp.status_code != 200:
            raise HTTPException(status_code=502, detail=f"AI call failed: {resp.status_code} - {resp.text[:300]}")
        return resp.json()["choices"][0]["message"]["content"]


@router.get("/api/ai/combos")
def list_ai_combos(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Return saved 9router endpoint/model choices."""
    proxies = db.query(AIProxy).order_by(AIProxy.created_at.asc()).all()
    return [{"name": p.name, "display_name": f"9router ({p.model})", "provider": "9router", "model": p.model} for p in proxies]


@router.get("/api/ai/active-combo")
def get_active_combo(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Return the active 9router endpoint config."""
    proxy = get_proxy_for_feature(db, "chat")
    if proxy:
        return {"combo": proxy.name, "provider": "9router", "base_url": proxy.base_url, "model": proxy.model}
    return {"combo": "none", "provider": "9router", "base_url": "", "model": "", "status": "Endpoint 9router belum dikonfigurasi"}


@router.post("/api/ai/active-combo")
def set_active_combo(body: dict, current_user: User = Depends(require_admin), db: Session = Depends(get_db)):
    """Set active 9router endpoint by AIProxy ID."""
    proxy_id = body.get("proxy_id") or body.get("combo", "").strip()
    if not proxy_id:
        raise HTTPException(status_code=400, detail="Field 'proxy_id' wajib diisi")
    proxy = db.query(AIProxy).filter(AIProxy.id == proxy_id).first()
    if not proxy:
        raise HTTPException(status_code=404, detail="Endpoint 9router tidak ditemukan")
    db.query(AIProxy).filter(AIProxy.feature == proxy.feature).update({"is_active": False})
    proxy.is_active = True
    db.commit()
    return {"ok": True, "combo": proxy.name, "provider": "9router", "base_url": proxy.base_url, "model": proxy.model}


@router.post("/api/ai/proxy-url")
def set_proxy_url(body: dict, current_user: User = Depends(require_admin), db: Session = Depends(get_db)):
    """Set fallback 9router URL when no endpoint row is configured."""
    url = (body.get("url") or "").strip().rstrip("/")
    if not url:
        raise HTTPException(status_code=400, detail="Field 'url' wajib diisi")
    row = db.query(SystemSettings).filter_by(key="ai_proxy_url").first()
    if row:
        row.value = url
    else:
        db.add(SystemSettings(key="ai_proxy_url", value=url))
    db.commit()
    return {"ok": True, "proxy_url": url}


@router.get("/api/ai/feature-defaults")
def get_feature_defaults(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return _get_feature_defaults(db)


@router.get("/api/ai/router-models")
async def list_9router_models(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Fetch model/combo registry directly from 9router /v1/models."""
    config = get_ai_config(db, "chat")
    try:
        return await fetch_9router_models_async(config)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc))


@router.post("/api/ai/feature-defaults")
def set_feature_defaults(body: dict, current_user: User = Depends(require_admin), db: Session = Depends(get_db)):
    """Set per-feature AI proxy mappings. Values must be AIProxy IDs."""
    valid_features = {"article", "analysis"}
    valid_proxy_ids = {p.id for p in db.query(AIProxy.id).all()}
    cleaned: dict[str, str] = {}
    for feature, proxy_id in (body or {}).items():
        if feature not in valid_features:
            raise HTTPException(status_code=400, detail=f"Fitur AI '{feature}' tidak valid")
        pid = (proxy_id or "").strip()
        if pid and pid not in valid_proxy_ids:
            raise HTTPException(status_code=400, detail=f"Proxy ID '{pid}' tidak valid untuk fitur '{feature}'")
        cleaned[feature] = pid
    value = json.dumps(cleaned)
    row = db.query(SystemSettings).filter_by(key="ai_feature_defaults").first()
    if row:
        row.value = value
    else:
        db.add(SystemSettings(key="ai_feature_defaults", value=value))
    db.commit()
    return cleaned


@router.get("/api/ai/health")
async def ai_health(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Check 9router connectivity through /models."""
    config = get_ai_config(db, "chat")
    base = config.get("base_url", "")
    model = config.get("model", "")
    try:
        result = await fetch_9router_models_async(config)
        return {
            "status": "connected",
            "provider": "9router",
            "base_url": result["base_url"],
            "stored_base_url": config.get("stored_base_url", ""),
            "base_url_repaired": bool(config.get("base_url_repaired")),
            "model": model,
            "models_count": result["count"],
        }
    except Exception as e:
        print(f"[AI health] {e}", flush=True)
        return {
            "status": "offline",
            "provider": "9router",
            "base_url": base,
            "stored_base_url": config.get("stored_base_url", ""),
            "base_url_repaired": bool(config.get("base_url_repaired")),
            "model": model,
        }


# ---------------------------------------------------------------------------
# Search / Scrape
# ---------------------------------------------------------------------------


@router.get("/api/content-types")
def get_content_types(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    row = db.query(SystemSettings).filter_by(key="content_types").first()
    if row and row.value:
        return json.loads(row.value)
    # General calendar event types (not content-only)
    return [
        {"value": "MEETING", "label": "Meeting", "color": "#3b82f6"},
        {"value": "DEADLINE", "label": "Deadline", "color": "#ef4444"},
        {"value": "REMINDER", "label": "Reminder", "color": "#f59e0b"},
        {"value": "CLIENT", "label": "Klien", "color": "#8b5cf6"},
        {"value": "CONTENT", "label": "Konten", "color": "#10b981"},
        {"value": "PERSONAL", "label": "Personal", "color": "#6b7280"},
        {"value": "OTHER", "label": "Lainnya", "color": "#64748b"},
    ]



@router.put("/api/content-types")
def update_content_types(types: list[dict], current_user: User = Depends(require_admin), db: Session = Depends(get_db)):
    row = db.query(SystemSettings).filter_by(key="content_types").first()
    if row:
        row.value = json.dumps(types)
    else:
        db.add(SystemSettings(key="content_types", value=json.dumps(types)))
    db.commit()
    return types


class ContentScheduleIn(BaseModel):
    title: str
    type: str
    schedule_date: str
    status: str = "DRAFT"


class ContentScheduleUpdate(BaseModel):
    title: Optional[str] = None
    type: Optional[str] = None
    schedule_date: Optional[str] = None
    status: Optional[str] = None


class ContentScheduleOut(BaseModel):
    id: str
    title: str
    type: str
    schedule_date: str
    google_event_id: Optional[str] = None
    status: str
    created_at: str
    model_config = {"from_attributes": True}



@router.get("/api/content-schedule", response_model=list[ContentScheduleOut])
def get_content_schedules(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return db.query(ContentSchedule).order_by(ContentSchedule.schedule_date.asc()).all()



@router.post("/api/content-schedule", response_model=ContentScheduleOut, status_code=201)
def create_content_schedule(body: ContentScheduleIn, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    google_event_id = sync_to_google_calendar(
        body.title,
        body.schedule_date,
        description=f"[{body.type}] via Kantor Teman Kalender · status {body.status}",
    )

    schedule = ContentSchedule(
        id=str(uuid.uuid4()),
        title=body.title,
        type=body.type,
        schedule_date=body.schedule_date,
        google_event_id=google_event_id,
        status=body.status,
        created_at=datetime.now(timezone.utc).isoformat(),
    )
    db.add(schedule)
    db.commit()
    db.refresh(schedule)
    log_audit(db, current_user.name, "CREATE", "content_schedules", schedule.id, {
        "title": body.title, "type": body.type, "gcal": bool(google_event_id),
    })
    return schedule



@router.put("/api/content-schedule/{schedule_id}", response_model=ContentScheduleOut)
def update_content_schedule(schedule_id: str, body: ContentScheduleUpdate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    schedule = db.query(ContentSchedule).filter(ContentSchedule.id == schedule_id).first()
    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule tidak ditemukan")

    if body.title is not None:
        schedule.title = body.title
    if body.type is not None:
        schedule.type = body.type
    if body.schedule_date is not None:
        schedule.schedule_date = body.schedule_date
    if body.status is not None:
        schedule.status = body.status

    db.commit()
    db.refresh(schedule)

    new_event_id = sync_to_google_calendar(
        schedule.title,
        schedule.schedule_date,
        schedule.google_event_id,
        description=f"[{schedule.type}] via Kantor Teman Kalender · status {schedule.status}",
    )
    if new_event_id and new_event_id != schedule.google_event_id:
        schedule.google_event_id = new_event_id
        db.commit()
        db.refresh(schedule)

    log_audit(db, current_user.name, "UPDATE", "content_schedules", schedule_id, {"title": schedule.title, "type": schedule.type})
    return schedule



@router.delete("/api/content-schedule/{schedule_id}", status_code=204)
def delete_content_schedule(schedule_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    schedule = db.query(ContentSchedule).filter(ContentSchedule.id == schedule_id).first()
    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule tidak ditemukan")

    if schedule.google_event_id:
        service = _get_google_calendar_service()
        if service:
            try:
                service.events().delete(calendarId=_get_setting("google_calendar_id", GOOGLE_CALENDAR_ID), eventId=schedule.google_event_id).execute()
            except Exception:
                pass

    log_audit(db, current_user.name, "DELETE", "content_schedules", schedule_id, {"title": schedule.title})
    db.delete(schedule)
    db.commit()


# ---------------------------------------------------------------------------
# Bulk Outreach Scheduler (Blast Campaign)
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Provider Config & Outreach Costs API
# ---------------------------------------------------------------------------

class ProviderConfigOut(BaseModel):
    id: str
    provider_name: str
    remaining_quota: float
    price_per_unit_idr: float
    price_input_token_usd: float
    price_output_token_usd: float
    model_config = {"from_attributes": True}


def _ai_proxy_out(proxy: AIProxy) -> dict:
    base_url = _router_base_url(proxy.base_url)
    legacy_name = (proxy.name or "").strip()
    is_legacy_name = legacy_name.lower() in {"aimurah", "openai", "custom"} or "aimurah" in legacy_name.lower()
    display_name = "9router" if is_legacy_name else (legacy_name or "9router")
    api_key = proxy.api_key or ""
    return {
        "id": proxy.id,
        "name": display_name,
        "base_url": base_url,
        "api_key": "***" if api_key else "",
        "model": _router_model(proxy.model),
        "provider": "9router",
        "feature": proxy.feature,
        "is_active": bool(proxy.is_active),
        "created_at": proxy.created_at,
    }


@router.get("/api/ai-proxies", response_model=List[AIProxyOut])
def list_ai_proxies(current_user: User = Depends(require_admin), db: Session = Depends(get_db)):
    return [_ai_proxy_out(proxy) for proxy in db.query(AIProxy).order_by(AIProxy.created_at.asc()).all()]


@router.post("/api/ai-proxies", response_model=AIProxyOut, status_code=201)
def create_ai_proxy(body: AIProxyIn, current_user: User = Depends(require_admin), db: Session = Depends(get_db)):
    if not _is_9router_url(body.base_url):
        raise HTTPException(status_code=400, detail="Base URL harus endpoint 9router VPS.")
    proxy = AIProxy(
        name=body.name,
        base_url=_router_base_url(body.base_url),
        api_key=_router_api_key(body.api_key),
        model=_router_model(body.model),
        provider=_canonical_provider(body.provider),
        feature=body.feature,
    )
    db.add(proxy)
    db.commit()
    db.refresh(proxy)
    return proxy


@router.put("/api/ai-proxies/{proxy_id}", response_model=AIProxyOut)
def update_ai_proxy(proxy_id: str, body: AIProxyIn, current_user: User = Depends(require_admin), db: Session = Depends(get_db)):
    proxy = db.query(AIProxy).filter_by(id=proxy_id).first()
    if not proxy:
        raise HTTPException(status_code=404, detail="Proxy tidak ditemukan")
    if not _is_9router_url(body.base_url):
        raise HTTPException(status_code=400, detail="Base URL harus endpoint 9router VPS.")
    proxy.name = body.name
    proxy.base_url = _router_base_url(body.base_url)
    # Preserve existing api_key if incoming is blank or masked
    if body.api_key and body.api_key != "***" and body.api_key.strip():
        proxy.api_key = _router_api_key(body.api_key)
    proxy.model = _router_model(body.model)
    proxy.provider = _canonical_provider(body.provider)
    proxy.feature = body.feature
    db.commit()
    db.refresh(proxy)
    return proxy


@router.post("/api/ai-proxies/{proxy_id}/activate", response_model=AIProxyOut)
def activate_ai_proxy(proxy_id: str, current_user: User = Depends(require_admin), db: Session = Depends(get_db)):
    proxy = db.query(AIProxy).filter_by(id=proxy_id).first()
    if not proxy:
        raise HTTPException(status_code=404, detail="Proxy tidak ditemukan")
    db.query(AIProxy).filter(AIProxy.feature == proxy.feature).update({"is_active": False})
    proxy.is_active = True
    db.commit()
    db.refresh(proxy)
    return proxy


@router.delete("/api/ai-proxies/{proxy_id}", status_code=204)
def delete_ai_proxy(proxy_id: str, current_user: User = Depends(require_admin), db: Session = Depends(get_db)):
    proxy = db.query(AIProxy).filter_by(id=proxy_id).first()
    if not proxy:
        raise HTTPException(status_code=404, detail="Proxy tidak ditemukan")
    db.delete(proxy)
    db.commit()


# --- Content Provider CRUD ---


@router.get("/api/content/providers", response_model=List[ContentProviderOut])
def list_content_providers(
    tool_type: Optional[str] = Query(None),
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    if tool_type in {"image", "caption"}:
        return []
    q = db.query(ContentProvider)
    if tool_type:
        q = q.filter(ContentProvider.tool_type == tool_type)
    providers = q.order_by(ContentProvider.created_at.desc()).all()
    result = []
    for p in providers:
        out = ContentProviderOut.model_validate(p)
        if out.api_key:
            out.api_key = out.api_key[:6] + "***"
        if p.extra_params:
            try:
                out.extra_params = json.loads(p.extra_params)
            except Exception:
                pass
        result.append(out)
    return result



@router.post("/api/content/providers", response_model=ContentProviderOut, status_code=201)
def create_content_provider(
    body: ContentProviderIn,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    if body.tool_type in {"image", "caption"}:
        raise HTTPException(status_code=410, detail="Fitur gambar dan caption sosmed sudah dihapus. Gunakan Artikel SEO.")
    p = ContentProvider(
        id=str(uuid.uuid4()), name=body.name, tool_type=body.tool_type,
        base_url=body.base_url.rstrip("/"), api_key=body.api_key, model=body.model,
        extra_params=json.dumps(body.extra_params) if body.extra_params else None,
        is_active=body.is_active,
    )
    db.add(p); db.commit(); db.refresh(p)
    out = ContentProviderOut.model_validate(p)
    if out.api_key:
        out.api_key = out.api_key[:6] + "***"
    return out



@router.put("/api/content/providers/{provider_id}", response_model=ContentProviderOut)
def update_content_provider(
    provider_id: str, body: ContentProviderIn,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    p = db.query(ContentProvider).filter(ContentProvider.id == provider_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Provider tidak ditemukan")
    if body.tool_type in {"image", "caption"}:
        raise HTTPException(status_code=410, detail="Fitur gambar dan caption sosmed sudah dihapus. Gunakan Artikel SEO.")
    p.name = body.name; p.tool_type = body.tool_type
    p.base_url = body.base_url.rstrip("/"); p.model = body.model; p.is_active = body.is_active
    p.extra_params = json.dumps(body.extra_params) if body.extra_params else None
    if body.api_key and not body.api_key.endswith("***"):
        p.api_key = body.api_key
    db.commit(); db.refresh(p)
    out = ContentProviderOut.model_validate(p)
    if out.api_key:
        out.api_key = out.api_key[:6] + "***"
    return out



@router.delete("/api/content/providers/{provider_id}", status_code=204)
def delete_content_provider(
    provider_id: str, current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    p = db.query(ContentProvider).filter(ContentProvider.id == provider_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Provider tidak ditemukan")
    db.delete(p); db.commit()


# --- Content Session CRUD ---


@router.get("/api/content/sessions", response_model=List[ContentSessionOut])
def list_content_sessions(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return (db.query(ContentSession)
            .filter(ContentSession.user_id == current_user.id)
            .order_by(ContentSession.created_at.desc()).all())



@router.post("/api/content/sessions", response_model=ContentSessionOut, status_code=201)
def create_content_session(
    body: ContentSessionIn, current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    s = ContentSession(id=str(uuid.uuid4()), user_id=current_user.id,
                       name=body.name, description=body.description)
    db.add(s); db.commit(); db.refresh(s)
    return s



@router.delete("/api/content/sessions/{session_id}", status_code=204)
def delete_content_session(
    session_id: str, current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    s = db.query(ContentSession).filter(
        ContentSession.id == session_id, ContentSession.user_id == current_user.id).first()
    if not s:
        raise HTTPException(status_code=404, detail="Session tidak ditemukan")
    db.query(ContentGeneration).filter(ContentGeneration.session_id == session_id).delete()
    db.delete(s); db.commit()



@router.put("/api/content/sessions/{session_id}", response_model=ContentSessionOut)
def update_content_session(
    session_id: str, body: ContentSessionUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    s = db.query(ContentSession).filter(
        ContentSession.id == session_id, ContentSession.user_id == current_user.id).first()
    if not s:
        raise HTTPException(status_code=404, detail="Session tidak ditemukan")
    s.name = body.name
    if body.description is not None:
        s.description = body.description
    db.commit(); db.refresh(s)
    return s


# --- History ---


@router.get("/api/content/generations")
def list_content_generations(
    session_id: Optional[str] = Query(None),
    tool_type: Optional[str] = Query(None),
    limit: int = Query(20),
    q: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    query = db.query(ContentGeneration).filter(ContentGeneration.user_id == current_user.id)
    if session_id:
        query = query.filter(ContentGeneration.session_id == session_id)
    if tool_type:
        query = query.filter(ContentGeneration.tool_type == tool_type)
    if q:
        search = f"%{q}%"
        query = query.filter(
            ContentGeneration.input_data.ilike(search) | ContentGeneration.output_data.ilike(search)
        )
    gens = query.order_by(ContentGeneration.created_at.desc()).limit(limit).all()
    result = []
    for g in gens:
        item = {
            "id": g.id, "session_id": g.session_id, "tool_type": g.tool_type,
            "model_used": g.model_used, "provider_name": g.provider_name,
            "status": g.status, "error_msg": g.error_msg, "created_at": g.created_at,
        }
        try:
            item["input_data"] = json.loads(g.input_data)
        except Exception:
            item["input_data"] = {}
        try:
            item["output_data"] = json.loads(g.output_data) if g.output_data else None
        except Exception:
            item["output_data"] = g.output_data
        result.append(item)
    return result



@router.delete("/api/content/generations/{generation_id}", status_code=204)
def delete_content_generation(
    generation_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    gen = db.query(ContentGeneration).filter(
        ContentGeneration.id == generation_id,
        ContentGeneration.user_id == current_user.id,
    ).first()
    if not gen:
        raise HTTPException(status_code=404, detail="Generation not found")
    db.delete(gen)
    db.commit()
    return


# --- Generate: Image ---


@router.post("/api/content/generate/image")
def generate_image(
    body: ImageGenRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    raise HTTPException(status_code=410, detail="Fitur generate gambar sudah dihapus. Gunakan Generator Artikel SEO.")
    provider = db.query(ContentProvider).filter(
        ContentProvider.id == body.provider_id,
        ContentProvider.tool_type == "image",
        ContentProvider.is_active == True,
    ).first()
    if not provider:
        raise HTTPException(status_code=404, detail="Image provider tidak ditemukan atau tidak aktif")

    gen = ContentGeneration(
        id=str(uuid.uuid4()), user_id=current_user.id, session_id=body.session_id,
        tool_type="image",
        input_data=json.dumps({"prompt": body.prompt, "negative_prompt": body.negative_prompt,
                               "width": body.width, "height": body.height, "provider": provider.name}),
        model_used=provider.model, provider_name=provider.name, status="pending",
    )
    db.add(gen); db.commit()

    try:
        extra = json.loads(provider.extra_params) if provider.extra_params else {}
        payload = {"model": provider.model, "prompt": body.prompt, "n": 1,
                   "size": f"{body.width}x{body.height}", **extra}
        if body.negative_prompt:
            payload["negative_prompt"] = body.negative_prompt

        import httpx as _httpx
        with _httpx.Client(timeout=120) as client:
            resp = client.post(
                f"{provider.base_url}/images/generations",
                headers={"Authorization": f"Bearer {provider.api_key}", "Content-Type": "application/json"},
                json=payload,
            )
        if resp.status_code != 200:
            raise Exception(f"Image API error {resp.status_code}: {resp.text[:300]}")

        items = resp.json().get("data", [])
        images = []
        for item in items:
            if "url" in item:
                images.append({"type": "url", "value": item["url"]})
            elif "b64_json" in item:
                images.append({"type": "b64", "value": item["b64_json"]})

        gen.output_data = json.dumps({"images": images})
        gen.status = "done"; db.commit()
        return {"id": gen.id, "status": "done", "images": images, "created_at": gen.created_at}

    except HTTPException:
        raise
    except Exception as e:
        gen.status = "error"; gen.error_msg = str(e); db.commit()
        raise HTTPException(status_code=502, detail=f"Gagal generate image: {str(e)}")


# --- Generate: Caption ---


@router.post("/api/content/generate/caption")
def generate_caption(
    body: CaptionGenRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    raise HTTPException(status_code=410, detail="Fitur caption sosmed sudah dihapus. Gunakan Generator Artikel SEO.")
    """Generate caption using canonical multi-provider AI routing."""
    from app.services.ai_service import generate_caption as svc_generate_caption
    try:
        result = svc_generate_caption(
            db=db,
            user_id=current_user.id,
            topic=body.topic,
            platform=body.platform,
            tone=body.tone,
            keywords=body.keywords or [],
            session_id=body.session_id,
            context_from=body.context_from,
        )
        return {"id": result["id"], "status": "done", "created_at": result["created_at"], **result}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Gagal generate caption: {str(e)}")


# --- Generate: SEO Article ---


@router.post("/api/content/generate/seo-article")
def generate_seo_article(
    body: SeoArticleGenRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Generate SEO article using canonical multi-provider AI routing."""
    from app.services.ai_service import generate_seo_article as svc_generate_seo_article
    try:
        result = svc_generate_seo_article(
            db=db,
            user_id=current_user.id,
            keyword=body.keyword,
            title=body.title,
            word_count=body.word_count,
            tone=body.tone,
            search_intent=body.search_intent,
            keyword_difficulty=body.keyword_difficulty,
            search_volume=body.search_volume,
            lsi_keywords=body.lsi_keywords,
            faq_topics=body.faq_topics,
            serp_features=body.serp_features,
            target_audience=body.target_audience,
            target_location=body.target_location,
            brand_name=body.brand_name,
            unique_angle=body.unique_angle,
            internal_link_targets=body.internal_link_targets,
            session_id=body.session_id,
            context_from=body.context_from,
        )
        return {"id": result["id"], "status": "done", "created_at": result["created_at"], **result}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Gagal generate artikel: {str(e)}")


# --- CMS Proxy ---

class CmsPublishRequest(BaseModel):
    title: str
    slug: str
    excerpt: Optional[str] = None
    content: str
    meta_description: Optional[str] = None
    focus_keyword: Optional[str] = None
    status: str = "draft"


@router.post("/api/cms/publish-article")
def cms_publish_article(body: CmsPublishRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    cms_url_row = db.query(SystemSettings).filter_by(key="cms_url").first()
    cms_token_row = db.query(SystemSettings).filter_by(key="cms_api_token").first()
    if not cms_url_row or not cms_url_row.value:
        raise HTTPException(status_code=400, detail="CMS URL belum diset di Settings")
    if not cms_token_row or not cms_token_row.value:
        raise HTTPException(status_code=400, detail="CMS API Token belum diset di Settings")
    import httpx as _httpx
    cms_base = cms_url_row.value.rstrip("/")
    headers = {
        "Authorization": f"Bearer {cms_token_row.value}",
        "Content-Type": "application/json",
    }
    use_ip = cms_base.replace("https://","").split(":")[0].replace(".","").isdigit()
    if use_ip:
        headers["Host"] = "api.temanumkmkita.com"
    try:
        resp = _httpx.post(
            f"{cms_base}/api/articles",
            headers=headers,
            json=body.model_dump(),
            timeout=30,
            follow_redirects=True,
            verify=not use_ip,
        )
        if resp.status_code not in (200, 201):
            raise HTTPException(status_code=502, detail=f"CMS error {resp.status_code}: {resp.text[:300]}")
        return resp.json()
    except _httpx.RequestError as e:
        raise HTTPException(status_code=502, detail=f"Gagal koneksi ke CMS: {str(e)}")


# ---------------------------------------------------------------------------
# Document Archive: Folders & Documents
# ---------------------------------------------------------------------------

class ArchiveFolderIn(BaseModel):
    name: str
    parent_id: Optional[str] = None
    color: Optional[str] = "#6B7280"


class ArchiveFolderUpdate(BaseModel):
    name: Optional[str] = None
    parent_id: Optional[str] = None
    color: Optional[str] = None


class ArchiveDocIn(BaseModel):
    title: str
    body: Optional[str] = None
    url: Optional[str] = None
    tags: Optional[List[str]] = []
    folder_id: Optional[str] = None


class ArchiveDocUpdate(BaseModel):
    title: Optional[str] = None
    body: Optional[str] = None
    url: Optional[str] = None
    tags: Optional[List[str]] = None
    folder_id: Optional[str] = None


def _archive_parent_creates_cycle(db: Session, folder_id: str, parent_id: Optional[str]) -> bool:
    seen = set()
    current_id = parent_id
    while current_id:
        if current_id == folder_id or current_id in seen:
            return True
        seen.add(current_id)
        current = db.query(DocumentFolder).filter(DocumentFolder.id == current_id).first()
        current_id = current.parent_id if current else None
    return False
