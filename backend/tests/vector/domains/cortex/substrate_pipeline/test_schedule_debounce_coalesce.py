"""Substrate pipeline schedule coalesce — debounce without perpetual starvation."""

from __future__ import annotations

import time
import uuid
from unittest.mock import MagicMock

import pytest


def test_resolve_action_schedule_when_no_anchor(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql+psycopg://test:test@localhost:5432/vector_test",
    )
    monkeypatch.setattr(
        "vector.infrastructure.cortex_substrate_pipeline_schedule."
        "read_substrate_pipeline_schedule_anchor_v1",
        lambda *_a, **_k: None,
    )
    from vector.infrastructure.cortex_substrate_pipeline_schedule import (
        resolve_substrate_pipeline_schedule_action_v1,
    )

    action, meta = resolve_substrate_pipeline_schedule_action_v1(
        uuid.uuid4(),
        debounce_seconds=120,
        max_wait_seconds=900,
    )
    assert action == "schedule"
    assert meta["anchor_unix"] is None


def test_resolve_action_coalesce_within_max_wait(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql+psycopg://test:test@localhost:5432/vector_test",
    )
    anchor = time.time() - 60
    monkeypatch.setattr(
        "vector.infrastructure.cortex_substrate_pipeline_schedule."
        "read_substrate_pipeline_schedule_anchor_v1",
        lambda *_a, **_k: anchor,
    )
    from vector.infrastructure.cortex_substrate_pipeline_schedule import (
        resolve_substrate_pipeline_schedule_action_v1,
    )

    action, meta = resolve_substrate_pipeline_schedule_action_v1(
        uuid.uuid4(),
        debounce_seconds=120,
        max_wait_seconds=900,
    )
    assert action == "coalesce"
    assert float(meta["elapsed_seconds"]) >= 59


def test_resolve_action_force_now_after_max_wait(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql+psycopg://test:test@localhost:5432/vector_test",
    )
    anchor = time.time() - 1000
    monkeypatch.setattr(
        "vector.infrastructure.cortex_substrate_pipeline_schedule."
        "read_substrate_pipeline_schedule_anchor_v1",
        lambda *_a, **_k: anchor,
    )
    from vector.infrastructure.cortex_substrate_pipeline_schedule import (
        resolve_substrate_pipeline_schedule_action_v1,
    )

    action, _meta = resolve_substrate_pipeline_schedule_action_v1(
        uuid.uuid4(),
        debounce_seconds=120,
        max_wait_seconds=900,
    )
    assert action == "force_now"


def test_orchestrator_coalesces_second_schedule_without_revoke(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql+psycopg://test:test@localhost:5432/vector_test",
    )
    tid = uuid.uuid4()
    apply_calls: list[dict[str, object]] = []
    revoke_calls: list[str] = []
    schedule_actions = ["schedule", "coalesce"]

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
        "vector.domains.cortex.canonical.transform_runtime."
        "resolve_default_bundle_id_for_stub_transform",
        lambda *_a, **_k: "bundle-test",
    )
    monkeypatch.setattr(
        "vector.domains.cortex.operational_runtime.substrate_runtime_economics."
        "evaluate_pipeline_concurrency_v1",
        lambda *_a, **_k: {"may_start_pipeline": True},
    )

    def _resolve_action(*_a: object, **_k: object) -> tuple[str, dict[str, object]]:
        return schedule_actions.pop(0), {"elapsed_seconds": 30}

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
    monkeypatch.setattr(
        "vector.infrastructure.cortex_substrate_pipeline_schedule."
        "clear_substrate_pipeline_schedule_anchor_v1",
        lambda *_a, **_k: None,
    )

    from vector.domains.cortex.substrate_pipeline.orchestrator import schedule_substrate_pipeline_v1
    from vector.settings import get_settings

    get_settings.cache_clear()
    try:
        first = schedule_substrate_pipeline_v1(tenant_id=tid, reason="sync_a")
        second = schedule_substrate_pipeline_v1(tenant_id=tid, reason="sync_b")
        assert first["scheduled"] is True
        assert first.get("coalesced") is False
        assert second["coalesced"] is True
        assert len(apply_calls) == 1
        assert len(revoke_calls) == 1
    finally:
        get_settings.cache_clear()


def test_orchestrator_no_bundle_returns_early(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql+psycopg://test:test@localhost:5432/vector_test",
    )
    tid = uuid.uuid4()

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
    monkeypatch.setattr(
        "vector.domains.cortex.canonical.transform_runtime."
        "resolve_default_bundle_id_for_stub_transform",
        lambda *_a, **_k: None,
    )

    from vector.domains.cortex.substrate_pipeline.orchestrator import schedule_substrate_pipeline_v1
    from vector.settings import get_settings

    get_settings.cache_clear()
    try:
        out = schedule_substrate_pipeline_v1(tenant_id=tid)
        assert out == {"scheduled": False, "reason": "no_transformable_bundle"}
    finally:
        get_settings.cache_clear()
