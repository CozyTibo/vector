"""Graph completeness projection — entity-linked accounting."""

from __future__ import annotations

import uuid
from unittest.mock import MagicMock

import pytest

from vector.domains.cortex.completeness._completeness_common import build_stage_envelope_v1
from vector.domains.cortex.completeness.graph_completeness_projection import (
    project_graph_completeness_v1,
)


def test_stage_envelope_percents_never_exceed_100() -> None:
    stage = build_stage_envelope_v1(
        stage_id="graph",
        label="Graph",
        total_objects=100,
        processed_count=0,
        degraded_count=500,
        unresolved_count=100,
        detail_route="/g",
    )
    assert stage["degraded_percent"] <= 100.0
    assert stage["unresolved_percent"] <= 100.0
    assert stage["success_percent"] <= 100.0


def test_graph_projection_uses_linked_entity_count(monkeypatch: pytest.MonkeyPatch) -> None:
    tid = uuid.uuid4()
    session = MagicMock()

    def _scalar(_stmt: object) -> int:
        return _scalar.n  # type: ignore[attr-defined]

    _scalar.n = 0  # type: ignore[attr-defined]

    def _next() -> int:
        values = [977, 0, 2000]
        v = values[_scalar.n] if _scalar.n < len(values) else 0  # type: ignore[attr-defined]
        _scalar.n += 1  # type: ignore[attr-defined]
        return v

    session.scalar.side_effect = lambda _stmt: _next()
    monkeypatch.setattr(
        "vector.domains.cortex.completeness.graph_completeness_projection._count_entities_with_authoritative_links",
        lambda *_a, **_k: 400,
    )
    out = project_graph_completeness_v1(session, tenant_id=tid)
    assert out["total_objects"] == 977
    assert out["degraded_percent"] <= 100.0
    assert out["metrics"]["linked_entity_count"] == 400
    assert out["metrics"]["orphan_node_count"] == 577
    assert out["omission_classes"].get("orphan_artifacts") == 577
    assert out["omission_classes"].get("pending_link_candidates") == 2000
