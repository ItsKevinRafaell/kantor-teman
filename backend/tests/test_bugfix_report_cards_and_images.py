"""Targeted tests for the 2 KantorTeman ERP bugfixes.

BUG 1: _render_metric_cards must SKIP empty/0/error cards (no forced blanks).
BUG 2: custom attached_images render as safe <img> HTML; unsafe input dropped.
"""


def test_metric_cards_skip_empty_pagespeed_and_zero_workspace():
    from app.services.client_report_service import _render_metric_cards

    # Empty workspace + pagespeed error (HTTP 429 -> status != ok)
    html = _render_metric_cards({
        "workspace": {"summary": {"total_tasks": 0, "completed_tasks": 0, "completion_pct": 0}},
        "metrics": {"board": {"columns": []}, "pagespeed": {"status": "error"}},
    })
    assert html == "", "no cards should render when everything is empty/0/error"
    assert "Belum tersedia" not in html


def test_metric_cards_render_only_available():
    from app.services.client_report_service import _render_metric_cards

    html = _render_metric_cards({
        "workspace": {"summary": {"total_tasks": 5, "completed_tasks": 3, "completion_pct": 60}},
        "metrics": {"board": {"columns": [{"count": 4}]}, "pagespeed": {"status": "error"}},
    })
    assert "Progress tugas" in html
    assert "Tugas selesai" in html
    assert "Card aktif" in html
    # pagespeed errored -> card omitted, never "Belum tersedia"
    assert "PageSpeed" not in html
    assert "Belum tersedia" not in html


def test_metric_cards_include_pagespeed_when_ok():
    from app.services.client_report_service import _render_metric_cards

    html = _render_metric_cards({
        "workspace": {"summary": {"total_tasks": 2, "completed_tasks": 2, "completion_pct": 100}},
        "metrics": {"board": {"columns": []}, "pagespeed": {"status": "ok", "performance_score": 88}},
    })
    assert "PageSpeed mobile" in html
    assert "88" in html
    # zero active cards -> Card aktif omitted
    assert "Card aktif" not in html


def test_attached_images_builds_safe_img_and_drops_unsafe():
    from routers.documents import _build_attached_images_html

    html = _build_attached_images_html([
        "https://cdn.example.com/bukti.png",
        {"url": "https://cdn.example.com/stempel.jpg", "caption": "Stempel Resmi"},
        "javascript:alert(1)",                       # dropped: bad scheme
        "https://evil.example.com/x.svg",            # dropped: svg not allowed
        "data:image/png;base64,iVBORw0KGgo=",        # allowed data uri
        "data:text/html;base64,PHNjcmlwdD4=",        # dropped: not image mime
    ])
    assert html.count("<img") == 3
    assert "bukti.png" in html
    assert "stempel.jpg" in html
    assert "Stempel Resmi" in html
    assert "javascript:" not in html
    assert ".svg" not in html
    assert "text/html" not in html


def test_attached_images_empty_yields_empty_string():
    from routers.documents import _build_attached_images_html

    assert _build_attached_images_html(None) == ""
    assert _build_attached_images_html([]) == ""
    assert _build_attached_images_html(["not-a-url", "ftp://x/y.png"]) == ""
