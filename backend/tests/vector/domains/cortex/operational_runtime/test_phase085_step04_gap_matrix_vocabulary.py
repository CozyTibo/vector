"""P085-04 — Gap matrix + vocabulary baselining."""

from __future__ import annotations

from vector.domains.cortex.operational_runtime.cesp_gap_matrix import (
    build_cesp_gap_matrix_catalog_v1,
    hash_cesp_gap_matrix_fixture_v1,
    parse_cesp_gap_matrix_markdown_v1,
    verify_gap_matrix_matches_baseline_registry_v1,
)
from vector.domains.cortex.operational_runtime.cesp_gap_matrix_gate import (
    verify_gp085_gap_matrix_baseline_static,
    verify_gp085_gap_matrix_discipline_static,
    verify_gp085_vocabulary_static,
)
from vector.domains.cortex.operational_runtime.vocabulary import (
    PHASE085_VOCABULARY_TERM_IDS_V1,
    build_phase085_vocabulary_catalog_v1,
)


def test_vocabulary_catalog_has_ten_closed_terms() -> None:
    cat = build_phase085_vocabulary_catalog_v1()
    assert cat["term_count"] == 10
    assert set(cat["term_ids"]) == set(PHASE085_VOCABULARY_TERM_IDS_V1)
    assert cat["surface_kind"] == "doctrine_catalog"


def test_gap_matrix_parses_p0_and_p1_rows() -> None:
    parsed = parse_cesp_gap_matrix_markdown_v1()
    assert len(parsed["active_p0"]) == 10
    assert len(parsed["active_p1"]) == 8
    assert verify_gap_matrix_matches_baseline_registry_v1(parsed) == []


def test_gap_matrix_catalog_marks_step2_gaps_closed() -> None:
    cat = build_cesp_gap_matrix_catalog_v1()
    closed = {r["gap_id"] for r in cat["active_p0"] if r["status"] == "closed"}
    assert "P0-085-02" in closed
    assert "P0-085-03" in closed
    assert "P0-085-04" in closed
    assert cat["summary"]["active_p0_open"] >= 1
    assert cat["blocks_step_36_freeze"] is True


def test_gap_matrix_fixture_digest_stable() -> None:
    assert hash_cesp_gap_matrix_fixture_v1() == hash_cesp_gap_matrix_fixture_v1()
    cat = build_cesp_gap_matrix_catalog_v1()
    assert cat["gap_matrix_fixture_digest_sha256"] == hash_cesp_gap_matrix_fixture_v1()


def test_verify_gp085_vocabulary_static_passes() -> None:
    assert verify_gp085_vocabulary_static()["passed"] is True


def test_verify_gp085_gap_matrix_baseline_static_passes() -> None:
    assert verify_gp085_gap_matrix_baseline_static()["passed"] is True


def test_verify_gp085_gap_matrix_discipline_static_passes() -> None:
    out = verify_gp085_gap_matrix_discipline_static()
    assert out["passed"] is True
    assert out["gate_id"] == "G-P085-GAP-MATRIX"
