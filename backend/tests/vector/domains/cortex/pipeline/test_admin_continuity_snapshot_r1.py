"""R1 — admin continuity snapshot writer/reader tests."""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy.orm import Session

from vector.domains.cortex.pipeline.admin_continuity_snapshot import (
    build_admin_continuity_snapshot_payload_v1,
    read_admin_continuity_snapshot_v1,
    refresh_admin_continuity_snapshot_v1,
)
from vector.infrastructure.db.models.membership import TenantMembership
from vector.infrastructure.db.models.tenant import Tenant
from vector.infrastructure.db.models.user import User

pytestmark = pytest.mark.integration


def _tenant(db_session: Session) -> uuid.UUID:
    user = User(email=f"snap-{uuid.uuid4().hex[:10]}@example.com", full_name="Snap")
    tenant = Tenant(
        company_name="Snap Co",
        primary_email=user.email,
        email_domain="example.com",
        slug=f"snap-{uuid.uuid4().hex[:8]}",
        status="active",
        workspace_access_enabled=True,
    )
    db_session.add_all([user, tenant])
    db_session.flush()
    db_session.add(TenantMembership(tenant_id=tenant.id, user_id=user.id, role="owner"))
    db_session.flush()
    return tenant.id


def test_refresh_admin_continuity_snapshot_persists_row(db_session: Session) -> None:
    tid = _tenant(db_session)
    db_session.commit()
    payload = build_admin_continuity_snapshot_payload_v1(db_session, tenant_id=tid)
    assert payload["schema_version"] == 1
    assert "graph_summary_json" in payload
    refresh_admin_continuity_snapshot_v1(db_session, tenant_id=tid)
    db_session.commit()
    read = read_admin_continuity_snapshot_v1(db_session, tenant_id=tid)
    assert read["available"] is True
    assert read["graph_summary"] is not None
