"""§6 Steps 22–26 + Step 7 — execution narrative → managerial decisions (deterministic, no LLM).

Pipeline: ``gaps + signals → ExecutionSituation[] → collapse by failure mode → cross-failure dominance
→ compose_execution_narrative_from_ordered → DecisionItem[]`` (1 primary diagnosis + up to 2 orthogonal
supporting decisions; other failure modes fold into ``required_inputs["supporting_failure_modes"]``).
"""

from __future__ import annotations

import hashlib
from collections import defaultdict
from datetime import UTC, datetime
from typing import Any, Literal

from vector.contracts.manager_insights_activity import (
    CoordinationDecisionType,
    CoordinationLinkInputBundle,
    DecisionBundle,
    DecisionBundleItem,
    DecisionDefaultAction,
    DecisionItem,
    DecisionRuleTraceDebug,
    EvidenceBundle,
    ExecutionSituation,
    ExecutionSituationType,
    GapBundle,
    GapItem,
    LinkBundle,
    SignalsV0Debug,
    WorkItemBundle,
)
from vector.domains.manager_insights.compose_execution_narrative import (
    ExecutionNarrative,
    compose_execution_narrative_from_ordered,
)
from vector.domains.manager_insights.detect_execution_situations import (
    SITUATION_TO_DECISION,
    detect_execution_situations,
    situation_axis_key,
)
from pydantic import ValidationError

from vector.domains.manager_insights.artifact_decision_context import (
    artifact_action_targets_payload,
    build_deterministic_artifact_interpretation,
    merge_required_inputs_artifact_targets,
    select_primary_work_items,
)
from vector.domains.manager_insights.llm_interpretation import interpret_decision_with_llm
from vector.settings import get_settings

_MAX_SURFACE_DECISIONS = 3  # 1 cross-failure dominant + up to 2 orthogonal supporting
_MAX_GAP_IDS_AGGREGATE = 16

_FAILURE_OWNERSHIP = "OWNERSHIP_FAILURE"
_FAILURE_DECISION = "DECISION_FAILURE"
_FAILURE_EXECUTION_ALIGNMENT = "EXECUTION_ALIGNMENT_FAILURE"
_KNOWN_FAILURE_MODES = frozenset(
    {_FAILURE_OWNERSHIP, _FAILURE_DECISION, _FAILURE_EXECUTION_ALIGNMENT},
)

SITUATION_TO_FAILURE_MODE: dict[ExecutionSituationType, str] = {
    "OWNERSHIP_FRAGMENTED": _FAILURE_OWNERSHIP,
    "KEY_PERSON_BOTTLENECK": _FAILURE_OWNERSHIP,
    "UNKNOWN_OWNERSHIP": _FAILURE_OWNERSHIP,
    "DECISION_NOT_CONNECTED_TO_OWNER": _FAILURE_DECISION,
    "DECISION_LOOP": _FAILURE_DECISION,
    "MISALIGNED_REALITY": _FAILURE_EXECUTION_ALIGNMENT,
    "SHADOW_WORK": _FAILURE_EXECUTION_ALIGNMENT,
}


def _failure_mode_bucket(situ: ExecutionSituation) -> str:
    """Group key: named failure mode, else the situation type itself (singleton group)."""
    return SITUATION_TO_FAILURE_MODE.get(situ.type, situ.type)


def _merge_actor_metrics_for_group(members: list[ExecutionSituation]) -> dict[str, Any] | None:
    rows: list[dict[str, Any]] = []
    for m in members:
        if m.actor_situation_metrics:
            rows.append({"situation_type": m.type, "metrics": m.actor_situation_metrics})
    if not rows:
        return None
    return {"failure_mode_aggregation": True, "by_situation": rows}


def _collapse_situations_by_failure_mode(situations: list[ExecutionSituation]) -> list[ExecutionSituation]:
    """One representative ``ExecutionSituation`` per failure-mode bucket (or per unmapped type)."""
    if not situations:
        return []
    groups: dict[str, list[ExecutionSituation]] = defaultdict(list)
    for s in situations:
        groups[_failure_mode_bucket(s)].append(s)
    out: list[ExecutionSituation] = []
    for mode_key, members in groups.items():
        members_sorted = sorted(
            members,
            key=lambda x: (-x.severity, -len(x.supporting_gap_ids), x.type),
        )
        rep = members_sorted[0]
        gap_seen: set[str] = set()
        merged_gaps: list[str] = []
        for m in members_sorted:
            for gid in m.supporting_gap_ids:
                if gid not in gap_seen:
                    gap_seen.add(gid)
                    merged_gaps.append(gid)
        merged_gaps = merged_gaps[:_MAX_GAP_IDS_AGGREGATE]
        sig_seen: set[str] = set()
        merged_sigs: list[str] = []
        for m in members_sorted:
            for sig in m.supporting_signals:
                if sig not in sig_seen:
                    sig_seen.add(sig)
                    merged_sigs.append(sig)
        sev = max(m.severity for m in members_sorted)
        distinct_types: list[ExecutionSituationType] = []
        dt_seen: set[ExecutionSituationType] = set()
        for m in members_sorted:
            if m.type not in dt_seen:
                dt_seen.add(m.type)
                distinct_types.append(m.type)
        supporting_types = [t for t in distinct_types if t != rep.type]
        afm: str | None = mode_key if mode_key in _KNOWN_FAILURE_MODES else None
        actor_m = _merge_actor_metrics_for_group(members_sorted)
        out.append(
            ExecutionSituation(
                type=rep.type,
                severity=sev,
                supporting_gap_ids=merged_gaps,
                supporting_signals=merged_sigs,
                rationale=rep.rationale,
                decision_override=rep.decision_override,
                hold_start_emission_trace=rep.hold_start_emission_trace,
                actor_situation_metrics=actor_m,
                aggregated_failure_mode=afm,
                aggregated_supporting_situation_types=supporting_types,
            )
        )
    return out


def _failure_mode_key_for_dominance(s: ExecutionSituation) -> str:
    return s.aggregated_failure_mode or str(s.type)


def _actor_signal_strength(s: ExecutionSituation, sig: SignalsV0Debug) -> float:
    strength = 0.0
    m = s.actor_situation_metrics
    if isinstance(m, dict):
        by = m.get("by_situation")
        if isinstance(by, list) and len(by) > 0:
            strength += min(0.3, 0.1 * len(by))
        elif m.get("rule"):
            strength += 0.12
        elif m.get("actor_fragmentation_observed") is not None:
            try:
                obs = float(m.get("actor_fragmentation_observed", 0))
            except (TypeError, ValueError):
                obs = 0.0
            strength += min(0.2, 0.03 * obs)
        elif m.get("max_owner_share_of_open_execution") is not None:
            try:
                share = float(m.get("max_owner_share_of_open_execution", 0))
            except (TypeError, ValueError):
                share = 0.0
            if share > 0.4:
                strength += min(0.18, 0.25 * share)
    if strength < 0.08 and s.aggregated_failure_mode in _KNOWN_FAILURE_MODES:
        frag = min(1.0, sig.actor_fragmentation / 20.0)
        load = min(1.0, sig.actor_load / 12.0)
        cons = max(0.0, min(1.0, sig.actor_consistency))
        strength += min(0.12, 0.06 * frag + 0.04 * load + 0.02 * cons)
    return min(0.45, strength)


def _dominance_score_failure_row(s: ExecutionSituation, sig: SignalsV0Debug) -> float:
    gaps_n = len(s.supporting_gap_ids)
    return s.severity * 0.5 + min(1.0, gaps_n / 16.0) * 0.35 + _actor_signal_strength(s, sig)


def _related_failure_mode_line(s: ExecutionSituation) -> str:
    if s.aggregated_failure_mode == _FAILURE_DECISION:
        return "Related: decisions are not sticking"
    if s.aggregated_failure_mode == _FAILURE_EXECUTION_ALIGNMENT:
        return "Related: execution is misaligned"
    if s.aggregated_failure_mode == _FAILURE_OWNERSHIP:
        return "Related: ownership is under strain"
    return f"Related: {str(s.type).replace('_', ' ').lower()}"


def _supporting_failure_mode_payload(s: ExecutionSituation) -> dict[str, Any]:
    key = s.aggregated_failure_mode or str(s.type)
    return {
        "failure_mode": key,
        "representative_situation_type": s.type,
        "severity": s.severity,
        "underlying_gap_count": len(s.supporting_gap_ids),
        "supporting_situation_types": list(s.aggregated_supporting_situation_types),
        "related_title": _related_failure_mode_line(s),
    }


def _select_cross_failure_dominance(
    collapsed: list[ExecutionSituation],
    sig: SignalsV0Debug,
) -> tuple[ExecutionSituation, tuple[ExecutionSituation, ...], list[dict[str, Any]]]:
    if not collapsed:
        msg = "cross-failure dominance requires at least one collapsed situation"
        raise ValueError(msg)

    scored = sorted(
        collapsed,
        key=lambda s: (
            -_dominance_score_failure_row(s, sig),
            -s.severity,
            -len(s.supporting_gap_ids),
            _failure_mode_key_for_dominance(s),
        ),
    )
    dominant = scored[0]
    rest = scored[1:]
    dominant_axis = situation_axis_key(dominant)[0]

    orthogonal: list[ExecutionSituation] = []
    for s in sorted(
        rest,
        key=lambda x: (
            -_dominance_score_failure_row(x, sig),
            -x.severity,
            _failure_mode_key_for_dominance(x),
        ),
    ):
        if len(orthogonal) >= 2:
            break
        if situation_axis_key(s)[0] != dominant_axis:
            orthogonal.append(s)

    orth_ids = {id(x) for x in orthogonal}
    supporting_failure_modes: list[dict[str, Any]] = []
    for s in rest:
        if id(s) in orth_ids:
            continue
        supporting_failure_modes.append(_supporting_failure_mode_payload(s))

    return dominant, tuple(orthogonal), supporting_failure_modes


# Fallback titles only when situation-specific copy is missing.
_FALLBACK_TITLE: dict[CoordinationDecisionType, str] = {
    "MAKE_BLOCKERS_EXPLICIT": "Blockers are discussed but not reliably tracked — make them explicit",
    "UNBLOCK_REVIEW": "Reviews and handoffs are bottlenecking commitments",
    "REALIGN_PRIORITY": "Urgent work is competing without a clear sequence",
    "STRUCTURE_INCIDENT": "Reactive coordination needs an incident-style structure",
    "BLOCK_RELEASE": "Shipping risk is elevated until blockers and state reconcile",
    "RESOLVE_STATE_MISMATCH": "Tools disagree on execution state — reconcile before more build",
    "FORCE_DECISION": "Discussion is looping without durable decisions in tracking",
    "REDUCE_WIP": "Too much is in flight for the coordination bandwidth available",
    "ASSIGN_OWNER": "Ownership is ambiguous across threads and issues",
    "CAPTURE_WORK": "Work is living off-ticket where planning cannot see it",
    "SPLIT_SCOPE": "Scope is drifting relative to committed execution",
    "HOLD_START": "Hold new tracked work until scope is explicit in tracking",
    "CLARIFY_SPEC": "Clarify scope and constraints before more execution lands",
    "RECENTER_WORK": "Pause incremental work until priorities match reality",
}


def _neutral_signals() -> SignalsV0Debug:
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
            "scope_ambiguity": "low",
            "discussion_churn": "low",
            "contradiction_density": "low",
            "explain": {},
        }
    )


def _evidence_refs(gap: GapItem) -> list[str]:
    out: list[str] = []
    for _k, vals in sorted(gap.evidence_pointers.items()):
        out.extend(vals)
    seen: set[str] = set()
    unique: list[str] = []
    for x in out:
        if x not in seen:
            seen.add(x)
            unique.append(x)
    return unique


def _aggregate_evidence_refs(by_id_gap: dict[str, GapItem], situ: ExecutionSituation) -> list[str]:
    out: list[str] = []
    for gid in situ.supporting_gap_ids:
        g = by_id_gap.get(gid)
        if g:
            out.extend(_evidence_refs(g))
    seen: set[str] = set()
    uniq: list[str] = []
    for x in out:
        if x not in seen:
            seen.add(x)
            uniq.append(x)
    return uniq


def _signal_refs(signals: SignalsV0Debug) -> list[str]:
    refs: list[str] = []
    if signals.urgent_pressure != "low":
        refs.append("urgent_pressure")
    if signals.scope_ambiguity != "low":
        refs.append("scope_ambiguity")
    if signals.discussion_churn != "low":
        refs.append("discussion_churn")
    if signals.contradiction_density != "low":
        refs.append("contradiction_density")
    if signals.repeated_discussion_present:
        refs.append("repeated_discussion_present")
    return refs


def _signal_refs_situation(signals: SignalsV0Debug, situ: ExecutionSituation) -> list[str]:
    refs = _signal_refs(signals)
    refs.extend(situ.supporting_signals)
    refs.append(f"execution_situation:{situ.type}")
    if situ.aggregated_failure_mode:
        refs.append(f"failure_mode_aggregate:{situ.aggregated_failure_mode}")
    for st in situ.aggregated_supporting_situation_types:
        refs.append(f"execution_situation:{st}")
    seen: set[str] = set()
    out: list[str] = []
    for x in refs:
        if x not in seen:
            seen.add(x)
            out.append(x)
    return out


def _decision_id_situation(situ: ExecutionSituation) -> str:
    head = situ.aggregated_failure_mode or situ.type
    blob = f"{head}:{situ.decision_override or ''}:{','.join(sorted(situ.supporting_gap_ids))}"
    h = hashlib.sha1(blob.encode()).hexdigest()[:16]
    slug = str(head).lower().replace("_", "-")
    return f"coordination:decision:situation:{slug}:{h}"


def _supporting_type_labels(narr: ExecutionNarrative) -> frozenset[ExecutionSituationType]:
    return frozenset(s.type for s in narr.supporting)


def _situation_title(
    situ: ExecutionSituation,
    decision_type: CoordinationDecisionType,
    sig: SignalsV0Debug,
    *,
    dominant: bool,
    narrative: ExecutionNarrative,
    title_profile: Literal["cross_primary", "cross_orthogonal", "default"] = "default",
) -> str:
    n = len(situ.supporting_gap_ids)
    st = _supporting_type_labels(narrative)

    if title_profile == "cross_orthogonal" and situ.aggregated_failure_mode in _KNOWN_FAILURE_MODES:
        if situ.aggregated_failure_mode == _FAILURE_OWNERSHIP:
            return "Related: ownership is under strain"
        if situ.aggregated_failure_mode == _FAILURE_DECISION:
            return "Related: decisions are not sticking"
        if situ.aggregated_failure_mode == _FAILURE_EXECUTION_ALIGNMENT:
            return "Related: execution is misaligned"

    if title_profile == "cross_primary" and situ.aggregated_failure_mode in _KNOWN_FAILURE_MODES:
        if situ.aggregated_failure_mode == _FAILURE_OWNERSHIP:
            return "Ownership structure is broken — this is the primary driver of execution failure"
        if situ.aggregated_failure_mode == _FAILURE_DECISION:
            return "Decision structures are failing — this is the primary driver of execution failure"
        if situ.aggregated_failure_mode == _FAILURE_EXECUTION_ALIGNMENT:
            return "Execution alignment is failing — this is the primary driver of execution failure"

    if dominant and narrative.theme == "coordination_breakdown" and situ.type == "INVISIBLE_BLOCKERS" and "DECISION_LOOP" in st:
        return (
            "Execution is slowing because blockers are discussed but not tracked **and** high-churn discussion "
            "is not producing durable decisions — make blockers explicit and force closure in the same breath"
        )
    if dominant and narrative.theme == "lack_of_focus" and situ.type == "FRAGMENTED_EXECUTION" and "PRIORITY_CONFLICT" in st:
        return (
            "The team lacks focus: parallel WIP is fighting urgent, unprioritized pulls — narrow scope before priorities move again"
        )
    if dominant and narrative.theme == "execution_confusion" and situ.type == "MISALIGNED_REALITY" and "SCOPE_DRIFT" in st:
        return (
            "Execution confusion: contradictory state signals and drifting scope are compounding — align reality then split scope"
        )
    if dominant and narrative.theme == "delivery_friction" and situ.type == "REVIEW_BOTTLENECK":
        return (
            "Delivery friction: reviews and handoffs are lagging while momentum is not recovering — unblock the review path first"
        )

    if title_profile == "default" and situ.aggregated_failure_mode == _FAILURE_OWNERSHIP:
        t = "Ownership structure is broken — work is not clearly owned"
        return t if dominant else "Related ownership-system failure — sequence after the headline move"
    if title_profile == "default" and situ.aggregated_failure_mode == _FAILURE_DECISION:
        t = "Decisions are not sticking to execution — discussion and shipped work are disconnected"
        return t if dominant else "Related decision–execution disconnect — reinforce the headline move"
    if title_profile == "default" and situ.aggregated_failure_mode == _FAILURE_EXECUTION_ALIGNMENT:
        t = "Execution reality is misaligned — work lives in the wrong surfaces"
        return t if dominant else "Related alignment failure — reinforce the headline move"

    if situ.type == "INVISIBLE_BLOCKERS":
        mom = "slowing" if sig.execution_momentum == "slowing" else "stalling"
        base = (
            f"Execution is {mom} because blockers are discussed but not tracked across "
            f"{'this thread' if n == 1 else f'{n} coordination gaps'} — make them explicit with owners"
        )
        return base if dominant else f"Consequence — {base[0].lower()}{base[1:]}"
    if situ.type == "MISALIGNED_REALITY":
        t = (
            "Slack, issues, and PRs disagree on what is blocked versus done — align reality before the next commitment"
        )
        return t if dominant else f"Consequence — {t[0].lower()}{t[1:]}"
    if situ.type == "DECISION_LOOP":
        t = "High churn discussion without durable decisions in tracking — force closure on the next conversation"
        return t if dominant else f"Consequence — {t[0].lower()}{t[1:]}"
    if situ.type == "PRIORITY_CONFLICT":
        t = "Urgent pressure is fighting weak follow-through — realign what ships first and who owns tradeoffs"
        return t if dominant else f"Consequence — {t[0].lower()}{t[1:]}"
    if situ.type == "FRAGMENTED_EXECUTION":
        t = "Parallel work and weak momentum together — narrow WIP so coordination can finish something"
        return t if dominant else f"Consequence — {t[0].lower()}{t[1:]}"
    if situ.type == "SCOPE_DRIFT" and situ.decision_override == "HOLD_START":
        return "Scope is ambiguous and the open-execution neighborhood is large — hold new starts until scope is explicit"
    if situ.type == "SCOPE_DRIFT" and situ.decision_override == "CLARIFY_SPEC":
        return "Scope is still ambiguous — clarify constraints and owners before more build lands"
    if situ.type == "SCOPE_DRIFT":
        t = "Requirements and docs are drifting away from committed execution — split and re-estimate scope"
        return t if dominant else f"Consequence — {t[0].lower()}{t[1:]}"
    if situ.type == "REVIEW_BOTTLENECK":
        t = "Commitments are waiting on reviews and handoffs — unblock review latency with named reviewers"
        return t if dominant else f"Consequence — {t[0].lower()}{t[1:]}"
    if situ.type == "SHADOW_WORK":
        t = "Work is negotiated in Slack-only threads — capture it where execution is reviewable"
        return t if dominant else f"Consequence — {t[0].lower()}{t[1:]}"
    if situ.type == "OWNERSHIP_CONFUSION":
        t = "No single accountable owner while multiple actors participate — assign a DRI on tracked work"
        return t if dominant else f"Consequence — {t[0].lower()}{t[1:]}"
    if situ.type == "RISKY_SHIPPING":
        t = "Delivery signal is weak with open risk — block release until blockers and state reconcile"
        return t if dominant else f"Consequence — {t[0].lower()}{t[1:]}"
    if situ.type == "UNCONTROLLED_INCIDENT":
        t = "Reactive, high-churn coordination — structure roles, cadence, and exit criteria like an incident"
        return t if dominant else f"Consequence — {t[0].lower()}{t[1:]}"
    if situ.type == "OWNERSHIP_FRAGMENTED":
        t = "Too many distinct coordination identities — narrow owners and reconcile cross-tool actor mapping"
        return t if dominant else f"Consequence — {t[0].lower()}{t[1:]}"
    if situ.type == "KEY_PERSON_BOTTLENECK":
        t = "Open execution is concentrated on one actor — redistribute ownership and drain the bottleneck queue"
        return t if dominant else f"Consequence — {t[0].lower()}{t[1:]}"
    if situ.type == "DECISION_NOT_CONNECTED_TO_OWNER":
        t = "Discussion identities do not match execution owners — link conversations to the DRI on tracked work"
        return t if dominant else f"Consequence — {t[0].lower()}{t[1:]}"
    if situ.type == "UNKNOWN_OWNERSHIP":
        t = "Most participant slots lack resolved actors — backfill identities before scaling coordination automation"
        return t if dominant else f"Consequence — {t[0].lower()}{t[1:]}"
    fb = _FALLBACK_TITLE.get(decision_type, f"Coordination: {decision_type.replace('_', ' ').lower()}")
    return fb if dominant else f"Consequence — {fb[0].lower()}{fb[1:]}"


def _situation_rationale(
    situ: ExecutionSituation,
    decision_type: CoordinationDecisionType,
    sig: SignalsV0Debug,
    *,
    dominant: bool,
    narrative: ExecutionNarrative,
) -> str:
    sig_line = (
        f"Signals in play: churn={sig.discussion_churn}, contradiction={sig.contradiction_density}, "
        f"momentum={sig.execution_momentum}, focus={sig.focus}, urgent_pressure={sig.urgent_pressure}, "
        f"follow_through={sig.follow_through}."
    )
    if dominant:
        theme_line = (
            f"Narrative frame: **{narrative.theme.replace('_', ' ')}** — this is the primary diagnosis for the run."
            if narrative.theme
            else "Narrative frame: single dominant execution risk for this window."
        )
        supp = ", ".join(s.type for s in narrative.supporting) or "none listed"
        parts = [
            f"**System state:** {situ.rationale.strip()}",
            theme_line,
            sig_line,
            f"**Connected gaps:** {len(situ.supporting_gap_ids)} underlying gap(s) anchor this story; "
            f"supporting dimensions to close in parallel: {supp}.",
            f"**What to do next:** execute **{decision_type}** as the headline managerial move.",
        ]
        if situ.hold_start_emission_trace is not None:
            parts.append(situ.hold_start_emission_trace.reason)
        return " ".join(parts)
    parts = [
        "**Supporting consequence:** " + situ.rationale.strip(),
        "This row reinforces or explains the headline diagnosis — it should be sequenced after the dominant move.",
        sig_line,
        f"**What to do next:** execute **{decision_type}** without letting it compete for ownership with the headline item.",
    ]
    if situ.hold_start_emission_trace is not None:
        parts.append(situ.hold_start_emission_trace.reason)
    return " ".join(parts)


def _bundle_from_situation(
    situ: ExecutionSituation,
    *,
    gaps: GapBundle,
    sig: SignalsV0Debug,
    ts: datetime,
    include_decision_debug: bool,
    dominant: bool,
    narrative: ExecutionNarrative,
    title_profile: Literal["cross_primary", "cross_orthogonal", "default"] = "default",
    supporting_failure_modes: list[dict[str, Any]] | None = None,
) -> DecisionBundleItem:
    by_gap = {g.id: g for g in gaps.gaps}
    d_type = situ.decision_override or SITUATION_TO_DECISION[situ.type]
    synthetic_gap_id = _decision_id_situation(situ)
    title = _situation_title(
        situ,
        d_type,
        sig,
        dominant=dominant,
        narrative=narrative,
        title_profile=title_profile,
    )
    rationale = _situation_rationale(situ, d_type, sig, dominant=dominant, narrative=narrative)
    if dominant:
        req = {
            "underlying_gap_ids": list(situ.supporting_gap_ids),
            "narrative_theme": narrative.theme,
            "narrative_supporting_situation_types": [s.type for s in narrative.supporting],
        }
        if supporting_failure_modes:
            req["supporting_failure_modes"] = supporting_failure_modes
    else:
        req = {
            "underlying_gap_ids": list(situ.supporting_gap_ids),
            "narrative_theme": narrative.theme,
            "narrative_headline_situation_type": narrative.dominant.type,
        }
    if situ.aggregated_failure_mode:
        req["failure_mode"] = situ.aggregated_failure_mode
    if situ.aggregated_supporting_situation_types:
        req["supporting_situation_types"] = list(situ.aggregated_supporting_situation_types)
    decision = DecisionItem(
        id=synthetic_gap_id,
        gap_id=synthetic_gap_id,
        gap_type="aggregated_situation",
        decision_type=d_type,
        title=title,
        rationale=rationale,
        default_action=DecisionDefaultAction(kind="noop"),
        required_inputs=req,
        evidence_refs=_aggregate_evidence_refs(by_gap, situ),
        signal_refs=_signal_refs_situation(sig, situ),
        dominant=dominant,
        created_at=ts,
        run_id=gaps.run_id,
        status=None,
    )
    dbg: DecisionRuleTraceDebug | None = None
    if include_decision_debug:
        matched = f"execution_situation:{situ.type}" + (f":{situ.decision_override}" if situ.decision_override else "")
        if situ.aggregated_failure_mode:
            matched = f"failure_mode_aggregate:{situ.aggregated_failure_mode};{matched}"
        folded = [situ.type, *situ.aggregated_supporting_situation_types]
        cond_details = [situ.rationale[:220], *(list(narrative.relationship_labels)[:3])]
        if situ.aggregated_failure_mode:
            cond_details.insert(
                0,
                f"aggregated_failure_mode={situ.aggregated_failure_mode} folded={[str(t) for t in folded]}",
            )
        dbg = DecisionRuleTraceDebug(
            gap_id=synthetic_gap_id,
            matched_rule=matched,
            conditions_met={
                "execution_situation": True,
                "narrative_dominant": dominant,
                "severity": situ.severity >= 0.5,
                "hold_start_emitted": situ.decision_override == "HOLD_START",
                "failure_mode_aggregate": bool(situ.aggregated_failure_mode),
            },
            execution_failure=None,
            condition_details=cond_details,
            execution_situation=situ.type,
            situation_support_count=len(situ.supporting_gap_ids),
            narrative_theme=narrative.theme,
            narrative_dominant=dominant,
            actor_situation_metrics=situ.actor_situation_metrics,
        )
    return DecisionBundleItem(
        decision=decision,
        decision_debug=dbg,
        decision_emission_debug=situ.hold_start_emission_trace,
    )


def compute_decisions(
    gaps: GapBundle,
    *,
    signals: SignalsV0Debug | None = None,
    work_items: WorkItemBundle | None = None,
    links: LinkBundle | None = None,
    evidence: EvidenceBundle | None = None,
    coordination_input: CoordinationLinkInputBundle | None = None,
    hold_start_affected_wi_threshold: int = 2,
    gaps_use_graph_adjacency: bool = False,
    created_at: datetime | None = None,
    include_decision_debug: bool = True,
) -> DecisionBundle:
    """Build ``DecisionBundle`` via execution narrative (dominant + supporting)."""
    ts = created_at or datetime.now(UTC)
    if not gaps.gaps:
        return DecisionBundle(run_id=gaps.run_id, tenant_id=gaps.tenant_id, window_days=gaps.window_days, items=[])

    sig_eff = signals if signals is not None else _neutral_signals()
    perception_rows = coordination_input.perception_rows if coordination_input is not None else []
    situations = detect_execution_situations(
        gaps,
        sig_eff,
        perception_rows=perception_rows,
        work_items=work_items,
        links=links,
        evidence=evidence,
        coordination_input=coordination_input,
        hold_start_affected_wi_threshold=hold_start_affected_wi_threshold,
        gaps_use_graph=gaps_use_graph_adjacency,
    )
    collapsed = _collapse_situations_by_failure_mode(situations)
    dominant_situ, orthogonal_supports, supporting_failure_modes = _select_cross_failure_dominance(
        collapsed,
        sig_eff,
    )
    narrative = compose_execution_narrative_from_ordered(
        dominant_situ,
        orthogonal_supports,
        signals=sig_eff,
        total_gap_count=len(gaps.gaps),
    )
    items: list[DecisionBundleItem] = []
    items.append(
        _bundle_from_situation(
            dominant_situ,
            gaps=gaps,
            sig=sig_eff,
            ts=ts,
            include_decision_debug=include_decision_debug,
            dominant=True,
            narrative=narrative,
            title_profile="cross_primary",
            supporting_failure_modes=supporting_failure_modes or None,
        )
    )
    for s in orthogonal_supports[: _MAX_SURFACE_DECISIONS - 1]:
        items.append(
            _bundle_from_situation(
                s,
                gaps=gaps,
                sig=sig_eff,
                ts=ts,
                include_decision_debug=include_decision_debug,
                dominant=False,
                narrative=narrative,
                title_profile="cross_orthogonal",
            )
        )

    try:
        settings_llm = get_settings()
    except ValidationError:
        settings_llm = None

    enriched: list[DecisionBundleItem] = []
    for it in items:
        primary = select_primary_work_items(
            it,
            work_items=work_items,
            evidence=evidence,
            links=links,
            signals=sig_eff,
        )
        targets = artifact_action_targets_payload(primary)
        labels = [str(t["label"]) for t in targets if t.get("label")]
        req = merge_required_inputs_artifact_targets(it, targets)
        it_aug = it.model_copy(
            update={"decision": it.decision.model_copy(update={"required_inputs": req})},
        )
        det = build_deterministic_artifact_interpretation(it_aug, primary, labels)

        llm_out: dict[str, str | None] | None = None
        if (
            settings_llm is not None
            and settings_llm.vector_manager_insights_llm_interpretation
            and settings_llm.openai_api_key.strip()
        ):
            llm_out = interpret_decision_with_llm(
                it_aug,
                settings=settings_llm,
                work_items=work_items,
                evidence=evidence,
                links=links,
                signals=sig_eff,
            )

        use_llm = (
            llm_out is not None
            and isinstance(llm_out.get("llm_headline"), str)
            and isinstance(llm_out.get("llm_explanation"), str)
            and isinstance(llm_out.get("llm_next_step"), str)
            and llm_out["llm_headline"].strip()
            and llm_out["llm_explanation"].strip()
            and llm_out["llm_next_step"].strip()
        )
        chosen = (
            {
                "llm_headline": llm_out["llm_headline"],
                "llm_explanation": llm_out["llm_explanation"],
                "llm_next_step": llm_out["llm_next_step"],
            }
            if use_llm
            else det
        )
        enriched.append(
            it_aug.model_copy(
                update={
                    "llm_headline": chosen["llm_headline"],
                    "llm_explanation": chosen["llm_explanation"],
                    "llm_next_step": chosen["llm_next_step"],
                },
            ),
        )
    items = enriched

    return DecisionBundle(run_id=gaps.run_id, tenant_id=gaps.tenant_id, window_days=gaps.window_days, items=items)
