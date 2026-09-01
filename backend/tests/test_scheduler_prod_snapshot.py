"""Snapshot env prod 30 Agu 08:00 WIB — READ ONLY, bukan deploy.

Live SSH qqwtlphb (password, bukan key):
  ~/backend/.env ENABLE_BACKGROUND_SCHEDULER=false (mtime 28 Agu 17:04)
  sub-flag BLAST/FOLLOWUP/LIFECYCLE/BILLING tidak ada di .env
  flags.py + run_scheduler_worker.py BELUM di server
  stderr.log 0 match APScheduler
  ps: tidak ada process scheduler

Tes ini mengunci: env prod saat ini = worker tidak start.
Kalau Kevin ACC deploy worker, tes ini tetap valid untuk .env web (master OFF).
"""
import os

from app.schedulers.flags import scheduler_plan
from scripts.run_scheduler_worker import probe, start_blocking


def test_prod_env_as_of_20260830_does_not_start(monkeypatch):
    # Mirror .env prod: hanya master=false, sub-flag absen.
    monkeypatch.setenv("ENABLE_BACKGROUND_SCHEDULER", "false")
    for name in (
        "ENABLE_BLAST_SCHEDULER",
        "ENABLE_FOLLOWUP_SCHEDULER",
        "ENABLE_LIFECYCLE_SCHEDULER",
        "ENABLE_BILLING_SCHEDULER",
    ):
        monkeypatch.delenv(name, raising=False)

    plan = scheduler_plan()
    assert plan["master"] is False
    assert plan["jobs"] == []
    assert plan["job_ids"] == []
    assert plan["will_start"] is False
    assert probe() == 0
    assert start_blocking(allow_blast=False) == 0
