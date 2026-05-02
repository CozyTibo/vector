"""§6 Steps 22 + 25 — compute_decisions: execution situations → decisions (unified pipeline)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from vector.contracts.manager_insights_activity import (
    GapBundle,
    GapItem,
    SignalsV0Debug,
    WorkItem,
    WorkItemBundle,
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


def test_compute_decisions_produces_multiple_situations_for_four_gaps() -> None:
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
    assert 1 <= len(out.items) <= 3
    assert sum(1 for r in out.items if r.decision.dominant) == 1
    for row in out.items:
        assert row.decision.gap_type == "aggregated_situation"
    types = {row.decision.decision_type for row in out.items}
    assert "MAKE_BLOCKERS_EXPLICIT" in types
    assert out.items[0].decision.dominant is True
    assert "**System state:**" in out.items[0].decision.rationale


def test_multi_gap_decision_debug_includes_execution_situation() -> None:
    rid = uuid.uuid4()
    tid = uuid.uuid4()
    gaps = GapBundle(
        run_id=rid,
        tenant_id=tid,
        window_days=30,
        gaps=[
            GapItem(id="a", type="blocker_not_tracked", description="b1", evidence_pointers={}),
            GapItem(id="b", type="blocker_not_tracked", description="b2", evidence_pointers={}),
            GapItem(id="c", type="blocker_not_tracked", description="b3", evidence_pointers={}),
        ],
    )
    sig = _sig()
    out = compute_decisions(gaps, signals=sig, include_decision_debug=True)
    assert len(out.items) >= 2
    kinds = {row.decision_debug.execution_situation for row in out.items if row.decision_debug}
    assert "INVISIBLE_BLOCKERS" in kinds
    top = next(r for r in out.items if r.decision_debug and r.decision_debug.execution_situation == "INVISIBLE_BLOCKERS")
    assert top.decision_debug is not None
    assert top.decision_debug.situation_support_count >= 1
    assert top.decision_debug.matched_rule.startswith("execution_situation:")


def test_cross_failure_dominance_folds_non_surface_modes_into_supporting_failure_modes() -> None:
    """Dominant failure mode + up to two orthogonal decisions; remainder attach as supporting_failure_modes."""
    rid = uuid.uuid4()
    tid = uuid.uuid4()
    gaps = GapBundle(
        run_id=rid,
        tenant_id=tid,
        window_days=30,
        gaps=[
            GapItem(id="g1", type="discussed_not_linked_to_work", description="d", evidence_pointers={}),
            GapItem(id="g2", type="expected_not_executed", description="d2", evidence_pointers={}),
            GapItem(id="g3", type="blocker_not_tracked", description="b", evidence_pointers={}),
        ],
    )
    actor = uuid.uuid4()
    wi = WorkItemBundle(
        run_id=rid,
        tenant_id=tid,
        window_days=30,
        items=[
            WorkItem(
                id="linear:o1",
                source="linear",
                type="issue",
                title="A",
                status="open",
                owner_actor_id=actor,
                participants=[],
                source_ref={},
            ),
            WorkItem(
                id="linear:o2",
                source="linear",
                type="issue",
                title="B",
                status="open",
                owner_actor_id=actor,
                participants=[],
                source_ref={},
            ),
            WorkItem(
                id="linear:o3",
                source="linear",
                type="issue",
                title="C",
                status="open",
                owner_actor_id=actor,
                participants=[],
                source_ref={},
            ),
        ],
    )
    sig = _sig(
        discussion_churn="high",
        contradiction_density="high",
        actor_fragmentation=8,
        actor_load=0,
        actor_consistency=0.0,
    )
    out = compute_decisions(gaps, signals=sig, work_items=wi, include_decision_debug=False)
    assert len(out.items) <= 3
    assert sum(1 for r in out.items if r.decision.dominant) == 1
    primary = next(r for r in out.items if r.decision.dominant)
    assert "primary driver of execution failure" in primary.decision.title
    sfm = primary.decision.required_inputs.get("supporting_failure_modes")
    assert isinstance(sfm, list) and len(sfm) >= 1
    assert any(entry.get("failure_mode") == "INVISIBLE_BLOCKERS" for entry in sfm)
    related = [r.decision.title for r in out.items if not r.decision.dominant]
    assert any(t.startswith("Related:") for t in related)


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
    assert "r1" in out.items[0].decision.evidence_refs and "r2" in out.items[0].decision.evidence_refs


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
    refs: set[str] = set()
    for row in out.items:
        refs.update(row.decision.signal_refs)
    assert "urgent_pressure" in refs
    assert "execution_situation:MISALIGNED_REALITY" in refs or "execution_situation:INVISIBLE_BLOCKERS" in refs


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
    assert len(out.items) >= 2
    dbg0 = out.items[0].decision_debug
    assert dbg0 is not None
    assert dbg0.matched_rule.startswith("execution_situation:")
    assert dbg0.execution_situation is not None
    assert dbg0.situation_support_count >= 1


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
    out = compute_decisions(gaps, signals=sig, include_decision_debug=True)
    clarify = next(r for r in out.items if r.decision.decision_type == "CLARIFY_SPEC")
    assert "Clarify" in clarify.decision.title or "scope" in clarify.decision.title.lower()
    assert clarify.decision_debug is not None
    assert "SCOPE_DRIFT" in (clarify.decision_debug.matched_rule or "") or "CLARIFY_SPEC" in (
        clarify.decision_debug.matched_rule or ""
    )


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
    d = next(r for r in out.items if r.decision.decision_type == "RESOLVE_STATE_MISMATCH").decision
    assert d.decision_type == "RESOLVE_STATE_MISMATCH"
    row = next(r for r in out.items if r.decision.decision_type == "RESOLVE_STATE_MISMATCH")
    assert row.decision_debug is not None
    assert row.decision_debug.execution_situation == "MISALIGNED_REALITY"


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
    recenter = next((r.decision for r in out.items if r.decision.decision_type == "RECENTER_WORK"), None)
    assert recenter is not None


def test_step25_blocker_under_contradiction_prefers_state_then_blockers() -> None:
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
    types = [r.decision.decision_type for r in out.items]
    assert "RESOLVE_STATE_MISMATCH" in types
    assert "MAKE_BLOCKERS_EXPLICIT" in types


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
    assert any(r.decision.decision_type == "RESOLVE_STATE_MISMATCH" for r in out.items)
