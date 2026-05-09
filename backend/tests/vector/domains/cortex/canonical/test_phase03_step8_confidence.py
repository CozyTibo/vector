"""Phase 03 Step 8 — confidence taxonomy + stub lineage mapping."""

from __future__ import annotations

import pytest

from vector.domains.cortex.canonical.confidence_runtime import (
    CONFIDENCE_PROPAGATION_SCHEMA_VERSION,
    Phase03ConfidenceClass,
    materialization_confidence_rollup,
    stub_lineage_confidence,
    validate_confidence_class,
)


def test_confidence_propagation_schema_version() -> None:
    assert CONFIDENCE_PROPAGATION_SCHEMA_VERSION >= 1


def test_validate_confidence_class_rejects_probabilistic() -> None:
    with pytest.raises(ValueError, match="forbidden"):
        validate_confidence_class("PROBABILISTIC_MODEL")


def test_validate_confidence_class_accepts_deterministic_rule() -> None:
    assert validate_confidence_class(Phase03ConfidenceClass.DETERMINISTIC_RULE.value) == "DETERMINISTIC_RULE"


def test_stub_lineage_confidence_parse_format_for_payload_title() -> None:
    cc, meta = stub_lineage_confidence(
        field_path="attributes.title",
        rule_id="rule.stub.x.payload.title",
        evidence_grade="E0",
    )
    assert cc == Phase03ConfidenceClass.PARSE_FORMAT.value
    assert meta["parse_surface"] == "json_field"


def test_materialization_confidence_rollup_sorted_keys() -> None:
    class _R:
        def __init__(self, cc: str) -> None:
            self.confidence_class = cc

    rollup = materialization_confidence_rollup([_R("B"), _R("A"), _R("A")])
    assert rollup["semantics"] == "structured_metadata_non_ranking"
    assert list(rollup["by_confidence_class"].keys()) == ["A", "B"]
    assert rollup["by_confidence_class"]["A"] == 2
