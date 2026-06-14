"""Fonnte WhatsApp sender for outreach workflows."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import httpx
from sqlalchemy.orm import Session

from models import SystemSettings


WHATSAPP_PROVIDER = "fonnte"


@dataclass
class WhatsAppSendResult:
    ok: bool
    provider: str
    status_code: Optional[int] = None
    error: Optional[str] = None
    response: Any = None


@dataclass
class WhatsAppConfig:
    provider: str
    fonnte_token: str
    blast_delay_seconds: int


def _get_setting(db: Session, key: str, default: str = "") -> str:
    row = db.query(SystemSettings).filter_by(key=key).first()
    return (row.value or default) if row else default


def _safe_int(value: str, default: int, minimum: int = 0, maximum: int = 3600) -> int:
    try:
        parsed = int(str(value).strip())
    except Exception:
        return default
    return max(minimum, min(maximum, parsed))


def get_whatsapp_config(db: Session) -> WhatsAppConfig:
    return WhatsAppConfig(
        provider=WHATSAPP_PROVIDER,
        fonnte_token=_get_setting(db, "fonnte_token", ""),
        blast_delay_seconds=_safe_int(
            _get_setting(db, "whatsapp_blast_delay_seconds", "5"),
            default=5,
            minimum=1,
            maximum=300,
        ),
    )


def get_whatsapp_cost_provider_id(db: Session) -> str:
    get_whatsapp_config(db)
    return "FONNTE"


async def _send_fonnte(config: WhatsAppConfig, phone: str, message: str) -> WhatsAppSendResult:
    if not config.fonnte_token:
        return WhatsAppSendResult(False, "fonnte", error="Token Fonnte belum diisi")
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(
                "https://api.fonnte.com/send",
                headers={"Authorization": config.fonnte_token},
                data={"target": phone, "message": message, "delay": str(config.blast_delay_seconds)},
            )
        ok = resp.status_code == 200
        try:
            body: Any = resp.json()
            if isinstance(body, dict) and body.get("status") is False:
                ok = False
        except Exception:
            body = resp.text[:300]
        return WhatsAppSendResult(ok, "fonnte", status_code=resp.status_code, response=body, error=None if ok else str(body)[:300])
    except Exception as exc:
        return WhatsAppSendResult(False, "fonnte", error=str(exc))


async def send_whatsapp_message(db: Session, phone: str, message: str, metadata: dict[str, Any] | None = None) -> WhatsAppSendResult:
    config = get_whatsapp_config(db)
    return await _send_fonnte(config, phone, message)


def send_whatsapp_message_sync(db: Session, phone: str, message: str, httpx_module=httpx, metadata: dict[str, Any] | None = None) -> WhatsAppSendResult:
    config = get_whatsapp_config(db)
    if not config.fonnte_token:
        return WhatsAppSendResult(False, "fonnte", error="Token Fonnte belum diisi")
    try:
        with httpx_module.Client(timeout=15) as client:
            resp = client.post(
                "https://api.fonnte.com/send",
                headers={"Authorization": config.fonnte_token},
                data={"target": phone, "message": message, "delay": str(config.blast_delay_seconds)},
            )
        ok = resp.status_code == 200
        try:
            body: Any = resp.json()
            if isinstance(body, dict) and body.get("status") is False:
                ok = False
        except Exception:
            body = resp.text[:300]
        return WhatsAppSendResult(ok, "fonnte", status_code=resp.status_code, response=body, error=None if ok else str(body)[:300])
    except Exception as exc:
        return WhatsAppSendResult(False, "fonnte", error=str(exc))
