"""Phase 08 Step 34 — admin synthesis E2E operational catalog HTTP."""

from __future__ import annotations

import pytest
from starlette.testclient import TestClient

from vector.domains.cortex.synthesis.testing import GP08_E2E01_GATE_ID_V1

pytestmark = pytest.mark.integration


def test_admin_e2e_operational_catalog(monkeypatch: pytest.MonkeyPatch, client: TestClient) -> None:
    monkeypatch.setenv("ADMIN_PASSWORD", "integration-admin-password")
    r = client.get(
        "/admin/catalog/cortex/synthesis/e2e-operational",
        auth=("admin", "integration-admin-password"),
    )
    assert r.status_code == 200
    body = r.json()
    assert body["gate_id"] == GP08_E2E01_GATE_ID_V1
    assert body["catalog_id"] == "synthesis_e2e_operational_v1"
    assert len(body["scenarios"]) == 4
    assert len(body["test_modules"]) == 4
