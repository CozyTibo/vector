"""P04-08 — org link temporal half-open validity, overlap verification gate, admin timeline strip."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy.orm import Session
from starlette.testclient import TestClient

from vector.domains.cortex.canonical.canonical_verification_engine import run_canonical_verification
from vector.domains.cortex.identity.link_ledger import (
    LINK_LEDGER_RUNTIME_SCHEMA_VERSION,
    LinkLedgerInvariantError,
    append_authoritative_org_link,
    find_authoritative_temporal_overlaps,
    list_authoritative_temporal_overlap_violations_for_tenant,
)
from vector.domains.cortex.identity.org_entities import upsert_org_entity
from vector.domains.cortex.identity.org_link_temporal import (
    ORG_LINK_TEMPORAL_SCHEMA_VERSION,
    OrgLinkTemporalError,
    assert_org_link_validity_half_open,
    org_link_temporal_axis_static_errors,
    verify_link_ledger_soft_revocation_tombstone_static,
)
from vector.infrastructure.db.models.cortex_org_link import CortexOrgLink


def test_org_link_temporal_axis_static_errors_empty() -> None:
    assert org_link_temporal_axis_static_errors() == []


def test_assert_org_link_validity_half_open_rejects_touching_bounds() -> None:
    t = datetime(2026, 5, 1, tzinfo=UTC)
    with pytest.raises(OrgLinkTemporalError):
        assert_org_link_validity_half_open(t, t)


def test_verify_soft_revocation_gate_shape() -> None:
    g = verify_link_ledger_soft_revocation_tombstone_static()
    assert g["id"] == "G-P04-11"
    assert g["passed"] is True


def test_append_authoritative_rejects_invalid_interval(db_session: Session) -> None:
    from vector.infrastructure.db.models.membership import TenantMembership
    from vector.infrastructure.db.models.tenant import Tenant
    from vector.infrastructure.db.models.user import User

    user = User(email=f"p408u-{uuid.uuid4().hex[:8]}@example.com", full_name="P408")
    tenant = Tenant(
        company_name="P408 Co",
        primary_email=user.email,
        email_domain="example.com",
        slug=f"p408-{uuid.uuid4().hex[:10]}",
        status="active",
        workspace_access_enabled=True,
    )
    db_session.add_all([user, tenant])
    db_session.flush()
    db_session.add(TenantMembership(tenant_id=tenant.id, user_id=user.id, role="owner"))
    db_session.flush()
    src = upsert_org_entity(
        db_session,
        tenant_id=tenant.id,
        entity_kind="human_actor",
        identity_material={"a": 1},
        metadata_json={},
    )
    dst = upsert_org_entity(
        db_session,
        tenant_id=tenant.id,
        entity_kind="human_actor",
        identity_material={"a": 2},
        metadata_json={},
    )
    bad_from = datetime(2026, 6, 10, tzinfo=UTC)
    bad_to = datetime(2026, 6, 1, tzinfo=UTC)
    with pytest.raises(LinkLedgerInvariantError):
        append_authoritative_org_link(
            db_session,
            tenant_id=tenant.id,
            link_type="org.persona_belongs_to_handle",
            source_entity_id=src.id,
            target_entity_id=dst.id,
            evidence_raw_record_ids=[1],
            valid_from=bad_from,
            valid_to=bad_to,
        )


def test_list_authoritative_temporal_overlap_violations_for_tenant(db_session: Session) -> None:
    from vector.infrastructure.db.models.membership import TenantMembership
    from vector.infrastructure.db.models.tenant import Tenant
    from vector.infrastructure.db.models.user import User

    user = User(email=f"p408o-{uuid.uuid4().hex[:8]}@example.com", full_name="P408o")
    tenant = Tenant(
        company_name="P408o Co",
        primary_email=user.email,
        email_domain="example.com",
        slug=f"p408o-{uuid.uuid4().hex[:10]}",
        status="active",
        workspace_access_enabled=True,
    )
    db_session.add_all([user, tenant])
    db_session.flush()
    db_session.add(TenantMembership(tenant_id=tenant.id, user_id=user.id, role="owner"))
    db_session.flush()
    src = upsert_org_entity(
        db_session,
        tenant_id=tenant.id,
        entity_kind="human_actor",
        identity_material={"o": 1},
        metadata_json={},
    )
    dst = upsert_org_entity(
        db_session,
        tenant_id=tenant.id,
        entity_kind="human_actor",
        identity_material={"o": 2},
        metadata_json={},
    )
    a = uuid.uuid4()
    b = uuid.uuid4()
    link_a = CortexOrgLink(
        id=a,
        tenant_id=tenant.id,
        link_type="org.persona_belongs_to_handle",
        source_entity_id=src.id,
        target_entity_id=dst.id,
        evidence_raw_record_ids=[10],
        rule_id=None,
        confidence_class="phase03_confidence_stub",
        valid_from=datetime(2026, 1, 1, tzinfo=UTC),
        valid_to=datetime(2026, 6, 1, tzinfo=UTC),
        link_authority="authoritative",
        link_class="authoritative",
        metadata_json={},
        engine_build_ref="t",
    )
    link_b = CortexOrgLink(
        id=b,
        tenant_id=tenant.id,
        link_type="org.persona_belongs_to_handle",
        source_entity_id=src.id,
        target_entity_id=dst.id,
        evidence_raw_record_ids=[11],
        rule_id=None,
        confidence_class="phase03_confidence_stub",
        valid_from=datetime(2026, 3, 1, tzinfo=UTC),
        valid_to=datetime(2026, 9, 1, tzinfo=UTC),
        link_authority="authoritative",
        link_class="authoritative",
        metadata_json={},
        engine_build_ref="t",
    )
    overlaps = find_authoritative_temporal_overlaps([link_a, link_b])
    assert len(overlaps) == 1
    assert {overlaps[0]["link_id_a"], overlaps[0]["link_id_b"]} == {str(a), str(b)}
    db_session.add(link_a)
    db_session.flush()
    v = list_authoritative_temporal_overlap_violations_for_tenant(db_session, tenant_id=tenant.id)
    assert len(v) == 0


def test_canonical_verification_includes_temporal_gates(db_session: Session) -> None:
    from vector.infrastructure.db.models.membership import TenantMembership
    from vector.infrastructure.db.models.tenant import Tenant
    from vector.infrastructure.db.models.user import User

    user = User(email=f"p408v-{uuid.uuid4().hex[:8]}@example.com", full_name="P408v")
    tenant = Tenant(
        company_name="P408v Co",
        primary_email=user.email,
        email_domain="example.com",
        slug=f"p408v-{uuid.uuid4().hex[:10]}",
        status="active",
        workspace_access_enabled=True,
    )
    db_session.add_all([user, tenant])
    db_session.flush()
    db_session.add(TenantMembership(tenant_id=tenant.id, user_id=user.id, role="owner"))
    db_session.commit()
    out = run_canonical_verification(db_session, tenant_id=tenant.id, persist=False)
    ids = [g["id"] for g in out["gates"]]
    assert "G-P04-TMP-01" in ids
    assert "G-P04-11" in ids
    assert next(g for g in out["gates"] if g["id"] == "G-P04-TMP-01")["passed"] is True
    assert next(g for g in out["gates"] if g["id"] == "G-P04-11")["passed"] is True


def test_canonical_verification_gp04_tmp01_fails_on_authoritative_overlap(db_session: Session) -> None:
    from vector.infrastructure.db.models.membership import TenantMembership
    from vector.infrastructure.db.models.tenant import Tenant
    from vector.infrastructure.db.models.user import User

    user = User(email=f"p408f-{uuid.uuid4().hex[:8]}@example.com", full_name="P408f")
    tenant = Tenant(
        company_name="P408f Co",
        primary_email=user.email,
        email_domain="example.com",
        slug=f"p408f-{uuid.uuid4().hex[:10]}",
        status="active",
        workspace_access_enabled=True,
    )
    db_session.add_all([user, tenant])
    db_session.flush()
    db_session.add(TenantMembership(tenant_id=tenant.id, user_id=user.id, role="owner"))
    db_session.flush()
    src = upsert_org_entity(
        db_session,
        tenant_id=tenant.id,
        entity_kind="human_actor",
        identity_material={"f": 1},
        metadata_json={},
    )
    dst = upsert_org_entity(
        db_session,
        tenant_id=tenant.id,
        entity_kind="human_actor",
        identity_material={"f": 2},
        metadata_json={},
    )
    from unittest.mock import patch

    overlap_row = {
        "link_id_a": str(uuid.uuid4()),
        "link_id_b": str(uuid.uuid4()),
        "link_type": "org.persona_belongs_to_handle",
    }
    with patch(
        "vector.domains.cortex.canonical.canonical_verification_engine."
        "list_authoritative_temporal_overlap_violations_for_tenant",
        return_value=[overlap_row],
    ):
        out = run_canonical_verification(db_session, tenant_id=tenant.id, persist=False)
    gate = next(g for g in out["gates"] if g["id"] == "G-P04-TMP-01")
    assert gate["passed"] is False
    assert gate["detail"]["overlap_count"] >= 1


@pytest.mark.integration
def test_admin_links_timeline_strip(
    monkeypatch: pytest.MonkeyPatch,
    client: TestClient,
    db_session: Session,
) -> None:
    monkeypatch.setenv("ADMIN_PASSWORD", "integration-admin-password")
    from vector.infrastructure.db.models.membership import TenantMembership
    from vector.infrastructure.db.models.tenant import Tenant
    from vector.infrastructure.db.models.user import User

    user = User(email=f"p408t-{uuid.uuid4().hex[:8]}@example.com", full_name="P408t")
    tenant = Tenant(
        company_name="P408t Co",
        primary_email=user.email,
        email_domain="example.com",
        slug=f"p408t-{uuid.uuid4().hex[:10]}",
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
        identity_material={"t": 1},
        metadata_json={},
    )
    e2 = upsert_org_entity(
        db_session,
        tenant_id=tenant.id,
        entity_kind="human_actor",
        identity_material={"t": 2},
        metadata_json={},
    )
    vf = datetime(2026, 4, 1, tzinfo=UTC)
    vt = datetime(2026, 5, 1, tzinfo=UTC)
    link = append_authoritative_org_link(
        db_session,
        tenant_id=tenant.id,
        link_type="org.persona_belongs_to_handle",
        source_entity_id=e1.id,
        target_entity_id=e2.id,
        evidence_raw_record_ids=[99],
        valid_from=vf,
        valid_to=vt,
    )
    db_session.commit()

    r = client.get(
        f"/admin/tenants/{tenant.id}/cortex/identity/links/timeline",
        auth=("admin", "integration-admin-password"),
    )
    assert r.status_code == 200
    body = r.json()
    assert body["org_link_temporal_schema_version"] == ORG_LINK_TEMPORAL_SCHEMA_VERSION
    assert body["link_ledger_runtime_schema_version"] == LINK_LEDGER_RUNTIME_SCHEMA_VERSION
    assert body["strips"]
    top = next(x for x in body["strips"] if x["id"] == str(link.id))
    assert top["link_type"] == "org.persona_belongs_to_handle"
    assert top["valid_from"] == vf.isoformat()
    assert top["valid_to"] == vt.isoformat()
    assert top["revoked_at"] is None
