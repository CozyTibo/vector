"""§6 Step 35 — skip_interpretations / skip_insights bypass P7/P8 generators on fetch-debug."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from unittest.mock import MagicMock

import pytest

import vector.domains.manager_insights as manager_insights_pkg

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


def _settings() -> Settings:
    return Settings.model_construct(
        database_url="postgresql://fetch-debug-skip-narrative-step35-test",
        openai_api_key="sk-test",
        openai_model="gpt-4o-mini",
        env="development",
        secret_key="dev-only-secret-key-min-32-chars-long!!",
        vector_manager_insights_perception_llm=False,
        vector_manager_insights_include_execution_graph=False,
        vector_manager_insights_skip_narrative_steps=False,
        vector_manager_insights_gaps_use_graph=False,
    )


def test_fetch_debug_skip_interpretations_skips_generator(monkeypatch: pytest.MonkeyPatch) -> None:
    tid = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
    monkeypatch.setattr(
        "vector.domains.manager_insights.run_fetch_activity_bundle",
        lambda *a, **k: _minimal_fetch_bundle(tenant_id=tid),
    )

    def _boom(*_a: object, **_k: object):
        raise AssertionError("generate_interpretations must not be called when skip_interpretations")

    monkeypatch.setattr(manager_insights_pkg, "generate_interpretations", _boom)
    session = MagicMock()
    out = run_manager_insights_fetch_debug(session, _settings(), tenant_id=tid, skip_interpretations=True)
    assert out.interpretations.items == []
    assert out.interpretations.fallback_reason == "skip_interpretations_fetch_debug"
    assert out.perception_qa.query_skip_interpretations is True
    assert out.perception_qa.query_skip_insights is False


def test_fetch_debug_skip_insights_skips_generator(monkeypatch: pytest.MonkeyPatch) -> None:
    tid = uuid.UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")
    monkeypatch.setattr(
        "vector.domains.manager_insights.run_fetch_activity_bundle",
        lambda *a, **k: _minimal_fetch_bundle(tenant_id=tid),
    )

    def _boom(*_a: object, **_k: object):
        raise AssertionError("generate_insights must not be called when skip_insights")

    monkeypatch.setattr(manager_insights_pkg, "generate_insights", _boom)
    session = MagicMock()
    out = run_manager_insights_fetch_debug(session, _settings(), tenant_id=tid, skip_insights=True)
    assert out.insights.items == []
    assert out.insights.fallback_reason == "skip_insights_fetch_debug"
    assert out.perception_qa.query_skip_insights is True
    assert out.perception_qa.query_skip_interpretations is False


def test_fetch_debug_skip_both_skips_both(monkeypatch: pytest.MonkeyPatch) -> None:
    tid = uuid.UUID("cccccccc-cccc-cccc-cccc-cccccccccccc")
    monkeypatch.setattr(
        "vector.domains.manager_insights.run_fetch_activity_bundle",
        lambda *a, **k: _minimal_fetch_bundle(tenant_id=tid),
    )

    def _boom_i(*_a: object, **_k: object):
        raise AssertionError("generate_interpretations must not be called")

    def _boom_n(*_a: object, **_k: object):
        raise AssertionError("generate_insights must not be called")

    monkeypatch.setattr(manager_insights_pkg, "generate_interpretations", _boom_i)
    monkeypatch.setattr(manager_insights_pkg, "generate_insights", _boom_n)
    session = MagicMock()
    out = run_manager_insights_fetch_debug(
        session,
        _settings(),
        tenant_id=tid,
        skip_interpretations=True,
        skip_insights=True,
    )
    assert out.interpretations.items == []
    assert out.insights.items == []
    assert out.perception_qa.query_skip_interpretations is True
    assert out.perception_qa.query_skip_insights is True


def test_build_perception_qa_echoes_skip_flags() -> None:
    from vector.domains.manager_insights.coordination_perception import build_perception_qa_debug

    q = build_perception_qa_debug(
        _settings(),
        query_skip_interpretations=True,
        query_skip_insights=True,
    )
    assert q.query_skip_interpretations is True
    assert q.query_skip_insights is True
