"""Operator people directory routes."""

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
    user = User(email=f"people-{uuid.uuid4().hex[:10]}@example.com", full_name="People Test")
    tenant = Tenant(
        company_name="People Co",
        primary_email=user.email,
        email_domain="example.com",
        slug=f"people-{uuid.uuid4().hex[:8]}",
        status="active",
        workspace_access_enabled=True,
    )
    db_session.add_all([user, tenant])
    db_session.flush()
    db_session.add(TenantMembership(tenant_id=tenant.id, user_id=user.id, role="owner"))
    db_session.flush()
    return tenant.id


def test_operator_people_directory_empty(client: TestClient, db_session: Session) -> None:
    tid = _tenant(db_session)
    db_session.commit()
    res = client.get(f"/admin/tenants/{tid}/cortex/operator/people")
    assert res.status_code == 200
    body = res.json()
    assert body["surface_kind"] == "operator_people_directory_v1"
    assert body["people"] == []
    assert body["total"] == 0


def test_operator_people_directory_with_auth_graph_link(
    client: TestClient,
    db_session: Session,
) -> None:
    from vector.infrastructure.db.models.cortex_org_entity import CortexOrgEntity
    from vector.infrastructure.db.models.cortex_org_link import CortexOrgLink

    tid = _tenant(db_session)
    e1 = CortexOrgEntity(
        id=uuid.uuid4(),
        tenant_id=tid,
        entity_kind="human_actor",
        lifecycle_state="active",
        identity_key_fingerprint="a" * 64,
        metadata_json={"projection_kind": "github_user", "github_login": "octocat"},
        engine_build_ref="test",
    )
    e2 = CortexOrgEntity(
        id=uuid.uuid4(),
        tenant_id=tid,
        entity_kind="human_actor",
        lifecycle_state="active",
        identity_key_fingerprint="b" * 64,
        metadata_json={"projection_kind": "slack_user", "slack_user_id": "U123"},
        engine_build_ref="test",
    )
    link = CortexOrgLink(
        id=uuid.uuid4(),
        tenant_id=tid,
        link_type="org.test_link",
        source_entity_id=e1.id,
        target_entity_id=e2.id,
        evidence_raw_record_ids=[1],
        rule_id=None,
        confidence_class="test",
        link_authority="authoritative",
        link_class="authoritative",
        metadata_json={},
        engine_build_ref="test",
    )
    db_session.add_all([e1, e2, link])
    db_session.commit()

    res = client.get(f"/admin/tenants/{tid}/cortex/operator/people")
    assert res.status_code == 200
    body = res.json()
    assert body["total"] == 1
    assert len(body["people"]) == 1
    person = body["people"][0]
    assert person["in_auth_graph"] is True
    assert person["linked_account_count"] == 2


def test_operator_person_profile_not_found(client: TestClient, db_session: Session) -> None:
    tid = _tenant(db_session)
    db_session.commit()
    missing = uuid.uuid4()
    res = client.get(f"/admin/tenants/{tid}/cortex/operator/people/{missing}")
    assert res.status_code == 404
    assert res.json()["detail"] == "person_not_found"
