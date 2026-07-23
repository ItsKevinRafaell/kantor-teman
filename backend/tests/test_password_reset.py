from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient

from app.core.dependencies import hash_password, verify_password
from models import PasswordResetToken, SystemSettings, User


def _settings(db, **values):
    for key, value in values.items():
        row = db.query(SystemSettings).filter_by(key=key).first()
        if row:
            row.value = value
        else:
            db.add(SystemSettings(key=key, value=value))
    db.commit()


def test_password_reset_request_is_generic_and_sends_email(client: TestClient, db_session, monkeypatch):
    user = User(name="Admin", email="admin@example.test", hashed_password=hash_password("oldpassword"), role="admin")
    db_session.add(user)
    db_session.commit()
    _settings(
        db_session,
        smtp_host="smtp.example.test",
        smtp_port="587",
        smtp_user="sender@example.test",
        smtp_password="app-password",
        smtp_from="sender@example.test",
    )

    sent = {}

    def fake_send(db, to_email, reset_url):
        sent["to"] = to_email
        sent["url"] = reset_url
        return True

    monkeypatch.setattr("routers.auth._send_password_reset_email", fake_send)

    response = client.post("/api/auth/password/forgot", json={"email": "admin@example.test"})

    assert response.status_code == 200
    assert "Jika email terdaftar" in response.json()["message"]
    assert sent["to"] == "admin@example.test"
    assert "/reset-password?token=" in sent["url"]
    assert db_session.query(PasswordResetToken).count() == 1


def test_password_reset_confirm_changes_password_once(client: TestClient, db_session):
    user = User(name="Admin", email="admin@example.test", hashed_password=hash_password("oldpassword"), role="admin")
    db_session.add(user)
    db_session.commit()

    from routers.auth import _hash_reset_token

    raw_token = "reset-token-for-test-1234567890-abcdef"
    db_session.add(PasswordResetToken(
        id="reset-1",
        user_id=user.id,
        token_hash=_hash_reset_token(raw_token),
        expires_at=(datetime.now(timezone.utc) + timedelta(minutes=10)).isoformat(),
        created_at=datetime.now(timezone.utc).isoformat(),
    ))
    db_session.commit()

    response = client.post("/api/auth/password/reset", json={"token": raw_token, "password": "NewP4ssword!"})

    assert response.status_code == 200
    db_session.refresh(user)
    assert verify_password("NewP4ssword!", user.hashed_password)

    second = client.post("/api/auth/password/reset", json={"token": raw_token, "password": "An0th3rP4ss!"})
    assert second.status_code == 400
