"""Phase 02 Step 16 — operational trust proof pass (G16)."""

from __future__ import annotations

import uuid

from vector.domains.cortex.ingestion.raw_memory_operational_trust_proof import (
    verify_phase02_step16_operational_trust_proof,
)
from vector.domains.cortex.ingestion.raw_memory_verification_unified import (
    compute_phase02_gate_g16_operational_trust_proof,
)


def test_gate_g16_follows_step16_passed() -> None:
    assert compute_phase02_gate_g16_operational_trust_proof({"passed": True})["decision"] == "pass"
    assert compute_phase02_gate_g16_operational_trust_proof({"passed": False})["decision"] == "hard_fail"


def test_step16_passes_when_operational_pillars_coherent() -> None:
    tid = uuid.uuid4()
    truth = {
        "schema_version": 1,
        "tenant_id": str(tid),
        "freshness": {"from_cache": False, "label": "fresh"},
        "proof_quality": {"primary": "measured"},
    }
    rep = verify_phase02_step16_operational_trust_proof(
        runtime_correctness={"passed": True, "state": "ok"},
        raw_memory_temporal={"passed": True, "state": "reconstruction-safe"},
        raw_memory_replay={
            "passed": True,
            "state": "replay-safe",
            "summary": {"jobs_examined": 0, "highest_divergence": {"class": "D0"}},
        },
        raw_memory_replay_hardening={
            "passed": True,
            "state": "hardened",
            "summary": {"jobs_examined": 0, "forbidden_classes": ["D3", "D4", "D5"]},
        },
        raw_memory_failure_recovery={"passed": True, "state": "ok"},
        raw_memory_critical_integrity={"passed": True, "state": "integrity_sound"},
        raw_memory_trust_signal={"passed": True, "state": "operator_safe"},
        phase02_verification_truth=truth,
    )
    assert rep["passed"] is True
    assert rep["state"] == "operationally_proven"


def test_step16_fails_when_freshness_incoherent() -> None:
    tid = uuid.uuid4()
    truth_wrong = {
        "tenant_id": str(tid),
        "freshness": {"from_cache": False, "label": "stale"},
    }
    rep = verify_phase02_step16_operational_trust_proof(
        runtime_correctness={"passed": True, "state": "ok"},
        raw_memory_temporal={"passed": True, "state": "reconstruction-safe"},
        raw_memory_replay={
            "passed": True,
            "summary": {"jobs_examined": 0, "highest_divergence": {"class": "D0"}},
        },
        raw_memory_replay_hardening={
            "passed": True,
            "summary": {"jobs_examined": 0, "forbidden_classes": []},
        },
        raw_memory_failure_recovery={"passed": True},
        raw_memory_critical_integrity={"passed": True},
        raw_memory_trust_signal={"passed": True},
        phase02_verification_truth=truth_wrong,
    )
    assert rep["passed"] is False
