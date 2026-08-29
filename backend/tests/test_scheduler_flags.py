"""Flag matrix scheduler — default OFF, blast tidak nyelinap."""
import os

import pytest

from app.schedulers.flags import JOB_FLAGS, MASTER_FLAG, flag_on, scheduler_plan


@pytest.fixture(autouse=True)
def _clear_scheduler_env(monkeypatch):
    monkeypatch.delenv(MASTER_FLAG, raising=False)
    for envname in JOB_FLAGS.values():
        monkeypatch.delenv(envname, raising=False)


def test_flag_on_default_off(monkeypatch):
    monkeypatch.delenv("ENABLE_BLAST_SCHEDULER", raising=False)
    assert flag_on("ENABLE_BLAST_SCHEDULER") is False


def test_flag_on_true_only_literal_true(monkeypatch):
    monkeypatch.setenv("ENABLE_BILLING_SCHEDULER", "true")
    assert flag_on("ENABLE_BILLING_SCHEDULER") is True
    monkeypatch.setenv("ENABLE_BILLING_SCHEDULER", "TRUE")
    assert flag_on("ENABLE_BILLING_SCHEDULER") is True
    monkeypatch.setenv("ENABLE_BILLING_SCHEDULER", "1")
    assert flag_on("ENABLE_BILLING_SCHEDULER") is False
    monkeypatch.setenv("ENABLE_BILLING_SCHEDULER", "yes")
    assert flag_on("ENABLE_BILLING_SCHEDULER") is False


def test_plan_master_off_ignores_subflags(monkeypatch):
    monkeypatch.setenv(MASTER_FLAG, "false")
    monkeypatch.setenv("ENABLE_BILLING_SCHEDULER", "true")
    monkeypatch.setenv("ENABLE_BLAST_SCHEDULER", "true")
    plan = scheduler_plan()
    assert plan["master"] is False
    assert plan["jobs"] == []
    assert plan["will_start"] is False


def test_plan_master_on_all_sub_off_does_not_start(monkeypatch):
    monkeypatch.setenv(MASTER_FLAG, "true")
    plan = scheduler_plan()
    assert plan["master"] is True
    assert plan["jobs"] == []
    assert plan["will_start"] is False


def test_plan_billing_only_blast_stays_off(monkeypatch):
    monkeypatch.setenv(MASTER_FLAG, "true")
    monkeypatch.setenv("ENABLE_BILLING_SCHEDULER", "true")
    plan = scheduler_plan()
    assert plan["jobs"] == ["billing"]
    assert plan["will_start"] is True
    assert "blast" not in plan["jobs"]
    assert plan["flags"]["ENABLE_BLAST_SCHEDULER"] is False


def test_plan_followup_and_lifecycle(monkeypatch):
    monkeypatch.setenv(MASTER_FLAG, "true")
    monkeypatch.setenv("ENABLE_FOLLOWUP_SCHEDULER", "true")
    monkeypatch.setenv("ENABLE_LIFECYCLE_SCHEDULER", "true")
    plan = scheduler_plan()
    assert plan["jobs"] == ["followup", "lifecycle"]


def test_worker_probe_master_off(monkeypatch):
    monkeypatch.setenv(MASTER_FLAG, "false")
    from scripts.run_scheduler_worker import probe

    assert probe() == 0
    assert scheduler_plan()["will_start"] is False


def test_worker_refuses_blast_without_allow(monkeypatch):
    monkeypatch.setenv(MASTER_FLAG, "true")
    monkeypatch.setenv("ENABLE_BLAST_SCHEDULER", "true")
    from scripts.run_scheduler_worker import start_blocking

    rc = start_blocking(allow_blast=False)
    assert rc == 3
