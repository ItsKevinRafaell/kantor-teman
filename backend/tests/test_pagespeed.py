"""Tests fitur PageSpeed scoring lead.

Spec (task Kevin via nara, 6 Sep 2026):
- kolom page_speed_score + last_speed_check di leads (migrate idempotent)
- auto-check saat lead ke-scrape/ke-buat dengan website_url (fail-open)
- POST /api/leads/{id}/speed-check trigger manual
- GET /api/leads hot_list filter (no web / skor rendah / web gating IG-Linktree)
- LeadOut expose skor
"""
import os
import subprocess
import uuid

import pytest

import app.services.pagespeed_service as pss
from app.core.cache import clear_cache_prefix
from app.core.dependencies import create_token, hash_password
from models import User, Lead


@pytest.fixture(autouse=True)
def _clear_leads_cache():
    """Cache 30s antar-test bisa balikin data test sebelumnya (tabel udah di-drop/recreate)."""
    clear_cache_prefix("cache:/api/leads")
    yield
    clear_cache_prefix("cache:/api/leads")


def _unique_phone():
    return f"0812{uuid.uuid4().hex[:8]}"


def _user(db, email="admin@example.test", role="admin"):
    u = db.query(User).filter(User.email == email).first()
    if not u:
        u = User(email=email, name="Admin Test", hashed_password=hash_password("Password!234"), role=role)
        db.add(u)
        db.commit()
        db.refresh(u)
    return u


def _admin_headers(client, db):
    u = _user(db)
    token = create_token(u.id, u.email)
    return {"Authorization": f"Bearer {token}"}, u


def _make_lead(db, **kw):
    lead = Lead(
        business_name=kw.get("business_name", "CV Uji Speed"),
        phone_number=_unique_phone(),
        status=kw.get("status", "Scraped"),
        website_url=kw.get("website_url"),
        page_speed_score=kw.get("page_speed_score"),
        last_speed_check=kw.get("last_speed_check"),
    )
    db.add(lead)
    db.commit()
    db.refresh(lead)
    return lead


@pytest.fixture
def no_psi_call(monkeypatch):
    """PSI jangan pernah di-call beneran dari unit test; kembalikan skor 42."""
    calls = []

    def _fake_fetch(url, api_key="", strategy="mobile", timeout=45.0):
        calls.append(url)
        return 42, None

    monkeypatch.setattr(pss, "fetch_pagespeed_score", _fake_fetch)
    monkeypatch.setattr(pss, "resolve_api_key", lambda fallback="": "")
    return calls


# ── Helper murni ─────────────────────────────────────────────────────────────
class TestHelpers:
    def test_normalize_adds_scheme(self):
        assert pss.normalize_website_url("tokobaju.com") == "https://tokobaju.com"
        assert pss.normalize_website_url("https://tokobaju.com/path") == "https://tokobaju.com/path"

    def test_normalize_rejects_empty(self):
        assert pss.normalize_website_url("") is None
        assert pss.normalize_website_url(None) is None
        assert pss.normalize_website_url("   ") is None

    def test_gating_web_detection(self):
        assert pss.is_gating_web("https://www.instagram.com/tokobaju") is True
        assert pss.is_gating_web("https://linktr.ee/tokobaju") is True
        assert pss.is_gating_web("https://s.id/toko") is True
        assert pss.is_gating_web("https://wa.me/628123") is True
        assert pss.is_gating_web("https://tokobaju.com") is False
        assert pss.is_gating_web(None) is False
        assert pss.is_gating_web("") is False


# ── Migrate idempotent (SQLite jalur, simulasi DB prod existing) ────────────
class TestMigrate:
    def _make_db_like_prod(self, db_file):
        """Buat schema penuh via model, lalu drop 2 kolom baru → simulasi
        prod yang belum punya page_speed_score/last_speed_check."""
        import sqlite3
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker
        from models.base import Base

        engine = create_engine(f"sqlite:///{db_file}")
        Base.metadata.create_all(bind=engine)
        engine.dispose()
        con = sqlite3.connect(db_file)
        con.execute("ALTER TABLE leads DROP COLUMN page_speed_score")
        con.execute("ALTER TABLE leads DROP COLUMN last_speed_check")
        con.commit()
        con.close()

    def test_migrate_sqlite_idempotent_two_runs(self, tmp_path):
        db_file = tmp_path / "ps_migrate_test.db"
        self._make_db_like_prod(db_file)
        env = dict(os.environ)
        env["DATABASE_URL"] = f"sqlite:///{db_file}"
        repo_backend = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        outs = []
        for _ in range(2):
            proc = subprocess.run(
                ["python", "migrate.py"], cwd=repo_backend, env=env,
                capture_output=True, text=True, timeout=120,
            )
            outs.append(proc)
        assert outs[0].returncode == 0, outs[0].stderr[-500:]
        assert outs[1].returncode == 0, outs[1].stderr[-500:]
        # Run pertama: kolom ditambahkan. Run kedua: skip (idempotent).
        assert "+ kolom page_speed_score ditambahkan ke leads" in outs[0].stdout
        assert "= leads.page_speed_score sudah ada, skip" in outs[1].stdout
        assert "+ kolom last_speed_check ditambahkan ke leads" in outs[0].stdout
        assert "= leads.last_speed_check sudah ada, skip" in outs[1].stdout


# ── Endpoint trigger manual ──────────────────────────────────────────────────
class TestSpeedCheckEndpoint:
    def test_speed_check_success(self, client, db, no_psi_call):
        headers, _ = _admin_headers(client, db)
        lead = _make_lead(db, website_url="tokobajukece.com")
        resp = client.post(f"/api/leads/{lead.id}/speed-check", headers=headers)
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["page_speed_score"] == 42
        assert body["last_speed_check"]
        assert body["error"] is None
        db.expire_all()
        fresh = db.query(Lead).filter(Lead.id == lead.id).first()
        assert fresh.page_speed_score == 42
        assert fresh.last_speed_check

    def test_speed_check_no_web_400(self, client, db, no_psi_call):
        headers, _ = _admin_headers(client, db)
        lead = _make_lead(db, website_url=None)
        resp = client.post(f"/api/leads/{lead.id}/speed-check", headers=headers)
        assert resp.status_code == 400

    def test_speed_check_psi_error_keeps_old_score(self, client, db, monkeypatch):
        headers, _ = _admin_headers(client, db)
        lead = _make_lead(db, website_url="https://lama.com", page_speed_score=77)

        def _fail(url, api_key="", strategy="mobile", timeout=45.0):
            return None, "PSI HTTP 500: boom"

        monkeypatch.setattr(pss, "fetch_pagespeed_score", _fail)
        monkeypatch.setattr(pss, "resolve_api_key", lambda fallback="": "")
        resp = client.post(f"/api/leads/{lead.id}/speed-check", headers=headers)
        assert resp.status_code == 200
        body = resp.json()
        assert body["error"] == "PSI HTTP 500: boom"
        db.expire_all()
        fresh = db.query(Lead).filter(Lead.id == lead.id).first()
        assert fresh.page_speed_score == 77  # skor lama utuh
        assert fresh.last_speed_check is None

    def test_speed_check_requires_auth(self, client, db):
        lead = _make_lead(db, website_url="https://x.com")
        resp = client.post(f"/api/leads/{lead.id}/speed-check")
        assert resp.status_code in (401, 403)


# ── GET /api/leads expose skor + hot_list filter ─────────────────────────────
class TestListLeadsHotList:
    def test_leadout_exposes_speed_fields(self, client, db):
        headers, _ = _admin_headers(client, db)
        _make_lead(db, website_url="https://cepet.com", page_speed_score=88, last_speed_check="2026-09-06 10:00:00")
        resp = client.get("/api/leads", headers=headers)
        assert resp.status_code == 200
        rows = resp.json()
        target = next(r for r in rows if r["website_url"] == "https://cepet.com")
        assert target["page_speed_score"] == 88
        assert target["last_speed_check"] == "2026-09-06 10:00:00"

    def test_hot_list_includes_no_web_low_score_gating_excludes_fast(self, client, db):
        headers, _ = _admin_headers(client, db)
        no_web = _make_lead(db, business_name="Tanpa Web", website_url=None)
        slow = _make_lead(db, business_name="Web Lemot", website_url="https://lemot.com", page_speed_score=35)
        gated = _make_lead(db, business_name="Cuma IG", website_url="https://instagram.com/cumaig")
        fast = _make_lead(db, business_name="Web Kenceng", website_url="https://kenceng.com", page_speed_score=90)
        unchecked = _make_lead(db, business_name="Belum Dicek", website_url="https://belum.com", page_speed_score=None)

        resp = client.get("/api/leads?hot_list=true", headers=headers)
        assert resp.status_code == 200
        ids = {r["id"] for r in resp.json()}
        assert no_web.id in ids
        assert slow.id in ids
        assert gated.id in ids
        assert unchecked.id in ids  # belum dicek = tetap kandidat prioritas
        assert fast.id not in ids

    def test_hot_list_false_returns_all(self, client, db):
        headers, _ = _admin_headers(client, db)
        fast = _make_lead(db, website_url="https://kenceng2.com", page_speed_score=95)
        resp = client.get("/api/leads", headers=headers)
        ids = {r["id"] for r in resp.json()}
        assert fast.id in ids

    def test_hot_list_custom_threshold(self, client, db):
        headers, _ = _admin_headers(client, db)
        mid = _make_lead(db, website_url="https://sedang.com", page_speed_score=70)
        resp = client.get("/api/leads?hot_list=true&hot_max_score=80", headers=headers)
        ids = {r["id"] for r in resp.json()}
        assert mid.id in ids


# ── Background task fail-open ────────────────────────────────────────────────
class TestBackgroundHook:
    def test_run_speed_check_bg_does_not_raise_on_bad_db_url(self):
        # fail-open: db url rusak → print log, TIDAK raise
        pss.run_speed_check_bg("sqlite:////nonexistent/dir/x.db", 999999, "")

    def test_run_speed_check_bg_updates_score(self, monkeypatch, tmp_path):
        import sqlite3
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker
        from models.base import Base
        import models as m

        db_file = tmp_path / "bg.db"
        engine = create_engine(f"sqlite:///{db_file}")
        Base.metadata.create_all(bind=engine)
        S = sessionmaker(bind=engine)
        s = S()
        lead = Lead(business_name="BG Lead", phone_number=_unique_phone(), website_url="https://bgtest.com")
        s.add(lead)
        s.commit()
        lead_id = lead.id
        s.close()

        monkeypatch.setattr(pss, "fetch_pagespeed_score", lambda url, api_key="", strategy="mobile", timeout=45.0: (55, None))
        monkeypatch.setattr(pss, "resolve_api_key", lambda fallback="": "")
        pss.run_speed_check_bg(f"sqlite:///{db_file}", lead_id, "")

        s2 = S()
        fresh = s2.query(Lead).filter(Lead.id == lead_id).first()
        assert fresh.page_speed_score == 55
        assert fresh.last_speed_check
        s2.close()
