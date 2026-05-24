"""Operator admin v2 inspect routes (R3)."""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy.orm import Session
from starlette.testclient import TestClient

from vector.infrastructure.db.models.membership import TenantMembership
from vector.infrastructure.db.models.tenant import Tenant
from vector.infrastructure.db.models.user import User

pytestmark = pytest.mark.integration


def _tenant(db_session: Session) -> uuid.UUID:
    user = User(email=f"opr3-{uuid.uuid4().hex[:10]}@example.com", full_name="Op R3")
    tenant = Tenant(
        company_name="Op R3 Co",
        primary_email=user.email,
        email_domain="example.com",
        slug=f"opr3-{uuid.uuid4().hex[:8]}",
        status="active",
        workspace_access_enabled=True,
    )
    db_session.add_all([user, tenant])
    db_session.flush()
    db_session.add(TenantMembership(tenant_id=tenant.id, user_id=user.id, role="owner"))
    db_session.flush()
    return tenant.id


def test_operator_graph_snapshot_when_flag_enabled(
    client: TestClient,
    db_session: Session,
) -> None:
    tid = _tenant(db_session)
    db_session.commit()
    res = client.get(f"/admin/tenants/{tid}/cortex/operator/snapshots/graph")
    assert res.status_code == 200
    body = res.json()
    assert body["surface_kind"] == "operator_graph_snapshot_v1"
    assert body["tenant_id"] == str(tid)
    assert "prose_summary" in body


def test_operator_edge_provenance_requires_query(
    client: TestClient,
    db_session: Session,
) -> None:
    tid = _tenant(db_session)
    db_session.commit()
    res = client.get(f"/admin/tenants/{tid}/cortex/operator/inspect/edges")
    assert res.status_code == 400


def test_operator_islands_list_when_flag_enabled(
    client: TestClient,
    db_session: Session,
) -> None:
    tid = _tenant(db_session)
    db_session.commit()
    res = client.get(f"/admin/tenants/{tid}/cortex/operator/inspect/islands")
    assert res.status_code == 200
    body = res.json()
    assert body["surface_kind"] == "operator_islands_list_v1"
    assert body["island_count"] == 0
    assert body["islands"] == []
