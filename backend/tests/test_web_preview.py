"""Tests fitur web preview: generate per-lead, reuse, tracking buka,
integrasi blast (lead panas dapat link, bukan panas tidak), dan
kegagalan generate tidak memblokir blast."""
import asyncio
import json
import uuid

from app.core.dependencies import create_token, hash_password
from app.constants import LeadStatus
from app.services.web_preview_service import normalize_wa
from models import User, Lead, BlastCampaign, DynamicTemplate, WebPreview


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


def _unique_phone():
    return f"0812{uuid.uuid4().hex[:8]}"


def _hot_lead(db, **kw):
    lead = Lead(business_name=kw.get("business_name", "CV Uji Coba"), phone_number=_unique_phone(),
                status=LeadStatus.HOT_PROSPECT, is_archived=False, do_not_contact=False,
                address=kw.get("address"))
    db.add(lead)
    db.commit()
    db.refresh(lead)
    return lead


# ── Generate + view publik ───────────────────────────────────────────────────
class TestGenerateAndView:
    def test_generate_returns_slug_and_url(self, client, db):
        headers, _ = _admin_headers(client, db)
        lead = _hot_lead(db)

        r = client.post(f"/api/web-preview/generate/{lead.id}", headers=headers, json={})
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["reused"] is False
        assert body["template_key"] in ("klinik", "bengkel", "kontraktor")
        assert body["url"].endswith(f"/wp/{body['slug']}")

        assert db.query(WebPreview).filter_by(lead_id=lead.id).count() == 1

    def test_generate_reuses_existing(self, client, db):
        headers, _ = _admin_headers(client, db)
        lead = _hot_lead(db)
        r1 = client.post(f"/api/web-preview/generate/{lead.id}", headers=headers, json={})
        r2 = client.post(f"/api/web-preview/generate/{lead.id}", headers=headers, json={})
        assert r1.json()["slug"] == r2.json()["slug"]
        assert r2.json()["reused"] is True
        assert db.query(WebPreview).filter_by(lead_id=lead.id).count() == 1

    def test_generate_unknown_template_422(self, client, db):
        headers, _ = _admin_headers(client, db)
        lead = _hot_lead(db)
        r = client.post(f"/api/web-preview/generate/{lead.id}", headers=headers,
                        json={"template_key": "ga-ada"})
        assert r.status_code == 422

    def test_view_tracks_open(self, client, db):
        headers, _ = _admin_headers(client, db)
        lead = _hot_lead(db)
        slug = client.post(f"/api/web-preview/generate/{lead.id}", headers=headers, json={}).json()["slug"]

        r = client.get(f"/wp/{slug}")
        assert r.status_code == 200
        assert "text/html" in r.headers["content-type"]
        # Nama bisnis lead harus ter-render di HTML (swap brand berhasil)
        assert lead.business_name in r.text

        row = db.query(WebPreview).filter_by(slug=slug).first()
        db.expire_all()
        row = db.query(WebPreview).filter_by(slug=slug).first()
        assert row.opened_count == 1
        assert row.first_opened_at is not None

    def test_view_unknown_slug_404(self, client, db):
        r = client.get("/wp/tidak-ada-slug-ini")
        assert r.status_code == 404

    def test_keyword_selects_klinik(self, client, db):
        from app.services.web_preview_service import select_template_key
        lead = Lead(business_name="Klinik Gigi Sehat", phone_number=_unique_phone(),
                    product_interest="klinik kesehatan", status=LeadStatus.HOT_PROSPECT)
        assert select_template_key(lead) == "klinik"
        lead2 = Lead(business_name="Bengkel Jaya Motor", phone_number=_unique_phone(),
                     product_interest="servis mobil", status=LeadStatus.HOT_PROSPECT)
        assert select_template_key(lead2) == "bengkel"
        lead3 = Lead(business_name="Toko Baru", phone_number=_unique_phone(), status=LeadStatus.HOT_PROSPECT)
        assert select_template_key(lead3) == "kontraktor"  # default

    def test_asset_rewrite_keeps_html_quotes_intact(self, client, db):
        """Kutip penutup atribut tidak boleh hilang saat rewrite asset."""
        from app.services.web_preview_service import _render
        lead = Lead(business_name="Klinik Uji Kutip", phone_number="081299998888",
                    product_interest="klinik")
        html = _render("klinik", lead)
        assert 'src="/uploads/web_preview_assets/klinik/01.jpg"' in html
        # Atribut setelah src tidak boleh nyemplak ke dalam nilai src
        assert 'jpg alt=' not in html
        # Tidak ada sisa path relatif template
        assert "klinik-assets/" not in html


# ── Integrasi blast ──────────────────────────────────────────────────────────
def _setup_blast(monkeypatch, db, lead, status_text):
    """Siapkan campaign + template WA_BLAST, monkeypatch send, jalankan execute."""
    from app.services import campaign_service

    template = DynamicTemplate(
        id=str(uuid.uuid4()), name="t", type="WA_BLAST", is_active=True,
        content=status_text,
    )
    db.add(template)
    db.commit()
    campaign = BlastCampaign(
        id=str(uuid.uuid4()), name="c", template_id=template.id,
        filter_criteria=json.dumps({"status": lead.status, "batch_name": "b1"}),
        scheduled_for="2026-01-01T00:00:00Z", status="PENDING",
        created_at="2026-01-01T00:00:00Z",
    )
    db.add(campaign)
    db.commit()
    db.refresh(campaign)

    captured = {}

    # Lead harus punya batch_name yang sama dengan criteria blast
    lead.batch_name = "b1"
    db.commit()

    async def _fake_send(_db, phone, message, meta=None, number_id=None):
        captured["phone"] = phone
        captured["message"] = message
        class _R:
            ok = True
            error = None
            provider = "test"
        return _R()

    monkeypatch.setattr(campaign_service, "send_whatsapp_message", _fake_send)

    class _Cfg:
        blast_delay_seconds = 0
    monkeypatch.setattr(campaign_service, "get_whatsapp_config", lambda *_a, **_k: _Cfg())
    monkeypatch.setattr(campaign_service, "generate_report_for_lead", lambda *_a, **_k: "dummy-slug")

    asyncio.run(campaign_service.execute_blast_campaign(campaign, db, None))
    return captured


class TestBlastIntegration:
    def test_hot_lead_gets_preview_link(self, client, db, monkeypatch):
        lead = _hot_lead(db)
        captured = _setup_blast(
            monkeypatch, db, lead,
            "Halo {{client_name}}, cek {{proposal_link}} dan {{web_preview_link}} ya.",
        )
        msg = captured["message"]
        assert "/wp/" in msg
        assert "{{web_preview_link}}" not in msg
        assert lead.business_name in msg

    def test_hot_lead_without_placeholder_gets_appended_link(self, client, db, monkeypatch):
        lead = _hot_lead(db)
        captured = _setup_blast(monkeypatch, db, lead, "Halo {{client_name}}.")
        assert "/wp/" in captured["message"]

    def test_non_hot_lead_no_preview(self, client, db, monkeypatch):
        lead = Lead(business_name="Scraped Co", phone_number=_unique_phone(),
                    status=LeadStatus.SCRAPED, is_archived=False, do_not_contact=False)
        db.add(lead)
        db.commit()
        db.refresh(lead)
        captured = _setup_blast(monkeypatch, db, lead, "Halo {{client_name}}.")
        assert "/wp/" not in captured["message"]

    def test_preview_failure_does_not_block_blast(self, client, db, monkeypatch):
        from app.services import campaign_service, web_preview_service

        lead = _hot_lead(db)

        def _boom(*a, **k):
            raise RuntimeError("template hilang")
        monkeypatch.setattr(web_preview_service, "generate_preview_for_lead", _boom)
        # Patch referensi yang dipakai campaign_service (import langsung)
        monkeypatch.setattr(campaign_service, "generate_preview_for_lead", _boom)

        captured = _setup_blast(
            monkeypatch, db, lead,
            "Halo {{client_name}}, laporan: {{proposal_link}}. Preview: {{web_preview_link}}.",
        )
        assert captured["message"].startswith("Halo CV Uji Coba")
        assert "{{web_preview_link}}" not in captured["message"]
        assert "/wp/" not in captured["message"]


# ── Sanitasi data sample template (6 Sep 2026) ──────────────────────────────
class TestSampleDataSanitized:
    """Slot FAKTUAL (kontak, alamat, brand, kota di slot info) tidak boleh masih
    bawa data sample template. Klaim marketing sample (harga, tahun, jumlah
    proyek, portfolio, testimoni) = isu konten terpisah, dilaporkan ke Kevin."""

    def _view(self, client, db, lead):
        headers, _ = _admin_headers(client, db)
        r = client.post(f"/api/web-preview/generate/{lead.id}", headers=headers, json={})
        assert r.status_code == 200, r.text
        slug = r.json()["slug"]
        return client.get(f"/wp/{slug}").text

    def test_kontraktor_no_sample_brand_or_contacts(self, client, db):
        lead = _hot_lead(db, business_name="PT Mitra Uji Sarana",
                         address="Jl. Melati No. 9, Bandung, Jawa Barat")
        html = self._view(client, db, lead)
        for dummy in ["Cipta Griya", "ciptagriya", "765-5188", ">CG<", "MT Haryono No. 88",
                      "KONTRAKTOR · BALIKPAPAN", "Area layanan: Balikpapan",
                      "Punya rencana bangun di Balikpapan", "sejak 2010",
                      "tel:+625427655188", "625427655188"]:
            assert dummy not in html, f"dummy '{dummy}' bocor"
        assert "PT Mitra Uji Sarana" in html
        wa = normalize_wa(lead.phone_number)
        assert f"wa.me/{wa}" in html
        assert f"tel:+{wa}" in html
        assert "Jl. Melati No. 9" in html

    def test_no_address_falls_back_to_neutral_area(self, client, db):
        lead = _hot_lead(db)  # tanpa address
        html = self._view(client, db, lead)
        assert "kota Anda &amp; sekitarnya" in html or "kota Anda & sekitarnya" in html
        assert "MT Haryono No. 88" not in html

    def test_bengkel_no_sample_brand_or_email(self, client, db):
        lead = _hot_lead(db, business_name="Bengkel Jaya Motor")
        html = self._view(client, db, lead)
        for dummy in ["garasi88", "Soekarno Hatta", ">G88<", "SPBU KM 5",
                      "Balikpapan</span>", "Bengkel motor jujur di Balikpapan"]:
            assert dummy not in html, f"dummy '{dummy}' bocor"
        assert "BJM" in html          # inisial brand lead
        assert "Bengkel Jaya Motor" in html

    def test_klinik_no_sample_address(self, client, db):
        lead = _hot_lead(db, business_name="Klinik Uji Bersih",
                         address="Jl. Anggrek 12, Surabaya")
        html = self._view(client, db, lead)
        for dummy in ["Jl. Soekarno-Hatta", "Gunung Samarinda", "Balikpapan"]:
            assert dummy not in html, f"dummy '{dummy}' bocor"
        assert "Jl. Anggrek 12" in html
        assert "Klinik Uji Bersih" in html
