"""Wave S0 — semantic readiness admin API."""

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
    user = User(email=f"sr-{uuid.uuid4().hex[:10]}@example.com", full_name="SR")
    tenant = Tenant(
        company_name="SR Co",
        primary_email=user.email,
        email_domain="example.com",
        slug=f"sr-{uuid.uuid4().hex[:8]}",
        status="active",
        workspace_access_enabled=True,
    )
    db_session.add_all([user, tenant])
    db_session.flush()
    db_session.add(TenantMembership(tenant_id=tenant.id, user_id=user.id, role="owner"))
    db_session.flush()
    return tenant.id


def test_semantic_readiness_endpoint(client: TestClient, db_session: Session) -> None:
    tid = _tenant(db_session)
    db_session.commit()
    res = client.get(f"/admin/tenants/{tid}/cortex/pipeline/semantic-readiness")
    assert res.status_code == 200
    body = res.json()
    assert body["surface_kind"] == "semantic_readiness"
    assert body["product_substrate"] == "retrieval"
    g = body["graph_truth"]
    assert g["primary_metric_key"] == "unique_auth_pairs"
    assert g["auth_edge_rows_deprecated_primary"] is True
    assert g["unique_auth_pairs"] == 0
    panel = body["semantic_operator_panel"]
    assert len(panel) == 6
    assert panel[0]["key"] == "unique_auth_pairs"


def test_execution_overview_includes_semantic_readiness(
    client: TestClient, db_session: Session
) -> None:
    tid = _tenant(db_session)
    db_session.commit()
    res = client.get(f"/admin/tenants/{tid}/cortex/pipeline/overview/execution")
    assert res.status_code == 200
    body = res.json()
    sr = body.get("semantic_readiness")
    assert sr is not None
    assert sr["graph_truth"]["unique_auth_pairs"] == 0
    assert len(sr["semantic_operator_panel"]) == 6


def test_execution_overview_hides_legacy_primary_kpi_card_fields(
    client: TestClient, db_session: Session
) -> None:
    tid = _tenant(db_session)
    db_session.commit()
    res = client.get(f"/admin/tenants/{tid}/cortex/pipeline/overview/execution")
    assert res.status_code == 200
    kpi = res.json().get("operator_primary_kpi")
    assert kpi is not None
    assert kpi.get("hide_from_overview") is True
    assert kpi.get("semantic_primary_active") is True
