"""Async traversal retry + frontier heal pass (**G-P085-WALK-02**)."""

from __future__ import annotations

import logging
import uuid
from typing import Any

from app.celery_app import celery_app
from vector.domains.cortex.operational_runtime.substrate_traversal_retry import (
    CELERY_TRAVERSAL_RETRY_TASK_NAME_V1,
    run_traversal_retry_and_heal_pass_v1,
)
from vector.infrastructure.db.session import session_scope

_LOGGER = logging.getLogger("app")

_TASK = CELERY_TRAVERSAL_RETRY_TASK_NAME_V1


@celery_app.task(name=_TASK, queue="vector")
def run_traversal_retry_and_heal_pass_task(*, tenant_id: str) -> dict[str, Any]:
    tid = uuid.UUID(str(tenant_id))
    _LOGGER.info(
        "traversal_retry_and_heal_pass_start tenant_id=%s task=%s",
        tid,
        _TASK,
    )
    with session_scope() as session:
        out = run_traversal_retry_and_heal_pass_v1(session, tenant_id=tid)
        session.commit()
    _LOGGER.info(
        "traversal_retry_and_heal_pass_done tenant_id=%s scanned=%s",
        tid,
        out.get("records_scanned"),
    )
    return out
