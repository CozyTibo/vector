"""Phase 08.5 P085-17 — traversal density + explainability (**G-P085-WALK-04**).

Normative: ``DOCS/cortex/operational-runtime/phase-085-traversal-completion-doctrine.md`` §Explainability.
"""

from __future__ import annotations

import inspect
import uuid
from datetime import UTC, datetime
from typing import Any, Final

from sqlalchemy.orm import Session

from vector.domains.cortex.operational_runtime.graph_density import (
    GRAPH_MATURITY_STAGE_G0_V1,
    GRAPH_MATURITY_STAGE_G1_V1,
    GRAPH_MATURITY_STAGE_G2_V1,
    GRAPH_MATURITY_STAGE_G3_V1,
    METRIC_GRAPH_DENSITY_SCORE_V1,
    compute_graph_density_metrics_v1,
)
from vector.domains.cortex.operational_runtime.graph_orphan_continuity import (
    ORPHAN_CLASS_DISCONNECTED_COMPONENT_V1,
    ORPHAN_CLASS_IDENTITY_UNRESOLVED_V1,
    classify_tenant_graph_orphans_v1,
    list_graph_connected_components_v1,
)
from vector.domains.cortex.operational_runtime.normative import (
    PHASE085_NORMATIVE_TREE_V1,
)
from vector.domains.cortex.operational_runtime.substrate_traversal_retry import (
    CESP_WALK_RETRY_DETAIL_KEY_V1,
    classify_walk_failure_v1,
)
from vector.domains.cortex.operational_runtime.substrate_traversal_scheduling import (
    GP085_WALK01_GATE_ID_V1,
    _is_traversal_propagation_blocked_v1,
    evaluate_traversal_schedule_v1,
    get_traversal_queue_saturation_threshold_v1,
)
from vector.domains.cortex.operational_runtime.substrate_stalled_traversal_recovery import (
    CESP_WALK_STALL_DETAIL_KEY_V1,
    GP085_WALK03_GATE_ID_V1,
    classify_walk_poison_v1,
    evaluate_tenant_traversal_stall_v1,
)
from vector.domains.cortex.traversal.runtime.durable_walk_store import resolve_octs_walk_store_v1
from vector.domains.cortex.traversal.walk_api_contract import WalkApiRecordV1
from vector.infrastructure.db.models.cortex_octs_durable_walk_record import (
    CortexOctsDurableWalkRecord,
)

PHASE085_TRAVERSAL_EXPLAINABILITY_RUNTIME_SCHEMA_VERSION: Final[int] = 1

PHASE085_TRAVERSAL_EXPLAINABILITY_SPEC_REF_V1: Final[str] = (
    f"{PHASE085_NORMATIVE_TREE_V1}phase-085-traversal-completion-doctrine.md"
)

GP085_WALK04_GATE_ID_V1: Final[str] = "G-P085-WALK-04"

METRIC_WALKS_COMPLETED_RATE_V1: Final[str] = "walks_completed_rate"
METRIC_WALKS_PENDING_GAUGE_V1: Final[str] = "walks_pending_gauge"
METRIC_TRAVERSAL_DENSITY_SCORE_V1: Final[str] = "traversal_density_score"

_EXPLAINABILITY_PANEL_REQUIRED_KEYS_V1: Final[frozenset[str]] = frozenset(
    {
        "gate_id",
        "tenant_id",
        "metrics",
        "why_walks_pending",
        "upstream_graph_omissions",
        "per_walk_explanations",
        "operational_alive",
    }
)

_GRAPH_G1_PLUS_STAGES_V1: Final[frozenset[str]] = frozenset(
    {
        GRAPH_MATURITY_STAGE_G1_V1,
        GRAPH_MATURITY_STAGE_G2_V1,
        GRAPH_MATURITY_STAGE_G3_V1,
    }
)

_EARLY_TERMINATION_REASONS_V1: Final[frozenset[str]] = frozenset(
    {
        "empty_frontier",
        "budget_exhausted",
        "policy_rejected",
        "invalid_edge_at_t",
        "dangling_evidence",
        "import_hash_mismatch",
        "error_internal",
    }
)


class SubstrateTraversalExplainabilityError(ValueError):
    def __init__(self, code: str, *, detail: dict[str, Any] | None = None) -> None:
        self.code = code
        self.detail = dict(detail or {})
        super().__init__(code)


def get_traversal_density_operational_alive_threshold_v1() -> float:
    try:
        from vector.settings import get_settings

        return max(0.0, min(1.0, float(get_settings().cortex_traversal_density_operational_alive_threshold)))
    except Exception:  # noqa: BLE001
        return 0.5


def _termination_reason_from_record_v1(record: WalkApiRecordV1) -> str:
    payload = dict(record.walk_payload or {})
    hb = dict((payload.get("walk_result") or {}).get("hash_body") or {})
    return str(hb.get("termination_reason") or "").strip()


def _hop_count_from_record_v1(record: WalkApiRecordV1) -> int:
    payload = dict(record.walk_payload or {})
    telemetry = dict(payload.get("telemetry") or {})
    if telemetry.get("hops_emitted") is not None:
        return int(telemetry["hops_emitted"])
    hb = dict((payload.get("walk_result") or {}).get("hash_body") or {})
    return len(hb.get("hop_receipts") or [])


def _durable_row_replay_fields_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    walk_id: uuid.UUID,
) -> dict[str, Any]:
    row = session.get(CortexOctsDurableWalkRecord, walk_id)
    if row is None or row.tenant_id != tenant_id:
        return {}
    return {
        "replay_legality_posture": str(row.replay_legality_posture or ""),
        "degradation_classes": list(row.degradation_classes or []),
        "replay_identity": str(row.replay_identity or ""),
        "parent_walk_id": str(row.parent_walk_id) if row.parent_walk_id else None,
    }


def explain_walk_replay_posture_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    record: WalkApiRecordV1,
) -> dict[str, Any]:
    """Replay posture per walk (**G-P085-WALK-04**)."""
    durable = _durable_row_replay_fields_v1(session, tenant_id=tenant_id, walk_id=record.walk_id)
    posture = durable.get("replay_legality_posture") or ""
    if not posture:
        tr = _termination_reason_from_record_v1(record)
        if record.status != "completed":
            posture = "not_completed"
        elif tr in ("completed", "frontier_exhausted", ""):
            posture = "replay_safe"
        else:
            posture = "degraded"
    degradation = list(durable.get("degradation_classes") or [])
    if not degradation and posture == "degraded":
        tr = _termination_reason_from_record_v1(record)
        if tr:
            degradation = [tr]
    return {
        "walk_id": str(record.walk_id),
        "replay_legality_posture": posture,
        "degradation_classes": degradation,
        "replay_identity": durable.get("replay_identity"),
        "parent_walk_id": durable.get("parent_walk_id"),
    }


def explain_walk_early_termination_v1(record: WalkApiRecordV1) -> dict[str, Any]:
    """Why a walk terminated early (**G-P085-WALK-04**)."""
    tr = _termination_reason_from_record_v1(record)
    hops = _hop_count_from_record_v1(record)
    terminated_early = bool(tr and tr not in ("completed", "frontier_exhausted"))
    failure_class, reason_code = classify_walk_failure_v1(record)
    return {
        "walk_id": str(record.walk_id),
        "status": record.status,
        "termination_reason": tr or None,
        "hops_emitted": hops,
        "terminated_early": terminated_early,
        "early_termination_reason_known": tr in _EARLY_TERMINATION_REASONS_V1 if tr else False,
        "cesp_failure_class": failure_class,
        "cesp_reason_code": reason_code or None,
        "summary": (
            f"Walk ended with termination_reason={tr} after {hops} hop(s)."
            if tr
            else "Walk has no termination_reason in payload."
        ),
    }


def explain_why_walks_pending_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    pending_records: list[WalkApiRecordV1],
    stall_evaluation: dict[str, Any],
    schedule_evaluation: dict[str, Any],
    queue_depth: int,
) -> list[dict[str, Any]]:
    """Operator-facing reasons why walks remain pending."""
    reasons: list[dict[str, Any]] = []
    if not pending_records:
        reasons.append({"code": "no_pending_walks", "detail": "Traversal queue is empty."})
        return reasons

    if stall_evaluation.get("stalled"):
        reasons.append(
            {
                "code": "traversal_stalled",
                "detail": stall_evaluation.get("reason"),
                "stall_threshold_seconds": stall_evaluation.get("stall_threshold_seconds"),
            }
        )

    if not schedule_evaluation.get("should_schedule"):
        reasons.append(
            {
                "code": "scheduling_not_eligible",
                "detail": schedule_evaluation.get("schedule_reason"),
            }
        )

    if queue_depth >= get_traversal_queue_saturation_threshold_v1():
        reasons.append(
            {
                "code": "queue_saturated",
                "detail": f"walk_queue_depth={queue_depth}",
            }
        )

    for rec in pending_records[:8]:
        body = dict(rec.request_body or {})
        per: dict[str, Any] = {
            "code": "pending_walk",
            "walk_id": str(rec.walk_id),
            "status": rec.status,
            "job_id": rec.job_id,
        }
        if body.get(CESP_WALK_STALL_DETAIL_KEY_V1):
            per["stall_detail"] = dict(body[CESP_WALK_STALL_DETAIL_KEY_V1])
        if body.get(CESP_WALK_RETRY_DETAIL_KEY_V1):
            per["retry_detail"] = dict(body[CESP_WALK_RETRY_DETAIL_KEY_V1])
        is_poison, poison_reason = classify_walk_poison_v1(rec)
        if is_poison:
            per["poison_candidate"] = True
            per["poison_reason"] = poison_reason
        reasons.append(per)

    return reasons


def build_upstream_graph_omissions_for_traversal_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
) -> dict[str, Any]:
    """Upstream graph omissions that block or degrade traversal."""
    from vector.domains.cortex.operational_runtime.graph_completeness_propagation import (
        propagate_graph_completeness_stage_v1,
    )

    graph_stage = propagate_graph_completeness_stage_v1(session, tenant_id=tenant_id)
    omission_classes = dict(graph_stage.get("omission_classes") or {})
    metrics = dict(graph_stage.get("metrics") or {})
    manifest = dict(metrics.get("graph_completeness_propagation") or {})

    blocked = bool(manifest.get("traversal_propagation_blocked"))
    if not blocked:
        orphan_cls = classify_tenant_graph_orphans_v1(session, tenant_id=tenant_id, sample_limit=0)
        counts = dict(orphan_cls.get("counts_by_class") or {})
        dm = compute_graph_density_metrics_v1(session, tenant_id=tenant_id)["metrics"]
        blocked = _is_traversal_propagation_blocked_v1(
            linked_entity_count=int(dm.get("linked_entity_count") or 0),
            entity_count=int(dm.get("entity_count") or 0),
            orphan_disconnected_count=int(counts.get(ORPHAN_CLASS_DISCONNECTED_COMPONENT_V1, 0)),
            orphan_identity_unresolved_count=int(
                counts.get(ORPHAN_CLASS_IDENTITY_UNRESOLVED_V1, 0)
            ),
        )

    return {
        "traversal_propagation_blocked": blocked,
        "omission_classes": omission_classes,
        "graph_substrate_state": graph_stage.get("substrate_state"),
        "graph_maturity_stage": metrics.get("graph_maturity_stage"),
        "ret_skip_when_disconnected": manifest.get("ret_skip_when_disconnected"),
    }


def compute_traversal_density_metrics_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
) -> dict[str, Any]:
    """Doctrine metrics: completed rate, pending gauge, traversal density score."""
    store = resolve_octs_walk_store_v1(session)
    records = store.list_walk_records_for_tenant_v1(tenant_id)
    snapshot = store.get_tenant_walk_queue_snapshot_v1(tenant_id)

    completed_with_payload = 0
    completed_total = 0
    for rec in records:
        if rec.status == "completed":
            completed_total += 1
            if rec.walk_payload:
                completed_with_payload += 1

    pending = int(snapshot["pending_count"])
    total = len(records)
    walks_completed_rate = (
        float(completed_total) / float(total) if total > 0 else 0.0
    )

    components = list_graph_connected_components_v1(session, tenant_id=tenant_id)
    eligible_frontiers = max(1, len(components) if components else 0)
    if not components:
        density = compute_graph_density_metrics_v1(session, tenant_id=tenant_id)
        entity_count = int(density["metrics"].get("entity_count") or 0)
        eligible_frontiers = max(1, min(entity_count, 1) if entity_count else 1)

    traversal_density = float(completed_with_payload) / float(eligible_frontiers)
    traversal_density = max(0.0, min(1.0, traversal_density))

    graph_density = compute_graph_density_metrics_v1(session, tenant_id=tenant_id)
    maturity = str(graph_density.get("graph_maturity_stage") or GRAPH_MATURITY_STAGE_G0_V1)
    threshold = get_traversal_density_operational_alive_threshold_v1()
    operational_alive = False
    if maturity in _GRAPH_G1_PLUS_STAGES_V1:
        operational_alive = traversal_density >= threshold

    return {
        METRIC_WALKS_COMPLETED_RATE_V1: round(walks_completed_rate, 4),
        METRIC_WALKS_PENDING_GAUGE_V1: pending,
        METRIC_TRAVERSAL_DENSITY_SCORE_V1: round(traversal_density, 4),
        "completed_walks_with_payload": completed_with_payload,
        "completed_walks_total": completed_total,
        "eligible_graph_frontiers": eligible_frontiers,
        "walk_records_total": total,
        "operational_alive_threshold": threshold,
        "graph_maturity_stage": maturity,
        "graph_density_score": int(
            graph_density["metrics"].get(METRIC_GRAPH_DENSITY_SCORE_V1) or 0
        ),
        "operational_alive": operational_alive,
    }


def build_traversal_explainability_panel_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    per_walk_limit: int = 32,
) -> dict[str, Any]:
    """Operator panel — answers pending / early termination / replay / graph block (**G-P085-WALK-04**)."""
    store = resolve_octs_walk_store_v1(session)
    snapshot = store.get_tenant_walk_queue_snapshot_v1(tenant_id)
    pending_records = list(snapshot.get("pending_records") or [])
    queue_depth = int(snapshot["pending_count"])

    metrics = compute_traversal_density_metrics_v1(session, tenant_id=tenant_id)
    stall_eval = evaluate_tenant_traversal_stall_v1(session, tenant_id=tenant_id)
    schedule_eval = evaluate_traversal_schedule_v1(session, tenant_id=tenant_id)
    upstream = build_upstream_graph_omissions_for_traversal_v1(session, tenant_id=tenant_id)

    why_pending = explain_why_walks_pending_v1(
        session,
        tenant_id=tenant_id,
        pending_records=pending_records,
        stall_evaluation=stall_eval,
        schedule_evaluation=schedule_eval,
        queue_depth=queue_depth,
    )

    all_records = store.list_walk_records_for_tenant_v1(tenant_id)
    per_walk: list[dict[str, Any]] = []
    lim = max(1, min(int(per_walk_limit), 200))
    for rec in all_records[-lim:]:
        per_walk.append(
            {
                "early_termination": explain_walk_early_termination_v1(rec),
                "replay_posture": explain_walk_replay_posture_v1(
                    session,
                    tenant_id=tenant_id,
                    record=rec,
                ),
            }
        )

    return {
        "gate_id": GP085_WALK04_GATE_ID_V1,
        "related_gate_ids": [
            GP085_WALK01_GATE_ID_V1,
            GP085_WALK03_GATE_ID_V1,
        ],
        "tenant_id": str(tenant_id),
        "computed_at_utc": datetime.now(tz=UTC).isoformat(),
        "metrics": {
            METRIC_WALKS_COMPLETED_RATE_V1: metrics[METRIC_WALKS_COMPLETED_RATE_V1],
            METRIC_WALKS_PENDING_GAUGE_V1: metrics[METRIC_WALKS_PENDING_GAUGE_V1],
            METRIC_TRAVERSAL_DENSITY_SCORE_V1: metrics[METRIC_TRAVERSAL_DENSITY_SCORE_V1],
        },
        "traversal_density_detail": {
            "completed_walks_with_payload": metrics["completed_walks_with_payload"],
            "eligible_graph_frontiers": metrics["eligible_graph_frontiers"],
            "formula": "completed_walks_with_payload / eligible_graph_frontiers",
        },
        "operational_alive": metrics["operational_alive"],
        "operational_alive_threshold": metrics["operational_alive_threshold"],
        "graph_maturity_stage": metrics["graph_maturity_stage"],
        "why_walks_pending": why_pending,
        "upstream_graph_omissions": upstream,
        "stall_evaluation": stall_eval,
        "schedule_evaluation": schedule_eval,
        "per_walk_explanations": per_walk,
    }


def build_substrate_traversal_explainability_catalog_v1() -> dict[str, Any]:
    return {
        "surface_kind": "doctrine_catalog",
        "phase085_traversal_explainability_runtime_schema_version": int(
            PHASE085_TRAVERSAL_EXPLAINABILITY_RUNTIME_SCHEMA_VERSION,
        ),
        "spec_ref": PHASE085_TRAVERSAL_EXPLAINABILITY_SPEC_REF_V1,
        "primary_gate_id": GP085_WALK04_GATE_ID_V1,
        "metric_ids": [
            METRIC_WALKS_COMPLETED_RATE_V1,
            METRIC_WALKS_PENDING_GAUGE_V1,
            METRIC_TRAVERSAL_DENSITY_SCORE_V1,
        ],
        "panel_entrypoint": "build_traversal_explainability_panel_v1",
        "operational_alive_threshold": get_traversal_density_operational_alive_threshold_v1(),
        "runtime_package": (
            "vector.domains.cortex.operational_runtime.substrate_traversal_explainability"
        ),
    }


def verify_gp085_walk04_static() -> dict[str, Any]:
    errors: list[str] = []
    cat = build_substrate_traversal_explainability_catalog_v1()
    if cat["primary_gate_id"] != GP085_WALK04_GATE_ID_V1:
        errors.append("primary_gate_id_mismatch")

    for mid in (
        METRIC_WALKS_COMPLETED_RATE_V1,
        METRIC_WALKS_PENDING_GAUGE_V1,
        METRIC_TRAVERSAL_DENSITY_SCORE_V1,
    ):
        if mid not in cat["metric_ids"]:
            errors.append(f"missing_metric_id:{mid}")

    src = inspect.getsource(build_traversal_explainability_panel_v1)
    if "random" in src.lower():
        errors.append("probabilistic_explainability_forbidden")

    from vector.domains.cortex.operational_runtime import substrate_traversal_scheduling as sts

    sts_src = inspect.getsource(sts.run_octs_walk_schedule_pass_v1)
    if "build_traversal_explainability_panel_v1" not in sts_src:
        errors.append("schedule_pass_missing_explainability_integration")

    panel_keys = set(_EXPLAINABILITY_PANEL_REQUIRED_KEYS_V1)
    for key in panel_keys:
        if key not in src:
            errors.append(f"panel_missing_key:{key}")

    passed = not errors
    return {
        "id": GP085_WALK04_GATE_ID_V1,
        "name": "cesp_substrate_traversal_explainability",
        "passed": passed,
        "severity": "hard_fail",
        "detail": {"errors": errors},
    }
