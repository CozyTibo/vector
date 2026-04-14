"""Slack Events API + Interactivity for Manager Slack onboarding."""

from __future__ import annotations

import json
import logging
from typing import Any
from urllib.parse import parse_qs

from fastapi import APIRouter, HTTPException, Request, status
from fastapi.responses import JSONResponse

from vector.domains.manager_onboarding.engine.tokens import augment_slack_message_text_with_block_users
from vector.domains.manager_onboarding.slack_signing import verify_slack_signature
from vector.settings import get_settings

logger = logging.getLogger("app")


def build_slack_manager_onboarding_router() -> APIRouter:
    """Mounted at app root: ``/slack/events``, ``/slack/interactive``."""
    r = APIRouter(tags=["slack-manager-onboarding"])

    @r.post("/slack/events")
    async def slack_events(request: Request) -> JSONResponse:
        settings = get_settings()
        secret = settings.slack_signing_secret.strip()
        if not secret:
            raise HTTPException(
                status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Slack signing secret not configured.",
            )
        raw = await request.body()
        ts = request.headers.get("X-Slack-Request-Timestamp", "")
        sig = request.headers.get("X-Slack-Signature", "")
        if not verify_slack_signature(
            signing_secret=secret,
            timestamp_header=ts,
            raw_body=raw,
            signature_header=sig,
        ):
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Invalid signature")

        try:
            body: dict[str, Any] = json.loads(raw.decode("utf-8"))
        except json.JSONDecodeError as e:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Invalid JSON") from e

        if body.get("type") == "url_verification":
            ch = body.get("challenge")
            if isinstance(ch, str):
                return JSONResponse({"challenge": ch})
            raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Missing challenge")

        if body.get("type") != "event_callback":
            return JSONResponse({"ok": True})

        event = body.get("event")
        if not isinstance(event, dict):
            return JSONResponse({"ok": True})

        ev_type = event.get("type")
        if ev_type != "message":
            return JSONResponse({"ok": True})

        subtype = event.get("subtype")
        if subtype in ("bot_message", "message_changed", "message_deleted"):
            return JSONResponse({"ok": True})
        if event.get("bot_id"):
            return JSONResponse({"ok": True})

        text = event.get("text")
        if not isinstance(text, str):
            text = ""
        text = augment_slack_message_text_with_block_users(text, event.get("blocks"))

        channel_id = event.get("channel")
        if not isinstance(channel_id, str) or not channel_id.startswith("D"):
            return JSONResponse({"ok": True})

        slack_user_id = event.get("user")
        if not isinstance(slack_user_id, str):
            return JSONResponse({"ok": True})

        team_id = body.get("team_id")
        if not isinstance(team_id, str):
            team_id = event.get("team")
            if not isinstance(team_id, str):
                return JSONResponse({"ok": True})

        event_id = body.get("event_id")
        event_id_str = event_id if isinstance(event_id, str) else None

        raw_ts = event.get("ts")
        message_ts = raw_ts.strip() if isinstance(raw_ts, str) and raw_ts.strip() else None

        from app.tasks.manager_onboarding import process_manager_slack_event_task

        process_manager_slack_event_task.delay(
            team_id=team_id,
            slack_user_id=slack_user_id,
            text=text,
            channel_id=channel_id,
            slack_event_id=event_id_str,
            message_ts=message_ts,
        )
        return JSONResponse({"ok": True})

    @r.post("/slack/interactive")
    async def slack_interactive(request: Request) -> JSONResponse:
        settings = get_settings()
        secret = settings.slack_signing_secret.strip()
        if not secret:
            raise HTTPException(
                status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Slack signing secret not configured.",
            )
        raw = await request.body()
        ts = request.headers.get("X-Slack-Request-Timestamp", "")
        sig = request.headers.get("X-Slack-Signature", "")
        if not verify_slack_signature(
            signing_secret=secret,
            timestamp_header=ts,
            raw_body=raw,
            signature_header=sig,
        ):
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Invalid signature")

        try:
            qs = parse_qs(raw.decode("utf-8"), keep_blank_values=True)
        except Exception as e:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Invalid body") from e

        payload_list = qs.get("payload")
        payload_raw = payload_list[0] if payload_list else None
        if not isinstance(payload_raw, str):
            raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Missing payload")

        try:
            payload: dict[str, Any] = json.loads(payload_raw)
        except json.JSONDecodeError as e:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Invalid payload JSON") from e

        if payload.get("type") != "block_actions":
            return JSONResponse({"ok": True})

        team = payload.get("team")
        team_id = team.get("id") if isinstance(team, dict) else None
        if not isinstance(team_id, str):
            return JSONResponse({"ok": True})

        user = payload.get("user")
        slack_user_id = user.get("id") if isinstance(user, dict) else None
        if not isinstance(slack_user_id, str):
            return JSONResponse({"ok": True})

        channel = payload.get("channel")
        channel_id = channel.get("id") if isinstance(channel, dict) else None
        if not isinstance(channel_id, str):
            return JSONResponse({"ok": True})

        actions = payload.get("actions")
        if not isinstance(actions, list) or not actions:
            return JSONResponse({"ok": True})

        first = actions[0]
        if not isinstance(first, dict):
            return JSONResponse({"ok": True})

        action_id = first.get("action_id")
        action_value = first.get("value")
        if not isinstance(action_id, str) or not isinstance(action_value, str):
            return JSONResponse({"ok": True})

        from app.tasks.manager_onboarding import process_manager_slack_block_action_task

        process_manager_slack_block_action_task.delay(
            team_id=team_id,
            slack_user_id=slack_user_id,
            channel_id=channel_id,
            action_id=action_id,
            action_value=action_value,
        )
        return JSONResponse({"ok": True})

    return r
