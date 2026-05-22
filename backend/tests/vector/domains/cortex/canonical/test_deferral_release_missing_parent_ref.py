"""Fix 1 — release topology deferrals when missing_parent_ref parent is materialized."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from types import SimpleNamespace

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from vector.domains.cortex.canonical.forward_progress.constants import (
    DEFERRAL_QUEUE_TOPOLOGY_ORPHAN,
    DEFERRAL_REASON_MISSING_DEPLOYMENT,
)
from vector.domains.cortex.canonical.forward_progress.deferral_store import (
    raw_record_ids_releasable_for_missing_parent_refs,
    release_deferrals_when_missing_parent_ref_materialized_v1,
)
from vector.domains.cortex.canonical.replay_topology import build_node_key_index
from vector.domains.cortex.canonical.transform_runtime import materialize_raw_record
from vector.infrastructure.db.models.cortex_canonical_materialization_deferral import (
    CortexCanonicalMaterializationDeferral,
)
from vector.infrastructure.db.models.ingestion_run import IngestionRun
from vector.infrastructure.db.models.raw_ingestion_record import RawIngestionRecord
from vector.infrastructure.db.models.tenant import Tenant
from vector.infrastructure.db.models.tenant_connection import TenantConnection
from vector.infrastructure.db.models.membership import TenantMembership
from vector.infrastructure.db.models.user import User

_STUB_BUNDLE = "bundle.phase03.step03.logical_keys.v1"


def _raw(
    *,
    tenant_id: uuid.UUID,
    connection_id: uuid.UUID,
    run_id: uuid.UUID,
    suffix: str,
    resource_type: str,
    payload_body: dict,
    external_id: str = "",
) -> RawIngestionRecord:
    return RawIngestionRecord(
        tenant_id=tenant_id,
        connection_id=connection_id,
        connector="github",
        resource_type=resource_type,
        external_id=external_id or f"ext-{suffix}",
        api_endpoint="https://github.com/test",
        query_params={},
        payload_body=payload_body,
        payload_hash=f"hash-{suffix}",
        http_status=200,
        fetched_at=datetime.now(UTC),
        run_id=run_id,
        source_trigger="manual_admin",
        idempotency_key=f"idem-{suffix}",
        source_identity_key=f"github:{resource_type}:{suffix}",
        source_revision_key=f"rev-{suffix}",
    )


def test_build_node_key_index_matches_topology_dependency_ref() -> None:
    rows = [
        SimpleNamespace(
            id=1,
            connector="github",
            resource_type="github.deployment",
            payload_body={"deployment": {"id": 999}},
            external_id="",
        ),
        SimpleNamespace(
            id=2,
            connector="github",
            resource_type="github.deployment_status",
            payload_body={"deployment_id": 999, "state": "success"},
            external_id="",
        ),
    ]
    index = build_node_key_index(rows)  # type: ignore[arg-type]
    assert index["github.deployment:999"] == 1


def test_raw_record_ids_releasable_for_missing_parent_refs_pure() -> None:
    releasable = raw_record_ids_releasable_for_missing_parent_refs(
        deferrals=[(10, "github.deployment:999"), (11, "github.deployment:404")],
        node_key_index={"github.deployment:999": 1},
        materialized_raw_record_ids={1},
    )
    assert releasable == [10]


@pytest.mark.integration
def test_release_deferrals_when_missing_parent_ref_materialized(
    db_session: Session,
) -> None:
    user = User(email=f"defrel-{uuid.uuid4().hex[:8]}@example.com", full_name="DefRel")
    tenant = Tenant(
        company_name="DefRel Co",
        primary_email=user.email,
        email_domain="example.com",
        slug=f"defrel-{uuid.uuid4().hex[:10]}",
        status="active",
        workspace_access_enabled=True,
    )
    db_session.add_all([user, tenant])
    db_session.flush()
    db_session.add(TenantMembership(tenant_id=tenant.id, user_id=user.id, role="owner"))
    conn = TenantConnection(
        tenant_id=tenant.id,
        provider="github",
        status="active",
        connected_by_user_id=user.id,
    )
    db_session.add(conn)
    db_session.flush()
    run = IngestionRun(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        connection_id=conn.id,
        connector="github",
        source_trigger="manual_admin",
        sync_mode="incremental",
        replay_mode=False,
        replay_version=1,
        status="COMPLETED",
        started_at=datetime.now(UTC),
    )
    db_session.add(run)
    db_session.flush()

    parent = _raw(
        tenant_id=tenant.id,
        connection_id=conn.id,
        run_id=run.id,
        suffix="p1",
        resource_type="github.deployment",
        payload_body={"deployment": {"id": 4242}},
    )
    child = _raw(
        tenant_id=tenant.id,
        connection_id=conn.id,
        run_id=run.id,
        suffix="c1",
        resource_type="github.deployment_status",
        payload_body={"deployment_id": 4242, "state": "success"},
    )
    db_session.add_all([parent, child])
    db_session.flush()

    materialize_raw_record(
        db_session,
        tenant_id=tenant.id,
        bundle_id=_STUB_BUNDLE,
        raw_record_id=int(parent.id),
        commit=False,
    )

    now = datetime.now(UTC)
    db_session.add(
        CortexCanonicalMaterializationDeferral(
            tenant_id=tenant.id,
            bundle_id=_STUB_BUNDLE,
            raw_record_id=int(child.id),
            connector="github",
            resource_type="github.deployment_status",
            deferral_reason=DEFERRAL_REASON_MISSING_DEPLOYMENT,
            queue=DEFERRAL_QUEUE_TOPOLOGY_ORPHAN,
            parent_raw_record_id=None,
            missing_parent_ref="github.deployment:4242",
            pass_key=None,
            retry_ready_at=now,
            deferred_at=now,
            detail_json={"orphan_class": "missing_deployment"},
        )
    )
    db_session.flush()

    released = release_deferrals_when_missing_parent_ref_materialized_v1(
        db_session,
        tenant_id=tenant.id,
        bundle_id=_STUB_BUNDLE,
    )
    assert released == 1

    remaining = db_session.scalar(
        select(func.count())
        .select_from(CortexCanonicalMaterializationDeferral)
        .where(
            CortexCanonicalMaterializationDeferral.tenant_id == tenant.id,
            CortexCanonicalMaterializationDeferral.bundle_id == _STUB_BUNDLE,
        )
    )
    assert int(remaining or 0) == 0


@pytest.mark.integration
def test_release_does_not_clear_when_parent_not_materialized(db_session: Session) -> None:
    user = User(email=f"defrel2-{uuid.uuid4().hex[:8]}@example.com", full_name="DefRel2")
    tenant = Tenant(
        company_name="DefRel2",
        primary_email=user.email,
        email_domain="example.com",
        slug=f"defrel2-{uuid.uuid4().hex[:10]}",
        status="active",
        workspace_access_enabled=True,
    )
    db_session.add_all([user, tenant])
    db_session.flush()
    db_session.add(TenantMembership(tenant_id=tenant.id, user_id=user.id, role="owner"))
    conn = TenantConnection(
        tenant_id=tenant.id,
        provider="github",
        status="active",
        connected_by_user_id=user.id,
    )
    db_session.add(conn)
    db_session.flush()
    run = IngestionRun(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        connection_id=conn.id,
        connector="github",
        source_trigger="manual_admin",
        sync_mode="incremental",
        replay_mode=False,
        replay_version=1,
        status="COMPLETED",
        started_at=datetime.now(UTC),
    )
    db_session.add(run)
    db_session.flush()

    parent = _raw(
        tenant_id=tenant.id,
        connection_id=conn.id,
        run_id=run.id,
        suffix="p2",
        resource_type="github.deployment",
        payload_body={"deployment": {"id": 77}},
    )
    child = _raw(
        tenant_id=tenant.id,
        connection_id=conn.id,
        run_id=run.id,
        suffix="c2",
        resource_type="github.deployment_status",
        payload_body={"deployment_id": 77, "state": "pending"},
    )
    db_session.add_all([parent, child])
    db_session.flush()

    now = datetime.now(UTC)
    db_session.add(
        CortexCanonicalMaterializationDeferral(
            tenant_id=tenant.id,
            bundle_id=_STUB_BUNDLE,
            raw_record_id=int(child.id),
            connector="github",
            resource_type="github.deployment_status",
            deferral_reason=DEFERRAL_REASON_MISSING_DEPLOYMENT,
            queue=DEFERRAL_QUEUE_TOPOLOGY_ORPHAN,
            parent_raw_record_id=None,
            missing_parent_ref="github.deployment:77",
            pass_key=None,
            retry_ready_at=now,
            deferred_at=now,
            detail_json={},
        )
    )
    db_session.flush()

    released = release_deferrals_when_missing_parent_ref_materialized_v1(
        db_session,
        tenant_id=tenant.id,
        bundle_id=_STUB_BUNDLE,
    )
    assert released == 0

    remaining = db_session.scalar(
        select(func.count())
        .select_from(CortexCanonicalMaterializationDeferral)
        .where(
            CortexCanonicalMaterializationDeferral.tenant_id == tenant.id,
            CortexCanonicalMaterializationDeferral.bundle_id == _STUB_BUNDLE,
        )
    )
    assert int(remaining or 0) == 1
