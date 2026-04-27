"""Step 6 — deterministic signal computation (no LLM)."""

from __future__ import annotations

from datetime import datetime, timedelta

from vector.contracts.manager_insights_activity import (
    EvidenceBundle,
    GapBundle,
    KeyAchievementsBundleDebug,
    LinkBundle,
    RawHighlightsBundleDebug,
    SignalsV0Debug,
    WorkItem,
    WorkItemLink,
    WorkItemBundle,
)

_EXEC_TYPES = {"issue", "pull_request"}
_DISCUSSION_TYPES = {"call", "message_thread"}
_LINK_OK = {"high", "medium"}
_DONE_STATUS = {"done", "closed", "merged", "completed", "complete", "canceled", "cancelled"}
_URGENT_TERMS = ("urgent", "p0", "p1", "critical", "sev1", "incident")
_ASK_HELP_TERMS = ("need help", "can someone", "blocked", "stuck", "waiting on")
_GIVE_HELP_TERMS = ("i can help", "i will help", "happy to help", "paired", "reviewed", "unblocked")
_DEFENSIVE_TERMS = ("won't fix", "wont fix", "not changing", "disagree")
_PROACTIVE_TERMS = ("addressed review", "updated per feedback", "followed up", "resolved review")
_FRICTION_TERMS = ("clarification", "confusion", "unclear", "disagree", "blocked", "waiting on")


def _is_done(item: WorkItem) -> bool:
    if item.closed_at is not None:
        return True
    return (item.status or "").strip().lower() in _DONE_STATUS


def _is_open(item: WorkItem) -> bool:
    return not _is_done(item)


def _blob(*parts: str | None) -> str:
    return " ".join((p or "") for p in parts).lower()


def _adjacency(links: LinkBundle) -> dict[str, set[str]]:
    out: dict[str, set[str]] = {}
    for edge in links.links:
        if edge.confidence not in _LINK_OK:
            continue
        out.setdefault(edge.from_work_item_id, set()).add(edge.to_work_item_id)
        out.setdefault(edge.to_work_item_id, set()).add(edge.from_work_item_id)
    return out


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


def _merge_texts(work_items: WorkItemBundle, evidence: EvidenceBundle) -> list[str]:
    rows: list[str] = []
    for w in work_items.items:
        rows.append(_blob(w.title, w.summary))
    for e in [*evidence.action_items, *evidence.blockers, *evidence.decisions]:
        rows.append(_blob(e.statement, e.evidence))
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
    evidence: EvidenceBundle,
    links: LinkBundle,
    gaps: GapBundle,
    key_achievements: KeyAchievementsBundleDebug,
    raw_highlights: RawHighlightsBundleDebug,
) -> SignalsV0Debug:
    """Build deterministic SignalsV0-like values + explain strings from Steps 2–5.6."""
    by_id = {w.id: w for w in work_items.items}
    adj = _adjacency(links)
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

    merged_rows = _merge_texts(work_items, evidence)
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
        },
    )
