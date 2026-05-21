"""Wave 2 — pipeline run API."""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy.orm import Session
from starlette.testclient import TestClient

from vector.domains.cortex.pipeline.pipeline_admin_run import (
    CORTEX_FLUSH_DERIVED_CONFIRM_PHRASE,
    CORTEX_MANUAL_SYNC_CONFIRM_PHRASE,
)
from vector.infrastructure.db.models.membership import TenantMembership
from vector.infrastructure.db.models.tenant import Tenant
from vector.infrastructure.db.models.user import User

pytestmark = pytest.mark.integration


def _tenant(db_session: Session) -> uuid.UUID:
    user = User(email=f"run-{uuid.uuid4().hex[:10]}@example.com", full_name="Run")
    tenant = Tenant(
        company_name="Run Co",
        primary_email=user.email,
        email_domain="example.com",
        slug=f"run-{uuid.uuid4().hex[:8]}",
        status="active",
        workspace_access_enabled=True,
    )
    db_session.add_all([user, tenant])
    db_session.flush()
    db_session.add(TenantMembership(tenant_id=tenant.id, user_id=user.id, role="owner"))
    db_session.flush()
    return tenant.id


def test_pipeline_run_from_ingestion_requires_confirmation(
    client: TestClient,
    db_session: Session,
) -> None:
    tid = _tenant(db_session)
    db_session.commit()
    bad = client.post(
        f"/admin/tenants/{tid}/cortex/pipeline/run",
        json={"mode": "from_ingestion", "confirmation": "wrong"},
    )
    assert bad.status_code == 400
    ok = client.post(
        f"/admin/tenants/{tid}/cortex/pipeline/run",
        json={"mode": "from_ingestion", "confirmation": CORTEX_MANUAL_SYNC_CONFIRM_PHRASE},
    )
    assert ok.status_code == 200
    assert ok.json()["mode"] == "from_ingestion"


def test_pipeline_run_from_phase(client: TestClient, db_session: Session) -> None:
    tid = _tenant(db_session)
    db_session.commit()
    res = client.post(
        f"/admin/tenants/{tid}/cortex/pipeline/run",
        json={"mode": "from_phase", "start_phase": "identity"},
    )
    assert res.status_code == 200
    body = res.json()
    assert body["mode"] == "from_phase"
    assert body["start_phase"] == "identity"
    assert body.get("execution") is not None


def test_pipeline_run_flush_derived_requires_phrase(
    client: TestClient,
    db_session: Session,
) -> None:
    tid = _tenant(db_session)
    db_session.commit()
    res = client.post(
        f"/admin/tenants/{tid}/cortex/pipeline/run",
        json={
            "mode": "flush_and_run",
            "flush_mode": "derived_only",
            "confirmation": CORTEX_FLUSH_DERIVED_CONFIRM_PHRASE,
        },
    )
    assert res.status_code == 200
    assert res.json()["flush_mode"] == "derived_only"
