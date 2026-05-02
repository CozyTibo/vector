"""§6 Step 23 — fetch-debug `decisions` from compute_decisions (Step 22)."""

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
        database_url="postgresql://fetch-debug-decisions-step23-test",
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


def test_fetch_debug_decisions_bundle_matches_gaps(monkeypatch: pytest.MonkeyPatch) -> None:
    tid = uuid.UUID("22222222-2222-2222-2222-222222222222")
    monkeypatch.setattr(
        "vector.domains.manager_insights.run_fetch_activity_bundle",
        lambda *a, **k: _minimal_fetch_bundle(tenant_id=tid),
    )
    session = MagicMock()
    out = run_manager_insights_fetch_debug(session, _settings(), tenant_id=tid, max_decisions=50)
    assert isinstance(out.perception_qa.step42_gap_demotion_by_gap_type, dict)
    assert out.decisions is not None
    ng, nd = len(out.gaps.gaps), len(out.decisions.items)
    if ng <= 1:
        assert nd == ng
    else:
        assert 1 <= nd <= min(6, ng)
    assert out.decisions.run_id == out.gaps.run_id
    assert out.decisions_prioritized is not None
    assert len(out.decisions_prioritized) == len(out.decisions.items)
    assert {x.decision.id for x in out.decisions_prioritized} == {x.decision.id for x in out.decisions.items}


def test_fetch_debug_decisions_non_empty_when_gaps_present(monkeypatch: pytest.MonkeyPatch) -> None:
    """Orchestrator passes gaps into compute_decisions — situation pipeline still surfaces injected gap ids."""
    tid = uuid.UUID("33333333-3333-3333-3333-333333333333")
    monkeypatch.setattr(
        "vector.domains.manager_insights.run_fetch_activity_bundle",
        lambda *a, **k: _minimal_fetch_bundle(tenant_id=tid),
    )

    def _with_injected_gap(*a: object, **kw: object):
        b = _compute_gaps_real(*a, **kw)
        extra = GapItem(
            id="step23-inject-gap",
            type="blocker_not_tracked",
            description="injected for §6 Step 23 test",
            evidence_pointers={"t": ["ev-1"]},
        )
        return b.model_copy(update={"gaps": [*b.gaps, extra]})

    monkeypatch.setattr(manager_insights_pkg, "compute_gaps", _with_injected_gap)
    session = MagicMock()
    out = run_manager_insights_fetch_debug(session, _settings(), tenant_id=tid, max_decisions=50)
    assert out.decisions is not None
    assert len(out.decisions.items) >= 1
    assert sum(1 for r in out.decisions.items if r.decision.dominant) == 1
    mb = [
        r.decision
        for r in out.decisions.items
        if r.decision.decision_type == "MAKE_BLOCKERS_EXPLICIT"
        and "step23-inject-gap" in (r.decision.required_inputs.get("underlying_gap_ids") or [])
    ]
    assert mb, "expected injected blocker gap to map to MAKE_BLOCKERS_EXPLICIT somewhere in the narrative bundle"
    inv = mb[0]
    assert inv.gap_type == "aggregated_situation"
    assert "ev-1" in inv.evidence_refs
    assert out.decisions_prioritized is not None
    assert len(out.decisions_prioritized) == len(out.decisions.items)
