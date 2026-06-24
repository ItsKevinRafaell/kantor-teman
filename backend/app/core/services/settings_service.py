"""
Settings helpers — read/write system settings from DB.
"""
from sqlalchemy.orm import Session

from models import SystemSettings

SENSITIVE_SETTING_KEYS = {
    "fonnte_token", "ai_api_key", "google_api_key", "google_service_account_json",
    "cms_api_token", "external_lead_api_key", "smtp_password",
}


def _mask_secret(value: str) -> str:
    if not value:
        return ""
    if len(value) <= 4:
        return "****"
    return "****" + value[-4:]


def _get_setting(key: str, default: str = "") -> str:
    from models import SessionLocal
    db = SessionLocal()
    try:
        row = db.query(SystemSettings).filter_by(key=key).first()
        return row.value if row and row.value else default
    finally:
        db.close()
