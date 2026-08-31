"""
Settings helpers — read/write system settings from DB.
"""
from typing import Optional

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


def _get_setting(key: str, default: str = "", db: Optional[Session] = None) -> str:
    # db opsional: kalau dipanggil dari dalam transaksi/savepoint (mis. pipeline
    # generate dokumen), WAJIB pakai session pemanggil. SessionLocal() di tengah
    # savepoint (test StaticPool) me-rollback koneksi bersama dan membunuh
    # SAVEPOINT; di prod bikin read di luar transaksi saat ini.
    if db is not None:
        row = db.query(SystemSettings).filter_by(key=key).first()
        return row.value if row and row.value else default
    from models import SessionLocal
    local_db = SessionLocal()
    try:
        row = local_db.query(SystemSettings).filter_by(key=key).first()
        return row.value if row and row.value else default
    finally:
        local_db.close()
