"""Web preview service — generate landing page per-lead dari template bank.

Sumber template: backend/web_preview_templates/{key}.html (dibundle di repo,
bukan path eksternal) + aset di UPLOADS_DIR/web_preview_assets/{key}/
(diserve FastAPI via mount /uploads).

Aturan swap (mengikuti prinsip build_swap.py anti-halusinasi):
- Hanya replace string yang PERSIS ada di template (anchor per template
  di REGISTRY bawah). Tidak ada copy yang digenerate.
- Asset path relatif di-rewrite ke /uploads/web_preview_assets/{key}/<file>.
- Idempotent: lead + template yang sama → reuse row yang sudah ada.

Hook dipanggil dari campaign_service.execute_blast_campaign untuk lead
berstatus Prospek Panas; kegagalan generate TIDAK boleh memblokir blast.
"""
import os
import re
from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from app.core.config import FRONTEND_URL
from models import WebPreview, Lead, LeadActivityLog

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
TEMPLATES_DIR = os.path.join(BACKEND_DIR, "web_preview_templates")

# ── Registry template ────────────────────────────────────────────────────────
# brand/phone/wa anchor = string PERSIS yang ada di file template.
# keywords: dicocokkan ke product_interest + business_name (lowercase, "in").
DEFAULT_TEMPLATE_KEY = "kontraktor"
IMAGE_EXT = (".jpg", ".jpeg", ".png", ".webp", ".svg", ".avif")

REGISTRY: dict = {
    "klinik": {
        "title": "Landing klinik/praktik kesehatan",
        "keywords": ["klinik", "kesehatan", "medis", "dokter", "gigi", "puskesmas", "praktik", "apotek", "laboratorium"],
        "brand_anchor": "Klinik Pratama Harapan",
        "phone_display_anchor": "0812-555-1234",
        "wa_anchor": "628125551234",
        "sanitize": [
            (" — Balikpapan</title>", "</title>"),
            ("<small>Balikpapan</small>", "<small>{area_text}</small>"),
            ("Klinik pratama · Gunung Samarinda", "Klinik pratama"),
            ("Yang biasa dicari pasien di Balikpapan.", "Yang biasa dicari pasien."),
            ("Peta area Gunung Samarinda, Balikpapan", "Peta area layanan {brand}"),
            ("Jl. Soekarno-Hatta, Gunung Samarinda", "{address_line}"),
            ("Dekat simpang Soekarno-Hatta, Balikpapan Utara. Parkir motor &amp; mobil di halaman.", "{address_line}"),
            # Netralisasi nama dokter fiktif → label jadwal netral (ACC Kevin 6 Sep)
            ("dr. Aulia Rahman", "dr. Umum (Pagi)"),
            ("dr. Farhan Yusuf", "dr. Umum (Sore)"),
            ("drg. Sinta Maharani", "drg. Gigi (Pagi)"),
            ("dr. Maya Putri, Sp.A", "dr. Anak (KIA)"),
            ("drg. Rizky Ananda", "drg. Gigi (Sore)"),
        ],
    },
    "bengkel": {
        "title": "Landing bengkel/otomotif",
        "keywords": ["bengkel", "otomotif", "servis mobil", "servis motor", "oli", "tambal ban", "montir", "cuci mobil", "cuci motor"],
        "brand_anchor": "Garasi 88",
        "phone_display_anchor": "0812-5478-0088",
        "wa_anchor": "6281254780088",
        "sanitize": [
            ("Sejak 2011 di Soekarno Hatta KM 5", "Melayani {area_text}"),
            ("Sejak 2011<br><small>Balikpapan</small>", "Sejak 2011"),
            ("Bengkel motor jujur di Balikpapan sejak 2011.", "Bengkel motor jujur."),
            ("Bengkel motor jujur di Balikpapan. Harga di papan, garansi 7 hari, estimasi gratis.", "Bengkel motor jujur. Estimasi dulu, setuju baru kerja."),
            ("Bengkel motor Balikpapan yang nulis estimasi dulu.", "Bengkel motor yang nulis estimasi dulu."),
            ("Cari papan hijau G88 sebelah SPBU KM 5. Parkir luas.", "Chat WhatsApp kami buat arah lokasi & jadwal."),
            ("Soekarno Hatta KM 5", "{address_line}"),
            ("halo@garasi88.id", "{contact_text}"),
            (">G88<", ">{brand_short}<"),
            ("Balikpapan</span>", "</span>"),
            # Netralisasi garansi spesifik palsu (ACC Kevin 6 Sep)
            ("<b>7 hari</b><span>garansi jasa</span>", "<b>Garansi</b><span>jasa tertulis</span>"),
            ("Jasa bergaransi 7 hari.</p><span class=\"tag\">Garansi 7 hari</span>", "Jasa bergaransi sesuai kesepakatan.</p><span class=\"tag\">Garansi tertulis</span>"),
            ("<summary>Garansi 7 hari ngitungnya?</summary>", "<summary>Garansinya ngitungnya?</summary>"),
            ("Masalah yang sama dalam 7 hari dikerjain ulang tanpa biaya jasa.", "Masalah yang sama dikerjain ulang tanpa biaya jasa, ketentuannya sepakati di awal."),
            ("Langganan keluarga sejak 2019.", "Langganan keluarga kami."),
        ],
    },
    "kontraktor": {
        "title": "Landing kontraktor/konstruksi (default)",
        "keywords": ["kontraktor", "konstruksi", "bangunan", "renovasi", "pembangunan", "material bangunan", "design interior"],
        "brand_anchor": "CV Cipta Griya Kontraktor",
        "phone_display_anchor": "",  # template ini tidak menampilkan nomor teks
        "wa_anchor": "6281256789012",
        "sanitize": [
            (" — Balikpapan</title>", "</title>"),
            ("di Balikpapan & Samarinda sejak 2010. 128 proyek selesai, garansi struktur 5 tahun.", "di kota Anda."),
            ("CV Cipta Griya berdiri di Balikpapan sejak 2010, bergerak", "{brand} bergerak"),
            ("di Kalimantan Timur sejak 2010. Pekerjaan tim internal, angka terbuka, garansi tertulis.", "di kota Anda. Angka terbuka, pengerjaan transparan."),
            ("KONTRAKTOR · BALIKPAPAN", "KONTRAKTOR"),
            ("Punya rencana bangun di Balikpapan atau Samarinda?", "Punya rencana bangun?"),
            ("128 proyek selesai sejak 2010 — rumah, ruko, gudang, sampai renovasi kantor.", "Rumah, ruko, gudang, sampai renovasi kantor."),
            ("Arsip 128 proyek →", "Arsip proyek →"),
            ("Area layanan: Balikpapan · Samarinda · Penajam Paser Utara", "Area layanan: {area_text}"),
            ("tel:+625427655188", "{tel_href}"),
            ("tel:&#43;625427655188", "{tel_href}"),
            ("(0542) 765-5188", "{contact_text}"),
            ("mailto:halo@ciptagriya.co.id", "{wa_href}"),
            ("halo@ciptagriya.co.id", "{contact_text}"),
            (">CG<", ">{brand_short}<"),
            ("Cipta Griya", "{brand}"),
            ("Jl. MT Haryono No. 88, Damai Bahagia,<br>Balikpapan 76114, Kalimantan Timur", "{address_line}"),
            # ── Netralisasi klaim fiktif (ACC Kevin 6 Sep: "eksekusi aja semuanya") ──
            # Nama orang/perusahaan fiktif → label netral
            ("<b>Ibu Ratna</b>", "<b>Rumah 2 lantai</b>"),
            ("<b>PT Bina Logistik Kaltim</b>", "<b>Gudang logistik</b>"),
            ("<b>Ir. Hartono Wijaya</b> — Direktur Operasional, sejak 2012", "— Prinsip kerja tim {brand_short}"),
            # Garansi spesifik palsu → netral (prospek bisa quote ke pelanggannya)
            ("<h3>Garansi 5 Tahun</h3><p>Cacat struktur diperbaiki tanpa biaya. Garansi tertulis di lampiran kontrak.</p>", "<h3>Garansi Tertulis</h3><p>Ketentuan garansi ditulis di lampiran kontrak, mengikuti skope proyek Anda.</p>"),
            # Angka personel fiktif (42)
            ("<b>42</b><span>Personel internal, tersertifikasi SKK</span>", "<b>SKK</b><span>Personel internal tersertifikasi</span>"),
            ("<small>42 personel tersertifikasi konstruksi</small>", "<small>Personel tersertifikasi konstruksi</small>"),
            ("<b>Rekor 0 kecelakaan kerja</b> sejak 2022 — diaudit internal setiap bulan.", "<b>Prosedur K3</b> sama di semua proyek — diaudit internal berkala."),
            # Berita fiktif: nama proyek + klaim jadwal sewa
            ("Topping off Ruko Damai Bahagia tahap II", "Topping off proyek ruko tahap II"),
            ("<h3>Topping off Ruko Damai Bahagia, tahap II</h3>", "<h3>Topping off proyek ruko, tahap II</h3>"),
            ("Struktur 12 unit tahap kedua mencapai atap. Penyewaan dibuka mulai November 2026.", "Struktur tahap kedua mencapai atap — progress proyek berjalan."),
            ("Cara tim kami meratakan adukan dan menyusun bata di proyek Sepinggan.", "Cara tim kami meratakan adukan dan menyusun bata di lapangan."),
            ("<h3>Pelatihan K3 ulang untuk 42 personel</h3>", "<h3>Pelatihan K3 berkala seluruh personel</h3>"),
            # Nama proyek portfolio/hero fiktif + referensi kota template bank → generik
            ("<h1>Struktur Perumahan Balikpapan Baru<br>Tahap II</h1>", "<h1>Struktur Perumahan<br>Tahap II</h1>"),
            ("Rumah Dua Lantai, Sepinggan", "Rumah Dua Lantai"),
            ("Rumah dua lantai Sepinggan", "Rumah dua lantai"),
            ("Ruko Damai Bahagia Balikpapan Kota", "Ruko Dua Lantai"),
            ("<h3>Ruko Damai Bahagia, Tahap I</h3>", "<h3>Ruko Dua Lantai, Tahap I</h3>"),
            ("Gudang Logistik Karang Joang", "Gudang Logistik"),
            ("Gudang logistik Karang Joang", "Gudang logistik"),
            ("Kantor Bina Cakrawala, MT Haryono", "Renovasi Kantor"),
            ("Renovasi kantor Bina Cakrawala", "Renovasi kantor"),
            # Lokasi template bank di stat/hero → netral
            ("Hunian berderet · 32 unit · Balikpapan, Kalimantan Timur", "Hunian berderet · {area_text}"),
            ("Tahun beroperasi di Kalimantan Timur", "Tahun beroperasi"),
        ],
    },
}


# ── Normalisasi nomor ────────────────────────────────────────────────────────
def _digits(phone: str) -> str:
    return re.sub(r"\D", "", phone or "")


def normalize_wa(phone: str) -> str:
    d = _digits(phone)
    if not d:
        return ""
    if d.startswith("0"):
        d = "62" + d[1:]
    elif not d.startswith("62"):
        d = "62" + d
    return d


def format_phone_display(phone: str) -> str:
    """081234567890 → 0812-3456-7890 (4-digit prefix, sisanya dibagi rata).
    11 digit → 0812-345-6789 (pola umum template)."""
    d = _digits(phone)
    if d.startswith("62") and len(d) >= 10:
        d = "0" + d[2:]
    if len(d) < 9:
        return phone or ""
    rest = d[4:]
    mid = len(rest) // 2
    return f"{d[:4]}-{rest[:mid]}-{rest[mid:]}"


# ── Pilih template ───────────────────────────────────────────────────────────
def _brand_short(name: str) -> str:
    """Inisial brand untuk logo/monogram template (mis. 'G88'/'CG' → inisial lead).
    Bukan data baru — turunan langsung dari business_name."""
    words = [w.strip(".,") for w in (name or "").split()]
    letters = [w[0].upper() for w in words if w and w[0].isalpha() and w.upper() not in ("PT", "CV", "UD")]
    return "".join(letters[:4]) or (name or "")[:4].upper()


def select_template_key(lead: Lead, explicit_key: Optional[str] = None) -> str:
    if explicit_key and explicit_key in REGISTRY:
        return explicit_key
    text = f"{lead.product_interest or ''} {lead.business_name or ''}".lower()
    best_key, best_score = "", 0
    for key, meta in REGISTRY.items():
        score = sum(1 for kw in meta["keywords"] if kw in text)
        if score > best_score:
            best_key, best_score = key, score
    return best_key or DEFAULT_TEMPLATE_KEY


# ── Swap engine ──────────────────────────────────────────────────────────────
# Grup 1 = prefix (termasuk kutip pembuka), grup 2 = path, grup 3 = kutip penutup
# + penutup (WAJIB di-emit ulang — kalau hilang, atribut HTML berikutnya rusak).
_ASSET_TAG_RE = re.compile(
    r"""((?:src|href|poster)\s*=\s*["'])([^"']*)(["'])""",
    re.IGNORECASE,
)
_CSS_URL_RE = re.compile(r"""(url\(\s*["']?)([^'")]*)(["']?\s*\))""", re.IGNORECASE)


def _rewrite_asset(match, key: str) -> str:
    prefix, path, suffix = match.group(1), match.group(2), match.group(3)
    low = path.lower()
    if low.startswith(("http://", "https://", "data:", "//", "#", "mailto:", "tel:", "wa.me")):
        return match.group(0)
    if not low.endswith(IMAGE_EXT):
        return match.group(0)
    base = os.path.basename(path)
    return f"{prefix}/uploads/web_preview_assets/{key}/{base}{suffix}"


def _render(template_key: str, lead: Lead) -> str:
    meta = REGISTRY[template_key]
    path = os.path.join(TEMPLATES_DIR, f"{template_key}.html")
    with open(path, encoding="utf-8") as f:
        html = f.read()

    # 1) Nama bisnis — hanya anchor persis (anti-halusinasi)
    brand = lead.business_name or meta["brand_anchor"]
    if meta["brand_anchor"] and meta["brand_anchor"] in html:
        html = html.replace(meta["brand_anchor"], brand)

    # 2) Nomor WA link + nomor tampilan
    wa = normalize_wa(lead.phone_number)
    if wa and meta["wa_anchor"]:
        html = html.replace(f"wa.me/{meta['wa_anchor']}", f"wa.me/{wa}")
    disp = format_phone_display(lead.phone_number)
    if disp and meta.get("phone_display_anchor") and meta["phone_display_anchor"] in html:
        html = html.replace(meta["phone_display_anchor"], disp)

    # 2b) Sanitasi slot FAKTUAL yang masih bawa data sample template (email/tel/
    #     alamat/kota/kode brand) — find = string PERSIS dari file template
    #     (anti-halusinasi), nilai = data lead asli, fallback netral.
    #     CATATAN: klaim marketing sample (harga, "sejak 20xx", jumlah proyek,
    #     nama portfolio/testimoni) sengaja TIDAK diubah di sini — butuh keputusan
    #     konten, bukan swap mekanis (lihat laporan ke Kevin 6 Sep 2026).
    tokens = {
        "brand": brand,
        "brand_short": _brand_short(brand),
        "wa": wa,
        "disp": disp,
        "tel_href": f"tel:+{wa}" if wa else "#",
        "wa_href": f"https://wa.me/{wa}" if wa else "#",
        "contact_text": f"WA {disp}" if disp else brand,
        "address_line": (lead.address or "").strip() or "Lokasi lengkap via WhatsApp",
        "area_text": (lead.address or "").strip() or "kota Anda & sekitarnya",
    }
    for find, repl in meta.get("sanitize", []):
        if find in html:
            html = html.replace(find, repl.format(**tokens))

    # 3) Asset path → /uploads/web_preview_assets/{key}/
    html = _ASSET_TAG_RE.sub(lambda m: _rewrite_asset(m, template_key), html)
    html = _CSS_URL_RE.sub(lambda m: _rewrite_asset(m, template_key), html)
    return html


# ── Public API ───────────────────────────────────────────────────────────────
def generate_preview_for_lead(
    lead: Lead,
    db: Session,
    campaign_id: Optional[str] = None,
    template_key: Optional[str] = None,
    force_new: bool = False,
) -> dict:
    """Generate (atau reuse) web preview untuk lead. Return:
    {slug, template_key, reused}."""
    key = select_template_key(lead, template_key)

    if not force_new:
        existing = (
            db.query(WebPreview)
            .filter(WebPreview.lead_id == lead.id, WebPreview.template_key == key)
            .order_by(WebPreview.id.desc())
            .first()
        )
        if existing:
            return {"slug": existing.slug, "template_key": key, "reused": True}

    html = _render(key, lead)
    preview = WebPreview(
        slug=WebPreview.new_slug(),
        lead_id=lead.id,
        campaign_id=campaign_id,
        template_key=key,
        html=html,
        opened_count=0,
        created_at=datetime.utcnow().isoformat(),
    )
    db.add(preview)
    db.commit()
    return {"slug": preview.slug, "template_key": key, "reused": False}


def preview_public_url(db: Session, slug: str) -> str:
    """URL yang dikirim ke lead — lewat domain frontend (Vercel rewrite
    /wp/:slug → backend). Konsisten dengan pola laporan /r/{slug}."""
    from app.core.services.settings_service import _get_setting

    frontend = _get_setting("frontend_url", FRONTEND_URL) or FRONTEND_URL
    return f"{frontend.rstrip('/')}/wp/{slug}"


def record_open_and_get_html(db: Session, slug: str) -> Optional[str]:
    """Track pembukaan (1x per GET) + return HTML. None kalau slug ga ada."""
    preview = db.query(WebPreview).filter(WebPreview.slug == slug).first()
    if not preview:
        return None
    now = datetime.utcnow().isoformat()
    preview.opened_count = (preview.opened_count or 0) + 1
    if not preview.first_opened_at:
        preview.first_opened_at = now
    preview.last_opened_at = now
    db.add(LeadActivityLog(lead_id=preview.lead_id, activity_type="WEB_PREVIEW_OPENED", created_at=now))
    db.commit()
    return preview.html


def get_preview_info(db: Session, lead_id: int) -> Optional[dict]:
    """Info preview terakhir untuk lead (buat UI detail lead)."""
    p = (
        db.query(WebPreview)
        .filter(WebPreview.lead_id == lead_id)
        .order_by(WebPreview.id.desc())
        .first()
    )
    if not p:
        return None
    return {
        "slug": p.slug,
        "url": preview_public_url(db, p.slug),
        "template_key": p.template_key,
        "opened_count": p.opened_count,
        "first_opened_at": p.first_opened_at,
        "last_opened_at": p.last_opened_at,
        "created_at": p.created_at,
    }
