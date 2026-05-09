"""Phase 03 Step 4 — deterministic mapping contracts."""

from __future__ import annotations

from vector.domains.cortex.canonical.mapping_contracts import (
    MAPPING_CONTRACT_SCHEMA_VERSION,
    EvidenceGrade,
    build_mapping_contracts_public_section,
    validate_mapping_contracts_internal_consistency,
)


def test_mapping_contract_schema_version() -> None:
    assert MAPPING_CONTRACT_SCHEMA_VERSION == 1


def test_evidence_grade_enum() -> None:
    assert EvidenceGrade.E0.value == "E0"
    assert EvidenceGrade.E1.value == "E1"


def test_validate_mapping_contracts() -> None:
    validate_mapping_contracts_internal_consistency()


def test_public_section_shape() -> None:
    sec = build_mapping_contracts_public_section()
    assert sec["mapping_contract_schema_version"] == MAPPING_CONTRACT_SCHEMA_VERSION
    assert len(sec["evidence_grades"]) == 2
    assert sec["forbidden_operations"]
    assert sec["mapping_table_row_shape"]
