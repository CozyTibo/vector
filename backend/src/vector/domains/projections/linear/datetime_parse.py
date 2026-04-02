"""Parse Linear GraphQL ISO-8601 timestamps."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any


def parse_linear_datetime(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    s = value.strip().replace("Z", "+00:00")
    try:
        dt = datetime.fromisoformat(s)
        if dt.tzinfo is None:
            return dt.replace(tzinfo=UTC)
        return dt
    except ValueError:
        return None
