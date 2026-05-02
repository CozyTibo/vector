"""Tests for artifact-grounded decision copy helpers."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from vector.contracts.manager_insights_activity import (
    DecisionBundleItem,
    DecisionDefaultAction,
    DecisionItem,
    DecisionRuleTraceDebug,
    EvidenceItem,
    LinkBundle,
    SignalsV0Debug,
    WorkItem,
    WorkItemBundle,
    WorkItemLink,
)
from vector.domains.manager_insights.artifact_decision_context import (
    artifact_action_targets_payload,
    artifact_label_for_work_item,
    build_deterministic_artifact_interpretation,
    expand_evidence_refs_to_work_item_ids,
    merge_required_inputs_artifact_targets,
    select_primary_work_items,
)


def _sig(**overrides: object) -> SignalsV0Debug:
    base = dict(
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
    base.update(overrides)
    return SignalsV0Debug.model_validate(base)  # type: ignore[arg-type]


def test_artifact_label_issue_identifier() -> None:
    wi = WorkItem(
        id="linear:issue:NEX-112",
        source="linear",
        type="issue",
        title="Fix checkout",
        source_ref={"identifier": "NEX-112"},
    )
    assert artifact_label_for_work_item(wi) == "NEX-112"


def test_expand_evidence_refs_resolves_evidence_id() -> None:
    wi = WorkItem(
        id="linear:issue:NEX-1",
        source="linear",
        type="issue",
        title="T",
        source_ref={"identifier": "NEX-1"},
    )
    ev = EvidenceItem(
        id="ev:block:1",
        kind="blocker",
        statement="s",
        evidence="e",
        source_work_item_id=wi.id,
        source_connector="slack",
        source_type="message_thread",
        source_ref={},
    )
    wi_by_id = {wi.id: wi}
    ev_by_id = {ev.id: ev}
    assert expand_evidence_refs_to_work_item_ids([ev.id], wi_by_id, ev_by_id) == [wi.id]


def test_select_primary_prefers_linked_issue() -> None:
    rid = uuid.uuid4()
    tid = uuid.uuid4()
    issue = WorkItem(
        id="linear:issue:NEX-9",
        source="linear",
        type="issue",
        title="Big issue",
        source_ref={"identifier": "NEX-9"},
        owner=None,
    )
    thread = WorkItem(
        id="slack:thread:abc",
        source="slack",
        type="message_thread",
        title="Discussion",
        source_ref={"channel": "eng-payments"},
    )
    bundle = WorkItemBundle(run_id=rid, tenant_id=tid, window_days=7, items=[issue, thread])
    ln = WorkItemLink(
        id="l1",
        from_work_item_id=issue.id,
        to_work_item_id=thread.id,
        link_type="semantic_match",
        confidence="high",
        similarity=0.5,
        evidence="overlap",
    )
    links = LinkBundle(run_id=rid, tenant_id=tid, window_days=7, links=[ln], work_items_capped=0, perception_rows_used_for_linking=0)
    sig = _sig(
        repeated_discussion_present=True,
        discussion_churn="high",
    )
    d = DecisionItem(
        id="d1",
        gap_id="g1",
        gap_type="aggregated_situation",
        decision_type="FORCE_DECISION",
        title="t",
        rationale="r",
        default_action=DecisionDefaultAction(kind="noop"),
        required_inputs={"failure_mode": "DECISION_FAILURE"},
        evidence_refs=[thread.id, issue.id],
        signal_refs=[],
        dominant=True,
        created_at=datetime.now(UTC),
        run_id=rid,
        status=None,
    )
    dbg = DecisionRuleTraceDebug(
        gap_id=d.gap_id,
        matched_rule="x",
        execution_situation="DECISION_LOOP",
    )
    item = DecisionBundleItem(decision=d, decision_debug=dbg)
    primary = select_primary_work_items(item, work_items=bundle, evidence=None, links=links, signals=sig)
    assert primary[0].type == "message_thread"


def test_deterministic_copy_names_artifact() -> None:
    rid = uuid.uuid4()
    wi = WorkItem(
        id="github:pr:acme/repo/89",
        source="github",
        type="pull_request",
        title="Payments",
        source_ref={},
    )
    d = DecisionItem(
        id="d1",
        gap_id="g1",
        gap_type="aggregated_situation",
        decision_type="ASSIGN_OWNER",
        title="t",
        rationale="r",
        default_action=DecisionDefaultAction(kind="noop"),
        required_inputs={"failure_mode": "OWNERSHIP_FAILURE"},
        evidence_refs=[wi.id],
        signal_refs=[],
        dominant=True,
        created_at=datetime.now(UTC),
        run_id=rid,
        status=None,
    )
    item = DecisionBundleItem(decision=d, decision_debug=None)
    label = artifact_label_for_work_item(wi)
    out = build_deterministic_artifact_interpretation(item, [wi], [label])
    assert "PR #89" in out["llm_next_step"] or label in out["llm_next_step"]
    assert label in out["llm_explanation"] or "PR #89" in out["llm_explanation"]


def test_merge_required_inputs_adds_artifact_targets() -> None:
    rid = uuid.uuid4()
    wi = WorkItem(
        id="linear:issue:NEX-5",
        source="linear",
        type="issue",
        title="Do the thing",
        source_ref={"identifier": "NEX-5"},
    )
    d = DecisionItem(
        id="d1",
        gap_id="g1",
        gap_type="aggregated_situation",
        decision_type="TRACK_BLOCKER",
        title="t",
        rationale="r",
        default_action=DecisionDefaultAction(kind="noop"),
        required_inputs={"failure_mode": "INVISIBLE_BLOCKERS"},
        evidence_refs=[wi.id],
        signal_refs=[],
        dominant=True,
        created_at=datetime.now(UTC),
        run_id=rid,
        status=None,
    )
    item = DecisionBundleItem(decision=d, decision_debug=None)
    targets = artifact_action_targets_payload([wi])
    merged = merge_required_inputs_artifact_targets(item, targets)
    assert isinstance(merged.get("artifact_action_targets"), list)
    assert any(isinstance(t, dict) and t.get("label") == "NEX-5" for t in merged["artifact_action_targets"])
