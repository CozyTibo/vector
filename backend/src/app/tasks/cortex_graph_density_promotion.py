"""Async lawful edge promotion pass (**G-P085-PROMO-01**)."""

from __future__ import annotations

import logging
import uuid
from typing import Any

from app.celery_app import celery_app
from vector.domains.cortex.operational_runtime.graph_density_promotion import (
    CELERY_GRAPH_DENSITY_PROMOTION_TASK_NAME_V1,
    run_graph_density_promotion_pass_v1,
)
from vector.infrastructure.db.session import session_scope

_LOGGER = logging.getLogger("app")

_TASK = CELERY_GRAPH_DENSITY_PROMOTION_TASK_NAME_V1


@celery_app.task(name=_TASK, queue="vector")
def run_graph_density_promotion_pass_task(
    *,
    tenant_id: str,
    trigger: str = "manual",
    pipeline_run_id: str | None = None,
) -> dict[str, Any]:
    tid = uuid.UUID(str(tenant_id))
    prid = uuid.UUID(str(pipeline_run_id)) if pipeline_run_id else None
    _LOGGER.info(
        "graph_density_promotion_pass_start tenant_id=%s trigger=%s task=%s",
        tid,
        trigger,
        _TASK,
    )
    with session_scope() as session:
        out = run_graph_density_promotion_pass_v1(
            session,
            tenant_id=tid,
            trigger=trigger,
            pipeline_run_id=prid,
        )
        session.commit()
    _LOGGER.info(
        "graph_density_promotion_pass_done tenant_id=%s promoted=%s",
        tid,
        out.get("promoted_count"),
    )
    return out
