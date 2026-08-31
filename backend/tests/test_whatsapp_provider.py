import asyncio

from app.core.whatsapp_provider import get_whatsapp_config, send_whatsapp_message
from models import SystemSettings


def _setting(db, key: str, value: str) -> None:
    db.add(SystemSettings(key=key, value=value))
    db.commit()


def test_get_whatsapp_config_is_fonnte_only(db_session):
    _setting(db_session, "whatsapp_provider", "waha")

    config = get_whatsapp_config(db_session)

    assert config.provider == "fonnte"
    assert config.blast_delay_seconds == 5


def test_send_whatsapp_message_uses_fonnte_payload(db_session, monkeypatch):
    _setting(db_session, "whatsapp_provider", "autolead")
    _setting(db_session, "fonnte_token", "secret-token")
    _setting(db_session, "whatsapp_blast_delay_seconds", "7")

    captured = {}

    class FakeResponse:
        status_code = 200
        text = '{"status":true}'

        def json(self):
            return {"status": True, "id": "message-id"}

    class FakeAsyncClient:
        def __init__(self, timeout):
            self.timeout = timeout

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return None

        async def post(self, url, headers, data):
            captured["url"] = url
            captured["headers"] = headers
            captured["data"] = data
            return FakeResponse()

    monkeypatch.setattr("app.core.whatsapp_provider.httpx.AsyncClient", FakeAsyncClient)

    result = asyncio.run(send_whatsapp_message(db_session, "081234567890", "Halo"))

    assert result.ok is True
    assert result.provider == "fonnte"
    assert captured["url"] == "https://api.fonnte.com/send"
    assert captured["headers"]["Authorization"] == "secret-token"
    assert captured["data"] == {"target": "081234567890", "message": "Halo", "delay": "7"}


def _wa_number(db, **kwargs) -> "WhatsAppNumber":
    from models import WhatsAppNumber
    row = WhatsAppNumber(
        id=kwargs.get("id", "num-1"),
        label=kwargs.get("label", "Nomor Klien"),
        phone_number=kwargs.get("phone_number", "6281234567890"),
        token=kwargs.get("token", "device-token-1"),
        is_active=kwargs.get("is_active", True),
        created_at="2026-08-31T00:00:00+00:00",
    )
    db.add(row)
    db.commit()
    return row


def test_get_whatsapp_config_uses_selected_number(db_session):
    _setting(db_session, "fonnte_token", "legacy-token")
    _wa_number(db_session, id="num-1", token="device-token-1")

    config = get_whatsapp_config(db_session, "num-1")

    assert config.fonnte_token == "device-token-1"
    assert config.source == "whatsapp_numbers:num-1"


def test_get_whatsapp_config_rejects_inactive_number(db_session):
    _setting(db_session, "fonnte_token", "legacy-token")
    _wa_number(db_session, id="num-2", token="device-token-2", is_active=False)

    import pytest
    with pytest.raises(ValueError, match="nonaktif"):
        get_whatsapp_config(db_session, "num-2")


def test_get_whatsapp_config_rejects_missing_number(db_session):
    import pytest
    with pytest.raises(ValueError, match="tidak ditemukan"):
        get_whatsapp_config(db_session, "num-404")


def test_get_whatsapp_config_without_number_falls_back_legacy(db_session):
    _setting(db_session, "fonnte_token", "legacy-token")

    config = get_whatsapp_config(db_session, None)

    assert config.fonnte_token == "legacy-token"
    assert config.source == "system_settings"
