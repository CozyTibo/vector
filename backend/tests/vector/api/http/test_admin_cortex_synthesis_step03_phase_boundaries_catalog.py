"""Phase 08 Step 03 — admin synthesis phase-boundary doctrine catalog HTTP surface."""

from __future__ import annotations

import pytest
from starlette.testclient import TestClient

pytestmark = pytest.mark.integration


def test_admin_catalog_cortex_synthesis_phase_boundaries_ok(
    monkeypatch: pytest.MonkeyPatch,
    client: TestClient,
) -> None:
    monkeypatch.setenv("ADMIN_PASSWORD", "integration-admin-password")

    r = client.get(
        "/admin/catalog/cortex/synthesis/phase-boundaries",
        auth=("admin", "integration-admin-password"),
    )
    assert r.status_code == 200
    body = r.json()
    assert body["surface_kind"] == "doctrine_catalog"
    assert "SYN-BND-07-01" in body["rule_ids"]
    assert "SYN-BND-09-01" in body["rule_ids"]
    assert body["sd_upstream_rd"] == "SD-UPSTREAM-RD"
