"""Build reply-step conversation context from stored Slack transcript (chronological)."""

from __future__ import annotations

from typing import Any, Protocol


class _Msg(Protocol):
    direction: str
    text: str


_MAX_LINE = 1200
_DEFAULT_RECENT_MESSAGES = 5


def _clip(t: str) -> str:
    s = (t or "").strip().replace("\n", " ")
    if len(s) <= _MAX_LINE:
        return s
    return s[: _MAX_LINE - 3] + "..."


def _is_inbound(m: Any) -> bool:
    return (getattr(m, "direction", "") or "").strip().lower() == "inbound"


def _is_outbound(m: Any) -> bool:
    return (getattr(m, "direction", "") or "").strip().lower() == "outbound"


def format_recent_messages_transcript(
    rows_chrono: list[Any],
    *,
    current_user_text: str,
    max_messages: int = _DEFAULT_RECENT_MESSAGES,
) -> str:
    """
    Last ``max_messages`` DM rows (chronological), labeled User / Vector.

    ``rows_chrono`` should include the current inbound (just persisted). If empty, only the
    current user line is shown.
    """
    cu = _clip(current_user_text)
    if not rows_chrono:
        return f"Recent conversation:\nUser: {cu}\n"
    tail = rows_chrono[-max_messages:] if len(rows_chrono) >= max_messages else list(rows_chrono)
    lines: list[str] = []
    for m in tail:
        t = _clip(str(getattr(m, "text", "") or ""))
        if _is_inbound(m):
            lines.append(f"User: {t}")
        elif _is_outbound(m):
            lines.append(f"Vector: {t}")
    if not lines:
        return f"Recent conversation:\nUser: {cu}\n"
    return "Recent conversation:\n" + "\n".join(lines) + "\n"
