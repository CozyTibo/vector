"""Operator admin v2 retrieval/synthesis/execution inspect (R5)."""

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
    user = User(email=f"opr5-{uuid.uuid4().hex[:10]}@example.com", full_name="Op R5")
    tenant = Tenant(
        company_name="Op R5 Co",
        primary_email=user.email,
        email_domain="example.com",
        slug=f"opr5-{uuid.uuid4().hex[:8]}",
        status="active",
        workspace_access_enabled=True,
    )
    db_session.add_all([user, tenant])
    db_session.flush()
    db_session.add(TenantMembership(tenant_id=tenant.id, user_id=user.id, role="owner"))
    db_session.flush()
    return tenant.id


def test_operator_retrieval_epochs_when_flag_enabled(
    client: TestClient,
    db_session: Session,
) -> None:
    tid = _tenant(db_session)
    db_session.commit()
    res = client.get(f"/admin/tenants/{tid}/cortex/operator/inspect/retrieval/epochs")
    assert res.status_code == 200
    body = res.json()
    assert body["surface_kind"] == "operator_retrieval_epochs_v1"
    assert body["epochs"] == []


def test_operator_retrieval_entries_requires_query(
    client: TestClient,
    db_session: Session,
) -> None:
    tid = _tenant(db_session)
    db_session.commit()
    res = client.get(f"/admin/tenants/{tid}/cortex/operator/inspect/retrieval/entries")
    assert res.status_code == 400


def test_operator_synthesis_jobs_when_flag_enabled(
    client: TestClient,
    db_session: Session,
) -> None:
    tid = _tenant(db_session)
    db_session.commit()
    res = client.get(
        f"/admin/tenants/{tid}/cortex/operator/inspect/synthesis/jobs",
        params={"status": "failed", "limit": 10},
    )
    assert res.status_code == 200
    body = res.json()
    assert body["surface_kind"] == "operator_synthesis_jobs_v1"
    assert body["jobs"] == []
    assert body["recent_artifacts"] == []


def test_operator_execution_thread_requires_query(
    client: TestClient,
    db_session: Session,
) -> None:
    tid = _tenant(db_session)
    db_session.commit()
    res = client.get(f"/admin/tenants/{tid}/cortex/operator/inspect/execution/thread")
    assert res.status_code == 400


def test_operator_retrieval_lineage_org_link(
    client: TestClient,
    db_session: Session,
) -> None:
    tid = _tenant(db_session)
    db_session.commit()
    res = client.get(
        f"/admin/tenants/{tid}/cortex/operator/inspect/retrieval/lineage/org_link/test-ref",
    )
    assert res.status_code == 200
    body = res.json()
    assert body["surface_kind"] == "operator_retrieval_lineage_v1"
    assert body["artifact_kind"] == "org_link"
    assert "chain" in body
