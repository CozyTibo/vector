"""Phase 08 Step 23 — admin synthesis operator workflows HTTP surface."""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy.orm import Session
from starlette.testclient import TestClient

from vector.domains.cortex.synthesis.synthesis_operator_workflows import (
    GP08_WF01_GATE_ID_V1,
    build_synthesis_resynthesize_confirmation_phrase_v1,
)

pytestmark = pytest.mark.integration


def _tenant_with_owner(db_session: Session) -> tuple[uuid.UUID, str]:
    from vector.infrastructure.db.models.membership import TenantMembership
    from vector.infrastructure.db.models.tenant import Tenant
    from vector.infrastructure.db.models.user import User

    slug = f"p8wf23-{uuid.uuid4().hex[:8]}"
    user = User(email=f"p8wf23adm-{uuid.uuid4().hex[:10]}@example.com", full_name="P8 WF23")
    tenant = Tenant(
        company_name="P8WF23",
        primary_email=user.email,
        email_domain="example.com",
        slug=slug,
        status="active",
        workspace_access_enabled=True,
    )
    db_session.add_all([user, tenant])
    db_session.flush()
    db_session.add(TenantMembership(tenant_id=tenant.id, user_id=user.id, role="owner"))
    db_session.flush()
    return tenant.id, slug


def test_admin_synthesis_workflows_ok(
    monkeypatch: pytest.MonkeyPatch,
    client: TestClient,
    db_session: Session,
) -> None:
    monkeypatch.setenv("ADMIN_PASSWORD", "integration-admin-password")
    tid, _slug = _tenant_with_owner(db_session)
    db_session.commit()

    r = client.get(
        f"/admin/tenants/{tid}/cortex/synthesis/workflows",
        auth=("admin", "integration-admin-password"),
    )
    assert r.status_code == 200
    body = r.json()
    assert body["gate_id"] == GP08_WF01_GATE_ID_V1
    assert len(body["workflows"]) == 4
    assert len(body["spa_route_registry"]) >= 16
    assert len(body["ui_api_mapping"]) >= 10


def test_admin_synthesis_jobs_and_omissions_ok(
    monkeypatch: pytest.MonkeyPatch,
    client: TestClient,
    db_session: Session,
) -> None:
    monkeypatch.setenv("ADMIN_PASSWORD", "integration-admin-password")
    tid, _slug = _tenant_with_owner(db_session)
    db_session.commit()

    jobs = client.get(
        f"/admin/tenants/{tid}/cortex/synthesis/jobs",
        auth=("admin", "integration-admin-password"),
    )
    assert jobs.status_code == 200
    assert "jobs" in jobs.json()

    omissions = client.get(
        f"/admin/tenants/{tid}/cortex/synthesis/omissions",
        auth=("admin", "integration-admin-password"),
    )
    assert omissions.status_code == 200
    assert "omission_histogram" in omissions.json()


def test_admin_synthesis_resynthesize_requires_confirmation(
    monkeypatch: pytest.MonkeyPatch,
    client: TestClient,
    db_session: Session,
) -> None:
    monkeypatch.setenv("ADMIN_PASSWORD", "integration-admin-password")
    tid, slug = _tenant_with_owner(db_session)
    db_session.commit()

    bad = client.post(
        f"/admin/tenants/{tid}/cortex/synthesis/jobs/resynthesize",
        json={"confirmation_phrase": "wrong", "envelope": {}},
        auth=("admin", "integration-admin-password"),
    )
    assert bad.status_code == 403
    assert bad.json()["error"] == "confirmation_phrase_invalid"

    ok = client.post(
        f"/admin/tenants/{tid}/cortex/synthesis/jobs/resynthesize",
        json={
            "confirmation_phrase": build_synthesis_resynthesize_confirmation_phrase_v1(slug),
            "envelope": {
                "synthesis_workload_class": "degradation_brief",
                "synthesis_intent": "inspect",
                "execution_partition": "authoritative",
            },
        },
        auth=("admin", "integration-admin-password"),
    )
    assert ok.status_code in (200, 400, 404)
    assert ok.json().get("error") != "confirmation_phrase_invalid"
