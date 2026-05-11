"""P04-04 — org link ledger: evidence/rule invariants, temporal non-overlap, admin read surface."""

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
    half_open_intervals_overlap,
    list_links_failing_evidence_or_rule,
    verify_link_ledger_evidence_rule_static,
)
from vector.domains.cortex.identity.org_entities import upsert_org_entity
from vector.infrastructure.db.models.cortex_org_link import CortexOrgLink


def test_verify_link_ledger_evidence_rule_static_passes() -> None:
    gate = verify_link_ledger_evidence_rule_static()
    assert gate["id"] == "G-P04-LINK-01"
    assert gate["passed"] is True


def test_half_open_overlap() -> None:
    t0 = datetime(2026, 1, 1, tzinfo=UTC)
    t1 = datetime(2026, 2, 1, tzinfo=UTC)
    t2 = datetime(2026, 3, 1, tzinfo=UTC)
    assert half_open_intervals_overlap(t0, t1, t0, t1) is True
    assert half_open_intervals_overlap(t0, t1, t1, t2) is False
    assert half_open_intervals_overlap(None, t2, t1, None) is True


def test_find_authoritative_temporal_overlaps_detects_pair() -> None:
    tid = uuid.uuid4()
    a = uuid.uuid4()
    b = uuid.uuid4()
    s = uuid.uuid4()
    t = uuid.uuid4()
    r1 = CortexOrgLink(
        id=a,
        tenant_id=tid,
        link_type="org.persona_belongs_to_handle",
        source_entity_id=s,
        target_entity_id=t,
        evidence_raw_record_ids=[1],
        rule_id=None,
        confidence_class="phase03_confidence_stub",
        valid_from=datetime(2026, 1, 1, tzinfo=UTC),
        valid_to=datetime(2026, 6, 1, tzinfo=UTC),
        link_authority="authoritative",
        link_class="authoritative",
        metadata_json={},
        engine_build_ref="t",
    )
    r2 = CortexOrgLink(
        id=b,
        tenant_id=tid,
        link_type="org.persona_belongs_to_handle",
        source_entity_id=s,
        target_entity_id=t,
        evidence_raw_record_ids=[2],
        rule_id=None,
        confidence_class="phase03_confidence_stub",
        valid_from=datetime(2026, 3, 1, tzinfo=UTC),
        valid_to=datetime(2026, 9, 1, tzinfo=UTC),
        link_authority="authoritative",
        link_class="authoritative",
        metadata_json={},
        engine_build_ref="t",
    )
    v = find_authoritative_temporal_overlaps([r1, r2])
    assert len(v) == 1
    assert v[0]["link_id_a"] in (str(a), str(b))


def test_find_overlaps_ignores_revoked() -> None:
    tid = uuid.uuid4()
    a = uuid.uuid4()
    b = uuid.uuid4()
    s = uuid.uuid4()
    t = uuid.uuid4()
    r1 = CortexOrgLink(
        id=a,
        tenant_id=tid,
        link_type="x",
        source_entity_id=s,
        target_entity_id=t,
        evidence_raw_record_ids=[1],
        rule_id=None,
        confidence_class="c",
        valid_from=datetime(2026, 1, 1, tzinfo=UTC),
        valid_to=datetime(2026, 6, 1, tzinfo=UTC),
        revoked_at=datetime(2026, 1, 15, tzinfo=UTC),
        link_authority="authoritative",
        link_class="authoritative",
        metadata_json={},
        engine_build_ref="t",
    )
    r2 = CortexOrgLink(
        id=b,
        tenant_id=tid,
        link_type="x",
        source_entity_id=s,
        target_entity_id=t,
        evidence_raw_record_ids=[2],
        rule_id=None,
        confidence_class="c",
        valid_from=datetime(2026, 3, 1, tzinfo=UTC),
        valid_to=datetime(2026, 9, 1, tzinfo=UTC),
        link_authority="authoritative",
        link_class="authoritative",
        metadata_json={},
        engine_build_ref="t",
    )
    assert find_authoritative_temporal_overlaps([r1, r2]) == []


@pytest.mark.integration
def test_append_and_list_round_trip(db_session: Session) -> None:
    from vector.infrastructure.db.models.membership import TenantMembership
    from vector.infrastructure.db.models.tenant import Tenant
    from vector.infrastructure.db.models.user import User

    user = User(email=f"p404-{uuid.uuid4().hex[:8]}@example.com", full_name="P404")
    tenant = Tenant(
        company_name="P404 Co",
        primary_email=user.email,
        email_domain="example.com",
        slug=f"p404-{uuid.uuid4().hex[:10]}",
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
        identity_material={"u": "a"},
        metadata_json={},
    )
    dst = upsert_org_entity(
        db_session,
        tenant_id=tenant.id,
        entity_kind="team",
        identity_material={"u": "b"},
        metadata_json={},
    )
    db_session.commit()

    row = append_authoritative_org_link(
        db_session,
        tenant_id=tenant.id,
        link_type="org.persona_belongs_to_handle",
        source_entity_id=src.id,
        target_entity_id=dst.id,
        evidence_raw_record_ids=[101, 102],
        confidence_class="E1",
    )
    db_session.commit()
    assert list_links_failing_evidence_or_rule(db_session, tenant_id=tenant.id) == []

    row2 = append_authoritative_org_link(
        db_session,
        tenant_id=tenant.id,
        link_type="org.fixture_rule_only",
        source_entity_id=dst.id,
        target_entity_id=src.id,
        evidence_raw_record_ids=[],
        rule_id="rule.phase04.step04.fixture.v1",
        confidence_class="E0",
    )
    db_session.commit()
    assert list_links_failing_evidence_or_rule(db_session, tenant_id=tenant.id) == []

    with pytest.raises(LinkLedgerInvariantError):
        append_authoritative_org_link(
            db_session,
            tenant_id=tenant.id,
            link_type="org.bad",
            source_entity_id=src.id,
            target_entity_id=dst.id,
            evidence_raw_record_ids=[],
            rule_id=None,
        )


@pytest.mark.integration
def test_admin_links_list_detail(
    monkeypatch: pytest.MonkeyPatch,
    client: TestClient,
    db_session: Session,
) -> None:
    monkeypatch.setenv("ADMIN_PASSWORD", "integration-admin-password")
    from vector.infrastructure.db.models.membership import TenantMembership
    from vector.infrastructure.db.models.tenant import Tenant
    from vector.infrastructure.db.models.user import User

    user = User(email=f"p404a-{uuid.uuid4().hex[:8]}@example.com", full_name="P404a")
    tenant = Tenant(
        company_name="P404a Co",
        primary_email=user.email,
        email_domain="example.com",
        slug=f"p404a-{uuid.uuid4().hex[:10]}",
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
        identity_material={"x": 1},
        metadata_json={},
    )
    e2 = upsert_org_entity(
        db_session,
        tenant_id=tenant.id,
        entity_kind="human_actor",
        identity_material={"x": 2},
        metadata_json={},
    )
    link = append_authoritative_org_link(
        db_session,
        tenant_id=tenant.id,
        link_type="org.persona_belongs_to_handle",
        source_entity_id=e1.id,
        target_entity_id=e2.id,
        evidence_raw_record_ids=[55],
        confidence_class="E1",
    )
    db_session.commit()
    lid = link.id

    lst = client.get(
        f"/admin/tenants/{tenant.id}/cortex/identity/links",
        auth=("admin", "integration-admin-password"),
    )
    assert lst.status_code == 200
    body = lst.json()
    assert body["link_ledger_runtime_schema_version"] == LINK_LEDGER_RUNTIME_SCHEMA_VERSION
    assert any(x["id"] == str(lid) for x in body["links"])

    det = client.get(
        f"/admin/tenants/{tenant.id}/cortex/identity/links/{lid}",
        auth=("admin", "integration-admin-password"),
    )
    assert det.status_code == 200
    assert det.json()["evidence_raw_record_ids"] == [55]


@pytest.mark.integration
def test_canonical_verification_includes_link_gates(db_session: Session) -> None:
    from vector.infrastructure.db.models.membership import TenantMembership
    from vector.infrastructure.db.models.tenant import Tenant
    from vector.infrastructure.db.models.user import User

    user = User(email=f"p404b-{uuid.uuid4().hex[:8]}@example.com", full_name="P404b")
    tenant = Tenant(
        company_name="P404b Co",
        primary_email=user.email,
        email_domain="example.com",
        slug=f"p404b-{uuid.uuid4().hex[:10]}",
        status="active",
        workspace_access_enabled=True,
    )
    db_session.add_all([user, tenant])
    db_session.flush()
    db_session.add(TenantMembership(tenant_id=tenant.id, user_id=user.id, role="owner"))
    db_session.commit()

    out = run_canonical_verification(db_session, tenant_id=tenant.id, persist=False)
    ids = [g["id"] for g in out["gates"]]
    assert "G-P04-LINK-01" in ids
    assert "G-P04-06" in ids
    assert next(g for g in out["gates"] if g["id"] == "G-P04-LINK-01")["passed"] is True
    assert next(g for g in out["gates"] if g["id"] == "G-P04-06")["passed"] is True
