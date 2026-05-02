"""§6 — primary work-item anchors for manager-facing decision copy (deterministic).

Resolves ``evidence_refs`` to concrete ``WorkItem`` rows, scores candidates, and builds
artifact-grounded headline / explanation / next-step strings when the LLM is off or rejected.
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from typing import Any

from vector.contracts.manager_insights_activity import (
    CoordinationDecisionType,
    DecisionBundleItem,
    EvidenceBundle,
    EvidenceItem,
    LinkBundle,
    SignalsV0Debug,
    WorkItem,
    WorkItemBundle,
    WorkItemLink,
)


def _uniq_preserve(xs: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for x in xs:
        if not x or x in seen:
            continue
        seen.add(x)
        out.append(x)
    return out


def _evidence_id_index(evidence: EvidenceBundle | None) -> dict[str, EvidenceItem]:
    if evidence is None:
        return {}
    m: dict[str, EvidenceItem] = {}
    for coll in (evidence.action_items, evidence.blockers, evidence.decisions):
        for it in coll:
            m[it.id] = it
    return m


def _all_evidence_rows(evidence: EvidenceBundle | None) -> list[EvidenceItem]:
    if evidence is None:
        return []
    return [*evidence.action_items, *evidence.blockers, *evidence.decisions]


def expand_evidence_refs_to_work_item_ids(
    refs: list[str],
    wi_by_id: dict[str, WorkItem],
    evidence_by_id: dict[str, EvidenceItem],
) -> list[str]:
    out: list[str] = []
    for r in refs:
        if r in wi_by_id:
            out.append(r)
            continue
        ev = evidence_by_id.get(r)
        if ev is not None:
            out.append(ev.source_work_item_id)
    return _uniq_preserve(out)


def artifact_label_for_work_item(wi: WorkItem) -> str:
    """Human-stable anchor: issue keys, PR numbers, channel/thread hints, or short title."""
    ident = (wi.source_ref or {}).get("identifier") or (wi.source_ref or {}).get("key")
    if isinstance(ident, str) and ident.strip():
        return ident.strip()
    if wi.type == "pull_request":
        tail = wi.id.split("/")[-1].split(":")[-1]
        digits = "".join(c for c in tail if c.isdigit())
        if digits:
            return f"PR #{digits}"
        t = (wi.title or "").strip()
        return (t[:40] + ("…" if len(t) > 40 else "")) if t else "Pull request"
    if wi.type == "issue":
        m = re.search(r"(?:linear:issue:|github:issue:)([\w-]+)", wi.id, re.IGNORECASE)
        if m:
            return m.group(1)
        t = (wi.title or "").strip()
        return (t[:48] + ("…" if len(t) > 48 else "")) if t else "Issue"
    if wi.type == "message_thread":
        ch = (wi.source_ref or {}).get("channel") or (wi.source_ref or {}).get("channel_name")
        if isinstance(ch, str) and ch.strip():
            c = ch.strip()
            return c if c.startswith("#") else f"#{c.lstrip('#')}"
        t = (wi.title or "").strip()
        return (t[:48] + ("…" if len(t) > 48 else "")) if t else "Slack thread"
    if wi.type == "document":
        t = (wi.title or "").strip()
        return (t[:44] + ("…" if len(t) > 44 else "")) if t else "Notion page"
    if wi.type == "call":
        t = (wi.title or "").strip()
        return (t[:44] + ("…" if len(t) > 44 else "")) if t else "Calendar event"
    tail = wi.id.split(":")[-1]
    return tail[:32] if tail else wi.id[:32]


def _link_degree(link_index: dict[str, list[WorkItemLink]], wi_id: str) -> int:
    return len(link_index.get(wi_id, ()))


def _build_link_index(links: LinkBundle | None) -> dict[str, list[WorkItemLink]]:
    out: dict[str, list[WorkItemLink]] = {}
    if links is None:
        return out
    for ln in links.links:
        if ln.confidence not in ("high", "medium"):
            continue
        out.setdefault(ln.from_work_item_id, []).append(ln)
        out.setdefault(ln.to_work_item_id, []).append(ln)
    return out


def _evidence_for_work_item(evidence: EvidenceBundle | None, wi_id: str) -> list[EvidenceItem]:
    return [e for e in _all_evidence_rows(evidence) if e.source_work_item_id == wi_id]


def score_work_item_for_decision(
    wi: WorkItem,
    *,
    link_index: dict[str, list[WorkItemLink]],
    evidence: EvidenceBundle | None,
    signals: SignalsV0Debug | None,
) -> float:
    wid = wi.id
    s = 0.0
    if wi.type == "message_thread":
        s += 4.0
        if signals is not None and signals.repeated_discussion_present:
            s += 3.0
        churn = getattr(signals, "discussion_churn", None) if signals is not None else None
        if churn in ("high", "moderate"):
            s += 1.5
    if wi.type in ("issue", "pull_request"):
        s += 2.0
        if not (wi.owner or "").strip():
            s += 3.0
    if wi.type == "document":
        s += 1.0
    if wi.type == "call":
        s += 0.5

    s += min(6.0, _link_degree(link_index, wid) * 1.0)

    for ev in _evidence_for_work_item(evidence, wid):
        if ev.kind == "blocker":
            s += 3.5
        else:
            s += 0.5
    return s


def select_primary_work_items(
    item: DecisionBundleItem,
    *,
    work_items: WorkItemBundle | None,
    evidence: EvidenceBundle | None,
    links: LinkBundle | None,
    signals: SignalsV0Debug | None,
    max_items: int = 2,
) -> list[WorkItem]:
    if work_items is None or not work_items.items:
        return []
    wi_by_id = {w.id: w for w in work_items.items}
    ev_by_id = _evidence_id_index(evidence)
    wi_ids = expand_evidence_refs_to_work_item_ids(item.decision.evidence_refs, wi_by_id, ev_by_id)
    candidates = [wi_by_id[i] for i in wi_ids if i in wi_by_id]
    if not candidates:
        return []

    link_index = _build_link_index(links)
    def _score(w: WorkItem) -> float:
        return score_work_item_for_decision(
            w,
            link_index=link_index,
            evidence=evidence,
            signals=signals,
        )

    scored = sorted(candidates, key=lambda w: (-_score(w), w.id))
    return scored[:max_items]


def artifact_action_targets_payload(wis: list[WorkItem]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for wi in wis:
        rows.append(
            {
                "work_item_id": wi.id,
                "label": artifact_label_for_work_item(wi),
                "type": wi.type,
                "connector": wi.source if isinstance(wi.source, str) else str(wi.source),
                "url": wi.url,
                "owner": (wi.owner or "").strip() or None,
                "owner_actor_id": str(wi.owner_actor_id) if wi.owner_actor_id is not None else None,
            },
        )
    return rows


def _failure_mode(item: DecisionBundleItem) -> str | None:
    ri = item.decision.required_inputs
    if not isinstance(ri, dict):
        return None
    fm = ri.get("failure_mode")
    return str(fm) if fm is not None else None


def _compressed_issue_tail(
    *,
    failure_mode: str | None,
    decision_type: CoordinationDecisionType,
    wi: WorkItem,
) -> str:
    if failure_mode == "DECISION_FAILURE":
        return "no decision recorded"
    if failure_mode == "OWNERSHIP_FAILURE" or decision_type in (
        "ASSIGN_OWNER",
        "RESOLVE_OWNERSHIP",
    ):
        return "no owner assigned"
    if failure_mode == "EXECUTION_ALIGNMENT_FAILURE" or decision_type in (
        "VERIFY_STATUS",
        "RESOLVE_STATE_MISMATCH",
    ):
        return "state not explicit in tracking"
    if decision_type in (
        "TRACK_BLOCKER",
        "BLOCKER_ESCALATION",
        "MAKE_BLOCKERS_EXPLICIT",
    ):
        return "no resolution path"
    if wi.type == "message_thread":
        return "discussion not tied to a tracked decision"
    if wi.type == "document":
        return "not linked to an execution task"
    return "execution risk on this artifact"


def _verb_for_artifact(
    *,
    decision_type: CoordinationDecisionType,
    wi: WorkItem,
    failure_mode: str | None,
) -> str:
    if wi.type == "message_thread":
        if failure_mode == "DECISION_FAILURE" or decision_type == "FORCE_DECISION":
            return "Post a written decision in"
        return "Close loop in"
    if wi.type == "pull_request" and failure_mode == "OWNERSHIP_FAILURE":
        return "Assign an owner to"
    if wi.type == "issue":
        if decision_type in ("TRACK_BLOCKER", "BLOCKER_ESCALATION", "MAKE_BLOCKERS_EXPLICIT"):
            return "Resolve blocker in"
        if failure_mode == "OWNERSHIP_FAILURE" or decision_type in (
            "ASSIGN_OWNER",
            "RESOLVE_OWNERSHIP",
        ):
            return "Assign owner to"
    if wi.type == "document":
        return "Link"
    if wi.type == "call":
        return "Confirm outcomes from"
    return "Act on"


def _maybe_person_prefix(wi: WorkItem) -> str:
    """Optional 'Ask {Name} to ' when owner string is present (actor id enforces trusted field)."""
    if wi.owner_actor_id is None:
        return ""
    name = (wi.owner or "").strip()
    if not name or len(name) > 48:
        return ""
    # Single-line display name / handle; skip team lists
    if any(x in name.lower() for x in (" everyone", " team", " folks", ";", "\n")):
        return ""
    return f"Ask {name} to "


def build_deterministic_artifact_interpretation(
    item: DecisionBundleItem,
    primary: list[WorkItem],
    labels: list[str],
) -> dict[str, str]:
    """Always returns three non-empty strings grounded in the primary artifact when possible."""
    d = item.decision
    fm = _failure_mode(item)
    if not primary or not labels:
        title_part = (d.title or "Act on evidence").strip()[:120]
        line = f"Open or link the issue or PR behind this gap — {title_part}"
        expl = (
            "Without a concrete issue, PR, or thread id, the team cannot assign ownership "
            "or close the loop in tooling. Surface the artifact in tracking first."
        )
        return {"llm_headline": line[:200], "llm_explanation": expl, "llm_next_step": line[:300]}

    wi = primary[0]
    label = labels[0]
    tail = _compressed_issue_tail(failure_mode=fm, decision_type=d.decision_type, wi=wi)
    verb = _verb_for_artifact(decision_type=d.decision_type, wi=wi, failure_mode=fm)
    person = _maybe_person_prefix(wi)

    next_line = f"{person}{verb} {label} — {tail}"

    head = next_line
    words = head.split()
    if len(words) > 14:
        head = " ".join(words[:14]).rstrip(",;:") + "…"

    second = labels[1] if len(labels) > 1 else None
    extra = f" Also watch {second}." if second else ""
    expl = f"When {label} stays in this state, execution reviews miss the blocking path.{extra}"
    return {"llm_headline": head, "llm_explanation": expl.strip(), "llm_next_step": next_line}


def merge_required_inputs_artifact_targets(
    item: DecisionBundleItem,
    targets: list[dict[str, Any]],
) -> dict[str, Any]:
    ri = item.decision.required_inputs
    base = dict(ri) if isinstance(ri, dict) else {}
    if targets:
        base["artifact_action_targets"] = targets
    return base


__all__ = [
    "artifact_action_targets_payload",
    "artifact_label_for_work_item",
    "build_deterministic_artifact_interpretation",
    "expand_evidence_refs_to_work_item_ids",
    "merge_required_inputs_artifact_targets",
    "select_primary_work_items",
    "score_work_item_for_decision",
]
