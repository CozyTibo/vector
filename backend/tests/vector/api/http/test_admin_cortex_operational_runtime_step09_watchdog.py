"""Admin HTTP — Phase 08.5 Step 09 continuity watchdog."""

from __future__ import annotations

import pytest
from starlette.testclient import TestClient

pytestmark = pytest.mark.integration


def test_admin_catalog_continuity_watchdog_ok(
    monkeypatch: pytest.MonkeyPatch,
    client: TestClient,
) -> None:
    monkeypatch.setenv("ADMIN_PASSWORD", "integration-admin-password")
    r = client.get(
        "/admin/catalog/cortex/operational-runtime/continuity-watchdog",
        auth=("admin", "integration-admin-password"),
    )
    assert r.status_code == 200
    body = r.json()
    assert body["primary_gate_id"] == "G-P085-WATCH-01"
    assert body["default_interval_seconds"] == 600
    assert body["celery_task_name"] == "vector.cortex.substrate_pipeline.continuity_watchdog"


def test_admin_catalog_continuity_watchdog_gate_ok(
    monkeypatch: pytest.MonkeyPatch,
    client: TestClient,
) -> None:
    monkeypatch.setenv("ADMIN_PASSWORD", "integration-admin-password")
    r = client.get(
        "/admin/catalog/cortex/operational-runtime/continuity-watchdog-gate",
        auth=("admin", "integration-admin-password"),
    )
    assert r.status_code == 200
    assert r.json()["passed"] is True


def test_admin_run_continuity_watchdog_ok(
    monkeypatch: pytest.MonkeyPatch,
    client: TestClient,
) -> None:
    monkeypatch.setenv("ADMIN_PASSWORD", "integration-admin-password")
    r = client.post(
        "/admin/catalog/cortex/substrate-pipeline/continuity-watchdog/run",
        params={"auto_recover": "false"},
        auth=("admin", "integration-admin-password"),
    )
    assert r.status_code == 200
    body = r.json()
    assert "audit" in body
    assert body["audit"]["gate_id"] == "G-P085-WATCH-01"
