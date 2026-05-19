"""Async TCRE saturation schedule pass (**G-P085-TCRE-01**)."""

from __future__ import annotations

import logging
import uuid
from typing import Any

from app.celery_app import celery_app
from vector.domains.cortex.operational_runtime.substrate_tcre_saturation_scheduling import (
    CELERY_TCRE_SATURATION_SCHEDULE_TASK_NAME_V1,
    run_tcre_saturation_schedule_pass_v1,
)
from vector.infrastructure.db.session import session_scope

_LOGGER = logging.getLogger("app")

_TASK = CELERY_TCRE_SATURATION_SCHEDULE_TASK_NAME_V1


@celery_app.task(name=_TASK, queue="vector")
def run_tcre_saturation_schedule_pass_task(
    *,
    tenant_id: str,
    pipeline_run_id: str | None = None,
    octs_walk_id: str | None = None,
    trigger: str = "manual",
    force: bool = False,
) -> dict[str, Any]:
    tid = uuid.UUID(str(tenant_id))
    prid = uuid.UUID(str(pipeline_run_id)) if pipeline_run_id else None
    _LOGGER.info(
        "tcre_saturation_schedule_pass_start tenant_id=%s pipeline_run_id=%s task=%s",
        tid,
        prid,
        _TASK,
    )
    with session_scope() as session:
        out = run_tcre_saturation_schedule_pass_v1(
            session,
            tenant_id=tid,
            pipeline_run_id=prid,
            octs_walk_id=octs_walk_id,
            trigger=trigger,
            skip_if_saturated=not force,
        )
        session.commit()
    _LOGGER.info(
        "tcre_saturation_schedule_pass_done tenant_id=%s jobs_enqueued=%s",
        tid,
        out.get("jobs_enqueued"),
    )
    return out
