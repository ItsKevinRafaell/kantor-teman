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
