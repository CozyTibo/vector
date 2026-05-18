"""Phase 08 Step 10 — admin synthesis retrieval plan HTTP surface."""

from __future__ import annotations

import uuid

import pytest
from starlette.testclient import TestClient

from vector.domains.cortex.synthesis.synthesis_query_plan import GP08_RETRIEVE01_GATE_ID_V1

pytestmark = pytest.mark.integration


def test_admin_get_synthesis_retrieval_plan_catalog_ok(
    monkeypatch: pytest.MonkeyPatch,
    client: TestClient,
) -> None:
    monkeypatch.setenv("ADMIN_PASSWORD", "integration-admin-password")
    r = client.get(
        "/admin/catalog/cortex/synthesis/retrieval-plan",
        auth=("admin", "integration-admin-password"),
    )
    assert r.status_code == 200
    body = r.json()
    assert body["surface_kind"] == "doctrine_catalog"
    assert body["gate_id"] == GP08_RETRIEVE01_GATE_ID_V1
    assert "execution_understanding" in body["synthesis_to_primary_retrieval_workload"]
    assert len(body["retrieval_fanout_rules"]) >= 1


def test_admin_post_retrieval_plan_preview_ok(
    monkeypatch: pytest.MonkeyPatch,
    client: TestClient,
) -> None:
    monkeypatch.setenv("ADMIN_PASSWORD", "integration-admin-password")
    r = client.post(
        "/admin/catalog/cortex/synthesis/retrieval-plan/preview",
        auth=("admin", "integration-admin-password"),
        json={
            "schema_version": 1,
            "tenant_id": str(uuid.UUID(int=0)),
            "synthesis_workload_class": "execution_understanding",
            "synthesis_intent": "inspect",
            "execution_partition": "authoritative",
            "retrieval_scope": {"retrieval_lookup_id": "sha256:" + "a" * 64},
        },
    )
    assert r.status_code == 200
    body = r.json()
    assert body["surface_kind"] == "synthesis_retrieval_plan_preview"
    assert body["retrieval_plan_count"] == 2
    assert body["retrieval_plan"][1]["retrieval_workload_class"] == "lineage_explorer"
