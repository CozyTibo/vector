"""Graph truth inspector HTTP surface."""

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
    user = User(email=f"gti-{uuid.uuid4().hex[:10]}@example.com", full_name="GTI")
    tenant = Tenant(
        company_name="GTI Co",
        primary_email=user.email,
        email_domain="example.com",
        slug=f"gti-{uuid.uuid4().hex[:8]}",
        status="active",
        workspace_access_enabled=True,
    )
    db_session.add_all([user, tenant])
    db_session.flush()
    db_session.add(TenantMembership(tenant_id=tenant.id, user_id=user.id, role="owner"))
    db_session.flush()
    return tenant.id


def test_graph_truth_inspector_endpoint(client: TestClient, db_session: Session) -> None:
    tid = _tenant(db_session)
    db_session.commit()
    res = client.get(f"/admin/tenants/{tid}/cortex/pipeline/graph-truth-inspector")
    assert res.status_code == 200
    body = res.json()
    assert body["surface_kind"] == "graph_truth_inspector"
    assert "graph_truth" in body
    assert "edge_type_distribution" in body
    assert isinstance(body["edge_type_distribution"], list)
    assert "unpromoted_candidates" in body
    assert body["graph_truth"]["primary_metric_key"] == "unique_auth_pairs"
