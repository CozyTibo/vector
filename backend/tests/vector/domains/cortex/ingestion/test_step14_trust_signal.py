"""Phase 02 Step 14 — trust-signal / proof-quality semantics."""

from __future__ import annotations

import uuid

from vector.domains.cortex.ingestion.raw_memory_trust_signal import (
    PROOF_QUALITY_PRIMARY_VALUES,
    verify_phase02_step14_trust_signal_hardening,
)
from vector.domains.cortex.ingestion.raw_memory_verification_unified import (
    build_phase02_verification_truth,
    compute_phase02_gate_g14_trust_signal_quality,
    infer_proof_quality,
)


def test_infer_proof_quality_trust_mismatch_is_inferred() -> None:
    pq = infer_proof_quality(
        canonical_gates={"G1": {"decision": "pass"}},
        from_cache=False,
        exhaust_gate_enforced=False,
        exhaust_gate_passed=None,
        trust_g1_g7_matches_closure=False,
    )
    assert pq["primary"] == "inferred"
    assert pq["inferred"] is True


def test_infer_proof_quality_cached_is_stale_primary() -> None:
    pq = infer_proof_quality(
        canonical_gates={
            "G1": {"decision": "pass"},
            "G2": {"decision": "pass"},
            "G3": {"decision": "pass"},
            "G4": {"decision": "pass"},
            "G5": {"decision": "pass"},
            "G6": {"decision": "pass"},
            "G7": {"decision": "pass"},
            "G8": {"decision": "pass"},
            "G9": {"decision": "pass"},
            "G10": {"decision": "pass"},
        },
        from_cache=True,
        exhaust_gate_enforced=False,
        exhaust_gate_passed=None,
        trust_g1_g7_matches_closure=True,
    )
    assert pq["primary"] == "stale"


def test_step14_verifier_accepts_complete_truth_shape() -> None:
    tid = uuid.uuid4()
    gates = {
        "G1": {"decision": "pass", "reason": "", "passed": True},
        "G2": {"decision": "pass", "reason": "", "passed": True},
        "G3": {"decision": "pass", "reason": "", "passed": True},
        "G4": {"decision": "pass", "reason": "", "passed": True},
        "G5": {"decision": "pass", "reason": "", "passed": True},
        "G6": {"decision": "pass", "reason": "", "passed": True},
        "G7": {"decision": "pass", "reason": "", "passed": True},
        "G8": {"decision": "pass", "reason": "", "passed": True},
        "G9": {"decision": "pass", "reason": "", "passed": True},
        "G10": {"decision": "pass", "reason": "", "passed": True},
        "G13": {"decision": "pass", "reason": "", "passed": True},
        "G14": {"decision": "pass", "reason": "", "passed": True},
        "G15": {"decision": "pass", "reason": "", "passed": True},
        "G16": {"decision": "pass", "reason": "", "passed": True},
    }
    truth = build_phase02_verification_truth(
        tenant_id=tid,
        canonical_gates=gates,
        trust_annotation={"verification": {"gate_decisions": {}}},
        from_cache=False,
        cache_ttl_seconds=12.0,
        enforcement_mode="progressive",
        exhaust_gate_enforced=False,
        exhaust_gate_passed=None,
        verification_passed=True,
    )
    rep = verify_phase02_step14_trust_signal_hardening(truth)
    assert rep["passed"] is True
    assert compute_phase02_gate_g14_trust_signal_quality(rep)["decision"] == "pass"


def test_proof_quality_primary_enum_complete() -> None:
    assert PROOF_QUALITY_PRIMARY_VALUES == frozenset(
        {"measured", "inferred", "stale", "partial", "unverifiable"}
    )
