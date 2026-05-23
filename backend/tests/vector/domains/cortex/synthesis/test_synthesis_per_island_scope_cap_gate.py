"""Phase C2 — per-island scope cap + fail-loud gate unit tests."""

from __future__ import annotations

import pytest

from vector.domains.cortex.synthesis.synthesis_orchestrator import SynthesisOrchestratorError
from vector.domains.cortex.synthesis.synthesis_per_island_scope_cap_gate import (
    ALL_SCOPES_FAILED_CODE_V1,
    ORCHESTRATOR_FAIL_LOUD_CODE_V1,
    SynthesisPerIslandMaterializeError,
    enforce_all_scopes_failed_fail_loud_v1,
    enforce_per_island_orchestrator_fail_loud_v1,
    resolve_per_island_scope_cap_budget_v1,
    should_fail_loud_on_orchestrator_exception_v1,
)


def test_resolve_cap_budget_uses_min_of_per_island_and_shared() -> None:
    class _Cfg:
        cortex_synthesis_per_island_max_scopes_per_island = 8
        cortex_synthesis_pipeline_max_scopes = 16

    budget = resolve_per_island_scope_cap_budget_v1(island_count=4, settings=_Cfg())
    assert budget["scopes_budget_per_island"] == 4
    assert budget["budget_source"] == "settings"


def test_resolve_cap_budget_override() -> None:
    class _Cfg:
        cortex_synthesis_per_island_max_scopes_per_island = 8
        cortex_synthesis_pipeline_max_scopes = 16

    budget = resolve_per_island_scope_cap_budget_v1(
        island_count=2,
        settings=_Cfg(),
        max_scopes_override=3,
    )
    assert budget["scopes_budget_per_island"] == 3
    assert budget["budget_source"] == "override"


def test_orchestrator_fail_loud_re_raises(monkeypatch) -> None:
    monkeypatch.setattr(
        "vector.domains.cortex.synthesis.synthesis_per_island_scope_cap_gate."
        "is_synthesis_per_island_fail_loud_enabled_v1",
        lambda: True,
    )
    exc = SynthesisOrchestratorError("orchestrator down")
    with pytest.raises(SynthesisPerIslandMaterializeError) as raised:
        enforce_per_island_orchestrator_fail_loud_v1(
            exc,
            island_scope_id="d7e41b3c763d38e9",
            retrieval_lookup_id="lk-1",
        )
    assert raised.value.code == ORCHESTRATOR_FAIL_LOUD_CODE_V1
    assert raised.value.detail["island_scope_id"] == "d7e41b3c763d38e9"


def test_orchestrator_fail_loud_disabled_swallows(monkeypatch) -> None:
    monkeypatch.setattr(
        "vector.domains.cortex.synthesis.synthesis_per_island_scope_cap_gate."
        "is_synthesis_per_island_fail_loud_enabled_v1",
        lambda: False,
    )
    exc = SynthesisOrchestratorError("orchestrator down")
    assert should_fail_loud_on_orchestrator_exception_v1(exc) is False
    enforce_per_island_orchestrator_fail_loud_v1(exc, island_scope_id="x")


def test_all_scopes_failed_fail_loud(monkeypatch) -> None:
    monkeypatch.setattr(
        "vector.domains.cortex.synthesis.synthesis_per_island_scope_cap_gate."
        "is_synthesis_per_island_fail_loud_enabled_v1",
        lambda: True,
    )
    with pytest.raises(SynthesisPerIslandMaterializeError) as raised:
        enforce_all_scopes_failed_fail_loud_v1(
            scopes_scheduled=5,
            jobs_completed=0,
            jobs_failed=5,
        )
    assert raised.value.code == ALL_SCOPES_FAILED_CODE_V1
