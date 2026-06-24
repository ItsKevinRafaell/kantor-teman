"""Profile discovery, config loading, and agent CRUD."""
import json
import os
import subprocess
import urllib.error
import urllib.request
from pathlib import Path
from typing import Optional

import yaml

import config
from src.util import validate_profile as _validate_profile


def validate_profile(profile: str) -> str:
    return _validate_profile(profile)


def resolve_profile(profile: str) -> str:
    profile = validate_profile(profile)
    return config.PROFILE_ALIASES.get(profile, profile)


def _profile_dir(profile: str) -> Path:
    if profile == "default":
        return config.HERMES_HOME
    return config.PROFILES_DIR / profile


def _canonical_profile(profile: str) -> str:
    return config.LEGACY_PROFILE_ALIASES.get(profile, profile)


def _existing_profile_dir(profile: str) -> Path:
    direct = _profile_dir(profile)
    if direct.exists():
        return direct
    legacy_name = config.LEGACY_PROFILE_DIRS.get(profile)
    if legacy_name:
        legacy_dir = _profile_dir(legacy_name)
        if legacy_dir.exists():
            return legacy_dir
    for legacy, current in config.LEGACY_PROFILE_ALIASES.items():
        if current == profile:
            legacy_dir = _profile_dir(legacy)
            if legacy_dir.exists():
                return legacy_dir
    return direct


def _runtime_profile(profile: str) -> str:
    """Return the installed Hermes profile name (handles legacy dir names)."""
    profile = resolve_profile(profile)
    if _profile_dir(profile).exists():
        return profile
    legacy_name = config.LEGACY_PROFILE_DIRS.get(profile)
    if legacy_name and _profile_dir(legacy_name).exists():
        return legacy_name
    for legacy, current in config.LEGACY_PROFILE_ALIASES.items():
        if current == profile and _profile_dir(legacy).exists():
            return legacy
    return profile


def _iter_agent_profiles() -> list[tuple[str, Path]]:
    profiles: dict[str, Path] = {}
    for profile in config.API_SERVER_PORTS:
        profiles[profile] = _existing_profile_dir(profile)
    if config.PROFILES_DIR.exists():
        for p in config.PROFILES_DIR.iterdir():
            if not p.is_dir():
                continue
            current = _canonical_profile(p.name)
            profiles.setdefault(current, _existing_profile_dir(current))
    if config.HERMES_HOME.exists():
        profiles.setdefault(_canonical_profile("default"), _existing_profile_dir(_canonical_profile("default")))
    ordered = []
    for profile in [*config.API_SERVER_PORTS.keys(), *sorted(profiles.keys())]:
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


def _read_soul_preview(profile_dir: Path, max_chars: int = 200) -> str:
    soul = profile_dir / "SOUL.md"
    if not soul.exists():
        return ""
    try:
        return soul.read_text(encoding="utf-8")[:max_chars]
    except Exception:
        return ""


def _hermes_cmd(profile: str, *args: str) -> list[str]:
    runtime_profile = _runtime_profile(profile)
    command = [config.HERMES_BIN]
    if runtime_profile != "default":
        command += ["--profile", runtime_profile]
    return command + list(args)


def _service_name_for_profile(profile: str) -> str:
    runtime = _runtime_profile(profile)
    return f"hermes-gateway-{runtime}.service"


def restart_agent_service(profile: str) -> dict:
    profile = resolve_profile(profile)
    service = _service_name_for_profile(profile)
    result = subprocess.run(
        ["systemctl", "--user", "restart", service],
        capture_output=True, text=True, timeout=30,
    )
    return {
        "profile": profile,
        "service": service,
        "ok": result.returncode == 0,
        "error": (result.stderr or result.stdout).strip()[:300] if result.returncode != 0 else "",
    }


def _db_path(profile: str) -> Optional[str]:
    p = _existing_profile_dir(profile) / "state.db"
    return str(p) if p.exists() else None


def _get_latest_session(profile: str) -> Optional[str]:
    """Get the most recent session ID for a profile."""
    db = _db_path(profile)
    if not db:
        return None
    try:
        import sqlite3
        con = sqlite3.connect(db)
        row = con.execute("SELECT id FROM sessions ORDER BY started_at DESC LIMIT 1").fetchone()
        con.close()
        return row[0] if row else None
    except Exception:
        return None


def _latest_session_for_room(
    profile: str,
    room_key: Optional[str] = None,
    chat_id: Optional[str] = None,
    message_thread_id: Optional[str] = None,
) -> Optional[str]:
    """Get the most recent session for a room."""
    db = _db_path(profile)
    if not db:
        return None
    try:
        import sqlite3
        con = sqlite3.connect(db)
        # Try to find session with matching room metadata
        row = con.execute(
            """
            SELECT s.id FROM sessions s
            LEFT JOIN messages m ON m.session_id = s.id
            WHERE m.metadata LIKE ?
            ORDER BY s.started_at DESC LIMIT 1
            """,
            (f"%{room_key or chat_id}%",),
        ).fetchone()
        con.close()
        if row:
            return row[0]
        return _get_latest_session(profile)
    except Exception:
        return None


def _office_topic_from_room_key(room_key: Optional[str]) -> str:
    """Extract topic name from room key like 'office:general'."""
    if not room_key:
        return "general"
    if room_key.startswith("office:"):
        return room_key.split(":", 1)[1]
    return room_key


def _office_room_key_from_topic(topic: str) -> str:
    """Convert topic to office room key."""
    if topic.startswith("office:"):
        return topic
    return f"office:{topic}"


def _telegram_binding_summary(profile: str) -> dict:
    """Get telegram binding summary for a profile."""
    return {
        "profile": profile,
        "name": _profile_display_name(profile),
        "binding": None,
    }


def _normalize_chat_type(chat_type: str) -> str:
    """Normalize chat type string."""
    if chat_type in {"private", "bot"}:
        return "private"
    if chat_type in {"group", "supergroup"}:
        return "group"
    return chat_type


def _canonical_room_key(chat_id: str, thread_id: Optional[str] = None) -> str:
    """Create canonical room key from chat identifiers."""
    if thread_id:
        return f"telegram:{chat_id}:{thread_id}"
    return f"telegram:{chat_id}"


def _room_telegram_destination(room_key: str) -> tuple[Optional[str], Optional[str]]:
    """Extract chat_id and thread_id from room key."""
    if room_key.startswith("telegram:"):
        parts = room_key.split(":", 2)
        if len(parts) == 3:
            return parts[1], parts[2]
        return parts[1], None
    return None, None


def _telegram_destination(profile: str, room_key: str) -> dict:
    """Get Telegram destination info from room key."""
    chat_id, thread_id = _room_telegram_destination(room_key)
    return {
        "chat_id": chat_id,
        "message_thread_id": thread_id,
    }


def _room_key(chat_id: str, thread_id: Optional[str] = None) -> str:
    """Create room key from chat_id and optional thread_id."""
    if thread_id:
        return f"telegram:{chat_id}:{thread_id}"
    return f"telegram:{chat_id}"


def _profile_dir(profile: str) -> str:
    """Get profile directory path as string."""
    from pathlib import Path
    p = _existing_profile_dir(profile)
    return str(p)


def _api_server_url(profile: str, path: str) -> str:
    port = config.API_SERVER_PORTS.get(profile)
    if not port:
        raise ValueError(f"Async chat is not configured for {profile}")
    return f"http://127.0.0.1:{port}{path}"


# ── Router helpers ──────────────────────────────────────────────────────────────

def _router_base_url(for_external: bool = False) -> str:
    base = config.ROUTER_EXTERNAL_BASE_URL if for_external else config.ROUTER_INTERNAL_BASE_URL
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
    for key_file in config.ROUTER_KEY_FILES:
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
    from fastapi import HTTPException
    from src.util import redact

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
            "raw": redact(raw),
        })
    return models


def _load_profile_env(profile: str) -> dict:
    profile_dir = _existing_profile_dir(profile)
    env_path = profile_dir / ".env"
    if not env_path.exists():
        return {}
    result = {}
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            result[k.strip()] = v.strip()
    return result


def read_agent_ai_config(profile: str) -> dict:
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
    api_key_present = bool(
        model_section.get("api_key") or env_values.get("OPENAI_API_KEY") or _router_default_api_key()
    )
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


def write_agent_ai_config(profile: str, updates: dict) -> dict:
    from fastapi import HTTPException
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
    return read_agent_ai_config(profile)
