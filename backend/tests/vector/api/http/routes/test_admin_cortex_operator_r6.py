"""R6 — legacy cortex admin catalog routes removed; keep-list endpoints remain."""

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
    user = User(email=f"r6-{uuid.uuid4().hex[:10]}@example.com", full_name="R6")
    tenant = Tenant(
        company_name="R6 Co",
        primary_email=user.email,
        email_domain="example.com",
        slug=f"r6-{uuid.uuid4().hex[:8]}",
        status="active",
        workspace_access_enabled=True,
    )
    db_session.add_all([user, tenant])
    db_session.flush()
    db_session.add(TenantMembership(tenant_id=tenant.id, user_id=user.id, role="owner"))
    db_session.flush()
    return tenant.id


@pytest.mark.parametrize(
    "path_suffix",
    [
        "cortex/pipeline/overview",
        "cortex/pipeline/semantic-readiness",
        "cortex/operational-runtime/health",
        "cortex/retrieval/legality",
        "cortex/synthesis/overview",
    ],
)
def test_r6_removed_legacy_routes_return_404(
    client: TestClient,
    db_session: Session,
    path_suffix: str,
) -> None:
    tid = _tenant(db_session)
    db_session.commit()
    res = client.get(f"/admin/tenants/{tid}/{path_suffix}")
    assert res.status_code == 404


def test_r6_retrieval_health_still_available(
    client: TestClient,
    db_session: Session,
) -> None:
    tid = _tenant(db_session)
    db_session.commit()
    res = client.get(f"/admin/tenants/{tid}/cortex/retrieval/health")
    assert res.status_code == 200


def test_r6_synthesis_jobs_still_available(
    client: TestClient,
    db_session: Session,
) -> None:
    tid = _tenant(db_session)
    db_session.commit()
    res = client.get(f"/admin/tenants/{tid}/cortex/synthesis/jobs")
    assert res.status_code == 200
