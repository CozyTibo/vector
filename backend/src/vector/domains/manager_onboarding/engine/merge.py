"""Merge validated patch fields into ``answers_json`` (only entry point for state writes from patches)."""

from __future__ import annotations

import copy
from typing import Any

from vector.domains.manager_onboarding.constants import SCOPE_JUST_ME, SCOPE_OTHER_MANAGERS

_PATCH_KEYS = frozenset(
    {
        "scope_intent",
        "peer_slack_user_ids",
        "team_scope",
        "team_member_slack_ids",
        "observed_channel_ids",
        "observed_channels_skipped",
        "reports_to_yes",
        "reports_to_slack_ids",
        "kpi_expectations",
    }
)


def merge_validated_patch(base: dict[str, Any], validated: dict[str, Any]) -> dict[str, Any]:
    """
    Apply only keys present in ``validated`` (already validated). Preserves unrelated keys.

    Invariant: ``answers_json`` is only modified through this merge after validation — never assign
    raw LLM output directly to session state.
    """
    out = copy.deepcopy(base)
    for k, v in validated.items():
        if k not in _PATCH_KEYS:
            continue
        out[k] = copy.deepcopy(v)

    if validated.get("scope_intent") == SCOPE_JUST_ME:
        out["peer_slack_user_ids"] = []

    if validated.get("reports_to_yes") is False:
        out["reports_to_slack_ids"] = []
        out.setdefault("kpi_expectations", "")

    if validated.get("observed_channels_skipped") is True:
        out["observed_channel_ids"] = []
        out["_pending_channel_ids"] = []

    return out


def answers_diff(before: dict[str, Any], after: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Shallow-ish diff for observability (patch-shaped keys only)."""
    keys = set(before) | set(after)
    diff: dict[str, dict[str, Any]] = {}
    for k in sorted(keys):
        if k not in _PATCH_KEYS and not k.startswith("_"):
            continue
        b, a = before.get(k), after.get(k)
        if b != a:
            diff[k] = {"before": b, "after": a}
    return diff
