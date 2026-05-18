"""Phase 08 Step 26 — admin synthesis verification harness HTTP surface."""

from __future__ import annotations

import pytest
from starlette.testclient import TestClient

pytestmark = pytest.mark.integration


def test_admin_catalog_synthesis_verification_harness_catalog(
    monkeypatch: pytest.MonkeyPatch,
    client: TestClient,
) -> None:
    monkeypatch.setenv("ADMIN_PASSWORD", "integration-admin-password")
    r = client.get(
        "/admin/catalog/cortex/synthesis/verification-harness",
        auth=("admin", "integration-admin-password"),
    )
    assert r.status_code == 200
    body = r.json()
    assert body["surface_kind"] == "verification_probe"
    assert len(body["gate_ids"]) == 19
    assert body.get("harness_run") is None


def test_admin_catalog_synthesis_verification_harness_pr_blocking_run(
    monkeypatch: pytest.MonkeyPatch,
    client: TestClient,
) -> None:
    monkeypatch.setenv("ADMIN_PASSWORD", "integration-admin-password")
    r = client.get(
        "/admin/catalog/cortex/synthesis/verification-harness?run=pr_blocking",
        auth=("admin", "integration-admin-password"),
    )
    assert r.status_code == 200
    body = r.json()
    assert body["run_mode"] == "pr_blocking"
    assert body["harness_run"]["passed"] is True
    assert body["harness_run"]["stages"] == ["A", "B", "C"]
