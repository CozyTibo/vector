"""Substrate pipeline orchestration — phase constants and durable walk binding."""

from __future__ import annotations

import uuid
from unittest.mock import MagicMock

import pytest

from vector.domains.cortex.reasoning.runtime.octs_binding_projection import (
    resolve_octs_walk_payload_v1,
)
from vector.domains.cortex.substrate_pipeline.constants import (
    PHASE_02_CANONICAL,
    PHASE_07_RETRIEVAL,
    SUBSTRATE_PIPELINE_PHASE_ORDER,
)
from vector.domains.cortex.traversal.runtime.durable_walk_store import OctsWalkApiDurableStore
from vector.domains.cortex.traversal.walk_api_contract import build_stub_completed_walk_payload_v1


def test_substrate_pipeline_phase_order_includes_retrieval() -> None:
    assert SUBSTRATE_PIPELINE_PHASE_ORDER[0] == PHASE_02_CANONICAL
    assert SUBSTRATE_PIPELINE_PHASE_ORDER[-1] == PHASE_07_RETRIEVAL
    assert len(SUBSTRATE_PIPELINE_PHASE_ORDER) == 6


@pytest.mark.integration
def test_resolve_octs_walk_payload_uses_durable_store_with_session(db_session) -> None:
    from vector.infrastructure.db.models.tenant import Tenant

    slug = f"pw-{uuid.uuid4().hex[:8]}"
    tenant = Tenant(
        company_name="Pipeline Walk Tenant",
        primary_email=f"{slug}@example.com",
        email_domain="example.com",
        slug=slug,
        status="active",
        workspace_access_enabled=True,
    )
    db_session.add(tenant)
    db_session.flush()
    walk_id = uuid.uuid4()
    body = {
        "temporal_anchor": {
            "tenant_id": str(tenant.id),
            "export_id": str(uuid.uuid4()),
            "export_sequence": 0,
            "projection_content_hash": "sha256:" + "a" * 64,
            "snapshot_unix_ns": {"unix_ns": 1},
            "graph_as_of_unix_ns": {"unix_ns": 1},
        },
        "walk_policy": {
            "max_hops": 4,
            "max_frontier": 64,
            "max_edges_visited": 500,
            "max_wall_ms": 100,
            "hop_class_allowlist": ["org.handle_links_canonical"],
            "tie_break": ["fingerprint", "org_link_id"],
            "respect_validity": True,
            "policy_version": 1,
        },
        "start_node_ids": [str(uuid.uuid4())],
        "walk_execution_strategy": "ONLINE_OBSERVED",
    }
    payload = build_stub_completed_walk_payload_v1(body, tenant_id=tenant.id)
    OctsWalkApiDurableStore(db_session).insert_completed_sync(
        tenant_id=tenant.id,
        walk_id=walk_id,
        request_body=body,
        walk_payload=payload,
        idempotency_key=None,
    )
    db_session.flush()
    resolved = resolve_octs_walk_payload_v1(
        tenant.id,
        octs_walk_id=str(walk_id),
        session=db_session,
    )
    assert resolved is not None
    assert resolved.get("walk_result")


def test_chain_after_phase_skips_tcre_to_retrieval_directly() -> None:
    from vector.domains.cortex.substrate_pipeline.constants import PHASE_06_TCRE
    from vector.domains.cortex.substrate_pipeline.orchestrator import chain_after_phase_v1

    mock_enqueue = MagicMock(return_value={"phase_id": PHASE_07_RETRIEVAL})
    import vector.domains.cortex.substrate_pipeline.orchestrator as orch

    original = orch.enqueue_next_pipeline_phase_v1
    orch.enqueue_next_pipeline_phase_v1 = mock_enqueue
    try:
        out = chain_after_phase_v1(
            tenant_id=uuid.uuid4(),
            pipeline_run_id=uuid.uuid4(),
            completed_phase_id=PHASE_06_TCRE,
        )
        assert out is None
        mock_enqueue.assert_not_called()
    finally:
        orch.enqueue_next_pipeline_phase_v1 = original
