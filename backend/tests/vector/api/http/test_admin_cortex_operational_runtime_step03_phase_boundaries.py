"""Admin HTTP — Phase 08.5 Step 03 phase-boundary doctrine catalog."""

from __future__ import annotations

import pytest
from starlette.testclient import TestClient

from vector.domains.cortex.operational_runtime.phase_boundaries import CESP_BND_RULE_IDS_V1

pytestmark = pytest.mark.integration


def test_admin_catalog_cortex_operational_runtime_phase_boundaries_ok(
    monkeypatch: pytest.MonkeyPatch,
    client: TestClient,
) -> None:
    monkeypatch.setenv("ADMIN_PASSWORD", "integration-admin-password")

    r = client.get(
        "/admin/catalog/cortex/operational-runtime/phase-boundaries",
        auth=("admin", "integration-admin-password"),
    )
    assert r.status_code == 200
    body = r.json()
    assert body["surface_kind"] == "doctrine_catalog"
    assert set(body["rule_ids"]) == set(CESP_BND_RULE_IDS_V1)
    assert "CESP-BND-08-01" in body["rule_ids"]
    assert body["hard_downstream_gate"] == "G-P085-CLOSE-01_before_phase_09"


def test_admin_catalog_cortex_operational_runtime_phase_boundaries_gate_ok(
    monkeypatch: pytest.MonkeyPatch,
    client: TestClient,
) -> None:
    monkeypatch.setenv("ADMIN_PASSWORD", "integration-admin-password")

    r = client.get(
        "/admin/catalog/cortex/operational-runtime/phase-boundaries-gate",
        auth=("admin", "integration-admin-password"),
    )
    assert r.status_code == 200
    body = r.json()
    assert body["gate_id"] == "G-P085-BND"
    assert body["passed"] is True
