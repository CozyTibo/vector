"""War-room step 4 — deploy validation helpers (A4 canonical motion)."""

from __future__ import annotations

from typing import Any


def evaluate_a4_canonical_motion_v1(
    *,
    drain_summary: dict[str, Any] | None,
    lease_last_canonical_outcome: str | None,
    released_missing_parent_ref: int = 0,
    deferrals_before_total: int = 0,
    deferrals_after_total: int = 0,
) -> tuple[bool, str]:
    """Return (passed, detail) for alive criterion A4 after deploy/wedge drain."""
    succeeded = 0
    if isinstance(drain_summary, dict):
        succeeded = int(drain_summary.get("total_succeeded") or 0)
    if succeeded > 0:
        return True, f"total_succeeded={succeeded}"
    outcome = str((drain_summary or {}).get("canonical_outcome") or "")
    if outcome in ("partial_progress", "progressed"):
        return True, f"canonical_outcome={outcome}"
    if int(released_missing_parent_ref) > 0:
        return True, f"released_missing_parent_ref={released_missing_parent_ref}"
    before = int(deferrals_before_total)
    after = int(deferrals_after_total)
    if before > after > 0:
        return True, f"deferrals_dropped={before}->{after}"
    if str(lease_last_canonical_outcome or "") in ("partial_progress", "progressed"):
        return True, f"lease_outcome={lease_last_canonical_outcome}"
    lease_out = str(lease_last_canonical_outcome or "")
    return (
        False,
        f"no_motion:outcome={outcome or lease_out or 'unknown'}:total_succeeded={succeeded}",
    )
