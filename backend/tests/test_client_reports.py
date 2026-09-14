import os
import json

from models import (
    Board,
    BoardColumn,
    Lead,
    Project,
    ReportSnapshot,
    SystemSettings,
    User,
    WorkspaceCell,
    WorkspaceColumn,
    WorkspaceRow,
    WorkspaceSheet,
)


def _seed_project_workspace(db_session):
    user = User(name="Admin", email="admin@example.com", hashed_password="x", role="admin")
    db_session.add(user)
    lead = Lead(
        business_name="Klinik Contoh",
        phone_number="081234567890",
        product_interest="SEO",
        website_url="https://example.com",
    )
    db_session.add(lead)
    db_session.flush()
    project = Project(
        id="report-project-1",
        lead_id=lead.id,
        name="SEO Klinik Contoh",
        type="RETAINER",
        status="ACTIVE",
        nominal=2500000,
        service_type="seo_gmaps",
        contract_months=3,
    )
    db_session.add(project)
    board = Board(id="report-board-1", project_id=project.id)
    db_session.add(board)
    column = BoardColumn(id="report-board-col-1", board_id=board.id, name="Done", position=0)
    db_session.add(column)
    sheet = WorkspaceSheet(
        id="report-sheet-1",
        project_id=project.id,
        sheet_index=0,
        sheet_label="Bulan 1",
        service_type="seo_gmaps",
        month_number=1,
    )
    db_session.add(sheet)
    task_col = WorkspaceColumn(id="report-col-task", sheet_id=sheet.id, column_key="task_name", column_label="Task", column_type="text", column_order=0)
    status_col = WorkspaceColumn(id="report-col-status", sheet_id=sheet.id, column_key="status", column_label="Status", column_type="select", column_order=1)
    done_col = WorkspaceColumn(id="report-col-done", sheet_id=sheet.id, column_key="done", column_label="Done", column_type="checkbox", column_order=2)
    proof_col = WorkspaceColumn(id="report-col-proof", sheet_id=sheet.id, column_key="bukti_link", column_label="Bukti", column_type="url", column_order=3)
    db_session.add_all([task_col, status_col, done_col, proof_col])
    row = WorkspaceRow(id="report-row-1", sheet_id=sheet.id, row_order=0, is_template=False)
    db_session.add(row)
    db_session.add_all([
        WorkspaceCell(id="report-cell-task", row_id=row.id, column_id=task_col.id, value_text="Publish artikel layanan"),
        WorkspaceCell(id="report-cell-status", row_id=row.id, column_id=status_col.id, value_text="Done"),
        WorkspaceCell(id="report-cell-done", row_id=row.id, column_id=done_col.id, value_bool=True),
        WorkspaceCell(id="report-cell-proof", row_id=row.id, column_id=proof_col.id, value_text="https://example.com/artikel"),
    ])
    db_session.commit()
    return project


def test_create_report_snapshot_generates_pdf_public_link_and_archive(db_session, monkeypatch):
    from app.services import client_report_service as svc
    from models import Document, GeneratedDocument

    project = _seed_project_workspace(db_session)
    monkeypatch.setattr(svc, "_fetch_pagespeed", lambda url: {"status": "ok", "url": url, "performance_score": 88})

    snapshot = svc.create_report_snapshot(
        db_session,
        target_type="project",
        target_id=project.id,
        report_type="monthly",
        month_number=1,
        period_start=None,
        period_end=None,
        manual_metrics={"gsc_clicks": 120, "gsc_clicks_previous": 80, "gsc_impressions": 4000, "gsc_impressions_previous": 3000},
        evidence={},
        narrative={"highlights": ["Artikel layanan sudah publish"], "next_steps": ["Optimasi internal link"]},
        run_pagespeed=True,
        public_enabled=True,
        actor="Admin",
    )

    assert snapshot.public_slug
    assert snapshot.generated_document_id
    assert db_session.query(ReportSnapshot).count() == 1
    generated = db_session.query(GeneratedDocument).filter(GeneratedDocument.id == snapshot.generated_document_id).first()
    assert generated is not None
    assert generated.template_name.startswith("Laporan Klien")
    assert os.path.exists(os.path.join(svc.DOCUMENTS_DIR, os.path.basename(generated.file_url)))
    archived = db_session.query(Document).filter(Document.source_type == "generated_document", Document.source_id == generated.id).first()
    assert archived is not None


def test_monthly_report_comparison_and_targets_work_for_non_seo_service(db_session, monkeypatch):
    from app.services import client_report_service as svc

    project = _seed_project_workspace(db_session)
    project.service_type = "sosmed"
    db_session.commit()

    payload = svc.build_report_payload(
        db_session,
        target_type="project",
        target_id=project.id,
        report_type="monthly",
        month_number=1,
        period_start=None,
        period_end=None,
        manual_metrics={
            "posts": 12,
            "posts_previous": 8,
            "posts_target_next_month": 16,
            "sosmed_comparison_notes": "Reach naik setelah format konten edukasi dipakai.",
            "sosmed_next_month_target_notes": "Target naik dengan cadence 4 post per minggu.",
        },
        evidence={},
        narrative={},
        run_pagespeed=False,
    )

    comparisons = payload["metrics"]["comparisons"]
    post_comparison = next(item for item in comparisons["metrics"] if item["key"] == "posts")
    post_target = next(item for item in payload["metrics"]["next_month_targets"]["metrics"] if item["key"] == "posts")

    assert comparisons["reference_label"] == "bulan lalu"
    assert comparisons["notes"] == "Reach naik setelah format konten edukasi dipakai."
    assert post_comparison["delta"]["previous"] == 8
    assert post_comparison["delta"]["current"] == 12
    assert post_comparison["delta"]["delta"] == 4
    assert post_target["value"] == 16
    assert payload["metrics"]["next_month_targets"]["notes"] == "Target naik dengan cadence 4 post per minggu."


def test_completion_seo_report_compares_against_initial_project_data(db_session, monkeypatch):
    from app.services import client_report_service as svc

    project = _seed_project_workspace(db_session)

    payload = svc.build_report_payload(
        db_session,
        target_type="project",
        target_id=project.id,
        report_type="completion",
        month_number=None,
        period_start=None,
        period_end=None,
        manual_metrics={
            "gsc_clicks": 220,
            "gsc_clicks_baseline": 90,
            "gsc_average_position": 8.5,
            "gsc_average_position_baseline": 21.0,
            "seo_gmaps_comparison_notes": "Akhir proyek membaik dibanding data pertama.",
        },
        evidence={},
        narrative={},
        run_pagespeed=False,
    )

    comparisons = payload["metrics"]["comparisons"]
    click_comparison = next(item for item in comparisons["metrics"] if item["key"] == "gsc_clicks")
    position_comparison = next(item for item in comparisons["metrics"] if item["key"] == "gsc_average_position")

    assert comparisons["reference_label"] == "data awal proyek"
    assert comparisons["notes"] == "Akhir proyek membaik dibanding data pertama."
    assert click_comparison["delta"]["previous"] == 90
    assert click_comparison["delta"]["current"] == 220
    assert position_comparison["lower_is_better"] is True
    assert position_comparison["delta"]["delta"] == -12.5
    assert payload["metrics"]["next_month_targets"]["metrics"] == []


def test_public_report_tracks_open_duration_and_download(client, db_session, monkeypatch):
    from app.services import client_report_service as svc

    project = _seed_project_workspace(db_session)
    monkeypatch.setattr(svc, "_fetch_pagespeed", lambda url: {"status": "ok", "url": url, "performance_score": 91})

    snapshot = svc.create_report_snapshot(
        db_session,
        target_type="project",
        target_id=project.id,
        report_type="monthly",
        month_number=1,
        period_start=None,
        period_end=None,
        manual_metrics={"gsc_clicks": 55, "gsc_clicks_previous": 40},
        evidence={},
        narrative={},
        run_pagespeed=True,
        public_enabled=True,
        actor="Admin",
    )

    response = client.get(f"/api/reports/public/{snapshot.public_slug}")
    assert response.status_code == 200
    body = response.json()
    assert body["open_count"] == 1
    assert body["public_url"] == f"https://test.example.com/client-report/{snapshot.public_slug}"

    duration_response = client.post(f"/api/reports/public/{snapshot.public_slug}/duration", json={"duration_seconds": 42})
    assert duration_response.status_code == 200
    assert duration_response.json()["max_duration_seconds"] == 42

    download_response = client.get(f"/api/reports/public/{snapshot.public_slug}/download")
    assert download_response.status_code == 200
    assert download_response.headers["content-type"].startswith("application/pdf")


def test_comparison_group_period_dates_compose_labels_and_echo(db_session):
    """Structured before/after date ranges auto-compose column labels and are
    echoed back so the PDF/public renderer can display the period."""
    from app.services import client_report_service as svc

    groups = svc._derive_comparison_groups({
        "comparison_groups": [
            {
                "title": "Trafik SEO",
                "before_start": "2026-05-01",
                "before_end": "2026-05-31",
                "after_start": "2026-06-01",
                "after_end": "2026-06-30",
                "rows": [{"label": "Clicks", "previous": 80, "current": 120}],
            }
        ]
    })

    assert len(groups) == 1
    group = groups[0]
    # Labels auto-composed from the date ranges (no explicit label supplied)
    assert group["reference_label"] == "2026-05-01 s/d 2026-05-31"
    assert group["current_label"] == "2026-06-01 s/d 2026-06-30"
    assert group["before_period"] == "2026-05-01 s/d 2026-05-31"
    assert group["after_period"] == "2026-06-01 s/d 2026-06-30"
    assert group["before_start"] == "2026-05-01"
    assert group["after_end"] == "2026-06-30"
    # Delta still computed correctly
    assert group["rows"][0]["delta"]["delta"] == 40


def test_comparison_group_explicit_label_wins_over_dates(db_session):
    """An explicit label always overrides the auto-composed date range."""
    from app.services import client_report_service as svc

    groups = svc._derive_comparison_groups({
        "comparison_groups": [
            {
                "reference_label": "Sebelum kontrak",
                "before_start": "2026-05-01",
                "before_end": "2026-05-31",
                "rows": [{"label": "Followers", "previous": 100, "current": 250}],
            }
        ]
    })

    group = groups[0]
    assert group["reference_label"] == "Sebelum kontrak"
    # Period still echoed for reference even when label is explicit
    assert group["before_period"] == "2026-05-01 s/d 2026-05-31"
    # current_label falls back to default (no after dates, no explicit label)
    assert group["current_label"] == "Sekarang"


def _seed_project_generic_sheet(db_session):
    """Project whose workspace has ONLY a generic sheet (month_number=NULL),
    like the real MLS/MHK boards. Reproduces the broken 'kerjaan -> laporan'
    chain: report asks for month N but no month-numbered sheet exists."""
    lead = Lead(business_name="Toko Generik", phone_number="0811", product_interest="SEO")
    db_session.add(lead)
    db_session.flush()
    project = Project(
        id="generic-project-1",
        lead_id=lead.id,
        name="SEO Toko Generik",
        type="RETAINER",
        status="ACTIVE",
        nominal=0,
        service_type="seo_gmaps",
        contract_months=6,
    )
    db_session.add(project)
    sheet = WorkspaceSheet(
        id="generic-sheet-1",
        project_id=project.id,
        sheet_index=0,
        sheet_label="Task Operasional",
        service_type="seo_gmaps",
        month_number=None,  # THE bug trigger: no month number
    )
    db_session.add(sheet)
    task_col = WorkspaceColumn(id="g-col-task", sheet_id=sheet.id, column_key="task_name", column_label="Task", column_type="text", column_order=0)
    done_col = WorkspaceColumn(id="g-col-done", sheet_id=sheet.id, column_key="done", column_label="Done", column_type="checkbox", column_order=1)
    db_session.add_all([task_col, done_col])
    row = WorkspaceRow(id="g-row-1", sheet_id=sheet.id, row_order=0, is_template=False)
    db_session.add(row)
    db_session.add_all([
        WorkspaceCell(id="g-cell-task", row_id=row.id, column_id=task_col.id, value_text="Riset keyword"),
        WorkspaceCell(id="g-cell-done", row_id=row.id, column_id=done_col.id, value_bool=True),
    ])
    db_session.commit()
    return project


def test_report_falls_back_to_generic_sheet_when_no_month_sheet(db_session):
    """REGRESSION: workspace with only a generic (month_number=NULL) sheet must
    still surface its tasks in a monthly report instead of returning 0.
    This is the fix that reconnects 'kerjaan tercatat -> masuk laporan'."""
    from app.services import client_report_service as svc

    project = _seed_project_generic_sheet(db_session)
    # Ask for month 1 even though the only sheet has month_number=NULL.
    snap = svc._workspace_snapshot(db_session, project.id, month_number=1)
    summary = snap["summary"]
    assert summary["total_tasks"] == 1, "fallback should pull the generic sheet's task"
    assert summary["completed_tasks"] == 1
    assert snap["tasks"], "tasks list must not be empty"


def test_report_no_month_still_counts_generic_sheet(db_session):
    """When no month_number is requested, all sheets (incl. generic) are counted."""
    from app.services import client_report_service as svc

    project = _seed_project_generic_sheet(db_session)
    snap = svc._workspace_snapshot(db_session, project.id, month_number=None)
    assert snap["summary"]["total_tasks"] == 1


def test_report_empty_month_sheet_falls_back_to_generic(db_session):
    """FIX#3: month-sheet ADA tapi KOSONG (0 task rows) sementara kerjaan nyata
    ada di sheet generik. Report harus fallback ke generik, BUKAN kasih 0 tugas.
    Ini penyebab report MLS 'total_tasks=0' di prod (month-sheet auto-dibuat
    tapi kosong, kerjaan tercatat di sheet generik)."""
    from app.services import client_report_service as svc

    project = _seed_project_generic_sheet(db_session)  # punya generic sheet + 1 task
    # Tambah month-sheet KOSONG untuk bulan 1 (tanpa rows).
    empty_month = WorkspaceSheet(
        id="empty-month-1",
        project_id=project.id,
        sheet_index=1,
        sheet_label="Bulan 1",
        service_type="seo_gmaps",
        month_number=1,
    )
    db_session.add(empty_month)
    db_session.commit()

    snap = svc._workspace_snapshot(db_session, project.id, month_number=1)
    assert snap["summary"]["total_tasks"] == 1, "month-sheet kosong harus fallback ke generic sheet"
    assert snap["tasks"], "tasks list tidak boleh kosong"


def test_report_populated_month_sheet_uses_only_month(db_session):
    """Kalau month-sheet ADA task-nya, pakai HANYA month-sheet itu (jangan
    ikut gabung generic) supaya laporan bulanan tetap akurat per-bulan."""
    from app.services import client_report_service as svc

    project = _seed_project_workspace(db_session)  # sudah punya month-sheet=1 dgn 1 task
    # Tambah generic sheet dgn 2 task; harusnya TIDAK ikut karena month-sheet ada isinya.
    generic = WorkspaceSheet(id="extra-generic", project_id=project.id, sheet_index=5,
                             sheet_label="Operasional", service_type="seo_gmaps", month_number=None)
    db_session.add(generic)
    gcol = WorkspaceColumn(id="eg-col", sheet_id=generic.id, column_key="task_name",
                           column_label="Task", column_type="text", column_order=0)
    db_session.add(gcol)
    for i in range(2):
        r = WorkspaceRow(id=f"eg-row-{i}", sheet_id=generic.id, row_order=i, is_template=False)
        db_session.add(r)
        db_session.add(WorkspaceCell(id=f"eg-cell-{i}", row_id=r.id, column_id=gcol.id, value_text=f"X{i}"))
    db_session.commit()

    snap = svc._workspace_snapshot(db_session, project.id, month_number=1)
    assert snap["summary"]["total_tasks"] == 1, "month-sheet berisi -> hanya hitung month-sheet"



def test_regenerate_same_period_updates_in_place_no_duplicate(db_session, monkeypatch):
    """DEDUP (prinsip Kevin): generate report untuk project+periode yang SAMA
    dua kali harus tetap 1 snapshot (ke-UPDATE in-place), BUKAN 2 row baru.
    Fondasi report->invoice: 1 report/periode = 1 invoice."""
    from app.services import client_report_service as svc
    from models import GeneratedDocument

    project = _seed_project_workspace(db_session)
    monkeypatch.setattr(svc, "_fetch_pagespeed", lambda url: {"status": "ok", "url": url, "performance_score": 88})

    kwargs = dict(
        target_type="project",
        target_id=project.id,
        report_type="monthly",
        month_number=1,
        period_start=None,
        period_end=None,
        evidence={},
        narrative={},
        run_pagespeed=False,
        public_enabled=True,
        actor="Admin",
    )

    snap1 = svc.create_report_snapshot(db_session, manual_metrics={"gsc_clicks": 100}, **kwargs)
    first_id = snap1.id
    first_slug = snap1.public_slug
    first_doc_id = snap1.generated_document_id
    first_pdf = os.path.join(svc.DOCUMENTS_DIR, os.path.basename(
        db_session.query(GeneratedDocument).get(first_doc_id).file_url))

    # Generate ULANG periode yang sama dengan angka berbeda.
    snap2 = svc.create_report_snapshot(db_session, manual_metrics={"gsc_clicks": 250}, **kwargs)

    # 1) Tetap 1 snapshot (di-update, bukan numpuk)
    assert db_session.query(ReportSnapshot).count() == 1, "harus tetap 1 snapshot setelah regenerate"
    # 2) Snapshot id sama (update in-place)
    assert snap2.id == first_id
    # 3) Public slug stabil (link publik ga berubah)
    assert snap2.public_slug == first_slug
    # 4) Konten ke-update (angka baru masuk metrics)
    import json as _json
    metrics = _json.loads(snap2.metrics_json)
    assert metrics["manual"]["gsc_clicks"] == 250
    # 5) Dokumen lama dibersihkan: hanya 1 GeneratedDocument tersisa
    assert db_session.query(GeneratedDocument).count() == 1, "dokumen lama harus dihapus (anti-duplikat)"
    # 6) PDF lama dihapus dari disk, PDF baru ada
    assert not os.path.exists(first_pdf), "PDF lama harus dihapus dari disk"
    new_doc = db_session.query(GeneratedDocument).get(snap2.generated_document_id)
    assert os.path.exists(os.path.join(svc.DOCUMENTS_DIR, os.path.basename(new_doc.file_url)))


def test_different_period_creates_separate_snapshot(db_session, monkeypatch):
    """Periode BEDA (month 1 vs month 2) tetap bikin snapshot terpisah —
    dedup hanya untuk periode yang sama, bukan menggabung semua."""
    from app.services import client_report_service as svc

    project = _seed_project_workspace(db_session)
    monkeypatch.setattr(svc, "_fetch_pagespeed", lambda url: {"status": "ok"})

    base = dict(
        target_type="project", target_id=project.id, report_type="monthly",
        period_start=None, period_end=None, manual_metrics={}, evidence={},
        narrative={}, run_pagespeed=False, public_enabled=True, actor="Admin",
    )
    svc.create_report_snapshot(db_session, month_number=1, **base)
    svc.create_report_snapshot(db_session, month_number=2, **base)
    assert db_session.query(ReportSnapshot).count() == 2, "periode beda = snapshot beda"


# ─────────────────────────────────────────────────────────────────────────────
# REPORT FINAL → DRAFT INVOICE (plan report->invoice)
# Yang dites di sini = LOGIKA finalize (idempotent + anti-duplikat mutlak),
# BUKAN render PDF invoice. `_generate_workflow_document` di-patch supaya
# nge-insert GeneratedDocument dummy (tanpa template/PDF) — kita cuma peduli
# apakah finalize bikin invoice ganda atau engga.
# ─────────────────────────────────────────────────────────────────────────────

def _patch_invoice_generator(monkeypatch, svc):
    """Patch _generate_workflow_document -> insert GeneratedDocument dummy.

    Balikin counter dict biar test bisa hitung berapa kali generator dipanggil
    (= berapa invoice fisik yang BENAR-BENAR dibuat). Anti-duplikat sejati =
    generator dipanggil TEPAT 1x walau finalize dipanggil berkali-kali.
    """
    from models import GeneratedDocument
    import uuid as _uuid

    calls = {"n": 0}

    def _fake_gen(db, template_type, target_type, target_id, variables, actor,
                  status, payment_status, archive_title, client_name,
                  project_name, doc_type_label):
        calls["n"] += 1
        doc = GeneratedDocument(
            id=str(_uuid.uuid4()),
            template_id=None,
            template_name=archive_title,
            target_type=target_type,
            target_id=target_id,
            variables_used="{}",
            file_url="/x/dummy-invoice.pdf",
            display_filename="dummy-invoice.pdf",
            status=status,
            payment_status=payment_status,
            generated_by=actor,
        )
        db.add(doc)
        db.flush()
        return doc, None

    # Patch di modul asalnya (sales_workflow_service) karena finalize import lokal.
    from app.services import sales_workflow_service as sws
    monkeypatch.setattr(sws, "_generate_workflow_document", _fake_gen)
    return calls


def _make_final_report(db_session, svc, monkeypatch, month_number=1):
    monkeypatch.setattr(svc, "_fetch_pagespeed", lambda url: {"status": "ok"})
    project = _seed_project_workspace(db_session)
    snap = svc.create_report_snapshot(
        db_session, target_type="project", target_id=project.id,
        report_type="monthly", month_number=month_number, period_start=None,
        period_end=None, manual_metrics={}, evidence={}, narrative={},
        run_pagespeed=False, public_enabled=True, actor="Admin",
    )
    return project, snap


def test_finalize_report_creates_draft_invoice_once(db_session, monkeypatch):
    """Skenario 1: finalize sekali → 1 draft invoice UNPAID kebikin,
    report jadi status final + ke-link ke invoice."""
    from app.services import client_report_service as svc
    from app.constants import DocumentStatus, PaymentStatus

    calls = _patch_invoice_generator(monkeypatch, svc)
    project, snap = _make_final_report(db_session, svc, monkeypatch)

    result = svc.finalize_report_and_generate_invoice(db_session, snap.id, "Admin")

    assert result["invoice_created"] is True
    assert result["invoice_id"], "harus ada invoice_id"
    assert calls["n"] == 1, "generator invoice dipanggil tepat 1x"
    db_session.refresh(snap)
    assert (snap.status or "").lower() == "final"
    assert snap.finalized_by == "Admin"
    assert snap.generated_invoice_id == result["invoice_id"]
    from models import GeneratedDocument
    inv = db_session.query(GeneratedDocument).get(result["invoice_id"])
    assert inv.status == DocumentStatus.DRAFT
    assert inv.payment_status == PaymentStatus.UNPAID


def test_finalize_twice_no_duplicate_invoice(db_session, monkeypatch):
    """Skenario 2: finalize 2x report yang SAMA → invoice TIDAK ganda,
    return existing (idempotent), generator TIDAK dipanggil lagi."""
    from app.services import client_report_service as svc
    from models import GeneratedDocument

    calls = _patch_invoice_generator(monkeypatch, svc)
    project, snap = _make_final_report(db_session, svc, monkeypatch)

    r1 = svc.finalize_report_and_generate_invoice(db_session, snap.id, "Admin")
    r2 = svc.finalize_report_and_generate_invoice(db_session, snap.id, "Admin")

    assert r1["invoice_id"] == r2["invoice_id"], "invoice sama, bukan baru"
    assert r2["already_final"] is True
    assert r2["invoice_created"] is False
    assert calls["n"] == 1, "generator TETAP 1x walau finalize 2x"
    inv_count = db_session.query(GeneratedDocument).filter(
        GeneratedDocument.template_name.like("Invoice Laporan%")
    ).count()
    assert inv_count == 1, "cuma 1 invoice fisik"


def test_two_reports_same_period_share_one_invoice(db_session, monkeypatch):
    """Skenario 3: 2 report periode SAMA untuk project sama → tidak 2 invoice.
    Report kedua nge-link ke invoice yang sudah ada (anti-duplikat per periode).

    Catatan: dedup snapshot (#4) bikin regenerate periode sama jadi 1 snapshot,
    tapi test ini mempertahankan 2 snapshot manual (project + periode sama tapi
    beda id paksa) untuk mengetes guard anti-duplikat DI FINALIZE, bukan cuma
    di snapshot. Kita simulasikan dua report objek berbeda periode sama."""
    from app.services import client_report_service as svc
    from models import GeneratedDocument, ReportSnapshot

    calls = _patch_invoice_generator(monkeypatch, svc)
    monkeypatch.setattr(svc, "_fetch_pagespeed", lambda url: {"status": "ok"})
    project = _seed_project_workspace(db_session)

    # Report A periode M01
    snapA = svc.create_report_snapshot(
        db_session, target_type="project", target_id=project.id,
        report_type="monthly", month_number=1, period_start=None, period_end=None,
        manual_metrics={}, evidence={}, narrative={}, run_pagespeed=False,
        public_enabled=True, actor="Admin",
    )
    rA = svc.finalize_report_and_generate_invoice(db_session, snapA.id, "Admin")

    # Report B: paksa snapshot kedua periode sama (bypass dedup dgn insert manual)
    import uuid as _uuid
    snapB = ReportSnapshot(
        id=str(_uuid.uuid4()), project_id=project.id, report_type="monthly",
        month_number=1, title="Laporan Manual Kedua M01", status="Draft",
        public_slug=str(_uuid.uuid4())[:8], metrics_json="{}",
        created_at=snapA.created_at,
    )
    db_session.add(snapB)
    db_session.flush()
    rB = svc.finalize_report_and_generate_invoice(db_session, snapB.id, "Admin")

    assert rA["invoice_id"] == rB["invoice_id"], "periode sama = invoice sama"
    assert rB["reused_existing_invoice"] if "reused_existing_invoice" in rB else rB["reused"], "report B pakai invoice existing"
    assert calls["n"] == 1, "cuma 1 invoice fisik untuk periode sama"
    inv_count = db_session.query(GeneratedDocument).filter(
        GeneratedDocument.template_name.like("Invoice Laporan%")
    ).count()
    assert inv_count == 1


def test_generate_report_draft_does_not_trigger_invoice(db_session, monkeypatch):
    """Skenario 4: generate report berkali-kali (draft) TIDAK bikin invoice.
    Cuma finalize yang trigger. Draft = 0 invoice."""
    from app.services import client_report_service as svc
    from models import GeneratedDocument

    calls = _patch_invoice_generator(monkeypatch, svc)
    monkeypatch.setattr(svc, "_fetch_pagespeed", lambda url: {"status": "ok"})
    project = _seed_project_workspace(db_session)

    base = dict(
        target_type="project", target_id=project.id, report_type="monthly",
        month_number=1, period_start=None, period_end=None, manual_metrics={},
        evidence={}, narrative={}, run_pagespeed=False, public_enabled=True, actor="Admin",
    )
    svc.create_report_snapshot(db_session, **base)
    svc.create_report_snapshot(db_session, **base)  # regenerate draft
    svc.create_report_snapshot(db_session, **base)  # sekali lagi

    assert calls["n"] == 0, "generate draft TIDAK boleh trigger invoice"
    # invoice generator patch hitung 0; ga ada GeneratedDocument invoice dari finalize
    invoice_docs = db_session.query(GeneratedDocument).filter(
        GeneratedDocument.template_name.like("Invoice Laporan%")
    ).count()
    assert invoice_docs == 0


# ─────────────────────────────────────────────────────────────────────────────
# A1 — FIX MAPS: MLS (seo_gmaps) tanpa data GBP tidak boleh sebut Google Maps
# ─────────────────────────────────────────────────────────────────────────────
def test_a1_narrative_mls_without_gbp_does_not_mention_google_maps(db_session, monkeypatch):
    from app.services import client_report_service as svc

    project = _seed_project_workspace(db_session)  # service_type=seo_gmaps
    monkeypatch.setattr(svc, "_fetch_pagespeed", lambda url: {"status": "skipped"})

    payload = svc.build_report_payload(
        db_session,
        target_type="project",
        target_id=project.id,
        report_type="monthly",
        month_number=1,
        period_start=None,
        period_end=None,
        # HANYA GSC — TIDAK ADA data GBP/Maps
        manual_metrics={"gsc_clicks": 120, "gsc_impressions": 4000},
        evidence={},
        narrative={},
        run_pagespeed=False,
    )
    summary = payload["narrative"]["executive_summary"]
    assert "Google Maps" not in summary, summary
    assert "eksekusi SEO." in summary or "eksekusi SEO " in summary, summary


def test_a1_narrative_mls_with_gbp_mentions_google_maps(db_session, monkeypatch):
    from app.services import client_report_service as svc

    project = _seed_project_workspace(db_session)
    monkeypatch.setattr(svc, "_fetch_pagespeed", lambda url: {"status": "skipped"})

    payload = svc.build_report_payload(
        db_session,
        target_type="project",
        target_id=project.id,
        report_type="monthly",
        month_number=1,
        period_start=None,
        period_end=None,
        # ADA data GBP -> narasi tetap sebut Google Maps
        manual_metrics={"gsc_clicks": 120, "gbp_views": 500, "gbp_calls": 30},
        evidence={},
        narrative={},
        run_pagespeed=False,
    )
    summary = payload["narrative"]["executive_summary"]
    assert "SEO & Google Maps" in summary, summary


def _pdf_text(pdf_bytes: bytes) -> str:
    """Ekstrak teks dari PDF bytes (pdftotext kalau ada, else pypdf)."""
    import subprocess, tempfile, shutil
    if shutil.which("pdftotext"):
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            f.write(pdf_bytes)
            path = f.name
        out = subprocess.run(["pdftotext", "-layout", path, "-"],
                             capture_output=True, text=True)
        return out.stdout
    try:
        import io
        from pypdf import PdfReader
        reader = PdfReader(io.BytesIO(pdf_bytes))
        return "\n".join((p.extract_text() or "") for p in reader.pages)
    except Exception:
        return ""


def test_a1_pdf_heading_seo_only_when_no_gbp(db_session):
    """Renderer: heading 'Performa SEO' (BUKAN '& Google Maps') saat GBP kosong."""
    from app.services.pdf_renderer import render_report_pdf_reportlab

    payload = {
        "title": "Laporan Bulanan SEO - MLS",
        "report_type": "monthly",
        "service_type": "seo_gmaps",
        "client": {"name": "MLS"},
        "project": {"name": "SEO MLS", "service_type": "seo_gmaps"},
        "period": {"label": "Bulan ke-3"},
        "metrics": {
            "service": {
                "gsc": {"clicks": 120, "impressions": 4000, "ctr": "3%", "average_position": "8.5"},
                "google_business": {},  # KOSONG
            },
        },
        "narrative": {},
        "evidence": {},
    }
    pdf = render_report_pdf_reportlab(payload, {})
    text = _pdf_text(pdf)
    assert "Performa SEO" in text, text[:400]
    assert "Google Maps" not in text, text[:400]


def test_a1_pdf_heading_includes_maps_when_gbp_present(db_session):
    from app.services.pdf_renderer import render_report_pdf_reportlab

    payload = {
        "title": "Laporan Bulanan SEO - Klien GBP",
        "report_type": "monthly",
        "service_type": "seo_gmaps",
        "client": {"name": "Klien GBP"},
        "project": {"name": "SEO GBP", "service_type": "seo_gmaps"},
        "period": {"label": "Bulan ke-3"},
        "metrics": {
            "service": {
                "gsc": {"clicks": 120, "impressions": 4000},
                "google_business": {"views": 500, "calls": 30},  # ADA data
            },
        },
        "narrative": {},
        "evidence": {},
    }
    pdf = render_report_pdf_reportlab(payload, {})
    text = _pdf_text(pdf)
    assert "Performa SEO & Google Maps" in text, text[:400]


# ─────────────────────────────────────────────────────────────────────────────
# A2 — REKOMENDASI NEXT MONTH (AI, editable, anti-halu, fallback aman)
# ─────────────────────────────────────────────────────────────────────────────
def test_a2_ai_fills_next_steps_when_empty(db_session, monkeypatch):
    """next_steps KOSONG + generate_ai_recommendations -> AI isi (based-on-data)."""
    from app.services import client_report_service as svc

    project = _seed_project_workspace(db_session)
    monkeypatch.setattr(svc, "_fetch_pagespeed", lambda url: {"status": "skipped"})

    captured = {}

    def _fake_ai(prompt, config, _httpx):
        captured["prompt"] = prompt
        return "- Tingkatkan clicks lewat optimasi judul\n- Publish 2 artikel layanan\n- Perbaiki internal link"

    # patch di dependencies (dipanggil via import lokal di _generate_next_steps_ai)
    import app.core.dependencies as deps
    monkeypatch.setattr(deps, "_call_ai_sync", _fake_ai)

    payload = svc.build_report_payload(
        db_session,
        target_type="project",
        target_id=project.id,
        report_type="monthly",
        month_number=1,
        period_start=None,
        period_end=None,
        manual_metrics={"gsc_clicks": 120, "gsc_clicks_previous": 80, "gsc_impressions": 4000},
        evidence={},
        narrative={},
        run_pagespeed=False,
        generate_ai_recommendations=True,
    )
    steps = payload["narrative"]["next_steps"]
    assert len(steps) == 3, steps
    assert "Publish 2 artikel layanan" in steps
    # Anti-halu: prompt HARUS memuat data REAL (angka GSC + task board asli)
    assert "120" in captured["prompt"]
    assert "Publish artikel layanan" in captured["prompt"]  # task board real
    assert "JANGAN mengarang" in captured["prompt"]


def test_a2_manual_next_steps_not_overwritten_by_ai(db_session, monkeypatch):
    """EDITABLE: next_steps diisi MANUAL -> AI JANGAN nimpa (dan JANGAN dipanggil)."""
    from app.services import client_report_service as svc

    project = _seed_project_workspace(db_session)
    monkeypatch.setattr(svc, "_fetch_pagespeed", lambda url: {"status": "skipped"})

    ai_called = {"n": 0}

    def _fake_ai(prompt, config, _httpx):
        ai_called["n"] += 1
        return "- rekomendasi AI"

    import app.core.dependencies as deps
    monkeypatch.setattr(deps, "_call_ai_sync", _fake_ai)

    payload = svc.build_report_payload(
        db_session,
        target_type="project",
        target_id=project.id,
        report_type="monthly",
        month_number=1,
        period_start=None,
        period_end=None,
        manual_metrics={"gsc_clicks": 120},
        evidence={},
        narrative={"next_steps": ["Rencana manual Kevin"]},
        run_pagespeed=False,
        generate_ai_recommendations=True,
    )
    assert payload["narrative"]["next_steps"] == ["Rencana manual Kevin"]
    assert ai_called["n"] == 0, "AI TIDAK boleh dipanggil kalau next_steps manual"


def test_a2_ai_failure_falls_back_gracefully(db_session, monkeypatch):
    """JARING PENGAMAN: AI gagal/timeout -> next_steps kosong, report TETAP jadi."""
    from app.services import client_report_service as svc

    project = _seed_project_workspace(db_session)
    monkeypatch.setattr(svc, "_fetch_pagespeed", lambda url: {"status": "skipped"})

    def _boom(prompt, config, _httpx):
        raise RuntimeError("AI timeout / provider down")

    import app.core.dependencies as deps
    monkeypatch.setattr(deps, "_call_ai_sync", _boom)

    payload = svc.build_report_payload(
        db_session,
        target_type="project",
        target_id=project.id,
        report_type="monthly",
        month_number=1,
        period_start=None,
        period_end=None,
        manual_metrics={"gsc_clicks": 120},
        evidence={},
        narrative={},
        run_pagespeed=False,
        generate_ai_recommendations=True,
    )
    # Tidak error, next_steps kosong (fallback aman)
    assert payload["narrative"]["next_steps"] == []


def test_a2_draft_preview_does_not_call_ai(db_session, monkeypatch):
    """Hemat: build_report_payload tanpa flag (preview draft) TIDAK panggil AI."""
    from app.services import client_report_service as svc

    project = _seed_project_workspace(db_session)
    monkeypatch.setattr(svc, "_fetch_pagespeed", lambda url: {"status": "skipped"})

    ai_called = {"n": 0}

    def _fake_ai(prompt, config, _httpx):
        ai_called["n"] += 1
        return "- x"

    import app.core.dependencies as deps
    monkeypatch.setattr(deps, "_call_ai_sync", _fake_ai)

    svc.build_report_payload(
        db_session,
        target_type="project",
        target_id=project.id,
        report_type="monthly",
        month_number=1,
        period_start=None,
        period_end=None,
        manual_metrics={"gsc_clicks": 120},
        evidence={},
        narrative={},
        run_pagespeed=False,
        # generate_ai_recommendations default False
    )
    assert ai_called["n"] == 0


# ─────────────────────────────────────────────────────────────────────────────
# Draft report patching: revisions must stay in the original draft snapshot and
# must not enter finalization, email, or publication flows.
# ─────────────────────────────────────────────────────────────────────────────
def _report_admin_headers(db_session):
    from app.core.dependencies import create_token

    user = User(name="Report Admin", email="report-admin@example.com", hashed_password="x", role="admin")
    db_session.add(user)
    db_session.commit()
    return {"Authorization": f"Bearer {create_token(user.id, user.email)}"}


def _draft_report_for_patch(db_session, monkeypatch):
    from app.services import client_report_service as svc

    project = _seed_project_workspace(db_session)
    monkeypatch.setattr(svc, "render_report_pdf_reportlab", lambda payload, brand: b"%PDF-draft-patch")
    monkeypatch.setattr(svc, "_generate_next_steps_ai", lambda *args, **kwargs: [])
    return svc.create_report_snapshot(
        db_session,
        target_type="project",
        target_id=project.id,
        report_type="monthly",
        month_number=1,
        period_start=None,
        period_end=None,
        manual_metrics={"gsc_clicks": 10},
        evidence={"items": [{"label": "Bukti lama", "url": "https://example.com/old"}]},
        narrative={"executive_summary": "Ringkasan lama"},
        run_pagespeed=False,
        public_enabled=False,
        actor="Admin",
    )


def test_patch_draft_report_updates_in_place_without_finalize_or_email(client, db_session, monkeypatch):
    from app.services import client_report_service as svc
    from routers import reports as reports_router
    from models import AuditLog

    snapshot = _draft_report_for_patch(db_session, monkeypatch)
    original_id = snapshot.id
    original_document_id = snapshot.generated_document_id
    original_title = snapshot.title
    original_target = (snapshot.target_type, snapshot.target_id, snapshot.project_id, snapshot.report_type, snapshot.month_number)

    def _must_not_run(*args, **kwargs):
        raise AssertionError("draft patch must not call finalize or email")

    monkeypatch.setattr(svc, "finalize_report_and_generate_invoice", _must_not_run)
    monkeypatch.setattr(reports_router, "finalize_report_and_generate_invoice", _must_not_run)
    monkeypatch.setattr(reports_router, "send_pdf_email", _must_not_run)

    response = client.patch(
        f"/api/reports/{snapshot.id}",
        headers=_report_admin_headers(db_session),
        json={
            "reason": "Koreksi data laporan dari catatan tim",
            "metrics": {"gsc_clicks": 125},
            "evidence": {"items": [{"label": "Bukti baru", "url": "https://example.com/new"}]},
            "narrative": {"executive_summary": "Ringkasan revisi"},
        },
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["id"] == original_id
    assert body["title"] == original_title
    assert body["status"].lower() == "draft"
    assert body["public_enabled"] is False
    assert body["public_slug"] is None
    assert body["generated_invoice_id"] is None
    assert body["finalized_at"] is None
    assert body["finalized_by"] is None
    assert body["metrics"]["manual"]["gsc_clicks"] == 125
    assert body["evidence"]["items"][0]["label"] == "Bukti baru"
    assert body["narrative"]["executive_summary"] == "Ringkasan revisi"

    db_session.expire_all()
    saved = db_session.query(ReportSnapshot).filter(ReportSnapshot.id == original_id).one()
    assert db_session.query(ReportSnapshot).count() == 1
    assert saved.generated_document_id == original_document_id
    assert (saved.target_type, saved.target_id, saved.project_id, saved.report_type, saved.month_number) == original_target
    from models import GeneratedDocument
    assert db_session.query(GeneratedDocument).filter(GeneratedDocument.id == original_document_id).one().generated_by == "Admin"
    audit = db_session.query(AuditLog).filter(AuditLog.table_name == "report_snapshots", AuditLog.record_id == original_id).one()
    assert audit.action == "UPDATE"
    assert json.loads(audit.details) == {
        "reason": "Koreksi data laporan dari catatan tim",
        "changed_fields": ["metrics", "evidence", "narrative"],
    }


def test_patch_finalized_report_is_rejected(client, db_session, monkeypatch):
    snapshot = _draft_report_for_patch(db_session, monkeypatch)
    snapshot.status = "final"
    snapshot.finalized_at = "2026-09-14T00:00:00+00:00"
    snapshot.finalized_by = "Admin"
    db_session.commit()

    response = client.patch(
        f"/api/reports/{snapshot.id}",
        headers=_report_admin_headers(db_session),
        json={"reason": "Tidak boleh mengubah final", "metrics": {"gsc_clicks": 999}},
    )

    assert response.status_code == 409
    assert "draft" in response.json()["detail"].lower()
    db_session.refresh(snapshot)
    assert snapshot.status == "final"
    assert snapshot.finalized_by == "Admin"


def test_patch_draft_report_requires_nonblank_reason(client, db_session, monkeypatch):
    snapshot = _draft_report_for_patch(db_session, monkeypatch)

    response = client.patch(
        f"/api/reports/{snapshot.id}",
        headers=_report_admin_headers(db_session),
        json={"reason": "   ", "metrics": {"gsc_clicks": 125}},
    )

    assert response.status_code == 422


def test_patch_draft_report_requires_admin(client, db_session, monkeypatch):
    from app.core.dependencies import create_token

    snapshot = _draft_report_for_patch(db_session, monkeypatch)
    editor = User(name="Report Editor", email="report-editor@example.com", hashed_password="x", role="user")
    db_session.add(editor)
    db_session.commit()

    response = client.patch(
        f"/api/reports/{snapshot.id}",
        headers={"Authorization": f"Bearer {create_token(editor.id, editor.email)}"},
        json={"reason": "Tidak berwenang", "metrics": {"gsc_clicks": 125}},
    )

    assert response.status_code == 403


def test_patch_missing_report_is_not_found_and_noop_is_unprocessable(client, db_session, monkeypatch):
    headers = _report_admin_headers(db_session)
    missing = client.patch(
        "/api/reports/missing-report",
        headers=headers,
        json={"reason": "Mencoba laporan hilang", "metrics": {"gsc_clicks": 125}},
    )
    assert missing.status_code == 404

    snapshot = _draft_report_for_patch(db_session, monkeypatch)
    no_op = client.patch(
        f"/api/reports/{snapshot.id}",
        headers=headers,
        json={"reason": "Tidak ada perubahan", "metrics": {"gsc_clicks": 10}},
    )
    assert no_op.status_code == 422


def test_patch_updates_archive_url_with_revised_generated_document(client, db_session, monkeypatch):
    from models import Document, GeneratedDocument

    snapshot = _draft_report_for_patch(db_session, monkeypatch)
    document = db_session.query(GeneratedDocument).filter(GeneratedDocument.id == snapshot.generated_document_id).one()
    old_url = document.file_url
    response = client.patch(
        f"/api/reports/{snapshot.id}",
        headers=_report_admin_headers(db_session),
        json={"reason": "Koreksi metrik", "metrics": {"gsc_clicks": 125}},
    )
    assert response.status_code == 200, response.text

    db_session.expire_all()
    document = db_session.query(GeneratedDocument).filter(GeneratedDocument.id == snapshot.generated_document_id).one()
    archive = db_session.query(Document).filter(
        Document.source_type == "generated_document", Document.source_id == document.id
    ).one()
    assert document.file_url != old_url
    assert archive.url == document.file_url


def test_patch_commit_failure_keeps_old_file_and_cleans_new_file(db_session, monkeypatch):
    from app.services import client_report_service as svc
    from models import GeneratedDocument

    snapshot = _draft_report_for_patch(db_session, monkeypatch)
    document = db_session.query(GeneratedDocument).filter(GeneratedDocument.id == snapshot.generated_document_id).one()
    old_url = document.file_url
    old_path = os.path.join(svc.DOCUMENTS_DIR, os.path.basename(old_url))
    assert os.path.exists(old_path)
    filenames_before = set(os.listdir(svc.DOCUMENTS_DIR))

    original_commit = db_session.commit
    monkeypatch.setattr(db_session, "commit", lambda: (_ for _ in ()).throw(RuntimeError("forced commit failure")))
    try:
        svc.patch_draft_report_snapshot(
            db_session,
            report_id=snapshot.id,
            manual_metrics={"gsc_clicks": 125},
            evidence=None,
            narrative=None,
            reason="Memastikan rollback aman",
            actor="Report Admin",
        )
    except RuntimeError:
        pass
    else:
        raise AssertionError("commit failure must be raised")
    finally:
        monkeypatch.setattr(db_session, "commit", original_commit)

    assert os.path.exists(old_path)
    assert set(os.listdir(svc.DOCUMENTS_DIR)) == filenames_before
    db_session.rollback()
    restored = db_session.query(GeneratedDocument).filter(GeneratedDocument.id == document.id).one()
    assert restored.file_url == old_url


def test_patch_uses_persisted_snapshot_not_changed_live_workspace(client, db_session, monkeypatch):
    from models import GeneratedDocument

    snapshot = _draft_report_for_patch(db_session, monkeypatch)
    document = db_session.query(GeneratedDocument).filter(GeneratedDocument.id == snapshot.generated_document_id).one()
    before_payload = json.loads(document.variables_used)
    assert before_payload["workspace"]["tasks"][0]["task_name"] == "Publish artikel layanan"

    cell = db_session.query(WorkspaceCell).filter(WorkspaceCell.id == "report-cell-task").one()
    cell.value_text = "DATA LIVE YANG TIDAK BOLEH MASUK REVISI"
    db_session.commit()

    response = client.patch(
        f"/api/reports/{snapshot.id}",
        headers=_report_admin_headers(db_session),
        json={"reason": "Koreksi metrik saja", "metrics": {"gsc_clicks": 125}},
    )
    assert response.status_code == 200, response.text

    db_session.expire_all()
    revised = db_session.query(GeneratedDocument).filter(GeneratedDocument.id == snapshot.generated_document_id).one()
    revised_payload = json.loads(revised.variables_used)
    assert revised_payload["workspace"] == before_payload["workspace"]
    assert revised_payload["metrics"]["board"] == before_payload["metrics"]["board"]


def test_patch_merges_manual_metrics_and_ignores_workspace_evidence_input(client, db_session, monkeypatch):
    from models import GeneratedDocument

    snapshot = _draft_report_for_patch(db_session, monkeypatch)
    document = db_session.query(GeneratedDocument).filter(GeneratedDocument.id == snapshot.generated_document_id).one()
    original_evidence = json.loads(snapshot.evidence_json)

    # A report commonly has several manually-entered metrics. A one-field PATCH
    # must retain the omitted fields in both persistence locations.
    metrics = json.loads(snapshot.metrics_json)
    metrics["manual"]["gsc_impressions"] = 4000
    metrics["manual"]["gsc_impressions_previous"] = 3000
    snapshot.metrics_json = json.dumps(metrics)
    payload = json.loads(document.variables_used)
    payload["metrics"] = metrics
    document.variables_used = json.dumps(payload)
    db_session.commit()

    response = client.patch(
        f"/api/reports/{snapshot.id}",
        headers=_report_admin_headers(db_session),
        json={
            "reason": "Koreksi clicks tanpa menghapus impressions",
            "metrics": {"gsc_clicks": 125},
            # Server-managed evidence must neither change nor make this request
            # look like a content change by itself.
            "evidence": {"workspace_evidence": [{"label": "Tidak boleh tersimpan"}]},
        },
    )

    assert response.status_code == 200, response.text
    assert response.json()["metrics"]["manual"] == {
        "gsc_clicks": 125,
        "gsc_impressions": 4000,
        "gsc_impressions_previous": 3000,
    }
    assert response.json()["evidence"]["workspace_evidence"] == original_evidence["workspace_evidence"]

    db_session.expire_all()
    saved = db_session.query(ReportSnapshot).filter(ReportSnapshot.id == snapshot.id).one()
    saved_document = db_session.query(GeneratedDocument).filter(GeneratedDocument.id == saved.generated_document_id).one()
    assert json.loads(saved.metrics_json)["manual"] == {
        "gsc_clicks": 125,
        "gsc_impressions": 4000,
        "gsc_impressions_previous": 3000,
    }
    assert json.loads(saved_document.variables_used)["metrics"]["manual"] == {
        "gsc_clicks": 125,
        "gsc_impressions": 4000,
        "gsc_impressions_previous": 3000,
    }
    assert json.loads(saved.evidence_json)["workspace_evidence"] == original_evidence["workspace_evidence"]


def test_patch_workspace_evidence_only_is_not_an_effective_change(client, db_session, monkeypatch):
    snapshot = _draft_report_for_patch(db_session, monkeypatch)

    response = client.patch(
        f"/api/reports/{snapshot.id}",
        headers=_report_admin_headers(db_session),
        json={
            "reason": "Mencoba mengubah evidence server",
            "evidence": {"workspace_evidence": [{"label": "Tidak boleh tersimpan"}]},
        },
    )

    assert response.status_code == 422


def test_patch_partial_pdf_write_failure_cleans_new_file_and_preserves_old_file(db_session, monkeypatch):
    import builtins

    from app.services import client_report_service as svc
    from models import GeneratedDocument

    snapshot = _draft_report_for_patch(db_session, monkeypatch)
    document = db_session.query(GeneratedDocument).filter(GeneratedDocument.id == snapshot.generated_document_id).one()
    old_url = document.file_url
    old_path = os.path.join(svc.DOCUMENTS_DIR, os.path.basename(old_url))
    filenames_before = set(os.listdir(svc.DOCUMENTS_DIR))
    assert os.path.exists(old_path)

    original_open = builtins.open
    attempted_paths = []

    class _PartialWriteFile:
        def __init__(self, handle):
            self.handle = handle

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, traceback):
            self.handle.close()
            return False

        def write(self, data):
            self.handle.write(data[:5])
            self.handle.flush()
            raise OSError("forced partial PDF write failure")

    def _partial_open(path, mode="r", *args, **kwargs):
        handle = original_open(path, mode, *args, **kwargs)
        if path.startswith(svc.DOCUMENTS_DIR) and mode == "wb":
            attempted_paths.append(path)
            return _PartialWriteFile(handle)
        return handle

    monkeypatch.setattr(builtins, "open", _partial_open)

    try:
        svc.patch_draft_report_snapshot(
            db_session,
            report_id=snapshot.id,
            manual_metrics={"gsc_clicks": 125},
            evidence=None,
            narrative=None,
            reason="Memastikan kegagalan write aman",
            actor="Report Admin",
        )
    except OSError as exc:
        assert "forced partial PDF write failure" in str(exc)
    else:
        raise AssertionError("partial PDF write failure must be raised")

    assert attempted_paths
    assert not os.path.exists(attempted_paths[0])
    assert os.path.exists(old_path)
    assert set(os.listdir(svc.DOCUMENTS_DIR)) == filenames_before
    db_session.rollback()
    restored = db_session.query(GeneratedDocument).filter(GeneratedDocument.id == document.id).one()
    assert restored.file_url == old_url


