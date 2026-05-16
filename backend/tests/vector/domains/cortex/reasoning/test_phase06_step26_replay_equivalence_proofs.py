"""P06-26 — Temporal / causal replay proofs (**``G‑P06‑REPLAY‑01``**)."""

from __future__ import annotations

from pathlib import Path

import pytest

from vector.domains.cortex.reasoning.replay_equivalence_proofs import (
    GP06_REPLAY_01_GATE_ID_V1,
    PHASE06_REPLAY_EQUIVALENCE_PROOFS_RUNTIME_SCHEMA_VERSION,
    REPLAY_EQUIVALENCE_SPEC_SECTION_REF_V1,
    ReplayEquivalenceProofsError,
    compare_gp06_replay_01_double_run_v1,
    normalize_gp06_replay_01_comparison_vector_v1,
    verify_gp06_req01_replay_01_gate_id_oracle_static,
    verify_gp06_req02_permutation_profile_id_literal_static,
    verify_gp06_req03_minimal_bundle_double_run_match_static,
    verify_gp06_req04_chronology_digest_required_when_participates_static,
    verify_gp06_req05_double_run_mismatch_raises_static,
    verify_gp06_req06_causal_only_insufficient_when_receipts_static,
)


def test_runtime_schema_version() -> None:
    assert PHASE06_REPLAY_EQUIVALENCE_PROOFS_RUNTIME_SCHEMA_VERSION >= 1


def test_static_gates() -> None:
    assert verify_gp06_req01_replay_01_gate_id_oracle_static()["passed"] is True
    assert verify_gp06_req02_permutation_profile_id_literal_static()["passed"] is True
    assert verify_gp06_req03_minimal_bundle_double_run_match_static()["passed"] is True
    assert verify_gp06_req04_chronology_digest_required_when_participates_static()["passed"] is True
    assert verify_gp06_req05_double_run_mismatch_raises_static()["passed"] is True
    assert verify_gp06_req06_causal_only_insufficient_when_receipts_static()["passed"] is True


def test_gate_id_constant() -> None:
    assert GP06_REPLAY_01_GATE_ID_V1 == "G-P06-REPLAY-01"


def test_normalize_minimal_vector() -> None:
    d = "a" * 64
    b = {
        "causal_chain_ids_sorted": ["z", "a"],
        "chronology_participates": False,
        "ambiguity_active": False,
        "walk_consumed": False,
        "reasoning_equivalence_receipt_digest": d,
    }
    with pytest.raises(ReplayEquivalenceProofsError, match="sorted"):
        normalize_gp06_replay_01_comparison_vector_v1(b)


def test_normalize_and_compare_with_walk() -> None:
    eq = "f" * 64
    ch = "0" * 64
    rp = "1" * 64
    a = {
        "causal_chain_ids_sorted": ["c1"],
        "chronology_participates": True,
        "ambiguity_active": False,
        "walk_consumed": True,
        "reasoning_equivalence_receipt_digest": eq,
        "reasoning_chronology_receipt_digest": ch,
        "reasoning_replay_receipt_digest": rp,
    }
    b = dict(a)
    va = normalize_gp06_replay_01_comparison_vector_v1(a)
    vb = normalize_gp06_replay_01_comparison_vector_v1(b)
    assert va == vb
    compare_gp06_replay_01_double_run_v1(a, b)


def test_spec_ref() -> None:
    assert "replay-equivalence" in REPLAY_EQUIVALENCE_SPEC_SECTION_REF_V1


def test_doctrine_file_exists() -> None:
    start = Path(__file__).resolve()
    for root in [start, *start.parents]:
        p = root / "DOCS" / "cortex" / "reasoning" / "replay-equivalence-reasoning-spec.md"
        if p.is_file():
            txt = p.read_text(encoding="utf-8")
            assert "G‑P06‑REPLAY‑01" in txt or "G-P06-REPLAY-01" in txt
            return
    pytest.fail("replay-equivalence-reasoning-spec.md not found")


def test_package_reexports() -> None:
    import vector.domains.cortex.reasoning as r

    assert r.PHASE06_REPLAY_EQUIVALENCE_PROOFS_RUNTIME_SCHEMA_VERSION >= 1
    assert r.GP06_REPLAY_01_GATE_ID_V1 == "G-P06-REPLAY-01"
    assert verify_gp06_req03_minimal_bundle_double_run_match_static()["passed"] is True
