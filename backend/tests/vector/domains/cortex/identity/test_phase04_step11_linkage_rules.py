"""P04-11 — linkage rule versions, manifest hash integrity, G-P04-RULE-01, admin HTTP."""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session
from starlette.testclient import TestClient

from vector.domains.cortex.canonical.canonical_verification_engine import run_canonical_verification
from vector.domains.cortex.identity.candidate_generation import regenerate_link_candidates
from vector.domains.cortex.identity.linkage_rules import (
    LINK_RULE_VERSION_SCHEMA_VERSION,
    compute_rules_manifest_sha256,
    create_link_rule_version,
    list_link_rule_version_manifest_mismatches,
    verify_link_rule_rule01_static,
)
from vector.domains.cortex.identity.org_entities import upsert_org_entity
from vector.infrastructure.db.models.cortex_org_link_candidate_batch import CortexOrgLinkCandidateBatch


def test_gp04_rule01_static_passes() -> None:
    st = verify_link_rule_rule01_static()
    assert st["passed"] is True
    assert st["id"] == "G-P04-RULE-01"


def test_manifest_hash_key_order_invariant() -> None:
    a = compute_rules_manifest_sha256({"x": 1, "y": 2})
    b = compute_rules_manifest_sha256({"y": 2, "x": 1})
    assert a == b


def test_create_rule_version_and_regen_pins_batch(db_session: Session) -> None:
    from vector.infrastructure.db.models.membership import TenantMembership
    from vector.infrastructure.db.models.tenant import Tenant
    from vector.infrastructure.db.models.user import User

    user = User(email=f"p411-{uuid.uuid4().hex[:8]}@example.com", full_name="P411")
    tenant = Tenant(
        company_name="P411 Co",
        primary_email=user.email,
        email_domain="example.com",
        slug=f"p411-{uuid.uuid4().hex[:10]}",
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
        semantic_version="rule.pack.p411.v1",
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
    out = regenerate_link_candidates(
        db_session,
        tenant_id=tenant.id,
        rule_version="rule.pack.p411.v1",
        rows=rows,
        link_rule_version_id=ver.id,
    )
    db_session.commit()
    bid = uuid.UUID(out["candidate_batch_id"])
    batch = db_session.get(CortexOrgLinkCandidateBatch, bid)
    assert batch is not None
    assert batch.link_rule_version_id == ver.id
    assert batch.rule_version == "rule.pack.p411.v1"


def test_manifest_mismatch_fails_gate(db_session: Session) -> None:
    from vector.infrastructure.db.models.membership import TenantMembership
    from vector.infrastructure.db.models.tenant import Tenant
    from vector.infrastructure.db.models.user import User

    user = User(email=f"p411m-{uuid.uuid4().hex[:8]}@example.com", full_name="P411m")
    tenant = Tenant(
        company_name="P411m Co",
        primary_email=user.email,
        email_domain="example.com",
        slug=f"p411m-{uuid.uuid4().hex[:10]}",
        status="active",
        workspace_access_enabled=True,
    )
    db_session.add_all([user, tenant])
    db_session.flush()
    db_session.add(TenantMembership(tenant_id=tenant.id, user_id=user.id, role="owner"))
    db_session.flush()
    ver = create_link_rule_version(
        db_session,
        tenant_id=tenant.id,
        semantic_version="rule.bad.hash",
        rules_manifest_json={"ok": True},
    )
    db_session.flush()
    ver.manifest_sha256 = "0" * 64
    db_session.commit()
    assert list_link_rule_version_manifest_mismatches(db_session, tenant_id=tenant.id) == [ver.id]
    out = run_canonical_verification(db_session, tenant_id=tenant.id, persist=False)
    gate = next(g for g in out["gates"] if g["id"] == "G-P04-RULE-01")
    assert gate["passed"] is False


def test_batch_semantic_mismatch_fails_gate(db_session: Session) -> None:
    from vector.infrastructure.db.models.membership import TenantMembership
    from vector.infrastructure.db.models.tenant import Tenant
    from vector.infrastructure.db.models.user import User

    user = User(email=f"p411b-{uuid.uuid4().hex[:8]}@example.com", full_name="P411b")
    tenant = Tenant(
        company_name="P411b Co",
        primary_email=user.email,
        email_domain="example.com",
        slug=f"p411b-{uuid.uuid4().hex[:10]}",
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
        identity_material={"k": 3},
        metadata_json={},
    )
    e2 = upsert_org_entity(
        db_session,
        tenant_id=tenant.id,
        entity_kind="human_actor",
        identity_material={"k": 4},
        metadata_json={},
    )
    db_session.flush()
    ver = create_link_rule_version(
        db_session,
        tenant_id=tenant.id,
        semantic_version="rule.pin.ok",
        rules_manifest_json={},
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
    regenerate_link_candidates(
        db_session,
        tenant_id=tenant.id,
        rule_version="rule.pin.ok",
        rows=rows,
        link_rule_version_id=ver.id,
    )
    db_session.flush()
    batch = db_session.scalars(
        select(CortexOrgLinkCandidateBatch)
        .where(CortexOrgLinkCandidateBatch.tenant_id == tenant.id)
        .order_by(CortexOrgLinkCandidateBatch.created_at.desc())
    ).first()
    assert batch is not None
    batch.rule_version = "wrong.label"
    db_session.commit()
    out = run_canonical_verification(db_session, tenant_id=tenant.id, persist=False)
    gate = next(g for g in out["gates"] if g["id"] == "G-P04-RULE-01")
    assert gate["passed"] is False


def test_verification_includes_rule01_gate(db_session: Session) -> None:
    from vector.infrastructure.db.models.membership import TenantMembership
    from vector.infrastructure.db.models.tenant import Tenant
    from vector.infrastructure.db.models.user import User

    user = User(email=f"p411v-{uuid.uuid4().hex[:8]}@example.com", full_name="P411v")
    tenant = Tenant(
        company_name="P411v Co",
        primary_email=user.email,
        email_domain="example.com",
        slug=f"p411v-{uuid.uuid4().hex[:10]}",
        status="active",
        workspace_access_enabled=True,
    )
    db_session.add_all([user, tenant])
    db_session.flush()
    db_session.add(TenantMembership(tenant_id=tenant.id, user_id=user.id, role="owner"))
    db_session.commit()
    out = run_canonical_verification(db_session, tenant_id=tenant.id, persist=False)
    assert "G-P04-RULE-01" in {g["id"] for g in out["gates"]}


@pytest.mark.integration
def test_admin_link_rule_versions_post_list_detail(
    monkeypatch: pytest.MonkeyPatch,
    client: TestClient,
    db_session: Session,
) -> None:
    monkeypatch.setenv("ADMIN_PASSWORD", "integration-admin-password")
    from vector.infrastructure.db.models.membership import TenantMembership
    from vector.infrastructure.db.models.tenant import Tenant
    from vector.infrastructure.db.models.user import User

    user = User(email=f"p411a-{uuid.uuid4().hex[:8]}@example.com", full_name="P411a")
    tenant = Tenant(
        company_name="P411a Co",
        primary_email=user.email,
        email_domain="example.com",
        slug=f"p411a-{uuid.uuid4().hex[:10]}",
        status="active",
        workspace_access_enabled=True,
    )
    db_session.add_all([user, tenant])
    db_session.flush()
    db_session.add(TenantMembership(tenant_id=tenant.id, user_id=user.id, role="owner"))
    db_session.commit()

    post = client.post(
        f"/admin/tenants/{tenant.id}/cortex/identity/link-rule-versions",
        auth=("admin", "integration-admin-password"),
        json={
            "semantic_version": "admin.rule.v1",
            "rules_manifest_json": {"x": 1},
            "lifecycle_state": "active",
        },
    )
    assert post.status_code == 200
    body = post.json()
    assert body["link_rule_version_schema_version"] == LINK_RULE_VERSION_SCHEMA_VERSION
    vid = uuid.UUID(body["version"]["id"])

    lst = client.get(
        f"/admin/tenants/{tenant.id}/cortex/identity/link-rule-versions",
        auth=("admin", "integration-admin-password"),
    )
    assert lst.status_code == 200
    data = lst.json()
    assert any(uuid.UUID(v["id"]) == vid for v in data["versions"])

    det = client.get(
        f"/admin/tenants/{tenant.id}/cortex/identity/link-rule-versions/{vid}",
        auth=("admin", "integration-admin-password"),
    )
    assert det.status_code == 200
    assert det.json()["version"]["semantic_version"] == "admin.rule.v1"
