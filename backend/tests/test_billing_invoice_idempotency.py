"""P0-3 verifikasi: idempotensi generate_due_monthly_invoices (billing scheduler).

Syarat aman sebelum scheduler billing boleh dinyalakan (menunggu ACC Kevin):
jalankan 2x berturut HARUS menghasilkan 1 invoice per periode, bukan duplikat.
Ini versi service-level dari verifikasi manual "trigger 2x" di PLAN-FIX-P0.

Pakai pipeline DOKUMEN ASLI (DocumentTemplate 'invoice' aktif diseed,
reportlab tersedia di venv test) supaya tag template_name yang dipakai guard
periode benar-benar terbukti ter-set oleh jalur produksi, bukan mock.
"""
from datetime import datetime, timedelta, timezone

import pytest

from app.services.sales_workflow_service import generate_due_monthly_invoices
from models import DocumentTemplate, GeneratedDocument, Lead, Project


def _today_utc():
    return datetime.now(timezone.utc).date()


def _today_iso():
    return _today_utc().isoformat()


@pytest.fixture()
def retainer_setup(db_session):
    """Lead + project retainer aktif yang invoice-nya jatuh tempo HARI INI."""
    lead = Lead(
        business_name="Klien Retainer Uji",
        phone_number="081200000001",
        status="Closed/Client",
    )
    db_session.add(lead)
    db_session.commit()

    project = Project(
        name="SEO Retainer Uji",
        type="RETAINER",
        status="ACTIVE",
        nominal=1_500_000,
        lead_id=lead.id,
        monthly_invoice_enabled=True,
        next_invoice_date=_today_iso(),
    )
    db_session.add(project)
    db_session.commit()

    tmpl = DocumentTemplate(
        name="Invoice Uji",
        type="invoice",
        html_template="<html><body>Invoice {{klien}} {{nomor_invoice}}</body></html>",
        variables="[]",
        is_active=True,
    )
    db_session.add(tmpl)
    db_session.commit()
    return project


def _invoices_for(db, project):
    return (
        db.query(GeneratedDocument)
        .filter(
            GeneratedDocument.target_type == "project",
            GeneratedDocument.target_id == project.id,
        )
        .order_by(GeneratedDocument.generated_at)
        .all()
    )


class TestGenerateDueMonthlyInvoicesIdempotent:
    def test_two_back_to_back_runs_create_exactly_one_invoice(self, db_session, retainer_setup):
        """Run 2x berturut (verifikasi manual PLAN-FIX-P0) -> 1 invoice, bukan 2."""
        project = retainer_setup

        first = generate_due_monthly_invoices(db_session, actor="test")
        assert len(first) == 1

        docs = _invoices_for(db_session, project)
        assert len(docs) == 1
        assert docs[0].template_name == f"Invoice Bulanan {_today_iso()[:7]}"
        assert (docs[0].status or "").lower() == "draft"

        # next_invoice_date maju +30 hari -> run kedua skip karena belum due.
        nxt = datetime.fromisoformat(project.next_invoice_date[:10]).date()
        assert nxt > _today_utc()

        second = generate_due_monthly_invoices(db_session, actor="test")
        assert len(second) == 0
        assert len(_invoices_for(db_session, project)) == 1  # TIDAK dobel

    def test_crash_recovery_same_period_does_not_duplicate(self, db_session, retainer_setup):
        """Defense-in-depth: invoice periode sudah ada TAPI next_invoice_date
        belum sempat maju (simulasi crash/retry antara generate & commit tanggal).
        Guard periode harus menahan duplikat dan tetap memajukan tanggal."""
        project = retainer_setup
        generate_due_monthly_invoices(db_session, actor="test")
        assert len(_invoices_for(db_session, project)) == 1

        # "Crash": tanggal balik ke due hari ini padahal invoice periode ini ada.
        project.next_invoice_date = _today_iso()
        db_session.commit()

        again = generate_due_monthly_invoices(db_session, actor="test")
        assert len(again) == 0
        assert len(_invoices_for(db_session, project)) == 1

        # Tanggal tetap dimajukan supaya periode berikutnya jalan normal.
        nxt = datetime.fromisoformat(project.next_invoice_date[:10]).date()
        assert nxt > _today_utc()

    def test_missing_template_creates_no_invoice_but_advances_date(self, db_session, retainer_setup):
        """Template hilang -> 0 invoice, tidak crash, tanggal tetap maju
        (biar tidak retry periode yang sama selamanya). CATATAN: skip ini masih
        diam-diam (tanpa notif) — gap terpisah, jangan diperbaiki di test ini."""
        project = retainer_setup
        db_session.query(DocumentTemplate).filter(DocumentTemplate.type == "invoice").delete()
        db_session.commit()

        out = generate_due_monthly_invoices(db_session, actor="test")
        assert len(out) == 0
        assert len(_invoices_for(db_session, project)) == 0

        nxt = datetime.fromisoformat(project.next_invoice_date[:10]).date()
        assert nxt > _today_utc()

    def test_new_period_generates_next_invoice(self, db_session, retainer_setup):
        """Guard tidak boleh mengunci selamanya: periode bulan depan (waktu
        dimajukan 31 hari) harus menghasilkan invoice BARU dengan tag periode baru."""
        from app.services import sales_workflow_service as sws

        project = retainer_setup
        generate_due_monthly_invoices(db_session, actor="test")
        assert len(_invoices_for(db_session, project)) == 1

        real_datetime = sws.datetime

        class _ShiftedDatetime(real_datetime):
            @classmethod
            def now(cls, tz=None):
                base = real_datetime.now(tz)
                return base + timedelta(days=31)

        project.next_invoice_date = (_today_utc() + timedelta(days=31)).isoformat()
        db_session.commit()

        with pytest.MonkeyPatch.context() as mp:
            mp.setattr(sws, "datetime", _ShiftedDatetime)
            out = generate_due_monthly_invoices(db_session, actor="test")

        assert len(out) == 1
        docs = _invoices_for(db_session, project)
        assert len(docs) == 2
        periods = {d.template_name for d in docs}
        shifted_month = (_today_utc() + timedelta(days=31)).strftime("%Y-%m")
        assert f"Invoice Bulanan {shifted_month}" in periods
