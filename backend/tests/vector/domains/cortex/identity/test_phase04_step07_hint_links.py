"""P04-07 — link_class hint family, merge-closure material, G-P04-02 / G-P04-HINT-01."""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy.orm import Session
from starlette.testclient import TestClient

from vector.domains.cortex.canonical.canonical_verification_engine import run_canonical_verification
from vector.domains.cortex.identity.link_classes import (
    OrgLinkClass,
    row_eligible_for_merge_closure_material,
    verify_merge_closure_excludes_non_authoritative_link_classes_static,
)
from vector.domains.cortex.identity.link_ledger import (
    LinkLedgerInvariantError,
    append_authoritative_org_link,
    append_non_truth_org_link,
    compute_authoritative_link_set_sha256,
)
from vector.domains.cortex.identity.org_entities import upsert_org_entity
from vector.infrastructure.db.models.cortex_org_link import CortexOrgLink
from vector.infrastructure.db.models.membership import TenantMembership
from vector.infrastructure.db.models.tenant import Tenant
from vector.infrastructure.db.models.user import User


def test_gp04_02_static_gate() -> None:
    g = verify_merge_closure_excludes_non_authoritative_link_classes_static()
    assert g["id"] == "G-P04-02"
    assert g["passed"] is True


def test_merge_closure_material_excludes_non_truth_rows() -> None:
    tid = uuid.uuid4()
    s = uuid.uuid4()
    t = uuid.uuid4()
    auth = CortexOrgLink(
        id=uuid.uuid4(),
        tenant_id=tid,
        link_type="org.persona_belongs_to_handle",
        source_entity_id=s,
        target_entity_id=t,
        evidence_raw_record_ids=[1],
        rule_id=None,
        confidence_class="c",
        link_authority="authoritative",
        link_class=OrgLinkClass.AUTHORITATIVE.value,
        metadata_json={},
        engine_build_ref="x",
    )
    hint = CortexOrgLink(
        id=uuid.uuid4(),
        tenant_id=tid,
        link_type="org.persona_belongs_to_handle",
        source_entity_id=s,
        target_entity_id=t,
        evidence_raw_record_ids=[2],
        rule_id=None,
        confidence_class="c",
        link_authority="non_authoritative",
        link_class=OrgLinkClass.HINT.value,
        metadata_json={},
        engine_build_ref="x",
    )
    assert row_eligible_for_merge_closure_material(auth) is True
    assert row_eligible_for_merge_closure_material(hint) is False


@pytest.mark.integration
def test_hint_row_does_not_shift_authoritative_link_hash(
    db_session: Session,
) -> None:
    user = User(email=f"p407-{uuid.uuid4().hex[:8]}@example.com", full_name="P407")
    tenant = Tenant(
        company_name="P407 Co",
        primary_email=user.email,
        email_domain="example.com",
        slug=f"p407-{uuid.uuid4().hex[:10]}",
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
        identity_material={"k": "h1"},
        metadata_json={},
    )
    e2 = upsert_org_entity(
        db_session,
        tenant_id=tenant.id,
        entity_kind="human_actor",
        identity_material={"k": "h2"},
        metadata_json={},
    )
    db_session.commit()

    append_authoritative_org_link(
        db_session,
        tenant_id=tenant.id,
        link_type="org.persona_belongs_to_handle",
        source_entity_id=e1.id,
        target_entity_id=e2.id,
        evidence_raw_record_ids=[7001],
    )
    db_session.commit()
    h0 = compute_authoritative_link_set_sha256(db_session, tenant_id=tenant.id)

    append_non_truth_org_link(
        db_session,
        tenant_id=tenant.id,
        link_class=OrgLinkClass.HINT.value,
        link_type="org.persona_belongs_to_handle",
        source_entity_id=e2.id,
        target_entity_id=e1.id,
        evidence_raw_record_ids=[7002, 7003],
    )
    db_session.commit()
    h1 = compute_authoritative_link_set_sha256(db_session, tenant_id=tenant.id)
    assert h0 == h1


@pytest.mark.integration
def test_verification_includes_hint_gates(db_session: Session) -> None:
    user = User(email=f"p407b-{uuid.uuid4().hex[:8]}@example.com", full_name="P407b")
    tenant = Tenant(
        company_name="P407b Co",
        primary_email=user.email,
        email_domain="example.com",
        slug=f"p407b-{uuid.uuid4().hex[:10]}",
        status="active",
        workspace_access_enabled=True,
    )
    db_session.add_all([user, tenant])
    db_session.flush()
    db_session.add(TenantMembership(tenant_id=tenant.id, user_id=user.id, role="owner"))
    db_session.commit()
    out = run_canonical_verification(db_session, tenant_id=tenant.id, materialization_sample_limit=3, persist=False)
    ids = {g["id"] for g in out["gates"]}
    assert "G-P04-02" in ids
    assert "G-P04-HINT-01" in ids
    assert next(g for g in out["gates"] if g["id"] == "G-P04-02")["passed"] is True
    assert next(g for g in out["gates"] if g["id"] == "G-P04-HINT-01")["passed"] is True


@pytest.mark.integration
def test_admin_hints_bucket(
    monkeypatch: pytest.MonkeyPatch,
    client: TestClient,
    db_session: Session,
) -> None:
    monkeypatch.setenv("ADMIN_PASSWORD", "integration-admin-password")
    user = User(email=f"p407c-{uuid.uuid4().hex[:8]}@example.com", full_name="P407c")
    tenant = Tenant(
        company_name="P407c Co",
        primary_email=user.email,
        email_domain="example.com",
        slug=f"p407c-{uuid.uuid4().hex[:10]}",
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
        identity_material={"k": "c1"},
        metadata_json={},
    )
    e2 = upsert_org_entity(
        db_session,
        tenant_id=tenant.id,
        entity_kind="human_actor",
        identity_material={"k": "c2"},
        metadata_json={},
    )
    db_session.flush()
    append_non_truth_org_link(
        db_session,
        tenant_id=tenant.id,
        link_class=OrgLinkClass.INFERRED.value,
        link_type="org.persona_belongs_to_handle",
        source_entity_id=e1.id,
        target_entity_id=e2.id,
        evidence_raw_record_ids=[8001],
    )
    db_session.commit()

    r = client.get(
        f"/admin/tenants/{tenant.id}/cortex/identity/links/hints",
        auth=("admin", "integration-admin-password"),
    )
    assert r.status_code == 200
    body = r.json()
    assert body["links"]
    assert body["links"][0]["link_class"] == OrgLinkClass.INFERRED.value
    assert body["links"][0]["link_authority"] == "non_authoritative"


def test_append_non_truth_rejects_authoritative_class() -> None:
    class _S:
        def get(self, *_a: object, **_k: object) -> object:
            return None

    with pytest.raises(LinkLedgerInvariantError, match="append_non_truth_org_link"):
        append_non_truth_org_link(
            _S(),  # type: ignore[arg-type]
            tenant_id=uuid.uuid4(),
            link_class="authoritative",
            link_type="x",
            source_entity_id=uuid.uuid4(),
            target_entity_id=uuid.uuid4(),
            evidence_raw_record_ids=[1],
        )
