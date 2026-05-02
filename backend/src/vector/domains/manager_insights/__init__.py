"""Manager insights domain: coordination fetch-debug pipeline; narrative V0 generators live in separate modules."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from vector.contracts.manager_insights_activity import (
    CoordinationContractsDebug,
    CoordinationLinkInputBundle,
    DecisionBundle,
    DecisionBundleItem,
    DecisionDefaultAction,
    DecisionItem,
    DecisionRuleTraceDebug,
    EvidenceBundle,
    ManagerInsightFetchDebugResponse,
    ManagerInsightsCoordinationSettingsDebug,
    OutcomeItem,
    PerceptionRow,
)
from vector.domains.manager_insights.build_execution_graph import build_execution_graph
from vector.domains.manager_insights.build_key_achievements import build_key_achievements
from vector.domains.manager_insights.build_raw_highlights import build_raw_highlights
from vector.domains.manager_insights.build_work_items import build_work_items
from vector.domains.manager_insights.compute_decisions import compute_decisions
from vector.domains.manager_insights.compute_gaps import compute_gaps
from vector.domains.manager_insights.compute_signals import compute_signals
from vector.domains.manager_insights.coordination_perception import (
    build_perception_qa_debug,
    run_coordination_perception_for_fetch_debug,
)
from vector.domains.manager_insights.data_reliability import compute_data_reliability, utc_now
from vector.domains.manager_insights.decision_sort_learning import (
    DecisionSortLearning,
    load_decision_sort_learning,
)
from vector.domains.manager_insights.extract_evidence import extract_evidence
from vector.domains.manager_insights.fetch_activity import run_fetch_activity_bundle
from vector.domains.manager_insights.link_work_items import link_work_items
from vector.domains.manager_insights.perceive_execution_state import (
    build_perception_execution_state_demo_debug,
    perceive_execution_state,
)
from vector.domains.manager_insights.prioritize_decisions import (
    cap_prioritized_decisions,
    prioritize_decisions,
    resolve_max_decisions_surfaced,
)
from vector.domains.manager_insights.validate_perception_rows import (
    build_perception_validation_demo_debug,
    validate_perception_rows,
)
from vector.settings import Settings


def _coordination_contracts_debug(
    settings: Settings,
    *,
    run_id: uuid.UUID,
    tenant_id: uuid.UUID,
    window_days: int,
) -> CoordinationContractsDebug:
    decision_item_example = DecisionItem(
        id="coordination:contract:example",
        gap_id="coordination:contract:gap:example",
        gap_type="expected_not_executed",
        decision_type="LINK_OR_CLOSE_COMMITMENT",
        title="Example decision (contract QA only)",
        rationale=(
            "Validates DecisionItem JSON in fetch-debug; live fetch-debug rows come from "
            "compute_decisions (§6 Step 22)."
        ),
        default_action=DecisionDefaultAction(kind="noop"),
        required_inputs={},
        evidence_refs=[],
        signal_refs=[],
        created_at=datetime(2026, 1, 1, tzinfo=UTC),
        run_id=run_id,
        status=None,
    )
    second = DecisionItem(
        id="coordination:contract:example-2",
        gap_id="coordination:contract:gap:example-2",
        gap_type="discussed_not_linked_to_work",
        decision_type="THREAD_TO_TRACKING_LINK",
        title="Second example (no row debug)",
        rationale="Demonstrates a bundle row without decision_debug.",
        default_action=DecisionDefaultAction(kind="noop"),
        required_inputs={},
        evidence_refs=[],
        signal_refs=[],
        created_at=datetime(2026, 1, 1, tzinfo=UTC),
        run_id=run_id,
        status="proposed",
    )
    decision_bundle_example = DecisionBundle(
        run_id=run_id,
        tenant_id=tenant_id,
        window_days=window_days,
        items=[
            DecisionBundleItem(
                decision=decision_item_example,
                decision_debug=DecisionRuleTraceDebug(
                    gap_id=decision_item_example.gap_id,
                    matched_rule="gap:expected_not_executed:v1",
                    conditions_met={"gap_present": True, "signal_tiebreak": False},
                ),
            ),
            DecisionBundleItem(decision=second, decision_debug=None),
        ],
    )
    outcome_item_example = OutcomeItem(
        id=uuid.UUID("660e8400-e29b-41d4-a716-446655440001"),
        decision_id=decision_item_example.id,
        tenant_id=tenant_id,
        observed_at=datetime(2026, 1, 2, tzinfo=UTC),
        outcome_type="dismissed",
        user_attribution="U_DEBUG",
        false_positive=True,
        ground_truth={"gap_id_absent_in_next_run": False},
    )
    perception_row_example = PerceptionRow(
        id="coordination:perception:example",
        work_item_id="wi:linear:NEX-1",
        kind="ambiguity",
        statement="Two owners claimed different ship dates in-thread.",
        quote="I'll ship this Friday.",
        execution_state="in_progress",
        state_transition=None,
        waits_on=["@legal"],
        blocked_by=[],
        commitment_strength="medium",
        ambiguity_class="contradiction",
        ambiguity_quote="Actually next sprint is safer.",
        contradiction_pair_id="coordination:contradiction:example-pair",
        ownership_inferred=None,
    )
    return CoordinationContractsDebug(
        decision_item_example=decision_item_example,
        decision_bundle_example=decision_bundle_example,
        outcome_item_example=outcome_item_example,
        perception_row_example=perception_row_example,
        perception_validation_demo=build_perception_validation_demo_debug(),
        perception_execution_state_demo=build_perception_execution_state_demo_debug(settings),
    )


def run_manager_insights_fetch_debug(
    session: Session,
    settings: Settings,
    *,
    tenant_id: uuid.UUID,
    window_days: int = 30,
    as_of: datetime | None = None,
    perception_query_regex: bool = False,
    include_execution_graph: bool = False,
    master_plan_debug: bool = False,
    max_decisions: int | None = None,
    persist_decisions: bool = False,
) -> ManagerInsightFetchDebugResponse:
    """Run coordination fetch-debug: Step 1 → 0.5 → 2 → … → signals → decisions → prioritize → cap → …

    **Narrative V0** (interpretations / insights bundles) is **not** included in this response. Use unit tests /
    ``generate_interpretations`` / ``generate_insights`` directly if you need those generators.

    **``master_plan_debug``** (``?master_plan_debug=1``): for this request only, run the coordination path with
    perception LLM on, attach ``execution_graph``, and merge graph edges into ``compute_gaps`` — without changing
    process env.

    When perception LLM is effective (env **or** ``master_plan_debug``), **§6 Step 10** runs
    ``perceive_execution_state`` then ``validate_perception_rows`` after work items (before evidence/linking); regex
    ``extract_evidence`` unchanged.

    **§6 Step 11:** ``perception_qa`` echoes the evidence-path label; ``perception_query_regex`` is set when the HTTP
    handler passes ``?perception=regex`` (QA hint only).

    **§6 Step 12:** ``link_work_items`` receives ``CoordinationLinkInputBundle(evidence=…, perception_rows=…)`` —
    validated ``PerceptionRow`` models plus Step-3 evidence only (architecture lock).

    **§6 Step 13:** ``compute_gaps`` receives the **same** bundle plus ``links``; perception rows only add
    mention-adjacency when non-empty (flag off → identical gap logic to bundle with empty perception).

    **§6 Step 14:** ``compute_signals`` receives the **same** ``coordination_input`` as linking and gaps;
    merges perception text into term-based signals and uses the same merged adjacency as ``compute_gaps``.

    **§6 Step 19:** ``SignalsV0Debug`` includes ``scope_ambiguity``, ``discussion_churn``, ``contradiction_density``
    (defaults + placeholder explain; **§6 Step 20** implements the predicates).

    **§6 Steps 22–23 + 25–26:** ``compute_decisions(...)`` builds the engine ``DecisionBundle`` (base mapping, Step 25
    extensions, Step 26 ``HOLD_START`` when guards pass + ``decision_emission_debug``); fetch-debug sets ``decisions``
    to that bundle; ``prioritize_decisions`` (§6 Step 27) then §6 Step 28 caps ``decisions_prioritized`` (query
    ``max_decisions`` or env ``VECTOR_MANAGER_INSIGHTS_MAX_DECISIONS_SURFACED``, default **3**).

    **§6 Step 42:** Loads policy + false-positive outcome aggregates for the tenant/window, then
    ``prioritize_decisions(..., learning=…)`` applies capped demotion after the Step-27 tuple (see
    ``decision_sort_learning``). ``perception_qa.step42_gap_demotion_by_gap_type`` echoes non-zero demotions.

    **§6 Step 15:** ``build_execution_graph`` (pure) builds ``ExecutionGraph`` from work items, links, and the
    same ``coordination_input``.

    **§6 Step 16:** When ``?include_execution_graph=1`` **or** ``VECTOR_MANAGER_INSIGHTS_INCLUDE_EXECUTION_GRAPH`` is
    true, the response ``execution_graph`` is ``build_execution_graph(...).model_dump(mode="json")``; otherwise **null**.

    **§6 Step 18:** When ``VECTOR_MANAGER_INSIGHTS_GAPS_USE_GRAPH`` is true, ``compute_gaps`` merges execution graph
    edges as undirected 1-hop adjacency (same graph as Step 15); ``gaps.gaps_debug`` carries a one-line QA summary.

    **§6 Step 32:** When ``persist_decisions`` is true (``?persist_decisions=1``), upsert **capped**
    ``decisions_prioritized`` rows into ``manager_insight_decisions`` and return ``persisted_decision_ids``.
    """

    bundle = run_fetch_activity_bundle(
        session,
        settings,
        tenant_id=tenant_id,
        window_days=window_days,
        as_of=as_of,
    )
    reliability = compute_data_reliability(bundle)
    work_items = build_work_items(bundle)
    perception_llm_effective = settings.vector_manager_insights_perception_llm or master_plan_debug
    perception_settings = settings.model_copy(
        update={"vector_manager_insights_perception_llm": perception_llm_effective}
    )
    perception, rejected_perception_rows, accepted_perception_rows = run_coordination_perception_for_fetch_debug(
        perception_settings,
        work_items,
    )
    evidence = extract_evidence(work_items)
    coordination_input = CoordinationLinkInputBundle(
        evidence=evidence,
        perception_rows=accepted_perception_rows,
    )
    links = link_work_items(work_items, link_input=coordination_input)
    gaps_use_graph_effective = settings.vector_manager_insights_gaps_use_graph or master_plan_debug
    gaps = compute_gaps(
        work_items,
        links,
        coordination_input,
        gaps_use_graph=gaps_use_graph_effective,
    )
    key_achievements = build_key_achievements(work_items, links)
    raw_highlights = build_raw_highlights(work_items, evidence, links, gaps)
    signals = compute_signals(
        work_items,
        links,
        gaps,
        key_achievements,
        raw_highlights,
        coordination_input=coordination_input,
    )
    want_execution_graph = (
        include_execution_graph
        or settings.vector_manager_insights_include_execution_graph
        or master_plan_debug
    )
    execution_graph_payload: dict | None = (
        build_execution_graph(work_items, links, coordination_input).model_dump(mode="json")
        if want_execution_graph
        else None
    )
    decision_bundle = compute_decisions(
        gaps,
        signals=signals,
        work_items=work_items,
        links=links,
        evidence=evidence,
        coordination_input=coordination_input,
        hold_start_affected_wi_threshold=settings.vector_manager_insights_hold_start_affected_wi_threshold,
        gaps_use_graph_adjacency=gaps_use_graph_effective,
    )
    as_of_effective = as_of if as_of is not None else utc_now()
    if isinstance(session, Session):
        decision_sort_learning = load_decision_sort_learning(
            session,
            tenant_id=tenant_id,
            as_of=as_of_effective,
            window_days=window_days,
        )
    else:
        decision_sort_learning = DecisionSortLearning.empty()
    prioritized_full = prioritize_decisions(
        decision_bundle,
        signals=signals,
        learning=decision_sort_learning,
    )
    eff_cap = resolve_max_decisions_surfaced(
        query_max=max_decisions,
        settings_default=settings.vector_manager_insights_max_decisions_surfaced,
    )
    decisions_prioritized, prioritized_before_cap = cap_prioritized_decisions(prioritized_full, eff_cap)

    persisted_decision_ids: list[uuid.UUID] = []
    if persist_decisions and decisions_prioritized:
        from vector.infrastructure.db.repositories.manager_insight_decisions import (
            manager_insight_decision_id_for_engine_row,
            upsert_decision_items_bulk,
        )

        persist_items = [row.decision for row in decisions_prioritized]
        persist_ranks = list(range(1, len(persist_items) + 1))
        upsert_decision_items_bulk(
            session,
            tenant_id=tenant_id,
            items=persist_items,
            ranks=persist_ranks,
        )
        persisted_decision_ids = [
            manager_insight_decision_id_for_engine_row(
                tenant_id=tenant_id,
                engine_decision_id=item.id,
            )
            for item in persist_items
        ]

    return ManagerInsightFetchDebugResponse(
        fetch=bundle,
        data_reliability=reliability,
        work_items=work_items,
        evidence=evidence,
        links=links,
        gaps=gaps,
        key_achievements=key_achievements,
        raw_highlights=raw_highlights,
        signals=signals,
        decisions=decision_bundle,
        decisions_prioritized=decisions_prioritized,
        persisted_decision_ids=persisted_decision_ids,
        rejected_perception_rows=rejected_perception_rows,
        execution_graph=execution_graph_payload,
        perception=perception,
        coordination_settings=ManagerInsightsCoordinationSettingsDebug(
            perception_llm=settings.vector_manager_insights_perception_llm,
            include_execution_graph=settings.vector_manager_insights_include_execution_graph,
            skip_narrative_steps=settings.vector_manager_insights_skip_narrative_steps,
            gaps_use_graph=settings.vector_manager_insights_gaps_use_graph,
            hold_start_affected_wi_threshold=settings.vector_manager_insights_hold_start_affected_wi_threshold,
            max_decisions_surfaced=settings.vector_manager_insights_max_decisions_surfaced,
        ),
        perception_qa=build_perception_qa_debug(
            settings,
            query_perception_regex=perception_query_regex,
            query_include_execution_graph=include_execution_graph,
            perception_llm_effective=perception_llm_effective,
            query_master_plan_debug=master_plan_debug,
            query_max_decisions=max_decisions,
            max_decisions_cap_applied=eff_cap,
            decisions_prioritized_full_count=prioritized_before_cap,
            query_persist_decisions=persist_decisions,
            step42_gap_demotion_by_gap_type=decision_sort_learning.gap_demotions_for_qa(),
        ),
        coordination_contracts=_coordination_contracts_debug(
            settings,
            run_id=bundle.run_id,
            tenant_id=bundle.tenant_id,
            window_days=bundle.window_days,
        ),
    )


__all__ = [
    "DecisionSortLearning",
    "build_execution_graph",
    "compute_data_reliability",
    "compute_signals",
    "generate_insights",
    "generate_interpretations",
    "build_key_achievements",
    "build_raw_highlights",
    "build_work_items",
    "compute_decisions",
    "load_decision_sort_learning",
    "cap_prioritized_decisions",
    "prioritize_decisions",
    "resolve_max_decisions_surfaced",
    "compute_gaps",
    "extract_evidence",
    "link_work_items",
    "run_fetch_activity_bundle",
    "run_manager_insights_fetch_debug",
    "validate_perception_rows",
    "perceive_execution_state",
    "build_perception_execution_state_demo_debug",
    "build_perception_qa_debug",
    "run_coordination_perception_for_fetch_debug",
]
