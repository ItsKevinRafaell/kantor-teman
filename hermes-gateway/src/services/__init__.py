"""Services module."""
from .profile_service import (
    resolve_profile,
    _existing_profile_dir,
    _iter_agent_profiles,
    _profile_display_name,
    _read_config,
    _write_config,
    _read_env_keys,
    _write_env,
    _read_soul_preview,
    _hermes_cmd,
    restart_agent_service,
    _db_path,
    read_agent_ai_config,
    write_agent_ai_config,
    _fetch_router_models,
)
