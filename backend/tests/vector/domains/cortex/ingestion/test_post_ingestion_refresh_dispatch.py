"""Post-ingestion substrate refresh scheduling (debounced coalesce)."""

from __future__ import annotations

import uuid
from unittest.mock import MagicMock

import pytest


def test_schedule_noops_when_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql+psycopg://test:test@localhost:5432/vector_test",
    )
    monkeypatch.setenv("CORTEX_POST_INGESTION_SUBSTRATE_REFRESH_ENABLED", "false")

    from vector.domains.cortex.ingestion.post_ingestion_refresh_dispatch import (
        schedule_post_ingestion_substrate_refresh,
    )
    from vector.settings import get_settings

    get_settings.cache_clear()
    try:
        out = schedule_post_ingestion_substrate_refresh(tenant_id=uuid.uuid4())
        assert out == {"scheduled": False, "reason": "disabled"}
    finally:
        get_settings.cache_clear()


def test_schedule_debounced_refresh_with_stable_task_id(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql+psycopg://test:test@localhost:5432/vector_test",
    )
    monkeypatch.setenv("CORTEX_POST_INGESTION_SUBSTRATE_REFRESH_ENABLED", "true")
    monkeypatch.setenv("CORTEX_POST_INGESTION_SUBSTRATE_REFRESH_DEBOUNCE_SECONDS", "120")

    tid = uuid.uuid4()
    apply_calls: list[dict[str, object]] = []
    revoke_calls: list[str] = []

    mock_task = MagicMock()

    def _apply_async(**kwargs: object) -> MagicMock:
        apply_calls.append(kwargs)
        result = MagicMock()
        result.id = "celery-uuid"
        return result

    mock_task.apply_async = _apply_async

    mock_celery = MagicMock()
    mock_celery.control.revoke.side_effect = lambda task_id, **_: revoke_calls.append(task_id)

    monkeypatch.setattr("app.celery_app.celery_app", mock_celery)
    monkeypatch.setattr(
        "app.tasks.cortex_substrate_pipeline.run_cortex_substrate_pipeline_coordinator_task",
        mock_task,
    )
    from contextlib import contextmanager

    @contextmanager
    def _fake_scope() -> MagicMock:
        yield MagicMock()

    monkeypatch.setattr(
        "vector.domains.cortex.substrate_pipeline.orchestrator.session_scope",
        _fake_scope,
    )
    monkeypatch.setattr(
        "vector.domains.cortex.operational_runtime.substrate_runtime_economics."
        "evaluate_pipeline_concurrency_v1",
        lambda *_a, **_k: {"may_start_pipeline": True},
    )

    from vector.domains.cortex.ingestion.post_ingestion_refresh_dispatch import (
        post_ingestion_refresh_celery_task_id,
        schedule_post_ingestion_substrate_refresh,
    )
    from vector.settings import get_settings

    get_settings.cache_clear()
    try:
        out = schedule_post_ingestion_substrate_refresh(tenant_id=tid, reason="test")
        assert out["scheduled"] is True
        assert out["countdown_seconds"] == 120
        assert len(apply_calls) == 1
        call = apply_calls[0]
        assert call["queue"] == "vector"
        assert call["countdown"] == 120
        assert call["task_id"] == post_ingestion_refresh_celery_task_id(tid)
        assert call["kwargs"]["tenant_id"] == str(tid)
        assert call["kwargs"]["batch_limit"] == get_settings().cortex_post_ingestion_canonical_batch_limit
        assert call["kwargs"]["trigger_kind"] == "post_ingestion"
        assert revoke_calls == [post_ingestion_refresh_celery_task_id(tid)]
    finally:
        get_settings.cache_clear()
