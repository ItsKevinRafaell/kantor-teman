"""PageSpeed Insights service — skor kecepatan web lead.

Sumber skor: Google PageSpeed Insights API v5 (gratis).
  GET https://www.googleapis.com/pagespeedonline/v5/runPagespeed?url=...&strategy=mobile[&key=...]

Key resolution: env PAGESPEED_API_KEY dulu; kalau kosong, caller boleh kirim
GOOGLE_API_KEY (PSI bisa pakai key Google API yang sama); kalau dua-duanya kosong,
call tetap jalan tanpa key (quota per-IP, cukup untuk volume mingguan lead kecil).

Fail-open: SEMUA error → return error string, TIDAK pernah raise ke caller produksi
(hook create/scrape/cron tidak boleh gagal karena PSI down).

"Web gating" = website_url yang bukan web beneran (IG, Linktree, wa.me, shortlink).
Lead semacam ini dianggap "belum punya web" untuk prioritas WA.
"""
from __future__ import annotations

import os
from datetime import datetime, timezone, timedelta
from typing import Optional, Tuple
from urllib.parse import urlsplit

import httpx

PSI_ENDPOINT = "https://www.googleapis.com/pagespeedonline/v5/runPagespeed"
PSI_TIMEOUT = 45.0

# Skor di bawah ini = "web lemot" (indikasi pain → prioritas outreach).
HOT_LIST_SCORE_MAX = 60

# Host yang dianggap BUKAN web bisnis (bio-link / sosmed / shortlink / chat).
GATING_WEB_HOSTS = (
    "instagram.com", "instagr.am",
    "facebook.com", "fb.me", "fb.com",
    "tiktok.com",
    "youtube.com", "youtu.be",
    "linkedin.com",
    "linktr.ee", "linkbio.co", "bio.link", "beacons.ai", "taplink.cc",
    "s.id", "bit.ly", "tinyurl.com", "cutt.ly", "shorturl.at", "tr.ee",
    "wa.me", "api.whatsapp.com", "chat.whatsapp.com",
    "heylink.me", "lit.link", "snipfeed.co", "karyakarsa.com",
    "shopee.co.id", "shopee.co", "tokopedia.com", "tokopedia.link",
    "bukalapak.com", "lazada.co.id",
    "google.com", "maps.app.goo.gl", "goo.gl", "business.site",
)


def normalize_website_url(url: Optional[str]) -> Optional[str]:
    """Kembalikan URL dengan scheme; None kalau kosong/ga valid."""
    if not url or not str(url).strip():
        return None
    url = str(url).strip()
    if not url.lower().startswith(("http://", "https://")):
        url = "https://" + url
    try:
        parts = urlsplit(url)
        if not parts.netloc or "." not in parts.netloc:
            return None
    except ValueError:
        return None
    return url


def is_gating_web(url: Optional[str]) -> bool:
    """True kalau website_url cuma IG/Linktree/shortlink/wa.me dsb."""
    normalized = normalize_website_url(url)
    if not normalized:
        return False
    host = (urlsplit(normalized).netloc or "").lower()
    host = host.removeprefix("www.")
    return any(host == g or host.endswith("." + g) or g in host for g in GATING_WEB_HOSTS)


def resolve_api_key(fallback: str = "") -> str:
    return (os.getenv("PAGESPEED_API_KEY") or fallback or "").strip()


def fetch_pagespeed_score(
    url: str,
    api_key: str = "",
    strategy: str = "mobile",
    timeout: float = PSI_TIMEOUT,
) -> Tuple[Optional[int], Optional[str]]:
    """Call PSI v5 → (skor 0-100, None) atau (None, pesan_error)."""
    normalized = normalize_website_url(url)
    if not normalized:
        return None, "website_url tidak valid"
    params = {"url": normalized, "strategy": strategy}
    if api_key:
        params["key"] = api_key
    try:
        resp = httpx.get(PSI_ENDPOINT, params=params, timeout=timeout)
    except httpx.HTTPError as exc:
        return None, f"PSI request gagal: {str(exc)[:160]}"
    if resp.status_code == 429:
        return None, "PSI rate limited (429)"
    if resp.status_code != 200:
        detail = ""
        try:
            detail = str(resp.json().get("error", {}).get("message", ""))[:160]
        except Exception:
            detail = resp.text[:160]
        return None, f"PSI HTTP {resp.status_code}: {detail}"
    try:
        data = resp.json()
        perf = data["lighthouseResult"]["categories"]["performance"]
        score = perf.get("score")
        if score is None:
            return None, "PSI sukses tapi skor performance kosong"
        return int(round(float(score) * 100)), None
    except (KeyError, TypeError, ValueError) as exc:
        return None, f"PSI respons tidak terbaca: {str(exc)[:160]}"


def _now_wib() -> str:
    return datetime.now(timezone(timedelta(hours=7))).strftime("%Y-%m-%d %H:%M:%S")


def run_speed_check(lead, db, api_key: str = "") -> dict:
    """Jalankan PSI untuk 1 lead (objek model) + simpan skor. Fail-open.

    Return dict: {website_url, gating, page_speed_score, last_speed_check, error}
    Skor/last_speed_check hanya di-update kalau fetch sukses (None error).
    """
    result = {
        "lead_id": getattr(lead, "id", None),
        "website_url": lead.website_url,
        "gating": is_gating_web(lead.website_url),
        "page_speed_score": getattr(lead, "page_speed_score", None),
        "last_speed_check": getattr(lead, "last_speed_check", None),
        "error": None,
    }
    normalized = normalize_website_url(lead.website_url)
    if not normalized:
        result["error"] = "lead tidak punya website_url valid"
        return result
    score, err = fetch_pagespeed_score(normalized, api_key=api_key)
    if err:
        result["error"] = err
        return result
    lead.page_speed_score = score
    lead.last_speed_check = _now_wib()
    db.commit()
    result["page_speed_score"] = score
    result["last_speed_check"] = lead.last_speed_check
    return result


def run_speed_check_bg(db_url: str, lead_id: int, api_key: str = "") -> None:
    """Background task: session sendiri, fail-open total (print log saja).

    Dipanggil dari BackgroundTasks di router saat lead dibuat/scraped dengan web.
    """
    try:
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker
        from models.lead import Lead

        engine = create_engine(db_url)
        SessionBg = sessionmaker(bind=engine)
        db = SessionBg()
        try:
            lead = db.query(Lead).filter(Lead.id == lead_id).first()
            if lead is None:
                return
            result = run_speed_check(lead, db, api_key=api_key)
            if result["error"]:
                print(f"[pagespeed] lead={lead_id} gagal: {result['error']}", flush=True)
            else:
                print(f"[pagespeed] lead={lead_id} skor={result['page_speed_score']}", flush=True)
        finally:
            db.close()
            engine.dispose()
    except Exception as exc:  # fail-open: jangan bikin request/error log bermasalah
        print(f"[pagespeed] lead={lead_id} background gagal: {str(exc)[:160]}", flush=True)
