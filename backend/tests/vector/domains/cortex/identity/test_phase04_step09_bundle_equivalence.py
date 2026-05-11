"""P04-09 — bundle equivalence declarations, G-P04-BNDL-01 / G-P04-03 / G-P04-14, admin list/append."""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy.orm import Session
from starlette.testclient import TestClient

from vector.domains.cortex.canonical.canonical_verification_engine import run_canonical_verification
from vector.domains.cortex.identity.bundle_equivalence import (
    BUNDLE_EQUIVALENCE_SCHEMA_VERSION,
    BundleEquivalenceError,
    append_bundle_equivalence_declaration,
    bundle_equivalence_pair_static_errors,
    cross_bundle_edge_bundles_from_link_metadata,
    has_active_bundle_equivalence_declaration,
    list_org_links_missing_cross_bundle_equivalence,
    normalize_bundle_pair,
)
from vector.domains.cortex.identity.link_ledger import append_authoritative_org_link
from vector.domains.cortex.identity.org_entities import upsert_org_entity
from vector.infrastructure.db.models.cortex_mapping_bundle import CortexMappingBundle
_STUB_A = "bundle.phase03.step03.logical_keys.v1"
_STUB_B = "bundle.phase04.step09.equivalence.b.v1"
_STUB_C = "bundle.phase04.step09.equivalence.c.v1"


def test_bundle_equivalence_pair_static_errors_empty() -> None:
    assert bundle_equivalence_pair_static_errors() == []


def test_normalize_bundle_pair_orders_lexicographically() -> None:
    assert normalize_bundle_pair("zebra", "apple") == ("apple", "zebra")


def test_cross_bundle_edge_from_metadata() -> None:
    md = {
        "cross_bundle_canonical": {
            "source_bundle_id": _STUB_B,
            "target_bundle_id": _STUB_A,
        }
    }
    assert cross_bundle_edge_bundles_from_link_metadata(md) == (_STUB_A, _STUB_B)


def test_append_declaration_and_replay_ordinal(db_session: Session) -> None:
    from vector.infrastructure.db.models.membership import TenantMembership
    from vector.infrastructure.db.models.tenant import Tenant
    from vector.infrastructure.db.models.user import User

    user = User(email=f"p409-{uuid.uuid4().hex[:8]}@example.com", full_name="P409")
    tenant = Tenant(
        company_name="P409 Co",
        primary_email=user.email,
        email_domain="example.com",
        slug=f"p409-{uuid.uuid4().hex[:10]}",
        status="active",
        workspace_access_enabled=True,
    )
    db_session.add_all([user, tenant])
    db_session.flush()
    db_session.add(TenantMembership(tenant_id=tenant.id, user_id=user.id, role="owner"))
    db_session.flush()
    db_session.add(
        CortexMappingBundle(
            bundle_id=_STUB_C,
            lifecycle_state="approved",
            manifest_hash="sha256:0000000000000000000000000000000000000000000000000000000000000002",
            owner_team="cortex-platform",
            title="P04-09 test bundle C",
            notes=None,
        )
    )
    db_session.flush()
    r1 = append_bundle_equivalence_declaration(
        db_session,
        tenant_id=tenant.id,
        bundle_id_a=_STUB_B,
        bundle_id_b=_STUB_A,
        evidence_raw_record_ids=[1],
    )
    db_session.flush()
    r2 = append_bundle_equivalence_declaration(
        db_session,
        tenant_id=tenant.id,
        bundle_id_a=_STUB_C,
        bundle_id_b=_STUB_A,
        evidence_raw_record_ids=[2],
    )
    db_session.commit()
    assert r1.replay_ordinal == 1
    assert r2.replay_ordinal == 2
    assert r1.left_bundle_id == _STUB_A and r1.right_bundle_id == _STUB_B
    assert r2.left_bundle_id == _STUB_A and r2.right_bundle_id == _STUB_C
    assert has_active_bundle_equivalence_declaration(
        db_session, tenant_id=tenant.id, bundle_id_a=_STUB_A, bundle_id_b=_STUB_B
    )


def test_append_rejects_unknown_bundle(db_session: Session) -> None:
    from vector.infrastructure.db.models.membership import TenantMembership
    from vector.infrastructure.db.models.tenant import Tenant
    from vector.infrastructure.db.models.user import User

    user = User(email=f"p409u-{uuid.uuid4().hex[:8]}@example.com", full_name="P409u")
    tenant = Tenant(
        company_name="P409u Co",
        primary_email=user.email,
        email_domain="example.com",
        slug=f"p409u-{uuid.uuid4().hex[:10]}",
        status="active",
        workspace_access_enabled=True,
    )
    db_session.add_all([user, tenant])
    db_session.flush()
    db_session.add(TenantMembership(tenant_id=tenant.id, user_id=user.id, role="owner"))
    db_session.flush()
    with pytest.raises(BundleEquivalenceError, match="unknown_bundle_id"):
        append_bundle_equivalence_declaration(
            db_session,
            tenant_id=tenant.id,
            bundle_id_a=_STUB_A,
            bundle_id_b="bundle.does.not.exist.for.tests",
        )


def test_gp04_03_detects_missing_declaration(db_session: Session) -> None:
    from vector.infrastructure.db.models.membership import TenantMembership
    from vector.infrastructure.db.models.tenant import Tenant
    from vector.infrastructure.db.models.user import User

    user = User(email=f"p409c-{uuid.uuid4().hex[:8]}@example.com", full_name="P409c")
    tenant = Tenant(
        company_name="P409c Co",
        primary_email=user.email,
        email_domain="example.com",
        slug=f"p409c-{uuid.uuid4().hex[:10]}",
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
        identity_material={"c": 1},
        metadata_json={},
    )
    e2 = upsert_org_entity(
        db_session,
        tenant_id=tenant.id,
        entity_kind="human_actor",
        identity_material={"c": 2},
        metadata_json={},
    )
    append_authoritative_org_link(
        db_session,
        tenant_id=tenant.id,
        link_type="org.persona_belongs_to_handle",
        source_entity_id=e1.id,
        target_entity_id=e2.id,
        evidence_raw_record_ids=[99],
        metadata_json={
            "cross_bundle_canonical": {
                "source_bundle_id": _STUB_A,
                "target_bundle_id": _STUB_B,
            }
        },
    )
    db_session.commit()
    missing = list_org_links_missing_cross_bundle_equivalence(db_session, tenant_id=tenant.id)
    assert len(missing) == 1
    out = run_canonical_verification(db_session, tenant_id=tenant.id, persist=False)
    g3 = next(g for g in out["gates"] if g["id"] == "G-P04-03")
    assert g3["passed"] is False

    append_bundle_equivalence_declaration(
        db_session,
        tenant_id=tenant.id,
        bundle_id_a=_STUB_A,
        bundle_id_b=_STUB_B,
    )
    db_session.commit()
    assert list_org_links_missing_cross_bundle_equivalence(db_session, tenant_id=tenant.id) == []
    out2 = run_canonical_verification(db_session, tenant_id=tenant.id, persist=False)
    assert next(g for g in out2["gates"] if g["id"] == "G-P04-03")["passed"] is True


def test_verification_includes_bundle_gates(db_session: Session) -> None:
    from vector.infrastructure.db.models.membership import TenantMembership
    from vector.infrastructure.db.models.tenant import Tenant
    from vector.infrastructure.db.models.user import User

    user = User(email=f"p409v-{uuid.uuid4().hex[:8]}@example.com", full_name="P409v")
    tenant = Tenant(
        company_name="P409v Co",
        primary_email=user.email,
        email_domain="example.com",
        slug=f"p409v-{uuid.uuid4().hex[:10]}",
        status="active",
        workspace_access_enabled=True,
    )
    db_session.add_all([user, tenant])
    db_session.flush()
    db_session.add(TenantMembership(tenant_id=tenant.id, user_id=user.id, role="owner"))
    db_session.commit()
    out = run_canonical_verification(db_session, tenant_id=tenant.id, persist=False)
    ids = {g["id"] for g in out["gates"]}
    assert "G-P04-BNDL-01" in ids
    assert "G-P04-03" in ids
    assert "G-P04-14" in ids


@pytest.mark.integration
def test_admin_bundle_equivalence_list_append(
    monkeypatch: pytest.MonkeyPatch,
    client: TestClient,
    db_session: Session,
) -> None:
    monkeypatch.setenv("ADMIN_PASSWORD", "integration-admin-password")
    from vector.infrastructure.db.models.membership import TenantMembership
    from vector.infrastructure.db.models.tenant import Tenant
    from vector.infrastructure.db.models.user import User

    user = User(email=f"p409a-{uuid.uuid4().hex[:8]}@example.com", full_name="P409a")
    tenant = Tenant(
        company_name="P409a Co",
        primary_email=user.email,
        email_domain="example.com",
        slug=f"p409a-{uuid.uuid4().hex[:10]}",
        status="active",
        workspace_access_enabled=True,
    )
    db_session.add_all([user, tenant])
    db_session.flush()
    db_session.add(TenantMembership(tenant_id=tenant.id, user_id=user.id, role="owner"))
    db_session.commit()

    post = client.post(
        f"/admin/tenants/{tenant.id}/cortex/identity/bundle-equivalence",
        auth=("admin", "integration-admin-password"),
        json={
            "bundle_id_a": _STUB_B,
            "bundle_id_b": _STUB_A,
            "evidence_raw_record_ids": [42],
        },
    )
    assert post.status_code == 200
    body = post.json()
    assert body["bundle_equivalence_schema_version"] == BUNDLE_EQUIVALENCE_SCHEMA_VERSION
    assert body["left_bundle_id"] == _STUB_A
    assert body["right_bundle_id"] == _STUB_B
    assert body["replay_ordinal"] == 1

    lst = client.get(
        f"/admin/tenants/{tenant.id}/cortex/identity/bundle-equivalence",
        auth=("admin", "integration-admin-password"),
    )
    assert lst.status_code == 200
    data = lst.json()
    assert data["declarations"]
    assert data["declarations"][0]["replay_ordinal"] == 1
