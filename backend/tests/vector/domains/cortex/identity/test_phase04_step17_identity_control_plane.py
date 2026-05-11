"""P04-17 — identity control plane aggregate, G-P04-18 / G-P04-21, admin HTTP."""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy.orm import Session
from starlette.testclient import TestClient

from vector.domains.cortex.canonical.canonical_verification_engine import run_canonical_verification
from vector.domains.cortex.identity.candidate_generation import regenerate_link_candidates
from vector.domains.cortex.identity.control_plane import (
    IDENTITY_CONTROL_PLANE_CONTRACT,
    build_identity_control_plane,
    verify_gp04_18_org_control_plane_replay_freshness,
    verify_gp04_21_identity_control_plane_aggregate,
    verify_identity_control_plane_v1_shape,
)
from vector.domains.cortex.identity.linkage_rules import create_link_rule_version
from vector.domains.cortex.identity.org_entities import upsert_org_entity


def test_candidate_links_card_counts_latest_batch_only(db_session: Session) -> None:
    """Each regen appends a batch; the dashboard card must not multiply totals across runs."""
    from vector.infrastructure.db.models.membership import TenantMembership
    from vector.infrastructure.db.models.tenant import Tenant
    from vector.infrastructure.db.models.user import User

    user = User(email=f"p417d-{uuid.uuid4().hex[:8]}@example.com", full_name="P417d")
    tenant = Tenant(
        company_name="P417d Co",
        primary_email=user.email,
        email_domain="example.com",
        slug=f"p417d-{uuid.uuid4().hex[:10]}",
        status="active",
        workspace_access_enabled=True,
    )
    db_session.add_all([user, tenant])
    db_session.flush()
    db_session.add(TenantMembership(tenant_id=tenant.id, user_id=user.id, role="owner"))
    db_session.flush()
    e1 = upsert_org_entity(
        db_session,
        tenant_id=tenant.id,
        entity_kind="human_actor",
        identity_material={"k": 1},
        metadata_json={},
    )
    e2 = upsert_org_entity(
        db_session,
        tenant_id=tenant.id,
        entity_kind="human_actor",
        identity_material={"k": 2},
        metadata_json={},
    )
    db_session.flush()
    ver = create_link_rule_version(
        db_session,
        tenant_id=tenant.id,
        semantic_version="rule.pack.p417d.v1",
        rules_manifest_json={"rules": [{"id": "stub"}]},
    )
    db_session.flush()
    rows = [
        {
            "link_type": "org.persona_belongs_to_handle",
            "source_entity_id": str(e1.id),
            "target_entity_id": str(e2.id),
            "evidence_raw_record_ids": [],
            "rule_id": "rule.p04.stub_regen_from_entities",
        }
    ]
    for _ in range(2):
        regenerate_link_candidates(
            db_session,
            tenant_id=tenant.id,
            rule_version="rule.pack.p417d.v1",
            rows=rows,
            link_rule_version_id=ver.id,
        )
    db_session.commit()

    payload = build_identity_control_plane(db_session, tenant_id=tenant.id)
    assert payload["cards"]["candidate_links"]["value"] == 1
    sub = payload["continuity_substrate"]
    assert sub["candidate_link_rows_latest_batch"] == 1
    assert sub["candidate_link_rows_total_retained"] == 2


def test_identity_control_plane_v1_shape_empty_tenant(db_session: Session) -> None:
    from vector.infrastructure.db.models.membership import TenantMembership
    from vector.infrastructure.db.models.tenant import Tenant
    from vector.infrastructure.db.models.user import User

    user = User(email=f"p417-{uuid.uuid4().hex[:8]}@example.com", full_name="P417")
    tenant = Tenant(
        company_name="P417 Co",
        primary_email=user.email,
        email_domain="example.com",
        slug=f"p417-{uuid.uuid4().hex[:10]}",
        status="active",
        workspace_access_enabled=True,
    )
    db_session.add_all([user, tenant])
    db_session.flush()
    db_session.add(TenantMembership(tenant_id=tenant.id, user_id=user.id, role="owner"))
    db_session.commit()

    payload = build_identity_control_plane(db_session, tenant_id=tenant.id)
    assert payload["schema_version"] == IDENTITY_CONTROL_PLANE_CONTRACT
    ok, errs = verify_identity_control_plane_v1_shape(payload)
    assert ok, errs
    assert payload["freshness_label"] == "fresh"
    assert payload["cards"]["org_handles"]["value"] == 0
    assert isinstance(payload["cards"]["replay_drift"]["histogram"], dict)

    g21 = verify_gp04_21_identity_control_plane_aggregate(db_session, tenant_id=tenant.id)
    assert g21["id"] == "G-P04-21"
    assert g21["passed"] is True

    g18 = verify_gp04_18_org_control_plane_replay_freshness(db_session, tenant_id=tenant.id)
    assert g18["id"] == "G-P04-18"
    assert g18["passed"] is True


def test_canonical_verification_includes_gp04_18_21(db_session: Session) -> None:
    from vector.infrastructure.db.models.membership import TenantMembership
    from vector.infrastructure.db.models.tenant import Tenant
    from vector.infrastructure.db.models.user import User

    user = User(email=f"p417b-{uuid.uuid4().hex[:8]}@example.com", full_name="P417b")
    tenant = Tenant(
        company_name="P417b Co",
        primary_email=user.email,
        email_domain="example.com",
        slug=f"p417b-{uuid.uuid4().hex[:10]}",
        status="active",
        workspace_access_enabled=True,
    )
    db_session.add_all([user, tenant])
    db_session.flush()
    db_session.add(TenantMembership(tenant_id=tenant.id, user_id=user.id, role="owner"))
    db_session.commit()

    full = run_canonical_verification(db_session, tenant_id=tenant.id, materialization_sample_limit=3, persist=False)
    ids = {g["id"] for g in full["gates"]}
    assert "G-P04-18" in ids
    assert "G-P04-21" in ids


@pytest.mark.integration
def test_admin_identity_control_plane_ok(
    monkeypatch: pytest.MonkeyPatch,
    client: TestClient,
    db_session: Session,
) -> None:
    monkeypatch.setenv("ADMIN_PASSWORD", "integration-admin-password")
    from vector.infrastructure.db.models.membership import TenantMembership
    from vector.infrastructure.db.models.tenant import Tenant
    from vector.infrastructure.db.models.user import User

    user = User(email=f"p417c-{uuid.uuid4().hex[:8]}@example.com", full_name="P417c")
    tenant = Tenant(
        company_name="P417c Co",
        primary_email=user.email,
        email_domain="example.com",
        slug=f"p417c-{uuid.uuid4().hex[:10]}",
        status="active",
        workspace_access_enabled=True,
    )
    db_session.add_all([user, tenant])
    db_session.flush()
    db_session.add(TenantMembership(tenant_id=tenant.id, user_id=user.id, role="owner"))
    db_session.commit()

    r = client.get(
        f"/admin/tenants/{tenant.id}/cortex/identity/control-plane",
        auth=("admin", "integration-admin-password"),
    )
    assert r.status_code == 200
    body = r.json()
    assert body["schema_version"] == IDENTITY_CONTROL_PLANE_CONTRACT
    assert body["tenant_id"] == str(tenant.id)
    assert body["freshness_label"] in ("fresh", "stale")
    assert "org_handles" in body["cards"]
