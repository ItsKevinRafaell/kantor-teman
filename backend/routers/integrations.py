import os
from urllib.parse import urlparse

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from models import SystemSettings, get_db
from app.core.whatsapp_provider import get_whatsapp_config

router = APIRouter()


def _configured_setting(db: Session, key: str) -> bool:
    row = db.query(SystemSettings).filter_by(key=key).first()
    return bool(row and row.value)


def _host(value: str) -> str:
    parsed = urlparse((value or "").strip())
    return parsed.netloc or parsed.path.split("/")[0]


@router.get("/api/integrations/ecosystem/status")
def ecosystem_status(db: Session = Depends(get_db)):
    whatsapp = get_whatsapp_config(db)
    lead_key_configured = _configured_setting(db, "external_lead_api_key")

    status = "ok" if lead_key_configured and _configured_setting(db, "fonnte_token") else "warning"

    return {
        "service": "kantorteman",
        "source_of_truth": True,
        "status": status,
        "lead_intake": {
            "endpoint": "/api/leads/external",
            "external_lead_api_key_configured": lead_key_configured,
            "accepted_sources": ["website_temanumkmkita", "autolead", "leadbot"],
        },
        "whatsapp": {
            "provider": whatsapp.provider,
            "fonnte_configured": _configured_setting(db, "fonnte_token"),
        },
        "office": {
            "hermes_gateway_configured": bool(os.getenv("HERMES_GATEWAY_URL", "")),
            "hermes_gateway_host": _host(os.getenv("HERMES_GATEWAY_URL", "")),
        },
    }
