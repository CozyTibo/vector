"""Phase C1 — phase 08 empty scope truth gate."""

from __future__ import annotations

from vector.domains.cortex.synthesis.phase08_empty_scope_truth_gate import (
    EMPTY_SCOPE_WITH_ENTRIES_CODE_V1,
    attach_phase08_empty_scope_truth_gate_v1,
    evaluate_phase08_empty_scope_truth_v1,
    should_fail_phase08_for_empty_scope_violation_v1,
)


def test_evaluate_violation_when_entries_but_no_scopes() -> None:
    gate = evaluate_phase08_empty_scope_truth_v1(
        {"scope_empty": True, "scopes_scheduled": 0, "jobs_completed": 0},
        retrieval_entries_in_epoch=1200,
    )
    assert gate["violation"] is True
    assert gate["ok"] is False
    assert gate["error_code"] == EMPTY_SCOPE_WITH_ENTRIES_CODE_V1


def test_evaluate_lawful_empty_when_no_entries() -> None:
    gate = evaluate_phase08_empty_scope_truth_v1(
        {"scope_empty": True, "scopes_scheduled": 0, "jobs_completed": 0},
        retrieval_entries_in_epoch=0,
    )
    assert gate["violation"] is False
    assert gate["lawful_empty"] is True


def test_evaluate_ok_when_jobs_completed() -> None:
    gate = evaluate_phase08_empty_scope_truth_v1(
        {"scope_empty": False, "scopes_scheduled": 3, "jobs_completed": 2},
        retrieval_entries_in_epoch=500,
    )
    assert gate["violation"] is False


def test_attach_sets_fail_flag(monkeypatch) -> None:
    monkeypatch.setattr(
        "vector.domains.cortex.synthesis.phase08_empty_scope_truth_gate."
        "count_retrieval_entries_in_published_epoch_v1",
        lambda *_a, **_k: {"published_index_epoch": "epoch-x", "retrieval_entries_in_epoch": 10},
    )
    out = attach_phase08_empty_scope_truth_gate_v1(
        None,  # type: ignore[arg-type]
        tenant_id=__import__("uuid").uuid4(),
        materialize_output={"scope_empty": True, "scopes_scheduled": 0, "jobs_completed": 0},
        published_index_epoch="epoch-x",
    )
    assert out["empty_scope_violation"] is True
    assert should_fail_phase08_for_empty_scope_violation_v1(out) is True
