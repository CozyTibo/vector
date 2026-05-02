"""§6 Step 38 — live apply for persisted coordination decisions (gated + receipt)."""

from __future__ import annotations

import logging
import uuid
from typing import Any

import httpx
from sqlalchemy.orm import Session

from vector.domains.manager_insights.apply_decision_dry_run import (
    plan_manager_insight_apply_dry_run,
)
from vector.infrastructure.db.models.manager_insight_decision import ManagerInsightDecision
from vector.infrastructure.db.repositories.slack_connection import get_slack_connection_for_tenant

log = logging.getLogger("app")


class LiveApplyUnsupportedError(Exception):
    """Raised when ``default_action`` has no live handler (§6 Step 38)."""

    def __init__(self, *, kind: str, connector: str | None) -> None:
        self.kind = kind
        self.connector = connector
        super().__init__(f"unsupported live apply: kind={kind!r} connector={connector!r}")


def slack_chat_post_message(*, bot_token: str, channel: str, text: str) -> dict[str, Any]:
    """Call Slack ``chat.postMessage`` (integration tests patch this)."""
    headers = {
        "Authorization": f"Bearer {bot_token}",
        "Content-Type": "application/json; charset=utf-8",
    }
    with httpx.Client(timeout=30.0) as client:
        r = client.post(
            "https://slack.com/api/chat.postMessage",
            headers=headers,
            json={"channel": channel.strip(), "text": text},
        )
        r.raise_for_status()
        return r.json()


def execute_manager_insight_live_apply(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    row: ManagerInsightDecision,
) -> tuple[dict[str, Any], str, dict[str, Any], dict[str, Any]]:
    """Live apply: mutates ``row`` receipt/status and flushes the session.

    Returns ``(receipt, decision_status, default_action_json, planned_payload)``.
    """
    default_action, planned_payload = plan_manager_insight_apply_dry_run(row)
    da_dump = default_action.model_dump(mode="json")
    kind = default_action.kind
    connector = default_action.connector

    if kind == "noop":
        receipt: dict[str, Any] = {
            "ok": True,
            "connector": None,
            "kind": "noop",
            "note": "§6 Step 38 — noop apply (no external I/O).",
        }
        row.receipt = receipt
        row.status = "completed"
        session.flush()
        return receipt, "completed", da_dump, planned_payload

    if kind == "post_message" and connector == "slack":
        req_in = dict(row.required_inputs or {})
        merged: dict[str, Any] = {**default_action.payload_template, **req_in}
        channel = merged.get("channel")
        text = merged.get("text")
        if not isinstance(channel, str) or not channel.strip():
            receipt = {"ok": False, "connector": "slack", "error": "missing_or_invalid_channel"}
            row.receipt = receipt
            row.status = "failed"
            session.flush()
            return receipt, "failed", da_dump, planned_payload
        if not isinstance(text, str) or not text.strip():
            receipt = {"ok": False, "connector": "slack", "error": "missing_or_invalid_text"}
            row.receipt = receipt
            row.status = "failed"
            session.flush()
            return receipt, "failed", da_dump, planned_payload

        link = get_slack_connection_for_tenant(session, tenant_id)
        if link is None:
            receipt = {"ok": False, "connector": "slack", "error": "slack_not_connected"}
            row.receipt = receipt
            row.status = "failed"
            session.flush()
            return receipt, "failed", da_dump, planned_payload

        try:
            api_json = slack_chat_post_message(
                bot_token=link.detail.bot_access_token,
                channel=channel.strip(),
                text=text,
            )
        except (httpx.HTTPError, OSError, RuntimeError) as exc:
            log.warning("slack live apply http error: %s", exc)
            receipt = {"ok": False, "connector": "slack", "error": "http_error", "detail": str(exc)}
            row.receipt = receipt
            row.status = "failed"
            session.flush()
            return receipt, "failed", da_dump, planned_payload

        if api_json.get("ok"):
            ts = api_json.get("ts")
            ch = api_json.get("channel")
            receipt = {
                "ok": True,
                "connector": "slack",
                "method": "chat.postMessage",
                "message_ts": ts,
                "channel": ch,
                "slack_response": api_json,
            }
            row.slack_message_ts = ts if isinstance(ts, str) else row.slack_message_ts
            row.slack_channel_id = ch if isinstance(ch, str) else row.slack_channel_id
            row.receipt = receipt
            row.status = "completed"
            session.flush()
            return receipt, "completed", da_dump, planned_payload

        err = api_json.get("error", "unknown")
        receipt = {
            "ok": False,
            "connector": "slack",
            "method": "chat.postMessage",
            "slack_error": err,
            "slack_response": api_json,
        }
        row.receipt = receipt
        row.status = "failed"
        session.flush()
        return receipt, "failed", da_dump, planned_payload

    raise LiveApplyUnsupportedError(kind=kind, connector=connector)


__all__ = [
    "LiveApplyUnsupportedError",
    "execute_manager_insight_live_apply",
    "slack_chat_post_message",
]
