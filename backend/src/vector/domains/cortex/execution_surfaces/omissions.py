"""Deterministic omission / coverage explanations for Execution Surfaces."""

from __future__ import annotations

from typing import Any

OBSERVATION_ACTIVITY_FOOTNOTE = (
    "Counts reflect Cortex observation signals (materialization and membership), "
    "not operational execution timelines. Operational event canonization is not yet complete."
)

EXECUTION_ACTIVITY_UNAVAILABLE_FOOTNOTE = (
    "Execution activity timeline is not available. Cortex does not yet canonize operational "
    "events (for example PR merged, issue assigned). Only relationship and membership "
    "observations are shown when present."
)

CHAIN_RELATIONSHIP_KINDS: frozenset[str] = frozenset(
    {
        "references",
        "comments_on",
        "relates_to",
        "blocks",
        "duplicates",
        "parent_of",
        "merged_as_commit",
        "deploys",
        "contains_commit",
        "attached_to",
    },
)


def section(
    *,
    count: int,
    empty_code: str,
    empty_message: str,
    empty_remediation: str | None = None,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "count": count,
        "items": [],
        "omission": None,
    }
    if extra:
        payload.update(extra)
    if count == 0:
        payload["omission"] = {
            "code": empty_code,
            "message": empty_message,
            "remediation": empty_remediation,
        }
    return payload


def with_items(section_payload: dict[str, Any], items: list[dict[str, Any]]) -> dict[str, Any]:
    out = dict(section_payload)
    out["count"] = len(items)
    out["items"] = items
    if len(items) == 0 and out.get("omission") is None:
        out["omission"] = {
            "code": "empty",
            "message": "No items in this section.",
            "remediation": None,
        }
    elif len(items) > 0:
        out["omission"] = None
    return out
