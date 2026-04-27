"""Step 3 — Evidence extraction with strict quote verification."""

from __future__ import annotations

import hashlib
import re

from vector.contracts.manager_insights_activity import (
    EvidenceBundle,
    EvidenceItem,
    EvidenceKind,
    WorkItem,
    WorkItemBundle,
)

_ACTION_PATTERNS = (
    re.compile(r"\b(todo|action item|next step|follow up|need to|must|should)\b", re.I),
    re.compile(r"\b(fix|implement|ship|prepare|send|update|review)\b", re.I),
)
_BLOCKER_PATTERNS = (
    re.compile(r"\b(blocked|blocking|stuck|cannot|can't|waiting on|dependency|degraded)\b", re.I),
)
_DECISION_PATTERNS = (
    re.compile(r"\b(decided|decision|agreed|we will|chosen|selected)\b", re.I),
)


def _norm(s: str) -> str:
    return " ".join(s.split()).strip().lower()


def _contains_quote(quote: str, source: str) -> bool:
    q = _norm(quote)
    s = _norm(source)
    return bool(q and s and q in s)


def _sentences(item: WorkItem) -> list[str]:
    parts: list[str] = [item.title]
    if item.summary:
        parts.append(item.summary)
    source = "\n".join(p for p in parts if p and p.strip())
    if not source:
        return []
    out: list[str] = []
    for piece in re.split(r"[.\n;]+", source):
        s = piece.strip()
        if len(s) >= 8:
            out.append(s)
    return out


def _classify(sentence: str) -> EvidenceKind | None:
    if any(p.search(sentence) for p in _DECISION_PATTERNS):
        return "decision"
    if any(p.search(sentence) for p in _BLOCKER_PATTERNS):
        return "blocker"
    if any(p.search(sentence) for p in _ACTION_PATTERNS):
        return "action_item"
    return None


def _item_id(kind: EvidenceKind, work_item_id: str, evidence: str) -> str:
    digest = hashlib.sha1(f"{kind}|{work_item_id}|{_norm(evidence)}".encode("utf-8")).hexdigest()[:12]
    return f"{kind}:{digest}"


def extract_evidence(bundle: WorkItemBundle) -> EvidenceBundle:
    """Extract action_items/blockers/decisions with exact evidence quotes."""
    action_items: list[EvidenceItem] = []
    blockers: list[EvidenceItem] = []
    decisions: list[EvidenceItem] = []
    discarded = 0
    seen: set[tuple[str, str, str]] = set()

    for wi in bundle.items:
        source_text = "\n".join([wi.title, wi.summary or ""])
        for sentence in _sentences(wi):
            kind = _classify(sentence)
            if kind is None:
                continue
            if not _contains_quote(sentence, source_text):
                discarded += 1
                continue
            dedup = (kind, wi.id, _norm(sentence))
            if dedup in seen:
                continue
            seen.add(dedup)
            rec = EvidenceItem(
                id=_item_id(kind, wi.id, sentence),
                kind=kind,
                statement=sentence,
                evidence=sentence,
                source_work_item_id=wi.id,
                source_connector=wi.source,
                source_type=wi.type,
                source_ref=wi.source_ref,
                linked_work_items=[],
            )
            if kind == "action_item":
                action_items.append(rec)
            elif kind == "blocker":
                blockers.append(rec)
            else:
                decisions.append(rec)

    action_items.sort(key=lambda x: x.id)
    blockers.sort(key=lambda x: x.id)
    decisions.sort(key=lambda x: x.id)
    return EvidenceBundle(
        run_id=bundle.run_id,
        tenant_id=bundle.tenant_id,
        window_days=bundle.window_days,
        action_items=action_items,
        blockers=blockers,
        decisions=decisions,
        discarded_without_evidence=discarded,
    )
