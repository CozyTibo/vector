"""P04-10 — org link continuity replay jobs, L-class receipts, G-P04-RPL-01, admin HTTP."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy.orm import Session
from starlette.testclient import TestClient

from app.celery_app import celery_app
from vector.domains.cortex.canonical.canonical_verification_engine import run_canonical_verification
from vector.domains.cortex.identity.anchor_continuity_candidates import ANCHOR_CONTINUITY_RULE_SEMANTIC
from vector.domains.cortex.identity.org_link_replay_runtime import (
    ORG_LINK_REPLAY_ENGINE_BUILD_REF,
    ORG_LINK_REPLAY_SCHEMA_VERSION,
    execute_org_link_replay_job,
    list_completed_org_link_replay_jobs_missing_receipts,
    verify_org_link_replay_rpl01_static,
)
from vector.infrastructure.db.models.cortex_org_link_replay_job import CortexOrgLinkReplayJob


def test_gp04_rpl01_static_passes() -> None:
    st = verify_org_link_replay_rpl01_static()
    assert st["passed"] is True
    assert st["id"] == "G-P04-RPL-01"


def test_execute_authoritative_replay_emits_receipt(db_session: Session) -> None:
    from vector.infrastructure.db.models.membership import TenantMembership
    from vector.infrastructure.db.models.tenant import Tenant
    from vector.infrastructure.db.models.user import User

    user = User(email=f"p410-{uuid.uuid4().hex[:8]}@example.com", full_name="P410")
    tenant = Tenant(
        company_name="P410 Co",
        primary_email=user.email,
        email_domain="example.com",
        slug=f"p410-{uuid.uuid4().hex[:10]}",
        status="active",
        workspace_access_enabled=True,
    )
    db_session.add_all([user, tenant])
    db_session.flush()
    db_session.add(TenantMembership(tenant_id=tenant.id, user_id=user.id, role="owner"))
    db_session.flush()
    job = execute_org_link_replay_job(
        db_session,
        tenant_id=tenant.id,
        job_kind="authoritative_replay",
        dry_run=False,
    )
    db_session.commit()
    assert job.status == "completed"
    assert len(job.receipts) == 1
    assert job.receipts[0].receipt_class == "L0"


def test_candidate_regen_defaults_to_anchor_continuity_rule(db_session: Session) -> None:
    from vector.infrastructure.db.models.membership import TenantMembership
    from vector.infrastructure.db.models.tenant import Tenant
    from vector.infrastructure.db.models.user import User

    user = User(email=f"p410b-{uuid.uuid4().hex[:8]}@example.com", full_name="P410b")
    tenant = Tenant(
        company_name="P410b Co",
        primary_email=user.email,
        email_domain="example.com",
        slug=f"p410b-{uuid.uuid4().hex[:10]}",
        status="active",
        workspace_access_enabled=True,
    )
    db_session.add_all([user, tenant])
    db_session.flush()
    db_session.add(TenantMembership(tenant_id=tenant.id, user_id=user.id, role="owner"))
    db_session.flush()
    job = execute_org_link_replay_job(
        db_session,
        tenant_id=tenant.id,
        job_kind="candidate_regen",
        dry_run=False,
        pinned_rule_version=None,
    )
    db_session.commit()
    assert job.status == "completed"
    assert job.pinned_rule_version == ANCHOR_CONTINUITY_RULE_SEMANTIC
    assert job.summary_json.get("replay_lane") == "anchor_continuity"


def test_completed_job_without_receipt_fails_gate(db_session: Session) -> None:
    from vector.infrastructure.db.models.membership import TenantMembership
    from vector.infrastructure.db.models.tenant import Tenant
    from vector.infrastructure.db.models.user import User

    user = User(email=f"p410c-{uuid.uuid4().hex[:8]}@example.com", full_name="P410c")
    tenant = Tenant(
        company_name="P410c Co",
        primary_email=user.email,
        email_domain="example.com",
        slug=f"p410c-{uuid.uuid4().hex[:10]}",
        status="active",
        workspace_access_enabled=True,
    )
    db_session.add_all([user, tenant])
    db_session.flush()
    db_session.add(TenantMembership(tenant_id=tenant.id, user_id=user.id, role="owner"))
    db_session.flush()
    bad = CortexOrgLinkReplayJob(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        job_kind="authoritative_replay",
        pinned_rule_version=None,
        dry_run=False,
        status="completed",
        scope_json={},
        summary_json={},
        engine_build_ref=ORG_LINK_REPLAY_ENGINE_BUILD_REF,
        started_at=datetime.now(tz=UTC),
        completed_at=datetime.now(tz=UTC),
    )
    db_session.add(bad)
    db_session.commit()
    assert list_completed_org_link_replay_jobs_missing_receipts(db_session, tenant_id=tenant.id) == [bad.id]
    out = run_canonical_verification(db_session, tenant_id=tenant.id, persist=False)
    gate = next(g for g in out["gates"] if g["id"] == "G-P04-RPL-01")
    assert gate["passed"] is False


def test_verification_includes_rpl01_gate(db_session: Session) -> None:
    from vector.infrastructure.db.models.membership import TenantMembership
    from vector.infrastructure.db.models.tenant import Tenant
    from vector.infrastructure.db.models.user import User

    user = User(email=f"p410v-{uuid.uuid4().hex[:8]}@example.com", full_name="P410v")
    tenant = Tenant(
        company_name="P410v Co",
        primary_email=user.email,
        email_domain="example.com",
        slug=f"p410v-{uuid.uuid4().hex[:10]}",
        status="active",
        workspace_access_enabled=True,
    )
    db_session.add_all([user, tenant])
    db_session.flush()
    db_session.add(TenantMembership(tenant_id=tenant.id, user_id=user.id, role="owner"))
    db_session.commit()
    out = run_canonical_verification(db_session, tenant_id=tenant.id, persist=False)
    ids = {g["id"] for g in out["gates"]}
    assert "G-P04-RPL-01" in ids


def test_celery_registers_run_org_link_replay_job() -> None:
    assert "vector.cortex.identity.run_org_link_replay_job" in celery_app.tasks


@pytest.mark.integration
def test_admin_org_link_replay_run_list_detail(
    monkeypatch: pytest.MonkeyPatch,
    client: TestClient,
    db_session: Session,
) -> None:
    monkeypatch.setenv("ADMIN_PASSWORD", "integration-admin-password")
    from vector.infrastructure.db.models.membership import TenantMembership
    from vector.infrastructure.db.models.tenant import Tenant
    from vector.infrastructure.db.models.user import User

    user = User(email=f"p410a-{uuid.uuid4().hex[:8]}@example.com", full_name="P410a")
    tenant = Tenant(
        company_name="P410a Co",
        primary_email=user.email,
        email_domain="example.com",
        slug=f"p410a-{uuid.uuid4().hex[:10]}",
        status="active",
        workspace_access_enabled=True,
    )
    db_session.add_all([user, tenant])
    db_session.flush()
    db_session.add(TenantMembership(tenant_id=tenant.id, user_id=user.id, role="owner"))
    db_session.commit()

    post = client.post(
        f"/admin/tenants/{tenant.id}/cortex/identity/replay-jobs/run",
        auth=("admin", "integration-admin-password"),
        json={"job_kind": "authoritative_replay", "dry_run": False},
    )
    assert post.status_code == 200
    body = post.json()
    assert body["job"]["status"] == "completed"
    assert body["job"]["job_kind"] == "authoritative_replay"
