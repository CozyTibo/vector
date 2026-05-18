"""Canonical retrieval materialization skip taxonomy (RET-SKIP-*)."""

from __future__ import annotations

from typing import Any, Final

RET_SKIP_TCRE_MISSING_V1: Final[str] = "RET-SKIP-TCRE-MISSING"
RET_SKIP_WALK_INCOMPLETE_V1: Final[str] = "RET-SKIP-WALK-INCOMPLETE"
RET_SKIP_ORG_LINK_MISSING_V1: Final[str] = "RET-SKIP-ORG-LINK-MISSING"
RET_SKIP_IDENTITY_UNRESOLVED_V1: Final[str] = "RET-SKIP-IDENTITY-UNRESOLVED"
RET_SKIP_GRAPH_DISCONNECTED_V1: Final[str] = "RET-SKIP-GRAPH-DISCONNECTED"
RET_SKIP_LEGALITY_FAILED_V1: Final[str] = "RET-SKIP-LEGALITY-FAILED"
RET_SKIP_TEMPORAL_INCONSISTENT_V1: Final[str] = "RET-SKIP-TEMPORAL-INCONSISTENT"
RET_SKIP_REPLAY_UNSAFE_V1: Final[str] = "RET-SKIP-REPLAY-UNSAFE"
RET_SKIP_NO_CANDIDATES_V1: Final[str] = "RET-SKIP-NO-CANDIDATES"

RET_SKIP_CODES_V1: Final[frozenset[str]] = frozenset(
    {
        RET_SKIP_TCRE_MISSING_V1,
        RET_SKIP_WALK_INCOMPLETE_V1,
        RET_SKIP_ORG_LINK_MISSING_V1,
        RET_SKIP_IDENTITY_UNRESOLVED_V1,
        RET_SKIP_GRAPH_DISCONNECTED_V1,
        RET_SKIP_LEGALITY_FAILED_V1,
        RET_SKIP_TEMPORAL_INCONSISTENT_V1,
        RET_SKIP_REPLAY_UNSAFE_V1,
        RET_SKIP_NO_CANDIDATES_V1,
    }
)

_SOURCE_TO_SKIP_V1: Final[dict[tuple[str, str], str]] = {
    ("tcre_job", "tcre_job_not_found"): RET_SKIP_TCRE_MISSING_V1,
    ("tcre_job", "tcre_artifact_missing"): RET_SKIP_TCRE_MISSING_V1,
    ("walk", "walk_incomplete"): RET_SKIP_WALK_INCOMPLETE_V1,
    ("walk", "walk_payload_empty"): RET_SKIP_WALK_INCOMPLETE_V1,
    ("org_link", "org_link_not_found"): RET_SKIP_ORG_LINK_MISSING_V1,
    ("org_link", "graph_ref_unresolved"): RET_SKIP_GRAPH_DISCONNECTED_V1,
    ("identity", "identity_unresolved"): RET_SKIP_IDENTITY_UNRESOLVED_V1,
}


def normalize_retrieval_skip_reason_v1(
    *,
    source: str,
    code: str,
    detail: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Map binding/legality codes to canonical RET-SKIP taxonomy."""
    src = str(source or "unknown").strip()
    raw_code = str(code or "unknown").strip()
    canonical = _SOURCE_TO_SKIP_V1.get((src, raw_code))
    if canonical is None:
        lowered = raw_code.lower()
        if "legality" in lowered or raw_code.startswith("RETRIEVAL_RD_"):
            canonical = RET_SKIP_LEGALITY_FAILED_V1
        elif "replay" in lowered or "drift" in lowered:
            canonical = RET_SKIP_REPLAY_UNSAFE_V1
        elif "temporal" in lowered:
            canonical = RET_SKIP_TEMPORAL_INCONSISTENT_V1
        elif "identity" in lowered:
            canonical = RET_SKIP_IDENTITY_UNRESOLVED_V1
        elif "graph" in lowered or "disconnected" in lowered:
            canonical = RET_SKIP_GRAPH_DISCONNECTED_V1
        elif src == "tcre_job":
            canonical = RET_SKIP_TCRE_MISSING_V1
        elif src == "walk":
            canonical = RET_SKIP_WALK_INCOMPLETE_V1
        elif src == "org_link":
            canonical = RET_SKIP_ORG_LINK_MISSING_V1
        else:
            canonical = RET_SKIP_LEGALITY_FAILED_V1
    row: dict[str, Any] = {
        "source": src,
        "upstream_code": raw_code,
        "ret_skip_code": canonical,
        "replay_safe": True,
    }
    if detail:
        row["detail"] = dict(detail)
    return row


def normalize_skip_reasons_from_stats_v1(
    skip_reasons: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for item in skip_reasons:
        if not isinstance(item, dict):
            continue
        out.append(
            normalize_retrieval_skip_reason_v1(
                source=str(item.get("source") or "unknown"),
                code=str(item.get("code") or "unknown"),
                detail={
                    k: v
                    for k, v in item.items()
                    if k not in ("source", "code")
                }
                or None,
            )
        )
    return out
