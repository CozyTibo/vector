"""M8 — consolidated admin execution surface and 410 deprecated bypass routes."""

from __future__ import annotations

import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session


def _tenant(db_session: Session) -> uuid.UUID:
    from vector.infrastructure.db.models.tenant import Tenant

    slug = f"m8exec-{uuid.uuid4().hex[:8]}"
    row = Tenant(
        company_name="M8 Execution Tenant",
        primary_email=f"{slug}@example.com",
        email_domain="example.com",
        slug=slug,
        status="active",
        workspace_access_enabled=True,
    )
    db_session.add(row)
    db_session.flush()
    return row.id


@pytest.mark.integration
def test_execution_state_inspect_ok(
    monkeypatch: pytest.MonkeyPatch,
    client: TestClient,
    db_session: Session,
) -> None:
    monkeypatch.setenv("ADMIN_PASSWORD", "integration-admin-password")
    tid = _tenant(db_session)
    db_session.commit()
    r = client.get(
        f"/admin/tenants/{tid}/cortex/execution/state",
        auth=("admin", "integration-admin-password"),
    )
    assert r.status_code == 200
    body = r.json()
    assert body["surface_kind"] == "execution_inspect"
    assert body["tenant_id"] == str(tid)


@pytest.mark.integration
def test_materialize_backlog_route_not_registered(
    monkeypatch: pytest.MonkeyPatch,
    client: TestClient,
    db_session: Session,
) -> None:
    monkeypatch.setenv("ADMIN_PASSWORD", "integration-admin-password")
    tid = _tenant(db_session)
    db_session.commit()
    r = client.post(
        f"/admin/tenants/{tid}/cortex/canonical/transform/materialize-backlog",
        auth=("admin", "integration-admin-password"),
        json={"bundle_id": "bundle-test", "batch_limit": 10, "dry_run": True},
    )
    assert r.status_code == 404


@pytest.mark.integration
def test_graph_density_promotion_run_route_registered(
    monkeypatch: pytest.MonkeyPatch,
    client: TestClient,
    db_session: Session,
) -> None:
    monkeypatch.setenv("ADMIN_PASSWORD", "integration-admin-password")
    tid = _tenant(db_session)
    db_session.commit()
    r = client.post(
        f"/admin/tenants/{tid}/cortex/operational-runtime/graph-density-promotion/run",
        auth=("admin", "integration-admin-password"),
        json={"force": False, "trigger": "manual"},
    )
    assert r.status_code == 200
    assert r.json()["gate_id"] == "G-P085-PROMO-01"
