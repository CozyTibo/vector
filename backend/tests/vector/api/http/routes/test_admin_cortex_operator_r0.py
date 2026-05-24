"""Operator admin v2 routes (R0 guardrails)."""

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
    user = User(email=f"op-{uuid.uuid4().hex[:10]}@example.com", full_name="Op")
    tenant = Tenant(
        company_name="Op Co",
        primary_email=user.email,
        email_domain="example.com",
        slug=f"op-{uuid.uuid4().hex[:8]}",
        status="active",
        workspace_access_enabled=True,
    )
    db_session.add_all([user, tenant])
    db_session.flush()
    db_session.add(TenantMembership(tenant_id=tenant.id, user_id=user.id, role="owner"))
    db_session.flush()
    return tenant.id


def test_operator_overview_disabled_by_default(
    client: TestClient,
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("CORTEX_ADMIN_V2", "false")
    tid = _tenant(db_session)
    db_session.commit()
    res = client.get(f"/admin/tenants/{tid}/cortex/operator/overview")
    assert res.status_code == 404
    assert res.json()["detail"] == "operator_admin_v2_disabled"


def test_operator_overview_when_flag_enabled(
    client: TestClient,
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("CORTEX_ADMIN_V2", "true")
    tid = _tenant(db_session)
    db_session.commit()
    res = client.get(f"/admin/tenants/{tid}/cortex/operator/overview")
    assert res.status_code == 200
    body = res.json()
    assert body["surface_kind"] == "operator_overview_v1"
    assert body["tenant_id"] == str(tid)
    assert body["query_groups_used"] == 8
    assert len(body["continuity_facts"]) == 5
    assert "phase_07_retrieval" in body["phase_receipts"]
    assert "phase_08_synthesis" in body["phase_receipts"]


def test_admin_build_info_endpoint(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("VECTOR_GIT_SHA", "abc123def4567890abcdef1234567890abcd")
    monkeypatch.setenv("CORTEX_ADMIN_V2", "true")
    res = client.get("/admin/build-info")
    assert res.status_code == 200
    body = res.json()
    assert body["surface_kind"] == "admin_build_info"
    assert body["git_sha"] == "abc123def4567890abcdef1234567890abcd"
    assert body["git_sha_short"] == "abc123d"
    assert body["cortex_admin_v2_enabled"] is True
