"""Phase 07 Step 24 — admin retrieval operator workflows HTTP surface."""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy.orm import Session
from starlette.testclient import TestClient

from vector.domains.cortex.retrieval.retrieval_operator_workflows import (
    GP07_WF01_GATE_ID_V1,
    RETRIEVAL_INDEX_REBUILD_CONFIRM_PHRASE_V1,
)

pytestmark = pytest.mark.integration


def _tenant_with_owner(db_session: Session) -> uuid.UUID:
    from vector.infrastructure.db.models.membership import TenantMembership
    from vector.infrastructure.db.models.tenant import Tenant
    from vector.infrastructure.db.models.user import User

    user = User(email=f"p7wfadm-{uuid.uuid4().hex[:10]}@example.com", full_name="P7 WF Admin")
    tenant = Tenant(
        company_name="P7WFADM",
        primary_email=user.email,
        email_domain="example.com",
        slug=f"p7wfadm-{uuid.uuid4().hex[:8]}",
        status="active",
        workspace_access_enabled=True,
    )
    db_session.add_all([user, tenant])
    db_session.flush()
    db_session.add(TenantMembership(tenant_id=tenant.id, user_id=user.id, role="owner"))
    db_session.flush()
    return tenant.id


def test_admin_retrieval_workflows_ok(
    monkeypatch: pytest.MonkeyPatch,
    client: TestClient,
    db_session: Session,
) -> None:
    monkeypatch.setenv("ADMIN_PASSWORD", "integration-admin-password")
    tid = _tenant_with_owner(db_session)
    db_session.commit()

    r = client.get(
        f"/admin/tenants/{tid}/cortex/retrieval/workflows",
        auth=("admin", "integration-admin-password"),
    )
    assert r.status_code == 200
    body = r.json()
    assert body["gate_id"] == GP07_WF01_GATE_ID_V1
    assert len(body["workflows"]) == 3
    assert len(body["spa_route_registry"]) >= 16


def test_admin_retrieval_index_rebuild_requires_confirmation(
    monkeypatch: pytest.MonkeyPatch,
    client: TestClient,
    db_session: Session,
) -> None:
    monkeypatch.setenv("ADMIN_PASSWORD", "integration-admin-password")
    tid = _tenant_with_owner(db_session)
    db_session.commit()

    bad = client.post(
        f"/admin/tenants/{tid}/cortex/retrieval/index/rebuild",
        json={"confirmation_phrase": "wrong"},
        auth=("admin", "integration-admin-password"),
    )
    assert bad.status_code == 403
    assert bad.json()["error"] == "confirmation_phrase_invalid"

    ok = client.post(
        f"/admin/tenants/{tid}/cortex/retrieval/index/rebuild",
        json={"confirmation_phrase": RETRIEVAL_INDEX_REBUILD_CONFIRM_PHRASE_V1},
        auth=("admin", "integration-admin-password"),
    )
    assert ok.status_code in (200, 400)


def test_admin_retrieval_index_bootstrap_ok(
    monkeypatch: pytest.MonkeyPatch,
    client: TestClient,
    db_session: Session,
) -> None:
    monkeypatch.setenv("ADMIN_PASSWORD", "integration-admin-password")
    tid = _tenant_with_owner(db_session)
    db_session.commit()

    r = client.post(
        f"/admin/tenants/{tid}/cortex/retrieval/index/bootstrap",
        json={},
        auth=("admin", "integration-admin-password"),
    )
    assert r.status_code == 200
    body = r.json()
    assert body["build_state"] == "PUBLISHED"
    assert "index_epoch" in body
