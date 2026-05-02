"""§6 Steps 22 + 25 — compute_decisions gap → decision mapping and signal extensions."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from vector.contracts.manager_insights_activity import (
    GapBundle,
    GapItem,
    SignalsV0Debug,
)
from vector.domains.manager_insights.compute_decisions import compute_decisions


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


def test_compute_decisions_maps_four_base_gap_types() -> None:
    rid = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
    tid = uuid.UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")
    ts = datetime(2026, 4, 30, 12, 0, 0, tzinfo=UTC)
    gaps = GapBundle(
        run_id=rid,
        tenant_id=tid,
        window_days=30,
        gaps=[
            GapItem(id="g1", type="expected_not_executed", description="d1", evidence_pointers={}),
            GapItem(id="g2", type="discussed_not_linked_to_work", description="d2", evidence_pointers={}),
            GapItem(id="g3", type="blocker_not_tracked", description="d3", evidence_pointers={}),
            GapItem(id="g4", type="doc_not_connected_to_execution", description="d4", evidence_pointers={}),
        ],
    )
    out = compute_decisions(gaps, created_at=ts, include_decision_debug=False)
    assert out.run_id == rid and out.tenant_id == tid and out.window_days == 30
    assert len(out.items) == 4
    types = [row.decision.decision_type for row in out.items]
    assert types == [
        "LINK_OR_CLOSE_COMMITMENT",
        "THREAD_TO_TRACKING_LINK",
        "BLOCKER_ESCALATION",
        "DOC_EXECUTION_BRIDGE",
    ]
    assert out.items[0].decision.id == "coordination:decision:g1"
    assert out.items[0].decision_debug is None
    assert "§6 Step 22" in out.items[0].decision.rationale


def test_compute_decisions_empty_gaps() -> None:
    rid = uuid.uuid4()
    tid = uuid.uuid4()
    gaps = GapBundle(run_id=rid, tenant_id=tid, window_days=14, gaps=[])
    out = compute_decisions(gaps)
    assert out.items == []


def test_evidence_pointers_flattened_deduped() -> None:
    rid = uuid.uuid4()
    tid = uuid.uuid4()
    gaps = GapBundle(
        run_id=rid,
        tenant_id=tid,
        window_days=30,
        gaps=[
            GapItem(
                id="gx",
                type="expected_not_executed",
                description="x",
                evidence_pointers={"a": ["r1", "r2"], "b": ["r1"]},
            ),
        ],
    )
    out = compute_decisions(gaps, include_decision_debug=False)
    assert out.items[0].decision.evidence_refs == ["r1", "r2"]


def test_signal_refs_non_low_slots() -> None:
    rid = uuid.uuid4()
    tid = uuid.uuid4()
    gaps = GapBundle(
        run_id=rid,
        tenant_id=tid,
        window_days=30,
        gaps=[
            GapItem(id="g1", type="blocker_not_tracked", description="b", evidence_pointers={}),
        ],
    )
    sig = _sig(
        urgent_pressure="high",
        scope_ambiguity="moderate",
        discussion_churn="high",
        contradiction_density="high",
        repeated_discussion_present=True,
    )
    out = compute_decisions(gaps, signals=sig, include_decision_debug=False)
    refs = out.items[0].decision.signal_refs
    assert set(refs) == {
        "urgent_pressure",
        "scope_ambiguity",
        "discussion_churn",
        "contradiction_density",
        "repeated_discussion_present",
    }


def test_decision_debug_when_enabled() -> None:
    rid = uuid.uuid4()
    tid = uuid.uuid4()
    gaps = GapBundle(
        run_id=rid,
        tenant_id=tid,
        window_days=30,
        gaps=[GapItem(id="g9", type="expected_not_executed", description="z", evidence_pointers={})],
    )
    out = compute_decisions(gaps, include_decision_debug=True)
    assert out.items[0].decision_debug is not None
    assert out.items[0].decision_debug.matched_rule == "gap:expected_not_executed:v1"
    assert out.items[0].decision_debug.gap_id == "g9"


def test_step25_clarify_spec_when_scope_ambiguity_high() -> None:
    rid = uuid.uuid4()
    tid = uuid.uuid4()
    gaps = GapBundle(
        run_id=rid,
        tenant_id=tid,
        window_days=30,
        gaps=[
            GapItem(id="ga", type="discussed_not_linked_to_work", description="thread", evidence_pointers={}),
        ],
    )
    sig = _sig(scope_ambiguity="high")
    out = compute_decisions(gaps, signals=sig, include_decision_debug=False)
    assert out.items[0].decision.decision_type == "CLARIFY_SPEC"
    assert "Clarify scope" in out.items[0].decision.title
    assert "§6 Step 25" in out.items[0].decision.rationale


def test_step25_recenter_when_contradiction_and_churn_high_discussed_gap() -> None:
    rid = uuid.uuid4()
    tid = uuid.uuid4()
    gaps = GapBundle(
        run_id=rid,
        tenant_id=tid,
        window_days=30,
        gaps=[
            GapItem(id="gb", type="discussed_not_linked_to_work", description="mixed signals", evidence_pointers={}),
        ],
    )
    sig = _sig(contradiction_density="high", discussion_churn="high", scope_ambiguity="high")
    out = compute_decisions(gaps, signals=sig, include_decision_debug=True)
    d = out.items[0].decision
    assert d.decision_type == "RECENTER"
    assert out.items[0].decision_debug is not None
    assert out.items[0].decision_debug.matched_rule == "extension:recenter_contradiction_churn:v1"
    assert out.items[0].decision_debug.conditions_met.get("extension_route") is True


def test_step25_pause_investment_when_contradiction_and_churn_high_expected_gap() -> None:
    rid = uuid.uuid4()
    tid = uuid.uuid4()
    gaps = GapBundle(
        run_id=rid,
        tenant_id=tid,
        window_days=30,
        gaps=[GapItem(id="gc", type="expected_not_executed", description="late", evidence_pointers={})],
    )
    sig = _sig(contradiction_density="high", discussion_churn="high")
    out = compute_decisions(gaps, signals=sig, include_decision_debug=False)
    assert out.items[0].decision.decision_type == "PAUSE_INVESTMENT"


def test_step25_blocker_gap_unchanged_when_contradiction_and_churn_high() -> None:
    """Blocker escalation stays base — extension table does not remap this gap type."""
    rid = uuid.uuid4()
    tid = uuid.uuid4()
    gaps = GapBundle(
        run_id=rid,
        tenant_id=tid,
        window_days=30,
        gaps=[GapItem(id="gd", type="blocker_not_tracked", description="b", evidence_pointers={})],
    )
    sig = _sig(contradiction_density="high", discussion_churn="high")
    out = compute_decisions(gaps, signals=sig, include_decision_debug=False)
    assert out.items[0].decision.decision_type == "BLOCKER_ESCALATION"


def test_step25_doc_gap_recenter_under_contradiction_churn() -> None:
    rid = uuid.uuid4()
    tid = uuid.uuid4()
    gaps = GapBundle(
        run_id=rid,
        tenant_id=tid,
        window_days=30,
        gaps=[GapItem(id="ge", type="doc_not_connected_to_execution", description="doc", evidence_pointers={})],
    )
    sig = _sig(contradiction_density="high", discussion_churn="high")
    out = compute_decisions(gaps, signals=sig, include_decision_debug=False)
    assert out.items[0].decision.decision_type == "RECENTER"
