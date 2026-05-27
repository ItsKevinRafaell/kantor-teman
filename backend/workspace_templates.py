"""
Workspace Klien — Service Templates
Each template defines sheets, columns, and default rows per service type.
"""
from typing import Any

_BASE_COLS = [
    {"key": "task_name", "label": "Nama Task", "type": "text", "is_system": True},
    {"key": "status", "label": "Status", "type": "status", "options": ["To Do", "In Progress", "Done"], "is_system": True},
    {"key": "pic", "label": "PIC", "type": "text"},
    {"key": "due_date", "label": "Due Date", "type": "date"},
    {"key": "notes", "label": "Catatan", "type": "textarea"},
    {"key": "done", "label": "✓", "type": "checkbox", "is_system": True},
]

WORKSPACE_TEMPLATES: dict[str, Any] = {

    "web_dev": {
        "default_months": 2,
        "sheets": [
            {
                "month": 1, "label": "Bulan 1 - Discovery & Design",
                "columns": _BASE_COLS,
                "default_rows": [
                    {"task_name": "Site audit / requirement gathering"},
                    {"task_name": "Wireframe & mockup design"},
                    {"task_name": "Content collection from client"},
                    {"task_name": "Domain & hosting setup"},
                ],
            },
            {
                "month": 2, "label": "Bulan 2 - Development & Launch",
                "columns": _BASE_COLS,
                "default_rows": [
                    {"task_name": "Frontend development"},
                    {"task_name": "Backend/CMS setup"},
                    {"task_name": "Content input"},
                    {"task_name": "Testing (responsive, form, speed)"},
                    {"task_name": "Launch & handover"},
                    {"task_name": "Tutorial CMS untuk klien"},
                    {"task_name": "Dokumen serah terima credentials"},
                ],
            },
        ],
    },

    "seo_gmaps": {
        "default_months": 6,
        "sheets": [
            {
                "month": 1, "label": "Bulan 1 - Audit & Setup",
                "columns": _BASE_COLS,
                "default_rows": [
                    {"task_name": "Site audit (speed, error, structure)"},
                    {"task_name": "Keyword research (10-15 keywords)"},
                    {"task_name": "Competitor analysis"},
                    {"task_name": "GMB audit & optimization"},
                    {"task_name": "Setup GSC + Analytics"},
                    {"task_name": "Content plan"},
                ],
            },
            {
                "month": 2, "label": "Bulan 2 - On-Page & Artikel Batch 1",
                "columns": _BASE_COLS,
                "default_rows": [
                    {"task_name": "Fix on-page (meta, heading, alt)"},
                    {"task_name": "Internal linking"},
                    {"task_name": "Artikel batch 1"},
                    {"task_name": "GMB update (foto, post, Q&A)"},
                ],
            },
        ],
        "month_3_to_n_template": {
            "label": "Bulan {month} - Content & Backlink",
            "columns": _BASE_COLS,
            "default_rows": [
                {"task_name": "Artikel batch lanjutan"},
                {"task_name": "Backlink outreach"},
                {"task_name": "Update artikel lama"},
                {"task_name": "GMB post rutin"},
            ],
        },
        "last_month_template": {
            "label": "Bulan {month} - Evaluasi & Renewal",
            "columns": _BASE_COLS,
            "default_rows": [
                {"task_name": "Final ranking check"},
                {"task_name": "Traffic comparison"},
                {"task_name": "Rekomendasi next steps"},
                {"task_name": "Proposal renewal"},
            ],
        },
        "extra_sheets": [
            {
                "label": "Artikel Tracker",
                "columns": [
                    {"key": "judul", "label": "Judul", "type": "text", "is_system": True},
                    {"key": "keyword", "label": "Keyword", "type": "text"},
                    {"key": "intent", "label": "Intent", "type": "select", "options": ["Informational", "Commercial", "Transactional", "Navigational"]},
                    {"key": "volume", "label": "Volume", "type": "number"},
                    {"key": "kd_pct", "label": "KD%", "type": "number"},
                    {"key": "status", "label": "Status", "type": "status", "options": ["Draft", "Review", "Revision", "Published"], "is_system": True},
                    {"key": "gdocs_link", "label": "Link Google Docs", "type": "url"},
                    {"key": "publish_date", "label": "Tanggal Publish", "type": "date"},
                    {"key": "done", "label": "✓", "type": "checkbox", "is_system": True},
                ],
                "default_rows": [],
            },
        ],
    },

    "sosmed": {
        "default_months": 3,
        "sheet_template": {
            "label": "Bulan {month} - Kelola Sosmed",
            "columns": [
                {"key": "task_name", "label": "Nama Task", "type": "text", "is_system": True},
                {"key": "status", "label": "Status", "type": "status", "options": ["Draft", "Approved", "Posted", "Revision"], "is_system": True},
                {"key": "platform", "label": "Platform", "type": "select", "options": ["Instagram", "Facebook", "TikTok", "LinkedIn", "Twitter/X"]},
                {"key": "content_type", "label": "Tipe Konten", "type": "select", "options": ["Feed", "Reels", "Story", "Carousel"]},
                {"key": "caption", "label": "Caption", "type": "textarea"},
                {"key": "schedule_date", "label": "Jadwal Post", "type": "date"},
                {"key": "posted_link", "label": "Link Post", "type": "url"},
                {"key": "notes", "label": "Catatan", "type": "textarea"},
                {"key": "done", "label": "✓", "type": "checkbox", "is_system": True},
            ],
            "default_rows": [
                {"task_name": "Content planning (pillar + calendar)"},
                {"task_name": "Content production - design"},
                {"task_name": "Content production - copy"},
                {"task_name": "Posting schedule"},
                {"task_name": "Engagement & community management"},
                {"task_name": "Monthly analytics review"},
                {"task_name": "Content approval dari klien"},
            ],
        },
    },

    "maintenance": {
        "default_months": 1,
        "sheet_template": {
            "label": "Bulan {month} - Maintenance",
            "columns": [
                {"key": "task_name", "label": "Nama Task", "type": "text", "is_system": True},
                {"key": "status", "label": "Status", "type": "status", "options": ["To Do", "Done"], "is_system": True},
                {"key": "screenshot", "label": "Screenshot Bukti", "type": "url"},
                {"key": "gdrive_link", "label": "Link Google Drive", "type": "url"},
                {"key": "notes", "label": "Catatan", "type": "textarea"},
                {"key": "done", "label": "✓", "type": "checkbox", "is_system": True},
            ],
            "default_rows": [
                {"task_name": "Backup website (screenshot bukti)"},
                {"task_name": "Update plugin/theme"},
                {"task_name": "Security scan"},
                {"task_name": "Cache clearing"},
                {"task_name": "Performance check"},
                {"task_name": "Form submission test"},
                {"task_name": "WhatsApp button test"},
                {"task_name": "Link Google Drive backup"},
            ],
        },
    },

    "web_dev_bulanan": {
        "default_months": 3,
        "sheets": [
            {
                "month": 1, "label": "Bulan 1 - Design + Pembayaran 30%",
                "columns": [
                    {"key": "task_name", "label": "Nama Task", "type": "text", "is_system": True},
                    {"key": "status", "label": "Status", "type": "status", "options": ["To Do", "In Progress", "Done"], "is_system": True},
                    {"key": "milestone", "label": "Milestone", "type": "text"},
                    {"key": "payment_pct", "label": "Pembayaran %", "type": "number"},
                    {"key": "quota_used", "label": "Quota Terpakai", "type": "number"},
                    {"key": "quota_total", "label": "Quota Total", "type": "number"},
                    {"key": "due_date", "label": "Due Date", "type": "date"},
                    {"key": "notes", "label": "Catatan", "type": "textarea"},
                    {"key": "done", "label": "✓", "type": "checkbox", "is_system": True},
                ],
                "default_rows": [
                    {"task_name": "Site audit / requirement gathering", "milestone": "Design", "payment_pct": 30},
                    {"task_name": "Wireframe & mockup design", "milestone": "Design"},
                    {"task_name": "Content collection from client", "milestone": "Design"},
                    {"task_name": "Domain & hosting setup", "milestone": "Design"},
                    {"task_name": "Invoice pembayaran 30%", "milestone": "Payment"},
                ],
            },
            {
                "month": 2, "label": "Bulan 2 - Development + Pembayaran 40%",
                "columns": [
                    {"key": "task_name", "label": "Nama Task", "type": "text", "is_system": True},
                    {"key": "status", "label": "Status", "type": "status", "options": ["To Do", "In Progress", "Done"], "is_system": True},
                    {"key": "milestone", "label": "Milestone", "type": "text"},
                    {"key": "payment_pct", "label": "Pembayaran %", "type": "number"},
                    {"key": "quota_used", "label": "Quota Terpakai", "type": "number"},
                    {"key": "quota_total", "label": "Quota Total", "type": "number"},
                    {"key": "due_date", "label": "Due Date", "type": "date"},
                    {"key": "notes", "label": "Catatan", "type": "textarea"},
                    {"key": "done", "label": "✓", "type": "checkbox", "is_system": True},
                ],
                "default_rows": [
                    {"task_name": "Frontend development", "milestone": "Development", "payment_pct": 40},
                    {"task_name": "Backend/CMS setup", "milestone": "Development"},
                    {"task_name": "Content input", "milestone": "Development"},
                    {"task_name": "Invoice pembayaran 40%", "milestone": "Payment"},
                ],
            },
            {
                "month": 3, "label": "Bulan 3 - Launch + Pembayaran 30%",
                "columns": [
                    {"key": "task_name", "label": "Nama Task", "type": "text", "is_system": True},
                    {"key": "status", "label": "Status", "type": "status", "options": ["To Do", "In Progress", "Done"], "is_system": True},
                    {"key": "milestone", "label": "Milestone", "type": "text"},
                    {"key": "payment_pct", "label": "Pembayaran %", "type": "number"},
                    {"key": "quota_used", "label": "Quota Terpakai", "type": "number"},
                    {"key": "quota_total", "label": "Quota Total", "type": "number"},
                    {"key": "due_date", "label": "Due Date", "type": "date"},
                    {"key": "notes", "label": "Catatan", "type": "textarea"},
                    {"key": "done", "label": "✓", "type": "checkbox", "is_system": True},
                ],
                "default_rows": [
                    {"task_name": "Testing (responsive, form, speed)", "milestone": "Launch", "payment_pct": 30},
                    {"task_name": "Launch & handover", "milestone": "Launch"},
                    {"task_name": "Tutorial CMS untuk klien", "milestone": "Launch"},
                    {"task_name": "Dokumen serah terima credentials", "milestone": "Launch"},
                    {"task_name": "Invoice pembayaran 30%", "milestone": "Payment"},
                ],
            },
        ],
    },

    "branding": {
        "default_months": 1,
        "sheets": [
            {
                "month": 1, "label": "Bulan 1 - Desain Logo & Branding",
                "columns": [
                    {"key": "task_name", "label": "Nama Task", "type": "text", "is_system": True},
                    {"key": "week", "label": "Minggu", "type": "select", "options": ["Minggu 1", "Minggu 2", "Minggu 3", "Minggu 4"]},
                    {"key": "status", "label": "Status", "type": "status", "options": ["To Do", "In Progress", "Revision", "Done"], "is_system": True},
                    {"key": "revision_count", "label": "Revisi ke-", "type": "number"},
                    {"key": "file_link", "label": "Link File", "type": "url"},
                    {"key": "notes", "label": "Catatan", "type": "textarea"},
                    {"key": "done", "label": "✓", "type": "checkbox", "is_system": True},
                ],
                "default_rows": [
                    {"task_name": "Client brief questionnaire", "week": "Minggu 1"},
                    {"task_name": "Mood board (3 directions)", "week": "Minggu 1"},
                    {"task_name": "Reference collection", "week": "Minggu 1"},
                    {"task_name": "Logo concept (3 options)", "week": "Minggu 2"},
                    {"task_name": "Client feedback round 1", "week": "Minggu 2"},
                    {"task_name": "Revisi logo (max 3x)", "week": "Minggu 3"},
                    {"task_name": "Color palette finalization", "week": "Minggu 3"},
                    {"task_name": "Typography selection", "week": "Minggu 3"},
                    {"task_name": "File package (/vector /raster /mockup /sosmed)", "week": "Minggu 4"},
                    {"task_name": "Brand guideline mini PDF", "week": "Minggu 4"},
                    {"task_name": "Social media kit", "week": "Minggu 4"},
                    {"task_name": "Source file handover", "week": "Minggu 4"},
                ],
            },
        ],
    },
}

WORKSPACE_TEMPLATES["general"] = {
    "default_months": 1,
    "sheets": [
        {
            "month": None,
            "label": "Task Board",
            "columns": [
                {"key": "task", "label": "Task", "type": "text", "is_system": True},
                {"key": "status", "label": "Status", "type": "status", "is_system": True,
                 "options": ["To Do", "In Progress", "Review", "Done"]},
                {"key": "assignee", "label": "PIC", "type": "text"},
                {"key": "due_date", "label": "Deadline", "type": "date"},
                {"key": "notes", "label": "Catatan", "type": "textarea"},
                {"key": "done", "label": "Selesai", "type": "checkbox", "is_system": True},
            ],
            "default_rows": [
                {"task": "Onboarding klien", "status": "To Do"},
                {"task": "Kick-off meeting", "status": "To Do"},
                {"task": "Deliverable pertama", "status": "To Do"},
            ],
        }
    ],
}


def build_sheets_for_service(service_type: str, contract_months: int) -> list[dict]:
    """
    Returns list of sheet defs: [{month, label, columns, default_rows}]
    Handles dynamic month generation for seo_gmaps, sosmed, maintenance.
    """
    tmpl = WORKSPACE_TEMPLATES.get(service_type)
    if not tmpl:
        raise ValueError(f"Unknown service_type: {service_type}")

    sheets: list[dict] = []

    if "sheets" in tmpl:
        # Fixed sheets (web_dev, web_dev_bulanan, branding)
        sheets = list(tmpl["sheets"])

    elif "sheet_template" in tmpl:
        # Repeating template per month (sosmed, maintenance)
        st = tmpl["sheet_template"]
        for m in range(1, contract_months + 1):
            sheets.append({
                "month": m,
                "label": st["label"].replace("{month}", str(m)),
                "columns": st["columns"],
                "default_rows": list(st["default_rows"]),
            })

    # seo_gmaps: fixed months 1-2, dynamic 3..N-1, last month evaluasi
    if service_type == "seo_gmaps":
        m3n = tmpl["month_3_to_n_template"]
        last = tmpl["last_month_template"]
        for m in range(3, contract_months):
            sheets.append({
                "month": m,
                "label": m3n["label"].replace("{month}", str(m)),
                "columns": m3n["columns"],
                "default_rows": list(m3n["default_rows"]),
            })
        if contract_months >= 3:
            sheets.append({
                "month": contract_months,
                "label": last["label"].replace("{month}", str(contract_months)),
                "columns": last["columns"],
                "default_rows": list(last["default_rows"]),
            })
        # Append extra sheets (Artikel Tracker)
        for i, extra in enumerate(tmpl.get("extra_sheets", [])):
            sheets.append({
                "month": None,
                "label": extra["label"],
                "columns": extra["columns"],
                "default_rows": list(extra["default_rows"]),
                "is_extra": True,
            })

    return sheets


def build_sheets_for_days(days: int, service_type: str = "general") -> list[dict]:
    """Generate weekly sheets for short-duration projects (< 30 days)."""
    tmpl = WORKSPACE_TEMPLATES.get(service_type, WORKSPACE_TEMPLATES["general"])
    cols = tmpl.get("sheets", [{}])[0].get("columns", _BASE_COLS) if "sheets" in tmpl else tmpl.get("sheet_template", {}).get("columns", _BASE_COLS)

    weeks = max(1, (days + 6) // 7)
    sheets = []
    for w in range(1, weeks + 1):
        day_start = (w - 1) * 7 + 1
        day_end = min(w * 7, days)
        sheets.append({
            "month": None,
            "label": f"Minggu {w} (Hari {day_start}-{day_end})",
            "columns": cols,
            "default_rows": [],
        })
    return sheets
