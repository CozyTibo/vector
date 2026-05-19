"""Phase 08.5 P085-14 — automatic OCTS walk scheduling (**G-P085-WALK-01**).

Normative: ``DOCS/cortex/operational-runtime/phase-085-traversal-completion-doctrine.md`` §Automatic walk scheduling.
"""

from __future__ import annotations

import inspect
import uuid
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
from vector.domains.cortex.substrate_pipeline.substrate_traversal_execution import (
    run_substrate_traversal_materialization_v1,
)

PHASE085_TRAVERSAL_SCHEDULING_RUNTIME_SCHEMA_VERSION: Final[int] = 1

PHASE085_TRAVERSAL_SCHEDULING_SPEC_REF_V1: Final[str] = (
    f"{PHASE085_NORMATIVE_TREE_V1}phase-085-traversal-completion-doctrine.md"
)

GP085_WALK01_GATE_ID_V1: Final[str] = "G-P085-WALK-01"

CELERY_TRAVERSAL_SCHEDULE_TASK_NAME_V1: Final[str] = (
    "vector.cortex.operational_runtime.schedule_octs_walks_for_tenant"
)

TRAVERSAL_SCHEDULE_TRIGGER_AFTER_PHASE_05_V1: Final[str] = "after_phase_05"
TRAVERSAL_SCHEDULE_TRIGGER_GRAPH_G1_V1: Final[str] = "graph_density_g1"
TRAVERSAL_SCHEDULE_TRIGGER_MANUAL_V1: Final[str] = "manual"

WAITING_ON_TRAVERSAL_COMPLETION_V1: Final[str] = "TRAVERSAL_COMPLETION"

_GRAPH_MATURITY_SCHEDULE_ELIGIBLE_V1: Final[frozenset[str]] = frozenset(
    {
        GRAPH_MATURITY_STAGE_G1_V1,
        GRAPH_MATURITY_STAGE_G2_V1,
        GRAPH_MATURITY_STAGE_G3_V1,
    }
)


class SubstrateTraversalSchedulingError(ValueError):
    def __init__(self, code: str, *, detail: dict[str, Any] | None = None) -> None:
        self.code = code
        self.detail = dict(detail or {})
        super().__init__(code)


def get_traversal_max_walks_per_pass_v1() -> int:
    try:
        from vector.settings import get_settings

        return max(1, int(get_settings().cortex_traversal_max_walks_per_pass))
    except Exception:  # noqa: BLE001
        return 32


def get_traversal_schedule_countdown_seconds_v1() -> int:
    try:
        from vector.settings import get_settings

        return max(0, int(get_settings().cortex_traversal_schedule_countdown_seconds))
    except Exception:  # noqa: BLE001
        return 5


def get_traversal_queue_saturation_threshold_v1() -> int:
    try:
        from vector.settings import get_settings

        return max(1, int(get_settings().cortex_traversal_queue_saturation_threshold))
    except Exception:  # noqa: BLE001
        return 64


def _is_traversal_propagation_blocked_v1(
    *,
    linked_entity_count: int,
    entity_count: int,
    orphan_disconnected_count: int,
    orphan_identity_unresolved_count: int,
) -> bool:
    if orphan_identity_unresolved_count > 0:
        return True
    if orphan_disconnected_count > 0 and linked_entity_count > 0:
        return True
    if entity_count > 0 and linked_entity_count == 0:
        return True
    return False


def rank_walk_frontiers_by_density_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    limit: int,
) -> tuple[list[str], dict[str, Any]]:
    """Pick start node ids from highest-density connected components (deterministic)."""
    density = compute_graph_density_metrics_v1(session, tenant_id=tenant_id)
    dm = dict(density["metrics"])
    tenant_density_score = int(dm.get(METRIC_GRAPH_DENSITY_SCORE_V1) or 0)
    components = list_graph_connected_components_v1(session, tenant_id=tenant_id)

    ranked: list[tuple[int, int, str]] = []
    if components:
        for comp in components:
            rep = str(min(comp, key=lambda x: str(x)))
            ranked.append((len(comp), tenant_density_score, rep))
        ranked.sort(key=lambda t: (-t[0], -t[1], t[2]))
    else:
        from vector.domains.cortex.identity.projection_export import (
            build_org_graph_projection_export_document,
        )

        export_doc = build_org_graph_projection_export_document(session, tenant_id=tenant_id)
        inner = export_doc.get("projection")
        if isinstance(inner, dict):
            nodes = inner.get("nodes")
            if isinstance(nodes, list):
                for node in nodes:
                    if not isinstance(node, dict):
                        continue
                    if str(node.get("kind")) != "org_entity":
                        continue
                    nid = str(node.get("id") or "").strip()
                    if nid:
                        ranked.append((1, tenant_density_score, nid))

    cap = max(1, min(int(limit), 500))
    starts = [rep for _size, _score, rep in ranked[:cap]]
    meta = {
        "graph_maturity_stage": density.get("graph_maturity_stage"),
        "graph_density_score": tenant_density_score,
        "connected_component_count": len(components),
        "frontier_candidates": len(ranked),
        "selected_start_count": len(starts),
    }
    return starts, meta


def evaluate_traversal_schedule_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    trigger: str | None = None,
) -> dict[str, Any]:
    """Whether to enqueue ``schedule_octs_walks_for_tenant_v1``."""
    from vector.domains.cortex.traversal.runtime.durable_walk_store import (
        resolve_octs_walk_store_v1,
    )

    density = compute_graph_density_metrics_v1(session, tenant_id=tenant_id)
    dm = dict(density["metrics"])
    entity_count = int(dm.get("entity_count") or 0)
    linked = int(dm.get("linked_entity_count") or 0)
    maturity = str(density.get("graph_maturity_stage") or GRAPH_MATURITY_STAGE_G0_V1)

    orphan_cls = classify_tenant_graph_orphans_v1(session, tenant_id=tenant_id, sample_limit=0)
    counts = dict(orphan_cls.get("counts_by_class") or {})
    disconnected = int(counts.get(ORPHAN_CLASS_DISCONNECTED_COMPONENT_V1, 0))
    identity_unresolved = int(counts.get(ORPHAN_CLASS_IDENTITY_UNRESOLVED_V1, 0))

    blocked = _is_traversal_propagation_blocked_v1(
        linked_entity_count=linked,
        entity_count=entity_count,
        orphan_disconnected_count=disconnected,
        orphan_identity_unresolved_count=identity_unresolved,
    )

    store = resolve_octs_walk_store_v1(session)
    queue_depth = int(store.walk_queue_depth_for_tenant(tenant_id))

    trig = (trigger or "").strip()
    if blocked:
        should = False
        reason = "traversal_propagation_blocked"
    elif queue_depth >= get_traversal_queue_saturation_threshold_v1():
        should = False
        reason = "walk_queue_saturated"
    elif trig == TRAVERSAL_SCHEDULE_TRIGGER_AFTER_PHASE_05_V1:
        should = entity_count > 0 and (linked > 0 or maturity in _GRAPH_MATURITY_SCHEDULE_ELIGIBLE_V1)
        reason = "after_phase_05_eligible" if should else "after_phase_05_not_eligible"
    elif maturity in _GRAPH_MATURITY_SCHEDULE_ELIGIBLE_V1 and entity_count > 0:
        should = True
        reason = TRAVERSAL_SCHEDULE_TRIGGER_GRAPH_G1_V1
    else:
        should = False
        reason = "graph_below_g1_or_empty"

    return {
        "tenant_id": str(tenant_id),
        "gate_id": GP085_WALK01_GATE_ID_V1,
        "should_schedule": should,
        "schedule_reason": reason,
        "trigger": trig or None,
        "graph_maturity_stage": maturity,
        "graph_density_score": int(dm.get(METRIC_GRAPH_DENSITY_SCORE_V1) or 0),
        "entity_count": entity_count,
        "linked_entity_count": linked,
        "walk_queue_depth": queue_depth,
        "traversal_propagation_blocked": blocked,
    }


def run_octs_walk_schedule_pass_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    trigger: str = TRAVERSAL_SCHEDULE_TRIGGER_MANUAL_V1,
    pipeline_run_id: uuid.UUID | None = None,
    graph_projection_stable_hash: str | None = None,
    max_walks: int | None = None,
) -> dict[str, Any]:
    """Bounded OCTS walk fanout with density-prioritized frontiers (**G-P085-WALK-01**)."""
    cap = max_walks if max_walks is not None else get_traversal_max_walks_per_pass_v1()
    starts, frontier_meta = rank_walk_frontiers_by_density_v1(
        session,
        tenant_id=tenant_id,
        limit=cap,
    )
    if not starts:
        return {
            "gate_id": GP085_WALK01_GATE_ID_V1,
            "trigger": trigger,
            "scheduled": False,
            "reason": "no_walk_frontiers",
            "frontier_meta": frontier_meta,
        }

    materialized = run_substrate_traversal_materialization_v1(
        session,
        tenant_id=tenant_id,
        graph_projection_stable_hash=graph_projection_stable_hash,
        max_starts=cap,
        start_node_ids=starts,
    )

    from vector.domains.cortex.operational_runtime.substrate_traversal_retry import (
        run_traversal_retry_and_heal_pass_v1,
    )

    retry_pass = run_traversal_retry_and_heal_pass_v1(session, tenant_id=tenant_id)

    from vector.domains.cortex.operational_runtime.substrate_stalled_traversal_recovery import (
        run_stalled_traversal_recovery_pass_v1,
    )

    stall_recovery_pass = run_stalled_traversal_recovery_pass_v1(session, tenant_id=tenant_id)

    from vector.domains.cortex.operational_runtime.substrate_traversal_explainability import (
        build_traversal_explainability_panel_v1,
    )

    explainability_panel = build_traversal_explainability_panel_v1(session, tenant_id=tenant_id)

    return {
        "gate_id": GP085_WALK01_GATE_ID_V1,
        "trigger": trigger,
        "scheduled": True,
        "max_walks_per_pass": cap,
        "frontier_meta": frontier_meta,
        "selected_start_node_ids": starts,
        "materialization": materialized,
        "traversal_retry_pass": retry_pass,
        "stalled_traversal_recovery_pass": stall_recovery_pass,
        "traversal_explainability_panel": explainability_panel,
        "pipeline_run_id": str(pipeline_run_id) if pipeline_run_id else None,
    }


def schedule_octs_walks_for_tenant_v1(
    *,
    tenant_id: uuid.UUID,
    trigger: str = TRAVERSAL_SCHEDULE_TRIGGER_GRAPH_G1_V1,
    pipeline_run_id: uuid.UUID | None = None,
    graph_projection_stable_hash: str | None = None,
    countdown: int | None = None,
    force: bool = False,
) -> dict[str, Any]:
    """Enqueue async OCTS walk scheduling pass (after phase 05 or graph ≥ G1)."""
    from vector.infrastructure.db.session import session_scope

    with session_scope() as session:
        eval_out = evaluate_traversal_schedule_v1(
            session,
            tenant_id=tenant_id,
            trigger=trigger,
        )
    if not force and not eval_out.get("should_schedule"):
        return {
            "scheduled": False,
            "reason": eval_out.get("schedule_reason"),
            "evaluation": eval_out,
        }

    cd = countdown if countdown is not None else get_traversal_schedule_countdown_seconds_v1()
    from app.tasks.cortex_substrate_traversal_scheduling import (
        run_octs_walk_schedule_pass_task,
    )

    async_result = run_octs_walk_schedule_pass_task.apply_async(
        kwargs={
            "tenant_id": str(tenant_id),
            "trigger": trigger,
            "pipeline_run_id": str(pipeline_run_id) if pipeline_run_id else None,
            "graph_projection_stable_hash": graph_projection_stable_hash,
        },
        queue="vector",
        countdown=max(0, int(cd)),
    )

    out: dict[str, Any] = {
        "scheduled": True,
        "celery_task_id": async_result.id,
        "task_name": CELERY_TRAVERSAL_SCHEDULE_TASK_NAME_V1,
        "countdown_seconds": cd,
        "trigger": trigger,
        "evaluation": eval_out,
    }
    if pipeline_run_id is not None:
        from vector.infrastructure.db.session import session_scope
        from vector.domains.cortex.substrate_pipeline.pipeline_continuation import (
            mark_pipeline_waiting_on_traversal_v1,
        )

        with session_scope() as session:
            cont = mark_pipeline_waiting_on_traversal_v1(
                session,
                tenant_id=tenant_id,
                pipeline_run_id=pipeline_run_id,
                walk_batch_id=uuid.uuid4(),
                celery_task_id=async_result.id,
                scheduled_start_count=0,
            )
            session.commit()
        out["continuation"] = {
            "continuation_id": str(cont.id),
            "waiting_on": WAITING_ON_TRAVERSAL_COMPLETION_V1,
        }
    return out


def build_substrate_traversal_scheduling_catalog_v1() -> dict[str, Any]:
    return {
        "surface_kind": "doctrine_catalog",
        "phase085_traversal_scheduling_runtime_schema_version": int(
            PHASE085_TRAVERSAL_SCHEDULING_RUNTIME_SCHEMA_VERSION,
        ),
        "spec_ref": PHASE085_TRAVERSAL_SCHEDULING_SPEC_REF_V1,
        "primary_gate_id": GP085_WALK01_GATE_ID_V1,
        "celery_task_name": CELERY_TRAVERSAL_SCHEDULE_TASK_NAME_V1,
        "scheduler_entrypoint": "schedule_octs_walks_for_tenant_v1",
        "pass_entrypoint": "run_octs_walk_schedule_pass_v1",
        "waiting_on_kind": WAITING_ON_TRAVERSAL_COMPLETION_V1,
        "max_walks_per_pass": get_traversal_max_walks_per_pass_v1(),
        "queue_saturation_threshold": get_traversal_queue_saturation_threshold_v1(),
        "schedule_triggers": [
            TRAVERSAL_SCHEDULE_TRIGGER_AFTER_PHASE_05_V1,
            TRAVERSAL_SCHEDULE_TRIGGER_GRAPH_G1_V1,
            TRAVERSAL_SCHEDULE_TRIGGER_MANUAL_V1,
        ],
        "runtime_package": "vector.domains.cortex.operational_runtime.substrate_traversal_scheduling",
    }


def verify_gp085_walk01_static() -> dict[str, Any]:
    errors: list[str] = []
    cat = build_substrate_traversal_scheduling_catalog_v1()
    if cat["scheduler_entrypoint"] != "schedule_octs_walks_for_tenant_v1":
        errors.append("scheduler_entrypoint_mismatch")

    src = inspect.getsource(rank_walk_frontiers_by_density_v1)
    if "random" in src.lower():
        errors.append("probabilistic_scheduling_forbidden")

    from vector.domains.cortex.substrate_pipeline import phase_runners as pr

    pr_src = inspect.getsource(pr.run_phase_05_traversal_v1)
    if "schedule_octs_walks_for_tenant_v1" not in pr_src:
        errors.append("phase_05_missing_schedule_octs_walks")

    ste_src = inspect.getsource(run_substrate_traversal_materialization_v1)
    if "start_node_ids" not in ste_src:
        errors.append("substrate_traversal_missing_start_node_ids_override")

    try:
        from app.celery_app import celery_app

        if CELERY_TRAVERSAL_SCHEDULE_TASK_NAME_V1 not in celery_app.tasks:
            import importlib

            importlib.import_module("app.tasks.cortex_substrate_traversal_scheduling")
        if CELERY_TRAVERSAL_SCHEDULE_TASK_NAME_V1 not in celery_app.tasks:
            errors.append("celery_task_not_registered")
    except Exception as exc:  # noqa: BLE001
        errors.append(f"celery_import:{exc}")

    passed = not errors
    return {
        "id": GP085_WALK01_GATE_ID_V1,
        "name": "cesp_substrate_traversal_scheduling",
        "passed": passed,
        "severity": "hard_fail",
        "detail": {"errors": errors},
    }
