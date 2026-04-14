"""Ordered missing onboarding requirements from ``answers_json`` (code-owned)."""

from __future__ import annotations

from typing import Any

from vector.domains.manager_onboarding.constants import SCOPE_OTHER_MANAGERS

REQ_SCOPE_INTENT = "scope_intent"
REQ_PEER_HANDLES = "peer_slack_user_ids"
REQ_TEAM_SCOPE = "team_scope"
REQ_TEAM_MEMBERS = "team_member_slack_ids"
REQ_CHANNELS = "channels"
REQ_REPORTS_TO = "reports_to_yes"
REQ_REPORTS_WHO = "reports_to_slack_ids"
REQ_KPIS = "kpi_expectations"

_ORDER: tuple[str, ...] = (
    REQ_SCOPE_INTENT,
    REQ_PEER_HANDLES,
    REQ_TEAM_SCOPE,
    REQ_TEAM_MEMBERS,
    REQ_CHANNELS,
    REQ_REPORTS_TO,
    REQ_REPORTS_WHO,
    REQ_KPIS,
)

_PRIMARY_LABELS: dict[str, str] = {
    REQ_SCOPE_INTENT: "whether this setup is mostly for them or for other managers too",
    REQ_PEER_HANDLES: "which other managers to include (people in Slack)",
    REQ_TEAM_SCOPE: "what the team mostly works on (short, plain description)",
    REQ_TEAM_MEMBERS: "who they work with day to day on the team (people in Slack)",
    REQ_CHANNELS: "which Slack channels matter for team coordination (they can skip)",
    REQ_REPORTS_TO: "whether they have a manager they report to",
    REQ_REPORTS_WHO: "who they report to (people in Slack)",
    REQ_KPIS: "what signals or KPIs matter when reporting upward",
}


def missing_requirements(answers: dict[str, Any]) -> list[str]:
    """
    Requirements still unfilled, in product order, **starting from the first gap only**
    (same progression as ``first_unanswered_step`` in ``service``).
    """
    out: list[str] = []
    scope = answers.get("scope_intent")
    if not scope:
        return [REQ_SCOPE_INTENT]
    if scope == SCOPE_OTHER_MANAGERS:
        peers = answers.get("peer_slack_user_ids")
        if not isinstance(peers, list):
            return [REQ_PEER_HANDLES]
    if not (answers.get("team_scope") or "").strip():
        return [REQ_TEAM_SCOPE]
    mem = answers.get("team_member_slack_ids")
    if not isinstance(mem, list):
        return [REQ_TEAM_MEMBERS]
    if answers.get("observed_channels_skipped") is not True:
        ch = answers.get("observed_channel_ids")
        if not isinstance(ch, list):
            return [REQ_CHANNELS]
    if answers.get("reports_to_yes") is None:
        return [REQ_REPORTS_TO]
    if answers.get("reports_to_yes") is True:
        rpt = answers.get("reports_to_slack_ids")
        if not isinstance(rpt, list):
            return [REQ_REPORTS_WHO]
    if answers.get("reports_to_yes") is True:
        if not (answers.get("kpi_expectations") or "").strip():
            return [REQ_KPIS]
    return out


def primary_requirement(answers: dict[str, Any]) -> str | None:
    m = missing_requirements(answers)
    return m[0] if m else None


def primary_requirement_label(req_id: str) -> str:
    return _PRIMARY_LABELS.get(req_id, req_id)


def requirement_sort_key(req_id: str) -> int:
    try:
        return _ORDER.index(req_id)
    except ValueError:
        return len(_ORDER)
