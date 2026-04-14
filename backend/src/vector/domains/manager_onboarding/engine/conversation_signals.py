"""Signals for the conversational layer (reply context, soft identity) without changing merge rules."""

from __future__ import annotations

import re
from typing import Any

from vector.domains.manager_onboarding.engine.requirements import (
    REQ_PEER_HANDLES,
    REQ_REPORTS_WHO,
    REQ_TEAM_MEMBERS,
)

_SLACK_UID = re.compile(r"^[UW][A-Z0-9]{8,}$")
_SUBTEAM_IN_STRING = re.compile(r"subteam\^", re.I)


def raw_patch_had_substance(raw_patch: dict[str, Any] | None) -> bool:
    """True if interpret + deterministic merge produced any non-empty structured content."""
    if not raw_patch:
        return False
    for _k, v in raw_patch.items():
        if v is None:
            continue
        if isinstance(v, bool):
            return True
        if isinstance(v, str) and v.strip():
            return True
        if isinstance(v, list) and len(v) > 0:
            return True
    return False


def _entry_is_name_like(s: str) -> bool:
    t = (s or "").strip()
    if not t:
        return False
    if _SUBTEAM_IN_STRING.search(t):
        return False
    if t.lower() in ("self", "me", "i", "myself"):
        return False
    if _SLACK_UID.fullmatch(t.upper()):
        return False
    return True


_PRIMARY_TO_LIST_KEY: dict[str, str] = {
    REQ_PEER_HANDLES: "peer_slack_user_ids",
    REQ_TEAM_MEMBERS: "team_member_slack_ids",
    REQ_REPORTS_WHO: "reports_to_slack_ids",
}


def extract_name_like_people_for_primary(
    raw_patch: dict[str, Any] | None,
    primary_req_id: str | None,
) -> list[str]:
    """Strings in the patch for the current people step that look like names, not Slack IDs."""
    if not raw_patch or not primary_req_id:
        return []
    lk = _PRIMARY_TO_LIST_KEY.get(primary_req_id)
    if not lk:
        return []
    raw = raw_patch.get(lk)
    if not isinstance(raw, list):
        return []
    out: list[str] = []
    seen: set[str] = set()
    for e in raw:
        if not isinstance(e, str):
            continue
        if not _entry_is_name_like(e):
            continue
        k = e.strip()
        if k and k.lower() not in seen:
            seen.add(k.lower())
            out.append(k[:200])
    return out


def should_suppress_entity_block(
    *,
    merged_something: bool,
    entity_unresolved: bool,
    soft_names: list[str],
) -> bool:
    """When the user clearly named people but IDs did not validate, avoid hard 'blocked' UX."""
    if merged_something:
        return False
    if not entity_unresolved:
        return False
    return len(soft_names) > 0
