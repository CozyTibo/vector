"""P04-19 — identity Celery enqueue, dispatch registry, tenant-scoped worker task polling."""

from __future__ import annotations

import uuid
from types import SimpleNamespace

import pytest
from sqlalchemy.orm import Session
from starlette.testclient import TestClient

from app.tasks.cortex_org_link_jobs import run_org_link_replay_job_task

pytestmark = pytest.mark.integration


def _tenant_with_owner(db_session: Session) -> uuid.UUID:
    from vector.infrastructure.db.models.membership import TenantMembership
    from vector.infrastructure.db.models.tenant import Tenant
    from vector.infrastructure.db.models.user import User

    user = User(email=f"p419-{uuid.uuid4().hex[:8]}@example.com", full_name="P419")
    tenant = Tenant(
        company_name="P419 Co",
        primary_email=user.email,
        email_domain="example.com",
        slug=f"p419-{uuid.uuid4().hex[:10]}",
        status="active",
        workspace_access_enabled=True,
    )
    db_session.add_all([user, tenant])
    db_session.flush()
    db_session.add(TenantMembership(tenant_id=tenant.id, user_id=user.id, role="owner"))
    db_session.commit()
    return tenant.id


def test_replay_job_enqueue_sets_celery_id_and_pollable(
    monkeypatch: pytest.MonkeyPatch,
    client: TestClient,
    db_session: Session,
) -> None:
    monkeypatch.setenv("ADMIN_PASSWORD", "integration-admin-password")
    tid = _tenant_with_owner(db_session)
    fake_id = "00000000-0000-4000-8000-000000000099"

    def _fake_delay(*_a: object, **_k: object) -> SimpleNamespace:
        return SimpleNamespace(id=fake_id)

    monkeypatch.setattr(run_org_link_replay_job_task, "delay", _fake_delay)

    post = client.post(
        f"/admin/tenants/{tid}/cortex/debug/identity/replay-jobs/enqueue",
        auth=("admin", "integration-admin-password"),
        json={"job_kind": "candidate_regen", "dry_run": False},
    )
    assert post.status_code == 200
    body = post.json()
    assert body["celery_task_id"] == fake_id
    assert body["job"]["job_kind"] == "candidate_regen"


def test_worker_task_unknown_returns_404(
    monkeypatch: pytest.MonkeyPatch,
    client: TestClient,
    db_session: Session,
) -> None:
    monkeypatch.setenv("ADMIN_PASSWORD", "integration-admin-password")
    tid = _tenant_with_owner(db_session)
    r = client.get(
        f"/admin/tenants/{tid}/cortex/identity/worker-tasks/deadbeef-dead-beef-dead-beefdeadbeef",
        auth=("admin", "integration-admin-password"),
    )
    assert r.status_code == 404


def test_legacy_regenerate_async_collapsed_on_primary(
    monkeypatch: pytest.MonkeyPatch,
    client: TestClient,
    db_session: Session,
) -> None:
    monkeypatch.setenv("ADMIN_PASSWORD", "integration-admin-password")
    tid = _tenant_with_owner(db_session)

    post = client.post(
        f"/admin/tenants/{tid}/cortex/identity/link-candidates/regenerate-async",
        auth=("admin", "integration-admin-password"),
        json={"rule_version": "1.0.0-test"},
    )
    assert post.status_code == 404


def test_projection_export_run_enqueues_graph_job(
    monkeypatch: pytest.MonkeyPatch,
    client: TestClient,
    db_session: Session,
) -> None:
    monkeypatch.setenv("ADMIN_PASSWORD", "integration-admin-password")
    tid = _tenant_with_owner(db_session)
    fake_id = "00000000-0000-4000-8000-0000000000bb"
    monkeypatch.setattr(run_org_link_replay_job_task, "delay", lambda *_a, **_k: SimpleNamespace(id=fake_id))

    post = client.post(
        f"/admin/tenants/{tid}/cortex/identity/projection-export/run",
        auth=("admin", "integration-admin-password"),
    )
    assert post.status_code == 200
    body = post.json()
    assert body["job"]["job_kind"] == "graph_projection_export"
    assert body["celery_task_id"] == fake_id
