"""Wave 2 — pipeline overview API."""

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
    user = User(email=f"pipe-{uuid.uuid4().hex[:10]}@example.com", full_name="Pipe")
    tenant = Tenant(
        company_name="Pipe Co",
        primary_email=user.email,
        email_domain="example.com",
        slug=f"pipe-{uuid.uuid4().hex[:8]}",
        status="active",
        workspace_access_enabled=True,
    )
    db_session.add_all([user, tenant])
    db_session.flush()
    db_session.add(TenantMembership(tenant_id=tenant.id, user_id=user.id, role="owner"))
    db_session.flush()
    return tenant.id


def test_pipeline_overview_returns_seven_phases(client: TestClient, db_session: Session) -> None:
    tid = _tenant(db_session)
    db_session.commit()
    res = client.get(f"/admin/tenants/{tid}/cortex/pipeline/overview")
    assert res.status_code == 200
    body = res.json()
    assert body["surface_kind"] == "pipeline_overview"
    assert len(body["phases"]) == 7
    phases = {p["phase"] for p in body["phases"]}
    assert phases == {
        "ingestion",
        "canonical",
        "identity",
        "graph",
        "reconstruction",
        "retrieval",
        "synthesis",
    }
    assert "execution" in body
    assert isinstance(body["attention"], list)
