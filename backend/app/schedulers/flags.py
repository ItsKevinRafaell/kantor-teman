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


class SchedulerPlan(TypedDict):
    master: bool
    jobs: list[str]
    will_start: bool
    flags: dict[str, bool]


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
        "will_start": bool(jobs),
        "flags": flags,
    }
