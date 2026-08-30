"""CLI --enable process-local: nyalain job TANPA tulis .env Passenger.

Snapshot prod 30 Agu: master=false, sub-flag absen. Worker yang cuma baca
.env itu = no-op. Tes ini mengunci: --safe-first / --enable followup
--dry-run start di process, blast+billing tidak ikut, .env tidak disentuh.
--enable billing tetap ada untuk override Kevin, bukan first-enable.
"""
import pytest

from app.schedulers.flags import JOB_FLAGS, MASTER_FLAG, scheduler_plan
from scripts.run_scheduler_worker import (
    apply_process_enables,
    main,
    parse_enable,
    start_blocking,
)


@pytest.fixture(autouse=True)
def _clear_scheduler_env(monkeypatch):
    monkeypatch.setenv(MASTER_FLAG, "false")
    for envname in JOB_FLAGS.values():
        monkeypatch.delenv(envname, raising=False)


def test_parse_enable_billing_only():
    assert parse_enable("billing") == ["billing"]
    assert parse_enable("billing,followup") == ["billing", "followup"]
    assert parse_enable(" billing , billing ") == ["billing"]


def test_parse_enable_unknown_raises():
    try:
        parse_enable("blast,nuklir")
        raise AssertionError("harusnya ValueError")
    except ValueError as exc:
        assert "nuklir" in str(exc)


def test_enable_billing_overrides_prod_snapshot(monkeypatch):
    monkeypatch.setenv(MASTER_FLAG, "false")
    for name in (
        "ENABLE_BLAST_SCHEDULER",
        "ENABLE_FOLLOWUP_SCHEDULER",
        "ENABLE_LIFECYCLE_SCHEDULER",
        "ENABLE_BILLING_SCHEDULER",
    ):
        monkeypatch.delenv(name, raising=False)

    apply_process_enables(["billing"])
    plan = scheduler_plan()
    assert plan["master"] is True
    assert plan["jobs"] == ["billing"]
    assert plan["job_ids"] == [
        "subscription-deductions",
        "project-billing-invoices",
    ]
    assert plan["will_start"] is True
    assert "blast" not in plan["jobs"]


def test_dry_run_enable_billing_does_not_start_scheduler(monkeypatch):
    monkeypatch.setenv(MASTER_FLAG, "false")
    monkeypatch.delenv("ENABLE_BILLING_SCHEDULER", raising=False)
    apply_process_enables(["billing"])
    rc = start_blocking(allow_blast=False, dry_run=True)
    assert rc == 0


def test_enable_blast_without_allow_refuses(monkeypatch):
    monkeypatch.setenv(MASTER_FLAG, "false")
    apply_process_enables(["blast"])
    rc = start_blocking(allow_blast=False, dry_run=True)
    assert rc == 3


def test_main_enable_billing_dry_run_exit_0(monkeypatch, capsys):
    monkeypatch.setenv(MASTER_FLAG, "false")
    monkeypatch.delenv("ENABLE_BILLING_SCHEDULER", raising=False)
    rc = main(["--enable", "billing", "--dry-run"])
    assert rc == 0
    plan = scheduler_plan()
    assert plan["jobs"] == ["billing"]
    out = capsys.readouterr().out
    assert "subscription-deductions" in out
    assert "project-billing-invoices" in out
    assert "pending-blasts" not in out


def test_main_enable_followup_is_safe_first(monkeypatch, capsys):
    """First-enable setelah deploy = followup, bukan billing by-tanggal / blast."""
    from app.schedulers.flags import SAFE_FIRST_ENABLE

    assert SAFE_FIRST_ENABLE == "followup"
    monkeypatch.setenv(MASTER_FLAG, "false")
    rc = main(["--enable", SAFE_FIRST_ENABLE, "--dry-run"])
    assert rc == 0
    plan = scheduler_plan()
    assert plan["jobs"] == ["followup"]
    assert plan["job_ids"] == ["followups"]
    out = capsys.readouterr().out
    assert "followups" in out
    assert "pending-blasts" not in out
    assert "subscription-deductions" not in out


def test_main_safe_first_flag_equals_followup(monkeypatch, capsys):
    """--safe-first = --enable followup. Billing/blast tidak ikut."""
    from app.schedulers.flags import SAFE_FIRST_ENABLE

    monkeypatch.setenv(MASTER_FLAG, "false")
    rc = main(["--safe-first", "--dry-run"])
    assert rc == 0
    plan = scheduler_plan()
    assert plan["jobs"] == [SAFE_FIRST_ENABLE]
    assert plan["job_ids"] == ["followups"]
    out = capsys.readouterr().out
    assert "followups" in out
    assert "subscription-deductions" not in out
    assert "pending-blasts" not in out


def test_main_safe_first_mixed_with_billing_refuses():
    rc = main(["--safe-first", "--enable", "billing", "--dry-run"])
    assert rc == 2


def test_main_unknown_job_exit_2():
    rc = main(["--enable", "nuklir", "--dry-run"])
    assert rc == 2


def test_main_probe_prod_snapshot_still_off(monkeypatch):
    monkeypatch.setenv(MASTER_FLAG, "false")
    for name in (
        "ENABLE_BLAST_SCHEDULER",
        "ENABLE_FOLLOWUP_SCHEDULER",
        "ENABLE_LIFECYCLE_SCHEDULER",
        "ENABLE_BILLING_SCHEDULER",
    ):
        monkeypatch.delenv(name, raising=False)
    rc = main(["--probe"])
    assert rc == 0
    assert scheduler_plan()["will_start"] is False
