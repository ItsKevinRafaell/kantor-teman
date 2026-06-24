"""Profile management endpoints."""
import uuid

from fastapi import APIRouter, Depends, HTTPException

import config
from src.auth.middleware import verify_auth
from src.models.profile import (
    AgentCreate,
    ConfigUpdate,
    EnvUpdate,
    HermesAgentConfigUpdate,
    HermesApplyAllRequest,
    SoulUpdate,
)
from src.services.profile_service import (
    _existing_profile_dir,
    _iter_agent_profiles,
    _profile_display_name,
    _read_config,
    _read_env_keys,
    _read_soul_preview,
    _write_config,
    _write_env,
    read_agent_ai_config,
    write_agent_ai_config,
    restart_agent_service,
    _fetch_router_models,
    _router_v1_url,
    _router_default_api_key,
    resolve_profile,
)
from src.services.queue_service import audit_ai_request, queue_wait_seconds
from src.util import validate_profile

router = APIRouter()


@router.get("/api/office/agents")
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


@router.post("/api/office/agents")
def create_agent(payload: AgentCreate, _: str = Depends(verify_auth)):
    import subprocess
    profile = payload.name
    validate_profile(profile)
    profile_dir = config.PROFILES_DIR / profile
    if profile_dir.exists():
        raise HTTPException(status_code=409, detail=f"Profile '{profile}' already exists")
    cmd = [config.HERMES_BIN, "profile", "create", profile]
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


@router.delete("/api/office/agents/{profile}")
def delete_agent(profile: str, _: str = Depends(verify_auth)):
    import subprocess
    validate_profile(profile)
    profile_dir = config.PROFILES_DIR / profile
    if not profile_dir.exists():
        raise HTTPException(status_code=404, detail=f"Profile '{profile}' not found")
    for flag in ["--yes", "-y"]:
        result = subprocess.run(
            [config.HERMES_BIN, "profile", "delete", profile, flag],
            capture_output=True, text=True, timeout=60,
        )
        if result.returncode == 0:
            return {"ok": True}
    raise HTTPException(status_code=500, detail=f"profile delete failed: {result.stderr.strip()[:300]}")


@router.put("/api/office/agents/{profile}/soul")
def update_soul(profile: str, payload: SoulUpdate, _: str = Depends(verify_auth)):
    profile = resolve_profile(profile)
    profile_dir = _existing_profile_dir(profile)
    if not profile_dir.exists():
        raise HTTPException(status_code=404, detail="Not found")
    (profile_dir / "SOUL.md").write_text(payload.soul, encoding="utf-8")
    return {"ok": True}


@router.put("/api/office/agents/{profile}/env")
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


@router.put("/api/office/agents/{profile}/config")
def update_agent_config(profile: str, payload: ConfigUpdate, _: str = Depends(verify_auth)):
    validate_profile(profile)
    profile_dir = _existing_profile_dir(resolve_profile(profile))
    if not profile_dir.exists():
        raise HTTPException(status_code=404, detail="Not found")
    _write_config(profile_dir, payload.model_dump(exclude_none=True))
    return {"ok": True}


@router.get("/api/office/hermes/models")
def hermes_models(_: str = Depends(verify_auth)):
    models = _fetch_router_models()
    return {
        "base_url": _router_v1_url(),
        "external_base_url": _router_v1_url(True),
        "models": models,
        "combos": [model for model in models if model.get("type") == "combo"],
        "count": len(models),
    }


@router.get("/api/office/hermes/agents/config")
def hermes_agent_configs(_: str = Depends(verify_auth)):
    return {
        "router": {
            "base_url": _router_v1_url(),
            "external_base_url": _router_v1_url(True),
            "api_key_configured": bool(_router_default_api_key()),
        },
        "multi_read_seconds": queue_wait_seconds(),
        "agents": [read_agent_ai_config(profile) for profile, _ in _iter_agent_profiles()],
    }


@router.patch("/api/office/hermes/agents/{profile}/config")
def patch_hermes_agent_config(profile: str, payload: HermesAgentConfigUpdate, _: str = Depends(verify_auth)):
    profile = resolve_profile(profile)
    updates = payload.model_dump(exclude_none=True)
    agent_cfg = write_agent_ai_config(profile, updates)
    restart = restart_agent_service(profile) if payload.restart else None
    audit_ai_request(
        f"config-{uuid.uuid4().hex}",
        app_name="office",
        channel="web-admin",
        profile=profile,
        model=agent_cfg.get("model", ""),
        base_url=agent_cfg.get("base_url", ""),
        request_payload={"action": "update_agent_config", "updates": updates},
        response_payload={"config": agent_cfg, "restart": restart},
        status="completed" if not restart or restart.get("ok") else "failed",
        error=restart.get("error") if restart and not restart.get("ok") else None,
        completed=True,
    )
    return {"ok": True, "agent": agent_cfg, "restart": restart}


@router.post("/api/office/hermes/agents/apply-all")
def apply_all_hermes_agent_config(payload: HermesApplyAllRequest, _: str = Depends(verify_auth)):
    updates = payload.model_dump(exclude_none=True)
    results = []
    for profile, _ in _iter_agent_profiles():
        agent_cfg = write_agent_ai_config(profile, updates)
        restart = restart_agent_service(profile) if payload.restart else None
        results.append({"profile": profile, "agent": agent_cfg, "restart": restart})
    audit_ai_request(
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
