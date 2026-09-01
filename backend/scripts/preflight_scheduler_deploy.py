#!/usr/bin/env python3
"""Preflight validator go-live scheduler prod Kantor Teman.

Tujuan: saat Kevin menulis "deploy", SEMUA pre-check jalan 1 command — tanpa
typo crontab, tanpa lupa file, tanpa salah urutan. Read-only penuh:
  - Lokal: cek branch/branch-file/konsistensi import + dry-run merge ke main
    di temp worktree (dihapus setelahnya).
  - Remote: SSH deploy-kantorteman HANYA cat/ls/crontab -l (zero mutasi).
  - Health API via HTTPS dari mesin ini.

TIDAK: edit .env, restart Passenger, rsync, tulis crontab. Itu tugas runbook
di PRODUCTION.md § "Runbook Go-Live Scheduler Prod" dan butuh Kevin "deploy".

Pemakaian:
  python3 scripts/preflight_scheduler_deploy.py            # lokal saja
  python3 scripts/preflight_scheduler_deploy.py --remote   # lokal + SSH read-only
  python3 scripts/preflight_scheduler_deploy.py --tests    # + suite scheduler & e2e lifecycle

Exit: 0 = siap deploy (menunggu kata "deploy"), 1 = ada FAIL.
"""
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import tempfile
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]  # .../kantorteman
BACKEND = REPO / "backend"
CANON_BRANCH = "feat/raka-e2e-scheduler-enable"
SSH_HOST = "deploy-kantorteman"
VENV_PY = "/home/qqwtlphb/virtualenv/backend/3.13/bin/python"
HEALTH_URL = "https://api.kantorteman.my.id/api/health"
CRONTAB_LINE = (
    "20 * * * * flock -n /tmp/kt-sched.lock "
    f"{VENV_PY} /home/qqwtlphb/backend/scripts/run_scheduler_worker.py "
    "--safe-first --once >> /home/qqwtlphb/backend/scheduler-worker.log 2>&1"
)
REQUIRED_FILES = [
    BACKEND / "main.py",
    BACKEND / "app" / "schedulers" / "flags.py",
    BACKEND / "scripts" / "run_scheduler_worker.py",
    BACKEND / "scripts" / "__init__.py",
]
WORKER_FLAGS = ["--once", "--safe-first", "--allow-blast", "--probe"]

results: list[tuple[str, str, str]] = []  # (status, cek, detail)


def rec(status: str, cek: str, detail: str = "") -> None:
    results.append((status, cek, detail))
    mark = {"PASS": "[PASS]", "FAIL": "[FAIL]", "WARN": "[WARN]", "INFO": "[INFO]"}[status]
    line = f"{mark} {cek}"
    if detail:
        line += f" — {detail}"
    print(line, flush=True)


def run(cmd: list[str], cwd: Path | None = None, timeout: int = 60) -> tuple[int, str]:
    try:
        p = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout)
        return p.returncode, (p.stdout + p.stderr).strip()
    except FileNotFoundError:
        return 127, f"binary tidak ada: {cmd[0]}"
    except subprocess.TimeoutExpired:
        return 124, "timeout"


def git(*args: str) -> tuple[int, str]:
    return run(["git", *args], cwd=REPO)


def check_local() -> None:
    rc, branch = git("branch", "--show-current")
    if rc != 0:
        rec("FAIL", "git branch", branch)
        return
    rec("PASS" if branch == CANON_BRANCH else "WARN",
        "branch", branch or "(detached)")

    rc, out = git("status", "--porcelain")
    rec("PASS" if (rc == 0 and not out) else "WARN",
        "worktree bersih", "ada perubahan belum commit" if out else "bersih")

    missing = [str(f.relative_to(REPO)) for f in REQUIRED_FILES if not f.is_file()]
    rec("PASS" if not missing else "FAIL",
        "file wajib deploy ada", "semua ada" if not missing else f"hilang: {missing}")

    main_py = (BACKEND / "main.py").read_text(errors="replace")
    ok_import = "app.schedulers.flags" in main_py or "from app.schedulers import flags" in main_py
    rec("PASS" if ok_import else "FAIL",
        "main.py import flags",
        "konsisten (deploy 3 file sekaligus WAJIB — jangan --all saja)" if ok_import
        else "tidak import flags → deploy parsial aman tapi verifikasi manual")

    worker = (BACKEND / "scripts" / "run_scheduler_worker.py").read_text(errors="replace")
    hilang = [f for f in WORKER_FLAGS if f not in worker]
    rec("PASS" if not hilang else "FAIL",
        "worker punya flag kanonis", "semua ada" if not hilang else f"hilang: {hilang}")

    prod_md = (REPO / "PRODUCTION.md").read_text(errors="replace")
    ok_runbook = "Runbook Go-Live Scheduler Prod" in prod_md and "crontab" in prod_md and "--once" in prod_md
    rec("PASS" if ok_runbook else "FAIL",
        "runbook kanonis di PRODUCTION.md",
        "ada (crontab --once + --safe-first)" if ok_runbook else "section runbook hilang/tidak kanonik")

    # Dry-run merge ke main di temp worktree — tanpa menyentuh repo utama.
    rc_m, out_m = git("rev-parse", "--verify", "main")
    if rc_m != 0:
        rec("WARN", "branch main", out_m)
        return
    tmp = tempfile.mkdtemp(prefix="kt-merge-test-")
    try:
        rc1, o1 = git("worktree", "add", "--detach", tmp, "main")
        if rc1 != 0:
            rec("FAIL", "dry-run merge: worktree", o1)
            return
        rc2, o2 = run(["git", "merge", "--no-commit", "--no-ff", CANON_BRANCH], cwd=Path(tmp))
        if rc2 == 0:
            rec("PASS", "dry-run merge ke main", "clean, tanpa konflik")
        else:
            rec("FAIL", "dry-run merge ke main", f"KONFLIK/perlu resolve: {o2[:300]}")
    finally:
        run(["git", "merge", "--abort"], cwd=Path(tmp))
        run(["git", "worktree", "remove", "--force", tmp], cwd=REPO)
        shutil.rmtree(tmp, ignore_errors=True)


def check_remote() -> None:
    ssh = ["ssh", "-o", "ConnectTimeout=15", "-o", "BatchMode=yes", SSH_HOST]
    rc, out = run(
        ssh + [
            "grep -c '^ENABLE_BACKGROUND_SCHEDULER=false' ~/backend/.env 2>/dev/null; "
            "echo ---; ls ~/backend/app/schedulers/flags.py 2>/dev/null || echo ABSENT_FLAGS; "
            "echo ---; ls ~/backend/scripts/run_scheduler_worker.py 2>/dev/null || echo ABSENT_WORKER; "
            f"echo ---; test -x {VENV_PY} && echo VENV_OK || echo VENV_MISSING; "
            "echo ---; crontab -l 2>/dev/null | grep -c run_scheduler_worker",
        ],
        timeout=45,
    )
    # Buang banner shell remote (mis. [HERMES-SAFETY]) supaya parsing bersih.
    out = "\n".join(l for l in out.splitlines() if not l.lstrip().startswith("[HERMES-SAFETY]"))
    if rc != 0 and "---" not in out:
        rec("FAIL", "SSH remote read-only", out[:300])
        return
    parts = out.split("---")
    master_cnt = parts[0].strip() if parts else ""
    rec("PASS" if master_cnt == "1" else "WARN",
        "master .env prod (harus false saat pre-deploy)",
        f"ENABLE_BACKGROUND_SCHEDULER=false x{master_cnt or '?'}")
    flags_st = "ADA" if "ABSENT_FLAGS" not in out else "belum ada"
    worker_st = "ADA" if "ABSENT_WORKER" not in out else "belum ada"
    rec("INFO", "flags.py di server", flags_st)
    rec("INFO", "run_scheduler_worker.py di server", worker_st)
    rec("FAIL" if "VENV_MISSING" in out else "PASS", "venv python 3.13",
        "siap" if "VENV_MISSING" not in out else "TIDAK ADA — deploy tak bisa jalan")
    cron_cnt = parts[-1].strip() if len(parts) > 4 else "?"
    if cron_cnt in ("0", ""):
        rec("INFO", "crontab scheduler", "belum terpasang (expected pre-deploy)")
        print(f"\n[PREFLIGHT] Baris crontab kanonis (step 3 runbook, jangan ketik manual):\n  {CRONTAB_LINE}\n", flush=True)
    else:
        rec("WARN", "crontab scheduler", f"sudah ada {cron_cnt} entry run_scheduler_worker")

    try:
        with urllib.request.urlopen(HEALTH_URL, timeout=20) as r:
            body = r.read(200).decode(errors="replace")
            rec("PASS" if r.status == 200 else "FAIL", "GET /api/health", f"HTTP {r.status} {body[:80]}")
    except Exception as e:  # noqa: BLE001
        rec("FAIL", "GET /api/health", repr(e))


def check_tests() -> None:
    venv = BACKEND / "venv" / "bin" / "python"
    py = str(venv) if venv.exists() else sys.executable
    rc, out = run([py, "-m", "pytest", "-q",
                   "tests/test_scheduler_flags.py", "tests/test_scheduler_enable_cli.py",
                   "tests/test_scheduler_prod_snapshot.py", "tests/test_billing_invoice_idempotency.py"],
                  cwd=BACKEND, timeout=300)
    rec("PASS" if rc == 0 else "FAIL", "suite scheduler (4 file)",
        out.splitlines()[-1] if out else "no output")
    rc2, out2 = run([py, "scripts/e2e_lifecycle_local.py"], cwd=BACKEND, timeout=180)
    ok = rc2 == 0 and "E2E-LIFECYCLE" in out2 and "PASS" in out2
    rec("PASS" if ok else "FAIL", "e2e lifecycle lokal (sqlite throwaway)",
        out2.splitlines()[-1] if out2 else "no output")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--remote", action="store_true", help="tambah SSH read-only ke prod")
    ap.add_argument("--tests", action="store_true", help="tambah pytest scheduler + e2e lifecycle")
    args = ap.parse_args()

    print(f"[PREFLIGHT] repo={REPO}", flush=True)
    check_local()
    if args.remote:
        check_remote()
    if args.tests:
        check_tests()

    fails = [r for r in results if r[0] == "FAIL"]
    print(f"\n[PREFLIGHT] ringkas: {len(results)} cek, {len(fails)} FAIL, "
          f"{sum(1 for r in results if r[0] == 'WARN')} WARN", flush=True)
    if fails:
        print("[PREFLIGHT] HASIL: BLOCKED — perbaiki FAIL di atas sebelum deploy.", flush=True)
        return 1
    print('[PREFLIGHT] HASIL: READY — semua pre-check lolos. Eksekusi deploy tetap '
          'MENUNGGU Kevin menulis "deploy" (runbook PRODUCTION.md).', flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
