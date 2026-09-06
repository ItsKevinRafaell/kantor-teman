"""Test tracking last_followup_at lead.

Aturan (card revisi leads tracking, 6 Sep 2026):
- last_followup_at HANYA ke-set pas pesan follow-up/blast TERKIRIM sukses
  via jalur Fonnte (send_whatsapp_message result.ok).
- Ganti status MANUAL TIDAK boleh menyentuh kolom ini.
"""
import asyncio
import json
import uuid
from datetime import datetime, timezone

import pytest

import app.services.campaign_service as cs
from app.constants import LeadStatus
from app.services.lead_service import update_lead_status
from models import Lead, BlastCampaign, BlastMessage, FollowUpSequence, SystemSettings


def _unique_phone():
    return f"081{uuid.uuid4().int % 10**10:010d}"


def _make_lead(db, **kw):
    lead = Lead(business_name=kw.get("business_name", "Test Co"), phone_number=_unique_phone(), status="Scraped")
    db.add(lead)
    db.commit()
    db.refresh(lead)
    return lead


class _OkResult:
    ok = True
    provider = "fonnte"
    error = None


class _FailResult:
    ok = False
    provider = "fonnte"
    error = "simulated fail"


class TestManualStatusDoesNotTouchLastFollowup:
    def test_manual_status_change_keeps_last_followup_at_null(self, db):
        lead = _make_lead(db)
        assert lead.last_followup_at is None

        updated = update_lead_status(db, lead.id, "Replied", "tester")
        assert updated.status == "Replied"
        assert updated.last_followup_at is None

    def test_manual_status_change_keeps_existing_value(self, db):
        lead = _make_lead(db)
        lead.last_followup_at = "2026-09-01T02:00:00+00:00"
        db.commit()

        updated = update_lead_status(db, lead.id, "Prospek Panas", "tester")
        assert updated.last_followup_at == "2026-09-01T02:00:00+00:00"


class TestBlastEngineSetsLastFollowup:
    def _campaign(self, db):
        camp = BlastCampaign(
            name=f"test-blast-{uuid.uuid4().hex[:6]}",
            filter_criteria=json.dumps({}),
            scheduled_for=datetime.now(timezone.utc).isoformat(),
            status="PROCESSING",
        )
        db.add(camp)
        db.commit()
        db.refresh(camp)
        return camp

    def test_blast_success_sets_last_followup_at(self, db, monkeypatch):
        lead = _make_lead(db)
        camp = self._campaign(db)

        async def fake_send(db_, phone, message, meta, number_id=None):
            return _OkResult()

        monkeypatch.setattr(cs, "send_whatsapp_message", fake_send)
        monkeypatch.setattr(cs, "generate_report_for_lead", lambda *a, **k: "slug-test")
        db.add(SystemSettings(key="whatsapp_blast_delay_seconds", value="1"))
        db.commit()

        asyncio.run(cs.execute_blast_campaign(camp, db, None))

        db.refresh(lead)
        assert lead.status == LeadStatus.WA_SENT
        assert lead.last_followup_at is not None
        msg = db.query(BlastMessage).filter(BlastMessage.lead_id == lead.id).first()
        assert msg is not None and msg.status == "sent"

    def test_blast_failure_does_not_set_last_followup_at(self, db, monkeypatch):
        lead = _make_lead(db)
        camp = self._campaign(db)

        async def fake_send(db_, phone, message, meta, number_id=None):
            return _FailResult()

        monkeypatch.setattr(cs, "send_whatsapp_message", fake_send)
        monkeypatch.setattr(cs, "generate_report_for_lead", lambda *a, **k: "slug-test")
        db.add(SystemSettings(key="whatsapp_blast_delay_seconds", value="1"))
        db.commit()

        asyncio.run(cs.execute_blast_campaign(camp, db, None))

        db.refresh(lead)
        assert lead.last_followup_at is None


class TestFollowupProcessorSetsLastFollowup:
    def test_followup_sent_sets_last_followup_at(self, db, monkeypatch):
        lead = _make_lead(db)
        assert lead.last_followup_at is None

        now = datetime.now(timezone.utc)
        wib_hour = now.hour + 7
        if wib_hour >= 24:
            wib_hour -= 24
        db.add(SystemSettings(key="followup_enabled", value="true"))
        db.add(SystemSettings(key="followup_hour", value=str(wib_hour)))
        seq = FollowUpSequence(
            lead_id=lead.id,
            template_ids=json.dumps([]),
            delays=json.dumps([1, 3, 7]),
            current_step=0,
            status="ACTIVE",
            next_send_at=(now.replace(microsecond=0)).isoformat(),
            started_at=now.isoformat(),
        )
        db.add(seq)
        db.commit()

        async def fake_send(db_, phone, message, meta, number_id=None):
            return _OkResult()

        monkeypatch.setattr(cs, "send_whatsapp_message", fake_send)

        # Processor bikin session sendiri dari SessionLocal — pakai session fixture
        # yang sama (StaticPool = 1 koneksi shared) biar datanya keliatan.
        # Catatan: processor memanggil db.close() → instance jadi detached,
        # jadi ID di-capture SEBELUM jalan, query ulang SESUDAH.
        lead_id = lead.id
        seq_id = seq.id
        asyncio.run(cs.scheduled_followup_processor(
            lambda: db, SystemSettings, FollowUpSequence, Lead, object,
        ))

        lead2 = db.query(Lead).filter(Lead.id == lead_id).first()
        assert lead2.last_followup_at is not None
        seq2 = db.query(FollowUpSequence).filter(FollowUpSequence.id == seq_id).first()
        assert seq2.current_step == 1
