"""Phase 03 Step 16 — canonical operator control plane."""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy.orm import Session

from vector.domains.cortex.canonical.canonical_control_plane import (
    CANONICAL_CONTROL_PLANE_SCHEMA_VERSION,
    build_canonical_control_plane,
    verify_phase03_step16_canonical_control_plane_contract,
)
from vector.infrastructure.db.models.membership import TenantMembership
from vector.infrastructure.db.models.tenant import Tenant
from vector.infrastructure.db.models.user import User


def test_control_plane_contract_rejects_empty_payload() -> None:
    vr = verify_phase03_step16_canonical_control_plane_contract(control_plane_payload={})
    assert vr["passed"] is False


def test_control_plane_schema_version() -> None:
    assert CANONICAL_CONTROL_PLANE_SCHEMA_VERSION >= 1


@pytest.mark.integration
def test_build_control_plane_smoke(db_session: Session) -> None:
    user = User(email=f"p316-{uuid.uuid4().hex[:8]}@example.com", full_name="P316 User")
    tenant = Tenant(
        company_name="P316 Co",
        primary_email=user.email,
        email_domain="example.com",
        slug=f"p316-{uuid.uuid4().hex[:10]}",
        status="active",
        workspace_access_enabled=True,
    )
    db_session.add_all([user, tenant])
    db_session.flush()
    db_session.add(TenantMembership(tenant_id=tenant.id, user_id=user.id, role="owner"))
    db_session.commit()

    payload = build_canonical_control_plane(db_session, tenant.id)
    vr = verify_phase03_step16_canonical_control_plane_contract(control_plane_payload=payload)
    assert vr["passed"] is True
    assert payload["canonical_control_plane_schema_version"] == CANONICAL_CONTROL_PLANE_SCHEMA_VERSION
    assert set(payload["logical_information_architecture"].keys()) >= {
        "A_overview",
        "H_recovery",
    }
