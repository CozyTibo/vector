"""P04-06 — merge policies, append-only ledger, gates G-P04-01 / G-P04-MRG-01 / G-P04-13."""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy.orm import Session
from starlette.testclient import TestClient

from vector.domains.cortex.canonical.canonical_verification_engine import run_canonical_verification
from vector.domains.cortex.identity.merge_governance import (
    MergeGovernanceError,
    append_org_merge,
    create_merge_policy,
    list_org_merges,
    merge_public_dict,
    verify_human_merge_two_persona_evidence_policy_static,
    verify_merge_rollback_via_compensating_only_static,
)
from vector.domains.cortex.identity.org_entities import upsert_org_entity
from vector.infrastructure.db.models.membership import TenantMembership
from vector.infrastructure.db.models.tenant import Tenant
from vector.infrastructure.db.models.user import User


def test_static_gates_gp04_mrg01_and_gp04_13() -> None:
    g1 = verify_human_merge_two_persona_evidence_policy_static()
    assert g1["id"] == "G-P04-MRG-01"
    assert g1["passed"] is True
    g13 = verify_merge_rollback_via_compensating_only_static()
    assert g13["id"] == "G-P04-13"
    assert g13["passed"] is True


@pytest.mark.integration
def test_human_merge_requires_two_distinct_evidence_and_rejects_email_only(
    db_session: Session,
) -> None:
    user = User(email=f"p406-{uuid.uuid4().hex[:8]}@example.com", full_name="P406")
    tenant = Tenant(
        company_name="P406 Co",
        primary_email=user.email,
        email_domain="example.com",
        slug=f"p406-{uuid.uuid4().hex[:10]}",
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
        identity_material={"k": "m1"},
        metadata_json={},
    )
    e2 = upsert_org_entity(
        db_session,
        tenant_id=tenant.id,
        entity_kind="human_actor",
        identity_material={"k": "m2"},
        metadata_json={},
    )
    e3 = upsert_org_entity(
        db_session,
        tenant_id=tenant.id,
        entity_kind="human_actor",
        identity_material={"k": "m3"},
        metadata_json={},
    )
    pol = create_merge_policy(db_session, tenant_id=tenant.id, policy_ref="merge.policy.p406.v1")
    db_session.commit()

    with pytest.raises(MergeGovernanceError, match="human_merge_requires_two_distinct"):
        append_org_merge(
            db_session,
            tenant_id=tenant.id,
            merge_kind="human_actor_merge",
            merge_policy_id=pol.id,
            source_entity_ids=[e1.id, e2.id],
            target_entity_id=e3.id,
            evidence_raw_record_ids=[42, 42],
            operator_user_id=user.id,
        )

    with pytest.raises(MergeGovernanceError, match="email_only"):
        append_org_merge(
            db_session,
            tenant_id=tenant.id,
            merge_kind="human_actor_merge",
            merge_policy_id=pol.id,
            source_entity_ids=[e1.id, e2.id],
            target_entity_id=e3.id,
            evidence_raw_record_ids=[101, 202],
            operator_user_id=user.id,
            metadata_json={"evidence_basis": "email_only"},
        )

    row = append_org_merge(
        db_session,
        tenant_id=tenant.id,
        merge_kind="human_actor_merge",
        merge_policy_id=pol.id,
        source_entity_ids=[e1.id, e2.id],
        target_entity_id=e3.id,
        evidence_raw_record_ids=[101, 202],
        operator_user_id=user.id,
    )
    db_session.commit()
    assert row.merge_kind == "human_actor_merge"
    assert merge_public_dict(row)["operator_user_id"] == str(user.id)


@pytest.mark.integration
def test_team_merge_and_compensating_merge(db_session: Session) -> None:
    user = User(email=f"p406b-{uuid.uuid4().hex[:8]}@example.com", full_name="P406b")
    tenant = Tenant(
        company_name="P406b Co",
        primary_email=user.email,
        email_domain="example.com",
        slug=f"p406b-{uuid.uuid4().hex[:10]}",
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
        entity_kind="team",
        identity_material={"k": "t1"},
        metadata_json={},
    )
    e2 = upsert_org_entity(
        db_session,
        tenant_id=tenant.id,
        entity_kind="team",
        identity_material={"k": "t2"},
        metadata_json={},
    )
    pol = create_merge_policy(db_session, tenant_id=tenant.id, policy_ref="merge.policy.team.v1")
    db_session.flush()
    base = append_org_merge(
        db_session,
        tenant_id=tenant.id,
        merge_kind="team_merge",
        merge_policy_id=pol.id,
        source_entity_ids=[e1.id],
        target_entity_id=e2.id,
        evidence_raw_record_ids=[5001],
        operator_user_id=None,
    )
    db_session.flush()
    comp = append_org_merge(
        db_session,
        tenant_id=tenant.id,
        merge_kind="compensating_merge",
        merge_policy_id=pol.id,
        source_entity_ids=[e2.id],
        target_entity_id=e1.id,
        evidence_raw_record_ids=[],
        supersedes_merge_id=base.id,
    )
    db_session.commit()
    assert comp.supersedes_merge_id == base.id


@pytest.mark.integration
def test_verification_includes_merge_gates(db_session: Session) -> None:
    user = User(email=f"p406c-{uuid.uuid4().hex[:8]}@example.com", full_name="P406c")
    tenant = Tenant(
        company_name="P406c Co",
        primary_email=user.email,
        email_domain="example.com",
        slug=f"p406c-{uuid.uuid4().hex[:10]}",
        status="active",
        workspace_access_enabled=True,
    )
    db_session.add_all([user, tenant])
    db_session.flush()
    db_session.add(TenantMembership(tenant_id=tenant.id, user_id=user.id, role="owner"))
    db_session.commit()
    out = run_canonical_verification(db_session, tenant_id=tenant.id, materialization_sample_limit=3, persist=False)
    ids = {g["id"] for g in out["gates"]}
    assert "G-P04-MRG-01" in ids
    assert "G-P04-01" in ids
    assert "G-P04-13" in ids
    assert next(g for g in out["gates"] if g["id"] == "G-P04-MRG-01")["passed"] is True
    assert next(g for g in out["gates"] if g["id"] == "G-P04-13")["passed"] is True


@pytest.mark.integration
def test_admin_merges_list_and_append(
    monkeypatch: pytest.MonkeyPatch,
    client: TestClient,
    db_session: Session,
) -> None:
    monkeypatch.setenv("ADMIN_PASSWORD", "integration-admin-password")
    user = User(email=f"p406d-{uuid.uuid4().hex[:8]}@example.com", full_name="P406d")
    tenant = Tenant(
        company_name="P406d Co",
        primary_email=user.email,
        email_domain="example.com",
        slug=f"p406d-{uuid.uuid4().hex[:10]}",
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
        identity_material={"k": "d1"},
        metadata_json={},
    )
    e2 = upsert_org_entity(
        db_session,
        tenant_id=tenant.id,
        entity_kind="human_actor",
        identity_material={"k": "d2"},
        metadata_json={},
    )
    e3 = upsert_org_entity(
        db_session,
        tenant_id=tenant.id,
        entity_kind="human_actor",
        identity_material={"k": "d3"},
        metadata_json={},
    )
    pol = create_merge_policy(db_session, tenant_id=tenant.id, policy_ref="merge.admin.v1")
    db_session.commit()

    r = client.post(
        f"/admin/tenants/{tenant.id}/cortex/identity/merges",
        auth=("admin", "integration-admin-password"),
        json={
            "merge_kind": "human_actor_merge",
            "merge_policy_id": str(pol.id),
            "source_entity_ids": [str(e1.id), str(e2.id)],
            "target_entity_id": str(e3.id),
            "evidence_raw_record_ids": [9001, 9002],
            "operator_user_id": str(user.id),
        },
    )
    assert r.status_code == 200
    mid = r.json()["id"]

    listed = client.get(
        f"/admin/tenants/{tenant.id}/cortex/identity/merges",
        auth=("admin", "integration-admin-password"),
    )
    assert listed.status_code == 200
    body = listed.json()
    assert body["merges"]
    assert body["merges"][0]["id"] == mid


@pytest.mark.integration
def test_human_merge_rejects_single_evidence_via_admin(
    monkeypatch: pytest.MonkeyPatch,
    client: TestClient,
    db_session: Session,
) -> None:
    monkeypatch.setenv("ADMIN_PASSWORD", "integration-admin-password")
    user = User(email=f"p406e-{uuid.uuid4().hex[:8]}@example.com", full_name="P406e")
    tenant = Tenant(
        company_name="P406e Co",
        primary_email=user.email,
        email_domain="example.com",
        slug=f"p406e-{uuid.uuid4().hex[:10]}",
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
        identity_material={"k": "e1"},
        metadata_json={},
    )
    e2 = upsert_org_entity(
        db_session,
        tenant_id=tenant.id,
        entity_kind="human_actor",
        identity_material={"k": "e2"},
        metadata_json={},
    )
    e3 = upsert_org_entity(
        db_session,
        tenant_id=tenant.id,
        entity_kind="human_actor",
        identity_material={"k": "e3"},
        metadata_json={},
    )
    pol = create_merge_policy(db_session, tenant_id=tenant.id, policy_ref="merge.reject.v1")
    db_session.commit()

    r = client.post(
        f"/admin/tenants/{tenant.id}/cortex/identity/merges",
        auth=("admin", "integration-admin-password"),
        json={
            "merge_kind": "human_actor_merge",
            "merge_policy_id": str(pol.id),
            "source_entity_ids": [str(e1.id), str(e2.id)],
            "target_entity_id": str(e3.id),
            "evidence_raw_record_ids": [1],
            "operator_user_id": str(user.id),
        },
    )
    assert r.status_code == 400
