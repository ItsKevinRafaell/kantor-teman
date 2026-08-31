#!/usr/bin/env python3
"""Dedicated scheduler worker — BUKAN di dalam worker web Passenger.

Kenapa terpisah:
  PRODUCTION.md: di shared hosting, biarkan ENABLE_BACKGROUND_SCHEDULER=false
  pada proses web supaya tiap LSAPI worker tidak menjalankan APScheduler.
  Scheduler hanya boleh hidup di process khusus ini.

Default AMAN:
  - Semua flag OFF → worker exit 0, tidak start job.
  - Blast ditolak kecuali --allow-blast (Kevin harus eksplisit).
  - --probe hanya cetak rencana (JSON) + exit. Tidak connect DB, tidak start job.

Usage (lokal / process terpisah, BUKAN deploy otomatis):
  python3 scripts/run_scheduler_worker.py --probe
  python3 scripts/run_scheduler_worker.py            # BlockingScheduler, sub-flag ON saja
  python3 scripts/run_scheduler_worker.py --allow-blast   # HANYA kalau Kevin ACC blast

DILARANG: jalankan ini di prod tanpa Kevin nulis "deploy" / "nyalain".
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
os.chdir(BACKEND_DIR)
sys.path.insert(0, str(BACKEND_DIR))

from dotenv import load_dotenv  # noqa: E402

_env_file = os.environ.get("ENV_FILE", ".env")
load_dotenv(_env_file)
load_dotenv(BACKEND_DIR / ".env", override=False)

from app.schedulers.flags import scheduler_plan  # noqa: E402


def _print_plan(plan: dict) -> None:
    print(json.dumps(plan, indent=2, sort_keys=True), flush=True)


def probe() -> int:
    plan = scheduler_plan()
    _print_plan(plan)
    if not plan["master"]:
        print("[SCHEDULER] probe: master OFF — worker tidak akan start.", flush=True)
        return 0
    if not plan["will_start"]:
        print("[SCHEDULER] probe: master ON tapi semua sub-flag OFF — tidak start.", flush=True)
        return 0
    print(f"[SCHEDULER] probe: would start jobs={','.join(plan['jobs'])}", flush=True)
    return 0


def start_blocking(*, allow_blast: bool) -> int:
    plan = scheduler_plan()
    _print_plan(plan)

    if "blast" in plan["jobs"] and not allow_blast:
        print(
            "[SCHEDULER] REFUSE: ENABLE_BLAST_SCHEDULER=true tapi --allow-blast tidak ada. "
            "Blast tetap OFF. Tidak start worker.",
            flush=True,
        )
        return 3

    if not plan["will_start"]:
        print("[SCHEDULER] tidak start (master OFF atau semua sub-flag OFF).", flush=True)
        return 0

    # Import job runners hanya saat benar-benar start — probe tidak nyentuh DB.
    import main as kt_main  # noqa: WPS433

    from apscheduler.schedulers.blocking import BlockingScheduler

    sched = BlockingScheduler(timezone="Asia/Jakarta")
    enabled = plan["jobs"]

    if "blast" in enabled:
        sched.add_job(
            kt_main._run_async_job,
            "interval",
            minutes=1,
            args=[kt_main.process_pending_blasts],
            id="pending-blasts",
            max_instances=1,
            coalesce=True,
        )
    if "followup" in enabled:
        sched.add_job(
            kt_main._run_async_job,
            "interval",
            hours=1,
            args=[kt_main.scheduled_followup_processor],
            id="followups",
            max_instances=1,
            coalesce=True,
        )
    if "lifecycle" in enabled:
        sched.add_job(
            kt_main._run_outreach_lifecycle,
            "interval",
            hours=1,
            id="outreach-lifecycle",
            max_instances=1,
            coalesce=True,
        )
    if "billing" in enabled:
        sched.add_job(
            kt_main._run_subscription_deductions,
            "cron",
            hour=0,
            minute=5,
            id="subscription-deductions",
            max_instances=1,
            coalesce=True,
        )
        sched.add_job(
            kt_main._run_project_billing_invoices,
            "cron",
            hour=0,
            minute=15,
            id="project-billing-invoices",
            max_instances=1,
            coalesce=True,
        )

    print(f"[SCHEDULER] worker started, jobs aktif: {', '.join(enabled)}", flush=True)
    sched.start()
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="KantorTeman dedicated scheduler worker")
    parser.add_argument(
        "--probe",
        action="store_true",
        help="Cetak rencana flag (JSON) lalu exit. Tidak start job, tidak sentuh DB.",
    )
    parser.add_argument(
        "--allow-blast",
        action="store_true",
        help="Izinkan job blast. Default TOLAK meski env-nya true. Butuh ACC Kevin.",
    )
    args = parser.parse_args(argv)
    if args.probe:
        return probe()
    return start_blocking(allow_blast=args.allow_blast)


if __name__ == "__main__":
    raise SystemExit(main())
