"""Phase B step B6 — fresh post-ingestion pipeline run after graph change (no eternal mirror)."""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any, Final

from sqlalchemy import select
from sqlalchemy.orm import Session

from vector.domains.cortex.execution.lease import get_tenant_execution_lease_v1
from vector.domains.cortex.substrate_pipeline.constants import (
    GRAPH_CHANGE_FRESH_PHASES_V1,
    PHASE_03_IDENTITY,
    PIPELINE_STATUS_PARTIAL,
    PIPELINE_STATUS_RUNNING,
    PIPELINE_TRIGGER_GRAPH_HASH_CHANGED,
    PIPELINE_TRIGGER_POST_INGESTION,
)
from vector.domains.cortex.substrate_pipeline.continuity_p0_recovery import (
    requeue_pipeline_phases_from_v1,
)
from vector.domains.cortex.substrate_pipeline.repository import (
    compute_pipeline_idempotency_key_v1,
    create_pipeline_run_v1,
    get_running_pipeline_run_v1,
    mark_pipeline_running_v1,
)
from vector.infrastructure.db.models.cortex_substrate_pipeline_run import CortexSubstratePipelineRun

_LOGGER = logging.getLogger(__name__)

POST_INGESTION_FRESH_RUN_SCHEMA_VERSION: Final[int] = 1
P0_B6_STEP: Final[str] = "step_b6_post_ingestion_fresh_pipeline_run"
SUPERSEDE_REASON_GRAPH_HASH_CHANGED_V1: Final[str] = "graph_hash_changed_fresh_run_b6"


def is_post_ingestion_fresh_run_on_graph_change_enabled_v1() -> bool:
    try:
        from vector.settings import get_settings

        return bool(get_settings().cortex_post_ingestion_fresh_run_on_graph_change_enabled)
    except Exception:  # noqa: BLE001
        return True


def supersede_pipeline_run_for_graph_change_v1(
    session: Session,
    *,
    pipeline_run_id: uuid.UUID,
    superseded_by_pipeline_run_id: uuid.UUID | None = None,
    reason: str = SUPERSEDE_REASON_GRAPH_HASH_CHANGED_V1,
) -> dict[str, Any]:
    """Mark a running pipeline partial so a fresh run can own phases 03–05 (B6)."""
    run = session.get(CortexSubstratePipelineRun, pipeline_run_id)
    if run is None:
        return {"superseded": False, "reason": "pipeline_run_not_found"}
    if run.status != PIPELINE_STATUS_RUNNING:
        return {
            "superseded": False,
            "reason": "pipeline_not_running",
            "status": run.status,
        }
    summary = dict(run.summary_json or {})
    summary.update(
        {
            "superseded": True,
            "superseded_reason": reason,
            "superseded_at": datetime.now(UTC).isoformat(),
            "superseded_by_pipeline_run_id": (
                str(superseded_by_pipeline_run_id) if superseded_by_pipeline_run_id else None
            ),
            "b6_fresh_run": True,
        }
    )
    run.summary_json = summary
    run.status = PIPELINE_STATUS_PARTIAL
    run.completed_at = datetime.now(UTC)
    run.current_phase_id = None
    session.flush()
    return {
        "superseded": True,
        "pipeline_run_id": str(pipeline_run_id),
        "superseded_by_pipeline_run_id": (
            str(superseded_by_pipeline_run_id) if superseded_by_pipeline_run_id else None
        ),
        "reason": reason,
    }


def start_fresh_pipeline_run_after_graph_change_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    graph_projection_stable_hash: str,
    prior_pipeline_run_id: uuid.UUID | None = None,
    trigger_kind: str = PIPELINE_TRIGGER_GRAPH_HASH_CHANGED,
    bundle_id: str | None = None,
) -> dict[str, Any]:
    """
    Create a new pipeline run keyed to the graph hash; supersede prior running run(s).

    Does **not** mirror completed phases from the prior run (B6 — fresh 03/04/05 receipts).
    """
    if not is_post_ingestion_fresh_run_on_graph_change_enabled_v1():
        return {
            "started": False,
            "reason": "fresh_run_on_graph_change_disabled",
            "fresh_pipeline_run_id": (
                str(prior_pipeline_run_id) if prior_pipeline_run_id is not None else None
            ),
        }

    graph_hash = (graph_projection_stable_hash or "").strip()
    if not graph_hash:
        return {"started": False, "reason": "missing_graph_hash"}

    superseded_ids: list[str] = []
    if prior_pipeline_run_id is not None:
        sup = supersede_pipeline_run_for_graph_change_v1(
            session,
            pipeline_run_id=prior_pipeline_run_id,
            reason=SUPERSEDE_REASON_GRAPH_HASH_CHANGED_V1,
        )
        if sup.get("superseded"):
            superseded_ids.append(str(prior_pipeline_run_id))

    running = get_running_pipeline_run_v1(session, tenant_id=tenant_id)
    if running is not None and str(running.id) not in superseded_ids:
        sup = supersede_pipeline_run_for_graph_change_v1(
            session,
            pipeline_run_id=running.id,
            reason=SUPERSEDE_REASON_GRAPH_HASH_CHANGED_V1,
        )
        if sup.get("superseded"):
            superseded_ids.append(str(running.id))

    idem = compute_pipeline_idempotency_key_v1(
        tenant_id=tenant_id,
        trigger_kind=trigger_kind,
        ingestion_epoch=graph_hash[:32],
    )
    run = create_pipeline_run_v1(
        session,
        tenant_id=tenant_id,
        trigger_kind=trigger_kind,
        bundle_id=bundle_id,
        idempotency_key=idem,
        allow_coalesce_running=False,
    )
    created = True
    mark_pipeline_running_v1(session, run)
    run.current_phase_id = PHASE_03_IDENTITY
    requeue_pipeline_phases_from_v1(
        session,
        pipeline_run_id=run.id,
        from_phase_id=PHASE_03_IDENTITY,
        clear_outputs=True,
    )
    summary = dict(run.summary_json or {})
    summary.update(
        {
            "b6_fresh_run": True,
            "graph_projection_stable_hash_sha256": graph_hash,
            "supersedes_pipeline_run_ids": superseded_ids,
            "no_phase_mirror": True,
        }
    )
    run.summary_json = summary
    session.flush()

    lease = get_tenant_execution_lease_v1(session, tenant_id=tenant_id)
    if lease is not None:
        lease.pipeline_run_id = run.id
        lease.phase_cursor = PHASE_03_IDENTITY
        session.flush()

    _LOGGER.info(
        "b6_fresh_pipeline_run tenant_id=%s fresh_run_id=%s superseded=%s graph_hash=%s",
        tenant_id,
        run.id,
        superseded_ids,
        graph_hash[:12],
    )
    return {
        "started": True,
        "fresh_pipeline_run_id": str(run.id),
        "fresh_pipeline_run_created": created,
        "superseded_pipeline_run_ids": superseded_ids,
        "trigger_kind": trigger_kind,
        "graph_projection_stable_hash_sha256": graph_hash,
        "resume_from_phase": PHASE_03_IDENTITY,
        "no_phase_mirror": True,
        "post_ingestion_fresh_run_schema_version": POST_INGESTION_FRESH_RUN_SCHEMA_VERSION,
    }


def resolve_pipeline_run_id_after_phase04_v1(
    phase04_output: dict[str, Any],
    *,
    current_pipeline_run_id: uuid.UUID,
) -> tuple[uuid.UUID, dict[str, Any]]:
    """Return execution pipeline run id; rewind to phase 03 when B6 fresh run was started."""
    trigger = dict(phase04_output.get("event_trigger_graph_hash") or {})
    fresh_raw = trigger.get("fresh_pipeline_run_id")
    if not fresh_raw:
        return current_pipeline_run_id, {
            "switched": False,
            "pipeline_run_id": str(current_pipeline_run_id),
        }
    fresh_id = uuid.UUID(str(fresh_raw))
    return fresh_id, {
        "switched": True,
        "pipeline_run_id": str(fresh_id),
        "superseded_pipeline_run_ids": list(trigger.get("superseded_pipeline_run_ids") or []),
        "resume_from_phase": trigger.get("resume_from_phase") or PHASE_03_IDENTITY,
    }


def find_fresh_graph_change_pipeline_runs_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    lookback_hours: int = 168,
    limit: int = 12,
) -> list[dict[str, Any]]:
    """SQL evidence: recent runs with fresh 03–05 ``started_at`` after graph-change supersede."""
    cutoff = datetime.now(UTC) - timedelta(hours=lookback_hours)
    runs = list(
        session.scalars(
            select(CortexSubstratePipelineRun)
            .where(
                CortexSubstratePipelineRun.tenant_id == tenant_id,
                CortexSubstratePipelineRun.trigger_kind.in_(
                    (PIPELINE_TRIGGER_GRAPH_HASH_CHANGED, PIPELINE_TRIGGER_POST_INGESTION)
                ),
            )
            .order_by(CortexSubstratePipelineRun.created_at.desc())
            .limit(limit * 4)
        ).all()
    )
    from vector.domains.cortex.substrate_pipeline.repository import get_phase_run_v1

    evidence: list[dict[str, Any]] = []
    for run in runs:
        if run.created_at is not None and run.created_at < cutoff:
            continue
        summary = dict(run.summary_json or {})
        if not summary.get("b6_fresh_run") and not summary.get("no_phase_mirror"):
            if run.trigger_kind != PIPELINE_TRIGGER_GRAPH_HASH_CHANGED:
                continue
        phase_started: dict[str, str | None] = {}
        fresh_ok = True
        for phase_id in GRAPH_CHANGE_FRESH_PHASES_V1:
            pr = get_phase_run_v1(session, pipeline_run_id=run.id, phase_id=phase_id)
            if pr is None or pr.started_at is None:
                fresh_ok = False
                break
            phase_started[phase_id] = pr.started_at.isoformat()
            if run.created_at is not None and pr.started_at < run.created_at:
                fresh_ok = False
        if not fresh_ok:
            continue
        evidence.append(
            {
                "pipeline_run_id": str(run.id),
                "trigger_kind": run.trigger_kind,
                "created_at": run.created_at.isoformat() if run.created_at else None,
                "status": run.status,
                "supersedes_pipeline_run_ids": summary.get("supersedes_pipeline_run_ids") or [],
                "no_phase_mirror": bool(summary.get("no_phase_mirror")),
                "phase_started_at": phase_started,
                "fresh_phases_ok": True,
            }
        )
        if len(evidence) >= limit:
            break
    return evidence
