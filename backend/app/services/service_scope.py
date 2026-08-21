"""Service-scope resolver (Opsi B — product-driven, Tahap 3 logika).

SUMBER KEBENARAN untuk "apakah project ini termasuk Google Maps / GBP dalam
scope layanannya". Sebelumnya scope Maps di-HARDCODE dari asumsi
``service_type == "seo_gmaps"`` selalu punya Maps. Itu salah untuk paket
seperti **SEO Pro** (klien MLS) yang MURNI SEO tanpa Maps/GBP.

Sekarang scope dibaca dari (urutan prioritas):
1. Relasi ``project -> product`` (nama product katalog, mis. "SEO + Google Maps").
2. Tabel ``project_addons`` (add-on Maps/GBP yang menempel pada project).
3. Data GBP aktual (kalau report benar-benar punya angka Google Business).

Kalau ketiganya tidak menunjukkan Maps, project dianggap SEO-only (TANPA Maps).
``service_type`` string TIDAK lagi dipakai untuk memutuskan Maps — ia jadi
turunan/deprecated (hanya penanda kategori layanan, bukan sumber scope Maps).

Fungsi di modul ini murni (tidak menyentuh DB tulis) dan defensif terhadap
project lama yang belum punya product_id / addons (return False = tanpa Maps,
kecuali ada data GBP aktual).
"""

from __future__ import annotations

from typing import Any, Optional

# Kata kunci yang menandakan sebuah nama layanan/add-on mencakup Google Maps / GBP.
# Sengaja spesifik ke "maps"/"gmaps"/"google business"/"gbp" — TIDAK memicu pada
# kata "seo" saja, supaya "SEO Pro" / "SEO Starter" / "SEO Expert" TIDAK dianggap
# punya Maps.
_MAPS_KEYWORDS = (
    "google maps",
    "gmaps",
    "g-maps",
    "google business",
    "google bisnis",
    "gbp",
    "gmb",
    "maps",
    "google my business",
)


def _text_indicates_maps(text: Optional[str]) -> bool:
    if not text:
        return False
    low = str(text).lower()
    return any(kw in low for kw in _MAPS_KEYWORDS)


def _gbp_data_present(service_metrics: Optional[dict]) -> bool:
    """True kalau ada data Google Business aktual (bukan kosong/'-')."""
    if not service_metrics:
        return False
    gbp = (service_metrics.get("google_business") or {}) if isinstance(service_metrics, dict) else {}
    if not isinstance(gbp, dict):
        return False
    return any(v not in (None, "", "-", 0, "0") for v in gbp.values())


def product_indicates_maps(product: Any) -> bool:
    """Cek nama/deskripsi product katalog untuk indikasi Maps/GBP."""
    if product is None:
        return False
    name = getattr(product, "name", None)
    desc = getattr(product, "description", None)
    return _text_indicates_maps(name) or _text_indicates_maps(desc)


def addons_indicate_maps(addons: Any) -> bool:
    """Cek daftar ProjectAddon: ada add-on Maps/GBP?"""
    if not addons:
        return False
    for addon in addons:
        name = getattr(addon, "name", None)
        desc = getattr(addon, "description", None)
        if _text_indicates_maps(name) or _text_indicates_maps(desc):
            return True
        # Add-on yang berasal dari katalog product juga dicek namanya.
        if product_indicates_maps(getattr(addon, "product", None)):
            return True
    return False


def project_has_maps(project: Any, service_metrics: Optional[dict] = None) -> bool:
    """Apakah project ini termasuk Google Maps / GBP dalam scope layanannya?

    Prioritas: product -> add-on -> data GBP aktual. TIDAK pakai service_type.

    Args:
        project: instance Project (boleh None). Diharap punya ``.product`` dan
            ``.addons`` (relasi Tahap 1). Aman kalau relasi belum ada.
        service_metrics: dict metrik service dari report (opsional). Dipakai
            sebagai fallback: kalau ada data GBP nyata, Maps dianggap in-scope
            meski product/addon belum ter-set (project lama / data historis).

    Returns:
        bool — True kalau Maps/GBP harus ditampilkan.
    """
    if project is not None:
        if product_indicates_maps(getattr(project, "product", None)):
            return True
        if addons_indicate_maps(getattr(project, "addons", None)):
            return True
    # Fallback terakhir: data GBP aktual (kompat project lama tanpa product/addon).
    if _gbp_data_present(service_metrics):
        return True
    return False


def resolve_service_label(
    project: Any,
    service_type: Optional[str],
    base_labels: Optional[dict] = None,
    service_metrics: Optional[dict] = None,
) -> str:
    """Label layanan yang JUJUR soal Maps.

    - Kalau product/addon/data menunjukkan Maps -> "SEO & Google Maps".
    - Kalau tidak -> "SEO" (untuk kategori SEO) atau label dasar per service_type.

    base_labels: mapping service_type -> label default (mis. REPORT_SERVICE_LABELS).
    """
    base_labels = base_labels or {}
    st = (service_type or "").lower()
    has_maps = project_has_maps(project, service_metrics)

    # Kategori SEO: label bergantung ada/tidaknya Maps.
    if st in ("seo", "seo_gmaps", "seo_pro", "seo_only") or ("seo" in st and "web" not in st):
        return "SEO & Google Maps" if has_maps else "SEO"

    # Non-SEO: pakai label dasar apa adanya.
    return base_labels.get(service_type, service_type or "layanan")
