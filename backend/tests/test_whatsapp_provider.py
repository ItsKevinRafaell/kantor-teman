import asyncio

from app.core.whatsapp_provider import (
    get_whatsapp_config,
    normalize_waha_chat_id,
    send_whatsapp_message,
)
from models import SystemSettings


def _setting(db, key: str, value: str) -> None:
    db.add(SystemSettings(key=key, value=value))
    db.commit()


def test_normalize_waha_chat_id():
    assert normalize_waha_chat_id("0812-3456-7890") == "6281234567890@c.us"
    assert normalize_waha_chat_id("81234567890") == "6281234567890@c.us"
    assert normalize_waha_chat_id("6281234567890") == "6281234567890@c.us"
    assert normalize_waha_chat_id("6281234567890@c.us") == "6281234567890@c.us"


def test_get_whatsapp_config_defaults_to_fonnte(db_session):
    config = get_whatsapp_config(db_session)
    assert config.provider == "fonnte"
    assert config.waha_session == "default"
    assert config.blast_delay_seconds == 5


def test_send_whatsapp_message_uses_waha_payload(db_session, monkeypatch):
    _setting(db_session, "whatsapp_provider", "waha")
    _setting(db_session, "waha_base_url", "http://waha.local")
    _setting(db_session, "waha_api_key", "secret-key")
    _setting(db_session, "waha_session", "kantor")

    captured = {}

    class FakeResponse:
        status_code = 201

        def json(self):
            return {"id": "message-id"}

    class FakeAsyncClient:
        def __init__(self, timeout):
            self.timeout = timeout

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return None

        async def post(self, url, headers, json):
            captured["url"] = url
            captured["headers"] = headers
            captured["json"] = json
            return FakeResponse()

    monkeypatch.setattr("app.core.whatsapp_provider.httpx.AsyncClient", FakeAsyncClient)

    result = asyncio.run(send_whatsapp_message(db_session, "081234567890", "Halo"))

    assert result.ok is True
    assert result.provider == "waha"
    assert captured["url"] == "http://waha.local/api/sendText"
    assert captured["headers"]["X-Api-Key"] == "secret-key"
    assert captured["json"] == {
        "session": "kantor",
        "chatId": "6281234567890@c.us",
        "text": "Halo",
    }


def test_send_whatsapp_message_uses_autolead_bridge_payload(db_session, monkeypatch):
    _setting(db_session, "whatsapp_provider", "autolead")
    _setting(db_session, "autolead_base_url", "https://leadbot.example.test")
    _setting(db_session, "autolead_api_key", "bridge-token")
    _setting(db_session, "autolead_demo", "true")

    captured = {}

    class FakeResponse:
        status_code = 200

        def json(self):
            return {"success": True, "action": "demo_recorded"}

    class FakeAsyncClient:
        def __init__(self, timeout):
            self.timeout = timeout

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return None

        async def post(self, url, headers, json):
            captured["url"] = url
            captured["headers"] = headers
            captured["json"] = json
            return FakeResponse()

    monkeypatch.setattr("app.core.whatsapp_provider.httpx.AsyncClient", FakeAsyncClient)

    result = asyncio.run(send_whatsapp_message(db_session, "081234567890", "Halo", {
        "lead_id": 12,
        "campaign_id": "campaign-1",
        "business_name": "Toko Demo",
    }))

    assert result.ok is True
    assert result.provider == "autolead"
    assert captured["url"] == "https://leadbot.example.test/api/integrations/kantorteman/whatsapp/send"
    assert captured["headers"]["X-KantorTeman-Key"] == "bridge-token"
    assert captured["json"] == {
        "target": "081234567890",
        "message": "Halo",
        "dry_run": True,
        "lead_id": 12,
        "campaign_id": "campaign-1",
        "business_name": "Toko Demo",
    }
