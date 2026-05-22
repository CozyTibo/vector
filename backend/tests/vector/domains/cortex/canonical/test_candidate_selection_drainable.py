"""Deferral-aware drainable candidate selection (Fix 2)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy.orm import Session

from vector.domains.cortex.canonical.forward_progress.candidate_selection import (
    list_forward_progress_candidate_ids,
    untreated_routable_drainable_exists_v1,
)
from vector.domains.cortex.canonical.forward_progress.constants import (
    DEFERRAL_QUEUE_TOPOLOGY_ORPHAN,
    DEFERRAL_REASON_MISSING_DEPLOYMENT,
)
from vector.domains.cortex.canonical.transform_runtime import materialize_raw_record
from vector.infrastructure.db.models.cortex_canonical_materialization_deferral import (
    CortexCanonicalMaterializationDeferral,
)
from vector.infrastructure.db.models.ingestion_run import IngestionRun
from vector.infrastructure.db.models.membership import TenantMembership
from vector.infrastructure.db.models.raw_ingestion_record import RawIngestionRecord
from vector.infrastructure.db.models.tenant import Tenant
from vector.infrastructure.db.models.tenant_connection import TenantConnection
from vector.infrastructure.db.models.user import User

_STUB_BUNDLE = "bundle.phase03.step03.logical_keys.v1"


@pytest.mark.integration
def test_drainable_exists_false_when_only_permanent_deferral_blocks(
    db_session: Session,
) -> None:
    user = User(email=f"drain-{uuid.uuid4().hex[:8]}@example.com", full_name="Drain")
    tenant = Tenant(
        company_name="Drain Co",
        primary_email=user.email,
        email_domain="example.com",
        slug=f"drain-{uuid.uuid4().hex[:10]}",
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

    parent = RawIngestionRecord(
        tenant_id=tenant.id,
        connection_id=conn.id,
        connector="github",
        resource_type="github.deployment",
        external_id="dep-p",
        api_endpoint="https://github.com/test",
        query_params={},
        payload_body={"deployment": {"id": 88}},
        payload_hash="hash-p",
        http_status=200,
        fetched_at=datetime.now(UTC),
        run_id=run.id,
        source_trigger="manual_admin",
        idempotency_key="idem-p",
        source_identity_key="github:deployment:p",
        source_revision_key="rev-p",
    )
    child = RawIngestionRecord(
        tenant_id=tenant.id,
        connection_id=conn.id,
        connector="github",
        resource_type="github.deployment_status",
        external_id="dep-c",
        api_endpoint="https://github.com/test",
        query_params={},
        payload_body={"deployment_id": 88, "state": "ok"},
        payload_hash="hash-c",
        http_status=200,
        fetched_at=datetime.now(UTC),
        run_id=run.id,
        source_trigger="manual_admin",
        idempotency_key="idem-c",
        source_identity_key="github:deployment_status:c",
        source_revision_key="rev-c",
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
            missing_parent_ref="github.deployment:88",
            pass_key=None,
            retry_ready_at=now,
            deferred_at=now,
            detail_json={"permanent_orphan": True},
        )
    )
    db_session.flush()

    assert untreated_routable_drainable_exists_v1(
        db_session, tenant_id=tenant.id, bundle_id=_STUB_BUNDLE
    ) is False
    ids, more, _ = list_forward_progress_candidate_ids(
        db_session,
        tenant_id=tenant.id,
        bundle_id=_STUB_BUNDLE,
        connector=None,
        resource_type=None,
        pass_index=0,
        fetch_limit=50,
    )
    assert ids == []
    assert more is False
