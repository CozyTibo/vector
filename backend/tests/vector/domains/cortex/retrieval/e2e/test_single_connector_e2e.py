"""E2E: substrate pipeline → published index → lawful query (no direct row injection)."""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from vector.domains.cortex.retrieval.testing import (
    assert_lawful_query_replay_stable_v1,
    assert_retrieval_substrate_ready_v1,
    run_substrate_pipeline_sync_through_retrieval_v1,
)
from vector.domains.cortex.canonical.transform_runtime import resolve_default_bundle_id_for_stub_transform
from vector.infrastructure.db.models.cortex_retrieval_index_entry import CortexRetrievalIndexEntry


@pytest.mark.integration
def test_single_connector_pipeline_to_lawful_query(
    db_session: Session,
    e2e_tenant_id: uuid.UUID,
) -> None:
    bundle_id = resolve_default_bundle_id_for_stub_transform(db_session, e2e_tenant_id)
    if not bundle_id:
        pytest.skip("no_transformable_bundle_for_e2e_tenant")

    pipeline = run_substrate_pipeline_sync_through_retrieval_v1(
        db_session,
        tenant_id=e2e_tenant_id,
        bundle_id=bundle_id,
        batch_limit=50,
    )
    db_session.commit()
    if pipeline.get("skipped"):
        pytest.skip(str(pipeline.get("reason")))

    ready = assert_retrieval_substrate_ready_v1(db_session, tenant_id=e2e_tenant_id)
    assert ready["ready"], ready.get("errors")

    row = db_session.scalar(
        select(CortexRetrievalIndexEntry)
        .where(CortexRetrievalIndexEntry.tenant_id == e2e_tenant_id)
        .limit(1)
    )
    if row is None:
        pytest.skip("no_index_rows_after_pipeline")

    epoch = pipeline.get("index_epoch") or row.index_epoch
    envelope = {
        "schema_version": 1,
        "tenant_id": str(e2e_tenant_id),
        "workload_class": "causal_chain",
        "intent": "inspect",
        "execution_partition": "authoritative",
        "retrieval_lookup_id": row.retrieval_lookup_id,
        "replay_pins": {"index_epoch": epoch},
    }
    replay_check = assert_lawful_query_replay_stable_v1(
        db_session, tenant_id=e2e_tenant_id, envelope=envelope
    )
    assert replay_check["passed"]
