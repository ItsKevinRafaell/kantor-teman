"""Scheduler flag plan — default SEMUA OFF.

Master ENABLE_BACKGROUND_SCHEDULER tetap gate global. Tiap job punya flag
sendiri. Blast WAJIB default OFF; worker terpisah menolak blast tanpa
--allow-blast (lihat scripts/run_scheduler_worker.py).

Jangan ubah default di sini tanpa keputusan Kevin.
"""
from __future__ import annotations

import os
from typing import TypedDict


MASTER_FLAG = "ENABLE_BACKGROUND_SCHEDULER"

JOB_FLAGS: dict[str, str] = {
    "blast": "ENABLE_BLAST_SCHEDULER",
    "followup": "ENABLE_FOLLOWUP_SCHEDULER",
    "lifecycle": "ENABLE_LIFECYCLE_SCHEDULER",
    "billing": "ENABLE_BILLING_SCHEDULER",
}

# APScheduler job id per flag. Satu flag bisa >1 job (billing).
# Sumber kebenaran ID — worker + tes wajib pakai ini, jangan hardcode string di 2 tempat.
JOB_SPECS: dict[str, tuple[str, ...]] = {
    "blast": ("pending-blasts",),
    "followup": ("followups",),
    "lifecycle": ("outreach-lifecycle",),
    "billing": ("subscription-deductions", "project-billing-invoices"),
}

# Trigger APScheduler per job id. Sumber kebenaran interval/cron — main.py + worker
# wajib pakai ini, jangan hardcode di 2 tempat.
# trigger: "interval" | "cron"; lalu kwargs ke add_job (minutes/hours ATAU hour/minute).
JOB_TRIGGERS: dict[str, dict] = {
    "pending-blasts": {"trigger": "interval", "minutes": 1},
    "followups": {"trigger": "interval", "hours": 1},
    "outreach-lifecycle": {"trigger": "interval", "hours": 1},
    "subscription-deductions": {"trigger": "cron", "hour": 0, "minute": 5},
    "project-billing-invoices": {"trigger": "cron", "hour": 0, "minute": 15},
}

# First-enable yang AMAN setelah Kevin "deploy" worker (bukan blast, bukan billing
# by-tanggal). Invoice retainer = turunan report final (PLAN-report-invoice).
SAFE_FIRST_ENABLE = "followup"


class SchedulerPlan(TypedDict):
    master: bool
    jobs: list[str]
    job_ids: list[str]
    will_start: bool
    flags: dict[str, bool]


def job_ids_for(jobs: list[str]) -> list[str]:
    """ID APScheduler yang akan di-add untuk daftar flag. Tidak start process."""
    ids: list[str] = []
    for job in jobs:
        ids.extend(JOB_SPECS.get(job, ()))
    return ids


def trigger_kwargs(job_id: str) -> tuple[str, dict]:
    """(trigger, kwargs) untuk add_job. Raise KeyError kalau ID tidak di JOB_TRIGGERS."""
    trig = dict(JOB_TRIGGERS[job_id])
    trigger = trig.pop("trigger")
    return trigger, trig


def flag_on(name: str) -> bool:
    """Env flag helper. Default OFF — job baru NYALA hanya kalau di-set 'true'."""
    return os.getenv(name, "false").strip().lower() == "true"


def scheduler_plan() -> SchedulerPlan:
    """Rencana start scheduler dari env saat ini. Tidak men-start process apa pun."""
    master = flag_on(MASTER_FLAG)
    jobs: list[str] = []
    if master:
        for job, envname in JOB_FLAGS.items():
            if flag_on(envname):
                jobs.append(job)
    flags = {MASTER_FLAG: master}
    flags.update({envname: flag_on(envname) for envname in JOB_FLAGS.values()})
    return {
        "master": master,
        "jobs": jobs,
        "job_ids": job_ids_for(jobs),
        "will_start": bool(jobs),
        "flags": flags,
    }
