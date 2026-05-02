"""Step 6 — deterministic signal computation (no LLM).

§6 Step 14: ``compute_signals`` takes the same ``CoordinationLinkInputBundle`` as linking and gaps
(Step-3 evidence + validated ``PerceptionRow`` list). Mention adjacency matches ``compute_gaps``; perception
text is merged into term-based signals (support, feedback, friction) without raw LLM JSON.
"""

from __future__ import annotations

import uuid
from collections import Counter
from datetime import datetime, timedelta

from vector.contracts.manager_insights_activity import (
    CoordinationLinkInputBundle,
    EvidenceBundle,
    GapBundle,
    KeyAchievementsBundleDebug,
    LinkBundle,
    PerceptionRow,
    RawHighlightsBundleDebug,
    SignalDeliveryStrength,
    SignalsV0Debug,
    WorkItem,
    WorkItemBundle,
)
from vector.domains.manager_insights.compute_gaps import (
    _adjacency,
    _merge_adjacency,
    _perception_mention_adjacency,
)

_EXEC_TYPES = {"issue", "pull_request"}
_DISCUSSION_TYPES = {"call", "message_thread"}
_DONE_STATUS = {"done", "closed", "merged", "completed", "complete", "canceled", "cancelled"}
_URGENT_TERMS = ("urgent", "p0", "p1", "critical", "sev1", "incident")
_ASK_HELP_TERMS = ("need help", "can someone", "blocked", "stuck", "waiting on")
_GIVE_HELP_TERMS = ("i can help", "i will help", "happy to help", "paired", "reviewed", "unblocked")
_DEFENSIVE_TERMS = ("won't fix", "wont fix", "not changing", "disagree")
_PROACTIVE_TERMS = ("addressed review", "updated per feedback", "followed up", "resolved review")
_FRICTION_TERMS = ("clarification", "confusion", "unclear", "disagree", "blocked", "waiting on")

# §6 Step 20 — coordination extension signals (deterministic; no LLM). See coordination plan §2.3 Step 6.
_SCOPE_AMBIGUITY_TERMS = (
    "unclear scope",
    "scope creep",
    "out of scope",
    "requirements tbd",
    "not defined",
    "boundary",
    "success criteria",
)
_DISCUSSION_CHURN_TERMS = (
    "reopen",
    "circling",
    "still discussing",
    "going in circles",
    "long thread",
    "another round",
    "back to this",
)
_CONTRADICTION_TERMS = (
    "contradiction",
    "contradicts",
    "conflicting",
    "two different",
    "on second thought",
)


def _norm_identity_str(value: str) -> str:
    return value.strip().lower()


def _identity_tuple_actor_or_string(
    *,
    actor_id: uuid.UUID | None,
    source: str,
    role: str,
    display: str | None,
) -> tuple[object, ...] | None:
    """Stable bucket for coordination faces: prefer canonical actor, else normalized display string."""
    if actor_id is not None:
        return ("a", actor_id)
    if display and str(display).strip():
        return ("s", source, role, _norm_identity_str(str(display)))
    return None


def _identity_keys_for_item(w: WorkItem) -> list[tuple[object, ...]]:
    keys: list[tuple[object, ...]] = []
    owner_key = _identity_tuple_actor_or_string(
        actor_id=w.owner_actor_id,
        source=w.source,
        role="owner",
        display=w.owner,
    )
    if owner_key is not None:
        keys.append(owner_key)
    participants = list(w.participants or [])
    actor_ids = list(w.participant_actor_ids or [])
    for i, p in enumerate(participants):
        aid = actor_ids[i] if i < len(actor_ids) else None
        pk = _identity_tuple_actor_or_string(
            actor_id=aid if isinstance(aid, uuid.UUID) else None,
            source=w.source,
            role="participant",
            display=p,
        )
        if pk is not None:
            keys.append(pk)
    return keys


def _open_exec_owner_bucket(w: WorkItem) -> tuple[object, ...] | None:
    if w.owner_actor_id is not None:
        return ("a", w.owner_actor_id)
    if w.owner and str(w.owner).strip():
        return ("s", w.source, "owner", _norm_identity_str(str(w.owner)))
    return None


def _actor_fragmentation_count(items: list[WorkItem]) -> int:
    bag: set[tuple[object, ...]] = set()
    for w in items:
        bag.update(_identity_keys_for_item(w))
    return len(bag)


def _actor_load_score(open_exec: list[WorkItem]) -> int:
    counts: Counter[tuple[object, ...]] = Counter()
    for w in open_exec:
        b = _open_exec_owner_bucket(w)
        if b is not None:
            counts[b] += 1
    return max(counts.values()) if counts else 0


def _actor_consistency_score(discussion_items: list[WorkItem], open_exec: list[WorkItem]) -> float:
    disc: set[tuple[object, ...]] = set()
    for w in discussion_items:
        b = _open_exec_owner_bucket(w)
        if b is not None:
            disc.add(b)
    exe: set[tuple[object, ...]] = set()
    for w in open_exec:
        b = _open_exec_owner_bucket(w)
        if b is not None:
            exe.add(b)
    if not disc or not exe:
        return 0.0
    return len(disc & exe) / len(disc | exe)


def _signal_level_high_mod_low(
    *,
    score_high: bool,
    score_moderate: bool,
) -> SignalDeliveryStrength:
    if score_high:
        return "high"
    if score_moderate:
        return "moderate"
    return "low"


def _scope_ambiguity_signal(
    perception_rows: list[PerceptionRow],
    merged_rows: list[str],
) -> tuple[SignalDeliveryStrength, str]:
    """Count ``unclear_scope`` perception rows + scope-ish terms (coordination plan §2.3)."""
    n_unclear = sum(1 for r in perception_rows if r.ambiguity_class == "unclear_scope")
    scope_term_hits = sum(_count_terms(t, _SCOPE_AMBIGUITY_TERMS) for t in merged_rows)
    high = n_unclear >= 2 or (n_unclear >= 1 and scope_term_hits >= 3) or scope_term_hits >= 5
    moderate = not high and (n_unclear >= 1 or scope_term_hits >= 2)
    level = _signal_level_high_mod_low(score_high=high, score_moderate=moderate)
    explain = (
        f"unclear_scope perception rows={n_unclear}, scope-term hits={scope_term_hits} "
        f"(§6 Step 20; coordination §2.3)"
    )
    return level, explain


def _discussion_churn_signal(
    perception_rows: list[PerceptionRow],
    merged_rows: list[str],
    gap_counts: dict[str, int],
    raw_highlights: RawHighlightsBundleDebug,
) -> tuple[SignalDeliveryStrength, str]:
    """``discussion_loop`` rows + discussed-not-linked gaps + churn terms + repeated-term highlights."""
    n_loop = sum(1 for r in perception_rows if r.ambiguity_class == "discussion_loop")
    discussed_gaps = gap_counts.get("discussed_not_linked_to_work", 0)
    churn_term_hits = sum(_count_terms(t, _DISCUSSION_CHURN_TERMS) for t in merged_rows)
    term_highlights = sum(1 for h in raw_highlights.items if h.text.lower().startswith("term "))
    high = (
        n_loop >= 2
        or discussed_gaps >= 2
        or (n_loop >= 1 and discussed_gaps >= 1)
        or churn_term_hits >= 4
    )
    moderate = not high and (
        n_loop >= 1 or discussed_gaps >= 1 or churn_term_hits >= 2 or term_highlights >= 1
    )
    level = _signal_level_high_mod_low(score_high=high, score_moderate=moderate)
    explain = (
        f"discussion_loop rows={n_loop}, discussed_not_linked gaps={discussed_gaps}, "
        f"churn-term hits={churn_term_hits}, repeated-term highlights={term_highlights} "
        f"(§6 Step 20; coordination §2.3)"
    )
    return level, explain


def _contradiction_density_signal(
    perception_rows: list[PerceptionRow],
    merged_rows: list[str],
) -> tuple[SignalDeliveryStrength, str]:
    """Contradiction-class perception rows + contradiction-ish terms."""
    n_contra = sum(1 for r in perception_rows if r.ambiguity_class == "contradiction")
    contra_term_hits = sum(_count_terms(t, _CONTRADICTION_TERMS) for t in merged_rows)
    high = n_contra >= 2 or contra_term_hits >= 4
    moderate = not high and (n_contra >= 1 or contra_term_hits >= 2)
    level = _signal_level_high_mod_low(score_high=high, score_moderate=moderate)
    explain = (
        f"contradiction perception rows={n_contra}, contradiction-term hits={contra_term_hits} "
        f"(§6 Step 20; coordination §2.3)"
    )
    return level, explain


def _is_done(item: WorkItem) -> bool:
    if item.closed_at is not None:
        return True
    return (item.status or "").strip().lower() in _DONE_STATUS


def _is_open(item: WorkItem) -> bool:
    return not _is_done(item)


def _blob(*parts: str | None) -> str:
    return " ".join((p or "") for p in parts).lower()


def _linked_exec_ids(source_id: str, links: dict[str, set[str]], by_id: dict[str, WorkItem]) -> list[str]:
    out = []
    for neighbor in sorted(links.get(source_id, set())):
        item = by_id.get(neighbor)
        if item and item.type in _EXEC_TYPES:
            out.append(neighbor)
    return out


def _delivery_strength(done_exec_count: int) -> tuple[str, str]:
    if done_exec_count >= 10:
        return "high", f"done execution items={done_exec_count} (>=10)"
    if done_exec_count >= 4:
        return "moderate", f"done execution items={done_exec_count} (>=4)"
    return "low", f"done execution items={done_exec_count} (<4)"


def _urgent_pressure(open_urgent_count: int) -> tuple[str, str]:
    if open_urgent_count >= 3:
        return "high", f"open urgent execution items={open_urgent_count} (>=3)"
    if open_urgent_count >= 1:
        return "moderate", f"open urgent execution items={open_urgent_count} (>=1)"
    return "low", "no open urgent execution items"


def _execution_momentum(done_exec: list[WorkItem]) -> tuple[str, str]:
    if len(done_exec) < 4:
        return "steady", f"insufficient done execution points={len(done_exec)} (<4)"
    marks = []
    for item in done_exec:
        marks.append(item.closed_at or item.updated_at or item.created_at)
    points = sorted(dt for dt in marks if dt is not None)
    if len(points) < 4:
        return "steady", f"insufficient dated points={len(points)} (<4)"
    latest = points[-1]
    recent_start = latest - timedelta(days=14)
    prior_start = latest - timedelta(days=28)
    recent = sum(1 for dt in points if dt > recent_start)
    prior = sum(1 for dt in points if prior_start < dt <= recent_start)
    if recent >= prior + 2 and recent >= int(prior * 1.4):
        return "accelerating", f"recent done={recent} vs prior={prior} (last 14d buckets)"
    if prior >= recent + 2 and prior >= int(recent * 1.4):
        return "slowing", f"recent done={recent} vs prior={prior} (last 14d buckets)"
    return "steady", f"recent done={recent} vs prior={prior} (last 14d buckets)"


def _count_terms(text: str, terms: tuple[str, ...]) -> int:
    lower = text.lower()
    return sum(1 for t in terms if t in lower)


def _perception_text_blobs(rows: list[PerceptionRow]) -> list[str]:
    """Validated perception prose only (same fields as link merge surface)."""
    out: list[str] = []
    for row in rows:
        parts: list[str] = [row.statement, row.quote]
        if row.ambiguity_quote and row.ambiguity_quote.strip():
            parts.append(row.ambiguity_quote)
        if row.state_transition is not None:
            parts.append(row.state_transition.quote)
        parts.extend(row.waits_on or [])
        parts.extend(row.blocked_by or [])
        blob = _blob(" ".join(p for p in parts if p))
        if blob.strip():
            out.append(blob)
    return out


def _merge_texts(
    work_items: WorkItemBundle,
    evidence: EvidenceBundle,
    perception_rows: list[PerceptionRow],
) -> list[str]:
    rows: list[str] = []
    for w in work_items.items:
        rows.append(_blob(w.title, w.summary))
    for e in [*evidence.action_items, *evidence.blockers, *evidence.decisions]:
        rows.append(_blob(e.statement, e.evidence))
    rows.extend(_perception_text_blobs(perception_rows))
    return rows


def _doc_linkage(
    docs: list[WorkItem],
    by_id: dict[str, WorkItem],
    adj: dict[str, set[str]],
) -> tuple[str, str]:
    if not docs:
        return "partially_linked", "no document items present"
    linked = 0
    for doc in docs:
        exec_links = _linked_exec_ids(doc.id, adj, by_id)
        if exec_links:
            linked += 1
    ratio = linked / max(1, len(docs))
    if ratio >= 0.75:
        return "linked", f"linked docs={linked}/{len(docs)} (>=75%)"
    if ratio >= 0.35:
        return "partially_linked", f"linked docs={linked}/{len(docs)} (>=35%)"
    return "not_linked", f"linked docs={linked}/{len(docs)} (<35%)"


def _focus(exec_items: list[WorkItem]) -> tuple[str, str]:
    projects = sorted(
        {
            (w.project or "").strip().lower()
            for w in exec_items
            if isinstance(w.project, str) and w.project.strip()
        }
    )
    n = len(projects)
    if n <= 2:
        return "focused", f"active execution projects={n} (<=2)"
    if n <= 4:
        return "moderate", f"active execution projects={n} (<=4)"
    return "fragmented", f"active execution projects={n} (>4)"


def _collaboration_intensity(discussion_items: list[WorkItem]) -> tuple[str, str]:
    participants: set[str] = set()
    for row in discussion_items:
        participants.update(p for p in row.participants if p)
        if row.owner:
            participants.add(row.owner)
    score = len(discussion_items) + len(participants)
    if score >= 20:
        return "high", f"discussion_items={len(discussion_items)} participants={len(participants)} score={score}"
    if score >= 8:
        return "moderate", f"discussion_items={len(discussion_items)} participants={len(participants)} score={score}"
    return "low", f"discussion_items={len(discussion_items)} participants={len(participants)} score={score}"


def _support_pattern(rows: list[str]) -> tuple[str, str]:
    asks = sum(_count_terms(r, _ASK_HELP_TERMS) for r in rows)
    gives = sum(_count_terms(r, _GIVE_HELP_TERMS) for r in rows)
    if asks == 0 and gives == 0:
        return "balanced", "no explicit help-request/help-given markers"
    if gives >= asks + 2 and gives >= int(asks * 1.3):
        return "gives_help", f"help markers gives={gives} asks={asks}"
    if asks >= gives + 2 and asks >= int(gives * 1.3):
        return "asks_for_help", f"help markers gives={gives} asks={asks}"
    return "balanced", f"help markers gives={gives} asks={asks}"


def _feedback_reception(exec_items: list[WorkItem], rows: list[str]) -> tuple[str, str]:
    texts = rows + [_blob(w.title, w.summary) for w in exec_items if w.type == "pull_request"]
    proactive = sum(_count_terms(t, _PROACTIVE_TERMS) for t in texts)
    defensive = sum(_count_terms(t, _DEFENSIVE_TERMS) for t in texts)
    if proactive >= defensive + 2 and proactive >= 2:
        return "proactive", f"proactive markers={proactive}, defensive markers={defensive}"
    if defensive >= proactive + 2 and defensive >= 2:
        return "defensive", f"proactive markers={proactive}, defensive markers={defensive}"
    return "neutral", f"defaulted to neutral (proactive={proactive}, defensive={defensive})"


def _coordination_role(
    discussion_items: list[WorkItem],
    evidence: EvidenceBundle,
    _achievements: KeyAchievementsBundleDebug,
) -> tuple[str, str]:
    decisions = len(evidence.decisions)
    actions = len(evidence.action_items)
    lead_score = (decisions * 2) + actions + (len(discussion_items) // 4)
    if lead_score >= 8:
        return "driving", f"lead_score={lead_score} (decisions={decisions}, actions={actions})"
    if lead_score >= 3:
        return "contributing", f"lead_score={lead_score} (decisions={decisions}, actions={actions})"
    return "peripheral", f"lead_score={lead_score} (decisions={decisions}, actions={actions})"


def compute_signals(
    work_items: WorkItemBundle,
    links: LinkBundle,
    gaps: GapBundle,
    key_achievements: KeyAchievementsBundleDebug,
    raw_highlights: RawHighlightsBundleDebug,
    *,
    coordination_input: CoordinationLinkInputBundle,
) -> SignalsV0Debug:
    """Build deterministic SignalsV0-like values + explain strings from Steps 2–5.6.

    §6 Step 14: ``coordination_input`` must be the same bundle passed to ``link_work_items`` and
    ``compute_gaps`` for this run.
    """
    evidence = coordination_input.evidence
    by_id = {w.id: w for w in work_items.items}
    adj = _merge_adjacency(
        _adjacency(links),
        _perception_mention_adjacency(coordination_input.perception_rows, by_id),
    )
    exec_items = [w for w in work_items.items if w.type in _EXEC_TYPES]
    done_exec = [w for w in exec_items if _is_done(w)]
    open_exec = [w for w in exec_items if _is_open(w)]
    docs = [w for w in work_items.items if w.type == "document"]
    discussion_items = [w for w in work_items.items if w.type in _DISCUSSION_TYPES]
    gap_counts: dict[str, int] = {}
    for g in gaps.gaps:
        gap_counts[g.type] = gap_counts.get(g.type, 0) + 1
    open_urgent_count = 0
    for item in open_exec:
        if any(term in _blob(item.title, item.summary) for term in _URGENT_TERMS):
            open_urgent_count += 1

    delivery_strength, explain_delivery = _delivery_strength(len(done_exec))
    urgent_pressure, explain_urgent = _urgent_pressure(open_urgent_count)

    action_total = len(evidence.action_items)
    expected_not_executed = gap_counts.get("expected_not_executed", 0)
    if action_total == 0:
        expectation_coverage = "partial"
        explain_expectation = "no action_items in evidence; default partial"
    else:
        covered = max(0, action_total - expected_not_executed)
        ratio = covered / action_total
        if ratio >= 0.8:
            expectation_coverage = "high"
        elif ratio >= 0.5:
            expectation_coverage = "partial"
        else:
            expectation_coverage = "low"
        explain_expectation = f"action coverage={covered}/{action_total} ({ratio:.2f})"

    followed = 0
    for row in evidence.action_items:
        linked = _linked_exec_ids(row.source_work_item_id, adj, by_id)
        if any(_is_done(by_id[eid]) for eid in linked if eid in by_id):
            followed += 1
    if action_total == 0:
        follow_through = "partial"
        explain_follow = "no action_items; default partial"
    else:
        ratio = followed / action_total
        if ratio >= 0.7:
            follow_through = "strong"
        elif ratio >= 0.35:
            follow_through = "partial"
        else:
            follow_through = "weak"
        explain_follow = f"action_items linked to done execution={followed}/{action_total} ({ratio:.2f})"

    blocker_total = len(evidence.blockers)
    blocker_untracked = gap_counts.get("blocker_not_tracked", 0)
    if blocker_total == 0:
        blocker_visibility = "partial"
        explain_blockers = "no blockers extracted; default partial"
    else:
        tracked = max(0, blocker_total - blocker_untracked)
        ratio = tracked / blocker_total
        if ratio >= 0.75:
            blocker_visibility = "visible"
        elif ratio >= 0.35:
            blocker_visibility = "partial"
        else:
            blocker_visibility = "not_visible"
        explain_blockers = f"tracked blockers={tracked}/{blocker_total} ({ratio:.2f})"

    repeated_discussion_present = bool(gap_counts.get("discussed_not_linked_to_work", 0))
    if not repeated_discussion_present:
        repeated_discussion_present = any(
            h.text.lower().startswith("term ") for h in raw_highlights.items
        )
    explain_repeated = (
        "true via discussed_not_linked_to_work gap or repeated-term raw highlight"
        if repeated_discussion_present
        else "false: no repeated-term highlight and no discussed_not_linked_to_work gaps"
    )

    execution_momentum, explain_momentum = _execution_momentum(done_exec)
    documentation_linkage, explain_doc_linkage = _doc_linkage(docs, by_id, adj)
    focus, explain_focus = _focus(exec_items)
    collaboration_intensity, explain_collab = _collaboration_intensity(discussion_items)

    merged_rows = _merge_texts(work_items, evidence, coordination_input.perception_rows)
    support_pattern, explain_support = _support_pattern(merged_rows)
    feedback_reception, explain_feedback = _feedback_reception(exec_items, merged_rows)
    coordination_role, explain_coordination = _coordination_role(
        discussion_items, evidence, key_achievements
    )

    friction_markers = sum(_count_terms(r, _FRICTION_TERMS) for r in merged_rows)
    if gap_counts.get("blocker_not_tracked", 0) > 0 or friction_markers >= 4:
        interaction_friction = "present"
    elif friction_markers > 0:
        interaction_friction = "unclear"
    else:
        interaction_friction = "absent"
    explain_friction = (
        f"friction markers={friction_markers}, blocker_not_tracked gaps={gap_counts.get('blocker_not_tracked', 0)}"
    )

    scope_ambiguity, explain_scope = _scope_ambiguity_signal(
        coordination_input.perception_rows,
        merged_rows,
    )
    discussion_churn, explain_churn = _discussion_churn_signal(
        coordination_input.perception_rows,
        merged_rows,
        gap_counts,
        raw_highlights,
    )
    contradiction_density, explain_contra = _contradiction_density_signal(
        coordination_input.perception_rows,
        merged_rows,
    )

    actor_fragmentation = _actor_fragmentation_count(work_items.items)
    actor_load = _actor_load_score(open_exec)
    actor_consistency = _actor_consistency_score(discussion_items, open_exec)
    explain_actor_frag = (
        f"distinct coordination identities={actor_fragmentation} across {len(work_items.items)} work items "
        f"(actor UUID when present else per-source string bucket)"
    )
    explain_actor_load = (
        f"max open execution items per owner identity={actor_load} over {len(open_exec)} open execution rows"
    )
    explain_actor_consistency = (
        f"owner identity Jaccard(discussion, open_exec)={actor_consistency:.2f} "
        f"(discussion={len(discussion_items)}, open_exec={len(open_exec)})"
    )

    return SignalsV0Debug(
        delivery_strength=delivery_strength,
        urgent_pressure=urgent_pressure,
        expectation_coverage=expectation_coverage,
        follow_through=follow_through,
        blocker_visibility=blocker_visibility,
        repeated_discussion_present=repeated_discussion_present,
        execution_momentum=execution_momentum,
        documentation_linkage=documentation_linkage,
        focus=focus,
        collaboration_intensity=collaboration_intensity,
        support_pattern=support_pattern,
        feedback_reception=feedback_reception,
        coordination_role=coordination_role,
        interaction_friction=interaction_friction,
        scope_ambiguity=scope_ambiguity,
        discussion_churn=discussion_churn,
        contradiction_density=contradiction_density,
        actor_fragmentation=actor_fragmentation,
        actor_load=actor_load,
        actor_consistency=actor_consistency,
        explain={
            "delivery_strength": explain_delivery,
            "urgent_pressure": explain_urgent,
            "expectation_coverage": explain_expectation,
            "follow_through": explain_follow,
            "blocker_visibility": explain_blockers,
            "repeated_discussion_present": explain_repeated,
            "execution_momentum": explain_momentum,
            "documentation_linkage": explain_doc_linkage,
            "focus": explain_focus,
            "collaboration_intensity": explain_collab,
            "support_pattern": explain_support,
            "feedback_reception": explain_feedback,
            "coordination_role": explain_coordination,
            "interaction_friction": explain_friction,
            "scope_ambiguity": explain_scope,
            "discussion_churn": explain_churn,
            "contradiction_density": explain_contra,
            "actor_fragmentation": explain_actor_frag,
            "actor_load": explain_actor_load,
            "actor_consistency": explain_actor_consistency,
        },
    )
