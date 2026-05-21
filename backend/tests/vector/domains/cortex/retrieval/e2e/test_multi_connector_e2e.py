"""E2E multi-connector post-ingestion — convergence lease per sync (M2)."""

from __future__ import annotations

import uuid
from unittest.mock import MagicMock, patch

import pytest


def test_multi_connector_schedule_enqueues_convergence_per_sync(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql+psycopg://test:test@localhost:5432/vector_test",
    )
    monkeypatch.setenv("CORTEX_POST_INGESTION_SUBSTRATE_REFRESH_ENABLED", "true")

    tid = uuid.uuid4()
    enqueue_reasons: list[str] = []

    def _enqueue(tenant_id: uuid.UUID | str, *, reason: str = "sweeper") -> dict[str, object]:
        enqueue_reasons.append(reason)
        return {"enqueued": True, "celery_task_id": f"task-{len(enqueue_reasons)}"}

    with (
        patch(
            "vector.domains.cortex.ingestion.post_ingestion_refresh_dispatch.mark_tenant_dirty_v1",
            return_value={"obligation_epoch": 1, "status": "dirty"},
        ) as mark_dirty,
        patch(
            "vector.domains.cortex.ingestion.post_ingestion_refresh_dispatch.session_scope",
        ) as scope,
        patch(
            "vector.domains.cortex.ingestion.post_ingestion_refresh_dispatch.enqueue_tenant_convergence_v1",
            side_effect=_enqueue,
        ),
    ):
        scope.return_value.__enter__.return_value = MagicMock()
        from vector.domains.cortex.ingestion.post_ingestion_refresh_dispatch import (
            schedule_post_ingestion_substrate_refresh,
        )
        from vector.settings import get_settings

        get_settings.cache_clear()
        try:
            schedule_post_ingestion_substrate_refresh(tenant_id=tid, reason="connector_a")
            schedule_post_ingestion_substrate_refresh(tenant_id=tid, reason="connector_b")
            assert mark_dirty.call_count == 2
            assert enqueue_reasons == ["connector_a", "connector_b"]
        finally:
            get_settings.cache_clear()
