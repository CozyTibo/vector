"""Traversal completeness — idle vs never-run semantics."""

from __future__ import annotations

import uuid
from unittest.mock import MagicMock

import pytest
from sqlalchemy.orm import Session

from vector.domains.cortex.completeness.traversal_completeness_projection import (
    project_traversal_completeness_v1,
)
from vector.domains.cortex.traversal.walk_api_contract import WalkApiRecordV1


def test_zero_walks_zero_graph_entities_is_healthy_idle(db_session: Session, monkeypatch: pytest.MonkeyPatch) -> None:
    tid = uuid.uuid4()
    monkeypatch.setattr(
        "vector.domains.cortex.completeness.traversal_completeness_projection.build_octs_traversal_control_plane_v1",
        lambda *a, **k: {"abort_classes": {}},
    )
    store = MagicMock()
    store.list_walk_records_for_tenant_v1.return_value = []
    monkeypatch.setattr(
        "vector.domains.cortex.completeness.traversal_completeness_projection.resolve_octs_walk_store_v1",
        lambda _s: store,
    )
    monkeypatch.setattr(
        "vector.domains.cortex.completeness.traversal_completeness_projection._count_graph_entities_v1",
        lambda *a, **k: 0,
    )

    stage = project_traversal_completeness_v1(db_session, tenant_id=tid)
    assert stage["substrate_state"] == "healthy"
    assert stage["total_objects"] == 0
    assert stage.get("intentionally_excluded_count", 0) == 0
    assert "traversal_never_executed" not in stage["omission_classes"]


def test_zero_walks_with_graph_entities_is_degraded_pending(db_session: Session, monkeypatch: pytest.MonkeyPatch) -> None:
    tid = uuid.uuid4()
    monkeypatch.setattr(
        "vector.domains.cortex.completeness.traversal_completeness_projection.build_octs_traversal_control_plane_v1",
        lambda *a, **k: {"abort_classes": {}},
    )
    store = MagicMock()
    store.list_walk_records_for_tenant_v1.return_value = []
    monkeypatch.setattr(
        "vector.domains.cortex.completeness.traversal_completeness_projection.resolve_octs_walk_store_v1",
        lambda _s: store,
    )
    monkeypatch.setattr(
        "vector.domains.cortex.completeness.traversal_completeness_projection._count_graph_entities_v1",
        lambda *a, **k: 977,
    )

    stage = project_traversal_completeness_v1(db_session, tenant_id=tid)
    assert stage["substrate_state"] == "degraded"
    assert stage["total_objects"] == 977
    assert stage["metrics"]["walk_record_count"] == 0
    assert stage["intentionally_excluded_count"] == 977
    assert stage["omission_classes"].get("traversal_never_executed") == 1
    assert stage["metrics"]["graph_entity_count"] == 977


def test_completed_walks_remain_healthy(db_session: Session, monkeypatch: pytest.MonkeyPatch) -> None:
    tid = uuid.uuid4()
    wid = uuid.uuid4()
    monkeypatch.setattr(
        "vector.domains.cortex.completeness.traversal_completeness_projection.build_octs_traversal_control_plane_v1",
        lambda *a, **k: {"abort_classes": {}},
    )
    rec = WalkApiRecordV1(
        walk_id=wid,
        tenant_id=tid,
        status="completed",
        request_body={},
        walk_payload={
            "walk_result": {
                "walk_result_hash": "sha256:" + "aa" * 32,
                "hash_body": {"termination_reason": "completed", "hop_receipts": [{}]},
            }
        },
        job_id=None,
        idempotency_key=None,
    )
    store = MagicMock()
    store.list_walk_records_for_tenant_v1.return_value = [rec]
    monkeypatch.setattr(
        "vector.domains.cortex.completeness.traversal_completeness_projection.resolve_octs_walk_store_v1",
        lambda _s: store,
    )
    monkeypatch.setattr(
        "vector.domains.cortex.completeness.traversal_completeness_projection._count_graph_entities_v1",
        lambda *a, **k: 10,
    )

    stage = project_traversal_completeness_v1(db_session, tenant_id=tid)
    assert stage["substrate_state"] == "healthy"
    assert stage["total_objects"] == 1
    assert stage["processed_count"] == 1
