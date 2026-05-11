"""Temporal continuity hardening helpers (Phase 3.5) — deterministic ordering without invented time."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Final

from vector.domains.cortex.canonical.temporal_runtime import build_temporal_ordering_key

TEMPORAL_CONTINUITY_HELPER_VERSION: Final[int] = 1


def normalize_provider_timestamp(value: str | None) -> tuple[datetime | None, str]:
    """Parse ISO-8601 timestamps from provider strings; return (utc_dt_or_none, parse_status).

    Status is one of: ok, unknown, invalid.
    """
    if not isinstance(value, str) or len(value) < 4:
        return None, "unknown"
    s = value.replace("Z", "+00:00")
    try:
        dt = datetime.fromisoformat(s)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=UTC)
        return dt.astimezone(UTC), "ok"
    except ValueError:
        return None, "invalid"


def partial_order_tuple(
    *,
    occurred_at: datetime | None,
    observed_at: datetime | None,
    replay_sequence: int,
    source_revision_key: str,
    raw_record_id: int,
) -> tuple[str, str, str, str, str]:
    """Explicit partial order dimensions (no total order claim across concurrent provider events).

    Returns a tuple comparable lexicographically when ``occurred_at`` is known; when unknown, callers
    should use ``materialization_ordering_fallback`` for replay-safe tie-break.
    """
    occ_s = occurred_at.astimezone(UTC).isoformat() if occurred_at is not None else ""
    obs_s = observed_at.astimezone(UTC).isoformat() if observed_at is not None else ""
    seq = f"{int(replay_sequence):016d}"
    rev = source_revision_key or ""
    rid = f"{int(raw_record_id):012d}"
    return (occ_s, obs_s, seq, rev, rid)


def materialization_ordering_fallback(
    *,
    occurred_at: datetime,
    replay_sequence: int,
    source_revision_key: str,
    raw_record_id: int,
) -> str:
    """Delegate to Phase 03 temporal ordering key for materialization-stable total order within bundle."""
    return build_temporal_ordering_key(
        occurred_at=occurred_at,
        replay_sequence=replay_sequence,
        source_revision_key=source_revision_key,
        raw_record_id=raw_record_id,
    )
