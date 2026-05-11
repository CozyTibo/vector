"""P04-12 — execution primitive instances, G-P04-09 / G-P04-PRIM-01, admin HTTP."""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy.orm import Session
from starlette.testclient import TestClient

from vector.domains.cortex.canonical.canonical_verification_engine import run_canonical_verification
from vector.domains.cortex.continuity.execution_primitives import (
    ExecutionPrimitiveKind,
    build_execution_primitive_envelope,
)
from vector.domains.cortex.identity.execution_primitives import (
    ORG_PRIMITIVE_INSTANCE_SCHEMA_VERSION,
    PrimitivePersistenceError,
    append_org_primitive_instance,
    verify_gp04_09_primitive_evidence_discipline_static,
    verify_gp04_prim01_static_evidence_contract,
)
from vector.domains.cortex.identity.org_entities import upsert_org_entity


def test_gp04_09_static_passes() -> None:
    st = verify_gp04_09_primitive_evidence_discipline_static()
    assert st["passed"] is True
    assert st["id"] == "G-P04-09"


def test_gp04_prim01_static_contract_passes() -> None:
    st = verify_gp04_prim01_static_evidence_contract()
    assert st["passed"] is True


def test_append_primitive_instance(db_session: Session) -> None:
    from vector.infrastructure.db.models.membership import TenantMembership
    from vector.infrastructure.db.models.tenant import Tenant
    from vector.infrastructure.db.models.user import User

    user = User(email=f"p412-{uuid.uuid4().hex[:8]}@example.com", full_name="P412")
    tenant = Tenant(
        company_name="P412 Co",
        primary_email=user.email,
        email_domain="example.com",
        slug=f"p412-{uuid.uuid4().hex[:10]}",
        status="active",
        workspace_access_enabled=True,
    )
    db_session.add_all([user, tenant])
    db_session.flush()
    db_session.add(TenantMembership(tenant_id=tenant.id, user_id=user.id, role="owner"))
    db_session.flush()
    ent = upsert_org_entity(
        db_session,
        tenant_id=tenant.id,
        entity_kind="human_actor",
        identity_material={"p": 12},
        metadata_json={},
    )
    db_session.flush()
    env = build_execution_primitive_envelope(
        kind=ExecutionPrimitiveKind.WORK_EPISODE,
        evidence_parts={"slice": "a"},
        evidence_raw_record_ids=[9001, 9002],
        bundle_id="bundle.phase04.step12.primitive.v1",
        tenant_id=str(tenant.id),
    )
    row = append_org_primitive_instance(
        db_session,
        tenant_id=tenant.id,
        org_entity_id=ent.id,
        envelope_json=dict(env),
    )
    db_session.commit()
    assert row.primitive_key == env["primitive_key"]
    assert row.org_entity_id == ent.id


def test_append_rejects_empty_evidence(db_session: Session) -> None:
    from vector.infrastructure.db.models.membership import TenantMembership
    from vector.infrastructure.db.models.tenant import Tenant
    from vector.infrastructure.db.models.user import User

    user = User(email=f"p412e-{uuid.uuid4().hex[:8]}@example.com", full_name="P412e")
    tenant = Tenant(
        company_name="P412e Co",
        primary_email=user.email,
        email_domain="example.com",
        slug=f"p412e-{uuid.uuid4().hex[:10]}",
        status="active",
        workspace_access_enabled=True,
    )
    db_session.add_all([user, tenant])
    db_session.flush()
    db_session.add(TenantMembership(tenant_id=tenant.id, user_id=user.id, role="owner"))
    db_session.flush()
    ent = upsert_org_entity(
        db_session,
        tenant_id=tenant.id,
        entity_kind="human_actor",
        identity_material={"p": 12},
        metadata_json={},
    )
    db_session.flush()
    env = dict(
        build_execution_primitive_envelope(
            kind=ExecutionPrimitiveKind.DELIVERY_ATTEMPT,
            evidence_parts={"x": 1},
            evidence_raw_record_ids=[1],
            bundle_id="bundle.phase04.step12.b",
            tenant_id=str(tenant.id),
        )
    )
    env["evidence_raw_record_ids"] = []
    with pytest.raises(PrimitivePersistenceError):
        append_org_primitive_instance(
            db_session,
            tenant_id=tenant.id,
            org_entity_id=ent.id,
            envelope_json=env,
        )


def test_duplicate_primitive_key_rejected(db_session: Session) -> None:
    from vector.infrastructure.db.models.membership import TenantMembership
    from vector.infrastructure.db.models.tenant import Tenant
    from vector.infrastructure.db.models.user import User

    user = User(email=f"p412d-{uuid.uuid4().hex[:8]}@example.com", full_name="P412d")
    tenant = Tenant(
        company_name="P412d Co",
        primary_email=user.email,
        email_domain="example.com",
        slug=f"p412d-{uuid.uuid4().hex[:10]}",
        status="active",
        workspace_access_enabled=True,
    )
    db_session.add_all([user, tenant])
    db_session.flush()
    db_session.add(TenantMembership(tenant_id=tenant.id, user_id=user.id, role="owner"))
    db_session.flush()
    ent = upsert_org_entity(
        db_session,
        tenant_id=tenant.id,
        entity_kind="human_actor",
        identity_material={"p": 12},
        metadata_json={},
    )
    db_session.flush()
    env = build_execution_primitive_envelope(
        kind=ExecutionPrimitiveKind.REVIEW_CYCLE,
        evidence_parts={"u": 1},
        evidence_raw_record_ids=[8001],
        bundle_id="bundle.phase04.step12.dup",
        tenant_id=str(tenant.id),
    )
    append_org_primitive_instance(
        db_session,
        tenant_id=tenant.id,
        org_entity_id=ent.id,
        envelope_json=dict(env),
    )
    db_session.commit()
    with pytest.raises(PrimitivePersistenceError, match="duplicate_primitive_key"):
        append_org_primitive_instance(
            db_session,
            tenant_id=tenant.id,
            org_entity_id=ent.id,
            envelope_json=dict(env),
        )


def test_verification_includes_primitive_gates(db_session: Session) -> None:
    from vector.infrastructure.db.models.membership import TenantMembership
    from vector.infrastructure.db.models.tenant import Tenant
    from vector.infrastructure.db.models.user import User

    user = User(email=f"p412v-{uuid.uuid4().hex[:8]}@example.com", full_name="P412v")
    tenant = Tenant(
        company_name="P412v Co",
        primary_email=user.email,
        email_domain="example.com",
        slug=f"p412v-{uuid.uuid4().hex[:10]}",
        status="active",
        workspace_access_enabled=True,
    )
    db_session.add_all([user, tenant])
    db_session.flush()
    db_session.add(TenantMembership(tenant_id=tenant.id, user_id=user.id, role="owner"))
    db_session.commit()
    out = run_canonical_verification(db_session, tenant_id=tenant.id, persist=False)
    ids = {g["id"] for g in out["gates"]}
    assert "G-P04-09" in ids
    assert "G-P04-PRIM-01" in ids


@pytest.mark.integration
def test_admin_primitive_instances_post_list_detail(
    monkeypatch: pytest.MonkeyPatch,
    client: TestClient,
    db_session: Session,
) -> None:
    monkeypatch.setenv("ADMIN_PASSWORD", "integration-admin-password")
    from vector.infrastructure.db.models.membership import TenantMembership
    from vector.infrastructure.db.models.tenant import Tenant
    from vector.infrastructure.db.models.user import User

    user = User(email=f"p412a-{uuid.uuid4().hex[:8]}@example.com", full_name="P412a")
    tenant = Tenant(
        company_name="P412a Co",
        primary_email=user.email,
        email_domain="example.com",
        slug=f"p412a-{uuid.uuid4().hex[:10]}",
        status="active",
        workspace_access_enabled=True,
    )
    db_session.add_all([user, tenant])
    db_session.flush()
    db_session.add(TenantMembership(tenant_id=tenant.id, user_id=user.id, role="owner"))
    db_session.flush()
    ent = upsert_org_entity(
        db_session,
        tenant_id=tenant.id,
        entity_kind="human_actor",
        identity_material={"p": 12},
        metadata_json={},
    )
    db_session.commit()
    env = build_execution_primitive_envelope(
        kind=ExecutionPrimitiveKind.COORDINATION_BURST,
        evidence_parts={"q": 2},
        evidence_raw_record_ids=[7001],
        bundle_id="bundle.phase04.step12.admin",
        tenant_id=str(tenant.id),
    )
    post = client.post(
        f"/admin/tenants/{tenant.id}/cortex/identity/primitive-instances",
        auth=("admin", "integration-admin-password"),
        json={"org_entity_id": str(ent.id), "envelope_json": dict(env)},
    )
    assert post.status_code == 200
    body = post.json()
    assert body["org_primitive_instance_schema_version"] == ORG_PRIMITIVE_INSTANCE_SCHEMA_VERSION
    iid = uuid.UUID(body["instance"]["id"])

    lst = client.get(
        f"/admin/tenants/{tenant.id}/cortex/identity/primitive-instances",
        auth=("admin", "integration-admin-password"),
    )
    assert lst.status_code == 200
    data = lst.json()
    assert any(uuid.UUID(x["id"]) == iid for x in data["instances"])

    det = client.get(
        f"/admin/tenants/{tenant.id}/cortex/identity/primitive-instances/{iid}",
        auth=("admin", "integration-admin-password"),
    )
    assert det.status_code == 200
    assert det.json()["instance"]["primitive_key"] == env["primitive_key"]
