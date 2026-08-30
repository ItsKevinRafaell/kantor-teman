#!/usr/bin/env python3
"""Dedicated scheduler worker — BUKAN di dalam worker web Passenger.

Kenapa terpisah:
  PRODUCTION.md: di shared hosting, biarkan ENABLE_BACKGROUND_SCHEDULER=false
  pada proses web supaya tiap LSAPI worker tidak menjalankan APScheduler.
  Scheduler hanya boleh hidup di process khusus ini.

Kenapa --enable (process-local):
  Snapshot prod 30 Agu: .env Passenger cuma master=false, sub-flag absen.
  Kalau worker cuma baca .env itu, file worker yang di-deploy tetap no-op.
  --enable Nyalain job HANYA di process ini (os.environ), TIDAK menulis .env.
  Blast tetap ditolak tanpa --allow-blast.

Default AMAN:
  - Semua flag OFF → worker exit 0, tidak start job.
  - Blast ditolak kecuali --allow-blast (Kevin harus eksplisit).
  - --probe / --dry-run hanya cetak rencana (JSON) + exit. Tidak connect DB, tidak start job.

Usage (lokal / process terpisah, BUKAN deploy otomatis):
  python3 scripts/run_scheduler_worker.py --probe
  python3 scripts/run_scheduler_worker.py --safe-first --dry-run
  python3 scripts/run_scheduler_worker.py --safe-first
  python3 scripts/run_scheduler_worker.py --safe-first --once   # run 1x lalu exit (buat crontab)
  python3 scripts/run_scheduler_worker.py --enable followup   # sama dengan --safe-first
  python3 scripts/run_scheduler_worker.py --allow-blast   # HANYA kalau Kevin ACC blast

DILARANG: jalankan ini di prod tanpa Kevin nulis "deploy" / "nyalain".
DILARANG: edit .env Passenger / touch tmp/restart.txt dari script ini.
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

from app.schedulers.flags import (  # noqa: E402
    JOB_FLAGS,
    JOB_SPECS,
    MASTER_FLAG,
    SAFE_FIRST_ENABLE,
    SchedulerPlan,
    scheduler_plan,
    trigger_kwargs,
)

ALLOWED_ENABLE = frozenset(JOB_FLAGS.keys())  # blast, followup, lifecycle, billing


def _print_plan(plan: "SchedulerPlan | dict") -> None:
    print(json.dumps(plan, indent=2, sort_keys=True), flush=True)


def apply_process_enables(jobs: list[str]) -> None:
    """Nyalain master + sub-flag HANYA di process ini. Tidak tulis file .env.

    Exclusive: job yang tidak disebut di --enable di-set false di process ini
    supaya blast tidak bocor dari env kotor / tes sebelumnya.
    """
    if not jobs:
        return
    os.environ[MASTER_FLAG] = "true"
    wanted = set(jobs)
    for job, envname in JOB_FLAGS.items():
        os.environ[envname] = "true" if job in wanted else "false"


def parse_enable(raw: str | None) -> list[str]:
    if not raw:
        return []
    jobs: list[str] = []
    for part in raw.split(","):
        name = part.strip().lower()
        if not name:
            continue
        if name not in ALLOWED_ENABLE:
            raise ValueError(
                f"job tidak dikenal: {name!r}. boleh: {', '.join(sorted(ALLOWED_ENABLE))}"
            )
        if name not in jobs:
            jobs.append(name)
    return jobs


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


def _job_runners(kt_main) -> dict:
    """Map job_id -> (fn, args) — SATU sumber, dipakai start_blocking & run_once.

    Semantik panggil = persis add_job(fn, trigger, args=[...]): fn(*args),
    atau fn() kalau args None. Jangan duplikasi map ini di 2 tempat.
    """
    return {
        "pending-blasts": (kt_main._run_async_job, [kt_main.process_pending_blasts]),
        "followups": (kt_main._run_async_job, [kt_main.scheduled_followup_processor]),
        "outreach-lifecycle": (kt_main._run_outreach_lifecycle, None),
        "subscription-deductions": (kt_main._run_subscription_deductions, None),
        "project-billing-invoices": (kt_main._run_project_billing_invoices, None),
    }


def run_once(*, allow_blast: bool, dry_run: bool = False) -> int:
    """Jalanin job yang di-enable SEKALI lalu exit. Mode buat crontab shared hosting.

    Kenapa ada: BlockingScheduler = process infinite, dan job interval APScheduler
    fire pertama di now+interval — process yang dibunuh cron/timeout sebelum itu
    fire 0x. --once memanggil runner langsung (tanpa APScheduler, tanpa daemon),
    jadi crontab `flock -n ... --once` per interval aman & tidak overlap.
    Blast tetap DITOLAK tanpa --allow-blast, sama seperti start_blocking.
    """
    plan = scheduler_plan()
    _print_plan(plan)
    if "blast" in plan["jobs"] and not allow_blast:
        print(
            "[SCHEDULER] REFUSE: ENABLE_BLAST_SCHEDULER=true tapi --allow-blast tidak ada. "
            "Blast tetap OFF. Tidak jalan sekali pun.",
            flush=True,
        )
        return 3
    if not plan["will_start"]:
        print(
            "[SCHEDULER] once: tidak ada job enable (master OFF / semua sub-flag OFF).",
            flush=True,
        )
        return 0
    ids = ",".join(plan["job_ids"])
    if dry_run:
        print(
            f"[SCHEDULER] once dry-run: would run jobs={','.join(plan['jobs'])} "
            f"job_ids={ids} — tidak import main, tidak sentuh DB.",
            flush=True,
        )
        return 0

    # Import job runners hanya saat benar-benar jalan — dry-run tidak nyentuh DB.
    import main as kt_main  # noqa: WPS433

    runners = _job_runners(kt_main)
    for job in plan["jobs"]:
        for jid in JOB_SPECS[job]:
            fn, args = runners[jid]
            print(f"[SCHEDULER] once: run {jid} ...", flush=True)
            if args is None:
                fn()
            else:
                fn(*args)
    print(
        f"[SCHEDULER] once selesai: jobs={','.join(plan['jobs'])} job_ids={ids}",
        flush=True,
    )
    return 0


def start_blocking(*, allow_blast: bool, dry_run: bool = False) -> int:
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

    if dry_run:
        ids = ",".join(plan["job_ids"])
        print(
            f"[SCHEDULER] dry-run: would start jobs={','.join(plan['jobs'])} "
            f"job_ids={ids} — tidak start BlockingScheduler.",
            flush=True,
        )
        return 0

    # Import job runners hanya saat benar-benar start — probe/dry-run tidak nyentuh DB.
    import main as kt_main  # noqa: WPS433

    from apscheduler.schedulers.blocking import BlockingScheduler

    sched = BlockingScheduler(timezone="Asia/Jakarta")
    enabled = plan["jobs"]
    runners = _job_runners(kt_main)
    for job in enabled:
        for jid in JOB_SPECS[job]:
            trigger, trig = trigger_kwargs(jid)
            fn, args = runners[jid]
            kw = dict(id=jid, max_instances=1, coalesce=True, **trig)
            if args is not None:
                kw["args"] = args
            sched.add_job(fn, trigger, **kw)

    print(
        f"[SCHEDULER] worker started, jobs aktif: {', '.join(enabled)} "
        f"job_ids={','.join(plan['job_ids'])}",
        flush=True,
    )
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
        "--dry-run",
        action="store_true",
        help="Sama seperti start tapi berhenti sebelum BlockingScheduler. Tidak sentuh DB.",
    )
    parser.add_argument(
        "--enable",
        metavar="JOBS",
        help=(
            "Nyalain job process-local (koma): followup,lifecycle,billing,blast. "
            "Set env HANYA di process ini. Tidak tulis .env. Blast tetap butuh --allow-blast. "
            "First-enable AMAN = followup (lihat --safe-first), bukan billing."
        ),
    )
    parser.add_argument(
        "--safe-first",
        action="store_true",
        help=(
            f"Alias first-enable AMAN: sama dengan --enable {SAFE_FIRST_ENABLE}. "
            "Bukan blast, bukan billing by-tanggal. Tidak tulis .env."
        ),
    )
    parser.add_argument(
        "--allow-blast",
        action="store_true",
        help="Izinkan job blast. Default TOLAK meski env-nya true. Butuh ACC Kevin.",
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help=(
            "Jalanin job yang di-enable SEKALI lalu exit (tanpa BlockingScheduler). "
            "Buat crontab shared hosting: flock -n ... run_scheduler_worker.py "
            "--safe-first --once >> scheduler.log 2>&1. --probe menang kalau digabung."
        ),
    )
    args = parser.parse_args(argv)
    try:
        enables = parse_enable(args.enable)
    except ValueError as exc:
        print(f"[SCHEDULER] REFUSE: {exc}", flush=True)
        return 2
    if args.safe_first:
        if enables and enables != [SAFE_FIRST_ENABLE]:
            print(
                f"[SCHEDULER] REFUSE: --safe-first tidak boleh dicampur job lain "
                f"(dapat {enables!r}). Pakai --enable {SAFE_FIRST_ENABLE} saja.",
                flush=True,
            )
            return 2
        enables = [SAFE_FIRST_ENABLE]
    apply_process_enables(enables)
    if args.probe:
        return probe()
    if args.once:
        return run_once(allow_blast=args.allow_blast, dry_run=args.dry_run)
    return start_blocking(allow_blast=args.allow_blast, dry_run=args.dry_run)


if __name__ == "__main__":
    raise SystemExit(main())
