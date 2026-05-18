"""Phase 08 Step 13 — admin synthesis SD omission explorer HTTP surface."""

from __future__ import annotations

import pytest
from starlette.testclient import TestClient

from vector.domains.cortex.synthesis.synthesis_bounded_caps import GP08_DEG01_GATE_ID_V1

pytestmark = pytest.mark.integration


def test_admin_get_synthesis_sd_explorer_ok(
    monkeypatch: pytest.MonkeyPatch,
    client: TestClient,
) -> None:
    monkeypatch.setenv("ADMIN_PASSWORD", "integration-admin-password")
    r = client.get(
        "/admin/catalog/cortex/synthesis/sd-explorer",
        auth=("admin", "integration-admin-password"),
    )
    assert r.status_code == 200
    body = r.json()
    assert body["surface_kind"] == "doctrine_catalog"
    assert body["gate_id"] == GP08_DEG01_GATE_ID_V1
    assert "SD-CAP-CLAIMS" in body["sd_codes_registry"]
    assert body["default_caps"]["max_claims"] == 64
