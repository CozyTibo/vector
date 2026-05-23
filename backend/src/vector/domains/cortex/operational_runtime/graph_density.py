"""Phase 08.5 P085-10 — graph density metrics (**G-P085-GRAPH-01**).

Normative: ``DOCS/cortex/operational-runtime/phase-085-graph-density-doctrine.md`` §Density metrics.
"""

from __future__ import annotations

import uuid
from typing import Any, Final

from sqlalchemy import func, select, union_all
from sqlalchemy.orm import Session

from vector.domains.cortex.operational_runtime.normative import (
    PHASE085_NORMATIVE_TREE_V1,
)
from vector.infrastructure.db.models.cortex_org_entity import CortexOrgEntity
from vector.infrastructure.db.models.cortex_org_link import CortexOrgLink
from vector.infrastructure.db.models.cortex_org_link_candidate import CortexOrgLinkCandidate

PHASE085_GRAPH_DENSITY_RUNTIME_SCHEMA_VERSION: Final[int] = 1

PHASE085_GRAPH_DENSITY_SPEC_REF_V1: Final[str] = (
    f"{PHASE085_NORMATIVE_TREE_V1}phase-085-graph-density-doctrine.md"
)

GP085_GRAPH01_GATE_ID_V1: Final[str] = "G-P085-GRAPH-01"

METRIC_GRAPH_PROMOTED_EDGE_COUNT_V1: Final[str] = "graph_promoted_edge_count"
METRIC_GRAPH_CANDIDATE_COUNT_V1: Final[str] = "graph_candidate_count"
METRIC_GRAPH_ORPHAN_ARTIFACT_COUNT_V1: Final[str] = "graph_orphan_artifact_count"
METRIC_GRAPH_CONNECTIVITY_RATIO_V1: Final[str] = "graph_connectivity_ratio"
METRIC_GRAPH_DENSITY_SCORE_V1: Final[str] = "graph_density_score"

GRAPH_DENSITY_METRIC_IDS_V1: Final[tuple[str, ...]] = (
    METRIC_GRAPH_PROMOTED_EDGE_COUNT_V1,
    METRIC_GRAPH_CANDIDATE_COUNT_V1,
    METRIC_GRAPH_ORPHAN_ARTIFACT_COUNT_V1,
    METRIC_GRAPH_CONNECTIVITY_RATIO_V1,
    METRIC_GRAPH_DENSITY_SCORE_V1,
)

GRAPH_MATURITY_STAGE_G0_V1: Final[str] = "G0"
GRAPH_MATURITY_STAGE_G1_V1: Final[str] = "G1"
GRAPH_MATURITY_STAGE_G2_V1: Final[str] = "G2"
GRAPH_MATURITY_STAGE_G3_V1: Final[str] = "G3"

GRAPH_MATURITY_STAGE_IDS_V1: Final[tuple[str, ...]] = (
    GRAPH_MATURITY_STAGE_G0_V1,
    GRAPH_MATURITY_STAGE_G1_V1,
    GRAPH_MATURITY_STAGE_G2_V1,
    GRAPH_MATURITY_STAGE_G3_V1,
)

GRAPH_MATURITY_G1_CONNECTIVITY_RATIO_V1: Final[float] = 0.3
GRAPH_MATURITY_G2_CONNECTIVITY_RATIO_V1: Final[float] = 0.7
GRAPH_ORPHAN_G0_ARTIFACT_RATIO_V1: Final[float] = 0.5

GRAPH_DENSITY_SCORE_WEIGHT_CONNECTIVITY_V1: Final[float] = 0.7
GRAPH_DENSITY_SCORE_WEIGHT_CANDIDATE_CLEARANCE_V1: Final[float] = 0.3


class GraphDensityError(ValueError):
    def __init__(self, code: str, *, detail: dict[str, Any] | None = None) -> None:
        self.code = code
        self.detail = dict(detail or {})
        super().__init__(code)


def get_graph_pending_candidate_threshold_v1() -> int:
    try:
        from vector.settings import get_settings

        return max(0, int(get_settings().cortex_graph_density_pending_candidate_threshold))
    except Exception:  # noqa: BLE001
        return 10


def count_active_org_entities_v1(session: Session, *, tenant_id: uuid.UUID) -> int:
    return int(
        session.scalar(
            select(func.count())
            .select_from(CortexOrgEntity)
            .where(
                CortexOrgEntity.tenant_id == tenant_id,
                CortexOrgEntity.tombstoned_at.is_(None),
                CortexOrgEntity.lifecycle_state == "active",
            )
        )
        or 0
    )


def count_graph_promoted_edge_count_v1(session: Session, *, tenant_id: uuid.UUID) -> int:
    """Authoritative non-revoked ``CortexOrgLink`` rows."""
    return int(
        session.scalar(
            select(func.count())
            .select_from(CortexOrgLink)
            .where(
                CortexOrgLink.tenant_id == tenant_id,
                CortexOrgLink.revoked_at.is_(None),
            )
        )
        or 0
    )


def count_graph_candidate_count_v1(session: Session, *, tenant_id: uuid.UUID) -> int:
    return int(
        session.scalar(
            select(func.count())
            .select_from(CortexOrgLinkCandidate)
            .where(CortexOrgLinkCandidate.tenant_id == tenant_id)
        )
        or 0
    )


def count_distinct_graph_candidate_pairs_v1(session: Session, *, tenant_id: uuid.UUID) -> int:
    """Distinct endpoint pairs — primary candidate inflation signal (not raw row count)."""
    return int(
        session.scalar(
            select(
                func.count(
                    func.distinct(
                        CortexOrgLinkCandidate.source_entity_id,
                        CortexOrgLinkCandidate.target_entity_id,
                        CortexOrgLinkCandidate.link_type,
                    )
                )
            ).where(CortexOrgLinkCandidate.tenant_id == tenant_id)
        )
        or 0
    )


def count_entities_with_promoted_edges_v1(session: Session, *, tenant_id: uuid.UUID) -> int:
    src = select(CortexOrgLink.source_entity_id.label("entity_id")).where(
        CortexOrgLink.tenant_id == tenant_id,
        CortexOrgLink.revoked_at.is_(None),
    )
    tgt = select(CortexOrgLink.target_entity_id.label("entity_id")).where(
        CortexOrgLink.tenant_id == tenant_id,
        CortexOrgLink.revoked_at.is_(None),
    )
    linked = union_all(src, tgt).subquery()
    return int(session.scalar(select(func.count(func.distinct(linked.c.entity_id)))) or 0)


def count_graph_orphan_artifact_count_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    entity_count: int | None = None,
    linked_entity_count: int | None = None,
) -> int:
    """Org entities (artifacts) without any authoritative connecting edge."""
    entities = entity_count if entity_count is not None else count_active_org_entities_v1(
        session,
        tenant_id=tenant_id,
    )
    linked = (
        linked_entity_count
        if linked_entity_count is not None
        else count_entities_with_promoted_edges_v1(session, tenant_id=tenant_id)
    )
    return max(0, entities - linked)


def compute_graph_connectivity_ratio_v1(
    *,
    graph_promoted_edge_count: int,
    graph_orphan_artifact_count: int,
) -> float:
    """``promoted / (promoted + orphans)`` per doctrine."""
    denom = graph_promoted_edge_count + graph_orphan_artifact_count
    if denom <= 0:
        return 0.0
    return round(graph_promoted_edge_count / denom, 6)


def compute_graph_density_score_v1(
    *,
    graph_connectivity_ratio: float,
    graph_candidate_count: int,
    graph_promoted_edge_count: int,
    pending_link_candidates: int,
) -> int:
    """Weighted composite **0–100** (connectivity + candidate backlog clearance)."""
    clearance = 1.0
    if graph_candidate_count > 0:
        backlog_ratio = pending_link_candidates / max(1, graph_candidate_count)
        clearance = max(0.0, 1.0 - min(1.0, backlog_ratio))
    elif graph_promoted_edge_count == 0 and pending_link_candidates > 0:
        clearance = 0.0
    raw = (
        GRAPH_DENSITY_SCORE_WEIGHT_CONNECTIVITY_V1 * graph_connectivity_ratio
        + GRAPH_DENSITY_SCORE_WEIGHT_CANDIDATE_CLEARANCE_V1 * clearance
    )
    return max(0, min(100, int(round(raw * 100))))


def classify_graph_maturity_stage_v1(
    *,
    entity_count: int,
    graph_orphan_artifact_count: int,
    graph_connectivity_ratio: float,
    pending_link_candidates: int,
) -> str:
    """Graph continuity maturity **G0..G3** (doctrine table)."""
    if entity_count > 0 and graph_orphan_artifact_count > entity_count * GRAPH_ORPHAN_G0_ARTIFACT_RATIO_V1:
        return GRAPH_MATURITY_STAGE_G0_V1
    if pending_link_candidates == 0 and graph_connectivity_ratio >= GRAPH_MATURITY_G2_CONNECTIVITY_RATIO_V1:
        return GRAPH_MATURITY_STAGE_G3_V1
    if graph_connectivity_ratio >= GRAPH_MATURITY_G2_CONNECTIVITY_RATIO_V1:
        return GRAPH_MATURITY_STAGE_G2_V1
    if graph_connectivity_ratio >= GRAPH_MATURITY_G1_CONNECTIVITY_RATIO_V1:
        return GRAPH_MATURITY_STAGE_G1_V1
    return GRAPH_MATURITY_STAGE_G0_V1


def evaluate_graph_density_fake_green_v1(
    *,
    graph_orphan_artifact_count: int,
    pending_link_candidates: int,
    substrate_state: str | None = None,
    pending_threshold: int | None = None,
) -> dict[str, Any]:
    """Doctrine fake-green rule: orphans + pending candidates above θ → not healthy."""
    theta = pending_threshold if pending_threshold is not None else get_graph_pending_candidate_threshold_v1()
    blocked = graph_orphan_artifact_count > 0 and pending_link_candidates > theta
    would_block_healthy = blocked and (substrate_state or "") == "healthy"
    return {
        "fake_green_blocked": blocked,
        "would_block_healthy_substrate_state": would_block_healthy,
        "pending_candidate_threshold": theta,
        "graph_orphan_artifact_count": graph_orphan_artifact_count,
        "pending_link_candidates": pending_link_candidates,
    }


def compute_graph_density_metrics_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
) -> dict[str, Any]:
    """Tenant graph density snapshot (**G-P085-GRAPH-01**)."""
    entity_count = count_active_org_entities_v1(session, tenant_id=tenant_id)
    promoted = count_graph_promoted_edge_count_v1(session, tenant_id=tenant_id)
    candidates = count_graph_candidate_count_v1(session, tenant_id=tenant_id)
    linked_entities = count_entities_with_promoted_edges_v1(session, tenant_id=tenant_id)
    orphans = count_graph_orphan_artifact_count_v1(
        session,
        tenant_id=tenant_id,
        entity_count=entity_count,
        linked_entity_count=linked_entities,
    )
    pending_candidates = max(0, candidates - promoted)
    connectivity = compute_graph_connectivity_ratio_v1(
        graph_promoted_edge_count=promoted,
        graph_orphan_artifact_count=orphans,
    )
    density_score = compute_graph_density_score_v1(
        graph_connectivity_ratio=connectivity,
        graph_candidate_count=candidates,
        graph_promoted_edge_count=promoted,
        pending_link_candidates=pending_candidates,
    )
    maturity_stage = classify_graph_maturity_stage_v1(
        entity_count=entity_count,
        graph_orphan_artifact_count=orphans,
        graph_connectivity_ratio=connectivity,
        pending_link_candidates=pending_candidates,
    )
    metrics = {
        METRIC_GRAPH_PROMOTED_EDGE_COUNT_V1: promoted,
        METRIC_GRAPH_CANDIDATE_COUNT_V1: candidates,
        METRIC_GRAPH_ORPHAN_ARTIFACT_COUNT_V1: orphans,
        METRIC_GRAPH_CONNECTIVITY_RATIO_V1: connectivity,
        METRIC_GRAPH_DENSITY_SCORE_V1: density_score,
        "entity_count": entity_count,
        "linked_entity_count": linked_entities,
        "pending_link_candidates": pending_candidates,
    }
    return {
        "tenant_id": str(tenant_id),
        "gate_id": GP085_GRAPH01_GATE_ID_V1,
        "graph_maturity_stage": maturity_stage,
        "metrics": metrics,
        "fake_green_evaluation": evaluate_graph_density_fake_green_v1(
            graph_orphan_artifact_count=orphans,
            pending_link_candidates=pending_candidates,
        ),
    }


def build_graph_density_catalog_v1() -> dict[str, Any]:
    """Doctrine catalog for graph density (P085-10)."""
    return {
        "surface_kind": "doctrine_catalog",
        "phase085_graph_density_runtime_schema_version": int(
            PHASE085_GRAPH_DENSITY_RUNTIME_SCHEMA_VERSION,
        ),
        "spec_ref": PHASE085_GRAPH_DENSITY_SPEC_REF_V1,
        "primary_gate_id": GP085_GRAPH01_GATE_ID_V1,
        "metric_ids": list(GRAPH_DENSITY_METRIC_IDS_V1),
        "graph_maturity_stage_ids": list(GRAPH_MATURITY_STAGE_IDS_V1),
        "maturity_thresholds": {
            "g0_orphan_artifact_ratio_gt": GRAPH_ORPHAN_G0_ARTIFACT_RATIO_V1,
            "g1_connectivity_ratio_gte": GRAPH_MATURITY_G1_CONNECTIVITY_RATIO_V1,
            "g2_connectivity_ratio_gte": GRAPH_MATURITY_G2_CONNECTIVITY_RATIO_V1,
            "g3_pending_candidates_eq": 0,
        },
        "density_score_weights": {
            "connectivity": GRAPH_DENSITY_SCORE_WEIGHT_CONNECTIVITY_V1,
            "candidate_clearance": GRAPH_DENSITY_SCORE_WEIGHT_CANDIDATE_CLEARANCE_V1,
        },
        "pending_candidate_threshold": get_graph_pending_candidate_threshold_v1(),
        "runtime_package": "vector.domains.cortex.operational_runtime.graph_density",
        "admin_explorer_route_hint": "/cortex/graph/density",
    }


def verify_gp085_graph01_static() -> dict[str, Any]:
    errors: list[str] = []
    cat = build_graph_density_catalog_v1()
    if cat["primary_gate_id"] != GP085_GRAPH01_GATE_ID_V1:
        errors.append("primary_gate_id_mismatch")
    if set(cat["metric_ids"]) != set(GRAPH_DENSITY_METRIC_IDS_V1):
        errors.append("metric_ids_mismatch")

    ratio = compute_graph_connectivity_ratio_v1(
        graph_promoted_edge_count=70,
        graph_orphan_artifact_count=30,
    )
    if abs(ratio - 0.7) > 0.001:
        errors.append("connectivity_ratio_formula")

    score = compute_graph_density_score_v1(
        graph_connectivity_ratio=1.0,
        graph_candidate_count=0,
        graph_promoted_edge_count=10,
        pending_link_candidates=0,
    )
    if score != 100:
        errors.append("density_score_max_expected_100")

    stage = classify_graph_maturity_stage_v1(
        entity_count=100,
        graph_orphan_artifact_count=10,
        graph_connectivity_ratio=0.75,
        pending_link_candidates=0,
    )
    if stage != GRAPH_MATURITY_STAGE_G3_V1:
        errors.append(f"expected_g3_got_{stage}")

    import inspect

    from vector.domains.cortex.operational_runtime import graph_completeness_propagation as gprop

    gprop_src = inspect.getsource(gprop.propagate_graph_completeness_stage_v1)
    if "compute_graph_density_metrics_v1" not in gprop_src:
        errors.append("graph_propagation_missing_density_integration")
    if "graph_density_score" not in gprop_src:
        errors.append("graph_propagation_missing_density_score_metric")

    passed = not errors
    return {
        "id": GP085_GRAPH01_GATE_ID_V1,
        "name": "cesp_graph_density_metrics",
        "passed": passed,
        "severity": "hard_fail",
        "detail": {"errors": errors},
    }
