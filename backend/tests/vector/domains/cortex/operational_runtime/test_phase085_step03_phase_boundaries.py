"""P085-03 — Phase boundaries vs Phase 08 / 09 / 10 (``operational_runtime.phase_boundaries``)."""

from __future__ import annotations

from pathlib import Path

import pytest

from vector.domains.cortex.operational_runtime.cesp_phase_boundaries_gate import (
    GP085_PHASE_BOUNDARIES_GATE_ID_V1,
    verify_gp085_phase_boundaries_gate_static,
)
from vector.domains.cortex.operational_runtime.phase_boundaries import (
    CESP_BND_RULE_IDS_V1,
    CespPhaseBoundaryError,
    PHASE085_BOUNDARIES_RUNTIME_SCHEMA_VERSION,
    assert_cesp_payload_respects_synthesis_schema_boundary_v1,
    assert_phase09_blocked_until_cesp_close_v1,
    build_operational_runtime_phase_boundary_catalog_v1,
    hash_synthesis_artifact_schema_fixture_v1,
    list_cesp_package_forward_product_import_violations_v1,
    list_registered_cesp_admin_route_paths_v1,
    list_upstream_packages_importing_cesp_violations_v1,
    verify_gp085_bnd_catalog_static,
    verify_gp085_bnd_acyclic_dependency_static,
)


def _repo_root_containing_phase085_docs() -> Path:
    start = Path(__file__).resolve()
    for root in [start, *start.parents]:
        marker = root / "DOCS" / "cortex" / "operational-runtime" / "phase-085-phase-boundaries-doctrine.md"
        if marker.is_file():
            return root
    pytest.fail("Could not locate DOCS/cortex/operational-runtime/ from test file parents.")


def test_phase085_boundaries_runtime_schema_version() -> None:
    assert PHASE085_BOUNDARIES_RUNTIME_SCHEMA_VERSION >= 1


def test_boundary_catalog_lists_all_cesp_bnd_rules() -> None:
    cat = build_operational_runtime_phase_boundary_catalog_v1()
    assert set(cat["rule_ids"]) == set(CESP_BND_RULE_IDS_V1)
    assert cat["surface_kind"] == "doctrine_catalog"
    assert "CESP-BND-08-01" in cat["rule_ids"]
    assert "CESP-BND-09-01" in cat["rule_ids"]
    assert "phase_08_5_cesp" in cat["acyclic_pipeline"]


def test_synthesis_schema_digest_matches_fixture_file() -> None:
    root = _repo_root_containing_phase085_docs()
    schema_path = root / "DOCS/cortex/synthesis/schemas/synthesis-intelligence-artifact-v1.schema.json"
    assert schema_path.is_file()
    assert hash_synthesis_artifact_schema_fixture_v1() == hash_synthesis_artifact_schema_fixture_v1()
    cat = build_operational_runtime_phase_boundary_catalog_v1()
    assert cat["synthesis_artifact_schema_digest_sha256"] == hash_synthesis_artifact_schema_fixture_v1()


def test_phase09_blocked_until_close() -> None:
    with pytest.raises(CespPhaseBoundaryError) as exc:
        assert_phase09_blocked_until_cesp_close_v1(
            phase09_ship_flags={"phase09_enabled": True},
            cesp_close_gate_passed=False,
        )
    assert exc.value.rule_id == "CESP-BND-09-01"


def test_synthesis_schema_boundary_rejects_version_bump() -> None:
    with pytest.raises(CespPhaseBoundaryError) as exc:
        assert_cesp_payload_respects_synthesis_schema_boundary_v1(
            {"schema_version": 99, "artifact_kind": "briefing"},
        )
    assert exc.value.rule_id == "CESP-BND-08-01"


def test_no_forward_product_imports_in_cesp_package() -> None:
    assert list_cesp_package_forward_product_import_violations_v1() == []


def test_synthesis_reasoning_do_not_import_cesp() -> None:
    assert list_upstream_packages_importing_cesp_violations_v1() == []


def test_admin_routes_under_operational_runtime_prefix() -> None:
    routes = list_registered_cesp_admin_route_paths_v1()
    assert routes
    for route in routes:
        assert "operational-runtime" in route


def test_verify_gp085_bnd_catalog_static_passes() -> None:
    assert verify_gp085_bnd_catalog_static()["passed"] is True


def test_verify_gp085_bnd_acyclic_static_passes() -> None:
    assert verify_gp085_bnd_acyclic_dependency_static()["passed"] is True


def test_verify_gp085_phase_boundaries_gate_static_passes() -> None:
    out = verify_gp085_phase_boundaries_gate_static()
    assert out["passed"] is True
    assert out["gate_id"] == GP085_PHASE_BOUNDARIES_GATE_ID_V1
