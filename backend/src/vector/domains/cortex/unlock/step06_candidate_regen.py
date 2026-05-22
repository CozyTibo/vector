"""War-room step 6 — candidate link regeneration (alive criterion A3)."""

from __future__ import annotations

from typing import Any

A3_WEDGE_MIN_CANDIDATES = 50
A3_CAP_CANDIDATES = 2_000


def evaluate_a3_candidate_links_v1(
    *,
    candidate_count: int,
    candidates_persisted: int | None = None,
) -> tuple[bool, str]:
    """Return (passed, detail) for alive criterion A3 after anchor continuity regen."""
    total = int(candidate_count)
    persisted = int(candidates_persisted) if candidates_persisted is not None else total
    if total >= A3_CAP_CANDIDATES:
        return True, f"link_candidates={total} at_cap>={A3_CAP_CANDIDATES}"
    if total >= A3_WEDGE_MIN_CANDIDATES:
        return True, f"link_candidates={total}>={A3_WEDGE_MIN_CANDIDATES}"
    if persisted > 0:
        return True, f"candidates_persisted={persisted}:link_candidates={total}"
    return False, f"link_candidates={total} below wedge minimum {A3_WEDGE_MIN_CANDIDATES}"
