"""Phase 02 Step 2 — persistence + provenance runtime model."""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from vector.domains.cortex.ingestion.raw_memory_persistence import (
    verify_phase02_step2_persistence_provenance,
)
from vector.domains.cortex.ingestion.sync_context import IngestionSyncContext
from vector.domains.cortex.ingestion.sync_executor import execute_connector_sync
from vector.infrastructure.db.models.raw_memory_lineage_index import RawMemoryLineageIndex
from vector.infrastructure.db.models.tenant_connection import TenantConnection
from vector.settings import get_settings

pytestmark = pytest.mark.integration


def _tenant_with_slack(db_session: Session) -> tuple[uuid.UUID, uuid.UUID]:
    from vector.infrastructure.db.models.membership import TenantMembership
    from vector.infrastructure.db.models.tenant import Tenant
    from vector.infrastructure.db.models.user import User

    user = User(email=f"s2-{uuid.uuid4().hex[:8]}@example.com", full_name="Step2 User")
    tenant = Tenant(
        company_name="Step2Co",
        primary_email=user.email,
        email_domain="example.com",
        slug=f"s2-{uuid.uuid4().hex[:10]}",
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


def test_step2_live_sync_creates_lineage_index_row(
    monkeypatch: pytest.MonkeyPatch,
    db_session: Session,
) -> None:
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
    assert out["records_written"] >= 1

    row = db_session.scalar(
        select(RawMemoryLineageIndex).where(
            RawMemoryLineageIndex.tenant_id == tid,
            RawMemoryLineageIndex.connector == "slack",
        )
    )
    assert row is not None
    assert row.first_observed_at <= row.latest_observed_at
    assert row.provenance_chain_id.startswith(f"{tid}:{row.connection_id}:slack:")
    assert row.latest_run_id == uuid.UUID(out["run_id"])
    assert row.latest_replay_job_id is None

    rep = verify_phase02_step2_persistence_provenance(db_session, tid)
    assert rep["passed"] is True


def test_step2_replay_sync_updates_lineage_replay_context(
    monkeypatch: pytest.MonkeyPatch,
    db_session: Session,
) -> None:
    monkeypatch.setenv("SECRET_KEY", "unit-test-secret-key-min-32-characters-long!")
    get_settings.cache_clear()
    settings = get_settings()
    tid, _uid = _tenant_with_slack(db_session)
    replay_job_id = uuid.uuid4()

    execute_connector_sync(
        db_session,
        settings,
        tenant_id=tid,
        connector_id="slack",
        source_trigger="live",
    )
    replay_out = execute_connector_sync(
        db_session,
        settings,
        tenant_id=tid,
        connector_id="slack",
        source_trigger="replay",
        ingestion_sync_context=IngestionSyncContext.replay(replay_job_id=replay_job_id, replay_version=2),
    )
    assert replay_out["status"] == "completed"

    row = db_session.scalar(
        select(RawMemoryLineageIndex).where(
            RawMemoryLineageIndex.tenant_id == tid,
            RawMemoryLineageIndex.connector == "slack",
        )
    )
    assert row is not None
    assert row.latest_replay_job_id == replay_job_id
    assert row.latest_replay_version == 2

    rep = verify_phase02_step2_persistence_provenance(db_session, tid)
    assert rep["passed"] is True
