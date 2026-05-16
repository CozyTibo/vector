"""P06-33 — Reasoning runtime legality matrix (**R‑LEG‑01..05**)."""

from __future__ import annotations

import uuid

from vector.domains.cortex.reasoning.reasoning_runtime_legality_matrix import (
    PHASE06_REASONING_RUNTIME_LEGALITY_MATRIX_RUNTIME_SCHEMA_VERSION,
    REASONING_RUNTIME_FORBIDDEN_DEPLOYMENTS_V1,
    REASONING_RUNTIME_LEGALITY_MATRIX_CONTRACT_V1,
    REASONING_RUNTIME_LEGALITY_MATRIX_SPEC_REF_V1,
    REASONING_RUNTIME_LEGALITY_PREDICATES_V1,
    ReasoningRuntimeLegalityPredicateV1,
    build_reasoning_runtime_legality_matrix_catalog_v1,
    list_reasoning_runtime_legality_predicate_ids_v1,
    verify_gp06_rlm01_predicate_catalog_five_sorted_unique_static,
    verify_gp06_rlm02_r_leg02_anti01_ci_green_static,
    verify_gp06_rlm03_cross_doc_anchors_frozen_static,
    verify_gp06_rlm04_forbidden_deployments_shape_static,
    verify_gp06_rlm05_waiver_yaml_future_path_literal_static,
    verify_gp06_rlm06_build_catalog_contract_shape_static,
    verify_gp06_rlm07_admin_openapi_path_matrix_static,
)


def test_runtime_constants() -> None:
    assert PHASE06_REASONING_RUNTIME_LEGALITY_MATRIX_RUNTIME_SCHEMA_VERSION >= 1
    assert "reasoning-runtime-legality-matrix" in REASONING_RUNTIME_LEGALITY_MATRIX_SPEC_REF_V1


def test_predicates_five_sorted() -> None:
    ids = list_reasoning_runtime_legality_predicate_ids_v1()
    assert ids == ("R-LEG-01", "R-LEG-02", "R-LEG-03", "R-LEG-04", "R-LEG-05")
    preds = REASONING_RUNTIME_LEGALITY_PREDICATES_V1
    assert all(isinstance(p, ReasoningRuntimeLegalityPredicateV1) for p in preds)


def test_forbidden_deployments() -> None:
    assert len(REASONING_RUNTIME_FORBIDDEN_DEPLOYMENTS_V1) == 2
    rows = REASONING_RUNTIME_FORBIDDEN_DEPLOYMENTS_V1
    assert rows[0].forbidden_id < rows[1].forbidden_id


def test_all_rlm_oracles_pass() -> None:
    assert verify_gp06_rlm01_predicate_catalog_five_sorted_unique_static()["passed"] is True
    assert verify_gp06_rlm02_r_leg02_anti01_ci_green_static()["passed"] is True
    assert verify_gp06_rlm03_cross_doc_anchors_frozen_static()["passed"] is True
    assert verify_gp06_rlm04_forbidden_deployments_shape_static()["passed"] is True
    assert verify_gp06_rlm05_waiver_yaml_future_path_literal_static()["passed"] is True
    assert verify_gp06_rlm06_build_catalog_contract_shape_static()["passed"] is True
    assert verify_gp06_rlm07_admin_openapi_path_matrix_static()["passed"] is True


def test_build_catalog() -> None:
    tid = uuid.uuid4()
    doc = build_reasoning_runtime_legality_matrix_catalog_v1(tenant_id=tid)
    assert doc["tenant_id"] == str(tid)
    c = REASONING_RUNTIME_LEGALITY_MATRIX_CONTRACT_V1
    assert doc["reasoning_runtime_legality_matrix_contract"] == c
    assert len(doc["predicates"]) == 5
    assert len(doc["forbidden_deployments"]) == 2
    assert len(doc["doctrine_anchors"]) == 4
