"""Async OCTS walk scheduling (**G-P085-WALK-01**)."""

from __future__ import annotations

import logging
import uuid
from typing import Any

from app.celery_app import celery_app
from vector.domains.cortex.operational_runtime.substrate_traversal_scheduling import (
    CELERY_TRAVERSAL_SCHEDULE_TASK_NAME_V1,
    run_octs_walk_schedule_pass_v1,
)
from vector.infrastructure.db.session import session_scope

_LOGGER = logging.getLogger("app")

_TASK = CELERY_TRAVERSAL_SCHEDULE_TASK_NAME_V1


@celery_app.task(name=_TASK, queue="vector")
def run_octs_walk_schedule_pass_task(
    *,
    tenant_id: str,
    trigger: str = "manual",
    pipeline_run_id: str | None = None,
    graph_projection_stable_hash: str | None = None,
) -> dict[str, Any]:
    tid = uuid.UUID(str(tenant_id))
    prid = uuid.UUID(str(pipeline_run_id)) if pipeline_run_id else None
    _LOGGER.info(
        "octs_walk_schedule_pass_start tenant_id=%s trigger=%s task=%s",
        tid,
        trigger,
        _TASK,
    )
    with session_scope() as session:
        out = run_octs_walk_schedule_pass_v1(
            session,
            tenant_id=tid,
            trigger=trigger,
            pipeline_run_id=prid,
            graph_projection_stable_hash=graph_projection_stable_hash,
        )
        if prid is not None:
            from vector.domains.cortex.operational_runtime.substrate_operational_progression import (
                PROGRESSION_TRIGGER_TRAVERSAL_PASS_V1,
                continue_substrate_operational_progression_v1,
            )

            out["progression"] = continue_substrate_operational_progression_v1(
                session,
                tenant_id=tid,
                pipeline_run_id=prid,
                trigger=PROGRESSION_TRIGGER_TRAVERSAL_PASS_V1,
            )
        session.commit()
    _LOGGER.info(
        "octs_walk_schedule_pass_done tenant_id=%s walks_persisted=%s",
        tid,
        (out.get("materialization") or {}).get("walks_persisted"),
    )
    return out
