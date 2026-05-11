"""P04-18 — operator console HTTP §15 routes, explorer rows, audits, verification gates."""

from __future__ import annotations

import uuid
from types import SimpleNamespace

import pytest
from sqlalchemy.orm import Session
from starlette.testclient import TestClient

from vector.domains.cortex.canonical.canonical_verification_engine import run_canonical_verification
from vector.domains.cortex.identity.operator_console import IDENTITY_OPERATOR_CONSOLE_CONFIRM_PHRASE


def test_canonical_verification_includes_gp04_22_to_26(db_session: Session) -> None:
    from vector.infrastructure.db.models.membership import TenantMembership
    from vector.infrastructure.db.models.tenant import Tenant
    from vector.infrastructure.db.models.user import User

    user = User(email=f"p418-{uuid.uuid4().hex[:8]}@example.com", full_name="P418")
    tenant = Tenant(
        company_name="P418 Co",
        primary_email=user.email,
        email_domain="example.com",
        slug=f"p418-{uuid.uuid4().hex[:10]}",
        status="active",
        workspace_access_enabled=True,
    )
    db_session.add_all([user, tenant])
    db_session.flush()
    db_session.add(TenantMembership(tenant_id=tenant.id, user_id=user.id, role="owner"))
    db_session.commit()

    full = run_canonical_verification(db_session, tenant_id=tenant.id, materialization_sample_limit=3, persist=False)
    ids = {g["id"] for g in full["gates"]}
    for gid in ("G-P04-22", "G-P04-23", "G-P04-24", "G-P04-25", "G-P04-26"):
        assert gid in ids
        g = next(x for x in full["gates"] if x["id"] == gid)
        assert g["passed"] is True


@pytest.mark.integration
def test_admin_operator_console_routes_smoke(
    monkeypatch: pytest.MonkeyPatch,
    client: TestClient,
    db_session: Session,
) -> None:
    monkeypatch.setenv("ADMIN_PASSWORD", "integration-admin-password")
    from vector.infrastructure.db.models.membership import TenantMembership
    from vector.infrastructure.db.models.tenant import Tenant
    from vector.infrastructure.db.models.user import User

    user = User(email=f"p418b-{uuid.uuid4().hex[:8]}@example.com", full_name="P418b")
    tenant = Tenant(
        company_name="P418b Co",
        primary_email=user.email,
        email_domain="example.com",
        slug=f"p418b-{uuid.uuid4().hex[:10]}",
        status="active",
        workspace_access_enabled=True,
    )
    db_session.add_all([user, tenant])
    db_session.flush()
    db_session.add(TenantMembership(tenant_id=tenant.id, user_id=user.id, role="owner"))
    db_session.commit()

    auth = ("admin", "integration-admin-password")
    tid = str(tenant.id)

    r = client.get(f"/admin/tenants/{tid}/cortex/identity/handles", auth=auth)
    assert r.status_code == 200
    assert r.json()["list_contract"] == "org_handle_list_row_v1"

    r = client.get(f"/admin/tenants/{tid}/cortex/identity/links?authoritative_only=true&limit=5", auth=auth)
    assert r.status_code == 200
    body = r.json()
    assert body["explorer_contract"] == "org_link_list_row_v1"
    assert isinstance(body["explorer_rows"], list)

    r = client.get(f"/admin/tenants/{tid}/cortex/identity/merge-queue", auth=auth)
    assert r.status_code == 200
    assert r.json()["queue_contract"] == "org_merge_queue_row_v1"

    r = client.get(f"/admin/tenants/{tid}/cortex/identity/ambiguity-queue", auth=auth)
    assert r.status_code == 200
    assert r.json()["queue_contract"] == "org_ambiguity_queue_row_v1"

    r = client.get(f"/admin/tenants/{tid}/cortex/identity/primitives", auth=auth)
    assert r.status_code == 200
    prim = r.json()
    assert prim["list_contract"] == "org_primitive_list_row_v1"
    assert prim["include_raw_envelope"] is False
    for row in prim["rows"]:
        assert "envelope_json" not in row

    r = client.get(f"/admin/tenants/{tid}/cortex/identity/projection-preview", auth=auth)
    assert r.status_code == 200
    pv = r.json()
    assert "nodes" not in pv and "edges" not in pv
    assert "projection_hash" in pv

    from app.tasks.cortex_org_link_jobs import run_org_link_replay_job_task

    monkeypatch.setattr(
        run_org_link_replay_job_task,
        "delay",
        lambda *_a, **_k: SimpleNamespace(id="00000000-0000-4000-8000-0000000000cc"),
    )
    r = client.post(f"/admin/tenants/{tid}/cortex/identity/projection-export/run", auth=auth)
    assert r.status_code == 200
    export = r.json()
    assert export["job"]["job_kind"] == "graph_projection_export"
    assert export["celery_task_id"] == "00000000-0000-4000-8000-0000000000cc"


@pytest.mark.integration
def test_merge_queue_action_and_link_revoke_write_audit(
    monkeypatch: pytest.MonkeyPatch,
    client: TestClient,
    db_session: Session,
) -> None:
    monkeypatch.setenv("ADMIN_PASSWORD", "integration-admin-password")
    from vector.infrastructure.db.models.cortex_org_entity import CortexOrgEntity
    from vector.infrastructure.db.models.cortex_org_link import CortexOrgLink
    from vector.infrastructure.db.models.cortex_org_merge import CortexOrgMerge
    from vector.infrastructure.db.models.cortex_org_merge_policy import CortexOrgMergePolicy
    from vector.infrastructure.db.models.membership import TenantMembership
    from vector.infrastructure.db.models.tenant import Tenant
    from vector.infrastructure.db.models.user import User

    user = User(email=f"p418c-{uuid.uuid4().hex[:8]}@example.com", full_name="P418c")
    tenant = Tenant(
        company_name="P418c Co",
        primary_email=user.email,
        email_domain="example.com",
        slug=f"p418c-{uuid.uuid4().hex[:10]}",
        status="active",
        workspace_access_enabled=True,
    )
    db_session.add_all([user, tenant])
    db_session.flush()
    db_session.add(TenantMembership(tenant_id=tenant.id, user_id=user.id, role="owner"))
    pol = CortexOrgMergePolicy(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        policy_ref="p418c-test",
        engine_build_ref="test",
    )
    db_session.add(pol)
    db_session.flush()
    e1 = CortexOrgEntity(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        entity_kind="human_actor",
        lifecycle_state="active",
        identity_key_fingerprint="a" * 64,
        metadata_json={},
        engine_build_ref="test",
    )
    e2 = CortexOrgEntity(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        entity_kind="human_actor",
        lifecycle_state="active",
        identity_key_fingerprint="b" * 64,
        metadata_json={},
        engine_build_ref="test",
    )
    db_session.add_all([e1, e2])
    merge = CortexOrgMerge(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        merge_kind="team_merge",
        merge_policy_id=pol.id,
        source_entity_ids=[str(e1.id)],
        target_entity_id=e2.id,
        evidence_raw_record_ids=[1],
        metadata_json={"merge_queue_status": "pending"},
        engine_build_ref="test",
    )
    link = CortexOrgLink(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        link_type="org.test_link",
        source_entity_id=e1.id,
        target_entity_id=e2.id,
        evidence_raw_record_ids=[1, 2],
        rule_id=None,
        confidence_class="test",
        link_authority="authoritative",
        link_class="authoritative",
        metadata_json={},
        engine_build_ref="test",
    )
    db_session.add_all([merge, link])
    db_session.commit()

    auth = ("admin", "integration-admin-password")
    tid = str(tenant.id)
    payload = {"confirmation_phrase": IDENTITY_OPERATOR_CONSOLE_CONFIRM_PHRASE}

    r = client.post(
        f"/admin/tenants/{tid}/cortex/identity/merge-queue/{merge.id}/approve",
        auth=auth,
        json=payload,
    )
    assert r.status_code == 200

    r = client.post(
        f"/admin/tenants/{tid}/cortex/identity/links/{link.id}/revoke",
        auth=auth,
        json=payload,
    )
    assert r.status_code == 200

    from sqlalchemy import select

    from vector.infrastructure.db.models.cortex_org_identity_console_audit import CortexOrgIdentityConsoleAudit

    audits = list(
        db_session.scalars(
            select(CortexOrgIdentityConsoleAudit).where(CortexOrgIdentityConsoleAudit.tenant_id == tenant.id)
        ).all()
    )
    kinds = {a.action_kind for a in audits}
    assert "merge_queue_approve" in kinds
    assert "org_link_revoke" in kinds
