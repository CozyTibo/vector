"""Phase 02 Step 3 — temporal continuity runtime model."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from vector.domains.cortex.ingestion.raw_envelope_contract import core_envelope_fields
from vector.domains.cortex.ingestion.raw_memory_temporal import (
    latest_known_before_t,
    list_revision_chain,
    verify_phase02_step3_temporal_continuity,
)
from vector.domains.cortex.ingestion.sync_context import IngestionSyncContext
from vector.domains.cortex.ingestion.sync_executor import _append_raw
from vector.infrastructure.db.models.ingestion_run import IngestionRun
from vector.infrastructure.db.models.raw_memory_revision_index import RawMemoryRevisionIndex
from vector.infrastructure.db.models.tenant_connection import TenantConnection

pytestmark = pytest.mark.integration


def _tenant_with_slack(db_session: Session) -> tuple[uuid.UUID, uuid.UUID]:
    from vector.infrastructure.db.models.membership import TenantMembership
    from vector.infrastructure.db.models.tenant import Tenant
    from vector.infrastructure.db.models.user import User

    user = User(email=f"s3-{uuid.uuid4().hex[:8]}@example.com", full_name="Step3 User")
    tenant = Tenant(
        company_name="Step3Co",
        primary_email=user.email,
        email_domain="example.com",
        slug=f"s3-{uuid.uuid4().hex[:10]}",
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


def test_step3_revision_chain_supersession_and_latest_before(
    db_session: Session,
) -> None:
    tid, _uid = _tenant_with_slack(db_session)
    conn_id = db_session.scalar(
        select(TenantConnection.id).where(
            TenantConnection.tenant_id == tid,
            TenantConnection.provider == "slack",
        )
    )
    assert conn_id is not None
    run_id = uuid.uuid4()
    db_session.add(
        IngestionRun(
            id=run_id,
            tenant_id=tid,
            connection_id=conn_id,
            connector="slack",
            source_trigger="test",
            sync_mode="incremental",
            replay_mode=False,
            replay_version=1,
            status="RUNNING",
            started_at=datetime.now(tz=UTC),
        )
    )
    db_session.flush()
    ctx = IngestionSyncContext.live_incremental()

    base = core_envelope_fields(
        connector="slack",
        connection_id=conn_id,
        source_object_type="slack.message",
        source_object_id="msg-1",
    )
    assert _append_raw(
        db_session,
        ctx=ctx,
        tenant_id=tid,
        connection_id=conn_id,
        connector="slack",
        run_id=run_id,
        source_trigger="test",
        resource_type="slack.message",
        external_id="msg-1",
        api_endpoint="internal://test/1",
        query_params={},
        payload_body={**base, "updated_at": "2026-01-01T00:00:01+00:00", "text": "v1"},
        http_status=200,
        idempotency_key="manual-1",
    )
    assert _append_raw(
        db_session,
        ctx=ctx,
        tenant_id=tid,
        connection_id=conn_id,
        connector="slack",
        run_id=run_id,
        source_trigger="test",
        resource_type="slack.message",
        external_id="msg-1",
        api_endpoint="internal://test/2",
        query_params={},
        payload_body={**base, "updated_at": "2026-01-01T00:00:02+00:00", "text": "v2"},
        http_status=200,
        idempotency_key="manual-2",
    )
    assert _append_raw(
        db_session,
        ctx=ctx,
        tenant_id=tid,
        connection_id=conn_id,
        connector="slack",
        run_id=run_id,
        source_trigger="test",
        resource_type="slack.message",
        external_id="msg-1",
        api_endpoint="internal://test/3",
        query_params={},
        payload_body={
            **base,
            "updated_at": "2026-01-01T00:00:03+00:00",
            "text": "v3",
            "deleted": True,
        },
        http_status=200,
        idempotency_key="manual-3",
    )
    db_session.flush()

    chain = list_revision_chain(
        db_session,
        tenant_id=tid,
        connection_id=conn_id,
        connector="slack",
        resource_type="slack.message",
        source_identity_key="slack:slack.message:msg-1",
    )
    assert len(chain) == 3
    assert chain[0].supersedes_source_revision_key is None
    assert chain[1].supersedes_source_revision_key == chain[0].source_revision_key
    assert chain[2].supersedes_source_revision_key == chain[1].source_revision_key
    assert chain[2].is_deleted_observed is True

    latest_before = latest_known_before_t(
        db_session,
        tenant_id=tid,
        connection_id=conn_id,
        connector="slack",
        resource_type="slack.message",
        source_identity_key="slack:slack.message:msg-1",
        as_of=datetime(2026, 1, 1, 0, 0, 2, 500000, tzinfo=UTC),
    )
    assert latest_before is not None
    assert latest_before.source_revision_key == chain[1].source_revision_key

    rep = verify_phase02_step3_temporal_continuity(db_session, tid)
    assert rep["passed"] is True


def test_step3_revision_index_written_by_sync_executor(
    monkeypatch: pytest.MonkeyPatch,
    db_session: Session,
) -> None:
    from vector.domains.cortex.ingestion.sync_executor import execute_connector_sync
    from vector.settings import get_settings

    monkeypatch.setenv("SECRET_KEY", "unit-test-secret-key-min-32-characters-long!")
    get_settings.cache_clear()
    settings = get_settings()
    tid, _uid = _tenant_with_slack(db_session)
    out = execute_connector_sync(
        db_session,
        settings,
        tenant_id=tid,
        connector_id="slack",
        source_trigger="test",
    )
    assert out["status"] == "completed"
    rev = db_session.scalar(
        select(RawMemoryRevisionIndex).where(
            RawMemoryRevisionIndex.tenant_id == tid,
            RawMemoryRevisionIndex.connector == "slack",
        )
    )
    assert rev is not None
