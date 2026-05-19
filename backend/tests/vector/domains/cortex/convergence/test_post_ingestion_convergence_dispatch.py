"""Post-ingestion dispatch uses convergence lease when runtime enabled."""

from __future__ import annotations

import uuid
from unittest.mock import patch

from vector.domains.cortex.ingestion.post_ingestion_refresh_dispatch import (
    schedule_post_ingestion_substrate_refresh,
)
def test_post_ingestion_uses_convergence_path_when_enabled() -> None:
    tenant_id = uuid.uuid4()
    cfg = type(
        "Cfg",
        (),
        {
            "cortex_post_ingestion_substrate_refresh_enabled": True,
            "cortex_convergence_runtime_enabled": True,
        },
    )()
    with (
        patch(
            "vector.domains.cortex.convergence.lease.mark_tenant_dirty_v1",
            return_value={"obligation_epoch": 1, "status": "dirty"},
        ) as mark_dirty,
        patch(
            "vector.infrastructure.db.session.session_scope",
        ) as scope,
        patch(
            "vector.domains.cortex.convergence.enqueue.enqueue_tenant_convergence_v1",
            return_value={"enqueued": True, "celery_task_id": "t1"},
        ) as enqueue,
    ):
        mock_session = scope.return_value.__enter__.return_value
        out = schedule_post_ingestion_substrate_refresh(
            tenant_id=tenant_id,
            settings=cfg,
            reason="incremental_sync_complete",
        )
    assert out["scheduled"] is True
    assert out["path"] == "convergence_lease"
    mark_dirty.assert_called_once()
    enqueue.assert_called_once()
