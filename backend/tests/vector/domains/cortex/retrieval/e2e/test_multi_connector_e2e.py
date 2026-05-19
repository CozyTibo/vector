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

    from contextlib import contextmanager

    @contextmanager
    def _fake_scope() -> MagicMock:
        yield MagicMock()

    schedule_actions = ["schedule", "coalesce"]

    monkeypatch.setattr(
        "vector.domains.cortex.substrate_pipeline.orchestrator.session_scope",
        _fake_scope,
    )
    monkeypatch.setattr(
        "vector.domains.cortex.operational_runtime.substrate_runtime_economics."
        "evaluate_pipeline_concurrency_v1",
        lambda *_a, **_k: {"may_start_pipeline": True},
    )
    monkeypatch.setattr(
        "vector.domains.cortex.canonical.transform_runtime."
        "resolve_default_bundle_id_for_stub_transform",
        lambda *_a, **_k: "bundle-test",
    )

    def _resolve_action(*_a, **_k: object) -> tuple[str, dict[str, object]]:
        return schedule_actions.pop(0), {}

    monkeypatch.setattr(
        "vector.infrastructure.cortex_substrate_pipeline_schedule."
        "resolve_substrate_pipeline_schedule_action_v1",
        _resolve_action,
    )
    monkeypatch.setattr(
        "vector.infrastructure.cortex_substrate_pipeline_schedule."
        "write_substrate_pipeline_schedule_anchor_v1",
        lambda *_a, **_k: True,
    )

    from vector.domains.cortex.ingestion.post_ingestion_refresh_dispatch import (
        schedule_post_ingestion_substrate_refresh,
    )
    from vector.settings import get_settings

    get_settings.cache_clear()
    try:
        schedule_post_ingestion_substrate_refresh(tenant_id=tid, reason="connector_a")
        schedule_post_ingestion_substrate_refresh(tenant_id=tid, reason="connector_b")
        assert len(calls) == 1
        assert calls[0].endswith(str(tid))
    finally:
        get_settings.cache_clear()
