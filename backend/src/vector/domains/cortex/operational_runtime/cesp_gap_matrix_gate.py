"""Phase 08.5 Step 04 — static gate **G-P085-GAP-MATRIX** + vocabulary discipline."""

from __future__ import annotations

from typing import Any

from vector.domains.cortex.operational_runtime.cesp_gap_matrix import (
    GP085_GAP_MATRIX_GATE_ID_V1,
    build_cesp_gap_matrix_catalog_v1,
    hash_cesp_gap_matrix_fixture_v1,
    parse_cesp_gap_matrix_markdown_v1,
    verify_gap_matrix_matches_baseline_registry_v1,
)
from vector.domains.cortex.operational_runtime.vocabulary import (
    PHASE085_VOCABULARY_ENTRIES_V1,
    PHASE085_VOCABULARY_TERM_IDS_V1,
    build_phase085_vocabulary_catalog_v1,
    vocabulary_term_labels_v1,
)


def _normative_index_vocabulary_labels_v1() -> list[str]:
    from vector.domains.cortex.operational_runtime.normative import _repo_root_v1, PHASE085_NORMATIVE_INDEX_REF_V1

    text = (_repo_root_v1() / "DOCS" / "cortex" / "operational-runtime" / PHASE085_NORMATIVE_INDEX_REF_V1).read_text(
        encoding="utf-8",
    )
    start = text.find("## Vocabulary")
    assert start >= 0
    block = text[start : start + 8000]
    labels: list[str] = []
    for line in block.splitlines():
        if line.strip().startswith("| **") and "|" in line[1:]:
            part = line.split("|")[1].strip()
            if part.startswith("**") and part.endswith("**"):
                labels.append(part.strip("*"))
    return labels


def verify_gp085_vocabulary_static() -> dict[str, Any]:
    errors: list[str] = []
    cat = build_phase085_vocabulary_catalog_v1()
    if cat["term_count"] != len(PHASE085_VOCABULARY_TERM_IDS_V1):
        errors.append("term_count_mismatch")
    if set(cat["term_ids"]) != set(PHASE085_VOCABULARY_TERM_IDS_V1):
        errors.append("term_ids_mismatch")
    normative_labels = _normative_index_vocabulary_labels_v1()
    runtime_labels = vocabulary_term_labels_v1()
    runtime_term_ids = {e["term_id"] for e in PHASE085_VOCABULARY_ENTRIES_V1}
    for label in normative_labels:
        if label in runtime_labels:
            continue
        if label.startswith("RET-SKIP") and "RET_SKIP" in runtime_term_ids:
            continue
        if label.replace("-", "_").upper() in runtime_term_ids:
            continue
        errors.append(f"missing_normative_label:{label}")
    passed = not errors
    return {
        "id": "G-P085-VOCAB",
        "name": "cesp_vocabulary_registry",
        "passed": passed,
        "severity": "hard_fail",
        "detail": {"errors": errors, "term_count": cat["term_count"]},
    }


def verify_gp085_gap_matrix_baseline_static() -> dict[str, Any]:
    errors: list[str] = []
    parsed = parse_cesp_gap_matrix_markdown_v1()
    errors.extend(verify_gap_matrix_matches_baseline_registry_v1(parsed))
    catalog = build_cesp_gap_matrix_catalog_v1()
    if catalog["gap_matrix_fixture_digest_sha256"] != hash_cesp_gap_matrix_fixture_v1():
        errors.append("catalog_digest_drift")
    summary = catalog["summary"]
    if summary["active_p0_total"] < 1:
        errors.append("active_p0_empty")
    if summary["active_p1_total"] < 1:
        errors.append("active_p1_empty")
    closed_ids = {r["gap_id"] for r in parsed["active_p0"] if r.get("status") == "closed"}
    for required_closed in ("P0-085-02", "P0-085-03", "P0-085-04"):
        if required_closed not in closed_ids:
            errors.append(f"expected_closed:{required_closed}")
    if "P0-085-01" not in {r["gap_id"] for r in parsed["active_p0"] if r.get("status") == "open"}:
        errors.append("p0_085_01_should_remain_open")
    passed = not errors
    return {
        "id": GP085_GAP_MATRIX_GATE_ID_V1,
        "name": "cesp_gap_matrix_baseline",
        "passed": passed,
        "severity": "hard_fail",
        "detail": {"errors": errors, "summary": summary},
    }


def verify_gp085_gap_matrix_discipline_static() -> dict[str, Any]:
    """Aggregate P085-04 — gap matrix + vocabulary baselined."""
    checks = (
        verify_gp085_gap_matrix_baseline_static(),
        verify_gp085_vocabulary_static(),
    )
    failures = [c["id"] for c in checks if not c.get("passed")]
    return {
        "id": GP085_GAP_MATRIX_GATE_ID_V1,
        "gate_id": GP085_GAP_MATRIX_GATE_ID_V1,
        "passed": not failures,
        "failure_codes": failures,
        "checks": list(checks),
    }
