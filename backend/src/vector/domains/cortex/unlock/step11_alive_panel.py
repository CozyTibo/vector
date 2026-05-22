"""War-room step 11 — §9.1 alive criteria panel (Track A, A1–A6)."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from vector.domains.cortex.retrieval.retrieval_skip_registry import RET_SKIP_GRAPH_DISCONNECTED_V1
from vector.domains.cortex.unlock.step04_deploy_validation import evaluate_a4_canonical_motion_v1
from vector.domains.cortex.unlock.step05_identity_backfill import evaluate_a1_org_handles_v1
from vector.domains.cortex.unlock.step06_candidate_regen import evaluate_a3_candidate_links_v1
from vector.domains.cortex.unlock.step07_graph_density_promotion import evaluate_a2_authoritative_links_v1
from vector.domains.cortex.unlock.step09_octs_walk import (
    authoritative_hops_on_walk_payload_v1,
    evaluate_a5_octs_execution_continuity_v1,
)
from vector.domains.cortex.unlock.step10_retrieval import (
    evaluate_a6_evidence_recovery_v1,
    is_graph_disconnect_dominated_v1,
    summarize_ret_skip_codes_v1,
)

TRACK_A_PANEL_HOLD_HOURS_V1 = 48

PANEL_CRITERION_IDS_V1: tuple[str, ...] = (
    "A1",
    "A2",
    "A3",
    "A4",
    "A5",
    "A6",
)


def evaluate_anti_fake_green_v1(
    *,
    raw_minus_mat_admin_gap: int,
    alive_criteria_pass_count: int,
) -> tuple[bool, str]:
    """Anti-fake: primary KPI is A1–A6, not raw−mat convergence alone."""
    gap = int(raw_minus_mat_admin_gap)
    passed = int(alive_criteria_pass_count)
    if passed >= 6:
        return True, f"alive_criteria_pass_count={passed} (not chasing raw_minus_mat={gap})"
    if gap == 0 and passed < 4:
        return False, "raw_minus_mat_zero_but_alive_criteria_insufficient"
    return True, f"alive_criteria_pass_count={passed}:raw_minus_mat_admin_gap={gap}"


def build_alive_panel_evaluation_v1(
    *,
    org_entities_active: int,
    authoritative_links_active: int,
    link_candidates: int,
    lease_last_canonical_outcome: str | None,
    released_missing_parent_ref: int = 0,
    deferrals_before_total: int = 0,
    deferrals_after_total: int = 0,
    drain_total_succeeded: int = 0,
    drain_canonical_outcome: str | None = None,
    completed_walks: int,
    walks_with_authoritative_hop: int,
    entries_materialized: int,
    retrieval_skip_code_counts: dict[str, int],
    raw_minus_mat_admin_gap: int,
    panel_captured_at: str | None = None,
) -> dict[str, Any]:
    """Evaluate full §9.1 panel; step 11 passes when all criteria green at T0 (starts 48h clock)."""
    a1_ok, a1_detail = evaluate_a1_org_handles_v1(
        org_entities_active=int(org_entities_active),
        entities_upserted=0,
        anchors_scanned=0,
    )
    a2_ok, a2_detail = evaluate_a2_authoritative_links_v1(
        authoritative_links_active=int(authoritative_links_active),
    )
    a3_ok, a3_detail = evaluate_a3_candidate_links_v1(
        candidate_count=int(link_candidates),
    )
    a4_ok, a4_detail = evaluate_a4_canonical_motion_v1(
        drain_summary={
            "total_succeeded": int(drain_total_succeeded),
            "canonical_outcome": drain_canonical_outcome,
        },
        lease_last_canonical_outcome=lease_last_canonical_outcome,
        released_missing_parent_ref=int(released_missing_parent_ref),
        deferrals_before_total=int(deferrals_before_total),
        deferrals_after_total=int(deferrals_after_total),
    )
    a5_ok, a5_detail = evaluate_a5_octs_execution_continuity_v1(
        completed_walks=int(completed_walks),
        walks_with_authoritative_hop=int(walks_with_authoritative_hop),
    )
    a6_ok, a6_detail = evaluate_a6_evidence_recovery_v1(
        entries_materialized=int(entries_materialized),
        skip_code_counts=dict(retrieval_skip_code_counts),
    )

    criteria: dict[str, dict[str, Any]] = {
        "A1": {"pass": a1_ok, "detail": a1_detail, "metric": "org_entities_active", "value": org_entities_active},
        "A2": {
            "pass": a2_ok,
            "detail": a2_detail,
            "metric": "authoritative_links_active",
            "value": authoritative_links_active,
        },
        "A3": {"pass": a3_ok, "detail": a3_detail, "metric": "link_candidates", "value": link_candidates},
        "A4": {
            "pass": a4_ok,
            "detail": a4_detail,
            "metric": "canonical_execution_motion",
            "value": lease_last_canonical_outcome,
        },
        "A5": {
            "pass": a5_ok,
            "detail": a5_detail,
            "metric": "octs_walks_with_authoritative_hop",
            "value": walks_with_authoritative_hop,
        },
        "A6": {
            "pass": a6_ok,
            "detail": a6_detail,
            "metric": "evidence_recovery_entries",
            "value": entries_materialized,
            "graph_disconnect_dominated": is_graph_disconnect_dominated_v1(retrieval_skip_code_counts),
        },
    }

    alive_pass_count = sum(1 for c in criteria.values() if c.get("pass"))
    anti_ok, anti_detail = evaluate_anti_fake_green_v1(
        raw_minus_mat_admin_gap=int(raw_minus_mat_admin_gap),
        alive_criteria_pass_count=alive_pass_count,
    )

    all_alive = alive_pass_count == len(PANEL_CRITERION_IDS_V1)
    step11_ok = all_alive and anti_ok
    captured = panel_captured_at or datetime.now().isoformat()

    return {
        "panel_schema_version": 1,
        "panel_captured_at": captured,
        "criteria": criteria,
        "alive_criteria_pass_count": alive_pass_count,
        "alive_criteria_total": len(PANEL_CRITERION_IDS_V1),
        "anti_fake_pass": anti_ok,
        "anti_fake_detail": anti_detail,
        "track_a_panel_all_green_at_capture": all_alive,
        "track_a_panel_hold_hours_required": TRACK_A_PANEL_HOLD_HOURS_V1,
        "track_a_panel_hold_started_at": captured if step11_ok else None,
        "track_a_signoff_pending": step11_ok,
        "track_a_signoff_note": (
            "Re-run unlock_step11_alive_panel.py daily; Track A sign-off when panel "
            f"stays green for {TRACK_A_PANEL_HOLD_HOURS_V1}h without manual backfill wedges."
            if step11_ok
            else "Fix failing criteria before starting 48h hold clock."
        ),
        "step11_pass": step11_ok,
        "step11_detail": (
            f"panel_green_at_T0:alive={alive_pass_count}/{len(PANEL_CRITERION_IDS_V1)}"
            if step11_ok
            else f"panel_incomplete:alive={alive_pass_count}/{len(PANEL_CRITERION_IDS_V1)}"
        ),
        "ret_skip_code_counts": dict(retrieval_skip_code_counts),
        "RET_SKIP_GRAPH_DISCONNECTED_present": RET_SKIP_GRAPH_DISCONNECTED_V1
        in retrieval_skip_code_counts,
    }


def merge_retrieval_skip_counts_from_report(
    skip_reasons: list[dict[str, Any]],
) -> dict[str, int]:
    return summarize_ret_skip_codes_v1(skip_reasons)
