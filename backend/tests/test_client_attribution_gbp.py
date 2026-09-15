from app.core.security import create_token
from models import ClientAttributionGBP, Contact, Lead, User


def _auth_headers(db_session):
    user = User(name="Tester", email="tester@example.com", hashed_password="x", role="admin")
    db_session.add(user)
    db_session.commit()
    return {"Authorization": f"Bearer {create_token(user.id, user.email, user.token_version)}"}


def _contact_with_lead(db_session):
    lead = Lead(business_name="Evidence Only", phone_number="081234567890")
    db_session.add(lead)
    db_session.flush()
    contact = Contact(business_name="Evidence Only", phone_number="081234567891", lead_id=lead.id)
    db_session.add(contact)
    db_session.commit()
    return contact, lead


def _payload(url="https://example.test/landing?ref=internal+note"):
    return {
        "canonical_landing_url": url,
        "ga4_measurement_id": "G-ABC123",
        "conversion_event_name": "whatsapp_click",
        "conversion_event_verified": True,
        "readiness_note": "Verified from stored internal evidence.",
    }


def test_attribution_gbp_requires_auth(client):
    response = client.get("/api/clients/1/attribution-gbp")
    assert response.status_code == 401


def test_attribution_gbp_get_is_empty_and_never_seeds_or_guesses(client, db_session):
    contact, lead = _contact_with_lead(db_session)
    response = client.get(f"/api/clients/{contact.id}/attribution-gbp", headers=_auth_headers(db_session))
    assert response.status_code == 200
    assert response.json() == {
        "lead_id": lead.id,
        "canonical_landing_url": None,
        "generated_url": None,
        "ga4_measurement_id": None,
        "conversion_event_name": None,
        "conversion_event_verified": False,
        "readiness_note": None,
        "created_at": None,
        "updated_at": None,
    }
    assert db_session.query(ClientAttributionGBP).count() == 0


def test_attribution_gbp_put_roundtrip_and_exact_encoded_url(client, db_session):
    contact, lead = _contact_with_lead(db_session)
    headers = _auth_headers(db_session)
    response = client.put(f"/api/clients/{contact.id}/attribution-gbp", headers=headers, json=_payload())
    assert response.status_code == 200
    body = response.json()
    assert body["lead_id"] == lead.id
    assert body["canonical_landing_url"] == "https://example.test/landing?ref=internal+note"
    assert body["generated_url"] == "https://example.test/landing?ref=internal+note&utm_source=google&utm_medium=organic&utm_campaign=gbp&utm_content=website"
    assert body["ga4_measurement_id"] == "G-ABC123"
    assert body["conversion_event_verified"] is True
    assert db_session.query(ClientAttributionGBP).filter_by(lead_id=lead.id).count() == 1

    fetched = client.get(f"/api/clients/{contact.id}/attribution-gbp", headers=headers)
    assert fetched.status_code == 200
    assert fetched.json()["generated_url"] == body["generated_url"]


def test_attribution_gbp_rejects_non_https_fragments_and_any_utm_key(client, db_session):
    contact, _ = _contact_with_lead(db_session)
    headers = _auth_headers(db_session)
    for url in ("http://example.test", "https://example.test/#section", "https://example.test/?UTM_Source=old", "https://example.test/?not_utm=ok&utm_other=x"):
        response = client.put(f"/api/clients/{contact.id}/attribution-gbp", headers=headers, json=_payload(url))
        assert response.status_code == 400
    assert db_session.query(ClientAttributionGBP).count() == 0


def test_attribution_gbp_returns_404_for_missing_contact_or_contact_without_lead(client, db_session):
    headers = _auth_headers(db_session)
    assert client.get("/api/clients/9999/attribution-gbp", headers=headers).status_code == 404

    orphan = Contact(business_name="Orphan", phone_number="081200000001")
    db_session.add(orphan)
    db_session.commit()
    assert client.get(f"/api/clients/{orphan.id}/attribution-gbp", headers=headers).status_code == 404
