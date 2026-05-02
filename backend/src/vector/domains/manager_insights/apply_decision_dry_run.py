"""§6 Step 37 — plan-only apply (no external connector I/O)."""

from __future__ import annotations

from typing import Any

from vector.contracts.manager_insights_activity import DecisionDefaultAction
from vector.infrastructure.db.models.manager_insight_decision import ManagerInsightDecision


def plan_manager_insight_apply_dry_run(
    row: ManagerInsightDecision,
) -> tuple[DecisionDefaultAction, dict[str, Any]]:
    """Validate ``default_action`` and build the JSON that a future apply layer would use.

    Returns ``(validated_default_action, planned_payload)``. No Slack/HTTP/connector calls.
    """
    default_action = DecisionDefaultAction.model_validate(row.default_action)
    required = dict(row.required_inputs or {})
    template = dict(default_action.payload_template)
    merged: dict[str, Any] = {**template, **required}
    planned_payload: dict[str, Any] = {
        "action_kind": default_action.kind,
        "connector": default_action.connector,
        "payload_template": template,
        "required_inputs": required,
        "merged_arguments": merged,
        "external_io": False,
    }
    return default_action, planned_payload


__all__ = ["plan_manager_insight_apply_dry_run"]
