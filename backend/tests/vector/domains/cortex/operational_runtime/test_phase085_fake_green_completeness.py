"""P085-02 — Fake-green prohibition (**G-P085-ANTI-IDLE-01**)."""

from __future__ import annotations

import uuid
from unittest.mock import MagicMock

import pytest
from sqlalchemy.orm import Session

from vector.domains.cortex.completeness.graph_completeness_projection import (
    _derive_graph_substrate_state_v1,
    project_graph_completeness_v1,
)
from vector.domains.cortex.completeness.tcre_completeness_projection import (
    _derive_tcre_substrate_state_v1,
)
from vector.domains.cortex.operational_runtime.cesp_anti_idle_gate import (
    verify_gp085_anti_idle01_static,
)
from vector.domains.cortex.operational_runtime.fake_green_prohibition import (
    OPERATIONAL_IDLE_STARVATION_V1,
    apply_cesp_anti_idle_law_to_pipeline_stages_v1,
    assert_never_fake_green_healthy_v1,
    classify_synthesis_idle_v1,
    CespAntiIdleLawError,
)
from vector.domains.cortex.retrieval.retrieval_completeness_projection import (
    derive_retrieval_stage_substrate_state_v1,
)


def test_verify_gp085_anti_idle01_static_passes() -> None:
    out = verify_gp085_anti_idle01_static()
    assert out["passed"] is True
    assert out["gate_id"] == "G-P085-ANTI-IDLE-01"


def test_assert_never_fake_green_rejects_eligible_unprocessed() -> None:
    with pytest.raises(CespAntiIdleLawError):
        assert_never_fake_green_healthy_v1(
            stage_id="synthesis",
            total_objects=8,
            processed_count=0,
            substrate_state="healthy",
        )


def test_graph_all_orphans_degraded() -> None:
    assert _derive_graph_substrate_state_v1(
        entity_count=100,
        linked_entities=0,
        orphan_count=100,
        link_count=0,
        candidate_count=0,
    ) == "degraded"


def test_tcre_reconstruction_never_run_degraded() -> None:
    assert _derive_tcre_substrate_state_v1(
        mat_total=50,
        reconstructed=0,
        reconstruction_never_run=True,
        failed_jobs=0,
        degraded_chron=0,
        pending=50,
    ) == "degraded"


def test_retrieval_zero_eligible_upstream_tcre_pending_degraded() -> None:
    state = derive_retrieval_stage_substrate_state_v1(
        eligible=0,
        indexed=0,
        coverage_percent=0.0,
        published_epoch=None,
        replay_posture="unknown",
        pending_index_builds=0,
        upstream_tcre_pending=True,
        upstream_work_present=True,
    )
    assert state == "degraded"


def test_retrieval_zero_eligible_true_idle_healthy() -> None:
    state = derive_retrieval_stage_substrate_state_v1(
        eligible=0,
        indexed=0,
        coverage_percent=0.0,
        published_epoch=None,
        replay_posture="unknown",
        pending_index_builds=0,
        upstream_tcre_pending=False,
        upstream_work_present=False,
    )
    assert state == "healthy"


def test_synthesis_classify_starved_vs_idle() -> None:
    assert (
        classify_synthesis_idle_v1(
            eligible_scopes=0,
            synthesized_scopes=0,
            upstream_starvation=True,
        )
        == "starved"
    )
    assert (
        classify_synthesis_idle_v1(
            eligible_scopes=0,
            synthesized_scopes=0,
            upstream_starvation=False,
        )
        == "healthy_idle"
    )


def test_anti_idle_post_pass_coerces_fake_green(monkeypatch: pytest.MonkeyPatch) -> None:
    session = MagicMock()
    tid = uuid.uuid4()
    stages = [
        {
            "stage_id": "ingestion",
            "substrate_state": "healthy",
            "total_objects": 0,
            "processed_count": 0,
            "metrics": {},
            "drift_warnings": [],
            "omission_classes": {},
        },
        {
            "stage_id": "graph",
            "substrate_state": "healthy",
            "total_objects": 10,
            "processed_count": 0,
            "metrics": {},
            "drift_warnings": [],
            "omission_classes": {},
        },
    ]
    monkeypatch.setattr(
        "vector.domains.cortex.operational_runtime.fake_green_prohibition.pipeline_continuation_blocks_progress_v1",
        lambda *_a, **_k: False,
    )
    out = apply_cesp_anti_idle_law_to_pipeline_stages_v1(
        session,
        tenant_id=tid,
        stages=stages,
        propagation_chain=[],
    )
    graph = next(s for s in out if s["stage_id"] == "graph")
    assert graph["substrate_state"] == "degraded"
    assert graph["metrics"]["operational_idle_class"] == OPERATIONAL_IDLE_STARVATION_V1


def test_graph_projection_all_orphans_not_healthy(monkeypatch: pytest.MonkeyPatch) -> None:
    tid = uuid.uuid4()
    session = MagicMock()

    def _scalar(_stmt: object) -> int:
        return _scalar.n  # type: ignore[attr-defined]

    _scalar.n = 0  # type: ignore[attr-defined]

    def _next() -> int:
        values = [50, 0, 0]
        v = values[_scalar.n] if _scalar.n < len(values) else 0  # type: ignore[attr-defined]
        _scalar.n += 1  # type: ignore[attr-defined]
        return v

    session.scalar.side_effect = lambda _stmt: _next()
    from vector.domains.cortex.operational_runtime.graph_density import (
        METRIC_GRAPH_CANDIDATE_COUNT_V1,
        METRIC_GRAPH_CONNECTIVITY_RATIO_V1,
        METRIC_GRAPH_DENSITY_SCORE_V1,
        METRIC_GRAPH_ORPHAN_ARTIFACT_COUNT_V1,
        METRIC_GRAPH_PROMOTED_EDGE_COUNT_V1,
    )

    monkeypatch.setattr(
        "vector.domains.cortex.operational_runtime.graph_density.compute_graph_density_metrics_v1",
        lambda *_a, **_k: {
            "graph_maturity_stage": "G0",
            "metrics": {
                "entity_count": 50,
                "linked_entity_count": 0,
                METRIC_GRAPH_PROMOTED_EDGE_COUNT_V1: 0,
                METRIC_GRAPH_CANDIDATE_COUNT_V1: 0,
                METRIC_GRAPH_ORPHAN_ARTIFACT_COUNT_V1: 50,
                METRIC_GRAPH_CONNECTIVITY_RATIO_V1: 0.0,
                METRIC_GRAPH_DENSITY_SCORE_V1: 0,
                "pending_link_candidates": 0,
            },
        },
    )
    monkeypatch.setattr(
        "vector.domains.cortex.operational_runtime.graph_orphan_continuity.classify_tenant_graph_orphans_v1",
        lambda *_a, **_k: {"orphan_entity_count": 50, "counts_by_class": {}},
    )
    out = project_graph_completeness_v1(session, tenant_id=tid)
    assert out["substrate_state"] == "degraded"
    assert out["metrics"]["orphan_node_count"] == 50
