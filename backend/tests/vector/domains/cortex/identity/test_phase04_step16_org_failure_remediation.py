"""P04-16 — org failure registry, remediation, G-P04-19, admin HTTP."""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy.orm import Session
from starlette.testclient import TestClient

from vector.domains.cortex.canonical.canonical_verification_engine import run_canonical_verification
from vector.domains.cortex.identity.failure_remediation import (
    ORG_FAILURE_REMEDIATION_RUNTIME_SCHEMA_VERSION,
    recompute_org_derived_failure_cases,
    sync_org_failure_cases,
    validate_org_remediation,
    verify_gp04_19_org_failure_registry_sync,
)
from vector.infrastructure.db.models.cortex_org_link_replay_job import CortexOrgLinkReplayJob


def test_org_failure_remediation_schema_version() -> None:
    assert ORG_FAILURE_REMEDIATION_RUNTIME_SCHEMA_VERSION >= 1


def test_gp04_19_passes_empty_tenant(db_session: Session) -> None:
    from vector.infrastructure.db.models.membership import TenantMembership
    from vector.infrastructure.db.models.tenant import Tenant
    from vector.infrastructure.db.models.user import User

    user = User(email=f"p416-{uuid.uuid4().hex[:8]}@example.com", full_name="P416")
    tenant = Tenant(
        company_name="P416 Co",
        primary_email=user.email,
        email_domain="example.com",
        slug=f"p416-{uuid.uuid4().hex[:10]}",
        status="active",
        workspace_access_enabled=True,
    )
    db_session.add_all([user, tenant])
    db_session.flush()
    db_session.add(TenantMembership(tenant_id=tenant.id, user_id=user.id, role="owner"))
    db_session.commit()
    gate = verify_gp04_19_org_failure_registry_sync(db_session, tenant_id=tenant.id)
    assert gate["id"] == "G-P04-19"
    assert gate["passed"] is True


def test_sync_lists_empty(db_session: Session) -> None:
    from vector.infrastructure.db.models.membership import TenantMembership
    from vector.infrastructure.db.models.tenant import Tenant
    from vector.infrastructure.db.models.user import User

    user = User(email=f"p416b-{uuid.uuid4().hex[:8]}@example.com", full_name="P416b")
    tenant = Tenant(
        company_name="P416b Co",
        primary_email=user.email,
        email_domain="example.com",
        slug=f"p416b-{uuid.uuid4().hex[:10]}",
        status="active",
        workspace_access_enabled=True,
    )
    db_session.add_all([user, tenant])
    db_session.flush()
    db_session.add(TenantMembership(tenant_id=tenant.id, user_id=user.id, role="owner"))
    db_session.commit()
    raw = sync_org_failure_cases(db_session, tenant_id=tenant.id)
    assert raw["active_failure_count"] == 0
    assert raw["org_failure_remediation_runtime_schema_version"] == ORG_FAILURE_REMEDIATION_RUNTIME_SCHEMA_VERSION


def test_org_ambiguity_ack_remediation(db_session: Session) -> None:
    from vector.infrastructure.db.models.membership import TenantMembership
    from vector.infrastructure.db.models.tenant import Tenant
    from vector.infrastructure.db.models.user import User

    user = User(email=f"p416c-{uuid.uuid4().hex[:8]}@example.com", full_name="P416c")
    tenant = Tenant(
        company_name="P416c Co",
        primary_email=user.email,
        email_domain="example.com",
        slug=f"p416c-{uuid.uuid4().hex[:10]}",
        status="active",
        workspace_access_enabled=True,
    )
    db_session.add_all([user, tenant])
    db_session.flush()
    db_session.add(TenantMembership(tenant_id=tenant.id, user_id=user.id, role="owner"))
    db_session.commit()
    out = validate_org_remediation(
        db_session,
        tenant_id=tenant.id,
        remediation_class="org_ambiguity_triage_ack",
        dry_run=True,
        confirm_execution=False,
        failure_case_gap_id=None,
        payload={"note": "ack"},
    )
    assert out["validation"]["result_status"] == "pass"
    db_session.commit()


def test_failed_replay_job_surfaces_in_sync(db_session: Session) -> None:
    from vector.infrastructure.db.models.membership import TenantMembership
    from vector.infrastructure.db.models.tenant import Tenant
    from vector.infrastructure.db.models.user import User

    user = User(email=f"p416d-{uuid.uuid4().hex[:8]}@example.com", full_name="P416d")
    tenant = Tenant(
        company_name="P416d Co",
        primary_email=user.email,
        email_domain="example.com",
        slug=f"p416d-{uuid.uuid4().hex[:10]}",
        status="active",
        workspace_access_enabled=True,
    )
    db_session.add_all([user, tenant])
    db_session.flush()
    db_session.add(TenantMembership(tenant_id=tenant.id, user_id=user.id, role="owner"))
    db_session.flush()
    job = CortexOrgLinkReplayJob(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        job_kind="authoritative_replay",
        pinned_rule_version=None,
        dry_run=False,
        status="failed",
        scope_json={},
        summary_json={},
        error_detail="forced_test_failure",
        engine_build_ref="test",
    )
    db_session.add(job)
    db_session.commit()
    recompute_org_derived_failure_cases(db_session, tenant_id=tenant.id)
    db_session.commit()
    raw = sync_org_failure_cases(db_session, tenant_id=tenant.id)
    assert raw["active_failure_count"] >= 1
    classes = raw["active_failure_classes"]
    assert classes.get("org_link_replay_job_failed", 0) >= 1


@pytest.mark.integration
def test_admin_identity_failures_and_remediation(
    monkeypatch: pytest.MonkeyPatch,
    client: TestClient,
    db_session: Session,
) -> None:
    monkeypatch.setenv("ADMIN_PASSWORD", "integration-admin-password")
    from vector.infrastructure.db.models.membership import TenantMembership
    from vector.infrastructure.db.models.tenant import Tenant
    from vector.infrastructure.db.models.user import User

    user = User(email=f"p416e-{uuid.uuid4().hex[:8]}@example.com", full_name="P416e")
    tenant = Tenant(
        company_name="P416e Co",
        primary_email=user.email,
        email_domain="example.com",
        slug=f"p416e-{uuid.uuid4().hex[:10]}",
        status="active",
        workspace_access_enabled=True,
    )
    db_session.add_all([user, tenant])
    db_session.flush()
    db_session.add(TenantMembership(tenant_id=tenant.id, user_id=user.id, role="owner"))
    db_session.commit()

    r = client.get(
        f"/admin/tenants/{tenant.id}/cortex/identity/failures",
        auth=("admin", "integration-admin-password"),
    )
    assert r.status_code == 200
    body = r.json()
    assert body["org_failure_remediation_runtime_schema_version"] == ORG_FAILURE_REMEDIATION_RUNTIME_SCHEMA_VERSION

    r2 = client.post(
        f"/admin/tenants/{tenant.id}/cortex/identity/remediation/validate",
        auth=("admin", "integration-admin-password"),
        json={
            "remediation_class": "org_link_replay_retry",
            "dry_run": True,
            "confirm_execution": False,
            "payload": {"job_kind": "authoritative_replay"},
        },
    )
    assert r2.status_code == 200
    v = r2.json()["validation"]
    assert v["result_status"] == "pass"


def test_canonical_verification_includes_gp04_19(db_session: Session) -> None:
    from vector.infrastructure.db.models.membership import TenantMembership
    from vector.infrastructure.db.models.tenant import Tenant
    from vector.infrastructure.db.models.user import User

    user = User(email=f"p416f-{uuid.uuid4().hex[:8]}@example.com", full_name="P416f")
    tenant = Tenant(
        company_name="P416f Co",
        primary_email=user.email,
        email_domain="example.com",
        slug=f"p416f-{uuid.uuid4().hex[:10]}",
        status="active",
        workspace_access_enabled=True,
    )
    db_session.add_all([user, tenant])
    db_session.flush()
    db_session.add(TenantMembership(tenant_id=tenant.id, user_id=user.id, role="owner"))
    db_session.commit()
    out = run_canonical_verification(db_session, tenant_id=tenant.id, materialization_sample_limit=3, persist=False)
    ids = {g["id"] for g in out["gates"]}
    assert "G-P04-19" in ids
