"""Phase 08 Step 11 — admin synthesis LLM model route HTTP surface."""

from __future__ import annotations

import uuid

import pytest
from starlette.testclient import TestClient

from vector.domains.cortex.synthesis.synthesis_llm_router import GP08_LLM01_GATE_ID_V1

pytestmark = pytest.mark.integration


def test_admin_get_synthesis_llm_model_routes_catalog_ok(
    monkeypatch: pytest.MonkeyPatch,
    client: TestClient,
) -> None:
    monkeypatch.setenv("ADMIN_PASSWORD", "integration-admin-password")
    r = client.get(
        "/admin/catalog/cortex/synthesis/llm-model-routes",
        auth=("admin", "integration-admin-password"),
    )
    assert r.status_code == 200
    body = r.json()
    assert body["surface_kind"] == "doctrine_catalog"
    assert body["gate_id"] == GP08_LLM01_GATE_ID_V1
    assert any(row["model_route_id"] == "struct-v1" for row in body["model_routes"])


def test_admin_post_llm_route_preview_ok(
    monkeypatch: pytest.MonkeyPatch,
    client: TestClient,
) -> None:
    monkeypatch.setenv("ADMIN_PASSWORD", "integration-admin-password")
    r = client.post(
        "/admin/catalog/cortex/synthesis/llm-model-routes/preview",
        auth=("admin", "integration-admin-password"),
        json={
            "schema_version": 1,
            "tenant_id": str(uuid.UUID(int=0)),
            "synthesis_workload_class": "degradation_brief",
            "synthesis_intent": "audit",
            "execution_partition": "authoritative",
            "retrieval_scope": {},
        },
    )
    assert r.status_code == 200
    body = r.json()
    assert body["surface_kind"] == "synthesis_llm_route_preview"
    assert body["gate_id"] == GP08_LLM01_GATE_ID_V1
    assert "struct-v1" in body["selected_model_route_ids"]
    assert "audit-v1" in body["selected_model_route_ids"]
