"""Phase 08 Step 05 — admin synthesis job contract catalog HTTP surface."""

from __future__ import annotations

import pytest
from starlette.testclient import TestClient

pytestmark = pytest.mark.integration


def test_admin_catalog_cortex_synthesis_job_contract_ok(
    monkeypatch: pytest.MonkeyPatch,
    client: TestClient,
) -> None:
    monkeypatch.setenv("ADMIN_PASSWORD", "integration-admin-password")

    r = client.get(
        "/admin/catalog/cortex/synthesis/job-contract",
        auth=("admin", "integration-admin-password"),
    )
    assert r.status_code == 200
    body = r.json()
    assert body["surface_kind"] == "doctrine_catalog"
    assert body["gp08_schema_gate_id"] == "G-P08-SCHEMA-01"
    assert len(body["synthesis_workload_classes"]) == 8
    assert len(body["synthesis_intent_classes"]) == 5
    workloads = {row["synthesis_workload_class"] for row in body["synthesis_workload_classes"]}
    assert "replay_equivalence_synthesis" in workloads
    assert "degradation_brief" in workloads
