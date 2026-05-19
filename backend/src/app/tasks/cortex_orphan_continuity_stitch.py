"""Async orphan continuity stitching pass (**G-P085-ORPHAN-01**)."""

from __future__ import annotations

import logging
import uuid
from typing import Any

from app.celery_app import celery_app
from vector.domains.cortex.operational_runtime.graph_orphan_continuity import (
    CELERY_ORPHAN_CONTINUITY_STITCH_TASK_NAME_V1,
    STITCH_TRIGGER_SCHEDULED_V1,
    run_continuity_stitching_pass_v1,
)
from vector.infrastructure.db.session import session_scope

_LOGGER = logging.getLogger("app")

_TASK = CELERY_ORPHAN_CONTINUITY_STITCH_TASK_NAME_V1


@celery_app.task(name=_TASK, queue="vector")
def run_orphan_continuity_stitch_pass_task(
    *,
    tenant_id: str,
    trigger: str = STITCH_TRIGGER_SCHEDULED_V1,
    dry_run: bool = False,
) -> dict[str, Any]:
    tid = uuid.UUID(str(tenant_id))
    _LOGGER.info(
        "orphan_continuity_stitch_start tenant_id=%s trigger=%s task=%s",
        tid,
        trigger,
        _TASK,
    )
    with session_scope() as session:
        out = run_continuity_stitching_pass_v1(
            session,
            tenant_id=tid,
            trigger=trigger,
            dry_run=bool(dry_run),
        )
        session.commit()
    _LOGGER.info(
        "orphan_continuity_stitch_done tenant_id=%s orphans=%s",
        tid,
        (out.get("classification") or {}).get("orphan_entity_count"),
    )
    return out
