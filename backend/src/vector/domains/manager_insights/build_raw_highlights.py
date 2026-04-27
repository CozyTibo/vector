"""Step 5.6 — Deterministic raw highlights (facts only, no LLM)."""

from __future__ import annotations

import hashlib
import re
from collections import defaultdict

from vector.contracts.manager_insights_activity import (
    EvidenceBundle,
    GapBundle,
    GapItem,
    GapType,
    LinkBundle,
    RawHighlightItem,
    RawHighlightsBundleDebug,
    WorkItem,
    WorkItemBundle,
)

_BANNED = (
    "seems",
    "likely",
    "concern",
    "probably",
    "maybe",
    "perhaps",
    "i think",
    "we think",
    "suggests",
    "indicates",
    "implication",
    "worry",
)
_DISCUSSION_SOURCES = {"calls", "slack"}
_TOKEN_RE = re.compile(r"[a-z0-9]{4,}", re.IGNORECASE)
_MIN_REPEAT = 2
_TOP_TOKENS = 15
_TOP_PRS = 12


def _hl_id(*parts: str) -> str:
    raw = "|".join(parts)
    d = hashlib.sha1(raw.encode("utf-8")).hexdigest()[:12]
    return f"rh:{d}"


def _sanitize_text(text: str) -> str:
    lower = text.lower()
    t = text
    for w in _BANNED:
        if w in lower:
            t = t.replace(w, "…")
    return t.strip()


def _tokens(title: str, summary: str | None) -> set[str]:
    blob = f"{title} {summary or ''}"
    return set(m.group(0).lower() for m in _TOKEN_RE.finditer(blob))


def _repeated_mention_highlights(
    work_items: WorkItemBundle,
) -> list[RawHighlightItem]:
    by_token: dict[str, set[str]] = defaultdict(set)
    for w in work_items.items:
        if w.source not in _DISCUSSION_SOURCES:
            continue
        if w.type not in ("call", "message_thread"):
            continue
        for tok in _tokens(w.title, w.summary):
            by_token[tok].add(w.id)
    rows: list[RawHighlightItem] = []
    scored = sorted(
        ((len(ids), tok, sorted(ids)) for tok, ids in by_token.items() if len(ids) >= _MIN_REPEAT),
        reverse=True,
    )[:_TOP_TOKENS]
    for _n, tok, ids in scored:
        text = _sanitize_text(
            f'Term "{tok}" appears in {len(ids)} distinct calls/Slack work items.'
        )
        rows.append(
            RawHighlightItem(
                id=_hl_id("repeat", tok, ",".join(ids)),
                text=text,
                sources=ids,
            )
        )
    return rows


def _notable_merged_prs(work_items: WorkItemBundle) -> list[RawHighlightItem]:
    prs = [
        w
        for w in work_items.items
        if w.type == "pull_request" and w.closed_at is not None
    ]
    prs.sort(
        key=lambda x: (x.closed_at or x.updated_at or x.created_at),  # type: ignore[return-value]
        reverse=True,
    )
    out: list[RawHighlightItem] = []
    for w in prs[:_TOP_PRS]:
        pl = f"status={w.status or 'unknown'}"
        text = _sanitize_text(f"Merged or closed pull request: {w.title} ({pl}).")
        out.append(
            RawHighlightItem(
                id=_hl_id("pr", w.id),
                text=text,
                sources=[w.id],
            )
        )
    return out


def _gap_highlights(gaps: GapBundle) -> list[RawHighlightItem]:
    out: list[RawHighlightItem] = []
    by_type: dict[GapType, list[GapItem]] = defaultdict(list)
    for g in gaps.gaps:
        by_type[g.type].append(g)
    for gtype, items in by_type.items():
        for g in items:
            srcs: list[str] = []
            for k, v in g.evidence_pointers.items():
                if isinstance(v, list):
                    srcs.extend(v)
            srcs = sorted(set(srcs)) or [g.id]
            text = _sanitize_text(
                f"Gap recorded ({gtype.replace('_', ' ')}): {g.description}"
            )
            out.append(
                RawHighlightItem(
                    id=_hl_id("gap", g.id),
                    text=text,
                    sources=srcs if srcs else [g.id],
                )
            )
    return out


def build_raw_highlights(
    work_items: WorkItemBundle,
    _evidence: EvidenceBundle,
    _links: LinkBundle,
    gaps: GapBundle,
) -> RawHighlightsBundleDebug:
    """Factual rows: repeated call/slack terms, closed PRs, and gap pointers."""
    items: list[RawHighlightItem] = []
    items.extend(_repeated_mention_highlights(work_items))
    items.extend(_notable_merged_prs(work_items))
    items.extend(_gap_highlights(gaps))
    # deterministic order
    items.sort(key=lambda x: (x.text, x.id))
    return RawHighlightsBundleDebug(
        run_id=work_items.run_id,
        tenant_id=work_items.tenant_id,
        window_days=work_items.window_days,
        items=items,
    )
