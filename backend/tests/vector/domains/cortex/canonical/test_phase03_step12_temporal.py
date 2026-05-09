"""Phase 03 Step 12 — temporal ordering keys, supersession ledger, admin temporal routes."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from starlette.testclient import TestClient

from vector.domains.cortex.canonical.ontology import (
    ONTOLOGY_SCHEMA_VERSION,
    build_phase03_step01_ontology_public_document,
)
from vector.domains.cortex.canonical.temporal_runtime import (
    TEMPORAL_RUNTIME_SCHEMA_VERSION,
    build_temporal_ordering_key,
    occurred_at_from_raw,
)
from vector.domains.cortex.canonical.transform_runtime import materialize_raw_record
from vector.infrastructure.db.models.cortex_canonical_temporal_supersession import (
    CortexCanonicalTemporalSupersession,
)
from vector.infrastructure.db.models.ingestion_run import IngestionRun
from vector.infrastructure.db.models.membership import TenantMembership
from vector.infrastructure.db.models.raw_ingestion_record import RawIngestionRecord
from vector.infrastructure.db.models.tenant import Tenant
from vector.infrastructure.db.models.tenant_connection import TenantConnection
from vector.infrastructure.db.models.user import User

_STUB_BUNDLE_ID = "bundle.phase03.step03.logical_keys.v1"


def test_temporal_runtime_schema_version() -> None:
    assert TEMPORAL_RUNTIME_SCHEMA_VERSION >= 1


def test_build_temporal_ordering_key_orders_by_occurred_then_sequence() -> None:
    t0 = datetime(2024, 1, 2, tzinfo=UTC)
    t1 = datetime(2024, 1, 3, tzinfo=UTC)
    k_early = build_temporal_ordering_key(
        occurred_at=t0, replay_sequence=100, source_revision_key="a", raw_record_id=99
    )
    k_late = build_temporal_ordering_key(
        occurred_at=t1, replay_sequence=1, source_revision_key="a", raw_record_id=1
    )
    assert k_early < k_late


def test_ontology_includes_temporal_pointer_section() -> None:
    doc = build_phase03_step01_ontology_public_document()
    assert doc["ontology_schema_version"] == 20
    assert ONTOLOGY_SCHEMA_VERSION == 20
    assert doc["implementation_step"] == 18
    assert doc["completed_implementation_steps"] == [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18]
    assert doc["temporal_supersessions_list_route"]
    assert doc["temporal_rebuild_preview_route"]
    assert doc["temporal_ordering_precedence"]
    assert doc["transform_persists_temporal_ordering"] is True


@pytest.mark.integration
def test_materialize_twice_writes_supersession_and_temporal_columns(db_session: Session) -> None:
    user = User(email=f"p312-{uuid.uuid4().hex[:8]}@example.com", full_name="P312 User")
    tenant = Tenant(
        company_name="P312 Co",
        primary_email=user.email,
        email_domain="example.com",
        slug=f"p312-{uuid.uuid4().hex[:10]}",
        status="active",
        workspace_access_enabled=True,
    )
    db_session.add_all([user, tenant])
    db_session.flush()
    db_session.add(TenantMembership(tenant_id=tenant.id, user_id=user.id, role="owner"))
    conn = TenantConnection(
        tenant_id=tenant.id,
        provider="slack",
        status="active",
        connected_by_user_id=user.id,
    )
    db_session.add(conn)
    db_session.flush()
    run = IngestionRun(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        connection_id=conn.id,
        connector="slack",
        source_trigger="manual_admin",
        sync_mode="incremental",
        replay_mode=False,
        replay_version=1,
        status="COMPLETED",
        started_at=datetime.now(UTC),
    )
    db_session.add(run)
    db_session.flush()
    raw = RawIngestionRecord(
        tenant_id=tenant.id,
        connection_id=conn.id,
        connector="slack",
        resource_type="slack.message",
        external_id="msg-1",
        api_endpoint="https://slack.com/api/conversations.history",
        query_params={},
        payload_body={"text": "hello"},
        payload_hash="hash-p312",
        http_status=200,
        fetched_at=datetime.now(UTC),
        run_id=run.id,
        source_trigger="manual_admin",
        idempotency_key="idem-p312-1",
        source_identity_key="slack:slack.message:msg-1",
        source_revision_key="rev-a",
    )
    db_session.add(raw)
    db_session.flush()

    mat1 = materialize_raw_record(
        db_session,
        tenant_id=tenant.id,
        bundle_id=_STUB_BUNDLE_ID,
        raw_record_id=int(raw.id),
        commit=False,
    )
    assert mat1.temporal_ordering_key
    assert mat1.occurred_at is not None

    raw.payload_body = {"text": "hello", "edited_at": "2024-06-01T12:00:00+00:00"}
    db_session.flush()

    mat2 = materialize_raw_record(
        db_session,
        tenant_id=tenant.id,
        bundle_id=_STUB_BUNDLE_ID,
        raw_record_id=int(raw.id),
        commit=False,
    )
    assert mat2.id != mat1.id
    n_ss = db_session.scalar(
        select(func.count()).select_from(CortexCanonicalTemporalSupersession).where(
            CortexCanonicalTemporalSupersession.tenant_id == tenant.id,
            CortexCanonicalTemporalSupersession.bundle_id == _STUB_BUNDLE_ID,
        )
    )
    assert int(n_ss or 0) >= 1

    occ2 = occurred_at_from_raw(raw)
    key2 = build_temporal_ordering_key(
        occurred_at=occ2,
        replay_sequence=int(raw.replay_sequence),
        source_revision_key=str(raw.source_revision_key),
        raw_record_id=int(raw.id),
    )
    assert mat2.temporal_ordering_key == key2


@pytest.mark.integration
def test_admin_temporal_routes(
    monkeypatch: pytest.MonkeyPatch,
    client: TestClient,
    db_session: Session,
) -> None:
    monkeypatch.setenv("ADMIN_PASSWORD", "integration-admin-password")
    user = User(email=f"p312a-{uuid.uuid4().hex[:8]}@example.com", full_name="P312a User")
    tenant = Tenant(
        company_name="P312a Co",
        primary_email=user.email,
        email_domain="example.com",
        slug=f"p312a-{uuid.uuid4().hex[:10]}",
        status="active",
        workspace_access_enabled=True,
    )
    db_session.add_all([user, tenant])
    db_session.flush()
    db_session.add(TenantMembership(tenant_id=tenant.id, user_id=user.id, role="owner"))
    conn = TenantConnection(
        tenant_id=tenant.id,
        provider="slack",
        status="active",
        connected_by_user_id=user.id,
    )
    db_session.add(conn)
    db_session.flush()
    run = IngestionRun(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        connection_id=conn.id,
        connector="slack",
        source_trigger="manual_admin",
        sync_mode="incremental",
        replay_mode=False,
        replay_version=1,
        status="COMPLETED",
        started_at=datetime.now(UTC),
    )
    db_session.add(run)
    db_session.flush()
    base = datetime.now(UTC)
    r1 = RawIngestionRecord(
        tenant_id=tenant.id,
        connection_id=conn.id,
        connector="slack",
        resource_type="slack.message",
        external_id="m-a",
        api_endpoint="https://slack.com/api/test",
        query_params={},
        payload_body={"ts": (base - timedelta(days=1)).isoformat()},
        payload_hash="h-a",
        http_status=200,
        fetched_at=base,
        run_id=run.id,
        source_trigger="manual_admin",
        idempotency_key="ia",
        source_identity_key="slack:slack.message:m-a",
        source_revision_key="r1",
    )
    r2 = RawIngestionRecord(
        tenant_id=tenant.id,
        connection_id=conn.id,
        connector="slack",
        resource_type="slack.message",
        external_id="m-b",
        api_endpoint="https://slack.com/api/test",
        query_params={},
        payload_body={"ts": base.isoformat()},
        payload_hash="h-b",
        http_status=200,
        fetched_at=base,
        run_id=run.id,
        source_trigger="manual_admin",
        idempotency_key="ib",
        source_identity_key="slack:slack.message:m-b",
        source_revision_key="r2",
    )
    db_session.add_all([r1, r2])
    db_session.flush()

    tid = tenant.id
    pr = client.post(
        f"/admin/tenants/{tid}/cortex/canonical/temporal/rebuild-preview",
        auth=("admin", "integration-admin-password"),
        json={"raw_record_ids": [int(r2.id), int(r1.id)]},
    )
    assert pr.status_code == 200
    body = pr.json()
    assert body["temporal_runtime_schema_version"] == TEMPORAL_RUNTIME_SCHEMA_VERSION
    ordered_ids = [row["raw_record_id"] for row in body["ordered"]]
    assert ordered_ids == [int(r1.id), int(r2.id)]

    materialize_raw_record(
        db_session,
        tenant_id=tid,
        bundle_id=_STUB_BUNDLE_ID,
        raw_record_id=int(r1.id),
        commit=False,
    )
    materialize_raw_record(
        db_session,
        tenant_id=tid,
        bundle_id=_STUB_BUNDLE_ID,
        raw_record_id=int(r1.id),
        commit=False,
    )
    db_session.flush()

    gs = client.get(
        f"/admin/tenants/{tid}/cortex/canonical/temporal/supersessions?limit=20",
        auth=("admin", "integration-admin-password"),
    )
    assert gs.status_code == 200
    gbody = gs.json()
    assert gbody["temporal_runtime_schema_version"] == TEMPORAL_RUNTIME_SCHEMA_VERSION
    assert len(gbody["items"]) >= 1
