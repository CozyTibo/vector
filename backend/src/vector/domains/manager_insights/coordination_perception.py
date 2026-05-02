"""§6 Step 10 — coordination perception path (perceive + validate) before linking."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, Literal

from vector.contracts.manager_insights_activity import (
    ManagerInsightPerceptionQaDebug,
    PerceptionExecutionStateLlmDebug,
    PerceptionRow,
    RejectedPerceptionRowDebug,
    WorkItemBundle,
)
from vector.domains.manager_insights.perceive_execution_state import perceive_execution_state
from vector.domains.manager_insights.validate_perception_rows import validate_perception_rows
from vector.settings import Settings


def build_perception_qa_debug(
    settings: Settings,
    *,
    query_perception_regex: bool = False,
    query_include_execution_graph: bool = False,
    perception_llm_effective: bool | None = None,
    query_master_plan_debug: bool = False,
    query_max_decisions: int | None = None,
    max_decisions_cap_applied: int | None = None,
    decisions_prioritized_full_count: int | None = None,
    query_persist_decisions: bool = False,
    step42_gap_demotion_by_gap_type: dict[str, int] | None = None,
) -> ManagerInsightPerceptionQaDebug:
    """§6 Step 11 — labels for admin QA (flag-driven + optional ``?perception=regex`` echo).

    ``perception_llm_effective`` overrides env for this run (e.g. admin ``?master_plan_debug=1``).
    """
    llm_on = (
        settings.vector_manager_insights_perception_llm
        if perception_llm_effective is None
        else perception_llm_effective
    )
    path: Literal["regex_evidence_only", "llm_perception_plus_regex_evidence"] = (
        "llm_perception_plus_regex_evidence" if llm_on else "regex_evidence_only"
    )
    cap = (
        settings.vector_manager_insights_max_decisions_surfaced
        if max_decisions_cap_applied is None
        else max_decisions_cap_applied
    )
    full_n = 0 if decisions_prioritized_full_count is None else decisions_prioritized_full_count
    step42 = {} if step42_gap_demotion_by_gap_type is None else dict(step42_gap_demotion_by_gap_type)
    return ManagerInsightPerceptionQaDebug(
        evidence_path=path,
        query_perception_regex=query_perception_regex,
        query_include_execution_graph=query_include_execution_graph,
        query_master_plan_debug=query_master_plan_debug,
        query_max_decisions=query_max_decisions,
        max_decisions_cap_applied=cap,
        decisions_prioritized_full_count=full_n,
        query_persist_decisions=query_persist_decisions,
        step42_gap_demotion_by_gap_type=step42,
    )


def run_coordination_perception_for_fetch_debug(
    settings: Settings,
    work_items: WorkItemBundle,
    *,
    perceive_fn: Callable[[Settings, WorkItemBundle], PerceptionExecutionStateLlmDebug] | None = None,
) -> tuple[dict[str, Any] | None, list[RejectedPerceptionRowDebug], list[PerceptionRow]]:
    """When ``vector_manager_insights_perception_llm`` is on: LLM parse → validate; else no-op.

    ``perceive_fn`` overrides ``perceive_execution_state`` for tests.

    Returns validated ``PerceptionRow`` models for §6 Step 12 (linking input bundle).
    """
    if not settings.vector_manager_insights_perception_llm:
        return None, [], []

    perceive = perceive_fn or perceive_execution_state
    llm: PerceptionExecutionStateLlmDebug = perceive(settings, work_items)
    by_id = {w.id: w for w in work_items.items}
    accepted, rejected = validate_perception_rows(llm.rows, work_items_by_id=by_id)

    perception: dict[str, Any] = {
        "enabled": True,
        "llm": llm.model_dump(mode="json"),
        "accepted": [a.model_dump(mode="json") for a in accepted],
        "accepted_count": len(accepted),
        "rejected_count": len(rejected),
    }
    return perception, rejected, accepted


__all__ = ["build_perception_qa_debug", "run_coordination_perception_for_fetch_debug"]
