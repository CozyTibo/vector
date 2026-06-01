"""Admin clear-derived Cortex action — keeps raw rows, wipes substrate."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from starlette.testclient import TestClient

from vector.domains.cortex.canon.materialize import execute_canon_pass_for_tenant, materialize_raw_row
from vector.domains.cortex.clear_derived import CLEAR_DERIVED_CORTEX_CONFIRMATION_PHRASE
from vector.infrastructure.db.models.canon_entity import CanonEntity
from vector.infrastructure.db.models.canon_materialization_cursor import CanonMaterializationCursor
from vector.infrastructure.db.models.cortex_pass import CortexPass
from vector.infrastructure.db.models.ingestion_run import IngestionRun
from vector.infrastructure.db.models.membership import TenantMembership
from vector.infrastructure.db.models.raw_ingestion_record import RawIngestionRecord
from vector.infrastructure.db.models.tenant import Tenant
from vector.infrastructure.db.models.tenant_connection import TenantConnection
from vector.infrastructure.db.models.user import User
from vector.domains.cortex.ingestion.live_idempotency import canonical_payload_hash
from vector.settings import get_settings

pytestmark = pytest.mark.integration


def _tenant_with_owner(db_session: Session) -> tuple[uuid.UUID, uuid.UUID]:
    user = User(email=f"clear-{uuid.uuid4().hex[:10]}@example.com", full_name="Clear Derived")
    tenant = Tenant(
        company_name="Clear Derived Co",
        primary_email=user.email,
        email_domain="example.com",
        slug=f"clear-{uuid.uuid4().hex[:8]}",
        status="active",
        workspace_access_enabled=True,
    )
    db_session.add_all([user, tenant])
    db_session.flush()
    db_session.add(TenantMembership(tenant_id=tenant.id, user_id=user.id, role="owner"))
    db_session.flush()
    return tenant.id, user.id


def _seed_raw_and_canon(db_session: Session, tenant_id: uuid.UUID, user_id: uuid.UUID) -> None:
    conn = TenantConnection(
        tenant_id=tenant_id,
        provider="github",
        status="active",
        connected_by_user_id=user_id,
    )
    db_session.add(conn)
    db_session.flush()
    run = IngestionRun(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        connection_id=conn.id,
        connector="github",
        source_trigger="test",
        sync_mode="incremental",
        replay_mode=False,
        replay_version=1,
        status="COMPLETED",
        started_at=datetime.now(UTC),
        finished_at=datetime.now(UTC),
        stats={},
    )
    db_session.add(run)
    db_session.flush()
    body = {"title": "issue for clear-derived test"}
    row = RawIngestionRecord(
        tenant_id=tenant_id,
        connection_id=conn.id,
        connector="github",
        resource_type="github.issue",
        external_id="issue-clear-derived",
        api_endpoint="https://api.github.com/repos/acme/issues/1",
        query_params={},
        payload_body=body,
        payload_hash=canonical_payload_hash(body),
        http_status=200,
        fetched_at=datetime.now(UTC),
        run_id=run.id,
        source_trigger="test",
        idempotency_key=f"idemp-{uuid.uuid4().hex}",
        source_identity_key=f"github:github.issue:issue-clear-derived",
        source_revision_key="hash:test",
    )
    db_session.add(row)
    db_session.flush()
    materialize_raw_row(db_session, row)
    execute_canon_pass_for_tenant(
        db_session,
        tenant_id=tenant_id,
        source_trigger="test",
        batch_limit=100,
    )


def test_admin_clear_derived_requires_confirmation(
    monkeypatch: pytest.MonkeyPatch,
    client: TestClient,
    db_session: Session,
) -> None:
    monkeypatch.setenv("ADMIN_PASSWORD", "integration-admin-password")
    get_settings.cache_clear()
    try:
        tid, uid = _tenant_with_owner(db_session)
        _seed_raw_and_canon(db_session, tid, uid)
        db_session.commit()

        r = client.post(
            f"/admin/tenants/{tid}/cortex/actions/clear-derived",
            auth=("admin", "integration-admin-password"),
            json={"confirmation": "wrong"},
        )
        assert r.status_code == 400
    finally:
        get_settings.cache_clear()


def test_admin_clear_derived_enqueues_background_task(
    monkeypatch: pytest.MonkeyPatch,
    client: TestClient,
    db_session: Session,
) -> None:
    monkeypatch.setenv("ADMIN_PASSWORD", "integration-admin-password")
    get_settings.cache_clear()
    enqueued: list[str] = []

    import app.tasks.cortex_runtime as cortex_runtime

    class _AsyncResult:
        id = "test-clear-derived-task-id"

    monkeypatch.setattr(
        cortex_runtime.clear_derived_cortex_task,
        "delay",
        lambda tenant_id: enqueued.append(tenant_id) or _AsyncResult(),
    )
    try:
        tid, uid = _tenant_with_owner(db_session)
        _seed_raw_and_canon(db_session, tid, uid)
        db_session.commit()

        r = client.post(
            f"/admin/tenants/{tid}/cortex/actions/clear-derived",
            auth=("admin", "integration-admin-password"),
            json={"confirmation": CLEAR_DERIVED_CORTEX_CONFIRMATION_PHRASE},
        )
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["accepted"] is True
        assert body["tenant_id"] == str(tid)
        assert body["task_id"] == "test-clear-derived-task-id"
        assert body["queue"] == "vector"
        assert enqueued == [str(tid)]

        assert (
            db_session.scalar(
                select(func.count()).select_from(CanonEntity).where(CanonEntity.tenant_id == tid),
            )
            or 0
        ) >= 1
    finally:
        get_settings.cache_clear()


def test_clear_derived_task_wipes_canon_keeps_raw_and_enqueues_pass(
    db_session: Session,
) -> None:
    from vector.domains.cortex.clear_derived import (
        clear_derived_cortex_for_tenant,
        enqueue_cortex_rematerialization_after_clear,
    )

    tid, uid = _tenant_with_owner(db_session)
    _seed_raw_and_canon(db_session, tid, uid)
    db_session.commit()

    raw_before = int(
        db_session.scalar(
            select(func.count())
            .select_from(RawIngestionRecord)
            .where(RawIngestionRecord.tenant_id == tid),
        )
        or 0,
    )
    out = clear_derived_cortex_for_tenant(db_session, tenant_id=tid)
    enqueue_cortex_rematerialization_after_clear(db_session, tenant_id=tid)
    db_session.commit()

    assert out["raw_ingestion_rows_remaining"] == raw_before
    assert int(out["deleted_rows_total"]) >= 1
    assert (
        db_session.scalar(
            select(func.count()).select_from(CanonEntity).where(CanonEntity.tenant_id == tid),
        )
        or 0
    ) == 0
    cursor = db_session.scalar(
        select(CanonMaterializationCursor).where(
            CanonMaterializationCursor.tenant_id == tid,
            CanonMaterializationCursor.scope_key == "live",
        ),
    )
    assert cursor is None
    pending_canon = db_session.scalar(
        select(CortexPass).where(
            CortexPass.tenant_id == tid,
            CortexPass.pass_type == "canon_pass",
            CortexPass.status == "pending",
        ),
    )
    assert pending_canon is not None
    assert pending_canon.source_trigger == "clear_derived_admin"
