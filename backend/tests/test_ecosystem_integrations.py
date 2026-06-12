from routers.integrations import ecosystem_status
from models import SystemSettings


def _setting(db, key: str, value: str) -> None:
    db.add(SystemSettings(key=key, value=value))
    db.commit()


def test_ecosystem_status_reports_config_without_secrets(db_session):
    _setting(db_session, "external_lead_api_key", "external-secret")
    _setting(db_session, "whatsapp_provider", "autolead")
    _setting(db_session, "autolead_base_url", "https://leadbot.example.test")
    _setting(db_session, "autolead_api_key", "bridge-secret")
    _setting(db_session, "autolead_demo", "true")

    status = ecosystem_status(db_session)

    assert status["service"] == "kantorteman"
    assert status["source_of_truth"] is True
    assert status["status"] == "ok"
    assert status["lead_intake"]["external_lead_api_key_configured"] is True
    assert status["whatsapp"]["provider"] == "autolead"
    assert status["whatsapp"]["autolead_configured"] is True
    assert status["whatsapp"]["autolead_demo"] is True
    assert status["whatsapp"]["autolead_host"] == "leadbot.example.test"
    assert "external-secret" not in str(status)
    assert "bridge-secret" not in str(status)
