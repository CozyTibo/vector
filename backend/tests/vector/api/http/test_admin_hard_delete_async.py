"""Admin hard-delete — async enqueue on vector queue."""

from __future__ import annotations

import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from vector.domains.tenancy.hard_delete_tenant import HARD_DELETE_TENANT_CONFIRMATION_PHRASE
from vector.infrastructure.db.models.tenant import Tenant
from vector.settings import get_settings


def _tenant(db: Session) -> tuple[uuid.UUID, str]:
    company = f"DeleteMe-{uuid.uuid4().hex[:8]}"
    tenant = Tenant(
        company_name=company,
        primary_email=f"del-{uuid.uuid4().hex[:8]}@example.com",
        email_domain="example.com",
        slug=f"del-{uuid.uuid4().hex[:8]}",
        status="active",
        workspace_access_enabled=True,
    )
    db.add(tenant)
    db.flush()
    return tenant.id, company


def test_admin_hard_delete_bulk_enqueues_background_task(
    monkeypatch: pytest.MonkeyPatch,
    client: TestClient,
    db_session: Session,
) -> None:
    monkeypatch.setenv("ADMIN_PASSWORD", "integration-admin-password")
    get_settings.cache_clear()
    enqueued: list[list[str]] = []

    import app.tasks.admin_tenancy as admin_tenancy

    class _AsyncResult:
        id = "test-hard-delete-task-id"

    monkeypatch.setattr(
        admin_tenancy.hard_delete_tenants_bulk_task,
        "delay",
        lambda tenant_ids: enqueued.append(list(tenant_ids)) or _AsyncResult(),
    )
    try:
        tid, company_name = _tenant(db_session)
        db_session.commit()

        r = client.post(
            "/admin/tenants/hard-delete-bulk",
            auth=("admin", "integration-admin-password"),
            json={
                "confirmation": HARD_DELETE_TENANT_CONFIRMATION_PHRASE,
                "tenants": [
                    {
                        "tenant_id": str(tid),
                        "company_name_confirmation": company_name,
                    }
                ],
            },
        )
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["accepted"] is True
        assert body["task_id"] == "test-hard-delete-task-id"
        assert body["queue"] == "vector"
        assert body["tenant_count"] == 1
        assert body["tenant_ids"] == [str(tid)]
        assert enqueued == [[str(tid)]]
    finally:
        get_settings.cache_clear()
