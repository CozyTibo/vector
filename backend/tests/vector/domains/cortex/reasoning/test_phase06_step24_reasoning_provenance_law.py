"""P06-24 — Reasoning provenance law (mandatory §1 envelope)."""

from __future__ import annotations

from pathlib import Path

import pytest

from vector.domains.cortex.reasoning.chronology_degradation_propagation import CD_CHRON, CD_CONT
from vector.domains.cortex.reasoning.reasoning_provenance_law import (
    PHASE06_REASONING_PROVENANCE_LAW_RUNTIME_SCHEMA_VERSION,
    REASONING_PROVENANCE_LAW_SPEC_REF_V1,
    REASONING_REPLAY_POSTURE_LITERALS_V1,
    ReasoningProvenanceLawError,
    reasoning_provenance_minimal_valid_fixture_v1,
    validate_reasoning_artifact_provenance_envelope_v1,
    verify_gp06_rpl01_replay_posture_literal_oracle_static,
    verify_gp06_rpl02_minimal_envelope_happy_path_static,
    verify_gp06_rpl03_missing_lineage_rejected_static,
    verify_gp06_rpl04_cross_system_requires_org_link_static,
    verify_gp06_rpl05_deprecated_degradation_semantics_rejected_static,
)


def test_runtime_schema_version() -> None:
    assert PHASE06_REASONING_PROVENANCE_LAW_RUNTIME_SCHEMA_VERSION >= 1


def test_static_gates() -> None:
    assert verify_gp06_rpl01_replay_posture_literal_oracle_static()["passed"] is True
    assert verify_gp06_rpl02_minimal_envelope_happy_path_static()["passed"] is True
    assert verify_gp06_rpl03_missing_lineage_rejected_static()["passed"] is True
    assert verify_gp06_rpl04_cross_system_requires_org_link_static()["passed"] is True
    assert verify_gp06_rpl05_deprecated_degradation_semantics_rejected_static()["passed"] is True


def test_replay_posture_literal_count() -> None:
    assert len(REASONING_REPLAY_POSTURE_LITERALS_V1) == 5


def test_minimal_fixture_validates() -> None:
    validate_reasoning_artifact_provenance_envelope_v1(reasoning_provenance_minimal_valid_fixture_v1())
    validate_reasoning_artifact_provenance_envelope_v1(
        reasoning_provenance_minimal_valid_fixture_v1(cross_system_causal=True)
    )


def test_rejects_bad_replay_posture() -> None:
    b = dict(reasoning_provenance_minimal_valid_fixture_v1())
    b["replay_posture"] = "not_a_posture"
    with pytest.raises(ReasoningProvenanceLawError, match="replay_posture"):
        validate_reasoning_artifact_provenance_envelope_v1(b)


def test_rejects_bad_chronology_legality() -> None:
    b = dict(reasoning_provenance_minimal_valid_fixture_v1())
    b["chronology_legality_class"] = "invalid_chron"
    with pytest.raises(ReasoningProvenanceLawError, match="chronology_legality_class"):
        validate_reasoning_artifact_provenance_envelope_v1(b)


def test_rejects_bad_confidence_source() -> None:
    b = dict(reasoning_provenance_minimal_valid_fixture_v1())
    b["confidence_source"] = "ml_model_score"
    with pytest.raises(ReasoningProvenanceLawError, match="confidence_source"):
        validate_reasoning_artifact_provenance_envelope_v1(b)


def test_cd_codes_must_be_sorted_unique() -> None:
    b = dict(reasoning_provenance_minimal_valid_fixture_v1())
    b["cd_codes"] = [CD_CONT, CD_CHRON]
    with pytest.raises(ReasoningProvenanceLawError, match="sorted unique"):
        validate_reasoning_artifact_provenance_envelope_v1(b)


def test_cd_codes_sorted_ok() -> None:
    b = dict(reasoning_provenance_minimal_valid_fixture_v1())
    b["cd_codes"] = [CD_CHRON, CD_CONT]
    b["degradation_coarse"] = "composite"
    validate_reasoning_artifact_provenance_envelope_v1(b)


def test_degradation_coarse_mismatch() -> None:
    b = dict(reasoning_provenance_minimal_valid_fixture_v1())
    b["cd_codes"] = [CD_CHRON]
    b["degradation_coarse"] = "composite"
    with pytest.raises(ReasoningProvenanceLawError, match="inconsistent"):
        validate_reasoning_artifact_provenance_envelope_v1(b)


def test_unverifiable_requires_cd() -> None:
    b = dict(reasoning_provenance_minimal_valid_fixture_v1())
    b["causal_legality_class"] = "causal_unverifiable"
    with pytest.raises(ReasoningProvenanceLawError, match="non-empty"):
        validate_reasoning_artifact_provenance_envelope_v1(b)


def test_source_raw_record_ids_type() -> None:
    b = dict(reasoning_provenance_minimal_valid_fixture_v1())
    b["source_raw_record_ids"] = ["1"]
    with pytest.raises(ReasoningProvenanceLawError, match="source_raw_record_ids"):
        validate_reasoning_artifact_provenance_envelope_v1(b)


def test_spec_ref() -> None:
    assert REASONING_PROVENANCE_LAW_SPEC_REF_V1.endswith("§1")


def test_doctrine_file_exists() -> None:
    start = Path(__file__).resolve()
    for root in [start, *start.parents]:
        p = root / "DOCS" / "cortex" / "reasoning" / "reasoning-provenance-law.md"
        if p.is_file():
            txt = p.read_text(encoding="utf-8")
            assert "Required fields" in txt
            assert "CD‑*" in txt or "CD-*" in txt
            return
    pytest.fail("reasoning-provenance-law.md not found")


def test_package_reexports() -> None:
    import vector.domains.cortex.reasoning as r

    assert r.PHASE06_REASONING_PROVENANCE_LAW_RUNTIME_SCHEMA_VERSION >= 1
    assert len(r.REASONING_REPLAY_POSTURE_LITERALS_V1) == 5
    assert verify_gp06_rpl02_minimal_envelope_happy_path_static()["passed"] is True
