"""Phase 08 Step 12 — admin synthesis prompt template HTTP surface."""

from __future__ import annotations

import uuid

import pytest
from starlette.testclient import TestClient

from vector.domains.cortex.synthesis.synthesis_prompt_assembly import GP08_PRM01_GATE_ID_V1

pytestmark = pytest.mark.integration


def test_admin_get_synthesis_prompt_templates_catalog_ok(
    monkeypatch: pytest.MonkeyPatch,
    client: TestClient,
) -> None:
    monkeypatch.setenv("ADMIN_PASSWORD", "integration-admin-password")
    r = client.get(
        "/admin/catalog/cortex/synthesis/prompt-templates",
        auth=("admin", "integration-admin-password"),
    )
    assert r.status_code == 200
    body = r.json()
    assert body["surface_kind"] == "doctrine_catalog"
    assert body["gate_id"] == GP08_PRM01_GATE_ID_V1
    assert any(t["prompt_template_id"] == "synthesis_struct_default" for t in body["prompt_templates"])


def test_admin_post_prompt_assembly_preview_ok(
    monkeypatch: pytest.MonkeyPatch,
    client: TestClient,
) -> None:
    monkeypatch.setenv("ADMIN_PASSWORD", "integration-admin-password")
    r = client.post(
        "/admin/catalog/cortex/synthesis/prompt-templates/preview",
        auth=("admin", "integration-admin-password"),
        json={
            "schema_version": 1,
            "tenant_id": str(uuid.UUID(int=0)),
            "synthesis_workload_class": "degradation_brief",
            "synthesis_intent": "inspect",
            "execution_partition": "authoritative",
        },
    )
    assert r.status_code == 200
    body = r.json()
    assert body["surface_kind"] == "synthesis_prompt_assembly_preview"
    assert body["gate_id"] == GP08_PRM01_GATE_ID_V1
    assert body["prompt_assembly_count"] >= 1
    assert len(body["prompt_hashes"]) >= 1
