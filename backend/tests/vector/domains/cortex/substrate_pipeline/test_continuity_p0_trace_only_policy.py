"""Phase A step A5 — trace-only prod sign-off ban."""

from __future__ import annotations

import os
import uuid

import pytest

from vector.domains.cortex.substrate_pipeline.continuity_p0_trace_only_policy import (
    TRACE_ONLY_CI_ENV,
    TraceOnlyProdSignoffError,
    assert_prod_baseline_signoff_allowed_v1,
    evaluate_p0_a5_trace_only_ban_proof_v1,
    merge_prod_signoff_checks_v1,
    record_p0_step_baseline_v1,
    resolve_trace_only_cli_v1,
    save_p0_step_baseline_v1,
    validate_baseline_prod_signoff_steps_v1,
    verify_a5_trace_only_ban_wiring_v1,
)


def test_trace_only_cli_requires_ci_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(TRACE_ONLY_CI_ENV, raising=False)
    with pytest.raises(TraceOnlyProdSignoffError):
        resolve_trace_only_cli_v1(requested=True)


def test_trace_only_cli_allowed_in_ci(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(TRACE_ONLY_CI_ENV, "1")
    assert resolve_trace_only_cli_v1(requested=True) is True


def test_baseline_write_refuses_trace_only() -> None:
    with pytest.raises(TraceOnlyProdSignoffError):
        assert_prod_baseline_signoff_allowed_v1(trace_only=True)


def test_save_p0_step_skips_baseline_on_trace_only(tmp_path) -> None:
    baseline: dict = {}
    saved = save_p0_step_baseline_v1(
        tmp_path / "baseline.json",
        baseline,
        step_key="step_a1_synthesis_job_reconcile",
        step_record={"p0_a1_pass": True},
        trace_only=True,
        save_fn=lambda _p, _b: tmp_path / "baseline.json",
    )
    assert saved is None
    assert "step_a1_synthesis_job_reconcile" not in baseline


def test_prod_signoff_checks_fail_when_trace_only() -> None:
    checks = merge_prod_signoff_checks_v1(
        {"ecs_deploy_matches_closure_sha": True},
        trace_only=True,
    )
    assert checks["prod_signoff_valid"] is False


def test_validate_phase_a_baseline_signoff() -> None:
    baseline = {
        "step_a1_synthesis_job_reconcile": {"trace_only": False, "signoff_grade": "prod"},
        "step_a4_aa_panel_strict": {"trace_only": True},
    }
    audit = validate_baseline_prod_signoff_steps_v1(
        baseline,
        step_keys=("step_a1_synthesis_job_reconcile", "step_a4_aa_panel_strict"),
    )
    assert audit["all_prod_signoff"] is False
    assert len(audit["violations"]) == 1


def test_a5_wiring_static() -> None:
    wiring = verify_a5_trace_only_ban_wiring_v1()
    assert wiring["wiring_ok"] is True
    assert wiring["scripts_checked"] >= 8


def test_a5_pass_when_phase_a_steps_prod_signed() -> None:
    baseline = {
        "trace_only_policy": {"schema_version": 1, "ci_only_env": TRACE_ONLY_CI_ENV},
        "step_a1_synthesis_job_reconcile": {"trace_only": False},
        "step_a2_ecs_deploy_align": {"trace_only": False},
        "step_a3_tcre_queued_drain": {"trace_only": False},
        "step_a4_aa_panel_strict": {"trace_only": False},
    }
    proof = evaluate_p0_a5_trace_only_ban_proof_v1(
        closure_git_sha="a" * 40,
        prod_deploy={"verification": {"deploy_matches_closure_sha": True}},
        baseline=baseline,
        wiring={"wiring_ok": True, "scripts_checked": 8},
        signoff_audit=validate_baseline_prod_signoff_steps_v1(baseline),
    )
    assert proof["p0_a5_pass"] is True
