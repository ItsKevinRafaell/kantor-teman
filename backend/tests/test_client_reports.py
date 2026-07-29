import os

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

