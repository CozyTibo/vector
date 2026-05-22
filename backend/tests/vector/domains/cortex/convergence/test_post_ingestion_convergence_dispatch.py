"""Post-ingestion dispatch uses convergence lease when runtime enabled."""

from __future__ import annotations

import uuid
from unittest.mock import patch

from vector.domains.cortex.ingestion.post_ingestion_refresh_dispatch import (
    schedule_post_ingestion_substrate_refresh,
)
def test_post_ingestion_uses_convergence_path() -> None:
    tenant_id = uuid.uuid4()
    cfg = type(
        "Cfg",
        (),
        {
            "cortex_post_ingestion_substrate_refresh_enabled": True,
        },
    )()
    with patch(
        "vector.domains.cortex.ingestion.post_ingestion_refresh_dispatch.mark_dirty_and_enqueue_convergence_v1",
        return_value={
            "scheduled": True,
            "path": "convergence_lease",
            "execution_path": "convergence",
            "execution_path_telemetry": {"event": "cortex_execution_path"},
        },
    ) as dispatch:
        out = schedule_post_ingestion_substrate_refresh(
            tenant_id=tenant_id,
            settings=cfg,
            reason="incremental_sync_complete",
        )
    assert out["scheduled"] is True
    assert out["path"] == "convergence_lease"
    assert out["execution_path"] == "convergence"
    assert out["execution_path_telemetry"]["event"] == "cortex_execution_path"
    dispatch.assert_called_once()
