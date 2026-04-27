"""Step 5.5 — Deterministic key achievements (closed issues + merged PRs only, no LLM)."""

from __future__ import annotations

import hashlib
from datetime import datetime

from vector.contracts.manager_insights_activity import (
    KeyAchievementItem,
    KeyAchievementsBundleDebug,
    LinkBundle,
    LinkConfidence,
    WorkItem,
    WorkItemBundle,
)

_DONE_ISSUE = {"closed", "done", "completed", "complete", "cancelled", "canceled", "resolved"}
_DONE_PR = {"merged", "closed", "closed_merged"}


def _is_closed_issue(w: WorkItem) -> bool:
    if w.type != "issue":
        return False
    if w.closed_at is not None:
        return True
    st = (w.status or "").strip().lower()
    return st in _DONE_ISSUE


def _is_merged_or_closed_pr(w: WorkItem) -> bool:
    if w.type != "pull_request":
        return False
    if w.closed_at is not None:
        return True
    st = (w.status or "").strip().lower()
    return st in _DONE_PR or "merge" in st


def _sort_ts(w: WorkItem) -> datetime:
    if w.closed_at is not None:
        return w.closed_at
    if w.updated_at is not None:
        return w.updated_at
    if w.created_at is not None:
        return w.created_at
    return datetime.min


def _ka_id(w: WorkItem) -> str:
    d = hashlib.sha1(f"ka|{w.id}".encode("utf-8")).hexdigest()[:12]
    return f"ka:{d}"


def _evidence_for(
    w: WorkItem, links: LinkBundle, by_id: dict[str, WorkItem]
) -> list[str]:
    out: list[str] = [f"work_item:{w.id}"]
    if w.url:
        out.append(f"url:{w.url}")
    for e in links.links:
        if e.confidence not in ("high", "medium"):
            continue
        other: str | None = None
        if e.from_work_item_id == w.id:
            other = e.to_work_item_id
        elif e.to_work_item_id == w.id:
            other = e.from_work_item_id
        if not other or other not in by_id:
            continue
        o = by_id[other]
        if o.type in ("document", "call", "message_thread"):
            out.append(
                f"reinforced_by_link:{e.id}({e.from_work_item_id}->{e.to_work_item_id},"
                f"confidence={e.confidence},type={e.link_type})"
            )
    # de-dupe preserve order
    seen: set[str] = set()
    uniq: list[str] = []
    for x in out:
        if x not in seen:
            seen.add(x)
            uniq.append(x)
    return uniq if len(uniq) >= 1 else [f"work_item:{w.id}"]


def build_key_achievements(
    work_items: WorkItemBundle,
    links: LinkBundle,
) -> KeyAchievementsBundleDebug:
    """List closed issues and merged/closed PRs; optional doc/call reinforcement via medium+ links."""
    by_id = {w.id: w for w in work_items.items}
    candidates: list[WorkItem] = []
    for w in work_items.items:
        if _is_closed_issue(w) or _is_merged_or_closed_pr(w):
            candidates.append(w)

    candidates.sort(key=_sort_ts, reverse=True)

    items: list[KeyAchievementItem] = []
    for w in candidates:
        items.append(
            KeyAchievementItem(
                id=_ka_id(w),
                title=w.title.strip() or w.id,
                linked_items=[w.id],
                evidence=_evidence_for(w, links, by_id),
                sort_at=_sort_ts(w) if _sort_ts(w) != datetime.min else None,
            )
        )

    return KeyAchievementsBundleDebug(
        run_id=work_items.run_id,
        tenant_id=work_items.tenant_id,
        window_days=work_items.window_days,
        items=items,
    )
