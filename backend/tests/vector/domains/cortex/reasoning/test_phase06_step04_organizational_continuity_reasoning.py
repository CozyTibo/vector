"""P06-04 — Organizational continuity reasoning (Phase 04 upstream law)."""

from __future__ import annotations

from pathlib import Path

import pytest

from vector.domains.cortex.reasoning.organizational_continuity_reasoning import (
    AMB_BRIDGE_WEAK,
    AMB_NONE,
    KNOWN_AMBIGUITY_CLASS_IDS,
    LINK_AUTHORITY_AUTHORITATIVE,
    PHASE06_ORG_CONTINUITY_RUNTIME_SCHEMA_VERSION,
    REPLAY_POSTURE_REPLAY_CONFLICTED,
    OrganizationalContinuityReasoningError,
    validate_ambiguity_class_id_registered,
    validate_authoritative_link_gates_for_tcre_support,
    validate_candidate_or_hint_not_sole_without_bridge_weak,
    validate_evidence_lineage_has_raw_or_ledger_hop,
    validate_replay_conflicted_walk_propagates,
    verify_gp06_cont01_authoritative_link_gate_static,
    verify_gp06_cont02_candidate_hint_sole_static,
    verify_gp06_cont03_evidence_lineage_substrate_static,
    verify_gp06_cont04_replay_conflicted_propagation_static,
)


def test_org_continuity_runtime_schema_version() -> None:
    assert PHASE06_ORG_CONTINUITY_RUNTIME_SCHEMA_VERSION >= 1


def test_validate_ambiguity_class_id_registered() -> None:
    validate_ambiguity_class_id_registered(AMB_BRIDGE_WEAK)
    with pytest.raises(OrganizationalContinuityReasoningError):
        validate_ambiguity_class_id_registered("free_text_ambiguity")


def test_authoritative_link_requires_temporal_gate() -> None:
    with pytest.raises(OrganizationalContinuityReasoningError, match="temporal_validity_ok"):
        validate_authoritative_link_gates_for_tcre_support(
            {"link_authority": LINK_AUTHORITY_AUTHORITATIVE, "temporal_validity_ok": False}
        )


def test_candidate_sole_rejects_without_bridge_weak() -> None:
    with pytest.raises(OrganizationalContinuityReasoningError, match="BRIDGE"):
        validate_candidate_or_hint_not_sole_without_bridge_weak(
            {"sole_support_kind": "candidate", "ambiguity_class_id": AMB_NONE}
        )


def test_candidate_sole_accepts_bridge_weak() -> None:
    validate_candidate_or_hint_not_sole_without_bridge_weak(
        {"sole_support_kind": "candidate", "ambiguity_class_id": AMB_BRIDGE_WEAK}
    )


def test_evidence_lineage_requires_substrate_hop() -> None:
    with pytest.raises(OrganizationalContinuityReasoningError):
        validate_evidence_lineage_has_raw_or_ledger_hop(
            [{"hop_kind": "derived_window", "window_id": "w1"}]
        )


def test_evidence_lineage_accepts_cross_link() -> None:
    validate_evidence_lineage_has_raw_or_ledger_hop([{"hop_kind": "cross_link", "link_id": "01HZ"}])


def test_replay_conflicted_propagation() -> None:
    validate_replay_conflicted_walk_propagates(
        walk_replay_posture=REPLAY_POSTURE_REPLAY_CONFLICTED,
        dependent_replay_posture=REPLAY_POSTURE_REPLAY_CONFLICTED,
    )
    with pytest.raises(OrganizationalContinuityReasoningError, match="replay_conflicted"):
        validate_replay_conflicted_walk_propagates(
            walk_replay_posture=REPLAY_POSTURE_REPLAY_CONFLICTED,
            dependent_replay_posture="replay_equivalent",
        )


def test_verify_gp06_cont01_static_passes() -> None:
    assert verify_gp06_cont01_authoritative_link_gate_static()["passed"] is True


def test_verify_gp06_cont02_static_passes() -> None:
    assert verify_gp06_cont02_candidate_hint_sole_static()["passed"] is True


def test_verify_gp06_cont03_static_passes() -> None:
    assert verify_gp06_cont03_evidence_lineage_substrate_static()["passed"] is True


def test_verify_gp06_cont04_static_passes() -> None:
    assert verify_gp06_cont04_replay_conflicted_propagation_static()["passed"] is True


def test_organizational_continuity_doctrine_contract() -> None:
    start = Path(__file__).resolve()
    for root in [start, *start.parents]:
        p = root / "DOCS" / "cortex" / "reasoning" / "organizational-continuity-reasoning.md"
        if p.is_file():
            text = p.read_text(encoding="utf-8")
            assert "## 2. Rules" in text
            assert "Authoritative links" in text
            assert "Candidates / hints" in text
            assert "OrgGraphProjectionV1" in text
            assert "## 3. Handoff to Phase 05" in text
            return
    pytest.fail("organizational-continuity-reasoning.md not found")


def test_ambiguity_registry_lists_all_known_ids() -> None:
    start = Path(__file__).resolve()
    for root in [start, *start.parents]:
        reg = root / "DOCS" / "cortex" / "reasoning" / "ambiguity-registry-v1.md"
        if reg.is_file():
            text = reg.read_text(encoding="utf-8")
            for aid in KNOWN_AMBIGUITY_CLASS_IDS:
                assert aid in text, f"registry doc must contain canonical id {aid!r}"
            return
    pytest.fail("ambiguity-registry-v1.md not found")
