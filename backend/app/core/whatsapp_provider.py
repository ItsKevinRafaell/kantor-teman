"""Provider-neutral WhatsApp sender for outreach workflows."""
from __future__ import annotations

import os
import re
from dataclasses import dataclass
from typing import Any, Optional

import httpx
from sqlalchemy.orm import Session

from app.core.config import IS_PRODUCTION
from models import SystemSettings


SUPPORTED_WHATSAPP_PROVIDERS = {"fonnte", "waha", "autolead"}


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
    waha_base_url: str
    waha_api_key: str
    waha_session: str
    autolead_base_url: str
    autolead_api_key: str
    autolead_demo: bool
    blast_delay_seconds: int


def _get_setting(db: Session, key: str, default: str = "") -> str:
    row = db.query(SystemSettings).filter_by(key=key).first()
    return (row.value or default) if row else default


def _clean_base_url(value: str) -> str:
    return (value or "").strip().rstrip("/")


def _safe_int(value: str, default: int, minimum: int = 0, maximum: int = 3600) -> int:
    try:
        parsed = int(str(value).strip())
    except Exception:
        return default
    return max(minimum, min(maximum, parsed))


def get_whatsapp_config(db: Session) -> WhatsAppConfig:
    provider = (_get_setting(db, "whatsapp_provider") or os.getenv("WHATSAPP_PROVIDER") or "fonnte").strip().lower()
    if provider not in SUPPORTED_WHATSAPP_PROVIDERS:
        provider = "fonnte"
    return WhatsAppConfig(
        provider=provider,
        fonnte_token=_get_setting(db, "fonnte_token", os.getenv("FONNTE_TOKEN", "")),
        waha_base_url=_clean_base_url(_get_setting(db, "waha_base_url", os.getenv("WAHA_BASE_URL", "http://127.0.0.1:3000"))),
        waha_api_key=_get_setting(db, "waha_api_key", os.getenv("WAHA_API_KEY", "")),
        waha_session=_get_setting(db, "waha_session", os.getenv("WAHA_SESSION", "default")) or "default",
        autolead_base_url=_clean_base_url(_get_setting(db, "autolead_base_url", os.getenv("AUTOLEAD_BASE_URL", ""))),
        autolead_api_key=_get_setting(db, "autolead_api_key", os.getenv("AUTOLEAD_API_KEY", "")),
        autolead_demo=(_get_setting(db, "autolead_demo", os.getenv("AUTOLEAD_DEMO", "false" if IS_PRODUCTION else "true")) or "true").lower() == "true",
        blast_delay_seconds=_safe_int(
            _get_setting(db, "whatsapp_blast_delay_seconds", os.getenv("WHATSAPP_BLAST_DELAY_SECONDS", "5")),
            default=5,
            minimum=1,
            maximum=300,
        ),
    )


def get_whatsapp_cost_provider_id(db: Session) -> str:
    provider = get_whatsapp_config(db).provider
    if provider == "waha":
        return "WAHA"
    if provider == "autolead":
        return "AUTOLEAD"
    return "FONNTE"


def normalize_waha_chat_id(phone: str) -> str:
    raw = (phone or "").strip()
    if raw.endswith("@c.us") or raw.endswith("@g.us"):
        return raw
    digits = re.sub(r"\D+", "", raw)
    if not digits:
        return ""
    if digits.startswith("0"):
        digits = "62" + digits[1:]
    elif digits.startswith("8"):
        digits = "62" + digits
    return f"{digits}@c.us"


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


async def _send_waha(config: WhatsAppConfig, phone: str, message: str) -> WhatsAppSendResult:
    chat_id = normalize_waha_chat_id(phone)
    if not config.waha_base_url:
        return WhatsAppSendResult(False, "waha", error="WAHA Base URL belum diisi")
    if not config.waha_api_key:
        return WhatsAppSendResult(False, "waha", error="WAHA API key belum diisi")
    if not chat_id:
        return WhatsAppSendResult(False, "waha", error="Nomor WA tidak valid")
    try:
        async with httpx.AsyncClient(timeout=20) as client:
            resp = await client.post(
                f"{config.waha_base_url}/api/sendText",
                headers={
                    "Accept": "application/json",
                    "Content-Type": "application/json",
                    "X-Api-Key": config.waha_api_key,
                },
                json={"session": config.waha_session, "chatId": chat_id, "text": message},
            )
        ok = 200 <= resp.status_code < 300
        try:
            body: Any = resp.json()
        except Exception:
            body = resp.text[:300]
        return WhatsAppSendResult(ok, "waha", status_code=resp.status_code, response=body, error=None if ok else str(body)[:300])
    except Exception as exc:
        return WhatsAppSendResult(False, "waha", error=str(exc))


def _autolead_payload(phone: str, message: str, metadata: Optional[dict[str, Any]] = None, demo: bool = True) -> dict[str, Any]:
    metadata = metadata or {}
    payload = {
        "target": phone,
        "message": message,
        "dry_run": demo,
    }
    for key in ("lead_id", "campaign_id", "template_id", "batch_name", "request_id", "business_name", "contact_name"):
        if metadata.get(key) is not None:
            payload[key] = metadata[key]
    return payload


async def _send_autolead(config: WhatsAppConfig, phone: str, message: str, metadata: Optional[dict[str, Any]] = None) -> WhatsAppSendResult:
    if not config.autolead_base_url:
        return WhatsAppSendResult(False, "autolead", error="AutoLead Base URL belum diisi")
    if not config.autolead_api_key:
        return WhatsAppSendResult(False, "autolead", error="AutoLead API key belum diisi")
    try:
        async with httpx.AsyncClient(timeout=20) as client:
            resp = await client.post(
                f"{config.autolead_base_url}/api/integrations/kantorteman/whatsapp/send",
                headers={
                    "Accept": "application/json",
                    "Content-Type": "application/json",
                    "X-KantorTeman-Key": config.autolead_api_key,
                },
                json=_autolead_payload(phone, message, metadata, config.autolead_demo),
            )
        ok = 200 <= resp.status_code < 300
        try:
            body: Any = resp.json()
            if isinstance(body, dict) and body.get("success") is False:
                ok = False
        except Exception:
            body = resp.text[:300]
        return WhatsAppSendResult(ok, "autolead", status_code=resp.status_code, response=body, error=None if ok else str(body)[:300])
    except Exception as exc:
        return WhatsAppSendResult(False, "autolead", error=str(exc))


async def send_whatsapp_message(db: Session, phone: str, message: str, metadata: Optional[dict[str, Any]] = None) -> WhatsAppSendResult:
    config = get_whatsapp_config(db)
    if config.provider == "autolead":
        return await _send_autolead(config, phone, message, metadata)
    if config.provider == "waha":
        return await _send_waha(config, phone, message)
    return await _send_fonnte(config, phone, message)


def send_whatsapp_message_sync(db: Session, phone: str, message: str, httpx_module=httpx, metadata: Optional[dict[str, Any]] = None) -> WhatsAppSendResult:
    config = get_whatsapp_config(db)
    if config.provider == "autolead":
        if not config.autolead_base_url:
            return WhatsAppSendResult(False, "autolead", error="AutoLead Base URL belum diisi")
        if not config.autolead_api_key:
            return WhatsAppSendResult(False, "autolead", error="AutoLead API key belum diisi")
        try:
            with httpx_module.Client(timeout=20) as client:
                resp = client.post(
                    f"{config.autolead_base_url}/api/integrations/kantorteman/whatsapp/send",
                    headers={
                        "Accept": "application/json",
                        "Content-Type": "application/json",
                        "X-KantorTeman-Key": config.autolead_api_key,
                    },
                    json=_autolead_payload(phone, message, metadata, config.autolead_demo),
                )
            ok = 200 <= resp.status_code < 300
            try:
                body: Any = resp.json()
                if isinstance(body, dict) and body.get("success") is False:
                    ok = False
            except Exception:
                body = resp.text[:300]
            return WhatsAppSendResult(ok, "autolead", status_code=resp.status_code, response=body, error=None if ok else str(body)[:300])
        except Exception as exc:
            return WhatsAppSendResult(False, "autolead", error=str(exc))

    if config.provider == "waha":
        chat_id = normalize_waha_chat_id(phone)
        if not config.waha_base_url:
            return WhatsAppSendResult(False, "waha", error="WAHA Base URL belum diisi")
        if not config.waha_api_key:
            return WhatsAppSendResult(False, "waha", error="WAHA API key belum diisi")
        if not chat_id:
            return WhatsAppSendResult(False, "waha", error="Nomor WA tidak valid")
        try:
            with httpx_module.Client(timeout=20) as client:
                resp = client.post(
                    f"{config.waha_base_url}/api/sendText",
                    headers={
                        "Accept": "application/json",
                        "Content-Type": "application/json",
                        "X-Api-Key": config.waha_api_key,
                    },
                    json={"session": config.waha_session, "chatId": chat_id, "text": message},
                )
            ok = 200 <= resp.status_code < 300
            try:
                body: Any = resp.json()
            except Exception:
                body = resp.text[:300]
            return WhatsAppSendResult(ok, "waha", status_code=resp.status_code, response=body, error=None if ok else str(body)[:300])
        except Exception as exc:
            return WhatsAppSendResult(False, "waha", error=str(exc))

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


async def test_waha_connection(db: Session) -> WhatsAppSendResult:
    config = get_whatsapp_config(db)
    if not config.waha_base_url:
        return WhatsAppSendResult(False, "waha", error="WAHA Base URL belum diisi")
    if not config.waha_api_key:
        return WhatsAppSendResult(False, "waha", error="WAHA API key belum diisi")
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(
                f"{config.waha_base_url}/api/sessions/{config.waha_session}",
                headers={"Accept": "application/json", "X-Api-Key": config.waha_api_key},
            )
        ok = 200 <= resp.status_code < 300
        try:
            body: Any = resp.json()
        except Exception:
            body = resp.text[:300]
        return WhatsAppSendResult(ok, "waha", status_code=resp.status_code, response=body, error=None if ok else str(body)[:300])
    except Exception as exc:
        return WhatsAppSendResult(False, "waha", error=str(exc))


async def test_autolead_connection(db: Session) -> WhatsAppSendResult:
    config = get_whatsapp_config(db)
    if not config.autolead_base_url:
        return WhatsAppSendResult(False, "autolead", error="AutoLead Base URL belum diisi")
    if not config.autolead_api_key:
        return WhatsAppSendResult(False, "autolead", error="AutoLead API key belum diisi")
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(
                f"{config.autolead_base_url}/api/integrations/kantorteman/health",
                headers={"Accept": "application/json", "X-KantorTeman-Key": config.autolead_api_key},
            )
        ok = 200 <= resp.status_code < 300
        try:
            body: Any = resp.json()
        except Exception:
            body = resp.text[:300]
        return WhatsAppSendResult(ok, "autolead", status_code=resp.status_code, response=body, error=None if ok else str(body)[:300])
    except Exception as exc:
        return WhatsAppSendResult(False, "autolead", error=str(exc))
