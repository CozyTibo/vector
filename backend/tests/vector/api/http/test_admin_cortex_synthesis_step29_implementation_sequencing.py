"""Phase 08 Step 29 — admin synthesis implementation sequencing HTTP surface."""

from __future__ import annotations

import pytest
from starlette.testclient import TestClient

pytestmark = pytest.mark.integration


def test_admin_catalog_synthesis_implementation_sequencing(
    monkeypatch: pytest.MonkeyPatch,
    client: TestClient,
) -> None:
    monkeypatch.setenv("ADMIN_PASSWORD", "integration-admin-password")
    r = client.get(
        "/admin/catalog/cortex/synthesis/implementation-sequencing",
        auth=("admin", "integration-admin-password"),
    )
    assert r.status_code == 200
    body = r.json()
    assert body["surface_kind"] == "doctrine_catalog"
    assert body["all_waves_0_5_passed"] is True
    assert body["phase09_readiness_passed"] is True
    assert len(body["tracker_step_wave_map"]) == 35
    assert body["wave_ids"] == ["0", "1", "2", "3", "4", "5", "6", "7"]
