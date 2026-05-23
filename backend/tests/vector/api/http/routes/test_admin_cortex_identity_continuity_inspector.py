"""Identity continuity inspector API tests."""

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
    user = User(email=f"ici-{uuid.uuid4().hex[:10]}@example.com", full_name="ICI")
    tenant = Tenant(
        company_name="ICI Co",
        primary_email=user.email,
        email_domain="example.com",
        slug=f"ici-{uuid.uuid4().hex[:8]}",
        status="active",
        workspace_access_enabled=True,
    )
    db_session.add_all([user, tenant])
    db_session.flush()
    db_session.add(TenantMembership(tenant_id=tenant.id, user_id=user.id, role="owner"))
    db_session.flush()
    return tenant.id


def test_identity_continuity_inspector_tenant(client: TestClient, db_session: Session) -> None:
    tid = _tenant(db_session)
    db_session.commit()
    res = client.get(f"/admin/tenants/{tid}/cortex/pipeline/identity-continuity-inspector")
    assert res.status_code == 200
    body = res.json()
    assert body["surface_kind"] == "identity_continuity_inspector"
    assert "identity_continuity" in body


def test_identity_continuity_search_requires_param(client: TestClient, db_session: Session) -> None:
    tid = _tenant(db_session)
    db_session.commit()
    res = client.get(f"/admin/tenants/{tid}/cortex/identity/continuity-inspector/search")
    assert res.status_code == 400


def test_identity_continuity_search_github_login(client: TestClient, db_session: Session) -> None:
    tid = _tenant(db_session)
    db_session.commit()
    res = client.get(
        f"/admin/tenants/{tid}/cortex/identity/continuity-inspector/search",
        params={"github_login": "octocat"},
    )
    assert res.status_code == 200
    body = res.json()
    assert body["surface_kind"] == "identity_continuity_search"
    assert isinstance(body["matches"], list)


def test_identity_continuity_search_canonical_entity_id_invalid(
    client: TestClient, db_session: Session
) -> None:
    tid = _tenant(db_session)
    db_session.commit()
    res = client.get(
        f"/admin/tenants/{tid}/cortex/identity/continuity-inspector/search",
        params={"canonical_entity_id": "not-a-uuid"},
    )
    assert res.status_code == 200
    body = res.json()
    assert any(m.get("error") == "invalid_uuid" for m in body["matches"])


def test_identity_continuity_entity_not_found(client: TestClient, db_session: Session) -> None:
    tid = _tenant(db_session)
    db_session.commit()
    missing = uuid.uuid4()
    res = client.get(f"/admin/tenants/{tid}/cortex/identity/continuity-inspector/entities/{missing}")
    assert res.status_code == 404


def test_identity_continuity_entity_evidence_not_found(client: TestClient, db_session: Session) -> None:
    tid = _tenant(db_session)
    db_session.commit()
    missing = uuid.uuid4()
    res = client.get(
        f"/admin/tenants/{tid}/cortex/identity/continuity-inspector/entities/{missing}/evidence"
    )
    assert res.status_code == 404


def test_identity_continuity_entity_candidates_not_found(client: TestClient, db_session: Session) -> None:
    tid = _tenant(db_session)
    db_session.commit()
    missing = uuid.uuid4()
    res = client.get(
        f"/admin/tenants/{tid}/cortex/identity/continuity-inspector/entities/{missing}/candidates"
    )
    assert res.status_code == 404
