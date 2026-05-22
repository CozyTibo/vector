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
    ingestion = next(p for p in body["phases"] if p["phase"] == "ingestion")
    assert ingestion["status_label"]
    assert ingestion["object_count_label"]
    assert "issues" in ingestion
    for phase in body["phases"]:
        assert phase["status_label"]
        assert "object_count_label" in phase
    assert "execution" in body
    assert isinstance(body["attention"], list)
    assert isinstance(body["recent_ingestion_runs"], list)
    assert body["next_scheduled_ingestion"]["status"] in {
        "disabled",
        "paused",
        "no_connectors",
        "running",
        "eligible_now",
        "waiting_cooldown",
    }
    canonical = next(p for p in body["phases"] if p["phase"] == "canonical")
    assert canonical["backlog_count"] is None or isinstance(canonical["backlog_count"], int)


def test_pipeline_overview_slices_match_full(client: TestClient, db_session: Session) -> None:
    tid = _tenant(db_session)
    db_session.commit()
    full = client.get(f"/admin/tenants/{tid}/cortex/pipeline/overview").json()
    execution = client.get(f"/admin/tenants/{tid}/cortex/pipeline/overview/execution").json()
    phases = client.get(f"/admin/tenants/{tid}/cortex/pipeline/overview/phases").json()
    ingestion = client.get(f"/admin/tenants/{tid}/cortex/pipeline/overview/ingestion").json()

    assert execution["surface_kind"] == "pipeline_overview_execution"
    assert phases["surface_kind"] == "pipeline_overview_phases"
    assert ingestion["surface_kind"] == "pipeline_overview_ingestion"
    assert execution["execution"] == full["execution"]
    assert phases["phases"] == full["phases"]
    assert phases["attention"] == full["attention"]
    assert ingestion["scheduler"] == full["scheduler"]
    assert ingestion["runnable_connectors"] == full["runnable_connectors"]
    assert ingestion["recent_ingestion_runs"] == full["recent_ingestion_runs"]
    assert ingestion["next_scheduled_ingestion"] == full["next_scheduled_ingestion"]
