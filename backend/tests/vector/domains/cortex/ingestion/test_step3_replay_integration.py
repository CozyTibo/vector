"""Phase 01 Step 3 — replay executor (requires DATABASE_URL + migrated schema)."""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session

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


def _tenant_with_slack(db_session: Session) -> tuple[uuid.UUID, uuid.UUID]:
    user = User(email=f"rpl-{uuid.uuid4().hex[:8]}@example.com", full_name="Replay User")
    tenant = Tenant(
        company_name="ReplayCo",
        primary_email=user.email,
        email_domain="example.com",
        slug=f"rpl-{uuid.uuid4().hex[:10]}",
        status="active",
        workspace_access_enabled=True,
    )
    db_session.add_all([user, tenant])
    db_session.flush()
    db_session.add(TenantMembership(tenant_id=tenant.id, user_id=user.id, role="owner"))
    db_session.add(
        TenantConnection(
            tenant_id=tenant.id,
            provider="slack",
            status="active",
            connected_by_user_id=user.id,
        ),
    )
    db_session.flush()
    return tenant.id, user.id


def test_replay_second_run_inserts_no_duplicate_raw_rows(
    monkeypatch: pytest.MonkeyPatch,
    db_session: Session,
) -> None:
    monkeypatch.setenv("SECRET_KEY", "unit-test-secret-key-min-32-characters-long!")
    get_settings.cache_clear()
    settings = get_settings()
    tid, _uid = _tenant_with_slack(db_session)
    conn_id = db_session.scalar(
        select(TenantConnection.id).where(
            TenantConnection.tenant_id == tid,
            TenantConnection.provider == "slack",
        )
    )
    assert conn_id is not None
    job = uuid.uuid4()
    ctx = IngestionSyncContext.replay(replay_job_id=job, replay_version=1)

    out1 = execute_connector_sync(
        db_session,
        settings,
        tenant_id=tid,
        connector_id="slack",
        source_trigger="replay",
        ingestion_sync_context=ctx,
    )
    assert out1["status"] == "completed"
    assert out1["records_written"] == 1
    assert out1.get("verification", {}).get("passed") is True

    n_raw_1 = db_session.scalar(
        select(func.count())
        .select_from(RawIngestionRecord)
        .where(RawIngestionRecord.replay_job_id == job),
    )
    assert n_raw_1 == 1

    out2 = execute_connector_sync(
        db_session,
        settings,
        tenant_id=tid,
        connector_id="slack",
        source_trigger="replay",
        ingestion_sync_context=ctx,
    )
    assert out2["status"] == "completed"
    assert out2["records_written"] == 0
    assert out2.get("verification", {}).get("passed") is True

    n_raw_2 = db_session.scalar(
        select(func.count())
        .select_from(RawIngestionRecord)
        .where(RawIngestionRecord.replay_job_id == job),
    )
    assert n_raw_2 == 1

    scope = f"replay:{job}"
    st = db_session.scalar(
        select(ConnectorSyncState).where(
            ConnectorSyncState.tenant_id == tid,
            ConnectorSyncState.connection_id == conn_id,
            ConnectorSyncState.connector == "slack",
            ConnectorSyncState.scope_key == scope,
        )
    )
    assert st is not None
    assert st.state.get("ping") is True
    assert st.state.get("checkpoint_schema_version") == 2
    assert st.state.get("meta", {}).get("last_writer_mode") == "incremental"
    assert st.state.get("modes", {}).get("incremental", {}).get("ping") is True


def test_replay_and_live_use_isolated_checkpoint_scopes(
    monkeypatch: pytest.MonkeyPatch,
    db_session: Session,
) -> None:
    monkeypatch.setenv("SECRET_KEY", "unit-test-secret-key-min-32-characters-long!")
    get_settings.cache_clear()
    settings = get_settings()
    tid, _uid = _tenant_with_slack(db_session)
    conn_id = db_session.scalar(
        select(TenantConnection.id).where(
            TenantConnection.tenant_id == tid,
            TenantConnection.provider == "slack",
        )
    )
    assert conn_id is not None
    replay_job = uuid.uuid4()

    live_out = execute_connector_sync(
        db_session,
        settings,
        tenant_id=tid,
        connector_id="slack",
        source_trigger="manual",
        ingestion_sync_context=IngestionSyncContext.live_incremental(),
    )
    replay_out = execute_connector_sync(
        db_session,
        settings,
        tenant_id=tid,
        connector_id="slack",
        source_trigger="replay",
        ingestion_sync_context=IngestionSyncContext.replay(replay_job_id=replay_job),
    )
    assert live_out["status"] == "completed"
    assert replay_out["status"] == "completed"

    live_state = db_session.scalar(
        select(ConnectorSyncState).where(
            ConnectorSyncState.tenant_id == tid,
            ConnectorSyncState.connection_id == conn_id,
            ConnectorSyncState.connector == "slack",
            ConnectorSyncState.scope_key == "default",
        )
    )
    replay_state = db_session.scalar(
        select(ConnectorSyncState).where(
            ConnectorSyncState.tenant_id == tid,
            ConnectorSyncState.connection_id == conn_id,
            ConnectorSyncState.connector == "slack",
            ConnectorSyncState.scope_key == f"replay:{replay_job}",
        )
    )
    assert live_state is not None
    assert replay_state is not None
    assert live_state.state.get("checkpoint_schema_version") == 2
    assert replay_state.state.get("checkpoint_schema_version") == 2
    assert live_state.scope_key != replay_state.scope_key
