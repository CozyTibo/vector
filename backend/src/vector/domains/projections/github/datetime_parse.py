"""Parse GitHub API timestamp strings."""

from __future__ import annotations

from datetime import UTC, datetime


def parse_github_datetime(value: object) -> datetime | None:
    if value is None:
        return None
    if not isinstance(value, str):
        return None
    s = value.strip()
    if not s:
        return None
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    dt = datetime.fromisoformat(s)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt
