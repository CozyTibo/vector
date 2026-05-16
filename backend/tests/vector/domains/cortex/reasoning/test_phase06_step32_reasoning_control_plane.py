"""P06-32 — Reasoning admin control plane (surface catalog + static oracles)."""

from __future__ import annotations

import uuid

from vector.domains.cortex.reasoning.reasoning_control_plane import (
    PHASE06_REASONING_CONTROL_PLANE_RUNTIME_SCHEMA_VERSION,
    REASONING_ADMIN_CONTROL_PLANE_SPEC_REF_V1,
    REASONING_CONTROL_PLANE_ADMIN_OPENAPI_PATHS_V1,
    REASONING_CONTROL_PLANE_CONTRACT_V1,
    REASONING_CONTROL_PLANE_SURFACE_VERSION_V1,
    REASONING_CONTROL_PLANE_SURFACES_V1,
    REASONING_DANGEROUS_ACTION_SAFETY_MODEL_REF_V1,
    ReasoningControlPlaneSurfaceV1,
    build_reasoning_control_plane_catalog_v1,
    list_reasoning_control_plane_surface_ids_v1,
    verify_gp06_rcp01_surface_catalog_sorted_unique_static,
    verify_gp06_rcp02_surfaces_match_admin_spec_table_static,
    verify_gp06_rcp03_doctrine_refs_frozen_static,
    verify_gp06_rcp04_build_catalog_contract_shape_static,
    verify_gp06_rcp05_admin_openapi_path_matrix_static,
    verify_gp06_rcp06_rbac_substrate_literal_frozen_static,
)


def test_runtime_constants() -> None:
    assert PHASE06_REASONING_CONTROL_PLANE_RUNTIME_SCHEMA_VERSION >= 1
    assert REASONING_CONTROL_PLANE_SURFACE_VERSION_V1 >= 1
    assert "reasoning-admin-control-plane-spec" in REASONING_ADMIN_CONTROL_PLANE_SPEC_REF_V1
    assert "dangerous-action-safety-model" in REASONING_DANGEROUS_ACTION_SAFETY_MODEL_REF_V1


def test_surface_tuple_frozen_order() -> None:
    ids = list_reasoning_control_plane_surface_ids_v1()
    assert len(ids) == 12
    assert list(ids) == sorted(ids)
    surfaces = REASONING_CONTROL_PLANE_SURFACES_V1
    assert all(isinstance(s, ReasoningControlPlaneSurfaceV1) for s in surfaces)


def test_all_rcp_oracles_pass() -> None:
    assert verify_gp06_rcp01_surface_catalog_sorted_unique_static()["passed"] is True
    assert verify_gp06_rcp02_surfaces_match_admin_spec_table_static()["passed"] is True
    assert verify_gp06_rcp03_doctrine_refs_frozen_static()["passed"] is True
    assert verify_gp06_rcp04_build_catalog_contract_shape_static()["passed"] is True
    assert verify_gp06_rcp05_admin_openapi_path_matrix_static()["passed"] is True
    assert verify_gp06_rcp06_rbac_substrate_literal_frozen_static()["passed"] is True


def test_build_catalog_openapi_contract() -> None:
    tid = uuid.uuid4()
    doc = build_reasoning_control_plane_catalog_v1(tenant_id=tid)
    assert doc["tenant_id"] == str(tid)
    assert doc["reasoning_control_plane_contract"] == REASONING_CONTROL_PLANE_CONTRACT_V1
    assert len(doc["surfaces"]) == 12
    assert doc["doctrine_anchors"] == [REASONING_ADMIN_CONTROL_PLANE_SPEC_REF_V1]
    assert REASONING_CONTROL_PLANE_ADMIN_OPENAPI_PATHS_V1[0].endswith("reasoning/control-plane")
