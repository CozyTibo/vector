"""Admin HTTP — Phase 08.5 Step 06 autonomous progression."""

from __future__ import annotations

import pytest
from starlette.testclient import TestClient

pytestmark = pytest.mark.integration


def test_admin_catalog_autonomous_progression_ok(
    monkeypatch: pytest.MonkeyPatch,
    client: TestClient,
) -> None:
    monkeypatch.setenv("ADMIN_PASSWORD", "integration-admin-password")
    r = client.get(
        "/admin/catalog/cortex/operational-runtime/autonomous-progression",
        auth=("admin", "integration-admin-password"),
    )
    assert r.status_code == 200
    body = r.json()
    assert body["primary_gate_id"] == "G-P085-PROG-01"
    assert body["pipe_rule_id"] == "PIPE-085-01"
    assert "PROG-06-WAIT" in body["progression_law_ids"]


def test_admin_catalog_progression_gate_ok(
    monkeypatch: pytest.MonkeyPatch,
    client: TestClient,
) -> None:
    monkeypatch.setenv("ADMIN_PASSWORD", "integration-admin-password")
    r = client.get(
        "/admin/catalog/cortex/operational-runtime/progression-gate",
        auth=("admin", "integration-admin-password"),
    )
    assert r.status_code == 200
    assert r.json()["passed"] is True
