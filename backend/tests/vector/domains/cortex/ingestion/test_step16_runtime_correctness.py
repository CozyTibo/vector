"""Phase 01 Step 16 — runtime correctness hardening validation."""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from vector.domains.cortex.ingestion.runtime_correctness import verify_runtime_correctness_invariants
from vector.domains.cortex.ingestion.sync_context import IngestionSyncContext
from vector.domains.cortex.ingestion.sync_executor import execute_connector_sync
from vector.infrastructure.db.models.connector_sync_state import ConnectorSyncState
from vector.infrastructure.db.models.membership import TenantMembership
from vector.infrastructure.db.models.raw_ingestion_record import RawIngestionRecord
from vector.infrastructure.db.models.tenant import Tenant
from vector.infrastructure.db.models.tenant_connection import TenantConnection
from vector.infrastructure.db.models.user import User
from vector.settings import get_settings

pytestmark = pytest.mark.integration


def _tenant_with_slack_connections(db_session: Session, *, active_connections: int = 1) -> tuple[uuid.UUID, list[uuid.UUID]]:
    user = User(email=f"step16-{uuid.uuid4().hex[:8]}@example.com", full_name="Step16 User")
    tenant = Tenant(
        company_name="Step16 Co",
        primary_email=user.email,
        email_domain="example.com",
        slug=f"step16-{uuid.uuid4().hex[:10]}",
        status="active",
        workspace_access_enabled=True,
    )
    db_session.add_all([user, tenant])
    db_session.flush()
    db_session.add(TenantMembership(tenant_id=tenant.id, user_id=user.id, role="owner"))
    conn_ids: list[uuid.UUID] = []
    for _ in range(active_connections):
        conn = TenantConnection(
            tenant_id=tenant.id,
            provider="slack",
            status="active",
            connected_by_user_id=user.id,
        )
        db_session.add(conn)
        db_session.flush()
        conn_ids.append(conn.id)
    db_session.flush()
    return tenant.id, conn_ids


def test_step16_live_uniqueness_is_connection_scoped(
    monkeypatch: pytest.MonkeyPatch,
    db_session: Session,
) -> None:
    monkeypatch.setenv("SECRET_KEY", "unit-test-secret-key-min-32-characters-long!")
    get_settings.cache_clear()
    settings = get_settings()
    tenant_id, conn_ids = _tenant_with_slack_connections(db_session, active_connections=2)

    out1 = execute_connector_sync(
        db_session,
        settings,
        tenant_id=tenant_id,
        connector_id="slack",
        source_trigger="manual_admin",
        connection_id=conn_ids[0],
    )
    out2 = execute_connector_sync(
        db_session,
        settings,
        tenant_id=tenant_id,
        connector_id="slack",
        source_trigger="manual_admin",
        connection_id=conn_ids[1],
    )
    assert out1["status"] == "completed"
    assert out2["status"] == "completed"

    count_stmt = (
        select(func.count())
        .select_from(RawIngestionRecord)
        .where(
            RawIngestionRecord.tenant_id == tenant_id,
            RawIngestionRecord.connector == "slack",
            RawIngestionRecord.resource_type == "slack.scope_ping",
            RawIngestionRecord.external_id == "missing-slack-detail",
            RawIngestionRecord.replay_job_id.is_(None),
        )
    )
    assert int(db_session.scalar(count_stmt) or 0) == 2

    inv = verify_runtime_correctness_invariants(db_session, tenant_id)
    assert inv["passed"] is True


def test_step16_replay_live_overlap_isolation_and_retry_safe(
    monkeypatch: pytest.MonkeyPatch,
    db_session: Session,
) -> None:
    monkeypatch.setenv("SECRET_KEY", "unit-test-secret-key-min-32-characters-long!")
    get_settings.cache_clear()
    settings = get_settings()
    tenant_id, conn_ids = _tenant_with_slack_connections(db_session, active_connections=1)
    conn_id = conn_ids[0]
    replay_job = uuid.uuid4()

    live = execute_connector_sync(
        db_session,
        settings,
        tenant_id=tenant_id,
        connector_id="slack",
        source_trigger="manual_admin",
        connection_id=conn_id,
    )
    replay_1 = execute_connector_sync(
        db_session,
        settings,
        tenant_id=tenant_id,
        connector_id="slack",
        source_trigger="manual_admin_replay",
        connection_id=conn_id,
        ingestion_sync_context=IngestionSyncContext.replay(replay_job_id=replay_job, replay_version=1),
    )
    replay_2 = execute_connector_sync(
        db_session,
        settings,
        tenant_id=tenant_id,
        connector_id="slack",
        source_trigger="manual_admin_replay",
        connection_id=conn_id,
        ingestion_sync_context=IngestionSyncContext.replay(replay_job_id=replay_job, replay_version=1),
    )
    assert live["status"] == "completed"
    assert replay_1["status"] == "completed"
    assert replay_2["status"] == "completed"
    assert replay_2["records_written"] == 0

    live_count = int(
        db_session.scalar(
            select(func.count())
            .select_from(RawIngestionRecord)
            .where(
                RawIngestionRecord.tenant_id == tenant_id,
                RawIngestionRecord.connector == "slack",
                RawIngestionRecord.resource_type == "slack.scope_ping",
                RawIngestionRecord.replay_job_id.is_(None),
            )
        )
        or 0,
    )
    replay_count = int(
        db_session.scalar(
            select(func.count())
            .select_from(RawIngestionRecord)
            .where(
                RawIngestionRecord.tenant_id == tenant_id,
                RawIngestionRecord.connector == "slack",
                RawIngestionRecord.resource_type == "slack.scope_ping",
                RawIngestionRecord.replay_job_id == replay_job,
            )
        )
        or 0,
    )
    assert live_count == 1
    assert replay_count == 1

    live_scope = db_session.scalar(
        select(ConnectorSyncState).where(
            ConnectorSyncState.tenant_id == tenant_id,
            ConnectorSyncState.connection_id == conn_id,
            ConnectorSyncState.connector == "slack",
            ConnectorSyncState.scope_key == "default",
        )
    )
    replay_scope = db_session.scalar(
        select(ConnectorSyncState).where(
            ConnectorSyncState.tenant_id == tenant_id,
            ConnectorSyncState.connection_id == conn_id,
            ConnectorSyncState.connector == "slack",
            ConnectorSyncState.scope_key == f"replay:{replay_job}",
        )
    )
    assert live_scope is not None
    assert replay_scope is not None
