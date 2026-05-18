"""Phase 08 Step 02 — admin synthesis anti-goals doctrine catalog HTTP surface."""

from __future__ import annotations

import pytest
from starlette.testclient import TestClient

from vector.domains.cortex.synthesis.anti_goals import SYNTHESIS_FORBIDDEN_LEGALITY_CLASS_V1

pytestmark = pytest.mark.integration


def test_admin_catalog_cortex_synthesis_anti_goals_ok(
    monkeypatch: pytest.MonkeyPatch,
    client: TestClient,
) -> None:
    monkeypatch.setenv("ADMIN_PASSWORD", "integration-admin-password")

    r = client.get(
        "/admin/catalog/cortex/synthesis/anti-goals",
        auth=("admin", "integration-admin-password"),
    )
    assert r.status_code == 200
    body = r.json()
    assert body["surface_kind"] == "doctrine_catalog"
    assert body["synthesis_forbidden_legality_class"] == SYNTHESIS_FORBIDDEN_LEGALITY_CLASS_V1
    assert "G-P08-ANTI-01" in body["gate_ids"]
    assert "chat" in body["job_envelope_forbidden_keys"]
    assert "answer" in body["artifact_forbidden_top_level_keys"]
