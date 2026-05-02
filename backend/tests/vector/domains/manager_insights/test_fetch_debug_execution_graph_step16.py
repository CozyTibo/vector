"""§6 Step 16 — execution_graph on fetch-debug when query or env requests it."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from unittest.mock import MagicMock

import pytest

from vector.contracts.manager_insights_activity import ConnectorFetchResult, FetchActivityBundle
from vector.domains.manager_insights import run_manager_insights_fetch_debug
from vector.settings import Settings


def _conn(name: str, *, ws: datetime, we: datetime) -> ConnectorFetchResult:
    return ConnectorFetchResult(
        connector=name,  # type: ignore[arg-type]
        status="not_configured",
        fetched_at=None,
        window_start=ws,
        window_end=we,
        caps_applied=[],
        errors=[],
    )


def _minimal_fetch_bundle(*, tenant_id: uuid.UUID) -> FetchActivityBundle:
    rid = uuid.UUID("11111111-1111-1111-1111-111111111111")
    wd = 30
    ws = datetime(2026, 1, 1, tzinfo=UTC)
    we = datetime(2026, 1, 31, tzinfo=UTC)
    return FetchActivityBundle(
        run_id=rid,
        tenant_id=tenant_id,
        window_days=wd,
        connectors={
            "slack": _conn("slack", ws=ws, we=we),
            "github": _conn("github", ws=ws, we=we),
            "linear": _conn("linear", ws=ws, we=we),
            "notion": _conn("notion", ws=ws, we=we),
            "calls": _conn("calls", ws=ws, we=we),
        },
    )


def _settings(**kwargs: object) -> Settings:
    base = dict(
        database_url="postgresql://execution-graph-step16-test",
        openai_api_key="sk-test",
        openai_model="gpt-4o-mini",
        env="development",
        secret_key="dev-only-secret-key-min-32-chars-long!!",
        vector_manager_insights_perception_llm=False,
        vector_manager_insights_include_execution_graph=False,
        vector_manager_insights_skip_narrative_steps=False,
        vector_manager_insights_gaps_use_graph=False,
    )
    base.update(kwargs)
    return Settings.model_construct(**base)  # type: ignore[arg-type]


def test_execution_graph_null_without_query_or_env(monkeypatch: pytest.MonkeyPatch) -> None:
    tid = uuid.UUID("22222222-2222-2222-2222-222222222222")
    monkeypatch.setattr(
        "vector.domains.manager_insights.run_fetch_activity_bundle",
        lambda *a, **k: _minimal_fetch_bundle(tenant_id=tid),
    )
    session = MagicMock()
    out = run_manager_insights_fetch_debug(
        session,
        _settings(),
        tenant_id=tid,
        include_execution_graph=False,
    )
    assert out.execution_graph is None
    assert out.perception_qa.query_include_execution_graph is False


def test_execution_graph_present_with_query_param(monkeypatch: pytest.MonkeyPatch) -> None:
    tid = uuid.UUID("22222222-2222-2222-2222-222222222222")
    monkeypatch.setattr(
        "vector.domains.manager_insights.run_fetch_activity_bundle",
        lambda *a, **k: _minimal_fetch_bundle(tenant_id=tid),
    )
    session = MagicMock()
    out = run_manager_insights_fetch_debug(
        session,
        _settings(),
        tenant_id=tid,
        include_execution_graph=True,
    )
    assert out.execution_graph is not None
    assert "nodes" in out.execution_graph
    assert "edges" in out.execution_graph
    assert "unresolved_dependency_refs" in out.execution_graph
    assert out.perception_qa.query_include_execution_graph is True


def test_execution_graph_present_when_only_env_flag(monkeypatch: pytest.MonkeyPatch) -> None:
    tid = uuid.UUID("22222222-2222-2222-2222-222222222222")
    monkeypatch.setattr(
        "vector.domains.manager_insights.run_fetch_activity_bundle",
        lambda *a, **k: _minimal_fetch_bundle(tenant_id=tid),
    )
    session = MagicMock()
    out = run_manager_insights_fetch_debug(
        session,
        _settings(vector_manager_insights_include_execution_graph=True),
        tenant_id=tid,
        include_execution_graph=False,
    )
    assert out.execution_graph is not None
    assert isinstance(out.execution_graph["nodes"], list)
