"""Async synthesis activation schedule pass (**G-P085-SYN-01**)."""

from __future__ import annotations

import logging
import uuid
from typing import Any

from app.celery_app import celery_app
from vector.domains.cortex.operational_runtime.substrate_synthesis_activation_scheduling import (
    CELERY_SYNTHESIS_ACTIVATION_SCHEDULE_TASK_NAME_V1,
    run_synthesis_activation_schedule_pass_v1,
)
from vector.infrastructure.db.session import session_scope

_LOGGER = logging.getLogger("app")

_TASK = CELERY_SYNTHESIS_ACTIVATION_SCHEDULE_TASK_NAME_V1


@celery_app.task(name=_TASK, queue="vector")
def run_synthesis_activation_schedule_pass_task(
    *,
    tenant_id: str,
    pipeline_run_id: str | None = None,
    published_index_epoch: str | None = None,
    trigger: str = "manual",
    force: bool = False,
) -> dict[str, Any]:
    tid = uuid.UUID(str(tenant_id))
    prid = uuid.UUID(str(pipeline_run_id)) if pipeline_run_id else None
    _LOGGER.info(
        "synthesis_activation_schedule_pass_start tenant_id=%s pipeline_run_id=%s task=%s",
        tid,
        prid,
        _TASK,
    )
    with session_scope() as session:
        out = run_synthesis_activation_schedule_pass_v1(
            session,
            tenant_id=tid,
            pipeline_run_id=prid,
            published_index_epoch=published_index_epoch,
            trigger=trigger,
            force=force,
            execute_inline=True,
        )
        session.commit()
    _LOGGER.info(
        "synthesis_activation_schedule_pass_done tenant_id=%s activated=%s",
        tid,
        out.get("activated"),
    )
    return out
