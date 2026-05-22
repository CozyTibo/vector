"""M4/M9: substrate pipeline schedule uses convergence only (debounce infra removed)."""

from __future__ import annotations

import uuid
from unittest.mock import MagicMock

import pytest


def test_schedule_substrate_pipeline_enqueues_convergence_not_coordinator(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql+psycopg://test:test@localhost:5432/vector_test",
    )
    tid = uuid.uuid4()
    enqueue_calls: list[str] = []
    dirty_calls: list[str] = []

    def _enqueue(tenant_id: object, *, reason: str = "sweeper") -> dict[str, object]:
        enqueue_calls.append(reason)
        return {"enqueued": True, "celery_task_id": "conv-1", "reason": reason}

    def _mark_dirty(_session: object, *, tenant_id: object, reason: str) -> dict[str, object]:
        dirty_calls.append(reason)
        return {"obligation_epoch": 1}

    from contextlib import contextmanager

    @contextmanager
    def _fake_scope() -> MagicMock:
        yield MagicMock()

    monkeypatch.setattr(
        "vector.domains.cortex.substrate_pipeline.orchestrator.session_scope",
        _fake_scope,
    )
    def _dispatch(*, tenant_id: object, reason: str, **kwargs: object) -> dict[str, object]:
        dirty_calls.append(reason)
        enqueue_calls.append(reason)
        return {
            "scheduled": True,
            "path": "convergence_lease",
            "obligation_epoch": 1,
            "enqueued": True,
            "celery_task_id": "conv-1",
        }

    monkeypatch.setattr(
        "vector.domains.cortex.execution.convergence_dispatch.mark_dirty_and_enqueue_convergence_v1",
        _dispatch,
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

    from vector.domains.cortex.substrate_pipeline.orchestrator import schedule_substrate_pipeline_v1
    from vector.settings import get_settings

    get_settings.cache_clear()
    try:
        first = schedule_substrate_pipeline_v1(tenant_id=tid, reason="sync_a")
        second = schedule_substrate_pipeline_v1(tenant_id=tid, reason="sync_b")
        assert first["scheduled"] is True
        assert first["path"] == "convergence_lease"
        assert first.get("coalesced") is False
        assert second["scheduled"] is True
        assert second["path"] == "convergence_lease"
        assert len(enqueue_calls) == 2
        assert len(dirty_calls) == 2
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
