"""§6 Step 28 — fetch-debug `max_decisions` caps `decisions_prioritized` (default from env)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from unittest.mock import MagicMock

import pytest

import vector.domains.manager_insights as manager_insights_pkg

from vector.contracts.manager_insights_activity import (
    ConnectorFetchResult,
    FetchActivityBundle,
    GapItem,
)
from vector.domains.manager_insights import run_manager_insights_fetch_debug
from vector.domains.manager_insights.compute_gaps import compute_gaps as _compute_gaps_real
from vector.domains.manager_insights.prioritize_decisions import prioritize_decisions
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
        database_url="postgresql://fetch-debug-max-decisions-step28-test",
        openai_api_key="sk-test",
        openai_model="gpt-4o-mini",
        env="development",
        secret_key="dev-only-secret-key-min-32-chars-long!!",
        vector_manager_insights_perception_llm=False,
        vector_manager_insights_include_execution_graph=False,
        vector_manager_insights_skip_narrative_steps=False,
        vector_manager_insights_gaps_use_graph=False,
        vector_manager_insights_max_decisions_surfaced=3,
    )
    base.update(kwargs)
    return Settings.model_construct(**base)  # type: ignore[arg-type]


def _inject_four_gaps(*args: object, **kwargs: object):
    b = _compute_gaps_real(*args, **kwargs)
    extras = [
        GapItem(
            id=f"step28-inject-gap-{i}",
            type="blocker_not_tracked",
            description="injected for §6 Step 28 cap test",
            evidence_pointers={"t": [f"ev-{i}"]},
        )
        for i in range(4)
    ]
    return b.model_copy(update={"gaps": [*b.gaps, *extras]})


def test_fetch_debug_default_cap_truncates_to_three(monkeypatch: pytest.MonkeyPatch) -> None:
    tid = uuid.UUID("44444444-4444-4444-4444-444444444444")
    monkeypatch.setattr(
        "vector.domains.manager_insights.run_fetch_activity_bundle",
        lambda *a, **k: _minimal_fetch_bundle(tenant_id=tid),
    )
    monkeypatch.setattr(manager_insights_pkg, "compute_gaps", _inject_four_gaps)
    session = MagicMock()
    out = run_manager_insights_fetch_debug(session, _settings(), tenant_id=tid)
    assert out.decisions is not None
    assert len(out.decisions.items) == 4
    assert out.decisions_prioritized is not None
    assert len(out.decisions_prioritized) == 3
    assert out.perception_qa.max_decisions_cap_applied == 3
    assert out.perception_qa.decisions_prioritized_full_count == 4
    assert out.perception_qa.query_max_decisions is None
    full_order = prioritize_decisions(out.decisions, signals=out.signals)
    assert [x.decision.id for x in out.decisions_prioritized] == [x.decision.id for x in full_order[:3]]


def test_fetch_debug_max_decisions_query_stable_order(monkeypatch: pytest.MonkeyPatch) -> None:
    tid = uuid.UUID("55555555-5555-5555-5555-555555555555")
    monkeypatch.setattr(
        "vector.domains.manager_insights.run_fetch_activity_bundle",
        lambda *a, **k: _minimal_fetch_bundle(tenant_id=tid),
    )
    monkeypatch.setattr(manager_insights_pkg, "compute_gaps", _inject_four_gaps)
    session = MagicMock()
    out = run_manager_insights_fetch_debug(session, _settings(), tenant_id=tid, max_decisions=2)
    assert out.decisions_prioritized is not None
    assert len(out.decisions_prioritized) == 2
    assert out.perception_qa.query_max_decisions == 2
    assert out.perception_qa.max_decisions_cap_applied == 2
    full_order = prioritize_decisions(out.decisions, signals=out.signals)
    assert [x.decision.id for x in out.decisions_prioritized] == [x.decision.id for x in full_order[:2]]


def test_fetch_debug_cap_respects_settings_default(monkeypatch: pytest.MonkeyPatch) -> None:
    tid = uuid.UUID("66666666-6666-6666-6666-666666666666")
    monkeypatch.setattr(
        "vector.domains.manager_insights.run_fetch_activity_bundle",
        lambda *a, **k: _minimal_fetch_bundle(tenant_id=tid),
    )
    monkeypatch.setattr(manager_insights_pkg, "compute_gaps", _inject_four_gaps)
    session = MagicMock()
    out = run_manager_insights_fetch_debug(
        session,
        _settings(vector_manager_insights_max_decisions_surfaced=2),
        tenant_id=tid,
    )
    assert out.decisions_prioritized is not None
    assert len(out.decisions_prioritized) == 2
    assert out.perception_qa.max_decisions_cap_applied == 2
