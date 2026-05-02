"""§6 Step 8 — validate perception rows (quote grounding, schema, dedupe)."""

from __future__ import annotations

import unicodedata
from collections.abc import Mapping, Sequence
from typing import Any

from pydantic import ValidationError

from vector.contracts.manager_insights_activity import (
    PerceptionRow,
    PerceptionValidationDemoDebug,
    RejectedPerceptionRowDebug,
    WorkItem,
)


def _normalize_for_substring(s: str) -> str:
    """Unicode-normalize and collapse whitespace for grounded substring checks."""
    s = unicodedata.normalize("NFKC", s)
    return " ".join(s.casefold().split())


def _quote_grounded(fragment: str, parent: str) -> bool:
    frag = fragment.strip()
    if not frag:
        return False
    return _normalize_for_substring(frag) in _normalize_for_substring(parent)


def parent_text_for_grounding(work_item: WorkItem) -> str:
    """Text slices perception quotes must appear in (title + summary)."""
    parts = [work_item.title or "", work_item.summary or ""]
    return " ".join(p.strip() for p in parts if p and p.strip())


def validate_perception_rows(
    rows: Sequence[PerceptionRow | Mapping[str, Any]],
    *,
    work_items_by_id: Mapping[str, WorkItem],
) -> tuple[list[PerceptionRow], list[RejectedPerceptionRowDebug]]:
    """Drop / reject rows that fail schema, unknown work items, quote grounding, or dedupe."""
    accepted: list[PerceptionRow] = []
    rejected: list[RejectedPerceptionRowDebug] = []
    seen_keys: set[tuple[str, str, str]] = set()

    for index, raw in enumerate(rows):
        if isinstance(raw, PerceptionRow):
            row = raw
            raw_dict: dict[str, Any] = row.model_dump(mode="python")
        else:
            try:
                row = PerceptionRow.model_validate(raw)
            except ValidationError as exc:
                errs: list[dict[str, Any]] = []
                for err in exc.errors(include_url=False):
                    e = dict(err)
                    loc = e.get("loc")
                    if isinstance(loc, tuple):
                        e["loc"] = list(loc)
                    errs.append(e)
                rejected.append(
                    RejectedPerceptionRowDebug(
                        index=index,
                        reason="schema_invalid",
                        raw={"payload": dict(raw), "errors": errs},
                    )
                )
                continue
            raw_dict = row.model_dump(mode="python")

        work_item = work_items_by_id.get(row.work_item_id)
        if work_item is None:
            rejected.append(
                RejectedPerceptionRowDebug(
                    index=index,
                    reason="unknown_work_item",
                    raw=raw_dict,
                )
            )
            continue

        parent = parent_text_for_grounding(work_item)
        if not parent.strip():
            rejected.append(
                RejectedPerceptionRowDebug(
                    index=index,
                    reason="empty_parent_text",
                    raw=raw_dict,
                )
            )
            continue

        if not _quote_grounded(row.quote, parent):
            rejected.append(
                RejectedPerceptionRowDebug(
                    index=index,
                    reason="quote_not_grounded",
                    raw=raw_dict,
                )
            )
            continue

        if row.state_transition is not None and not _quote_grounded(row.state_transition.quote, parent):
            rejected.append(
                RejectedPerceptionRowDebug(
                    index=index,
                    reason="state_transition_quote_not_grounded",
                    raw=raw_dict,
                )
            )
            continue

        if row.ambiguity_quote is not None and row.ambiguity_quote.strip():
            if not _quote_grounded(row.ambiguity_quote, parent):
                rejected.append(
                    RejectedPerceptionRowDebug(
                        index=index,
                        reason="ambiguity_quote_not_grounded",
                        raw=raw_dict,
                    )
                )
                continue

        if row.ownership_inferred is not None and not _quote_grounded(
            row.ownership_inferred.text_span,
            parent,
        ):
            rejected.append(
                RejectedPerceptionRowDebug(
                    index=index,
                    reason="ownership_span_not_grounded",
                    raw=raw_dict,
                )
            )
            continue

        failed_dependency = False
        for mention in row.waits_on:
            if mention.strip() and not _quote_grounded(mention, parent):
                rejected.append(
                    RejectedPerceptionRowDebug(
                        index=index,
                        reason="waits_on_not_grounded",
                        raw={**raw_dict, "failed_waits_on": mention},
                    )
                )
                failed_dependency = True
                break
        if failed_dependency:
            continue

        for mention in row.blocked_by:
            if mention.strip() and not _quote_grounded(mention, parent):
                rejected.append(
                    RejectedPerceptionRowDebug(
                        index=index,
                        reason="blocked_by_not_grounded",
                        raw={**raw_dict, "failed_blocked_by": mention},
                    )
                )
                failed_dependency = True
                break
        if failed_dependency:
            continue

        dedupe_key = (row.work_item_id, row.kind, row.quote)
        if dedupe_key in seen_keys:
            rejected.append(
                RejectedPerceptionRowDebug(
                    index=index,
                    reason="duplicate_row",
                    raw=raw_dict,
                )
            )
            continue
        seen_keys.add(dedupe_key)
        accepted.append(row)

    return accepted, rejected


_DEMO_WORK_ITEM_ID = "coordination:perception-validation:demo-wi"


def build_perception_validation_demo_debug() -> PerceptionValidationDemoDebug:
    """Deterministic fixture run for admin JSON + pytest parity."""
    parent_body = (
        "I'll ship this Friday. Actually next sprint is safer. "
        "Waiting on @legal for review. blocked on the auth service. "
        "Alice will drive the rollout. kicking off implementation today."
    )
    demo_wi = WorkItem(
        id=_DEMO_WORK_ITEM_ID,
        source="linear",
        type="issue",
        title="§6 Step 8 perception validation demo",
        summary=parent_body,
    )
    valid = PerceptionRow(
        id="demo-valid",
        work_item_id=_DEMO_WORK_ITEM_ID,
        kind="ambiguity",
        statement="Two conflicting ship dates.",
        quote="I'll ship this Friday.",
        execution_state="in_progress",
        state_transition=None,
        waits_on=["@legal"],
        blocked_by=["auth service"],
        commitment_strength="medium",
        ambiguity_class="contradiction",
        ambiguity_quote="Actually next sprint is safer.",
        contradiction_pair_id="demo-pair-1",
        ownership_inferred=None,
    )
    duplicate = PerceptionRow.model_validate(
        {**valid.model_dump(mode="python"), "id": "demo-dup"},
    )
    bad_quote = PerceptionRow(
        id="demo-bad-quote",
        work_item_id=_DEMO_WORK_ITEM_ID,
        kind="risk",
        statement="Not in text.",
        quote="ZZZ_NOT_IN_PARENT_ZZZ",
        execution_state=None,
    )
    unknown_wi = PerceptionRow(
        id="demo-unknown-wi",
        work_item_id="coordination:no-such-work-item",
        kind="blocker",
        statement="Orphan row.",
        quote="I'll ship this Friday.",
    )
    broken_schema: dict[str, Any] = {"id": "incomplete-row"}

    demo_rows: list[PerceptionRow | dict[str, Any]] = [
        valid,
        duplicate,
        bad_quote,
        unknown_wi,
        broken_schema,
    ]
    accepted, rejected = validate_perception_rows(
        demo_rows,
        work_items_by_id={_DEMO_WORK_ITEM_ID: demo_wi},
    )
    return PerceptionValidationDemoDebug(
        demo_work_item_id=_DEMO_WORK_ITEM_ID,
        input_row_count=len(demo_rows),
        accepted=accepted,
        rejected=rejected,
    )


__all__ = [
    "build_perception_validation_demo_debug",
    "parent_text_for_grounding",
    "validate_perception_rows",
]
