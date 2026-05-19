"""Async stalled traversal recovery pass (**G-P085-WALK-03**)."""

from __future__ import annotations

import logging
import uuid
from typing import Any

from app.celery_app import celery_app
from vector.domains.cortex.operational_runtime.substrate_stalled_traversal_recovery import (
    CELERY_STALLED_TRAVERSAL_RECOVERY_TASK_NAME_V1,
    run_stalled_traversal_recovery_pass_v1,
)
from vector.infrastructure.db.session import session_scope

_LOGGER = logging.getLogger("app")

_TASK = CELERY_STALLED_TRAVERSAL_RECOVERY_TASK_NAME_V1


@celery_app.task(name=_TASK, queue="vector")
def run_stalled_traversal_recovery_pass_task(*, tenant_id: str) -> dict[str, Any]:
    tid = uuid.UUID(str(tenant_id))
    _LOGGER.info(
        "stalled_traversal_recovery_pass_start tenant_id=%s task=%s",
        tid,
        _TASK,
    )
    with session_scope() as session:
        out = run_stalled_traversal_recovery_pass_v1(session, tenant_id=tid)
        session.commit()
    _LOGGER.info(
        "stalled_traversal_recovery_pass_done tenant_id=%s recovered=%s",
        tid,
        out.get("recovered"),
    )
    return out
