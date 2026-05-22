"""Wave 3 — phase summary + explorer for identity and graph."""

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
    user = User(email=f"phase-{uuid.uuid4().hex[:10]}@example.com", full_name="Phase")
    tenant = Tenant(
        company_name="Phase Co",
        primary_email=user.email,
        email_domain="example.com",
        slug=f"phase-{uuid.uuid4().hex[:8]}",
        status="active",
        workspace_access_enabled=True,
    )
    db_session.add_all([user, tenant])
    db_session.flush()
    db_session.add(TenantMembership(tenant_id=tenant.id, user_id=user.id, role="owner"))
    db_session.flush()
    return tenant.id


@pytest.mark.parametrize("phase", ["identity", "graph", "reconstruction", "retrieval", "synthesis"])
def test_phase_summary_and_explorer(
    client: TestClient,
    db_session: Session,
    phase: str,
) -> None:
    tid = _tenant(db_session)
    db_session.commit()
    summary = client.get(f"/admin/tenants/{tid}/cortex/pipeline/phases/{phase}/summary")
    assert summary.status_code == 200
    body = summary.json()
    assert body["surface_kind"] == "phase_summary"
    assert body["phase"] == phase
    assert "status" in body
    assert "blockers" in body

    explorer = client.get(
        f"/admin/tenants/{tid}/cortex/pipeline/phases/{phase}/explorer",
        params={"limit": 10, "offset": 0},
    )
    assert explorer.status_code == 200
    ex = explorer.json()
    assert ex["surface_kind"] == "phase_explorer"
    assert ex["phase"] == phase
    assert isinstance(ex["columns"], list)
    assert isinstance(ex["items"], list)


def test_identity_summary_includes_certification_warnings_key(
    client: TestClient,
    db_session: Session,
) -> None:
    tid = _tenant(db_session)
    db_session.commit()
    res = client.get(f"/admin/tenants/{tid}/cortex/pipeline/phases/identity/summary")
    assert res.status_code == 200
    body = res.json()
    assert "certification_warnings" in body
    assert isinstance(body["certification_warnings"], list)
    cards = body.get("cards")
    assert isinstance(cards, dict)
    assert "org_handles" in cards
    assert "value" in cards["org_handles"]


@pytest.mark.parametrize("phase", ["identity", "graph", "ingestion"])
def test_phase_summary_detail_matches_summary_extras(
    client: TestClient,
    db_session: Session,
    phase: str,
) -> None:
    tid = _tenant(db_session)
    db_session.commit()
    full = client.get(f"/admin/tenants/{tid}/cortex/pipeline/phases/{phase}/summary").json()
    detail = client.get(
        f"/admin/tenants/{tid}/cortex/pipeline/phases/{phase}/summary-detail"
    ).json()
    assert detail["surface_kind"] == "phase_summary_detail"
    nested = client.get(
        f"/admin/tenants/{tid}/cortex/pipeline/phases/{phase}/summary/detail"
    )
    assert nested.status_code == 200
    assert detail["phase"] == phase
    for key, value in detail.items():
        if key in ("surface_kind", "phase", "tenant_id"):
            continue
        assert full.get(key) == value
