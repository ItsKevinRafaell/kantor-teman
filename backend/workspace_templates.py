"""
Workspace Klien - template SOP per jenis layanan.

Board dipakai untuk melihat progress secara visual. Workspace dipakai sebagai
spreadsheet operasional: apa yang dikerjakan, outputnya apa, link buktinya di
mana, dan kriteria selesai tiap task.
"""
from copy import deepcopy
from typing import Any


DEFAULT_STATUS = ["To Do", "In Progress", "Review", "Done"]


def _ops_columns(status_options: list[str] | None = None, extra: list[dict] | None = None) -> list[dict]:
    columns = [
        {"key": "stage", "label": "Tahap", "type": "select", "options": ["Onboarding", "Riset", "Produksi", "Review", "Publikasi", "Reporting", "Administrasi"]},
        {"key": "task_name", "label": "Nama Task", "type": "text", "is_system": True},
        {"key": "status", "label": "Status", "type": "status", "options": status_options or DEFAULT_STATUS, "is_system": True},
        {"key": "pic", "label": "PIC", "type": "text"},
        {"key": "due_date", "label": "Deadline", "type": "date"},
    ]
    if extra:
        columns.extend(extra)
    columns.extend([
        {"key": "output_link", "label": "Output / Link Bukti", "type": "url"},
        {"key": "success_criteria", "label": "Kriteria Selesai", "type": "textarea"},
        {"key": "notes", "label": "Catatan", "type": "textarea"},
        {"key": "done", "label": "Selesai", "type": "checkbox", "is_system": True},
    ])
    return columns


_BASE_COLS = _ops_columns()


def _task(task_name: str, stage: str, success_criteria: str, **extra: Any) -> dict:
    return {
        "task_name": task_name,
        "stage": stage,
        "status": "To Do",
        "success_criteria": success_criteria,
        **extra,
    }


WORKSPACE_TEMPLATES: dict[str, Any] = {
    "web_dev": {
        "default_months": 2,
        "sheets": [
            {
                "month": 1,
                "label": "Bulan 1 - Discovery, Struktur, dan Desain",
                "columns": _BASE_COLS,
                "default_rows": [
                    _task("Kick-off dan brief kebutuhan klien", "Onboarding", "Tujuan bisnis, target audience, layanan utama, dan PIC klien sudah jelas."),
                    _task("Kumpulkan akses dan aset brand", "Onboarding", "Logo, warna, konten awal, domain/hosting, dan kontak admin sudah tercatat aman."),
                    _task("Susun sitemap dan struktur menu", "Riset", "Daftar halaman utama, halaman layanan, CTA, dan prioritas konten sudah disetujui."),
                    _task("Wireframe halaman utama dan halaman layanan", "Produksi", "Alur halaman mudah dipahami, CTA WhatsApp jelas, dan tidak ada section mubazir."),
                    _task("Draft copywriting halaman utama", "Produksi", "Headline, benefit, layanan, testimoni, FAQ, dan CTA sudah siap masuk desain."),
                    _task("Desain UI homepage versi desktop dan mobile", "Produksi", "Desain mobile tidak overflow, CTA mudah diklik, dan warna sesuai brand."),
                    _task("Review desain dengan klien", "Review", "Feedback klien tercatat dan keputusan revisi jelas."),
                ],
            },
            {
                "month": 2,
                "label": "Bulan 2 - Development, QA, dan Launch",
                "columns": _BASE_COLS,
                "default_rows": [
                    _task("Setup domain, hosting, SSL, dan environment", "Produksi", "Domain aktif, SSL hijau, dan akses produksi terdokumentasi."),
                    _task("Implementasi halaman utama dan halaman layanan", "Produksi", "Semua halaman sesuai desain dan konten sudah masuk."),
                    _task("Setup form, tombol WhatsApp, dan tracking dasar", "Produksi", "Form terkirim, tombol WA benar, event tracking penting aktif."),
                    _task("QA responsive desktop, tablet, dan mobile", "Review", "Tidak ada teks tumpuk, horizontal scroll, atau tombol sulit diklik."),
                    _task("QA performa, SEO basic, dan keamanan", "Review", "Meta title/description, sitemap, robots, cache, dan keamanan dasar sudah dicek."),
                    _task("Launch website", "Publikasi", "Website live dan klien menerima link final."),
                    _task("Handover CMS dan panduan singkat", "Administrasi", "Akses CMS, tutorial, dan catatan maintenance sudah dikirim ke klien."),
                ],
            },
        ],
    },

    "seo_gmaps": {
        "default_months": 6,
        "sheets": [
            {
                "month": 1,
                "label": "Bulan 1 - Baseline, Audit, dan Setup",
                "columns": _BASE_COLS,
                "default_rows": [
                    _task("Kumpulkan akses website, GSC, GA, dan Google Business", "Onboarding", "Semua akses penting tersedia atau status kendalanya tercatat."),
                    _task("Catat baseline ranking keyword utama", "Riset", "Minimal 10 keyword dicatat dengan posisi awal dan target page."),
                    _task("Riset keyword lokal dan intent pencarian", "Riset", "Keyword dikelompokkan berdasarkan intent: informasi, komersial, transaksi."),
                    _task("Analisis kompetitor lokal", "Riset", "Minimal 3 kompetitor dicatat: halaman kuat, review, konten, dan peluang gap."),
                    _task("Audit teknis website", "Review", "Masalah speed, index, heading, meta, broken link, dan struktur halaman dicatat."),
                    _task("Audit Google Business Profile", "Review", "Kategori, jam buka, foto, produk/layanan, post, Q&A, dan review dicek."),
                    _task("Susun rencana konten 3 bulan", "Produksi", "Judul artikel, keyword, target page, dan prioritas produksi sudah jelas."),
                    _task("Report baseline ke klien", "Reporting", "Klien menerima kondisi awal dan next action bulan berikutnya."),
                ],
            },
            {
                "month": 2,
                "label": "Bulan 2 - On-page, GMB, dan Konten Awal",
                "columns": _BASE_COLS,
                "default_rows": [
                    _task("Optimasi title, meta, heading, dan internal link", "Produksi", "Halaman prioritas punya metadata, struktur heading, dan internal link yang rapi."),
                    _task("Optimasi halaman layanan utama", "Produksi", "Konten layanan menjawab intent pencarian dan punya CTA WhatsApp yang jelas."),
                    _task("Update Google Business Profile", "Produksi", "Foto, layanan, deskripsi, Q&A, dan post awal sudah diperbarui."),
                    _task("Publikasi artikel batch 1", "Publikasi", "Minimal 2 artikel selesai, publish, dan link dicatat di tracker."),
                    _task("Bangun local citation awal", "Produksi", "Minimal 3 listing/citation relevan dibuat atau diupdate."),
                    _task("Buat alur minta review pelanggan", "Produksi", "Template WA/review link siap dipakai klien."),
                    _task("Report bulan 2", "Reporting", "Progress, kendala, ranking awal, dan action bulan berikutnya terkirim."),
                ],
            },
        ],
        "month_3_to_n_template": {
            "label": "Bulan {month} - Produksi Konten, GMB, dan Authority",
            "columns": _BASE_COLS,
            "default_rows": [
                _task("Update ranking keyword dan traffic", "Riset", "Perubahan ranking dan traffic dicatat sebelum eksekusi bulan berjalan."),
                _task("Publikasi artikel bulanan", "Publikasi", "Artikel sesuai content plan publish dan internal link sudah dipasang."),
                _task("Update Google Business post dan foto", "Publikasi", "Post/foto bulanan live dan link bukti dicatat."),
                _task("Optimasi halaman lama dari data performa", "Produksi", "Halaman yang turun/berpotensi naik sudah diperbaiki."),
                _task("Local citation atau backlink ringan", "Produksi", "Bukti link tersimpan dan relevansi sumber dicek."),
                _task("Report bulanan dan rekomendasi", "Reporting", "Klien menerima ringkasan hasil, kendala, dan prioritas bulan depan."),
            ],
        },
        "last_month_template": {
            "label": "Bulan {month} - Evaluasi Akhir dan Renewal",
            "columns": _BASE_COLS,
            "default_rows": [
                _task("Final ranking check", "Review", "Ranking akhir dibandingkan dengan baseline bulan pertama."),
                _task("Traffic dan conversion comparison", "Review", "Data traffic, klik WA, leads, dan insight utama dirangkum."),
                _task("Audit ulang halaman prioritas", "Review", "Sisa masalah teknis dan konten dicatat sebagai backlog."),
                _task("Rekomendasi next action 3 bulan", "Reporting", "Rencana lanjutan jelas: lanjut retainer, scale konten, atau perbaikan teknis."),
                _task("Proposal renewal atau upsell", "Administrasi", "Proposal renewal/upsell siap dikirim bila klien cocok lanjut."),
            ],
        },
        "extra_sheets": [
            {
                "label": "Keyword Tracker",
                "columns": [
                    {"key": "keyword", "label": "Keyword", "type": "text", "is_system": True},
                    {"key": "intent", "label": "Intent", "type": "select", "options": ["Informasi", "Komersial", "Transaksi", "Navigasi"]},
                    {"key": "volume", "label": "Volume", "type": "number"},
                    {"key": "difficulty", "label": "Kesulitan", "type": "number"},
                    {"key": "target_page", "label": "Target Page", "type": "url"},
                    {"key": "current_rank", "label": "Rank Saat Ini", "type": "number"},
                    {"key": "target_rank", "label": "Target Rank", "type": "number"},
                    {"key": "status", "label": "Status", "type": "status", "options": ["Riset", "Optimasi", "Monitoring", "Menang"], "is_system": True},
                    {"key": "notes", "label": "Catatan", "type": "textarea"},
                    {"key": "done", "label": "Selesai", "type": "checkbox", "is_system": True},
                ],
                "default_rows": [],
            },
            {
                "label": "Artikel Tracker",
                "columns": [
                    {"key": "judul", "label": "Judul", "type": "text", "is_system": True},
                    {"key": "keyword", "label": "Keyword Utama", "type": "text"},
                    {"key": "intent", "label": "Intent", "type": "select", "options": ["Informasi", "Komersial", "Transaksi", "Navigasi"]},
                    {"key": "writer", "label": "Writer", "type": "text"},
                    {"key": "reviewer", "label": "Reviewer", "type": "text"},
                    {"key": "status", "label": "Status", "type": "status", "options": ["Ide", "Draft", "Review", "Revisi", "Published"], "is_system": True},
                    {"key": "gdocs_link", "label": "Link Google Docs", "type": "url"},
                    {"key": "publish_link", "label": "Link Publish", "type": "url"},
                    {"key": "publish_date", "label": "Tanggal Publish", "type": "date"},
                    {"key": "done", "label": "Selesai", "type": "checkbox", "is_system": True},
                ],
                "default_rows": [],
            },
            {
                "label": "Google Business Tracker",
                "columns": [
                    {"key": "activity", "label": "Aktivitas", "type": "text", "is_system": True},
                    {"key": "status", "label": "Status", "type": "status", "options": ["To Do", "In Progress", "Done"], "is_system": True},
                    {"key": "activity_date", "label": "Tanggal", "type": "date"},
                    {"key": "proof_link", "label": "Link Bukti", "type": "url"},
                    {"key": "notes", "label": "Catatan", "type": "textarea"},
                    {"key": "done", "label": "Selesai", "type": "checkbox", "is_system": True},
                ],
                "default_rows": [
                    {"activity": "Update foto bisnis bulanan", "status": "To Do"},
                    {"activity": "Post Google Business bulanan", "status": "To Do"},
                    {"activity": "Cek review baru dan balasan", "status": "To Do"},
                ],
            },
        ],
    },

    "sosmed": {
        "default_months": 3,
        "sheet_template": {
            "label": "Bulan {month} - Kalender dan Eksekusi Sosmed",
            "columns": _ops_columns(
                status_options=["Ide", "Draft", "Review", "Approved", "Posted", "Revision", "Done"],
                extra=[
                    {"key": "platform", "label": "Platform", "type": "select", "options": ["Instagram", "Facebook", "TikTok", "LinkedIn"]},
                    {"key": "content_type", "label": "Tipe Konten", "type": "select", "options": ["Feed", "Reels", "Story", "Carousel", "Short Video"]},
                    {"key": "pillar", "label": "Pilar Konten", "type": "select", "options": ["Edukasi", "Promosi", "Testimoni", "Behind the Scene", "FAQ", "Portfolio"]},
                    {"key": "schedule_date", "label": "Jadwal Post", "type": "date"},
                    {"key": "caption", "label": "Caption", "type": "textarea"},
                    {"key": "asset_link", "label": "Link Asset", "type": "url"},
                    {"key": "posted_link", "label": "Link Post", "type": "url"},
                ],
            ),
            "default_rows": [
                _task("Susun kalender konten bulanan", "Riset", "Tema, pilar, jadwal, dan format konten sudah jelas."),
                _task("Kumpulkan bahan dari klien", "Onboarding", "Foto, video, promo, testimoni, dan info produk siap dipakai."),
                _task("Produksi desain/video batch 1", "Produksi", "Asset batch pertama siap review dan link asset tercatat."),
                _task("Review internal caption dan visual", "Review", "Tidak ada typo, visual sesuai brand, CTA jelas."),
                _task("Approval konten ke klien", "Review", "Status approved/revisi tercatat per konten."),
                _task("Posting sesuai jadwal", "Publikasi", "Link post dicatat dan status menjadi Posted/Done."),
                _task("Rekap performa bulanan", "Reporting", "Reach, engagement, konten terbaik, dan rekomendasi bulan depan tercatat."),
            ],
        },
    },

    "maintenance": {
        "default_months": 1,
        "sheet_template": {
            "label": "Bulan {month} - Checklist Maintenance",
            "columns": _ops_columns(
                status_options=["To Do", "In Progress", "Blocked", "Done"],
                extra=[
                    {"key": "area", "label": "Area", "type": "select", "options": ["Backup", "Security", "Performance", "Plugin/Theme", "Form", "Konten", "Laporan"]},
                    {"key": "risk", "label": "Risiko", "type": "select", "options": ["Rendah", "Sedang", "Tinggi"]},
                ],
            ),
            "default_rows": [
                _task("Backup website dan database", "Produksi", "File backup tersimpan dan link bukti dicatat.", area="Backup", risk="Tinggi"),
                _task("Update plugin, theme, atau dependency", "Produksi", "Update selesai tanpa error visual/fungsi.", area="Plugin/Theme", risk="Sedang"),
                _task("Security scan dasar", "Review", "Tidak ada temuan kritis atau temuan dicatat sebagai action item.", area="Security", risk="Tinggi"),
                _task("Cek performa dan cache", "Review", "Halaman utama tetap cepat dan cache berjalan.", area="Performance", risk="Sedang"),
                _task("Tes form, tombol WhatsApp, dan checkout jika ada", "Review", "Semua jalur kontak utama berhasil dites.", area="Form", risk="Tinggi"),
                _task("Update konten kecil sesuai request", "Produksi", "Perubahan konten sesuai request klien.", area="Konten", risk="Rendah"),
                _task("Laporan maintenance bulanan", "Reporting", "Ringkasan pekerjaan, bukti, dan rekomendasi dikirim ke klien.", area="Laporan", risk="Rendah"),
            ],
        },
    },

    "web_dev_bulanan": {
        "default_months": 3,
        "sheets": [
            {
                "month": 1,
                "label": "Bulan 1 - Discovery, Desain, dan DP 50%",
                "columns": _ops_columns(extra=[
                    {"key": "milestone", "label": "Milestone", "type": "text"},
                    {"key": "payment_pct", "label": "Pembayaran %", "type": "number"},
                ]),
                "default_rows": [
                    _task("Invoice pembayaran 50%", "Administrasi", "Invoice DP dibuat dan dikirim sebelum produksi dimulai.", milestone="DP", payment_pct=50),
                    _task("Kick-off dan brief kebutuhan", "Onboarding", "Scope, timeline, PIC, dan batas revisi disepakati.", milestone="Discovery"),
                    _task("Kumpulkan aset dan akses", "Onboarding", "Akses domain/hosting/CMS dan aset brand sudah aman.", milestone="Discovery"),
                    _task("Sitemap dan wireframe", "Riset", "Struktur halaman disetujui.", milestone="Design"),
                    _task("Desain homepage dan halaman utama", "Produksi", "Desain mobile dan desktop siap review.", milestone="Design"),
                ],
            },
            {
                "month": 2,
                "label": "Bulan 2 - Development dan Pembayaran 30%",
                "columns": _ops_columns(extra=[
                    {"key": "milestone", "label": "Milestone", "type": "text"},
                    {"key": "payment_pct", "label": "Pembayaran %", "type": "number"},
                ]),
                "default_rows": [
                    _task("Invoice pembayaran 30%", "Administrasi", "Invoice termin kedua dibuat saat development masuk.", milestone="Payment", payment_pct=30),
                    _task("Implementasi frontend", "Produksi", "UI sesuai desain dan responsive.", milestone="Development"),
                    _task("Setup backend/CMS", "Produksi", "CMS/admin dapat dipakai sesuai scope.", milestone="Development"),
                    _task("Input konten dan media", "Produksi", "Konten masuk sesuai struktur halaman.", milestone="Development"),
                    _task("Integrasi form, WhatsApp, dan tracking", "Produksi", "Semua integrasi utama berhasil dites.", milestone="Development"),
                ],
            },
            {
                "month": 3,
                "label": "Bulan 3 - QA, Launch, dan Pelunasan 20%",
                "columns": _ops_columns(extra=[
                    {"key": "milestone", "label": "Milestone", "type": "text"},
                    {"key": "payment_pct", "label": "Pembayaran %", "type": "number"},
                ]),
                "default_rows": [
                    _task("QA responsive, speed, dan fungsi", "Review", "Tidak ada blocker untuk launch.", milestone="QA"),
                    _task("Revisi final sesuai scope", "Review", "Revisi final selesai dan disetujui.", milestone="QA"),
                    _task("Invoice pembayaran 20%", "Administrasi", "Invoice pelunasan dibuat sebelum handover final.", milestone="Payment", payment_pct=20),
                    _task("Launch website", "Publikasi", "Website live dan domain mengarah benar.", milestone="Launch"),
                    _task("Handover akses dan panduan", "Administrasi", "Dokumen akses dan panduan singkat dikirim ke klien.", milestone="Handover"),
                ],
            },
        ],
    },

    "branding": {
        "default_months": 1,
        "sheets": [
            {
                "month": 1,
                "label": "Bulan 1 - Logo, Brand System, dan Handover",
                "columns": _ops_columns(extra=[
                    {"key": "week", "label": "Minggu", "type": "select", "options": ["Minggu 1", "Minggu 2", "Minggu 3", "Minggu 4"]},
                    {"key": "revision_count", "label": "Revisi Ke", "type": "number"},
                    {"key": "file_link", "label": "Link File", "type": "url"},
                ]),
                "default_rows": [
                    _task("Brand questionnaire dan brief", "Onboarding", "Arah brand, target audience, referensi, dan batas revisi sudah jelas.", week="Minggu 1"),
                    _task("Moodboard 2-3 arah visual", "Riset", "Moodboard dikirim dan arah visual dipilih.", week="Minggu 1"),
                    _task("Konsep logo awal", "Produksi", "Minimal 2 konsep logo siap review.", week="Minggu 2"),
                    _task("Review konsep dengan klien", "Review", "Feedback tertulis dan keputusan revisi tercatat.", week="Minggu 2"),
                    _task("Revisi logo", "Produksi", "Revisi sesuai scope selesai.", week="Minggu 3"),
                    _task("Finalisasi warna dan typography", "Produksi", "Palet warna dan font utama disetujui.", week="Minggu 3"),
                    _task("Mini brand guideline PDF", "Produksi", "Panduan penggunaan logo, warna, font, dan contoh aplikasi siap.", week="Minggu 4"),
                    _task("Handover source file dan asset pack", "Administrasi", "File vector/raster, guideline, dan mockup dikirim ke klien.", week="Minggu 4"),
                ],
            },
        ],
    },

    "general": {
        "default_months": 1,
        "sheets": [
            {
                "month": None,
                "label": "Task Operasional",
                "columns": _BASE_COLS,
                "default_rows": [
                    _task("Onboarding klien", "Onboarding", "PIC, scope, deadline, dan kebutuhan utama sudah jelas."),
                    _task("Kick-off meeting", "Onboarding", "Catatan meeting dan action item tersimpan."),
                    _task("Deliverable pertama", "Produksi", "Output pertama selesai dan siap review."),
                ],
            }
        ],
    },
}


def _clone(value: Any) -> Any:
    return deepcopy(value)


# ─── Service type normalization ──────────────────────────────────────────────
#
# service_type bisa datang dalam banyak bentuk:
#   - kosong / None                     -> fallback "general"
#   - key valid tunggal  "seo_gmaps"    -> dipakai langsung
#   - gabungan           "seo_gmaps,maintenance", "SEO + Maintenance", "web/seo"
#   - free text          "SEO & Google Maps", "Kelola Sosmed", dll
#
# Kalau gabungan, ambil yang PRIMARY berdasarkan prioritas di bawah. Ini bikin
# klien SEO tetap dapat template seo_gmaps (9 sheet) dan bukan fallback general.

# Urutan = prioritas (index kecil = lebih diprioritaskan saat gabungan).
SERVICE_TYPE_PRIORITY: list[str] = [
    "seo_gmaps",
    "web_dev",
    "web_dev_bulanan",
    "sosmed",
    "branding",
    "maintenance",
    "general",
]

# Substring/alias -> canonical key. Dicek pada tiap token hasil split.
# Urutan penting: token dicek terhadap semua alias, hasil dikumpulkan lalu
# dipilih yang prioritasnya tertinggi.
_SERVICE_ALIASES: list[tuple[tuple[str, ...], str]] = [
    (("seo", "gmaps", "google maps", "google business", "gbp", "maps", "lokal", "local"), "seo_gmaps"),
    (("web_dev_bulanan", "web bulanan", "website bulanan"), "web_dev_bulanan"),
    (("web_dev", "web", "website", "landing", "company profile", "dev", "frontend", "fullstack"), "web_dev"),
    (("sosmed", "sosial media", "social media", "instagram", "tiktok", "facebook", "kelola"), "sosmed"),
    (("branding", "logo", "desain", "identitas visual", "brand"), "branding"),
    (("maintenance", "maintain", "pemeliharaan"), "maintenance"),
]


def normalize_service_type(raw: Any) -> str:
    """
    Ubah service_type mentah (bisa kosong / gabungan / free text) jadi SATU key
    valid yang ada di WORKSPACE_TEMPLATES.

    Contoh:
        ""                      -> "general"
        None                    -> "general"
        "seo_gmaps"             -> "seo_gmaps"
        "seo_gmaps,maintenance" -> "seo_gmaps"   (primary by priority)
        "SEO + Maintenance"     -> "seo_gmaps"
        "maintenance,web_dev"   -> "web_dev"
        "sesuatu ga jelas"      -> "general"
    """
    if not raw:
        return "general"

    text = str(raw).strip().lower()
    if not text:
        return "general"

    # 1) Exact match key valid (fast path, termasuk "general").
    if text in WORKSPACE_TEMPLATES:
        return text

    # 2) Split gabungan pakai pemisah umum: koma, plus, ampersand, slash, "dan".
    import re
    tokens = [t.strip() for t in re.split(r"[,+&/|]|\bdan\b|\band\b", text) if t.strip()]
    if not tokens:
        tokens = [text]

    matched: set[str] = set()
    for tok in tokens:
        # 2a) token itu sendiri key valid?
        if tok in WORKSPACE_TEMPLATES:
            matched.add(tok)
            continue
        # 2b) cocokkan via alias/substring.
        for aliases, canonical in _SERVICE_ALIASES:
            if any(alias in tok for alias in aliases):
                matched.add(canonical)
                break

    # 3) Kalau ada full-string alias match yang kelewat (mis. spasi antar token
    #    ilang), cek ulang di seluruh text sebagai jaring pengaman.
    if not matched:
        for aliases, canonical in _SERVICE_ALIASES:
            if any(alias in text for alias in aliases):
                matched.add(canonical)

    if not matched:
        return "general"

    # 4) Pilih PRIMARY berdasarkan prioritas.
    for key in SERVICE_TYPE_PRIORITY:
        if key in matched:
            return key
    return "general"


def build_sheets_for_service(service_type: str, contract_months: int) -> list[dict]:
    """
    Return sheet definitions: [{month, label, columns, default_rows}].
    Dynamic services can repeat a monthly template and SEO can append tracker sheets.

    service_type dinormalisasi dulu supaya bentuk gabungan / kosong / free text
    tetap resolve ke template yang benar (bukan raise / fallback general keliru).
    """
    service_type = normalize_service_type(service_type)
    tmpl = WORKSPACE_TEMPLATES.get(service_type)
    if not tmpl:
        raise ValueError(f"Unknown service_type: {service_type}")

    sheets: list[dict] = []

    if "sheets" in tmpl:
        sheets = _clone(tmpl["sheets"])

    elif "sheet_template" in tmpl:
        st = tmpl["sheet_template"]
        for month in range(1, contract_months + 1):
            sheets.append({
                "month": month,
                "label": st["label"].replace("{month}", str(month)),
                "columns": _clone(st["columns"]),
                "default_rows": _clone(st["default_rows"]),
            })

    if service_type == "seo_gmaps":
        m3n = tmpl["month_3_to_n_template"]
        last = tmpl["last_month_template"]
        for month in range(3, contract_months):
            sheets.append({
                "month": month,
                "label": m3n["label"].replace("{month}", str(month)),
                "columns": _clone(m3n["columns"]),
                "default_rows": _clone(m3n["default_rows"]),
            })
        if contract_months >= 3:
            sheets.append({
                "month": contract_months,
                "label": last["label"].replace("{month}", str(contract_months)),
                "columns": _clone(last["columns"]),
                "default_rows": _clone(last["default_rows"]),
            })
        for extra in tmpl.get("extra_sheets", []):
            sheets.append({
                "month": None,
                "label": extra["label"],
                "columns": _clone(extra["columns"]),
                "default_rows": _clone(extra["default_rows"]),
                "is_extra": True,
            })

    return sheets


def build_sheets_for_days(days: int, service_type: str = "general") -> list[dict]:
    """Generate weekly sheets for short-duration projects (< 30 days)."""
    tmpl = WORKSPACE_TEMPLATES.get(service_type, WORKSPACE_TEMPLATES["general"])
    if "sheets" in tmpl:
        cols = _clone(tmpl["sheets"][0].get("columns", _BASE_COLS))
    else:
        cols = _clone(tmpl.get("sheet_template", {}).get("columns", _BASE_COLS))

    weeks = max(1, (days + 6) // 7)
    sheets = []
    for week in range(1, weeks + 1):
        day_start = (week - 1) * 7 + 1
        day_end = min(week * 7, days)
        sheets.append({
            "month": None,
            "label": f"Minggu {week} (Hari {day_start}-{day_end})",
            "columns": _clone(cols),
            "default_rows": [],
        })
    return sheets
