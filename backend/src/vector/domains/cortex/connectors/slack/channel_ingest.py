"""Admin Slack channel selection: list, join, persist ingest policy."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from vector.domains.cortex.connectors.slack.errors import SlackWebApiError
from vector.domains.cortex.connectors.slack.ingestion_api import (
    conversations_join,
    iter_conversations_list_pages,
)
from vector.infrastructure.db.models.raw_ingestion_record import RawIngestionRecord
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


def _parse_catalog_channel_rows(raw: dict[str, Any] | None) -> dict[str, dict[str, Any]]:
    if not isinstance(raw, dict):
        return {}
    channels = raw.get("channels")
    if not isinstance(channels, list):
        return {}
    by_id: dict[str, dict[str, Any]] = {}
    for item in channels:
        if not isinstance(item, dict):
            continue
        cid = str(item.get("channel_id") or item.get("id") or "").strip()
        if not cid:
            continue
        by_id[cid] = item
    return by_id


def _channel_row_from_slack_api(ch: dict[str, Any], *, saved_ids: set[str]) -> dict[str, Any] | None:
    cid = ch.get("id")
    if not isinstance(cid, str) or not cid.strip():
        return None
    if ch.get("is_archived"):
        return None
    cid = cid.strip()
    name = str(ch.get("name") or cid).strip()
    is_private = bool(ch.get("is_private"))
    is_member = ch.get("is_member") is True
    return {
        "channel_id": cid,
        "name": name,
        "is_private": is_private,
        "is_member": is_member,
        "selected_for_ingest": cid in saved_ids,
        "can_bot_join": not is_private,
    }


def _fetch_slack_channel_catalog_live(
    token: str,
    *,
    settings: Settings,
    saved_ids: set[str],
    max_pages: int,
) -> dict[str, dict[str, Any]]:
    api_base = _slack_api_base(settings)
    types = settings.cortex_slack_conversation_types.strip() or "public_channel,private_channel"
    by_id: dict[str, dict[str, Any]] = {}
    for page in iter_conversations_list_pages(
        token,
        api_base=api_base,
        types=types,
        max_pages=max_pages,
    ):
        for ch in page:
            row = _channel_row_from_slack_api(ch, saved_ids=saved_ids)
            if row is not None:
                by_id[str(row["channel_id"])] = row
    return by_id


def _channel_catalog_from_raw_ingest(
    db: Session,
    *,
    tenant_id: uuid.UUID,
    connection_id: uuid.UUID,
    saved_ids: set[str],
) -> dict[str, dict[str, Any]]:
    """Fallback catalog from latest ingested slack.conversation rows."""
    rows = db.execute(
        select(
            RawIngestionRecord.external_id,
            RawIngestionRecord.payload_body,
            RawIngestionRecord.fetched_at,
        )
        .where(
            RawIngestionRecord.tenant_id == tenant_id,
            RawIngestionRecord.connection_id == connection_id,
            RawIngestionRecord.resource_type == "slack.conversation",
        )
        .order_by(RawIngestionRecord.fetched_at.desc())
        .limit(5000)
    ).all()
    by_id: dict[str, dict[str, Any]] = {}
    for ext, payload, _fetched_at in rows:
        if not isinstance(ext, str) or ext in by_id:
            continue
        ch = payload.get("channel") if isinstance(payload, dict) else None
        if not isinstance(ch, dict):
            continue
        row = _channel_row_from_slack_api(ch, saved_ids=saved_ids)
        if row is not None:
            by_id[ext] = row
    return by_id


def _persist_channel_catalog(detail: Any, *, by_id: dict[str, dict[str, Any]], fetched_at: datetime) -> None:
    detail.channel_catalog_json = {"channels": sorted(by_id.values(), key=lambda x: str(x.get("name", "")).lower())}
    detail.channel_catalog_fetched_at = fetched_at


def _catalog_is_fresh(
    detail: Any,
    *,
    now: datetime,
    ttl_seconds: int,
) -> bool:
    fetched_at = getattr(detail, "channel_catalog_fetched_at", None)
    if fetched_at is None:
        return False
    if fetched_at.tzinfo is None:
        fetched_at = fetched_at.replace(tzinfo=UTC)
    age = (now - fetched_at).total_seconds()
    cached = _parse_catalog_channel_rows(getattr(detail, "channel_catalog_json", None))
    return age < float(ttl_seconds) and bool(cached)


def _resolve_channel_catalog(
    db: Session,
    link: slack_repo.SlackTenantLink,
    *,
    settings: Settings,
    force_refresh: bool,
) -> tuple[dict[str, dict[str, Any]], bool, datetime | None]:
    """Return (channels_by_id, catalog_stale, catalog_fetched_at)."""
    token = link.detail.bot_access_token
    saved_ids = set(get_saved_ingest_channel_ids(link.detail))
    now = _utc_now()
    ttl = settings.cortex_slack_admin_channel_catalog_ttl_seconds
    max_pages = settings.cortex_slack_admin_channel_catalog_max_pages

    if not force_refresh and _catalog_is_fresh(link.detail, now=now, ttl_seconds=ttl):
        cached = _parse_catalog_channel_rows(link.detail.channel_catalog_json)
        for cid in cached:
            cached[cid]["selected_for_ingest"] = cid in saved_ids
        fetched_at = link.detail.channel_catalog_fetched_at
        if fetched_at is not None and fetched_at.tzinfo is None:
            fetched_at = fetched_at.replace(tzinfo=UTC)
        return cached, False, fetched_at

    try:
        by_id = _fetch_slack_channel_catalog_live(
            token,
            settings=settings,
            saved_ids=saved_ids,
            max_pages=max_pages,
        )
        _persist_channel_catalog(link.detail, by_id=by_id, fetched_at=now)
        db.flush()
        return by_id, False, now
    except SlackWebApiError:
        cached = _parse_catalog_channel_rows(getattr(link.detail, "channel_catalog_json", None))
        if cached:
            for cid in cached:
                cached[cid]["selected_for_ingest"] = cid in saved_ids
            fetched_at = link.detail.channel_catalog_fetched_at
            if fetched_at is not None and fetched_at.tzinfo is None:
                fetched_at = fetched_at.replace(tzinfo=UTC)
            return cached, True, fetched_at
        by_id = _channel_catalog_from_raw_ingest(
            db,
            tenant_id=link.tenant_id,
            connection_id=link.connection.id,
            saved_ids=saved_ids,
        )
        if by_id:
            return by_id, True, None
        raise


def get_saved_ingest_channel_ids(detail: Any) -> list[str]:
    raw = getattr(detail, "ingest_channels_json", None)
    return [c["channel_id"] for c in _parse_saved_channels(raw if isinstance(raw, dict) else None)]


def _channel_catalog_cached_only(
    db: Session,
    link: slack_repo.SlackTenantLink,
) -> dict[str, dict[str, Any]]:
    """Catalog for apply/save only — never calls Slack conversations.list (avoids gateway timeouts)."""
    saved_ids = set(get_saved_ingest_channel_ids(link.detail))
    cached = _parse_catalog_channel_rows(getattr(link.detail, "channel_catalog_json", None))
    if cached:
        for cid in cached:
            cached[cid]["selected_for_ingest"] = cid in saved_ids
        return cached
    return _channel_catalog_from_raw_ingest(
        db,
        tenant_id=link.tenant_id,
        connection_id=link.connection.id,
        saved_ids=saved_ids,
    )


def list_slack_channels_for_admin(
    db: Session,
    *,
    tenant_id: uuid.UUID,
    settings: Settings,
    force_refresh: bool = False,
) -> dict[str, Any]:
    link = slack_repo.get_slack_connection_for_tenant(db, tenant_id)
    if link is None:
        return {"connected": False, "channels": [], "saved_channel_ids": []}

    by_id, catalog_stale, catalog_fetched_at = _resolve_channel_catalog(
        db,
        link,
        settings=settings,
        force_refresh=force_refresh,
    )
    saved_ids = sorted(set(get_saved_ingest_channel_ids(link.detail)))
    channels = sorted(by_id.values(), key=lambda x: str(x.get("name", "")).lower())
    return {
        "connected": True,
        "team_id": link.detail.team_id,
        "team_name": link.detail.team_name,
        "saved_channel_ids": saved_ids,
        "channels": channels,
        "catalog_stale": catalog_stale,
        "catalog_fetched_at": catalog_fetched_at.isoformat() if catalog_fetched_at else None,
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
    catalog_by_id = _channel_catalog_cached_only(db, link)

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
            meta = {
                "channel_id": cid,
                "name": cid,
                "is_private": False,
                "is_member": False,
                "can_bot_join": True,
            }
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
            "A Slack ingestion sync has been queued."
        ),
    }


def enqueue_slack_ingest_after_channel_apply(
    *,
    tenant_id: uuid.UUID,
    connection_id: uuid.UUID,
) -> dict[str, str]:
    """Queue one incremental Slack sync so history fetch starts without waiting for the scheduler."""
    from vector.domains.cortex.connectors.provider_keys import CONNECTION_PROVIDER_SLACK

    from app.tasks.cortex_ingestion_sync import run_cortex_connector_sync_task

    run_cortex_connector_sync_task.apply_async(
        args=[
            str(tenant_id),
            CONNECTION_PROVIDER_SLACK,
            "slack_channel_apply",
            "incremental",
            str(connection_id),
        ],
        queue="cortex_live",
    )
    return {"queued": "true", "connector": CONNECTION_PROVIDER_SLACK}
