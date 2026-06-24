"""Input validation helpers."""
import re
from typing import Optional

PROFILE_RE = re.compile(r"^[a-z][a-z0-9_-]{1,30}$")

ALLOWED_FILE_EXTS = {".md", ".yaml", ".yml", ".json", ".txt", ".env", ".log", ".py", ".sh"}


def validate_profile(profile: str) -> str:
    if not PROFILE_RE.match(profile):
        raise ValueError(f"Invalid profile name: {profile!r}")
    return profile


def sanitize_filename(name: str) -> str:
    return re.sub(r"[^a-zA-Z0-9._-]", "_", name)[:80]


def is_safe_doc_id(doc_id: str) -> bool:
    return bool(re.match(r"^[\w.\-]{1,80}$", doc_id))
