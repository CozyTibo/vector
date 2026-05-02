"""§6 Step 32 — fetch-debug `persist_decisions` upserts capped prioritized rows; response lists PKs."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from unittest.mock import MagicMock

import pytest

import vector.domains.manager_insights as manager_insights_pkg

from vector.contracts.manager_insights_activity import ConnectorFetchResult, FetchActivityBundle, GapItem
from vector.domains.manager_insights import run_manager_insights_fetch_debug
from vector.domains.manager_insights.compute_gaps import compute_gaps as _compute_gaps_real
from vector.domains.manager_insights.prioritize_decisions import prioritize_decisions
from vector.infrastructure.db.repositories.manager_insight_decisions import manager_insight_decision_id_for_engine_row
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
        database_url="postgresql://fetch-debug-persist-step32-test",
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
            id=f"step32-inject-gap-{i}",
            type="blocker_not_tracked",
            description="injected for §6 Step 32 persist test",
            evidence_pointers={"t": [f"ev-{i}"]},
        )
        for i in range(4)
    ]
    return b.model_copy(update={"gaps": [*b.gaps, *extras]})


def test_fetch_debug_persist_off_does_not_call_upsert(monkeypatch: pytest.MonkeyPatch) -> None:
    tid = uuid.UUID("77777777-7777-7777-7777-777777777777")
    monkeypatch.setattr(
        "vector.domains.manager_insights.run_fetch_activity_bundle",
        lambda *a, **k: _minimal_fetch_bundle(tenant_id=tid),
    )
    monkeypatch.setattr(manager_insights_pkg, "compute_gaps", _inject_four_gaps)

    called: list[object] = []

    def _no_upsert(*_a: object, **_k: object) -> int:
        called.append(True)
        return 0

    monkeypatch.setattr(
        "vector.infrastructure.db.repositories.manager_insight_decisions.upsert_decision_items_bulk",
        _no_upsert,
    )
    session = MagicMock()
    out = run_manager_insights_fetch_debug(session, _settings(), tenant_id=tid, persist_decisions=False)
    assert called == []
    assert out.persisted_decision_ids == []
    assert out.perception_qa.query_persist_decisions is False


def test_fetch_debug_persist_on_writes_capped_rows_and_returns_ids(monkeypatch: pytest.MonkeyPatch) -> None:
    tid = uuid.UUID("88888888-8888-8888-8888-888888888888")
    monkeypatch.setattr(
        "vector.domains.manager_insights.run_fetch_activity_bundle",
        lambda *a, **k: _minimal_fetch_bundle(tenant_id=tid),
    )
    monkeypatch.setattr(manager_insights_pkg, "compute_gaps", _inject_four_gaps)

    calls: list[tuple[list, list]] = []

    def _capture_upsert(_session: object, *, tenant_id: uuid.UUID, items: object, ranks: object) -> int:
        items_list = list(items)
        ranks_list = list(ranks)
        calls.append((items_list, ranks_list))
        return len(items_list)

    monkeypatch.setattr(
        "vector.infrastructure.db.repositories.manager_insight_decisions.upsert_decision_items_bulk",
        _capture_upsert,
    )
    session = MagicMock()
    out = run_manager_insights_fetch_debug(
        session,
        _settings(),
        tenant_id=tid,
        max_decisions=2,
        persist_decisions=True,
    )
    assert out.perception_qa.query_persist_decisions is True
    assert out.decisions_prioritized is not None
    assert len(out.decisions_prioritized) == 2
    assert len(calls) == 1
    items, ranks = calls[0]
    assert len(items) == 2
    assert ranks == [1, 2]
    assert out.decisions is not None
    full_order = prioritize_decisions(out.decisions, signals=out.signals)
    assert [d.id for d in items] == [x.decision.id for x in full_order[:2]]
    expected_ids = [
        manager_insight_decision_id_for_engine_row(tenant_id=tid, engine_decision_id=d.id) for d in items
    ]
    assert out.persisted_decision_ids == expected_ids


def test_fetch_debug_persist_on_empty_prioritized_no_upsert(monkeypatch: pytest.MonkeyPatch) -> None:
    tid = uuid.UUID("99999999-9999-9999-9999-999999999999")
    monkeypatch.setattr(
        "vector.domains.manager_insights.run_fetch_activity_bundle",
        lambda *a, **k: _minimal_fetch_bundle(tenant_id=tid),
    )

    called: list[object] = []

    def _no_upsert(*_a: object, **_k: object) -> int:
        called.append(True)
        return 0

    monkeypatch.setattr(
        "vector.infrastructure.db.repositories.manager_insight_decisions.upsert_decision_items_bulk",
        _no_upsert,
    )
    session = MagicMock()
    out = run_manager_insights_fetch_debug(session, _settings(), tenant_id=tid, persist_decisions=True)
    assert out.decisions_prioritized == []
    assert called == []
    assert out.persisted_decision_ids == []
