"""Unit tests for build_operator_overview_v1."""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy.orm import Session

from vector.domains.cortex.pipeline.operator_admin_overview import build_operator_overview_v1
from vector.infrastructure.db.models.membership import TenantMembership
from vector.infrastructure.db.models.tenant import Tenant
from vector.infrastructure.db.models.user import User
from vector.settings import get_settings

pytestmark = pytest.mark.integration


def _tenant(db_session: Session) -> uuid.UUID:
    user = User(email=f"opb-{uuid.uuid4().hex[:10]}@example.com", full_name="OpB")
    tenant = Tenant(
        company_name="OpB Co",
        primary_email=user.email,
        email_domain="example.com",
        slug=f"opb-{uuid.uuid4().hex[:8]}",
        status="active",
        workspace_access_enabled=True,
    )
    db_session.add_all([user, tenant])
    db_session.flush()
    db_session.add(TenantMembership(tenant_id=tenant.id, user_id=user.id, role="owner"))
    db_session.flush()
    return tenant.id


def test_build_operator_overview_v1_bounded(db_session: Session) -> None:
    tid = _tenant(db_session)
    db_session.commit()
    settings = get_settings()
    payload = build_operator_overview_v1(db_session, settings, tenant_id=tid)
    assert payload["surface_kind"] == "operator_overview_v1"
    assert payload["query_groups_used"] == 8
    assert payload["continuity_snapshot"]["available"] is False
    keys = {f["key"] for f in payload["continuity_facts"]}
    assert keys == {"ingestion", "execution", "graph", "retrieval", "synthesis"}
