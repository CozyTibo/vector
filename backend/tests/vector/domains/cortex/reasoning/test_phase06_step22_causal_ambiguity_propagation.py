"""P06-22 — Causal ambiguity propagation (``AMB‑*`` registry + AMB‑S1)."""

from __future__ import annotations

from pathlib import Path

import pytest

from vector.domains.cortex.reasoning.causal_ambiguity_propagation import (
    CONFLICT_RESOLUTION_AMBIGUITY_PROPAGATION_SECTION_REF_V1,
    PHASE06_CAUSAL_AMBIGUITY_PROPAGATION_RUNTIME_SCHEMA_VERSION,
    TCRE_AMBIGUITY_REGISTRY_VERSION,
    CausalAmbiguityPropagationError,
    normalize_ambiguity_corpus_token_to_registry_id_v1,
    validate_amb_s1_no_false_certainty_coercion_v1,
    validate_ambiguity_class_id_causal_registry_v1,
    validate_causal_ambiguity_propagation_bundle_v1,
    verify_gp06_amb01_registry_literal_oracle_static,
    verify_gp06_amb02_legacy_alias_normalization_static,
    verify_gp06_amb03_unknown_corpus_token_rejected_static,
    verify_gp06_amb04_amb_s1_rejects_coercion_flags_static,
    verify_gp06_amb05_bundle_happy_path_static,
)
from vector.domains.cortex.reasoning.organizational_continuity_reasoning import (
    AMB_CHRON_PARTIAL,
    AMB_NONE,
    KNOWN_AMBIGUITY_CLASS_IDS,
)


def test_runtime_schema_version() -> None:
    assert PHASE06_CAUSAL_AMBIGUITY_PROPAGATION_RUNTIME_SCHEMA_VERSION >= 1
    assert TCRE_AMBIGUITY_REGISTRY_VERSION >= 1


def test_static_gates() -> None:
    assert verify_gp06_amb01_registry_literal_oracle_static()["passed"] is True
    assert verify_gp06_amb02_legacy_alias_normalization_static()["passed"] is True
    assert verify_gp06_amb03_unknown_corpus_token_rejected_static()["passed"] is True
    assert verify_gp06_amb04_amb_s1_rejects_coercion_flags_static()["passed"] is True
    assert verify_gp06_amb05_bundle_happy_path_static()["passed"] is True


def test_normalize_case_insensitive_alias() -> None:
    assert normalize_ambiguity_corpus_token_to_registry_id_v1(
        "Weak_Cross_System_Bridge"
    ) == normalize_ambiguity_corpus_token_to_registry_id_v1("weak_cross_system_bridge")


def test_validate_causal_registry_wraps_unknown() -> None:
    with pytest.raises(CausalAmbiguityPropagationError, match="registered"):
        validate_ambiguity_class_id_causal_registry_v1("not_registered")


def test_amb_s1_allows_amb_none_with_coercion_key() -> None:
    """Coercion keys are only forbidden when ambiguity is active (non AMB‑NONE)."""
    validate_amb_s1_no_false_certainty_coercion_v1(
        {"ambiguity_class_id": AMB_NONE, "ambiguity_suppressed": True}
    )


def test_amb_s1_rejects_treat_resolved() -> None:
    with pytest.raises(CausalAmbiguityPropagationError, match="AMB-S1"):
        validate_amb_s1_no_false_certainty_coercion_v1(
            {
                "ambiguity_class_id": AMB_CHRON_PARTIAL,
                "treat_ambiguity_as_resolved": True,
            }
        )


def test_bundle_accepts_registered_only() -> None:
    validate_causal_ambiguity_propagation_bundle_v1({"ambiguity_class_id": "AMB\u2011NONE"})


def test_doctrine_files_exist() -> None:
    start = Path(__file__).resolve()
    for root in [start, *start.parents]:
        bounded = root / "DOCS" / "cortex" / "reasoning" / "bounded-ambiguity-law.md"
        if bounded.is_file():
            btxt = bounded.read_text(encoding="utf-8")
            assert "AMB‑S1" in btxt or "AMB-S1" in btxt
            reg = root / "DOCS" / "cortex" / "reasoning" / "ambiguity-registry-v1.md"
            assert reg.is_file()
            assert "Corpus loader" in reg.read_text(encoding="utf-8")
            cref = root / "DOCS" / "cortex" / "continuity" / "conflict-resolution-doctrine.md"
            assert cref.is_file()
            assert "## 5. Ambiguity propagation" in cref.read_text(encoding="utf-8")
            assert CONFLICT_RESOLUTION_AMBIGUITY_PROPAGATION_SECTION_REF_V1.endswith("§5")
            return
    pytest.fail("P06-22 doctrine files not found")


def test_known_ids_count() -> None:
    assert len(KNOWN_AMBIGUITY_CLASS_IDS) == 8


def test_package_reexports() -> None:
    import vector.domains.cortex.reasoning as r

    assert r.TCRE_AMBIGUITY_REGISTRY_VERSION >= 1
    assert callable(r.normalize_ambiguity_corpus_token_to_registry_id_v1)
    assert verify_gp06_amb01_registry_literal_oracle_static()["passed"] is True
