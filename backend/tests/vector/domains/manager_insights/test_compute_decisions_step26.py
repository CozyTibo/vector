"""§6 Step 26 — HOLD_START three-guard logic + decision_emission_debug."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from vector.contracts.manager_insights_activity import (
    CoordinationLinkInputBundle,
    EvidenceBundle,
    EvidenceItem,
    GapBundle,
    GapItem,
    LinkBundle,
    SignalsV0Debug,
    WorkItem,
    WorkItemBundle,
    WorkItemLink,
)
from vector.domains.manager_insights.compute_decisions import compute_decisions


def _wi(wid: str, *, wtype: str, title: str = "t") -> WorkItem:
    return WorkItem(
        id=wid,
        source="slack" if wid.startswith("slack:") else "linear",  # type: ignore[arg-type]
        type=wtype,  # type: ignore[arg-type]
        title=title,
        summary=None,
        status="open",
        source_ref={},
    )


def _link(rid: uuid.UUID, a: str, b: str) -> WorkItemLink:
    return WorkItemLink(
        id=f"lnk:{a}:{b}",
        from_work_item_id=a,
        to_work_item_id=b,
        link_type="semantic_match",  # type: ignore[arg-type]
        confidence="high",  # type: ignore[arg-type]
        similarity=0.9,
        evidence="test",
    )


def _sig_scope_high() -> SignalsV0Debug:
    return SignalsV0Debug.model_validate(
        {
            "delivery_strength": "moderate",
            "urgent_pressure": "low",
            "expectation_coverage": "high",
            "follow_through": "strong",
            "blocker_visibility": "visible",
            "repeated_discussion_present": False,
            "execution_momentum": "steady",
            "documentation_linkage": "linked",
            "focus": "focused",
            "collaboration_intensity": "moderate",
            "support_pattern": "balanced",
            "feedback_reception": "neutral",
            "coordination_role": "contributing",
            "interaction_friction": "absent",
            "scope_ambiguity": "high",
            "discussion_churn": "low",
            "contradiction_density": "low",
            "explain": {},
        }
    )


def _bundles_with_chain() -> tuple[uuid.UUID, uuid.UUID, WorkItemBundle, LinkBundle, EvidenceBundle, CoordinationLinkInputBundle]:
    rid = uuid.uuid4()
    tid = uuid.uuid4()
    wd = 30
    items = [
        _wi("slack:disc1", wtype="message_thread"),
        _wi("linear:i1", wtype="issue"),
        _wi("linear:i2", wtype="issue"),
        _wi("linear:i3", wtype="issue"),
    ]
    wi = WorkItemBundle(run_id=rid, tenant_id=tid, window_days=wd, items=items)
    lb = LinkBundle(
        run_id=rid,
        tenant_id=tid,
        window_days=wd,
        links=[
            _link(rid, "slack:disc1", "linear:i1"),
            _link(rid, "linear:i1", "linear:i2"),
            _link(rid, "linear:i2", "linear:i3"),
        ],
        work_items_capped=0,
    )
    ev = EvidenceBundle(
        run_id=rid,
        tenant_id=tid,
        window_days=wd,
        action_items=[],
        blockers=[],
        decisions=[],
        discarded_without_evidence=0,
    )
    coord = CoordinationLinkInputBundle(evidence=ev, perception_rows=[])
    return rid, tid, wi, lb, ev, coord


def test_step26_hold_start_emits_when_guards_pass() -> None:
    rid, tid, wi, lb, ev, coord = _bundles_with_chain()
    gap = GapBundle(
        run_id=rid,
        tenant_id=tid,
        window_days=30,
        gaps=[
            GapItem(
                id="gap:disc",
                type="discussed_not_linked_to_work",
                description="Discussion not linked.",
                evidence_pointers={"source_work_item_ids": ["slack:disc1"]},
            ),
        ],
    )
    out = compute_decisions(
        gap,
        signals=_sig_scope_high(),
        work_items=wi,
        links=lb,
        evidence=ev,
        coordination_input=coord,
        hold_start_affected_wi_threshold=2,
        include_decision_debug=True,
    )
    d = out.items[0].decision
    assert d.decision_type == "HOLD_START"
    assert out.items[0].decision_emission_debug is not None
    em = out.items[0].decision_emission_debug
    assert em is not None
    assert em.hold_start_emitted is True
    assert em.guard_open_execution_count_ok is True
    assert em.open_execution_count >= 3
    assert out.items[0].decision_debug is not None
    assert out.items[0].decision_debug.matched_rule == "extension:hold_start_scope_cluster:v1"


def test_step26_hold_start_suppressed_when_decision_evidence_in_cluster() -> None:
    rid, tid, wi, lb, ev, coord = _bundles_with_chain()
    ev.decisions.append(
        EvidenceItem(
            id="ev-dec-1",
            kind="decision",
            statement="We decided X",
            evidence="quote",
            source_work_item_id="linear:i2",
            source_connector="slack",  # type: ignore[arg-type]
            source_type="message_thread",  # type: ignore[arg-type]
            linked_work_items=[],
        )
    )
    gap = GapBundle(
        run_id=rid,
        tenant_id=tid,
        window_days=30,
        gaps=[
            GapItem(
                id="gap:disc2",
                type="discussed_not_linked_to_work",
                description="Discussion not linked.",
                evidence_pointers={"source_work_item_ids": ["slack:disc1"]},
            ),
        ],
    )
    out = compute_decisions(
        gap,
        signals=_sig_scope_high(),
        work_items=wi,
        links=lb,
        evidence=ev,
        coordination_input=coord,
        hold_start_affected_wi_threshold=2,
        include_decision_debug=True,
    )
    assert out.items[0].decision.decision_type == "CLARIFY_SPEC"
    em = out.items[0].decision_emission_debug
    assert em is not None
    assert em.hold_start_emitted is False
    assert em.decision_evidence_ids_in_cluster == ["ev-dec-1"]


def test_step26_threshold_suppresses_hold_start() -> None:
    rid, tid, wi, lb, ev, coord = _bundles_with_chain()
    gap = GapBundle(
        run_id=rid,
        tenant_id=tid,
        window_days=30,
        gaps=[
            GapItem(
                id="gap:disc3",
                type="discussed_not_linked_to_work",
                description="Discussion not linked.",
                evidence_pointers={"source_work_item_ids": ["slack:disc1"]},
            ),
        ],
    )
    out = compute_decisions(
        gap,
        signals=_sig_scope_high(),
        work_items=wi,
        links=lb,
        evidence=ev,
        coordination_input=coord,
        hold_start_affected_wi_threshold=5,
        include_decision_debug=True,
    )
    assert out.items[0].decision.decision_type == "CLARIFY_SPEC"
    em = out.items[0].decision_emission_debug
    assert em is not None
    assert em.hold_start_emitted is False
    assert em.guard_open_execution_count_ok is False
