"""Phase 03 Step 11 — provenance runtime constants + ontology surface."""

from __future__ import annotations

from vector.domains.cortex.canonical.ontology import ONTOLOGY_SCHEMA_VERSION, build_phase03_step01_ontology_public_document
from vector.domains.cortex.canonical.provenance_runtime import PROVENANCE_RUNTIME_SCHEMA_VERSION, _sorted_unique_rule_ids


def test_provenance_runtime_schema_version() -> None:
    assert PROVENANCE_RUNTIME_SCHEMA_VERSION >= 1


def test_sorted_unique_rule_ids() -> None:
    class S:
        def __init__(self, rule_id: str) -> None:
            self.rule_id = rule_id

    assert _sorted_unique_rule_ids([S("a"), S("b"), S("a")]) == ["a", "b"]


def test_ontology_includes_provenance_pointer_section() -> None:
    doc = build_phase03_step01_ontology_public_document()
    assert doc["ontology_schema_version"] == 20
    assert ONTOLOGY_SCHEMA_VERSION == 20
    assert doc["implementation_step"] == 18
    assert doc["completed_implementation_steps"] == [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18]
    assert doc["provenance_by_raw_record_route"]
    assert doc["provenance_by_materialization_route"]
    assert doc["provenance_evidence_shapes_documented"]
    assert doc["transform_emits_provenance_record"] is True
