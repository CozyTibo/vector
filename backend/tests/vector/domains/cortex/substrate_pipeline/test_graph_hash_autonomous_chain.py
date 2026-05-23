"""Phase B5 — graph-hash autonomous chain unit + integration tests."""

from __future__ import annotations

import uuid
from unittest.mock import MagicMock

import pytest
from sqlalchemy import select

from vector.domains.cortex.substrate_pipeline.graph_hash_autonomous_chain import (
    CHAIN_LINK_GRAPH_HASH_V1,
    CHAIN_LINK_RETRIEVAL_V1,
    CHAIN_LINK_TCRE_V1,
    CHAIN_LINK_WALKS_V1,
    run_graph_hash_autonomous_chain_v1,
)


def test_chain_runner_wires_phases_in_order(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[str] = []
    tenant_id = uuid.uuid4()
    prid = uuid.uuid4()

    def _p4(*_a, **_k):
        calls.append("04")
        return {
            "graph_projection_stable_hash_sha256": "hash-test",
            "event_trigger_graph_hash": {
                "triggered": True,
                "hash_changed": True,
                "walks_scheduled": True,
                "walk_schedule": {"scheduled": True},
            },
        }

    def _p5(*_a, **_k):
        calls.append("05")
        return {
            "walks_persisted": 2,
            "walk_ids": ["w1", "w2"],
            "primary_octs_walk_id": "w1",
            "scheduling_eligible": True,
        }

    def _p7(*_a, **_k):
        calls.append("07")
        return {
            "ok": True,
            "build_state": "PUBLISHED",
            "published_index_epoch": "epoch-test",
            "entries_materialized": 3,
        }

    monkeypatch.setattr(
        "vector.domains.cortex.substrate_pipeline.graph_hash_autonomous_chain."
        "is_graph_hash_autonomous_chain_enabled_v1",
        lambda: True,
    )
    monkeypatch.setattr(
        "vector.domains.cortex.substrate_pipeline.graph_hash_autonomous_chain."
        "create_pipeline_run_v1",
        lambda *_a, **_k: MagicMock(id=prid),
    )
    monkeypatch.setattr(
        "vector.domains.cortex.substrate_pipeline.graph_hash_autonomous_chain."
        "run_phase_04_graph_v1",
        _p4,
    )
    monkeypatch.setattr(
        "vector.domains.cortex.substrate_pipeline.graph_hash_autonomous_chain."
        "run_phase_05_traversal_v1",
        _p5,
    )
    monkeypatch.setattr(
        "vector.domains.cortex.substrate_pipeline.graph_hash_autonomous_chain."
        "_execute_phase06_tcre_sync_v1",
        lambda *_a, **_k: (calls.append("06"), {"ok": True, "job_id": "j1", "status": "completed"})[1],
    )
    monkeypatch.setattr(
        "vector.domains.cortex.substrate_pipeline.graph_hash_autonomous_chain."
        "run_phase_07_retrieval_v1",
        _p7,
    )

    out = run_graph_hash_autonomous_chain_v1(
        MagicMock(),
        tenant_id=tenant_id,
        pipeline_run_id=prid,
        run_upstream_phases=False,
    )
    assert calls == ["04", "05", "06", "07"]
    assert out["chain_ok"] is True
    assert out["chain_links"][CHAIN_LINK_GRAPH_HASH_V1]["ok"] is True
    assert out["chain_links"][CHAIN_LINK_WALKS_V1]["ok"] is True
    assert out["chain_links"][CHAIN_LINK_TCRE_V1]["ok"] is True
    assert out["chain_links"][CHAIN_LINK_RETRIEVAL_V1]["ok"] is True


@pytest.mark.integration
def test_graph_hash_autonomous_chain_on_tenant_with_graph(db_session) -> None:
    """Full in-process chain on tenants with org graph projection (no unlock scripts)."""
    from vector.domains.cortex.identity.projection_export import (
        build_org_graph_projection_export_document,
    )
    from vector.domains.cortex.substrate_pipeline.graph_hash_autonomous_chain import (
        seed_stale_graph_hash_for_chain_v1,
    )
    from vector.infrastructure.db.models.tenant import Tenant

    tenant = db_session.scalar(select(Tenant).limit(1))
    if tenant is None:
        pytest.skip("no tenant row")

    doc = build_org_graph_projection_export_document(db_session, tenant_id=tenant.id)
    if not doc.get("stable_hash_sha256"):
        pytest.skip("tenant lacks graph projection")

    seed_stale_graph_hash_for_chain_v1(db_session, tenant_id=tenant.id)
    out = run_graph_hash_autonomous_chain_v1(
        db_session,
        tenant_id=tenant.id,
        run_upstream_phases=False,
        force_graph_hash_schedule=True,
    )
    assert out["chain_links"][CHAIN_LINK_WALKS_V1]["ok"] is True
    assert out["chain_links"][CHAIN_LINK_RETRIEVAL_V1]["ok"] is True
