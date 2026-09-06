#!/usr/bin/env python3
"""Re-check PageSpeed mingguan untuk lead aktif yang punya website.

Dijalankan sebagai cron TERPISAH (pattern run_scheduler_worker.py): BUKAN di dalam
worker web Passenger, TIDAK menyentuh APScheduler / .env / restart.txt.

Kriteria lead yang dicek:
  - status masih di pipeline aktif (BUKAN Closed/Client, Closed/Lost, Deal,
    Klien Aktif, Selesai)
  - is_archived = 0, deleted_at IS NULL
  - website_url valid (bukan kosong)
  - last_speed_check NULL (belum pernah) ATAU lebih tua dari --stale-days (default 7)

Usage (di server hosting, venv cPanel):
  ~/virtualenv/backend/3.13/bin/python scripts/run_pagespeed_recheck.py --dry-run
  ~/virtualenv/backend/3.13/bin/python scripts/run_pagespeed_recheck.py            # eksekusi
  ~/virtualenv/backend/3.13/bin/python scripts/run_pagespeed_recheck.py --limit 20

Crontab (mingguan, Senin 09:07 WIB, flock anti-tabrakan):
  7 9 * * 1 flock -n /tmp/kt-pagespeed.lock cd /home/qqwtlphb/backend && \
      /home/qqwtlphb/virtualenv/backend/3.13/bin/python scripts/run_pagespeed_recheck.py \
      >> logs/pagespeed_recheck.log 2>&1

Fail-open: error per-lead di-print, TIDAK menghentikan loop; exit code 0 kecuali
fatal (DB ga konek). Rate limit: sleep 1.5s antar call PSI.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
os.chdir(BACKEND_DIR)
sys.path.insert(0, str(BACKEND_DIR))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(BACKEND_DIR / ".env")
load_dotenv(BACKEND_DIR / ".env.local", override=False)


def parse_args():
    p = argparse.ArgumentParser(description="Re-check PageSpeed lead aktif")
    p.add_argument("--dry-run", action="store_true", help="Cetak rencana, tanpa call PSI / tanpa update")
    p.add_argument("--stale-days", type=int, default=7, help="Re-check kalau last_speed_check lebih tua dari N hari (default 7)")
    p.add_argument("--limit", type=int, default=0, help="Batas jumlah lead per run (0 = tanpa batas)")
    p.add_argument("--include-gating", action="store_true", help="Ikutkan web gating (IG/Linktree) — default skip karena skor PSI sering 4xx")
    return p.parse_args()


def main() -> int:
    args = parse_args()

    from models import SessionLocal, Lead  # noqa: E402  (setelah chdir + dotenv)
    from app.constants import LeadStatus  # noqa: E402
    from app.services.pagespeed_service import (  # noqa: E402
        is_gating_web,
        normalize_website_url,
        resolve_api_key,
        run_speed_check,
    )

    excluded = {
        LeadStatus.CLOSED_CLIENT, LeadStatus.CLOSED_LOST,
        LeadStatus.DEAL, LeadStatus.ACTIVE_CLIENT, LeadStatus.COMPLETED,
    }
    stale_cutoff = (datetime.now(timezone.utc) - timedelta(days=args.stale_days)).strftime("%Y-%m-%d %H:%M:%S")

    db = SessionLocal()
    try:
        rows = (
            db.query(Lead)
            .filter(
                Lead.status.notin_(excluded),
                Lead.is_archived.is_(False),
                Lead.deleted_at.is_(None),
                Lead.website_url.isnot(None),
                Lead.website_url != "",
            )
            .all()
        )
        candidates = []
        for lead in rows:
            if not normalize_website_url(lead.website_url):
                continue
            if not args.include_gating and is_gating_web(lead.website_url):
                continue
            checked = lead.last_speed_check or ""
            if checked and checked >= stale_cutoff:
                continue  # masih fresh
            candidates.append(lead)
        if args.limit and len(candidates) > args.limit:
            candidates = candidates[: args.limit]

        plan = {
            "run_at": datetime.now(timezone(timedelta(hours=7))).isoformat(),
            "mode": "dry-run" if args.dry_run else "execute",
            "stale_days": args.stale_days,
            "total_web_leads": len(rows),
            "to_check": [l.id for l in candidates],
        }
        print(json.dumps(plan, ensure_ascii=False))
        if args.dry_run:
            return 0

        api_key = resolve_api_key(os.getenv("GOOGLE_API_KEY", ""))
        checked, failed, skipped = 0, 0, 0
        for lead in candidates:
            result = run_speed_check(lead, db, api_key=api_key)
            if result["error"]:
                failed += 1
                print(f"[pagespeed-recheck] lead={lead.id} gagal: {result['error']}", flush=True)
                if "rate limited" in (result["error"] or ""):
                    time.sleep(10)
            else:
                checked += 1
                print(f"[pagespeed-recheck] lead={lead.id} skor={result['page_speed_score']}", flush=True)
            time.sleep(1.5)  # rate limit PSI

        summary = {"checked": checked, "failed": failed, "skipped": len(candidates) - checked - failed}
        print("[pagespeed-recheck] summary " + json.dumps(summary))
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except SystemExit:
        raise
    except Exception as exc:  # fatal — biar cron log keliatan
        print(f"[pagespeed-recheck] FATAL: {str(exc)[:300]}", flush=True)
        raise SystemExit(1)
