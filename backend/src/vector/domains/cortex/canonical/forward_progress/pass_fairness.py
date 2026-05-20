"""Pass-local fairness state for canonical convergence (lease-persisted, bounded)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from vector.domains.cortex.canonical.forward_progress.pass_registry import (
    all_canonical_passes_fair_rotation,
    pass_key_label,
)


def _now() -> datetime:
    return datetime.now(UTC)


def parse_pass_cooldown_until(detail: dict[str, Any] | None) -> dict[str, datetime]:
    """Load pass_key → cooldown expiry from convergence lease detail_json."""
    raw = (detail or {}).get("pass_cooldown_until")
    if not isinstance(raw, dict):
        return {}
    out: dict[str, datetime] = {}
    for key, val in raw.items():
        if not isinstance(key, str) or not key.strip():
            continue
        if isinstance(val, datetime):
            out[key.strip()] = val if val.tzinfo else val.replace(tzinfo=UTC)
            continue
        if isinstance(val, str) and val.strip():
            try:
                parsed = datetime.fromisoformat(val.strip().replace("Z", "+00:00"))
                out[key.strip()] = parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)
            except ValueError:
                continue
    return out


def parse_pass_topology_stall_counts(detail: dict[str, Any] | None) -> dict[str, int]:
    raw = (detail or {}).get("pass_topology_stall_counts")
    if not isinstance(raw, dict):
        return {}
    out: dict[str, int] = {}
    for key, val in raw.items():
        if not isinstance(key, str) or not key.strip():
            continue
        try:
            out[key.strip()] = max(0, int(val))
        except (TypeError, ValueError):
            continue
    return out


def serialize_pass_cooldown_until(cooldowns: dict[str, datetime]) -> dict[str, str]:
    return {
        k: (v.astimezone(UTC).isoformat() if v.tzinfo else v.replace(tzinfo=UTC).isoformat())
        for k, v in sorted(cooldowns.items())
    }


def serialize_pass_topology_stall_counts(counts: dict[str, int]) -> dict[str, int]:
    return {k: int(v) for k, v in sorted(counts.items())}


def pass_is_on_cooldown(pass_key: str, *, pass_cooldowns: dict[str, datetime], now: datetime | None = None) -> bool:
    now = now or _now()
    until = pass_cooldowns.get(pass_key)
    return until is not None and until > now


def record_pass_topology_stall(
    *,
    pass_key: str,
    pass_cooldowns: dict[str, datetime],
    pass_stall_counts: dict[str, int],
    base_cooldown_seconds: int,
    max_cooldown_seconds: int,
    now: datetime | None = None,
) -> datetime:
    """Mark a pass locally cooled after a topology-only batch; return cooldown expiry."""
    now = now or _now()
    pk = pass_key.strip()
    stalls = int(pass_stall_counts.get(pk, 0)) + 1
    pass_stall_counts[pk] = stalls
    # Escalating cooldown per repeated stall on the same pass (bounded).
    mult = min(4, stalls)
    seconds = min(max_cooldown_seconds, max(5, int(base_cooldown_seconds)) * mult)
    until = now + timedelta(seconds=seconds)
    pass_cooldowns[pk] = until
    return until


def resolve_fair_pass_cursor(
    pass_index: int,
    *,
    pass_cooldowns: dict[str, datetime] | None = None,
    pass_stall_counts: dict[str, int] | None = None,
    now: datetime | None = None,
) -> tuple[str, str, str, int, bool]:
    """Return (connector, resource_type, pass_key, next_index, skipped_cooled_pass).

    Skips passes on cooldown; deprioritizes high stall-count passes when alternatives exist.
    """
    passes = all_canonical_passes_fair_rotation()
    if not passes:
        return "", "", "", 0, False
    now = now or _now()
    cooldowns = pass_cooldowns or {}
    stalls = pass_stall_counts or {}
    n = len(passes)
    start = int(pass_index) % n

    candidates: list[tuple[int, str, str, str, int]] = []
    for offset in range(n):
        idx = (start + offset) % n
        c, rt = passes[idx]
        pk = pass_key_label(c, rt)
        if pass_is_on_cooldown(pk, pass_cooldowns=cooldowns, now=now):
            continue
        candidates.append((idx, c, rt, pk, int(stalls.get(pk, 0))))

    skipped_cooled = len(candidates) < n and len(candidates) > 0

    if candidates:
        # Prefer productive passes: lowest topology stall count, then fair index order.
        candidates.sort(key=lambda t: (t[4], t[0]))
        idx, c, rt, pk, _ = candidates[0]
        return c, rt, pk, (idx + 1) % n, skipped_cooled

    # All passes on cooldown — fall back to cursor pass (batch may no-op quickly).
    idx = start
    c, rt = passes[idx]
    pk = pass_key_label(c, rt)
    return c, rt, pk, (idx + 1) % n, True


def count_passes_off_cooldown(*, pass_cooldowns: dict[str, datetime], now: datetime | None = None) -> int:
    now = now or _now()
    passes = all_canonical_passes_fair_rotation()
    return sum(
        1
        for c, rt in passes
        if not pass_is_on_cooldown(pass_key_label(c, rt), pass_cooldowns=pass_cooldowns, now=now)
    )
