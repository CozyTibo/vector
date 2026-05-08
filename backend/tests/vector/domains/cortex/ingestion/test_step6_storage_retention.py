"""Phase 02 Step 6 — storage + retention runtime model."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from vector.domains.cortex.ingestion.raw_memory_storage import (
    apply_raw_memory_retention_policy,
    verify_phase02_step6_storage_retention,
)
from vector.domains.cortex.ingestion.sync_executor import execute_connector_sync
from vector.infrastructure.db.models.raw_ingestion_record import RawIngestionRecord
from vector.infrastructure.db.models.raw_memory_archive_catalog import RawMemoryArchiveCatalog
from vector.infrastructure.db.models.raw_memory_retention_event import RawMemoryRetentionEvent
from vector.infrastructure.db.models.tenant_connection import TenantConnection
from vector.settings import get_settings

pytestmark = pytest.mark.integration


def _tenant_with_slack(db_session: Session) -> tuple[uuid.UUID, uuid.UUID]:
    from vector.infrastructure.db.models.membership import TenantMembership
    from vector.infrastructure.db.models.tenant import Tenant
    from vector.infrastructure.db.models.user import User

    user = User(email=f"s6-{uuid.uuid4().hex[:8]}@example.com", full_name="Step6 User")
    tenant = Tenant(
        company_name="Step6Co",
        primary_email=user.email,
        email_domain="example.com",
        slug=f"s6-{uuid.uuid4().hex[:10]}",
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


def test_step6_catalog_rows_written_for_raw_inserts(
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
    row = db_session.scalar(
        select(RawMemoryArchiveCatalog).where(RawMemoryArchiveCatalog.tenant_id == tid)
    )
    assert row is not None
    assert row.storage_tier == "hot"
    rep = verify_phase02_step6_storage_retention(db_session, tid)
    assert rep["passed"] is True


def test_step6_retention_apply_marks_cold_and_emits_events(
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

    # Force eligibility windows.
    cat = db_session.scalar(select(RawMemoryArchiveCatalog).where(RawMemoryArchiveCatalog.tenant_id == tid))
    assert cat is not None
    db_session.execute(
        RawMemoryArchiveCatalog.__table__.update()
        .where(RawMemoryArchiveCatalog.tenant_id == tid)
        .values(storage_tier="hot", archived_at=None, archive_pointer=None)
    )
    db_session.execute(
        RawIngestionRecord.__table__.update()
        .where(RawIngestionRecord.tenant_id == tid)
        .values(fetched_at=datetime.now(tz=UTC) - timedelta(days=90))
    )
    db_session.flush()

    out_apply = apply_raw_memory_retention_policy(
        db_session,
        tenant_id=tid,
        dry_run=False,
        archive_after_days=30,
        delete_after_days=120,
        allow_delete=False,
    )
    assert out_apply["archive_candidate_count"] >= 1
    cold = db_session.scalar(
        select(RawMemoryArchiveCatalog).where(
            RawMemoryArchiveCatalog.tenant_id == tid,
            RawMemoryArchiveCatalog.storage_tier == "cold",
        )
    )
    assert cold is not None
    ev = db_session.scalar(
        select(RawMemoryRetentionEvent).where(
            RawMemoryRetentionEvent.tenant_id == tid,
            RawMemoryRetentionEvent.event_type == "archive_marked",
        )
    )
    assert ev is not None
