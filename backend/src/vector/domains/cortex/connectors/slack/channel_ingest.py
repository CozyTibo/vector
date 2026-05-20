"""Admin Slack channel selection: list, join, persist ingest policy."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.orm import Session

from vector.domains.cortex.connectors.slack.errors import SlackWebApiError
from vector.domains.cortex.connectors.slack.ingestion_api import (
    conversations_join,
    iter_conversations_list_pages,
)
from vector.infrastructure.db.repositories import slack_connection as slack_repo
from vector.settings import Settings


def _utc_now() -> datetime:
    return datetime.now(UTC)


def _slack_api_base(settings: Settings) -> str:
    if settings.vector_use_mock_connectors and settings.notion_api_base_url().endswith("/admin/dataset/full"):
        return f"{settings.vector_mock_connector_base_url.rstrip('/')}/slack/api"
    return "https://slack.com/api"


def _parse_saved_channels(raw: dict[str, Any] | None) -> list[dict[str, str]]:
    if not isinstance(raw, dict):
        return []
    channels = raw.get("channels")
    if not isinstance(channels, list):
        return []
    out: list[dict[str, str]] = []
    for item in channels:
        if not isinstance(item, dict):
            continue
        cid = str(item.get("channel_id") or item.get("id") or "").strip()
        if not cid:
            continue
        name = str(item.get("name") or cid).strip()
        out.append({"channel_id": cid, "name": name})
    return out


def get_saved_ingest_channel_ids(detail: Any) -> list[str]:
    raw = getattr(detail, "ingest_channels_json", None)
    return [c["channel_id"] for c in _parse_saved_channels(raw if isinstance(raw, dict) else None)]


def list_slack_channels_for_admin(
    db: Session,
    *,
    tenant_id: uuid.UUID,
    settings: Settings,
) -> dict[str, Any]:
    link = slack_repo.get_slack_connection_for_tenant(db, tenant_id)
    if link is None:
        return {"connected": False, "channels": [], "saved_channel_ids": []}

    token = link.detail.bot_access_token
    api_base = _slack_api_base(settings)
    types = settings.cortex_slack_conversation_types.strip() or "public_channel,private_channel"
    saved_ids = set(get_saved_ingest_channel_ids(link.detail))
    by_id: dict[str, dict[str, Any]] = {}

    for page in iter_conversations_list_pages(
        token,
        api_base=api_base,
        types=types,
        max_pages=settings.cortex_slack_conversations_max_pages,
    ):
        for ch in page:
            cid = ch.get("id")
            if not isinstance(cid, str) or not cid.strip():
                continue
            if ch.get("is_archived"):
                continue
            name = str(ch.get("name") or cid).strip()
            is_private = bool(ch.get("is_private"))
            is_member = ch.get("is_member") is True
            by_id[cid] = {
                "channel_id": cid,
                "name": name,
                "is_private": is_private,
                "is_member": is_member,
                "selected_for_ingest": cid in saved_ids,
                "can_bot_join": not is_private,
            }

    channels = sorted(by_id.values(), key=lambda x: str(x.get("name", "")).lower())
    return {
        "connected": True,
        "team_id": link.detail.team_id,
        "team_name": link.detail.team_name,
        "saved_channel_ids": sorted(saved_ids),
        "channels": channels,
    }


def apply_slack_ingest_channel_selection(
    db: Session,
    *,
    tenant_id: uuid.UUID,
    channel_ids: list[str],
    settings: Settings,
) -> dict[str, Any]:
    link = slack_repo.get_slack_connection_for_tenant(db, tenant_id)
    if link is None:
        msg = "slack_not_connected"
        raise ValueError(msg)

    token = link.detail.bot_access_token
    api_base = _slack_api_base(settings)
    types = settings.cortex_slack_conversation_types.strip() or "public_channel,private_channel"
    catalog = list_slack_channels_for_admin(db, tenant_id=tenant_id, settings=settings)
    catalog_by_id = {
        str(c["channel_id"]): c for c in catalog.get("channels", []) if isinstance(c, dict)
    }

    requested = []
    seen: set[str] = set()
    for raw_id in channel_ids:
        cid = str(raw_id or "").strip()
        if not cid or cid in seen:
            continue
        seen.add(cid)
        requested.append(cid)

    join_results: list[dict[str, Any]] = []
    saved_channels: list[dict[str, str]] = []

    for cid in requested:
        meta = catalog_by_id.get(cid)
        if meta is None:
            join_results.append(
                {
                    "channel_id": cid,
                    "joined": False,
                    "error": "channel_not_visible_to_bot",
                }
            )
            continue
        name = str(meta.get("name") or cid)
        is_private = bool(meta.get("is_private"))
        is_member = bool(meta.get("is_member"))

        if is_member:
            join_results.append({"channel_id": cid, "joined": True, "error": None, "already_member": True})
            saved_channels.append({"channel_id": cid, "name": name})
            continue

        if is_private:
            join_results.append(
                {
                    "channel_id": cid,
                    "joined": False,
                    "error": "private_channel_invite_required",
                }
            )
            saved_channels.append({"channel_id": cid, "name": name})
            continue

        try:
            conversations_join(token, channel=cid, api_base=api_base)
            join_results.append({"channel_id": cid, "joined": True, "error": None})
            saved_channels.append({"channel_id": cid, "name": name})
        except SlackWebApiError as exc:
            join_results.append({"channel_id": cid, "joined": False, "error": str(exc)})

    link.detail.ingest_channels_json = {
        "channels": saved_channels,
        "updated_at": _utc_now().isoformat(),
        "conversation_types": types,
    }
    db.flush()

    joined_n = sum(1 for r in join_results if r.get("joined"))
    failed_n = sum(1 for r in join_results if not r.get("joined"))
    return {
        "saved_channels": saved_channels,
        "join_results": join_results,
        "joined_count": joined_n,
        "failed_count": failed_n,
        "message": (
            "Selection saved. Public channels were joined where possible; "
            "private channels require inviting the bot in Slack. "
            "Message history will be fetched on the next ingestion run."
        ),
    }
