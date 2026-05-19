"""Phase 08.5 P085-33 — queue pressure governance + density caps (**G-P085-ECON-01**).

Normative: ``DOCS/cortex/operational-runtime/phase-085-runtime-economics-doctrine.md``.
"""

from __future__ import annotations

import inspect
import logging
import uuid
from typing import Any, Final

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from vector.domains.cortex.operational_runtime.graph_density_promotion import (
    count_unpromoted_link_candidates_v1,
    get_promotion_max_per_pass_v1,
)
from vector.domains.cortex.operational_runtime.normative import (
    PHASE085_NORMATIVE_TREE_V1,
)
from vector.domains.cortex.operational_runtime.substrate_tcre_saturation_scheduling import (
    compute_tcre_saturation_metrics_v1,
    get_tcre_saturation_jobs_per_hour_v1,
    get_tcre_saturation_pass_max_jobs_v1,
)
from vector.domains.cortex.operational_runtime.substrate_traversal_scheduling import (
    get_traversal_max_walks_per_pass_v1,
)
from vector.domains.cortex.substrate_pipeline.repository import get_running_pipeline_run_v1
from vector.infrastructure.db.models.cortex_substrate_pipeline_run import (
    CortexSubstratePipelineRun,
)
from vector.settings import Settings, get_settings

_LOGGER = logging.getLogger(__name__)

PHASE085_RUNTIME_ECONOMICS_RUNTIME_SCHEMA_VERSION: Final[int] = 1

PHASE085_RUNTIME_ECONOMICS_SPEC_REF_V1: Final[str] = (
    f"{PHASE085_NORMATIVE_TREE_V1}phase-085-runtime-economics-doctrine.md"
)

GP085_ECON01_GATE_ID_V1: Final[str] = "G-P085-ECON-01"

P085_ECON01_RULE_ID_V1: Final[str] = "P085-ECON-01"

OPERATIONAL_OMISSION_SD_UPSTREAM_CAP_V1: Final[str] = "SD-UPSTREAM-CAP"

VECTOR_CELERY_QUEUE_NAME_V1: Final[str] = "vector"

CELERY_VECTOR_QUEUE_KEY_V1: Final[str] = "vector"


def get_substrate_pipeline_max_concurrent_per_tenant_v1() -> int:
    try:
        return max(1, int(get_settings().cortex_substrate_pipeline_max_concurrent_per_tenant))
    except Exception:  # noqa: BLE001
        return 1


def get_vector_queue_backpressure_threshold_v1() -> int:
    try:
        return max(1, int(get_settings().cortex_vector_queue_backpressure_threshold))
    except Exception:  # noqa: BLE001
        return 64


def get_post_ingestion_backpressure_extra_debounce_seconds_v1() -> int:
    try:
        return max(0, int(get_settings().cortex_post_ingestion_backpressure_extra_debounce_seconds))
    except Exception:  # noqa: BLE001
        return 300


def get_synthesis_pipeline_max_scopes_v1() -> int:
    try:
        return max(1, int(get_settings().cortex_synthesis_pipeline_max_scopes))
    except Exception:  # noqa: BLE001
        return 32


def build_upstream_cap_omission_v1(
    *,
    cap_kind: str,
    detail: str,
    deferred_count: int = 0,
) -> dict[str, Any]:
    """Structured **SD-UPSTREAM-CAP** omission — never silent drop."""
    return {
        "omission_class": OPERATIONAL_OMISSION_SD_UPSTREAM_CAP_V1,
        "cap_kind": cap_kind,
        "detail": detail,
        "deferred_count": int(deferred_count),
    }


def build_runtime_economics_knobs_v1(settings: Settings | None = None) -> dict[str, Any]:
    """Doctrine knob table — live settings values."""
    cfg = settings or get_settings()
    return {
        "CORTEX_SUBSTRATE_PIPELINE_MAX_CONCURRENT_PER_TENANT": int(
            cfg.cortex_substrate_pipeline_max_concurrent_per_tenant
        ),
        "CORTEX_TCRE_SATURATION_JOBS_PER_HOUR": int(cfg.cortex_tcre_saturation_jobs_per_hour),
        "CORTEX_TRAVERSAL_MAX_WALKS_PER_PASS": int(cfg.cortex_traversal_max_walks_per_pass),
        "CORTEX_SYNTHESIS_PIPELINE_MAX_SCOPES": int(cfg.cortex_synthesis_pipeline_max_scopes),
        "CORTEX_GRAPH_DENSITY_PROMOTION_MAX_PER_PASS": int(
            cfg.cortex_graph_density_promotion_max_per_pass
        ),
        "CORTEX_VECTOR_QUEUE_BACKPRESSURE_THRESHOLD": int(
            cfg.cortex_vector_queue_backpressure_threshold
        ),
        "CORTEX_POST_INGESTION_BACKPRESSURE_EXTRA_DEBOUNCE_SECONDS": int(
            cfg.cortex_post_ingestion_backpressure_extra_debounce_seconds
        ),
    }


def _count_tasks_on_vector_queue_v1(inspect_data: dict[str, list[dict[str, Any]]] | None) -> int:
    if not inspect_data:
        return 0
    total = 0
    for tasks in inspect_data.values():
        for task in tasks or []:
            if not isinstance(task, dict):
                continue
            queue = task.get("delivery_info", {}).get("routing_key") if isinstance(
                task.get("delivery_info"), dict
            ) else None
            if queue is None:
                queue = task.get("queue")
            if queue == VECTOR_CELERY_QUEUE_NAME_V1 or queue is None:
                total += 1
    return total


def _redis_vector_queue_depth_v1() -> int | None:
    try:
        import redis

        url = get_settings().redis_url
        if not url:
            return None
        client = redis.from_url(url)  # type: ignore[no-untyped-call]
        return int(client.llen(CELERY_VECTOR_QUEUE_KEY_V1))
    except Exception:  # noqa: BLE001
        return None


def measure_vector_queue_depth_v1(*, timeout: float = 1.5) -> dict[str, Any]:
    """Best-effort depth for the ``vector`` Celery queue (broker + in-flight)."""
    broker_depth = _redis_vector_queue_depth_v1()
    inspect_depth = 0
    inspect_status = "skipped"
    try:
        from app.celery_app import celery_app

        inspect = celery_app.control.inspect(timeout=timeout)
        if inspect is not None:
            active = inspect.active() or {}
            reserved = inspect.reserved() or {}
            scheduled = inspect.scheduled() or {}
            scheduled_requests: dict[str, list[dict[str, Any]]] = {}
            for worker, entries in scheduled.items():
                scheduled_requests[worker] = [
                    entry["request"]
                    for entry in (entries or [])
                    if isinstance(entry, dict) and isinstance(entry.get("request"), dict)
                ]
            inspect_depth = (
                _count_tasks_on_vector_queue_v1(active)
                + _count_tasks_on_vector_queue_v1(reserved)
                + _count_tasks_on_vector_queue_v1(scheduled_requests)
            )
            inspect_status = "ok"
    except Exception as exc:  # noqa: BLE001
        inspect_status = f"error:{type(exc).__name__}"

    if broker_depth is not None:
        depth = int(broker_depth) + int(inspect_depth)
        source = "redis_llen_plus_inspect"
    else:
        depth = int(inspect_depth)
        source = "inspect_only"

    return {
        "queue_name": VECTOR_CELERY_QUEUE_NAME_V1,
        "depth": depth,
        "broker_pending": broker_depth,
        "inspect_inflight": inspect_depth,
        "measurement_source": source,
        "inspect_status": inspect_status,
    }


def evaluate_vector_queue_backpressure_v1(
    settings: Settings | None = None,
) -> dict[str, Any]:
    """Whether post-ingestion refresh countdown should be extended."""
    cfg = settings or get_settings()
    threshold = int(cfg.cortex_vector_queue_backpressure_threshold)
    measured = measure_vector_queue_depth_v1()
    depth = int(measured.get("depth") or 0)
    active = depth > threshold
    return {
        "gate_id": GP085_ECON01_GATE_ID_V1,
        "queue_name": VECTOR_CELERY_QUEUE_NAME_V1,
        "queue_depth": depth,
        "backpressure_threshold": threshold,
        "backpressure_active": active,
        "measurement": measured,
    }


def resolve_post_ingestion_debounce_countdown_v1(
    settings: Settings | None = None,
    *,
    base_debounce_seconds: int | None = None,
) -> dict[str, Any]:
    """Resolve effective debounce for post-ingestion / substrate pipeline schedule."""
    cfg = settings or get_settings()
    base = max(30, int(base_debounce_seconds or cfg.cortex_post_ingestion_substrate_refresh_debounce_seconds))
    bp = evaluate_vector_queue_backpressure_v1(cfg)
    extra = 0
    if bp.get("backpressure_active"):
        extra = get_post_ingestion_backpressure_extra_debounce_seconds_v1()
    effective = base + extra
    return {
        "base_debounce_seconds": base,
        "extra_debounce_seconds": extra,
        "effective_countdown_seconds": effective,
        "backpressure": bp,
    }


def count_running_substrate_pipelines_v1(session: Session, *, tenant_id: uuid.UUID) -> int:
    return int(
        session.scalar(
            select(func.count())
            .select_from(CortexSubstratePipelineRun)
            .where(
                CortexSubstratePipelineRun.tenant_id == tenant_id,
                CortexSubstratePipelineRun.status == "running",
            )
        )
        or 0
    )


def evaluate_pipeline_concurrency_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
) -> dict[str, Any]:
    """**G-P085-ECON-01** — per-tenant pipeline overlap law."""
    max_concurrent = get_substrate_pipeline_max_concurrent_per_tenant_v1()
    running_count = count_running_substrate_pipelines_v1(session, tenant_id=tenant_id)
    existing = get_running_pipeline_run_v1(session, tenant_id=tenant_id)
    may_start = running_count < max_concurrent
    block_reason: str | None = None
    if not may_start:
        block_reason = "max_concurrent_pipelines_per_tenant"
    return {
        "gate_id": GP085_ECON01_GATE_ID_V1,
        "tenant_id": str(tenant_id),
        "max_concurrent_per_tenant": max_concurrent,
        "running_pipeline_count": running_count,
        "may_start_pipeline": may_start,
        "block_reason": block_reason,
        "running_pipeline_run_id": str(existing.id) if existing is not None else None,
    }


def evaluate_tenant_density_caps_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
) -> dict[str, Any]:
    """Snapshot density scheduler caps vs current utilization."""
    tcre = compute_tcre_saturation_metrics_v1(session, tenant_id=tenant_id)
    unpromoted = count_unpromoted_link_candidates_v1(session, tenant_id=tenant_id)
    jobs_hour = int(tcre.get("jobs_enqueued_last_hour") or 0)
    jobs_per_hour_cap = get_tcre_saturation_jobs_per_hour_v1()
    return {
        "gate_id": GP085_ECON01_GATE_ID_V1,
        "tenant_id": str(tenant_id),
        "knobs": build_runtime_economics_knobs_v1(),
        "tcre": {
            "jobs_enqueued_last_hour": jobs_hour,
            "jobs_per_hour_cap": jobs_per_hour_cap,
            "hourly_budget_remaining": max(0, jobs_per_hour_cap - jobs_hour),
            "pass_max_jobs": get_tcre_saturation_pass_max_jobs_v1(),
            "queued_running_jobs": int(tcre.get("queued_running_jobs") or 0),
            "hourly_cap_hit": jobs_hour >= jobs_per_hour_cap,
        },
        "traversal": {
            "max_walks_per_pass": get_traversal_max_walks_per_pass_v1(),
        },
        "synthesis": {
            "max_scopes_per_pass": get_synthesis_pipeline_max_scopes_v1(),
        },
        "graph_promotion": {
            "max_per_pass": get_promotion_max_per_pass_v1(),
            "unpromoted_candidates": unpromoted,
        },
    }


def build_runtime_economics_card_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
) -> dict[str, Any]:
    """Tenant runtime economics card for admin."""
    bp = evaluate_vector_queue_backpressure_v1()
    concurrency = evaluate_pipeline_concurrency_v1(session, tenant_id=tenant_id)
    caps = evaluate_tenant_density_caps_v1(session, tenant_id=tenant_id)
    debounce = resolve_post_ingestion_debounce_countdown_v1()
    return {
        "surface_kind": "runtime_economics_card",
        "gate_id": GP085_ECON01_GATE_ID_V1,
        "tenant_id": str(tenant_id),
        "knobs": caps["knobs"],
        "queue_backpressure": bp,
        "pipeline_concurrency": concurrency,
        "density_caps": caps,
        "post_ingestion_debounce": debounce,
    }


def build_substrate_runtime_economics_catalog_v1() -> dict[str, Any]:
    return {
        "surface_kind": "doctrine_catalog",
        "phase085_runtime_economics_runtime_schema_version": int(
            PHASE085_RUNTIME_ECONOMICS_RUNTIME_SCHEMA_VERSION,
        ),
        "spec_ref": PHASE085_RUNTIME_ECONOMICS_SPEC_REF_V1,
        "primary_gate_id": GP085_ECON01_GATE_ID_V1,
        "omission_class_upstream_cap": OPERATIONAL_OMISSION_SD_UPSTREAM_CAP_V1,
        "knobs": build_runtime_economics_knobs_v1(),
        "evaluation_entrypoints": [
            "evaluate_vector_queue_backpressure_v1",
            "resolve_post_ingestion_debounce_countdown_v1",
            "evaluate_pipeline_concurrency_v1",
            "evaluate_tenant_density_caps_v1",
        ],
        "runtime_package": "vector.domains.cortex.operational_runtime.substrate_runtime_economics",
    }


def verify_gp085_econ01_static() -> dict[str, Any]:
    errors: list[str] = []
    cat = build_substrate_runtime_economics_catalog_v1()
    if cat["primary_gate_id"] != GP085_ECON01_GATE_ID_V1:
        errors.append("primary_gate_id_mismatch")
    knobs = build_runtime_economics_knobs_v1()
    if int(knobs["CORTEX_SUBSTRATE_PIPELINE_MAX_CONCURRENT_PER_TENANT"]) < 1:
        errors.append("invalid_max_concurrent")

    from vector.domains.cortex.substrate_pipeline import orchestrator as orch

    sched_src = inspect.getsource(orch.schedule_substrate_pipeline_v1)
    if "resolve_post_ingestion_debounce_countdown_v1" not in sched_src:
        errors.append("orchestrator_missing_backpressure_debounce")
    if "evaluate_pipeline_concurrency_v1" not in sched_src:
        errors.append("orchestrator_missing_concurrency_check")

    from vector.domains.cortex.ingestion import post_ingestion_refresh_dispatch as pid

    dispatch_src = inspect.getsource(pid.schedule_post_ingestion_substrate_refresh)
    if "schedule_substrate_pipeline_v1" not in dispatch_src and "mark_tenant_dirty_v1" not in dispatch_src:
        errors.append("post_ingestion_dispatch_not_wired")

    passed = not errors
    return {
        "id": GP085_ECON01_GATE_ID_V1,
        "name": "cesp_substrate_runtime_economics",
        "passed": passed,
        "severity": "hard_fail",
        "detail": {"errors": errors},
    }
