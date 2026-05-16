"""Phase 06 Step 32 — admin reasoning control-plane HTTP surface."""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy.orm import Session
from starlette.testclient import TestClient

from vector.domains.cortex.reasoning.reasoning_control_plane import (
    REASONING_CONTROL_PLANE_CONTRACT_V1,
    REASONING_CONTROL_PLANE_SURFACE_VERSION_V1,
)

pytestmark = pytest.mark.integration


def _tenant_with_owner(db_session: Session) -> uuid.UUID:
    from vector.infrastructure.db.models.membership import TenantMembership
    from vector.infrastructure.db.models.tenant import Tenant
    from vector.infrastructure.db.models.user import User

    user = User(email=f"p6rcp-{uuid.uuid4().hex[:10]}@example.com", full_name="P6 RCP User")
    tenant = Tenant(
        company_name="P6RCP",
        primary_email=user.email,
        email_domain="example.com",
        slug=f"p6rcp-{uuid.uuid4().hex[:8]}",
        status="active",
        workspace_access_enabled=True,
    )
    db_session.add_all([user, tenant])
    db_session.flush()
    db_session.add(TenantMembership(tenant_id=tenant.id, user_id=user.id, role="owner"))
    db_session.flush()
    return tenant.id


def test_admin_cortex_reasoning_control_plane_ok(
    monkeypatch: pytest.MonkeyPatch,
    client: TestClient,
    db_session: Session,
) -> None:
    monkeypatch.setenv("ADMIN_PASSWORD", "integration-admin-password")
    tid = _tenant_with_owner(db_session)
    db_session.commit()

    r = client.get(
        f"/admin/tenants/{tid}/cortex/reasoning/control-plane",
        auth=("admin", "integration-admin-password"),
    )
    assert r.status_code == 200
    body = r.json()
    assert body["tenant_id"] == str(tid)
    assert body["reasoning_control_plane_contract"] == REASONING_CONTROL_PLANE_CONTRACT_V1
    sv = REASONING_CONTROL_PLANE_SURFACE_VERSION_V1
    assert body["reasoning_control_plane_surface_version"] == sv
    assert body["reasoning_control_plane_runtime_schema_version"] >= 1
    assert len(body["surfaces"]) == 12
    assert body["surfaces"][0]["surface_id"]
    assert body["surfaces"][0]["title"]
    assert body["surfaces"][0]["operator_purpose"]
    assert body["dangerous_action_doctrine_ref"]
    assert body["rbac_substrate_alignment_literal"]
