"""Admin HTTP — Phase 08.5 Step 07 dead-letter / recovery continuity."""

from __future__ import annotations

import pytest
from starlette.testclient import TestClient

pytestmark = pytest.mark.integration


def test_admin_catalog_recovery_continuity_ok(
    monkeypatch: pytest.MonkeyPatch,
    client: TestClient,
) -> None:
    monkeypatch.setenv("ADMIN_PASSWORD", "integration-admin-password")
    r = client.get(
        "/admin/catalog/cortex/operational-runtime/recovery-continuity",
        auth=("admin", "integration-admin-password"),
    )
    assert r.status_code == 200
    body = r.json()
    assert body["primary_gate_id"] == "G-P085-DLQ-01"
    assert body["durable_table"] == "cortex_substrate_pipeline_dead_letters"
    assert "tcre_failed" in body["failure_class_ids"]


def test_admin_catalog_dlq_gate_ok(
    monkeypatch: pytest.MonkeyPatch,
    client: TestClient,
) -> None:
    monkeypatch.setenv("ADMIN_PASSWORD", "integration-admin-password")
    r = client.get(
        "/admin/catalog/cortex/operational-runtime/dlq-gate",
        auth=("admin", "integration-admin-password"),
    )
    assert r.status_code == 200
    assert r.json()["passed"] is True


def test_admin_catalog_substrate_dead_letters_ok(
    monkeypatch: pytest.MonkeyPatch,
    client: TestClient,
) -> None:
    monkeypatch.setenv("ADMIN_PASSWORD", "integration-admin-password")
    r = client.get(
        "/admin/catalog/cortex/substrate-pipeline/dead-letters",
        auth=("admin", "integration-admin-password"),
    )
    assert r.status_code == 200
    assert "dead_letters" in r.json()
