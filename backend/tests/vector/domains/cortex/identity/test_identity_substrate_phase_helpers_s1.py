"""Phase S1.5–S1.6 — honest phase-03 receipts and phase-04 skip helpers."""

from __future__ import annotations

from vector.domains.cortex.identity.identity_substrate_phase_helpers_v1 import (
    infer_phase_03_processed_count_v1,
    should_skip_phase_04_after_identity_v1,
)
from vector.domains.cortex.substrate_pipeline.constants import PHASE_03_IDENTITY
from vector.domains.cortex.substrate_pipeline.substrate_phase_receipt import (
    PHASE_OUTCOME_COMPLETED_EMPTY,
    infer_processed_count_v1,
)


def test_infer_phase_03_processed_count_uses_substrate_work() -> None:
    raw = {
        "identity_substrate_audit": {
            "anchor_backfill": {"entities_upserted": 3},
            "candidates_generated_count": 12,
        }
    }
    assert infer_phase_03_processed_count_v1(raw) == 15
    assert infer_processed_count_v1(PHASE_03_IDENTITY, raw) == 15


def test_infer_phase_03_zero_when_no_work() -> None:
    raw = {
        "identity_substrate_audit": {
            "anchor_backfill": {"entities_upserted": 0},
            "candidates_generated_count": 0,
            "distinct_candidate_pairs_delta": 0,
        }
    }
    assert infer_phase_03_processed_count_v1(raw) == 0


def test_phase_03_completed_empty_inferred_when_no_work() -> None:
    raw = {
        "identity_substrate_audit": {
            "anchor_backfill": {"entities_upserted": 0},
            "candidates_generated_count": 0,
            "distinct_candidate_pairs_delta": 0,
        }
    }
    assert infer_processed_count_v1(PHASE_03_IDENTITY, raw) == 0


def test_should_skip_phase_04_when_identity_delta_zero() -> None:
    p03 = {
        "identity_substrate_audit": {
            "anchor_backfill": {"entities_upserted": 0},
            "candidates_generated_count": 0,
            "distinct_candidate_pairs_delta": 0,
        },
        "distinct_candidate_pairs_delta": 0,
        "substrate_phase_receipt": {"outcome": PHASE_OUTCOME_COMPLETED_EMPTY},
    }
    assert should_skip_phase_04_after_identity_v1(p03) is True


def test_should_not_skip_phase_04_when_pairs_delta_nonzero() -> None:
    p03 = {
        "identity_substrate_audit": {
            "anchor_backfill": {"entities_upserted": 0},
            "distinct_candidate_pairs_delta": 2,
        },
        "distinct_candidate_pairs_delta": 2,
        "substrate_phase_receipt": {"outcome": PHASE_OUTCOME_COMPLETED_EMPTY},
    }
    assert should_skip_phase_04_after_identity_v1(p03) is False
