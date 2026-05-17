"""P07-26 — Retrieval runtime legality matrix (**R‑LEG‑01..07**, **R‑FORB‑01..05**)."""

from __future__ import annotations

import uuid
from pathlib import Path

from vector.domains.cortex.retrieval.retrieval_legality_matrix import (
    RETRIEVAL_FORBIDDEN_DEPLOYMENTS_V1,
    RETRIEVAL_LEGALITY_PREDICATES_V1,
    list_retrieval_legality_predicate_ids_v1,
)
from vector.domains.cortex.retrieval.retrieval_runtime_legality_matrix import (
    GP07_RLM01_GATE_ID_V1,
    PHASE07_RETRIEVAL_RUNTIME_LEGALITY_MATRIX_RUNTIME_SCHEMA_VERSION,
    RETRIEVAL_RUNTIME_LEGALITY_MATRIX_CONTRACT_V1,
    RETRIEVAL_RUNTIME_LEGALITY_MATRIX_SPEC_REF_V1,
    build_retrieval_runtime_legality_matrix_catalog_v1,
    detect_retrieval_forbidden_deployments_v1,
    evaluate_retrieval_production_gates_v1,
    verify_gp07_rlm01_predicate_catalog_seven_sorted_unique_static,
    verify_gp07_rlm01_retrieval_runtime_legality_matrix_static_bundle,
    verify_gp07_rlm02_r_leg01_anti01_ci_green_static,
    verify_gp07_rlm03_r_leg07_replay01_double_run_static,
    verify_gp07_rlm04_forbidden_deployments_shape_static,
    verify_gp07_rlm05_production_milestones_frozen_static,
    verify_gp07_rlm06_build_catalog_contract_shape_static,
    verify_gp07_rlm07_admin_openapi_path_matrix_static,
)


def _repo_root() -> Path:
    start = Path(__file__).resolve()
    for root in [start, *start.parents]:
        marker = root / "DOCS" / "cortex" / "retrieval" / "phase-07-retrieval-runtime-legality-matrix.md"
        if marker.is_file():
            return root
    msg = "repo root not found"
    raise RuntimeError(msg)


def test_runtime_constants() -> None:
    assert PHASE07_RETRIEVAL_RUNTIME_LEGALITY_MATRIX_RUNTIME_SCHEMA_VERSION >= 1
    assert "phase-07-retrieval-runtime-legality-matrix" in RETRIEVAL_RUNTIME_LEGALITY_MATRIX_SPEC_REF_V1


def test_predicates_seven_sorted() -> None:
    ids = list_retrieval_legality_predicate_ids_v1()
    assert ids == tuple(f"R-LEG-{i:02d}" for i in range(1, 8))
    assert len(RETRIEVAL_LEGALITY_PREDICATES_V1) == 7


def test_forbidden_deployments_five() -> None:
    assert len(RETRIEVAL_FORBIDDEN_DEPLOYMENTS_V1) == 5
    assert RETRIEVAL_FORBIDDEN_DEPLOYMENTS_V1[0].forbidden_id == "R-FORB-01"


def test_all_rlm_oracles_pass() -> None:
    assert verify_gp07_rlm01_predicate_catalog_seven_sorted_unique_static()["passed"] is True
    assert verify_gp07_rlm02_r_leg01_anti01_ci_green_static()["passed"] is True
    assert verify_gp07_rlm03_r_leg07_replay01_double_run_static()["passed"] is True
    assert verify_gp07_rlm04_forbidden_deployments_shape_static()["passed"] is True
    assert verify_gp07_rlm05_production_milestones_frozen_static()["passed"] is True
    assert verify_gp07_rlm06_build_catalog_contract_shape_static()["passed"] is True
    assert verify_gp07_rlm07_admin_openapi_path_matrix_static()["passed"] is True
    bundle = verify_gp07_rlm01_retrieval_runtime_legality_matrix_static_bundle()
    assert bundle["passed"] is True
    assert bundle["id"] == GP07_RLM01_GATE_ID_V1


def test_build_runtime_catalog_with_production_gates() -> None:
    tid = uuid.uuid4()
    doc = build_retrieval_runtime_legality_matrix_catalog_v1(None, tenant_id=tid)
    assert doc["tenant_id"] == str(tid)
    assert doc["retrieval_runtime_legality_matrix_contract"] == RETRIEVAL_RUNTIME_LEGALITY_MATRIX_CONTRACT_V1
    assert doc["gate_id"] == GP07_RLM01_GATE_ID_V1
    assert len(doc["predicates"]) == 7
    assert len(doc["forbidden_deployments"]) == 5
    assert "production_milestones" in doc
    assert doc["production_milestones"]["dev"]["passed"] is True
    gates = evaluate_retrieval_production_gates_v1(None, tenant_id=tid)
    assert gates["R-LEG-01"]["passed"] is True
    assert gates["R-LEG-07"]["passed"] is True
    detector = detect_retrieval_forbidden_deployments_v1(None, tenant_id=tid)
    assert len(detector) == 5
    assert doc["forbidden_deployments_clear"] is True


def test_doctrine_present() -> None:
    root = _repo_root()
    text = (root / "DOCS" / "cortex" / "retrieval" / "phase-07-retrieval-runtime-legality-matrix.md").read_text(
        encoding="utf-8"
    )
    assert "R-LEG-01" in text and "R-FORB-05" in text
    assert "build_retrieval_runtime_legality_matrix_catalog_v1" in text
