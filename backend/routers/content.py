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
    get_9router_config, _get_9router_combos, _get_active_combo,
    _get_proxy_url, _get_feature_defaults, get_proxy_for_feature,
    get_default_model, COMBO_DISPLAY_NAMES,
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
    """Set this model as default for given capability (chat, image, article, analysis)."""
    if capability not in ("chat", "image", "article", "analysis"):
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
# 9router combo endpoints
# ---------------------------------------------------------------------------


@router.get("/api/ai/combos")
def list_ai_combos(current_user: User = Depends(get_current_user)):
    return _get_9router_combos()



@router.get("/api/ai/active-combo")
def get_active_combo(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return {"combo": _get_active_combo(db), "proxy_url": _get_proxy_url(db)}



@router.post("/api/ai/active-combo")
def set_active_combo(body: dict, current_user: User = Depends(require_admin), db: Session = Depends(get_db)):
    combo = body.get("combo", "").strip()
    if not combo:
        raise HTTPException(status_code=400, detail="Field 'combo' wajib diisi")
    valid = [c["name"] for c in _get_9router_combos()]
    if combo not in valid:
        raise HTTPException(status_code=400, detail=f"Combo '{combo}' tidak ditemukan di 9router")
    row = db.query(SystemSettings).filter_by(key="ai_active_combo").first()
    if row:
        row.value = combo
    else:
        db.add(SystemSettings(key="ai_active_combo", value=combo))
    db.commit()
    return {"ok": True, "combo": combo}



@router.post("/api/ai/proxy-url")
def set_proxy_url(body: dict, current_user: User = Depends(require_admin), db: Session = Depends(get_db)):
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



@router.post("/api/ai/feature-defaults")
def set_feature_defaults(body: dict, current_user: User = Depends(require_admin), db: Session = Depends(get_db)):
    valid_features = {"chat", "article", "image", "analysis", "caption"}
    valid_combos = {c["name"] for c in _get_9router_combos()}
    cleaned: dict[str, str] = {}
    for feature, combo in (body or {}).items():
        if feature not in valid_features:
            continue
        combo_str = (combo or "").strip()
        if combo_str and combo_str not in valid_combos:
            raise HTTPException(status_code=400, detail=f"Combo '{combo_str}' tidak valid untuk fitur '{feature}'")
        cleaned[feature] = combo_str
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
    proxy_url = _get_proxy_url(db)
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            r = await client.get(f"{proxy_url}/models", headers={"Authorization": f"Bearer {NINE_ROUTER_API_KEY}"})
        if r.status_code < 500:
            return {"status": "connected", "proxy_url": proxy_url}
    except Exception as e:
        print(f"[9router health] {e}", flush=True)
    return {"status": "offline", "proxy_url": proxy_url}


# ---------------------------------------------------------------------------
# Search / Scrape
# ---------------------------------------------------------------------------


@router.get("/api/content-types")
def get_content_types(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    row = db.query(SystemSettings).filter_by(key="content_types").first()
    if row and row.value:
        return json.loads(row.value)
    return [
        {"value": "IG_CAROUSEL", "label": "IG Carousel", "color": "#f97316"},
        {"value": "IG_REELS", "label": "IG Reels", "color": "#ec4899"},
        {"value": "SEO_ARTICLE", "label": "Artikel SEO", "color": "#10b981"},
        {"value": "TIKTOK", "label": "TikTok", "color": "#06b6d4"},
        {"value": "YOUTUBE", "label": "YouTube", "color": "#ef4444"},
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
    google_event_id = sync_to_google_calendar(body.title, body.schedule_date)

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
    log_audit(db, current_user.name, "CREATE", "content_schedules", schedule.id, {"title": body.title})
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

    sync_to_google_calendar(schedule.title, schedule.schedule_date, schedule.google_event_id)

    log_audit(db, current_user.name, "UPDATE", "content_schedules", schedule_id, {"title": schedule.title})
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



@router.get("/api/ai-proxies", response_model=List[AIProxyOut])
def list_ai_proxies(current_user: User = Depends(require_admin), db: Session = Depends(get_db)):
    return db.query(AIProxy).order_by(AIProxy.created_at.asc()).all()


@router.post("/api/ai-proxies", response_model=AIProxyOut, status_code=201)
def create_ai_proxy(body: AIProxyIn, current_user: User = Depends(require_admin), db: Session = Depends(get_db)):
    proxy = AIProxy(name=body.name, base_url=body.base_url.rstrip("/"), api_key=body.api_key, model=body.model, feature=body.feature)
    db.add(proxy)
    db.commit()
    db.refresh(proxy)
    return proxy


@router.put("/api/ai-proxies/{proxy_id}", response_model=AIProxyOut)
def update_ai_proxy(proxy_id: str, body: AIProxyIn, current_user: User = Depends(require_admin), db: Session = Depends(get_db)):
    proxy = db.query(AIProxy).filter_by(id=proxy_id).first()
    if not proxy:
        raise HTTPException(status_code=404, detail="Proxy tidak ditemukan")
    proxy.name = body.name
    proxy.base_url = body.base_url.rstrip("/")
    proxy.api_key = body.api_key
    proxy.model = body.model
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
    ai = _get_system_ai_config(db)
    if not ai["api_key"]:
        raise HTTPException(status_code=400, detail="API Key AI belum dikonfigurasi di Settings")

    platform_guide = {
        "instagram": "Instagram: max 2200 karakter, 3-5 hashtag relevan, emoji secukupnya, CTA di akhir.",
        "tiktok": "TikTok: singkat dan catchy, hook kuat di kalimat pertama, 5-10 hashtag trending.",
    }.get(body.platform, "")

    system_msg = (
        f"Kamu adalah content writer media sosial profesional Bahasa Indonesia. "
        f"Buat caption {body.platform.upper()} yang engaging, tone: '{body.tone}'. {platform_guide} "
        f"WAJIB return valid JSON: {{\"caption\": \"...\", \"hashtags\": [\"#tag\"], \"notes\": \"tip singkat\"}}"
    )
    user_msg = f"Topik: {body.topic}"
    if body.keywords:
        user_msg += f"\nKeyword wajib disebut: {', '.join(body.keywords)}"
    ctx = _get_session_ctx(body.session_id, db)
    if ctx:
        user_msg += f"\n\n{ctx}"
    mctx = _get_manual_ctx(body.context_from or [], db)
    if mctx:
        user_msg += f"\n\n{mctx}"

    gen = ContentGeneration(
        id=str(uuid.uuid4()), user_id=current_user.id, session_id=body.session_id,
        tool_type="caption", input_data=json.dumps(body.model_dump()),
        model_used=ai["model"], provider_name="System AI", status="pending",
    )
    db.add(gen); db.commit()

    try:
        text = _call_text_gen(
            messages=[{"role": "system", "content": system_msg}, {"role": "user", "content": user_msg}],
            api_key=ai["api_key"], base_url=ai["base_url"], model=ai["model"], max_tokens=800,
        )
        import re as _re
        m = _re.search(r'\{[\s\S]*\}', text)
        try:
            result = json.loads(m.group()) if m else {"caption": text, "hashtags": [], "notes": ""}
        except Exception:
            result = {"caption": text, "hashtags": [], "notes": ""}

        gen.output_data = json.dumps(result); gen.status = "done"; db.commit()
        return {"id": gen.id, "status": "done", "created_at": gen.created_at, **result}

    except HTTPException:
        raise
    except Exception as e:
        gen.status = "error"; gen.error_msg = str(e); db.commit()
        raise HTTPException(status_code=502, detail=f"Gagal generate caption: {str(e)}")


# --- Generate: SEO Article ---


@router.post("/api/content/generate/seo-article")
def generate_seo_article(
    body: SeoArticleGenRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    ai = _get_system_ai_config(db)
    if not ai["api_key"]:
        raise HTTPException(status_code=400, detail="API Key AI belum dikonfigurasi di Settings")

    target_title = body.title or f"Panduan Lengkap: {body.keyword}"

    intent_guide = {
        "informational": "Search intent INFORMATIONAL: edukasi pembaca, jawab 'apa', 'bagaimana', 'mengapa'. Buat artikel komprehensif dengan definisi jelas, contoh praktis, dan takeaway.",
        "commercial": "Search intent COMMERCIAL INVESTIGATION: pembaca sedang membandingkan pilihan. Sertakan perbandingan, pro-kontra, kriteria pemilihan, dan rekomendasi konkret.",
        "transactional": "Search intent TRANSACTIONAL: pembaca siap bertindak. CTA kuat, benefit produk/jasa menonjol, hilangkan keraguan, sertakan social proof.",
        "navigational": "Search intent NAVIGATIONAL: bantu user menemukan brand/resource spesifik. Fokus pada brand credibility dan unique value proposition.",
    }.get(body.search_intent or "informational", "")

    kd_guide = ""
    if body.keyword_difficulty is not None:
        if body.keyword_difficulty >= 70:
            kd_guide = f"Keyword difficulty {body.keyword_difficulty}/100 (HARD): artikel harus sangat komprehensif, lebih mendalam dari kompetitor, sertakan data/statistik, expert insight."
        elif body.keyword_difficulty >= 40:
            kd_guide = f"Keyword difficulty {body.keyword_difficulty}/100 (MEDIUM): artikel solid dan lengkap, pastikan semua subtopik penting tercakup."
        else:
            kd_guide = f"Keyword difficulty {body.keyword_difficulty}/100 (EASY): fokus pada kualitas dan kegunaan, pastikan E-E-A-T terpenuhi."

    serp_guide = ""
    if body.serp_features:
        hints = []
        if "featured_snippet" in body.serp_features:
            hints.append("tambah definition box atau tabel ringkasan di awal untuk optimasi Featured Snippet")
        if "paa" in body.serp_features:
            hints.append("sertakan FAQ section (H2 'Pertanyaan Umum') untuk optimasi People Also Ask")
        if "local_pack" in body.serp_features:
            hints.append("sertakan informasi lokal yang relevan untuk optimasi Local Pack")
        if "image_pack" in body.serp_features:
            hints.append("tambah deskripsi/caption gambar yang informatif untuk optimasi Image Pack")
        if hints:
            serp_guide = "SERP features target: " + "; ".join(hints) + "."

    system_msg = (
        f"Kamu adalah SEO content writer profesional Bahasa Indonesia, expert dalam E-E-A-T dan on-page SEO. "
        f"Buat artikel blog SEO berkualitas tinggi, tone: '{body.tone}', target sekitar {body.word_count} kata. "
        f"{intent_guide} {kd_guide} {serp_guide} "
        f"Gunakan heading H2/H3 dengan format markdown (## dan ###). "
        f"Optimalkan keyword secara natural (density 1-2%, jangan keyword stuffing). "
        f"Struktur artikel: hook intro, isi dengan heading logis, kesimpulan + CTA. "
        f"WAJIB output dengan format TEPAT berikut (jangan tambah teks lain di luar format):\n"
        f"TITLE: <judul artikel>\n"
        f"META: <meta description max 160 karakter, include keyword>\n"
        f"FOCUS_KEYWORD: <keyword utama>\n"
        f"SECONDARY_KEYWORDS: <keyword1>, <keyword2>, <keyword3>\n"
        f"---ARTICLE---\n"
        f"<artikel lengkap dalam markdown>\n"
        f"---END---"
    )

    user_parts = [f"Keyword utama: {body.keyword}", f"Judul: {target_title}"]
    if body.search_intent:
        user_parts.append(f"Search intent: {body.search_intent}")
    if body.search_volume:
        user_parts.append(f"Search volume: {body.search_volume:,}/bulan")
    if body.keyword_difficulty is not None:
        user_parts.append(f"Keyword difficulty: {body.keyword_difficulty}/100")
    if body.lsi_keywords:
        user_parts.append(f"LSI/related keywords (sisipkan secara natural): {', '.join(body.lsi_keywords)}")
    if body.target_audience:
        user_parts.append(f"Target pembaca: {body.target_audience}")
    if body.target_location:
        user_parts.append(f"Target lokasi: {body.target_location}")
    if body.brand_name:
        user_parts.append(f"Brand/bisnis: {body.brand_name}")
    if body.unique_angle:
        user_parts.append(f"Angle unik artikel ini: {body.unique_angle}")
    if body.faq_topics:
        user_parts.append(f"FAQ topics yang wajib dijawab: {'; '.join(body.faq_topics)}")
    if body.internal_link_targets:
        user_parts.append(f"Halaman internal untuk disarankan sebagai internal link: {body.internal_link_targets}")
    user_msg = "\n".join(user_parts)
    ctx = _get_session_ctx(body.session_id, db)
    if ctx:
        user_msg += f"\n\n{ctx}"
    mctx = _get_manual_ctx(body.context_from or [], db)
    if mctx:
        user_msg += f"\n\n{mctx}"

    gen = ContentGeneration(
        id=str(uuid.uuid4()), user_id=current_user.id, session_id=body.session_id,
        tool_type="seo_article", input_data=json.dumps(body.model_dump()),
        model_used=ai["model"], provider_name="System AI", status="pending",
    )
    db.add(gen); db.commit()

    try:
        text = _call_text_gen(
            messages=[{"role": "system", "content": system_msg}, {"role": "user", "content": user_msg}],
            api_key=ai["api_key"], base_url=ai["base_url"], model=ai["model"], max_tokens=4000,
        )
        import re as _re
        def _parse_delimited(t: str) -> dict:
            title = (_re.search(r'^TITLE:\s*(.+)', t, _re.MULTILINE) or _re.search(r'', t))
            meta = _re.search(r'^META:\s*(.+)', t, _re.MULTILINE)
            fk = _re.search(r'^FOCUS_KEYWORD:\s*(.+)', t, _re.MULTILINE)
            sk = _re.search(r'^SECONDARY_KEYWORDS:\s*(.+)', t, _re.MULTILINE)
            body_m = _re.search(r'---ARTICLE---([\s\S]*?)---END---', t)
            return {
                "title": title.group(1).strip() if title and title.lastindex else target_title,
                "meta_description": meta.group(1).strip() if meta else "",
                "focus_keyword": fk.group(1).strip() if fk else body.keyword,
                "secondary_keywords": [k.strip() for k in sk.group(1).split(",") if k.strip()] if sk else [],
                "body": body_m.group(1).strip() if body_m else t,
            }
        result = _parse_delimited(text)

        gen.output_data = json.dumps(result); gen.status = "done"; db.commit()
        return {"id": gen.id, "status": "done", "created_at": gen.created_at, **result}

    except HTTPException:
        raise
    except Exception as e:
        gen.status = "error"; gen.error_msg = str(e); db.commit()
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



