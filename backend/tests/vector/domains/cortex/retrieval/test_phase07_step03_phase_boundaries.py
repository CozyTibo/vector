"""P07-03 — Phase boundaries vs Phase 06 / 08 / 09 (``retrieval.phase_boundaries``)."""

from __future__ import annotations

from pathlib import Path

import pytest

from vector.domains.cortex.retrieval.phase_boundaries import (
    PHASE07_BOUNDARIES_RUNTIME_SCHEMA_VERSION,
    RETRIEVAL_RD_TCRE_GAP_V1,
    RET_BND_RULE_IDS_V1,
    RetrievalPhaseBoundaryError,
    build_rd_tcre_gap_omission_row_v1,
    build_retrieval_phase_boundary_catalog_v1,
    enforce_retrieval_envelope_phase06_boundary_v1,
    list_reasoning_package_retrieval_import_violations_v1,
    list_retrieval_package_forward_phase_import_violations_v1,
    map_upstream_trigger_to_rd_code_v1,
    merge_upstream_triggers_into_retrieval_omissions_v1,
    validate_retrieval_exploration_partition_label_v1,
    validate_retrieval_hit_legality_copy_from_upstream_v1,
    validate_retrieval_response_no_phase08_fields_v1,
    validate_retrieval_result_no_silent_tcre_gap_v1,
    verify_gp07_bnd06_tcre_boundary_static,
    verify_gp07_bnd08_synthesis_boundary_static,
    verify_gp07_bnd_acyclic_dependency_static,
    verify_gp07_bnd_catalog_static,
)


def _repo_root_containing_phase07_docs() -> Path:
    start = Path(__file__).resolve()
    for root in [start, *start.parents]:
        marker = root / "DOCS" / "cortex" / "retrieval" / "phase-07-phase-boundaries-doctrine.md"
        if marker.is_file():
            return root
    pytest.fail("Could not locate DOCS/cortex/retrieval/ from test file parents.")


def test_phase07_boundaries_runtime_schema_version() -> None:
    assert PHASE07_BOUNDARIES_RUNTIME_SCHEMA_VERSION >= 1


def test_boundary_catalog_lists_all_ret_bnd_rules() -> None:
    cat = build_retrieval_phase_boundary_catalog_v1()
    assert set(cat["rule_ids"]) == set(RET_BND_RULE_IDS_V1)
    assert "RET-BND-06-01" in cat["rule_ids"]
    assert "RET-BND-08-03" in cat["rule_ids"]


def test_map_tcre_gap_trigger_to_rd_code() -> None:
    assert map_upstream_trigger_to_rd_code_v1("reconstruction_coverage_gap") == RETRIEVAL_RD_TCRE_GAP_V1


def test_build_rd_tcre_gap_omission_row() -> None:
    row = build_rd_tcre_gap_omission_row_v1()
    assert row["retrieval_omission_class"] == RETRIEVAL_RD_TCRE_GAP_V1


def test_envelope_rejects_inline_tcre_reducer() -> None:
    with pytest.raises(RetrievalPhaseBoundaryError) as exc:
        enforce_retrieval_envelope_phase06_boundary_v1(
            {"workload_class": "causal_chain", "run_tcre_reconstruction": True}
        )
    assert exc.value.rule_id == "RET-BND-06-01"


def test_envelope_accepts_lookup_only() -> None:
    enforce_retrieval_envelope_phase06_boundary_v1(
        {"workload_class": "causal_chain", "retrieval_lookup_id": "sha256:00"}
    )


def test_rejects_synthesis_answer_field() -> None:
    with pytest.raises(RetrievalPhaseBoundaryError) as exc:
        validate_retrieval_response_no_phase08_fields_v1({"answer": "forbidden"})
    assert exc.value.rule_id == "RET-BND-08-02"


def test_hit_legality_must_copy_upstream() -> None:
    with pytest.raises(RetrievalPhaseBoundaryError) as exc:
        validate_retrieval_hit_legality_copy_from_upstream_v1(
            {
                "chronology_legality_class": "strict",
                "upstream_chronology_legality_class": "degraded",
            }
        )
    assert exc.value.rule_id == "RET-BND-06-02"


def test_hit_legality_copy_accepts_matching_upstream() -> None:
    validate_retrieval_hit_legality_copy_from_upstream_v1(
        {
            "chronology_legality_class": "strict",
            "upstream_chronology_legality_class": "strict",
            "causal_legality_class": "verified",
            "upstream_causal_legality_class": "verified",
        }
    )


def test_exploration_requires_non_authoritative_label() -> None:
    with pytest.raises(RetrievalPhaseBoundaryError) as exc:
        validate_retrieval_exploration_partition_label_v1(
            {"retrieval_lookup_id": "x"},
            execution_partition="exploration",
        )
    assert exc.value.rule_id == "RET-BND-08-03"


def test_silent_tcre_gap_rejected() -> None:
    with pytest.raises(RetrievalPhaseBoundaryError) as exc:
        validate_retrieval_result_no_silent_tcre_gap_v1(
            upstream_triggers={"reconstruction_coverage_gap": True},
            hits=[],
            omissions=[],
        )
    assert exc.value.rule_id == "RET-BND-06-03"


def test_merge_upstream_triggers_builds_omissions() -> None:
    rows = merge_upstream_triggers_into_retrieval_omissions_v1(
        {"reconstruction_coverage_gap": True}
    )
    assert any(r["retrieval_omission_class"] == RETRIEVAL_RD_TCRE_GAP_V1 for r in rows)


def test_verify_gp07_bnd06_static_passes() -> None:
    assert verify_gp07_bnd06_tcre_boundary_static()["passed"] is True


def test_verify_gp07_bnd08_static_passes() -> None:
    assert verify_gp07_bnd08_synthesis_boundary_static()["passed"] is True


def test_verify_gp07_bnd_acyclic_static_passes() -> None:
    assert verify_gp07_bnd_acyclic_dependency_static()["passed"] is True


def test_verify_gp07_bnd_catalog_static_passes() -> None:
    assert verify_gp07_bnd_catalog_static()["passed"] is True


def test_retrieval_and_reasoning_import_acyclic_clean() -> None:
    assert list_retrieval_package_forward_phase_import_violations_v1() == []
    assert list_reasoning_package_retrieval_import_violations_v1() == []


def test_phase07_boundaries_doctrine_contract_sections() -> None:
    root = _repo_root_containing_phase07_docs()
    text = (
        root / "DOCS" / "cortex" / "retrieval" / "phase-07-phase-boundaries-doctrine.md"
    ).read_text(encoding="utf-8")
    assert "## Phase 07 OWNS" in text
    assert "## Phase 07 DOES NOT OWN" in text
    assert "RET‑BND‑06‑01" in text
    assert "RET‑BND‑08‑02" in text
    assert "RET‑BND‑09‑02" in text
