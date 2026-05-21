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
    monkeypatch.setattr(
        "vector.domains.cortex.execution.lease.mark_tenant_dirty_v1",
        _mark_dirty,
    )
    monkeypatch.setattr(
        "vector.domains.cortex.execution.enqueue.enqueue_tenant_convergence_v1",
        _enqueue,
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
