"""Phase 02 Step 12 — canonical verification path semantics."""

from __future__ import annotations

import uuid

from vector.domains.cortex.ingestion.raw_memory_verification_unified import (
    build_phase02_verification_truth,
    compute_phase02_gates_g1_g7,
    compute_phase02_gates_g8_g10,
    finalize_phase02_closure_from_canonical_gates,
    merge_phase02_canonical_gates,
    trust_annotation_gate_decisions_from_g1_g7,
    verify_phase02_step12_unified_verification_semantics,
)

_TRUST_OK = {
    "passed": True,
    "checks": [{"id": "s8_deterministic_transition_logic", "passed": True}],
}
_FR_MIN = {"passed": True, "summary": {"active_failure_classes": {}}, "checks": []}


def test_canonical_g1_g7_matches_trust_slice() -> None:
    g17 = compute_phase02_gates_g1_g7(
        raw_memory_contracts={"passed": True},
        raw_memory_persistence={"passed": True},
        raw_memory_temporal={"passed": True, "state": "reconstruction-safe"},
        raw_memory_replay={"passed": True, "summary": {"highest_divergence": {"class": "D0"}}},
        raw_memory_query={"passed": True},
        raw_memory_failure_recovery={
            "passed": True,
            "summary": {"active_failure_classes": {}, "latest_recovery_validation": None},
            "checks": [],
        },
    )
    slim = trust_annotation_gate_decisions_from_g1_g7(g17)
    assert slim["G1"]["decision"] == "pass"
    assert set(slim.keys()) == {"G1", "G2", "G3", "G4", "G5", "G6", "G7"}


def test_merge_and_closure_summary_stable() -> None:
    tid = uuid.uuid4()
    g17 = compute_phase02_gates_g1_g7(
        raw_memory_contracts={"passed": True},
        raw_memory_persistence={"passed": True},
        raw_memory_temporal={"passed": True, "state": "reconstruction-safe"},
        raw_memory_replay={"passed": True, "summary": {"highest_divergence": {"class": "D0"}}},
        raw_memory_query={"passed": True},
        raw_memory_failure_recovery=_FR_MIN,
    )
    g810 = compute_phase02_gates_g8_g10(
        raw_memory_trust=_TRUST_OK,
        raw_memory_control_plane={"passed": True},
        control_plane_payload={
            "warnings": {
                "must_not_assume": [
                    "replay-safe does not imply replay-complete provider omniscience",
                ]
            }
        },
    )
    merged = merge_phase02_canonical_gates(g17, g810)
    closure = finalize_phase02_closure_from_canonical_gates(
        tenant_id=tid,
        gates=merged,
        raw_memory_trust={
            "passed": True,
            "annotation": {"blocking": {"allow_diagnostic_reads": True}},
        },
    )
    assert closure["passed"] is True
    assert len(closure["gate_results"]) == 10


def test_step12_semantics_passes_when_truth_matches_closure() -> None:
    tid = uuid.uuid4()
    g17 = compute_phase02_gates_g1_g7(
        raw_memory_contracts={"passed": True},
        raw_memory_persistence={"passed": True},
        raw_memory_temporal={"passed": True, "state": "reconstruction-safe"},
        raw_memory_replay={"passed": True, "summary": {"highest_divergence": {"class": "D0"}}},
        raw_memory_query={"passed": True},
        raw_memory_failure_recovery=_FR_MIN,
    )
    g810 = compute_phase02_gates_g8_g10(
        raw_memory_trust=_TRUST_OK,
        raw_memory_control_plane={"passed": True},
        control_plane_payload={
            "warnings": {
                "must_not_assume": [
                    "replay-safe does not imply replay-complete provider omniscience",
                ]
            }
        },
    )
    merged = merge_phase02_canonical_gates(g17, g810)
    closure = finalize_phase02_closure_from_canonical_gates(
        tenant_id=tid,
        gates=merged,
        raw_memory_trust={
            "passed": True,
            "annotation": {
                "blocking": {},
                "verification": {
                    "gate_decisions": trust_annotation_gate_decisions_from_g1_g7(g17),
                },
            },
        },
    )
    truth = build_phase02_verification_truth(
        tenant_id=tid,
        canonical_gates=merged,
        trust_annotation={
            "verification": {"gate_decisions": trust_annotation_gate_decisions_from_g1_g7(g17)}
        },
        from_cache=False,
        cache_ttl_seconds=12.0,
        enforcement_mode="progressive",
        exhaust_gate_enforced=False,
        exhaust_gate_passed=None,
        verification_passed=True,
    )
    rep = verify_phase02_step12_unified_verification_semantics(
        phase02_verification_truth=truth,
        raw_memory_phase_closure=closure,
        raw_memory_trust={
            "passed": True,
            "annotation": {
                "verification": {"gate_decisions": trust_annotation_gate_decisions_from_g1_g7(g17)}
            },
        },
    )
    assert rep["passed"] is True
