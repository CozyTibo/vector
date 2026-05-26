"""Tests for build_substrate_truth_v1 (Wave 0)."""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy.orm import Session

from vector.domains.cortex.substrate_pipeline.substrate_truth_v1 import (
    SUBSTRATE_TRUTH_SURFACE_KIND,
    build_substrate_truth_v1,
)
from vector.infrastructure.db.models.membership import TenantMembership
from vector.infrastructure.db.models.tenant import Tenant
from vector.infrastructure.db.models.user import User
from vector.settings import get_settings

pytestmark = pytest.mark.integration


def _tenant(db_session: Session) -> uuid.UUID:
    user = User(email=f"st-{uuid.uuid4().hex[:10]}@example.com", full_name="ST")
    tenant = Tenant(
        company_name="ST Co",
        primary_email=user.email,
        email_domain="example.com",
        slug=f"st-{uuid.uuid4().hex[:8]}",
        status="active",
        workspace_access_enabled=True,
    )
    db_session.add_all([user, tenant])
    db_session.flush()
    db_session.add(TenantMembership(tenant_id=tenant.id, user_id=user.id, role="owner"))
    db_session.flush()
    return tenant.id


def test_build_substrate_truth_v1_shape(db_session: Session) -> None:
    tid = _tenant(db_session)
    db_session.commit()
    payload = build_substrate_truth_v1(db_session, tenant_id=tid, settings=get_settings())
    assert payload["surface_kind"] == SUBSTRATE_TRUTH_SURFACE_KIND
    assert payload["tenant_id"] == str(tid)
    assert payload["overall_status"] in ("HEALTHY", "DEGRADED", "BROKEN", "STALLED")
    assert "identity" in payload
    assert "health" in payload["identity"]
    assert "graph" in payload
    assert payload["graph"]["primary_metric_key"] == "unique_auth_pairs"
    assert "queue_ownership" in payload
    assert payload["queue_ownership"]["dirty_owner"] == "mark_dirty_and_enqueue_convergence_v1"
    assert isinstance(payload["operator_guidance"], list)
    assert payload["runtime_flags"]["cortex_post_ingestion_substrate_refresh_enabled"] is True
