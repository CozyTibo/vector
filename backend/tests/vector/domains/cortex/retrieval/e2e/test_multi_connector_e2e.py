"""E2E multi-connector coalesce — debounced pipeline scheduling."""

from __future__ import annotations

import uuid
from unittest.mock import MagicMock

import pytest


def test_multi_connector_schedule_coalesces_task_id(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql+psycopg://test:test@localhost:5432/vector_test",
    )
    monkeypatch.setenv("CORTEX_POST_INGESTION_SUBSTRATE_REFRESH_ENABLED", "true")

    tid = uuid.uuid4()
    calls: list[str] = []

    mock_task = MagicMock()

    def _apply_async(**kwargs: object) -> MagicMock:
        calls.append(str(kwargs.get("task_id", "")))
        r = MagicMock()
        r.id = "celery-1"
        return r

    mock_task.apply_async = _apply_async
    mock_celery = MagicMock()
    monkeypatch.setattr("app.celery_app.celery_app", mock_celery)
    monkeypatch.setattr(
        "app.tasks.cortex_substrate_pipeline.run_cortex_substrate_pipeline_coordinator_task",
        mock_task,
    )

    from vector.domains.cortex.ingestion.post_ingestion_refresh_dispatch import (
        schedule_post_ingestion_substrate_refresh,
    )
    from vector.settings import get_settings

    get_settings.cache_clear()
    try:
        schedule_post_ingestion_substrate_refresh(tenant_id=tid, reason="connector_a")
        schedule_post_ingestion_substrate_refresh(tenant_id=tid, reason="connector_b")
        assert len(calls) == 2
        assert calls[0] == calls[1]
    finally:
        get_settings.cache_clear()
