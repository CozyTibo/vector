"""§6 Step 3 — optional coordination keys on ManagerInsightFetchDebugResponse."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from vector.domains.manager_insights.perceive_execution_state import build_perception_execution_state_demo_debug
from vector.domains.manager_insights.validate_perception_rows import build_perception_validation_demo_debug
from vector.contracts.manager_insights_activity import (
    ConnectorFetchResult,
    ConnectorReliabilityDetail,
    CoordinationContractsDebug,
    CoordinationLinkInputBundle,
    DataReliabilityReport,
    DecisionBundle,
    DecisionDefaultAction,
    DecisionItem,
    EvidenceBundle,
    FetchActivityBundle,
    GapBundle,
    InsightBundleDebug,
    InterpretationBundleDebug,
    KeyAchievementsBundleDebug,
    LinkBundle,
    ManagerInsightFetchDebugResponse,
    ManagerInsightPerceptionQaDebug,
    ManagerInsightsCoordinationSettingsDebug,
    OutcomeItem,
    PerceptionRow,
    RawHighlightsBundleDebug,
    RejectedPerceptionRowDebug,
    SignalsV0Debug,
    WorkItemBundle,
)


def _detail(tier: str = "high") -> ConnectorReliabilityDetail:
    return ConnectorReliabilityDetail(tier=tier, reasons=["ok"], metrics={})


def _conn(
    name: str,
    *,
    ws: datetime,
    we: datetime,
) -> ConnectorFetchResult:
    return ConnectorFetchResult(
        connector=name,  # type: ignore[arg-type]
        status="not_configured",
        fetched_at=None,
        window_start=ws,
        window_end=we,
        caps_applied=[],
        errors=[],
    )


def _minimal_fetch_debug_response() -> ManagerInsightFetchDebugResponse:
    """Smallest valid ManagerInsightFetchDebugResponse for round-trip tests."""
    rid = uuid.UUID("11111111-1111-1111-1111-111111111111")
    tid = uuid.UUID("22222222-2222-2222-2222-222222222222")
    wd = 30
    ws = datetime(2026, 1, 1, tzinfo=UTC)
    we = datetime(2026, 1, 31, tzinfo=UTC)
    fetch = FetchActivityBundle(
        run_id=rid,
        tenant_id=tid,
        window_days=wd,
        connectors={
            "slack": _conn("slack", ws=ws, we=we),
            "github": _conn("github", ws=ws, we=we),
            "linear": _conn("linear", ws=ws, we=we),
            "notion": _conn("notion", ws=ws, we=we),
            "calls": _conn("calls", ws=ws, we=we),
        },
    )
    rel = DataReliabilityReport(
        slack=_detail(),
        github=_detail(),
        linear=_detail(),
        notion=_detail(),
        calls=_detail(),
        overall_confidence="high",
    )
    empty_wi = WorkItemBundle(run_id=rid, tenant_id=tid, window_days=wd, items=[])
    ev = EvidenceBundle(
        run_id=rid,
        tenant_id=tid,
        window_days=wd,
        action_items=[],
        blockers=[],
        decisions=[],
        discarded_without_evidence=0,
    )
    lb = LinkBundle(run_id=rid, tenant_id=tid, window_days=wd, links=[], work_items_capped=0)
    gb = GapBundle(run_id=rid, tenant_id=tid, window_days=wd, gaps=[])
    ka = KeyAchievementsBundleDebug(run_id=rid, tenant_id=tid, window_days=wd, items=[])
    rh = RawHighlightsBundleDebug(run_id=rid, tenant_id=tid, window_days=wd, items=[])
    sig = SignalsV0Debug(
        delivery_strength="moderate",
        urgent_pressure="low",
        expectation_coverage="high",
        follow_through="strong",
        blocker_visibility="visible",
        repeated_discussion_present=False,
        execution_momentum="steady",
        documentation_linkage="linked",
        focus="focused",
        collaboration_intensity="moderate",
        support_pattern="balanced",
        feedback_reception="neutral",
        coordination_role="contributing",
        interaction_friction="absent",
        explain={},
    )
    interp = InterpretationBundleDebug(
        run_id=rid,
        tenant_id=tid,
        window_days=wd,
        items=[],
        generated_via="fallback",
        fallback_reason="test",
    )
    ins = InsightBundleDebug(
        run_id=rid,
        tenant_id=tid,
        window_days=wd,
        items=[],
        generated_via="fallback",
        fallback_reason="test",
    )
    di = DecisionItem(
        id="x",
        gap_id="g",
        gap_type="expected_not_executed",
        decision_type="LINK_OR_CLOSE_COMMITMENT",
        title="t",
        rationale="r",
        default_action=DecisionDefaultAction(kind="noop"),
        created_at=datetime(2026, 1, 1, tzinfo=UTC),
        run_id=rid,
    )
    ccd = CoordinationContractsDebug(
        decision_item_example=di,
        decision_bundle_example=DecisionBundle(run_id=rid, tenant_id=tid, window_days=wd, items=[]),
        outcome_item_example=OutcomeItem(
            id=uuid.UUID("33333333-3333-3333-3333-333333333333"),
            decision_id="x",
            tenant_id=tid,
            observed_at=datetime(2026, 1, 2, tzinfo=UTC),
            outcome_type="ignored",
        ),
        perception_row_example=PerceptionRow(
            id="p-min",
            work_item_id="wi-min",
            kind="risk",
            statement="Schedule risk called out in thread.",
            quote="might slip a week",
            execution_state="in_progress",
        ),
        perception_validation_demo=build_perception_validation_demo_debug(),
        perception_execution_state_demo=build_perception_execution_state_demo_debug(),
    )
    return ManagerInsightFetchDebugResponse(
        fetch=fetch,
        data_reliability=rel,
        work_items=empty_wi,
        evidence=ev,
        links=lb,
        gaps=gb,
        key_achievements=ka,
        raw_highlights=rh,
        signals=sig,
        interpretations=interp,
        insights=ins,
        decisions=None,
        decisions_prioritized=None,
        rejected_perception_rows=[],
        execution_graph=None,
        perception=None,
        coordination_settings=ManagerInsightsCoordinationSettingsDebug(),
        perception_qa=ManagerInsightPerceptionQaDebug(),
        coordination_contracts=ccd,
    )


def test_rejected_perception_row_debug_round_trip() -> None:
    r = RejectedPerceptionRowDebug(index=0, reason="bad quote", raw={"a": 1})
    dumped = r.model_dump(mode="json")
    assert RejectedPerceptionRowDebug.model_validate(dumped) == r


def test_manager_insight_perception_qa_debug_round_trip() -> None:
    q = ManagerInsightPerceptionQaDebug(
        evidence_path="llm_perception_plus_regex_evidence",
        query_perception_regex=True,
        query_include_execution_graph=True,
        query_master_plan_debug=True,
    )
    dumped = q.model_dump(mode="json")
    assert ManagerInsightPerceptionQaDebug.model_validate(dumped) == q


def test_step3_fields_round_trip_on_full_response() -> None:
    full = _minimal_fetch_debug_response()
    data = full.model_dump(mode="python")
    again = ManagerInsightFetchDebugResponse.model_validate(data)
    assert again.decisions is None
    assert again.decisions_prioritized is None
    assert again.rejected_perception_rows == []
    assert again.execution_graph is None
    assert again.perception is None
    assert again.coordination_settings == ManagerInsightsCoordinationSettingsDebug()
    assert again.perception_qa == ManagerInsightPerceptionQaDebug()
    assert again.persisted_decision_ids == []
    assert again == full


def test_step3_keys_omitted_from_dict_use_defaults() -> None:
    full = _minimal_fetch_debug_response()
    dumped = full.model_dump(mode="python")
    for key in (
        "decisions",
        "decisions_prioritized",
        "rejected_perception_rows",
        "execution_graph",
        "perception",
        "coordination_settings",
        "perception_qa",
        "persisted_decision_ids",
    ):
        dumped.pop(key, None)
    again = ManagerInsightFetchDebugResponse.model_validate(dumped)
    assert again.decisions is None
    assert again.decisions_prioritized is None
    assert again.rejected_perception_rows == []
    assert again.execution_graph is None
    assert again.perception is None
    assert again.coordination_settings == ManagerInsightsCoordinationSettingsDebug()
    assert again.perception_qa == ManagerInsightPerceptionQaDebug()
    assert again.persisted_decision_ids == []


def test_coordination_link_input_bundle_round_trip() -> None:
    rid = uuid.UUID("11111111-1111-1111-1111-111111111111")
    tid = uuid.UUID("22222222-2222-2222-2222-222222222222")
    wd = 30
    ev = EvidenceBundle(
        run_id=rid,
        tenant_id=tid,
        window_days=wd,
        action_items=[],
        blockers=[],
        decisions=[],
        discarded_without_evidence=0,
    )
    row = PerceptionRow(
        id="p-step12",
        work_item_id="wi-a",
        kind="risk",
        statement="Schedule pressure.",
        quote="might slip",
        execution_state="in_progress",
    )
    bundle = CoordinationLinkInputBundle(evidence=ev, perception_rows=[row])
    dumped = bundle.model_dump(mode="json")
    assert CoordinationLinkInputBundle.model_validate(dumped) == bundle


def test_link_bundle_perception_rows_used_for_linking_defaults() -> None:
    rid = uuid.UUID("11111111-1111-1111-1111-111111111111")
    tid = uuid.UUID("22222222-2222-2222-2222-222222222222")
    lb = LinkBundle(run_id=rid, tenant_id=tid, window_days=30, links=[], work_items_capped=0)
    assert lb.perception_rows_used_for_linking == 0
