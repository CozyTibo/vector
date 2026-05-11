"""Phase 02 Step 4 — replay equivalence + divergence classes."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from vector.domains.cortex.ingestion.raw_envelope_contract import core_envelope_fields
from vector.domains.cortex.ingestion.raw_memory_replay import verify_phase02_step4_replay_equivalence
from vector.domains.cortex.ingestion.sync_context import IngestionSyncContext
from vector.domains.cortex.ingestion.sync_executor import _append_raw, execute_connector_sync
from vector.infrastructure.db.models.ingestion_run import IngestionRun
from vector.infrastructure.db.models.tenant_connection import TenantConnection
from vector.settings import get_settings

pytestmark = pytest.mark.integration


def _tenant_with_slack(db_session: Session) -> tuple[uuid.UUID, uuid.UUID]:
    from vector.infrastructure.db.models.membership import TenantMembership
    from vector.infrastructure.db.models.tenant import Tenant
    from vector.infrastructure.db.models.user import User

    user = User(email=f"s4-{uuid.uuid4().hex[:8]}@example.com", full_name="Step4 User")
    tenant = Tenant(
        company_name="Step4Co",
        primary_email=user.email,
        email_domain="example.com",
        slug=f"s4-{uuid.uuid4().hex[:10]}",
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


def test_step4_replay_equivalence_unverifiable_without_replay(db_session: Session) -> None:
    rep = verify_phase02_step4_replay_equivalence(db_session, uuid.uuid4())
    assert rep["passed"] is True
    assert rep["state"] == "unverifiable"
    assert rep["summary"]["jobs_examined"] == 0


def test_step4_replay_equivalent_d0(
    monkeypatch: pytest.MonkeyPatch,
    db_session: Session,
) -> None:
    monkeypatch.setenv("SECRET_KEY", "unit-test-secret-key-min-32-characters-long!")
    get_settings.cache_clear()
    settings = get_settings()
    tid, _uid = _tenant_with_slack(db_session)
    replay_job = uuid.uuid4()

    live = execute_connector_sync(
        db_session,
        settings,
        tenant_id=tid,
        connector_id="slack",
        source_trigger="live",
    )
    assert live["status"] == "completed"
    replay = execute_connector_sync(
        db_session,
        settings,
        tenant_id=tid,
        connector_id="slack",
        source_trigger="replay",
        ingestion_sync_context=IngestionSyncContext.replay(replay_job_id=replay_job),
    )
    assert replay["status"] == "completed"

    rep = verify_phase02_step4_replay_equivalence(db_session, tid)
    assert rep["passed"] is True
    assert rep["summary"]["jobs_examined"] >= 1
    assert rep["summary"]["highest_divergence"]["class"] == "D0"


def test_step4_replay_provider_mutation_classified_d1(db_session: Session) -> None:
    tid, _uid = _tenant_with_slack(db_session)
    conn_id = db_session.scalar(
        select(TenantConnection.id).where(
            TenantConnection.tenant_id == tid,
            TenantConnection.provider == "slack",
        )
    )
    assert conn_id is not None

    live_run_id = uuid.uuid4()
    replay_run_id = uuid.uuid4()
    replay_job_id = uuid.uuid4()
    db_session.add_all(
        [
            IngestionRun(
                id=live_run_id,
                tenant_id=tid,
                connection_id=conn_id,
                connector="slack",
                source_trigger="test",
                sync_mode="incremental",
                replay_mode=False,
                replay_version=1,
                status="RUNNING",
                started_at=datetime.now(tz=UTC),
            ),
            IngestionRun(
                id=replay_run_id,
                tenant_id=tid,
                connection_id=conn_id,
                connector="slack",
                source_trigger="replay",
                sync_mode="replay",
                replay_mode=True,
                replay_job_id=replay_job_id,
                replay_version=1,
                status="RUNNING",
                started_at=datetime.now(tz=UTC),
            ),
        ]
    )
    db_session.flush()

    env = core_envelope_fields(
        connector="slack",
        connection_id=conn_id,
        source_object_type="slack.message",
        source_object_id="msg-42",
    )
    live_ok = _append_raw(
        db_session,
        ctx=IngestionSyncContext.live_incremental(),
        tenant_id=tid,
        connection_id=conn_id,
        connector="slack",
        run_id=live_run_id,
        source_trigger="live",
        resource_type="slack.message",
        external_id="msg-42",
        api_endpoint="internal://test/live",
        query_params={},
        payload_body={**env, "updated_at": "2026-01-01T00:00:10+00:00", "text": "before"},
        http_status=200,
        idempotency_key="live-1",
    )
    replay_ok = _append_raw(
        db_session,
        ctx=IngestionSyncContext.replay(replay_job_id=replay_job_id),
        tenant_id=tid,
        connection_id=conn_id,
        connector="slack",
        run_id=replay_run_id,
        source_trigger="replay",
        resource_type="slack.message",
        external_id="msg-42",
        api_endpoint="internal://test/replay",
        query_params={},
        payload_body={**env, "updated_at": "2026-01-01T00:00:10+00:00", "text": "after"},
        http_status=200,
        idempotency_key="replay-1",
    )
    assert live_ok is True
    assert replay_ok is True

    rep = verify_phase02_step4_replay_equivalence(db_session, tid)
    assert rep["passed"] is True
    assert rep["summary"]["highest_divergence"]["class"] == "D1"
