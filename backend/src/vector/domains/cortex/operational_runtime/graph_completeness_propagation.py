"""Phase 08.5 P085-13 — graph completeness propagation (**G-P085-GRAPH-PROP-01**).

Normative: ``DOCS/cortex/operational-runtime/phase-085-graph-density-doctrine.md`` §Completeness propagation.
Closes anti-fake-green graph card requirements (**P0-085-02**).
"""

from __future__ import annotations

import inspect
import uuid
from typing import Any, Final

from sqlalchemy.orm import Session

from vector.domains.cortex.operational_runtime.graph_density import (
    GRAPH_MATURITY_STAGE_G0_V1,
    METRIC_GRAPH_CANDIDATE_COUNT_V1,
    METRIC_GRAPH_CONNECTIVITY_RATIO_V1,
    METRIC_GRAPH_DENSITY_SCORE_V1,
    METRIC_GRAPH_ORPHAN_ARTIFACT_COUNT_V1,
    METRIC_GRAPH_PROMOTED_EDGE_COUNT_V1,
)
from vector.domains.cortex.operational_runtime.graph_orphan_continuity import (
    ORPHAN_CLASS_AWAITING_PROMOTION_V1,
    ORPHAN_CLASS_DISCONNECTED_COMPONENT_V1,
    ORPHAN_CLASS_IDENTITY_UNRESOLVED_V1,
    ORPHAN_CLASS_IDS_V1,
)
from vector.domains.cortex.operational_runtime.normative import (
    PHASE085_NORMATIVE_TREE_V1,
)
from vector.domains.cortex.retrieval.retrieval_skip_registry import (
    RET_SKIP_GRAPH_DISCONNECTED_V1,
)

PHASE085_GRAPH_PROPAGATION_RUNTIME_SCHEMA_VERSION: Final[int] = 1

PHASE085_GRAPH_PROPAGATION_SPEC_REF_V1: Final[str] = (
    f"{PHASE085_NORMATIVE_TREE_V1}phase-085-graph-density-doctrine.md"
)

GP085_GRAPH_PROP01_GATE_ID_V1: Final[str] = "G-P085-GRAPH-PROP-01"

GRAPH_PROPAGATION_LAW_VERSION_V1: Final[str] = "cesp.graph_completeness_propagation.v1"

GRAPH_STAGE_OMISSION_ORPHAN_ARTIFACTS_V1: Final[str] = "orphan_artifacts"
GRAPH_STAGE_OMISSION_PENDING_CANDIDATES_V1: Final[str] = "pending_link_candidates"

GRAPH_PROPAGATION_DOWNSTREAM_STAGES_V1: Final[tuple[str, ...]] = (
    "traversal",
    "tcre",
    "retrieval",
)


def derive_graph_completeness_substrate_state_v1(
    *,
    entity_count: int,
    linked_entities: int,
    orphan_count: int,
    link_count: int,
    candidate_count: int,
    pending_candidates: int,
    graph_maturity_stage: str,
    fake_green_blocked: bool,
    orphan_disconnected_count: int,
    orphan_identity_unresolved_count: int,
    islands_eligible_count: int = 0,
    traversal_propagation_mode: str = "global",
) -> str:
    """Derive graph stage ``substrate_state`` with traversal-blocking orphan law."""
    if entity_count == 0:
        return "critical"
    if linked_entities == 0:
        return "degraded"
    if orphan_count >= entity_count:
        return "degraded"
    if orphan_count > entity_count * 0.2:
        return "degraded"
    if link_count == 0 and candidate_count > 0:
        return "degraded"
    if graph_maturity_stage == GRAPH_MATURITY_STAGE_G0_V1:
        return "degraded"
    if (
        orphan_disconnected_count > 0
        and linked_entities > 0
        and not (
            traversal_propagation_mode == "component" and islands_eligible_count > 0
        )
    ):
        return "degraded"
    if orphan_identity_unresolved_count > 0:
        return "degraded"
    if fake_green_blocked:
        return "degraded"
    from vector.domains.cortex.operational_runtime.graph_density import (
        get_graph_pending_candidate_threshold_v1,
    )

    if pending_candidates > get_graph_pending_candidate_threshold_v1() and orphan_count > 0:
        return "degraded"
    return "healthy"


def build_graph_stage_omission_classes_v1(
    *,
    orphan_count: int,
    pending_candidates: int,
    orphan_classification_counts: dict[str, int],
) -> dict[str, int]:
    """Merge legacy + doctrine orphan class omissions for degradation propagation."""
    omissions: dict[str, int] = {}
    if orphan_count > 0:
        omissions[GRAPH_STAGE_OMISSION_ORPHAN_ARTIFACTS_V1] = orphan_count
    if pending_candidates > 0:
        omissions[GRAPH_STAGE_OMISSION_PENDING_CANDIDATES_V1] = pending_candidates
    for cls in ORPHAN_CLASS_IDS_V1:
        cnt = int(orphan_classification_counts.get(cls) or 0)
        if cnt > 0:
            omissions[cls] = cnt
    return omissions


def build_graph_completeness_propagation_manifest_v1(
    *,
    substrate_state: str,
    fake_green_evaluation: dict[str, Any],
    orphan_classification: dict[str, Any],
    traversal_propagation_blocked: bool,
    traversal_propagation: dict[str, Any] | None = None,
) -> dict[str, Any]:
    prop = dict(traversal_propagation or {})
    return {
        "law_version": GRAPH_PROPAGATION_LAW_VERSION_V1,
        "gate_id": GP085_GRAPH_PROP01_GATE_ID_V1,
        "substrate_state": substrate_state,
        "fake_green_evaluation": dict(fake_green_evaluation),
        "orphan_entity_count": int(orphan_classification.get("orphan_entity_count") or 0),
        "counts_by_orphan_class": dict(orphan_classification.get("counts_by_class") or {}),
        "traversal_propagation_blocked": traversal_propagation_blocked,
        "traversal_propagation_mode": prop.get(
            "traversal_propagation_mode", "global"
        ),
        "islands_eligible_count": int(prop.get("islands_eligible_count") or 0),
        "global_degraded": substrate_state == "degraded",
        "traversal_propagation_block_reason": prop.get("traversal_propagation_block_reason"),
        "downstream_stages": list(GRAPH_PROPAGATION_DOWNSTREAM_STAGES_V1),
        "ret_skip_when_disconnected": RET_SKIP_GRAPH_DISCONNECTED_V1,
    }


def propagate_graph_completeness_stage_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
) -> dict[str, Any]:
    """Build graph completeness stage envelope with density + orphan propagation law."""
    from vector.domains.cortex.completeness._completeness_common import (
        build_stage_envelope_v1,
        pct,
    )
    from vector.domains.cortex.operational_runtime.graph_density import (
        compute_graph_density_metrics_v1,
        evaluate_graph_density_fake_green_v1,
        get_graph_pending_candidate_threshold_v1,
    )
    from vector.domains.cortex.operational_runtime.graph_orphan_continuity import (
        classify_tenant_graph_orphans_v1,
    )

    density = compute_graph_density_metrics_v1(session, tenant_id=tenant_id)
    dm = dict(density["metrics"])
    entity_count = int(dm["entity_count"])
    link_count = int(dm[METRIC_GRAPH_PROMOTED_EDGE_COUNT_V1])
    candidate_count = int(dm[METRIC_GRAPH_CANDIDATE_COUNT_V1])
    linked_entities = int(dm["linked_entity_count"])
    orphan_count = int(dm[METRIC_GRAPH_ORPHAN_ARTIFACT_COUNT_V1])
    pending_candidates = int(dm["pending_link_candidates"])
    density_score = int(dm[METRIC_GRAPH_DENSITY_SCORE_V1])
    connectivity_ratio = float(dm[METRIC_GRAPH_CONNECTIVITY_RATIO_V1])
    maturity_stage = str(density.get("graph_maturity_stage") or GRAPH_MATURITY_STAGE_G0_V1)

    orphan_classification = classify_tenant_graph_orphans_v1(
        session,
        tenant_id=tenant_id,
        sample_limit=0,
    )
    counts_by_class = dict(orphan_classification.get("counts_by_class") or {})
    orphan_disconnected = int(counts_by_class.get(ORPHAN_CLASS_DISCONNECTED_COMPONENT_V1, 0))
    orphan_identity_unresolved = int(counts_by_class.get(ORPHAN_CLASS_IDENTITY_UNRESOLVED_V1, 0))

    from vector.domains.cortex.operational_runtime.substrate_traversal_scheduling import (
        evaluate_traversal_propagation_v1,
    )

    propagation_law = evaluate_traversal_propagation_v1(
        session,
        tenant_id=tenant_id,
        linked_entity_count=linked_entities,
        entity_count=entity_count,
        orphan_disconnected_count=orphan_disconnected,
        orphan_identity_unresolved_count=orphan_identity_unresolved,
    )
    traversal_blocked = bool(propagation_law["traversal_propagation_blocked"])
    islands_eligible = int(propagation_law.get("islands_eligible_count") or 0)
    propagation_mode = str(propagation_law.get("traversal_propagation_mode") or "global")

    fake_green = evaluate_graph_density_fake_green_v1(
        graph_orphan_artifact_count=orphan_count,
        pending_link_candidates=pending_candidates,
        substrate_state="healthy",
        pending_threshold=get_graph_pending_candidate_threshold_v1(),
    )

    substrate_state = derive_graph_completeness_substrate_state_v1(
        entity_count=entity_count,
        linked_entities=linked_entities,
        orphan_count=orphan_count,
        link_count=link_count,
        candidate_count=candidate_count,
        pending_candidates=pending_candidates,
        graph_maturity_stage=maturity_stage,
        fake_green_blocked=bool(fake_green["fake_green_blocked"]),
        orphan_disconnected_count=orphan_disconnected,
        orphan_identity_unresolved_count=orphan_identity_unresolved,
        islands_eligible_count=islands_eligible,
        traversal_propagation_mode=propagation_mode,
    )

    omission_classes = build_graph_stage_omission_classes_v1(
        orphan_count=orphan_count,
        pending_candidates=pending_candidates,
        orphan_classification_counts=counts_by_class,
    )

    degraded_count = orphan_disconnected + orphan_identity_unresolved

    replay_posture = "stable" if linked_entities and not orphan_count else (
        "partial" if linked_entities else "unknown"
    )

    propagation_manifest = build_graph_completeness_propagation_manifest_v1(
        substrate_state=substrate_state,
        fake_green_evaluation=fake_green,
        orphan_classification=orphan_classification,
        traversal_propagation_blocked=traversal_blocked,
        traversal_propagation=propagation_law,
    )

    drift_warnings: list[str] = []
    if fake_green.get("fake_green_blocked"):
        drift_warnings.append(
            "graph_fake_green_blocked:"
            f"orphans={orphan_count},pending_candidates={pending_candidates}"
        )
    if traversal_blocked:
        drift_warnings.append("graph_traversal_propagation_blocked")

    return build_stage_envelope_v1(
        stage_id="graph",
        label="Graph",
        total_objects=entity_count,
        processed_count=linked_entities,
        degraded_count=degraded_count,
        unresolved_count=orphan_count,
        omitted_count=pending_candidates,
        replay_posture=replay_posture,
        substrate_state=substrate_state,
        omission_classes=omission_classes,
        detail_route=f"/admin/tenants/{tenant_id}/cortex/graph",
        drift_warnings=drift_warnings,
        metrics={
            "entity_count": entity_count,
            "linked_entity_count": linked_entities,
            "authoritative_link_count": link_count,
            "candidate_link_count": candidate_count,
            "graph_connectivity_percent": pct(linked_entities, entity_count if entity_count else 1),
            "orphan_node_count": orphan_count,
            "graph_density_score": density_score,
            "graph_connectivity_ratio": connectivity_ratio,
            "graph_maturity_stage": maturity_stage,
            "orphan_classification_counts": counts_by_class,
            "graph_completeness_propagation": propagation_manifest,
            **{k: dm[k] for k in dm if k.startswith("graph_")},
        },
    )


def build_graph_completeness_propagation_catalog_v1() -> dict[str, Any]:
    return {
        "surface_kind": "doctrine_catalog",
        "phase085_graph_propagation_runtime_schema_version": int(
            PHASE085_GRAPH_PROPAGATION_RUNTIME_SCHEMA_VERSION,
        ),
        "spec_ref": PHASE085_GRAPH_PROPAGATION_SPEC_REF_V1,
        "primary_gate_id": GP085_GRAPH_PROP01_GATE_ID_V1,
        "propagation_law_version": GRAPH_PROPAGATION_LAW_VERSION_V1,
        "graph_stage_omission_classes": [
            GRAPH_STAGE_OMISSION_ORPHAN_ARTIFACTS_V1,
            GRAPH_STAGE_OMISSION_PENDING_CANDIDATES_V1,
            *ORPHAN_CLASS_IDS_V1,
        ],
        "downstream_stages": list(GRAPH_PROPAGATION_DOWNSTREAM_STAGES_V1),
        "p0_gap_closed": "P0-085-02",
        "runtime_package": "vector.domains.cortex.operational_runtime.graph_completeness_propagation",
        "propagation_entrypoint": "propagate_graph_completeness_stage_v1",
    }


def verify_gp085_graph_prop01_static() -> dict[str, Any]:
    errors: list[str] = []
    cat = build_graph_completeness_propagation_catalog_v1()
    if cat["primary_gate_id"] != GP085_GRAPH_PROP01_GATE_ID_V1:
        errors.append("primary_gate_id_mismatch")

    state = derive_graph_completeness_substrate_state_v1(
        entity_count=100,
        linked_entities=0,
        orphan_count=100,
        link_count=0,
        candidate_count=0,
        pending_candidates=0,
        graph_maturity_stage=GRAPH_MATURITY_STAGE_G0_V1,
        fake_green_blocked=False,
        orphan_disconnected_count=0,
        orphan_identity_unresolved_count=0,
    )
    if state != "degraded":
        errors.append(f"all_orphans_expected_degraded_got_{state}")

    state_fg = derive_graph_completeness_substrate_state_v1(
        entity_count=50,
        linked_entities=40,
        orphan_count=10,
        link_count=30,
        candidate_count=100,
        pending_candidates=100,
        graph_maturity_stage="G2",
        fake_green_blocked=True,
        orphan_disconnected_count=0,
        orphan_identity_unresolved_count=0,
    )
    if state_fg != "degraded":
        errors.append("fake_green_must_force_degraded")

    from vector.domains.cortex.completeness import graph_completeness_projection as gcp

    gcp_src = inspect.getsource(gcp.project_graph_completeness_v1)
    if "propagate_graph_completeness_stage_v1" not in gcp_src:
        errors.append("graph_completeness_projection_missing_propagation_delegate")

    from vector.domains.cortex.completeness import completeness_degradation_projection as cdp

    rules_src = inspect.getsource(cdp)
    if ORPHAN_CLASS_DISCONNECTED_COMPONENT_V1 not in rules_src:
        errors.append("degradation_chain_missing_orphan_disconnected_rule")
    if ORPHAN_CLASS_AWAITING_PROMOTION_V1 not in rules_src:
        errors.append("degradation_chain_missing_orphan_awaiting_promotion_rule")

    passed = not errors
    return {
        "id": GP085_GRAPH_PROP01_GATE_ID_V1,
        "name": "cesp_graph_completeness_propagation",
        "passed": passed,
        "severity": "hard_fail",
        "detail": {"errors": errors},
    }
