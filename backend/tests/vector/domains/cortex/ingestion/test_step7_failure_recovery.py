"""Phase 02 Step 7 — failure representation and recovery validation."""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from vector.domains.cortex.ingestion.raw_memory_failure_recovery import (
    run_raw_memory_recovery_validation,
    verify_phase02_step7_failure_recovery,
)
from vector.domains.cortex.ingestion.sync_executor import execute_connector_sync
from vector.infrastructure.db.models.raw_ingestion_record import RawIngestionRecord
from vector.infrastructure.db.models.raw_memory_archive_catalog import RawMemoryArchiveCatalog
from vector.infrastructure.db.models.raw_memory_failure_case import RawMemoryFailureCase
from vector.infrastructure.db.models.raw_memory_lineage_index import RawMemoryLineageIndex
from vector.infrastructure.db.models.raw_memory_revision_index import RawMemoryRevisionIndex
from vector.infrastructure.db.models.tenant_connection import TenantConnection
from vector.settings import get_settings

pytestmark = pytest.mark.integration


def _tenant_with_slack(db_session: Session) -> tuple[uuid.UUID, uuid.UUID]:
    from vector.infrastructure.db.models.membership import TenantMembership
    from vector.infrastructure.db.models.tenant import Tenant
    from vector.infrastructure.db.models.user import User

    user = User(email=f"s7-{uuid.uuid4().hex[:8]}@example.com", full_name="Step7 User")
    tenant = Tenant(
        company_name="Step7Co",
        primary_email=user.email,
        email_domain="example.com",
        slug=f"s7-{uuid.uuid4().hex[:10]}",
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


def test_step7_verification_passes_on_clean_scope(
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
    rep = verify_phase02_step7_failure_recovery(db_session, tid)
    assert rep["passed"] is True
    assert rep["summary"]["active_failure_count"] == 0


def test_step7_detects_payload_corruption_case(
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
        select(RawIngestionRecord).where(RawIngestionRecord.tenant_id == tid).limit(1)
    )
    assert row is not None
    row.payload_hash = "broken-hash"
    db_session.flush()

    rep = verify_phase02_step7_failure_recovery(db_session, tid)
    assert rep["passed"] is False
    assert rep["state"] in {"corrupted", "degraded"}
    case = db_session.scalar(
        select(RawMemoryFailureCase).where(
            RawMemoryFailureCase.tenant_id == tid,
            RawMemoryFailureCase.failure_class == "payload_mutation_corruption",
            RawMemoryFailureCase.active.is_(True),
        )
    )
    assert case is not None


def test_step7_recovery_validation_repairs_missing_derived_indexes(
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

    db_session.execute(delete(RawMemoryLineageIndex).where(RawMemoryLineageIndex.tenant_id == tid))
    db_session.execute(delete(RawMemoryRevisionIndex).where(RawMemoryRevisionIndex.tenant_id == tid))
    db_session.execute(delete(RawMemoryArchiveCatalog).where(RawMemoryArchiveCatalog.tenant_id == tid))
    db_session.flush()

    out_val = run_raw_memory_recovery_validation(db_session, tid, apply_repairs=True)
    assert out_val["status"] == "validated"
    assert db_session.scalar(
        select(RawMemoryLineageIndex).where(RawMemoryLineageIndex.tenant_id == tid).limit(1)
    )
    assert db_session.scalar(
        select(RawMemoryRevisionIndex).where(RawMemoryRevisionIndex.tenant_id == tid).limit(1)
    )
    assert db_session.scalar(
        select(RawMemoryArchiveCatalog).where(RawMemoryArchiveCatalog.tenant_id == tid).limit(1)
    )
