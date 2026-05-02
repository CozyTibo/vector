"""§6 Step 6.5 — deterministic execution situation detection (no LLM, not persisted).

Rules: situations may be anchored by ≥2 gaps **or** by 1 gap plus a **strong signal** (see
``_strong_signal_tags``). Output is merged for overlap, then padded to ``MIN_SITUATIONS`` using the
strongest unused signal drivers (target ``MIN_SITUATIONS``–``MAX_SITUATIONS_RETURNED`` distinct situations).
"""

from __future__ import annotations

import uuid
from collections import Counter, defaultdict

from vector.contracts.manager_insights_activity import (
    CoordinationDecisionType,
    CoordinationLinkInputBundle,
    EvidenceBundle,
    ExecutionSituation,
    ExecutionSituationType,
    GapBundle,
    GapItem,
    LinkBundle,
    PerceptionRow,
    SignalsV0Debug,
    WorkItem,
    WorkItemBundle,
)
from vector.domains.manager_insights.compute_signals import (
    _identity_keys_for_item,
    _open_exec_owner_bucket,
)
from vector.domains.manager_insights.hold_start_evaluation import (
    SCOPE_ELIGIBLE_GAP_TYPES,
    evaluate_hold_start_emission,
)

_EXEC_TYPES = frozenset({"issue", "pull_request"})
_DONE = frozenset(
    {
        "closed",
        "done",
        "completed",
        "complete",
        "merged",
        "cancelled",
        "canceled",
    }
)
_ACTIVE_PROJECT_THRESHOLD = 6
_MAX_GAP_IDS_PER_SITUATION = 16
_MAX_SITUATION_TYPES = 8
MIN_SITUATIONS = 2
MAX_SITUATIONS_RETURNED = 5

_ACTOR_FRAGMENTATION_THRESHOLD = 4
_DISCUSSION_TYPES_F = frozenset({"call", "message_thread"})
ACTOR_COORDINATION_SITUATION_TYPES: frozenset[str] = frozenset(
    {
        "OWNERSHIP_FRAGMENTED",
        "KEY_PERSON_BOTTLENECK",
        "DECISION_NOT_CONNECTED_TO_OWNER",
        "UNKNOWN_OWNERSHIP",
    }
)


def _is_execution_wi(w: WorkItem | None) -> bool:
    return bool(w and w.type in _EXEC_TYPES)


def _is_done_wi(w: WorkItem | None) -> bool:
    if w is None:
        return False
    if w.closed_at is not None:
        return True
    st = (w.status or "").strip().lower()
    return st in _DONE


def _gap_seeds(gap: GapItem, by_id: dict[str, WorkItem]) -> set[str]:
    seeds: set[str] = set()
    for vals in gap.evidence_pointers.values():
        for ref in vals:
            if ref in by_id:
                seeds.add(ref)
    return seeds


def _discussed_slack_only(gap: GapItem, by_id: dict[str, WorkItem]) -> bool:
    seeds = _gap_seeds(gap, by_id)
    if not seeds:
        return False
    return all(
        by_id.get(s) and by_id[s].type == "message_thread" and str(s).startswith("slack:") for s in seeds
    )


def _discussed_has_no_decision_evidence(
    gap: GapItem,
    by_id: dict[str, WorkItem],
    evidence: EvidenceBundle | None,
) -> bool:
    seeds = _gap_seeds(gap, by_id)
    if not seeds or evidence is None:
        return True
    return not any(d.source_work_item_id in seeds for d in evidence.decisions)


def _unique(ids: list[str]) -> list[str]:
    return list(dict.fromkeys(ids))


def _serial_identity_key(key: tuple[object, ...]) -> str:
    parts: list[str] = []
    for p in key:
        parts.append(str(p))
    return "|".join(parts)


def _uuid_actor_ids_from_items(items: list[WorkItem]) -> list[str]:
    found: set[uuid.UUID] = set()
    for w in items:
        if w.owner_actor_id is not None:
            found.add(w.owner_actor_id)
        for aid in w.participant_actor_ids or []:
            if isinstance(aid, uuid.UUID):
                found.add(aid)
    return sorted(str(x) for x in found)


def _open_execution_items(by_id: dict[str, WorkItem]) -> list[WorkItem]:
    return [w for w in by_id.values() if _is_execution_wi(w) and not _is_done_wi(w)]


def _discussion_work_items(by_id: dict[str, WorkItem]) -> list[WorkItem]:
    return [w for w in by_id.values() if w.type in _DISCUSSION_TYPES_F]


def _discussion_identity_keys(items: list[WorkItem]) -> set[tuple[object, ...]]:
    bag: set[tuple[object, ...]] = set()
    for w in items:
        bag.update(_identity_keys_for_item(w))
    return bag


def _exec_owner_identity_keys(open_exec: list[WorkItem]) -> set[tuple[object, ...]]:
    bag: set[tuple[object, ...]] = set()
    for w in open_exec:
        b = _open_exec_owner_bucket(w)
        if b is not None:
            bag.add(b)
    return bag


def _bottleneck_open_execution_ratio(open_exec: list[WorkItem]) -> tuple[int, int, float, tuple[object, ...] | None]:
    """Return (open_exec_total, max_owner_count, max_count/total, top_bucket)."""
    n = len(open_exec)
    if n < 2:
        return n, 0, 0.0, None
    counts: Counter[tuple[object, ...]] = Counter()
    for w in open_exec:
        b = _open_exec_owner_bucket(w)
        if b is not None:
            counts[b] += 1
    if not counts:
        return n, 0, 0.0, None
    top_bucket, top_n = max(counts.items(), key=lambda kv: kv[1])
    return n, top_n, top_n / n, top_bucket


def _participant_slots_missing_actor_ratio(items: list[WorkItem]) -> tuple[int, int, float]:
    slots = 0
    missing = 0
    for w in items:
        parts = list(w.participants or [])
        aids = list(w.participant_actor_ids or [])
        for i, p in enumerate(parts):
            if not str(p).strip():
                continue
            slots += 1
            aid = aids[i] if i < len(aids) else None
            if not isinstance(aid, uuid.UUID):
                missing += 1
    if slots == 0:
        return 0, 0, 0.0
    return slots, missing, missing / slots


def _append_actor_coordination_situations(
    out: list[ExecutionSituation],
    *,
    by_id: dict[str, WorkItem],
    sig: SignalsV0Debug,
    pool_for_pad: list[str],
) -> None:
    """Actor-signal-driven situations (thresholds on ``SignalsV0Debug`` + deterministic work-item math)."""
    gids = _supporting_ids(pool_for_pad[:8] if pool_for_pad else [], pool_for_pad, sig)

    if sig.actor_fragmentation > _ACTOR_FRAGMENTATION_THRESHOLD:
        out.append(
            ExecutionSituation(
                type="OWNERSHIP_FRAGMENTED",
                severity=0.93,
                supporting_gap_ids=gids,
                supporting_signals=[
                    f"actor_fragmentation:{sig.actor_fragmentation}",
                    f"threshold_gt:{_ACTOR_FRAGMENTATION_THRESHOLD}",
                ],
                rationale=(
                    "Many distinct coordination identities are active at once — ownership and sequencing get "
                    "expensive because the same human work is represented as different people across tools. "
                    "Next: consolidate accountability onto canonical actors in tracking and reduce parallel owners per thread."
                ),
                actor_situation_metrics={
                    "rule": "OWNERSHIP_FRAGMENTED",
                    "actor_fragmentation_observed": sig.actor_fragmentation,
                    "actor_fragmentation_threshold_gt": _ACTOR_FRAGMENTATION_THRESHOLD,
                    "actor_ids_uuid": _uuid_actor_ids_from_items(list(by_id.values())) if by_id else [],
                    "open_execution_item_count": len(_open_execution_items(by_id)) if by_id else 0,
                },
            )
        )

    if not by_id:
        return

    all_items = list(by_id.values())
    open_exec = _open_execution_items(by_id)
    disc_items = _discussion_work_items(by_id)
    disc_keys = _discussion_identity_keys(disc_items)
    exec_owner_keys = _exec_owner_identity_keys(open_exec)
    oe_total, oe_max, oe_ratio, top_bucket = _bottleneck_open_execution_ratio(open_exec)
    part_slots, part_missing, part_ratio = _participant_slots_missing_actor_ratio(all_items)
    actor_uuids = _uuid_actor_ids_from_items(all_items)

    if oe_total >= 2 and oe_ratio > 0.5 and top_bucket is not None:
        out.append(
            ExecutionSituation(
                type="KEY_PERSON_BOTTLENECK",
                severity=0.92,
                supporting_gap_ids=gids,
                supporting_signals=[
                    f"open_execution_owner_concentration:{oe_ratio:.2f}",
                    f"actor_load:{sig.actor_load}",
                ],
                rationale=(
                    "Open execution is concentrated on one coordination identity — delivery risk and review latency "
                    "collapse onto a single bottleneck. "
                    "Next: split ownership, add explicit delegates, and cap WIP for that actor until the queue drains."
                ),
                actor_situation_metrics={
                    "rule": "KEY_PERSON_BOTTLENECK",
                    "open_execution_total": oe_total,
                    "max_items_same_owner_bucket": oe_max,
                    "max_owner_share_of_open_execution": round(oe_ratio, 4),
                    "dominant_owner_bucket": _serial_identity_key(top_bucket),
                    "actor_load_signal": sig.actor_load,
                    "actor_ids_uuid": actor_uuids,
                },
            )
        )

    if disc_keys and exec_owner_keys and not (disc_keys & exec_owner_keys):
        out.append(
            ExecutionSituation(
                type="DECISION_NOT_CONNECTED_TO_OWNER",
                severity=0.91,
                supporting_gap_ids=gids,
                supporting_signals=[
                    "discussion_vs_execution_owner_disjoint",
                    f"actor_consistency:{sig.actor_consistency:.3f}",
                ],
                rationale=(
                    "Discussion participants do not match execution owners — commitments in conversation are not "
                    "anchored to the people shipping tracked work. "
                    "Next: link each discussion thread to an owning issue or PR and name the DRI in tracking."
                ),
                actor_situation_metrics={
                    "rule": "DECISION_NOT_CONNECTED_TO_OWNER",
                    "discussion_identity_count": len(disc_keys),
                    "execution_owner_identity_count": len(exec_owner_keys),
                    "discussion_identity_keys": sorted(_serial_identity_key(k) for k in disc_keys),
                    "execution_owner_identity_keys": sorted(_serial_identity_key(k) for k in exec_owner_keys),
                    "actor_consistency_signal": round(sig.actor_consistency, 4),
                    "actor_ids_uuid": actor_uuids,
                },
            )
        )

    if part_slots > 0 and part_ratio > 0.5:
        out.append(
            ExecutionSituation(
                type="UNKNOWN_OWNERSHIP",
                severity=0.90,
                supporting_gap_ids=gids,
                supporting_signals=[
                    f"participant_slots_missing_actor_ratio:{part_ratio:.2f}",
                ],
                rationale=(
                    "Most participant slots are not resolved to canonical actors — coordination metrics and routing "
                    "will keep mis-attributing work. "
                    "Next: backfill connector identities for the noisy tools and require actor mapping before scaling automation."
                ),
                actor_situation_metrics={
                    "rule": "UNKNOWN_OWNERSHIP",
                    "participant_slots_total": part_slots,
                    "participant_slots_missing_actor": part_missing,
                    "participant_slots_missing_actor_ratio": round(part_ratio, 4),
                    "actor_ids_uuid": actor_uuids,
                },
            )
        )


def _strong_signal_tags(sig: SignalsV0Debug) -> frozenset[str]:
    tags: list[str] = []
    if sig.discussion_churn == "high":
        tags.append("churn_high")
    if sig.discussion_churn == "moderate":
        tags.append("churn_moderate")
    if sig.contradiction_density == "high":
        tags.append("contradiction_high")
    if sig.contradiction_density == "moderate":
        tags.append("contradiction_moderate")
    if sig.execution_momentum == "slowing":
        tags.append("momentum_slowing")
    if sig.blocker_visibility == "not_visible":
        tags.append("blocker_hidden")
    if sig.blocker_visibility == "partial":
        tags.append("blocker_partial")
    # review / handoff latency proxy (no dedicated signal in v0)
    if sig.follow_through in ("weak", "partial") and (
        sig.expectation_coverage == "low"
        or sig.documentation_linkage in ("not_linked", "partially_linked")
        or sig.discussion_churn in ("moderate", "high")
    ):
        tags.append("review_latency")
    if sig.urgent_pressure == "high":
        tags.append("urgent_high")
    if sig.focus == "fragmented":
        tags.append("focus_fragmented")
    return frozenset(tags)


def has_strong_signal(sig: SignalsV0Debug) -> bool:
    return len(_strong_signal_tags(sig)) > 0


def _supporting_ids(
    primary: list[str],
    pool: list[str],
    sig: SignalsV0Debug,
) -> list[str]:
    """≥2 gaps **or** 1 gap + strong signal → keep a single gap; else pad from pool."""
    out = _unique(primary)[:_MAX_GAP_IDS_PER_SITUATION]
    if len(out) >= 2:
        return out
    if len(out) == 1 and has_strong_signal(sig):
        return out
    for pid in pool:
        if pid not in out:
            out.append(pid)
        if len(out) >= 2:
            break
    return out[:_MAX_GAP_IDS_PER_SITUATION]


def _active_open_projects(by_id: dict[str, WorkItem]) -> int:
    pjes: set[str] = set()
    for w in by_id.values():
        if _is_execution_wi(w) and not _is_done_wi(w):
            pjes.add((w.project or "").strip() or w.id)
    return len(pjes)


def _review_latency_high(sig: SignalsV0Debug) -> bool:
    return "review_latency" in _strong_signal_tags(sig)


SITUATION_TO_DECISION: dict[ExecutionSituationType, CoordinationDecisionType] = {
    "INVISIBLE_BLOCKERS": "MAKE_BLOCKERS_EXPLICIT",
    "DECISION_LOOP": "FORCE_DECISION",
    "FRAGMENTED_EXECUTION": "REDUCE_WIP",
    "OWNERSHIP_CONFUSION": "ASSIGN_OWNER",
    "SHADOW_WORK": "CAPTURE_WORK",
    "MISALIGNED_REALITY": "RESOLVE_STATE_MISMATCH",
    "SCOPE_DRIFT": "SPLIT_SCOPE",
    "REVIEW_BOTTLENECK": "UNBLOCK_REVIEW",
    "PRIORITY_CONFLICT": "REALIGN_PRIORITY",
    "UNCONTROLLED_INCIDENT": "STRUCTURE_INCIDENT",
    "RISKY_SHIPPING": "BLOCK_RELEASE",
    "OWNERSHIP_FRAGMENTED": "REDUCE_WIP",
    "KEY_PERSON_BOTTLENECK": "REALIGN_PRIORITY",
    "DECISION_NOT_CONNECTED_TO_OWNER": "FORCE_DECISION",
    "UNKNOWN_OWNERSHIP": "RESOLVE_OWNERSHIP",
}


def _axis_key(s: ExecutionSituation) -> tuple[str, str, str]:
    """(cause_family, driver_family, surface) for overlap merge."""
    cause_map: dict[ExecutionSituationType, str] = {
        "INVISIBLE_BLOCKERS": "blocker",
        "RISKY_SHIPPING": "shipping_risk",
        "REVIEW_BOTTLENECK": "delivery",
        "DECISION_LOOP": "decision",
        "UNCONTROLLED_INCIDENT": "incident",
        "PRIORITY_CONFLICT": "priority",
        "SCOPE_DRIFT": "scope",
        "OWNERSHIP_CONFUSION": "ownership",
        "SHADOW_WORK": "shadow",
        "MISALIGNED_REALITY": "state",
        "FRAGMENTED_EXECUTION": "wip",
        "OWNERSHIP_FRAGMENTED": "actor_fragmentation",
        "KEY_PERSON_BOTTLENECK": "actor_bottleneck",
        "DECISION_NOT_CONNECTED_TO_OWNER": "actor_discussion_exec_disjoint",
        "UNKNOWN_OWNERSHIP": "actor_unknown_participants",
    }
    cause = cause_map.get(s.type, "other")
    sigs = " ".join(s.supporting_signals).lower()
    driver = (
        "churn"
        if "churn" in sigs
        else "contradiction"
        if "contradiction" in sigs
        else "momentum"
        if "momentum" in sigs
        else "visibility"
        if "blocker" in sigs or "visibility" in sigs
        else "review"
        if "review" in sigs or "follow" in sigs
        else "focus"
        if "focus" in sigs or "wip" in sigs
        else "urgent"
        if "urgent" in sigs
        else "mixed"
    )
    surface = "incident" if s.type == "UNCONTROLLED_INCIDENT" else "cross_team" if len(s.supporting_gap_ids) > 2 else "team"
    return (cause, driver, surface)


def _jaccard(a: list[str], b: list[str]) -> float:
    sa, sb = set(a), set(b)
    if not sa and not sb:
        return 1.0
    u = sa | sb
    if not u:
        return 0.0
    return len(sa & sb) / len(u)


def _merge_key(s: ExecutionSituation) -> str:
    """Do not merge HOLD_START cluster with CLARIFY_SPEC fallback on the same enum type."""
    if s.decision_override:
        return f"{s.type}:{s.decision_override}"
    return s.type


def merge_cap_situations(candidates: list[ExecutionSituation]) -> list[ExecutionSituation]:
    """Merge duplicate types; cap to ``_MAX_SITUATION_TYPES`` by severity."""
    by_t: dict[str, ExecutionSituation] = {}
    for s in candidates:
        key = _merge_key(s)
        if key not in by_t:
            by_t[key] = s
            continue
        prev = by_t[key]
        merged_ids = _unique(prev.supporting_gap_ids + s.supporting_gap_ids)[:_MAX_GAP_IDS_PER_SITUATION]
        merged_sig = _unique(prev.supporting_signals + s.supporting_signals)
        sev = max(prev.severity, s.severity)
        rationale = prev.rationale if prev.severity >= s.severity else s.rationale
        hold_em = s.hold_start_emission_trace or prev.hold_start_emission_trace
        ov = s.decision_override or prev.decision_override
        if s.decision_override == "HOLD_START" or prev.decision_override == "HOLD_START":
            ov = "HOLD_START"
            hold_em = s.hold_start_emission_trace or prev.hold_start_emission_trace
        act_m = s.actor_situation_metrics if s.severity >= prev.severity else prev.actor_situation_metrics
        by_t[key] = ExecutionSituation(
            type=s.type,  # type: ignore[arg-type]
            severity=sev,
            supporting_gap_ids=merged_ids,
            supporting_signals=merged_sig,
            rationale=rationale,
            decision_override=ov,
            hold_start_emission_trace=hold_em,
            actor_situation_metrics=act_m,
            aggregated_failure_mode=None,
            aggregated_supporting_situation_types=[],
        )
    merged = sorted(by_t.values(), key=lambda x: (-x.severity, x.type))
    return merged[:_MAX_SITUATION_TYPES]


def dedupe_overlapping_axis(sits: list[ExecutionSituation]) -> list[ExecutionSituation]:
    """Drop lower-severity row when another situation shares axis + heavy gap overlap."""
    ordered = sorted(sits, key=lambda x: (-x.severity, x.type))
    kept: list[ExecutionSituation] = []
    for s in ordered:
        drop = False
        for k in kept:
            if _axis_key(s) == _axis_key(k) and _jaccard(s.supporting_gap_ids, k.supporting_gap_ids) >= 0.65:
                drop = True
                break
        if not drop:
            kept.append(s)
    return sorted(kept, key=lambda x: (-x.severity, x.type))


def _inject_from_signal_driver(
    existing: list[ExecutionSituation],
    gaps: list[GapItem],
    sig: SignalsV0Debug,
    *,
    used_tags: set[str],
) -> ExecutionSituation | None:
    """Create one extra situation from the strongest signal driver not yet reflected."""
    all_ids = [g.id for g in gaps]
    if not all_ids:
        return None
    # priority order for injection
    priority = [
        "churn_high",
        "contradiction_high",
        "urgent_high",
        "momentum_slowing",
        "focus_fragmented",
        "blocker_hidden",
        "review_latency",
        "churn_moderate",
        "contradiction_moderate",
    ]
    active = set(_strong_signal_tags(sig))
    for tag in priority:
        if tag not in active or tag in used_tags:
            continue
        gids = _supporting_ids([all_ids[0]], all_ids, sig)
        if tag.startswith("churn"):
            return ExecutionSituation(
                type="DECISION_LOOP",
                severity=0.48,
                supporting_gap_ids=gids,
                supporting_signals=[f"injected:{tag}"],
                rationale=(
                    "Discussion volume is elevated relative to durable decisions in tracking — "
                    "the team is spending coordination time without closing loops. "
                    "Next: end the next working session with one written decision and an owner on the issue or PR."
                ),
            )
        if tag.startswith("contradiction"):
            return ExecutionSituation(
                type="MISALIGNED_REALITY",
                severity=0.52,
                supporting_gap_ids=gids,
                supporting_signals=[f"injected:{tag}"],
                rationale=(
                    "Contradictory narratives are showing up across channels and tools — people are planning against different facts. "
                    "Next: reconcile status on one canonical issue or PR and broadcast the agreed truth."
                ),
            )
        if tag == "urgent_high":
            return ExecutionSituation(
                type="PRIORITY_CONFLICT",
                severity=0.5,
                supporting_gap_ids=gids,
                supporting_signals=[f"injected:{tag}"],
                rationale=(
                    "Urgency is spiking while execution signals do not show a matching narrowing of focus — "
                    "the team is being pulled without a sequencing contract. "
                    "Next: name what ships first, what waits, and who owns the tradeoff call."
                ),
            )
        if tag == "momentum_slowing":
            return ExecutionSituation(
                type="FRAGMENTED_EXECUTION",
                severity=0.46,
                supporting_gap_ids=gids,
                supporting_signals=[f"injected:{tag}"],
                rationale=(
                    "Momentum is slowing while coordination debt is visible — work is likely spread across too many threads. "
                    "Next: cut active commitments until two items can reach done this week."
                ),
            )
        if tag == "focus_fragmented":
            return ExecutionSituation(
                type="FRAGMENTED_EXECUTION",
                severity=0.44,
                supporting_gap_ids=gids,
                supporting_signals=[f"injected:{tag}"],
                rationale=(
                    "Focus is fragmented across parallel threads — reviews and sequencing will keep missing each other. "
                    "Next: consolidate to a single execution lane per team for the current milestone."
                ),
            )
        if tag == "blocker_hidden":
            return ExecutionSituation(
                type="INVISIBLE_BLOCKERS",
                severity=0.45,
                supporting_gap_ids=gids,
                supporting_signals=[f"injected:{tag}"],
                rationale=(
                    "Blocker visibility in tracking is weak even where risk is being discussed — "
                    "execution cannot depend on memory and DMs. "
                    "Next: promote each blocker to an owned issue or PR with a clear unblock path."
                ),
            )
        if tag == "review_latency":
            return ExecutionSituation(
                type="REVIEW_BOTTLENECK",
                severity=0.43,
                supporting_gap_ids=gids,
                supporting_signals=[f"injected:{tag}"],
                rationale=(
                    "Handoffs and reviews are lagging commitments — work is waiting in invisible queues. "
                    "Next: put SLAs on review and assign a named reviewer for each open commitment."
                ),
            )
    return None


def _refine_used_tags(sits: list[ExecutionSituation], sig: SignalsV0Debug) -> set[str]:
    """Heuristic: mark strong tags as used when a situation plausibly explains them."""
    tags = set(_strong_signal_tags(sig))
    used: set[str] = set()
    for s in sits:
        if s.type == "DECISION_LOOP" and sig.discussion_churn in ("high", "moderate"):
            used.update({"churn_high", "churn_moderate"})
        if s.type == "MISALIGNED_REALITY" and sig.contradiction_density in ("high", "moderate"):
            used.update({"contradiction_high", "contradiction_moderate"})
        if s.type == "PRIORITY_CONFLICT" and sig.urgent_pressure == "high":
            used.add("urgent_high")
        if s.type == "FRAGMENTED_EXECUTION" and (
            sig.focus == "fragmented" or sig.execution_momentum == "slowing"
        ):
            used.update({"focus_fragmented", "momentum_slowing"})
        if s.type == "INVISIBLE_BLOCKERS" and sig.blocker_visibility in ("not_visible", "partial"):
            used.update({"blocker_hidden", "blocker_partial"})
        if s.type == "REVIEW_BOTTLENECK":
            used.add("review_latency")
    return used & tags if used else set()


def ensure_situation_floor(
    sits: list[ExecutionSituation],
    all_g: list[GapItem],
    sig: SignalsV0Debug,
) -> list[ExecutionSituation]:
    """Guarantee at least ``MIN_SITUATIONS`` rows, at most ``MAX_SITUATIONS_RETURNED``, using signal injection."""
    out = list(sits)
    for _ in range(8):
        if len(out) >= MIN_SITUATIONS:
            break
        used = _refine_used_tags(out, sig)
        inj = _inject_from_signal_driver(out, all_g, sig, used_tags=used)
        if inj is None:
            gids = _supporting_ids([all_g[0].id], [g.id for g in all_g], sig)
            inj = ExecutionSituation(
                type="FRAGMENTED_EXECUTION",
                severity=0.35,
                supporting_gap_ids=gids,
                supporting_signals=["injected:coordination_spread"],
                rationale=(
                    "Several coordination gaps are open at once — even without a single loud signal, execution is spread thin. "
                    "Next: pick two outcomes to finish, park the rest explicitly, and reset weekly planning."
                ),
            )
        out.append(inj)
    out = dedupe_overlapping_axis(merge_cap_situations(out))
    if len(out) < MIN_SITUATIONS:
        gids = _supporting_ids([all_g[0].id], [g.id for g in all_g], sig)
        out.append(
            ExecutionSituation(
                type="DECISION_LOOP",
                severity=0.33,
                supporting_gap_ids=gids,
                supporting_signals=["injected:second_axis_coordination"],
                rationale=(
                    "Coordination is still under-specified for how decisions move to tracked work — "
                    "the team needs explicit closure mechanics, not more discussion. "
                    "Next: adopt a single written decision template and require it before closing the meeting."
                ),
            )
        )
        out = dedupe_overlapping_axis(merge_cap_situations(out))
    return sorted(out, key=lambda x: (-x.severity, x.type))[:MAX_SITUATIONS_RETURNED]


def detect_execution_situations(
    gaps: GapBundle,
    signals: SignalsV0Debug,
    *,
    perception_rows: list[PerceptionRow],
    work_items: WorkItemBundle | None,
    links: LinkBundle | None,
    evidence: EvidenceBundle | None,
    coordination_input: CoordinationLinkInputBundle | None,
    hold_start_affected_wi_threshold: int,
    gaps_use_graph: bool,
) -> list[ExecutionSituation]:
    """Aggregate gaps + signals + perception into execution situations (single pipeline for any gap count)."""
    all_g = list(gaps.gaps)
    if not all_g:
        return []

    by_id: dict[str, WorkItem] = {w.id: w for w in (work_items.items if work_items else [])}
    by_type: dict[str, list[GapItem]] = defaultdict(list)
    for g in all_g:
        by_type[g.type].append(g)

    all_gap_ids = [g.id for g in all_g]
    pool_for_pad = all_gap_ids

    discussed = by_type["discussed_not_linked_to_work"]
    blockers = by_type["blocker_not_tracked"]
    expected = by_type["expected_not_executed"]
    docs = by_type["doc_not_connected_to_execution"]

    sig = signals
    churn_h = sig.discussion_churn == "high"
    churn_mh = sig.discussion_churn in ("high", "moderate")
    contra_h = sig.contradiction_density == "high"
    contra_m_plus = sig.contradiction_density in ("high", "moderate")
    slowing = sig.execution_momentum == "slowing"
    not_accel = sig.execution_momentum != "accelerating"
    partial_block_vis = sig.blocker_visibility == "partial"
    not_visible = sig.blocker_visibility == "not_visible"
    follow_weak = sig.follow_through == "weak"
    follow_partial = sig.follow_through in ("weak", "partial")
    urgent_h = sig.urgent_pressure == "high"
    delivery_low = sig.delivery_strength == "low"
    collab_h = sig.collaboration_intensity == "high"
    scope_elevated = sig.scope_ambiguity in ("high", "moderate")

    out: list[ExecutionSituation] = []

    # 0 — Actor coordination (signals + deterministic work-item checks; no LLM)
    _append_actor_coordination_situations(out, by_id=by_id, sig=sig, pool_for_pad=pool_for_pad)

    # 1 — HOLD_START
    if coordination_input is not None and sig.scope_ambiguity == "high":
        for gap in all_g:
            if gap.type not in SCOPE_ELIGIBLE_GAP_TYPES:
                continue
            em = evaluate_hold_start_emission(
                gap,
                sig,
                work_items=work_items,
                links=links,
                evidence=evidence,
                coordination_input=coordination_input,
                hold_start_affected_wi_threshold=hold_start_affected_wi_threshold,
                gaps_use_graph=gaps_use_graph,
            )
            if em.hold_start_emitted:
                out.append(
                    ExecutionSituation(
                        type="SCOPE_DRIFT",
                        severity=0.98,
                        supporting_gap_ids=[gap.id],
                        supporting_signals=["scope_ambiguity:high", "hold_start_cluster"],
                        rationale=(
                            "Scope is ambiguous while a large neighborhood of open execution work has **no** recorded "
                            "decision evidence in-cluster — starting more tracked work will compound rework. "
                            "Next: hold new starts, write a one-page scope decision, and only then reopen execution."
                        ),
                        decision_override="HOLD_START",
                        hold_start_emission_trace=em,
                    )
                )
                break

    has_clarify_situation_early = any(s.decision_override == "CLARIFY_SPEC" for s in out)
    cluster_inputs_ok = (
        work_items is not None
        and links is not None
        and evidence is not None
        and coordination_input is not None
    )
    # 1c — CLARIFY when scope is high but HOLD did not fire and cluster math cannot run (partial runs).
    if (
        sig.scope_ambiguity == "high"
        and not any(s.decision_override == "HOLD_START" for s in out)
        and not has_clarify_situation_early
        and not cluster_inputs_ok
    ):
        for gap in all_g:
            if gap.type in SCOPE_ELIGIBLE_GAP_TYPES:
                out.append(
                    ExecutionSituation(
                        type="SCOPE_DRIFT",
                        severity=0.62,
                        supporting_gap_ids=_supporting_ids([gap.id], pool_for_pad, sig),
                        supporting_signals=["scope_ambiguity:high", "clarify:inputs_incomplete"],
                        rationale=(
                            "Scope reads ambiguous in signals while full cluster inputs were not available — "
                            "the team should still pin intent before more execution spreads. "
                            "Next: clarify success criteria, non-goals, and a single accountable owner in tracking."
                        ),
                        decision_override="CLARIFY_SPEC",
                    )
                )
                break

    hold_emitted = any(s.decision_override == "HOLD_START" for s in out)

    # 1b — CLARIFY_SPEC path when HOLD not emitted but scope high (full cluster inputs).
    if (
        coordination_input is not None
        and sig.scope_ambiguity == "high"
        and not hold_emitted
        and not any(s.decision_override == "CLARIFY_SPEC" for s in out)
    ):
        for gap in all_g:
            if gap.type not in SCOPE_ELIGIBLE_GAP_TYPES:
                continue
            em = evaluate_hold_start_emission(
                gap,
                sig,
                work_items=work_items,
                links=links,
                evidence=evidence,
                coordination_input=coordination_input,
                hold_start_affected_wi_threshold=hold_start_affected_wi_threshold,
                gaps_use_graph=gaps_use_graph,
            )
            if em.evaluated and not em.hold_start_emitted:
                out.append(
                    ExecutionSituation(
                        type="SCOPE_DRIFT",
                        severity=0.72,
                        supporting_gap_ids=_supporting_ids([gap.id], pool_for_pad, sig),
                        supporting_signals=["scope_ambiguity:high", "hold_start_not_emitted"],
                        rationale=(
                            "Scope ambiguity is high but the team still has partial guardrails — "
                            "you should clarify scope and owners before more build lands, without a full hold. "
                            "Next: run a 30-minute scope pin-down and capture constraints in the canonical issue."
                        ),
                        decision_override="CLARIFY_SPEC",
                        hold_start_emission_trace=em,
                    )
                )
                break

    # 2 — UNCONTROLLED_INCIDENT
    if churn_h and collab_h and (len(discussed) >= 3 or (len(discussed) >= 1 and has_strong_signal(sig))):
        base_ids = [d.id for d in discussed][:8] or all_gap_ids[:2]
        gids = _supporting_ids(base_ids, pool_for_pad, sig)
        out.append(
            ExecutionSituation(
                type="UNCONTROLLED_INCIDENT",
                severity=0.92,
                supporting_gap_ids=gids,
                supporting_signals=["discussion_churn:high", "collaboration_intensity:high"],
                rationale=(
                    "Discussion churn is high while collaboration intensity is high — coordination is reactive and noisy. "
                    "Next: move to an incident-style rhythm: single comms channel, explicit roles, and timeboxed decisions."
                ),
            )
        )

    # 3 — INVISIBLE_BLOCKERS (any blocker gap row — single gap is valid with scaled severity)
    b_ids = [b.id for b in blockers]
    if b_ids:
        gids = _supporting_ids(b_ids, pool_for_pad, sig)
        if len(b_ids) >= 3:
            sev = 0.95
        elif slowing or not_visible or partial_block_vis:
            sev = 0.72
        elif has_strong_signal(sig):
            sev = 0.52
        else:
            sev = 0.38
        sigs = ["blocker_not_tracked:multiple" if len(b_ids) >= 3 else "blocker_visibility:weak"]
        if slowing:
            sigs.append("execution_momentum:slowing")
        out.append(
            ExecutionSituation(
                type="INVISIBLE_BLOCKERS",
                severity=sev,
                supporting_gap_ids=gids,
                supporting_signals=_unique(sigs),
                rationale=(
                    "Execution is slowing because blockers are being discussed but **not** reliably carried in tracking — "
                    "the team cannot sequence or escalate what it cannot see. "
                    "Next: promote each blocker to an owned issue or PR with a named resolver and a dated unblock plan."
                ),
            )
        )

    # 4 — MISALIGNED_REALITY
    misaligned = contra_h or (contra_m_plus and churn_mh) or (contra_m_plus and len(all_g) >= 2)
    if misaligned:
        sev = 0.9 if contra_h else 0.58
        gids = _supporting_ids(all_gap_ids[:8], pool_for_pad, sig)
        override: CoordinationDecisionType | None = None
        if len(all_g) == 1 and all_g[0].type == "expected_not_executed" and contra_h and churn_h:
            override = "RECENTER_WORK"
        out.append(
            ExecutionSituation(
                type="MISALIGNED_REALITY",
                severity=sev,
                supporting_gap_ids=gids,
                supporting_signals=[f"contradiction_density:{sig.contradiction_density}", f"discussion_churn:{sig.discussion_churn}"],
                rationale=(
                    "Slack, issues, and PRs are telling different stories about what is done and what is blocked — "
                    "planning against misaligned reality burns calendar and trust. "
                    "Next: pick one source of truth for state, reconcile it live in a working session, and broadcast the outcome."
                ),
                decision_override=override,
            )
        )

    # 5 — DECISION_LOOP
    if (churn_h or sig.repeated_discussion_present) and (len(discussed) >= 2 or (len(discussed) >= 1 and has_strong_signal(sig))):
        loop_gaps = [d for d in discussed if _discussed_has_no_decision_evidence(d, by_id, evidence)]
        base_disc = loop_gaps if len(loop_gaps) >= 2 else (loop_gaps if loop_gaps else discussed)
        if base_disc or discussed:
            gids = _supporting_ids([d.id for d in (base_disc or discussed)], pool_for_pad, sig)
            loop_sig: list[str] = []
            if churn_h:
                loop_sig.append("discussion_churn:high")
            if sig.repeated_discussion_present:
                loop_sig.append("repeated_discussion_present")
            if not loop_sig:
                loop_sig = ["discussion_pattern"]
            out.append(
                ExecutionSituation(
                    type="DECISION_LOOP",
                    severity=0.88 if churn_h else 0.62,
                    supporting_gap_ids=gids,
                    supporting_signals=_unique(loop_sig),
                    rationale=(
                        "Threads are churning without durable decisions tied to execution — people re-argue because nothing was captured where work ships. "
                        "Next: end the next discussion with a written decision, link it to the issue or PR, and assign the owner who executes it."
                    ),
                )
            )

    # 6 — PRIORITY_CONFLICT
    if urgent_h and follow_weak:
        seed = [g.id for g in expected[:4]] + [g.id for g in blockers[:2]] or all_gap_ids
        gids = _supporting_ids(seed, pool_for_pad, sig)
        out.append(
            ExecutionSituation(
                type="PRIORITY_CONFLICT",
                severity=0.85,
                supporting_gap_ids=gids,
                supporting_signals=["urgent_pressure:high", "follow_through:weak"],
                rationale=(
                    "Urgent pressure is high while follow-through is weak — the system is signaling **more** work than it can land. "
                    "Next: realign priorities in writing: what ships this week, what waits, and who owns the tradeoff."
                ),
            )
        )

    # 7 — RISKY_SHIPPING
    if delivery_low and len(b_ids) >= 1 and (len(expected) >= 1 or has_strong_signal(sig)):
        gids = _supporting_ids(b_ids + [e.id for e in expected[:3]] or b_ids, pool_for_pad, sig)
        out.append(
            ExecutionSituation(
                type="RISKY_SHIPPING",
                severity=0.84,
                supporting_gap_ids=gids,
                supporting_signals=["delivery_strength:low"],
                rationale=(
                    "Delivery strength is low while risk items are still open — shipping would compound coordination debt. "
                    "Next: block release until blockers and contradictory state are reconciled with named owners."
                ),
            )
        )

    # 8 — REVIEW_BOTTLENECK (review-latency proxy + commitment gap)
    if len(expected) >= 1 and _review_latency_high(sig) and (len(expected) >= 2 or has_strong_signal(sig) or follow_partial):
        gids = _supporting_ids([e.id for e in expected], pool_for_pad, sig)
        out.append(
            ExecutionSituation(
                type="REVIEW_BOTTLENECK",
                severity=0.7,
                supporting_gap_ids=gids,
                supporting_signals=["review_latency:proxy", f"follow_through:{sig.follow_through}"],
                rationale=(
                    "Commitments are stalling where reviews and handoffs should be tightening — latency is hiding in calendars, not in tracking. "
                    "Next: assign explicit reviewers, shorten review batches, and track time-to-first-review on each commitment."
                ),
            )
        )

    # 9 — OWNERSHIP_CONFUSION
    own_hints = [r for r in perception_rows if r.kind == "ownership_hint" or "who owns" in r.statement.lower()]
    discussed_no_owner = [
        d
        for d in discussed
        if any(
            (w := by_id.get(s)) and w.type == "issue" and not (w.owner and str(w.owner).strip())
            for s in _gap_seeds(d, by_id)
        )
    ]
    if len(own_hints) >= 2 or len(discussed_no_owner) >= 2 or (len(discussed_no_owner) == 1 and has_strong_signal(sig)):
        seed: list[str] = [d.id for d in discussed_no_owner[:6]]
        if not seed and len(own_hints) >= 1 and (len(own_hints) >= 2 or has_strong_signal(sig)):
            seed = [g.id for g in discussed[:4]] or all_gap_ids[:1]
        if not seed:
            seed = [g.id for g in discussed[:2]] + [g.id for g in expected[:2]] or all_gap_ids[:1]
        gids = _supporting_ids(seed, pool_for_pad, sig)
        out.append(
            ExecutionSituation(
                type="OWNERSHIP_CONFUSION",
                severity=0.7,
                supporting_gap_ids=gids,
                supporting_signals=["perception:ownership_hint" if own_hints else "issue:no_assignee"],
                rationale=(
                    "Multiple threads lack a single accountable owner while actors multiply — decisions slow because no one can commit. "
                    "Next: assign one DRI per thread and record it where execution happens (issue/PR), not only in chat."
                ),
            )
        )

    # 10 — SHADOW_WORK
    slack_gaps = [d for d in discussed if _discussed_slack_only(d, by_id)]
    if len(slack_gaps) >= 2 or (len(slack_gaps) >= 1 and (churn_h or has_strong_signal(sig))):
        gids = _supporting_ids([d.id for d in slack_gaps], pool_for_pad, sig)
        out.append(
            ExecutionSituation(
                type="SHADOW_WORK",
                severity=0.75 if len(slack_gaps) >= 2 else 0.58,
                supporting_gap_ids=gids,
                supporting_signals=["slack_only_threads", "discussion_churn:high"] if churn_h else ["slack_only_threads"],
                rationale=(
                    "Work is being negotiated in Slack-only threads without durable links to issues or PRs — execution is invisible to planning. "
                    "Next: open or link a tracking artifact for each thread before the next stand-down."
                ),
            )
        )

    # 11 — SCOPE_DRIFT (non–HOLD_START / non–CLARIFY already emitted)
    has_clarify_situation = any(s.decision_override == "CLARIFY_SPEC" for s in out)
    if not hold_emitted and not has_clarify_situation and (
        (scope_elevated and sig.repeated_discussion_present)
        or len(docs) >= 2
        or (len(docs) == 1 and scope_elevated and has_strong_signal(sig))
    ):
        seed = [d.id for d in docs] + [d.id for d in discussed[:2]] or all_gap_ids
        gids = _supporting_ids(seed, pool_for_pad, sig)
        drift_sigs = (
            ["scope_ambiguity:elevated", "repeated_discussion_present"]
            if scope_elevated and sig.repeated_discussion_present
            else ["doc_not_connected:multiple"]
        )
        out.append(
            ExecutionSituation(
                type="SCOPE_DRIFT",
                severity=0.65,
                supporting_gap_ids=gids,
                supporting_signals=drift_sigs,
                rationale=(
                    "Scope and written intent are drifting away from what is actually being executed — new asks land without new commitments. "
                    "Next: split new requirements into separately estimated work with explicit owners."
                ),
            )
        )

    # 12 — FRAGMENTED_EXECUTION
    fragmented = sig.focus == "fragmented" or (bool(by_id) and _active_open_projects(by_id) > _ACTIVE_PROJECT_THRESHOLD)
    if fragmented and (not_accel or has_strong_signal(sig)):
        gids = _supporting_ids(all_gap_ids, pool_for_pad, sig)
        out.append(
            ExecutionSituation(
                type="FRAGMENTED_EXECUTION",
                severity=0.6,
                supporting_gap_ids=gids,
                supporting_signals=["focus:fragmented" if sig.focus == "fragmented" else "active_projects:high"],
                rationale=(
                    "Parallel surface area is high while momentum is not accelerating — the team is paying coordination tax on breadth. "
                    "Next: reduce WIP until two outcomes can reach done, then reopen breadth intentionally."
                ),
            )
        )

    merged = merge_cap_situations(out)
    merged = dedupe_overlapping_axis(merged)
    if not merged:
        merged = [
            ExecutionSituation(
                type="FRAGMENTED_EXECUTION",
                severity=0.28,
                supporting_gap_ids=_supporting_ids(all_gap_ids, [], sig),
                supporting_signals=["fallback:minimal_bundle"],
                rationale=(
                    "Coordination gaps are present but signals are quiet — still treat execution as under-described until tracking catches reality. "
                    "Next: pick the riskiest gap and drive it to closure with a named owner this week."
                ),
            )
        ]
    return ensure_situation_floor(merged, all_g, sig)


situation_axis_key = _axis_key
situation_gap_jaccard = _jaccard

__all__ = [
    "ACTOR_COORDINATION_SITUATION_TYPES",
    "SITUATION_TO_DECISION",
    "detect_execution_situations",
    "merge_cap_situations",
    "has_strong_signal",
    "dedupe_overlapping_axis",
    "situation_axis_key",
    "situation_gap_jaccard",
]
