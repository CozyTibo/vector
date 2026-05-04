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

# Product-facing titles — reject diagnosis / failure-mode phrasing (substring checks).
_ACTION_TITLE_BANNED_SUBSTRINGS: tuple[str, ...] = (
    "this is",
    "because ",
    " because",
    "system state",
    "execution is slowing",
    "execution is stuck",
    "ownership is broken",
    "ownership failure",
    "broken ownership",
    "stop ownership",
    "consequence",
    "execution alignment",
    "alignment failure",
)
_OWNERSHIP_DIAGNOSTIC_RE = re.compile(
    r"\bownership\s+is\b|\bfailure\s+mode\b|\bexecution\s+alignment\b",
    re.IGNORECASE,
)


def contains_product_banned_phrasing(text: str) -> bool:
    """Diagnostic / failure-mode fragments that must not appear in manager-facing copy."""
    t = (text or "").strip()
    if not t:
        return False
    low = t.lower()
    if any(b in low for b in _ACTION_TITLE_BANNED_SUBSTRINGS):
        return True
    return _OWNERSHIP_DIAGNOSTIC_RE.search(t) is not None


def is_valid_action_title(title: str) -> bool:
    """True when ``title`` reads as imperative action, not diagnostic narrative."""
    t = (title or "").strip()
    if len(t) < 8:
        return False
    if contains_product_banned_phrasing(t):
        return False
    first = t.split(None, 1)[0].lower().rstrip(",.:;")
    allowed_verbs = frozenset(
        {
            "talk",
            "ask",
            "resolve",
            "assign",
            "stop",
            "clarify",
            "decide",
            "link",
            "track",
            "close",
            "post",
            "confirm",
            "open",
            "file",
            "pause",
            "unblock",
            "review",
            "merge",
            "document",
            "escalate",
            "verify",
            "name",
            "cut",
            "complete",
            "ship",
            "schedule",
        },
    )
    return first in allowed_verbs


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
    deprioritize_work_item_ids: frozenset[str] | None = None,
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
        s = score_work_item_for_decision(
            w,
            link_index=link_index,
            evidence=evidence,
            signals=signals,
        )
        if deprioritize_work_item_ids is not None and w.id in deprioritize_work_item_ids:
            s -= 6.0
        return s

    scored = sorted(candidates, key=lambda w: (-_score(w), w.id))
    return scored[:max_items]


def _first_display_token(name: str) -> str | None:
    n = name.strip()
    if not n or len(n) > 48:
        return None
    tok = n.split()[0].strip().strip("@")
    if len(tok) > 32 or not tok:
        return None
    return tok


def collect_actor_display_names(wi: WorkItem) -> list[str]:
    """Stable display tokens for people tied to actor ids (owner + threaded participants)."""
    out: list[str] = []
    if wi.owner_actor_id is not None and wi.owner:
        t = _first_display_token(wi.owner)
        if t:
            out.append(t)
    parts = wi.participants or []
    ids = wi.participant_actor_ids or []
    for i, p in enumerate(parts):
        if i < len(ids) and ids[i] is not None:
            t = _first_display_token(str(p))
            if t:
                out.append(t)
    return _uniq_preserve(out)


def format_actor_names_for_context(names: list[str]) -> str:
    u = _uniq_preserve(names)[:4]
    if len(u) == 0:
        return ""
    if len(u) == 1:
        return u[0]
    if len(u) == 2:
        return f"{u[0]} and {u[1]}"
    return f"{u[0]}, {u[1]} and others"


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
                "actor_display_names": collect_actor_display_names(wi),
            },
        )
    return rows


def _failure_mode(item: DecisionBundleItem) -> str | None:
    ri = item.decision.required_inputs
    if not isinstance(ri, dict):
        return None
    fm = ri.get("failure_mode")
    return str(fm) if fm is not None else None


def pure_action_title_from_primary(
    primary: list[WorkItem],
    labels: list[str],
    *,
    decision_type: CoordinationDecisionType,
    failure_mode: str | None,
) -> str:
    """Imperative title: verb + concrete artifact label (no diagnostic tail)."""
    wi = primary[0]
    label = labels[0]
    if wi.type == "message_thread":
        return f"Resolve the debate in {label}"
    if wi.type == "pull_request":
        if decision_type in (
            "UNBLOCK_REVIEW",
            "TRACK_BLOCKER",
            "BLOCKER_ESCALATION",
            "MAKE_BLOCKERS_EXPLICIT",
        ):
            return f"Unblock {label}"
        return f"Review {label}"
    if wi.type == "issue":
        if decision_type in ("TRACK_BLOCKER", "BLOCKER_ESCALATION", "MAKE_BLOCKERS_EXPLICIT"):
            return f"Resolve the blocker on {label}"
        if (
            not (wi.owner or "").strip()
            or failure_mode == "OWNERSHIP_FAILURE"
            or decision_type in ("ASSIGN_OWNER", "RESOLVE_OWNERSHIP")
        ):
            return f"Assign an owner to {label}"
        return f"Verify status on {label}"
    if wi.type == "document":
        return f"Link {label} to execution"
    if wi.type == "call":
        return f"Confirm outcomes from {label}"
    return f"Track progress on {label}"


def derive_context_from_real_signals(
    primary: list[WorkItem],
    labels: list[str],
    *,
    evidence: EvidenceBundle | None,
    actor_display_names: list[str],
) -> str:
    """Factual sentences from counts, owners, blockers, and named actors."""
    wi_ids = {w.id for w in primary}
    rows = [e for e in _all_evidence_rows(evidence) if e.source_work_item_id in wi_ids]
    n_ev = len(rows)
    n_blockers = sum(1 for e in rows if e.kind == "blocker")
    name_phrase = format_actor_names_for_context(actor_display_names)

    wi = primary[0]
    lab0 = labels[0] if labels else artifact_label_for_work_item(wi)
    parts: list[str] = []

    if wi.type == "message_thread":
        if n_ev >= 2:
            if name_phrase:
                parts.append(
                    f"{name_phrase} exchanged {n_ev} tracked updates in {lab0} "
                    "without a recorded decision.",
                )
            else:
                parts.append(f"{n_ev} tracked updates in {lab0} without a recorded decision.")
        elif name_phrase:
            parts.append(f"{name_phrase} discussed {lab0} without closing the loop in tracking.")
        else:
            parts.append(f"Discussion in {lab0} has no recorded decision in tracking.")

    if wi.type == "issue" and not (wi.owner or "").strip():
        parts.append(f"No owner assigned to {lab0}.")

    if wi.type == "pull_request":
        if n_blockers > 0:
            who = name_phrase
            if who:
                parts.append(
                    f"{lab0} is blocked in tracking and {who} have not posted "
                    "a resolution.",
                )
            else:
                parts.append(f"{lab0} is blocked in tracking without a posted resolution.")
        elif n_ev >= 2:
            parts.append(f"{lab0} has multiple tracking updates without closure.")

    if len(labels) > 1:
        parts.append(f"{labels[1]} remains tied to the same execution thread.")

    if not parts:
        parts.append(
            f"Signals for this decision resolve to {lab0}; tie chat to tickets "
            "so the next step is explicit.",
        )

    text = " ".join(parts[:2]).strip()
    if len(text) > 320:
        text = text[:319].rsplit(" ", 1)[0] + "…"
    return text


def build_instruction_next_step(
    primary: list[WorkItem],
    labels: list[str],
    *,
    decision_type: CoordinationDecisionType,
) -> str:
    chunks: list[str] = []
    for i, w in enumerate(primary[:2]):
        lab = labels[i] if i < len(labels) else artifact_label_for_work_item(w)
        if w.type == "message_thread":
            chunks.append(f"post a decision in {lab}")
        elif w.type == "issue":
            if decision_type in ("TRACK_BLOCKER", "BLOCKER_ESCALATION", "MAKE_BLOCKERS_EXPLICIT"):
                chunks.append(f"resolve the blocker on {lab}")
            elif not (w.owner or "").strip() or decision_type in (
                "ASSIGN_OWNER",
                "RESOLVE_OWNERSHIP",
            ):
                chunks.append(f"assign an owner to {lab}")
            else:
                chunks.append(f"confirm status on {lab}")
        elif w.type == "pull_request":
            if decision_type in (
                "UNBLOCK_REVIEW",
                "TRACK_BLOCKER",
                "BLOCKER_ESCALATION",
                "MAKE_BLOCKERS_EXPLICIT",
            ):
                chunks.append(f"unblock {lab}")
            else:
                chunks.append(f"review or merge {lab}")
        elif w.type == "document":
            chunks.append(f"link {lab} to an execution task")
        elif w.type == "call":
            chunks.append(f"confirm outcomes from {lab}")
    if not chunks:
        chunks.append("tie chat updates to a tracked artifact")
    body = " and ".join(chunks)
    sent = body[0].upper() + body[1:] if body else ""
    return f"👉 {sent}."


def build_deterministic_artifact_interpretation(
    item: DecisionBundleItem,
    primary: list[WorkItem],
    labels: list[str],
    *,
    evidence: EvidenceBundle | None = None,
) -> dict[str, str]:
    """Three strings: action headline, factual context, expanded instruction."""
    d = item.decision
    fm = _failure_mode(item)
    if not primary or not labels:
        return {
            "llm_headline": "Link this gap to a tracked issue or thread",
            "llm_explanation": (
                "Evidence refs on this decision did not resolve to a concrete issue, "
                "PR, or thread id in the activity bundle."
            ),
            "llm_next_step": (
                "👉 Create or link an issue, PR, or Slack thread in tracking "
                "so the card names a real artifact."
            ),
        }

    names_agg: list[str] = []
    for w in primary:
        names_agg.extend(collect_actor_display_names(w))
    names_agg = _uniq_preserve(names_agg)

    head = pure_action_title_from_primary(
        primary,
        labels,
        decision_type=d.decision_type,
        failure_mode=fm,
    )

    expl = derive_context_from_real_signals(
        primary,
        labels,
        evidence=evidence,
        actor_display_names=names_agg,
    )
    next_line = build_instruction_next_step(primary, labels, decision_type=d.decision_type)

    words = head.split()
    if len(words) > 14:
        head = " ".join(words[:14]).rstrip(",;:") + "…"

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
    "build_instruction_next_step",
    "collect_actor_display_names",
    "contains_product_banned_phrasing",
    "derive_context_from_real_signals",
    "expand_evidence_refs_to_work_item_ids",
    "format_actor_names_for_context",
    "is_valid_action_title",
    "merge_required_inputs_artifact_targets",
    "pure_action_title_from_primary",
    "select_primary_work_items",
    "score_work_item_for_decision",
]
