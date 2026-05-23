"""Wave S4 step 17 — synthesis epoch/scope alignment."""

from __future__ import annotations

from vector.domains.cortex.synthesis.synthesis_epoch_scope_alignment_v1 import (
    FAILURE_CODE_ZERO_IN_SCOPE_V1,
    evaluate_synthesis_epoch_scope_readiness_v1,
)


def test_epoch_scope_gate_fails_when_entries_exist_but_zero_in_scope() -> None:
    gate = evaluate_synthesis_epoch_scope_readiness_v1(
        {
            "retrieval_entries_in_epoch": 50,
            "retrieval_entries_in_scope": 0,
        }
    )
    assert gate["violation"] is True
    assert gate["error_code"] == FAILURE_CODE_ZERO_IN_SCOPE_V1


def test_epoch_scope_gate_passes_when_in_scope_positive() -> None:
    gate = evaluate_synthesis_epoch_scope_readiness_v1(
        {
            "retrieval_entries_in_epoch": 50,
            "retrieval_entries_in_scope": 12,
        }
    )
    assert gate["violation"] is False
