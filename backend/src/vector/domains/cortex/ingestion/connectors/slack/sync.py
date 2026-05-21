"""Phase 01 — slack connector sync."""

from __future__ import annotations

import json
import logging
import time
import uuid
from datetime import UTC, datetime
from collections.abc import Mapping
from typing import Any, cast

import httpx
from sqlalchemy import Table, case, func, select, text
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from vector.domains.cortex.connectors.github.errors import GitHubApiError
from vector.domains.cortex.connectors.github.http_client import (
    create_github_installation_access_token,
    list_deployment_statuses_page,
    list_installation_repositories_page,
    list_pull_issue_comments_page,
    list_pull_review_comments_page,
    list_pull_reviews_page,
    list_repo_branches_page,
    list_repo_check_runs_page,
    list_repo_commit_comments_page,
    list_repo_commits_page,
    list_repo_deployments_page,
    list_repo_issues_page,
    list_repo_issue_timeline_page,
    list_repo_pulls_page,
    list_repo_releases_page,
    list_repo_tags_page,
    list_repo_workflow_runs_page,
)
from vector.domains.cortex.connectors.provider_keys import (
    CONNECTION_PROVIDER_CALLS,
    CONNECTION_PROVIDER_GITHUB,
    CONNECTION_PROVIDER_LINEAR,
    CONNECTION_PROVIDER_NOTION,
    CONNECTION_PROVIDER_SLACK,
)
from vector.domains.cortex.ingestion.checkpoint_contract import merge_monotonic_connector_state
from vector.domains.cortex.ingestion.raw_envelope_contract import (
    EnvelopeContractViolation,
    core_envelope_fields,
    validate_raw_payload_for_persistence,
)
from vector.domains.cortex.ingestion.live_idempotency import (
    canonical_payload_hash,
    derive_logical_idempotency_key,
    derive_source_identity_key,
    derive_source_revision_key,
)
from vector.domains.cortex.ingestion.sync_context import SCOPE_DEFAULT, IngestionSyncContext
from vector.domains.cortex.ingestion.temporal_ordering import (
    derive_deletion_observed,
    derive_provider_event_timestamp,
)
from vector.infrastructure.db.models.connector_sync_state import ConnectorSyncState
from vector.infrastructure.db.models.ingestion_run import IngestionRun
from vector.infrastructure.db.models.raw_ingestion_record import RawIngestionRecord
from vector.infrastructure.db.models.raw_memory_archive_catalog import RawMemoryArchiveCatalog
from vector.infrastructure.db.models.raw_memory_lineage_index import RawMemoryLineageIndex
from vector.infrastructure.db.models.raw_memory_revision_index import RawMemoryRevisionIndex
from vector.infrastructure.db.models.tenant_connection import TenantConnection
from vector.infrastructure.db.repositories import calls_connection as calls_repo
from vector.infrastructure.db.repositories import github_connection as gh_repo
from vector.infrastructure.db.repositories import linear_connection as lin_repo
from vector.infrastructure.db.repositories import notion_connection as notion_repo
from vector.domains.cortex.connectors.slack.channel_ingest import get_saved_ingest_channel_ids
from vector.infrastructure.db.repositories import slack_connection as slack_repo
from vector.infrastructure.observability.ingestion_tasks import (
    PHASE_STEP1,
    PHASE_STEP3,
    PHASE_STEP4,
    PHASE_STEP5,
    log_ingestion_event,
)
from vector.settings import Settings

_logger = logging.getLogger("app")

from vector.domains.cortex.ingestion.sync_shared import (
    append_raw,
    checkpoint_streams_for_mode,
    generic_scope_ping,
    hash_payload,
    idem_key,
    read_checkpoint_state,
    tag_replay_payload,
    upsert_checkpoint,
    utc_now,
)


def slack_ts_value(ts: str) -> float:
    try:
        return float(ts)
    except ValueError:
        return 0.0


def slack_history_pages_done(existing_history: dict[str, Any] | None) -> int | None:
    history = existing_history if isinstance(existing_history, dict) else {}
    cumulative = history.get("cumulative_history_pages")
    if isinstance(cumulative, int):
        return cumulative
    at_complete = history.get("history_pages_at_complete")
    if isinstance(at_complete, int):
        return at_complete
    last_run = history.get("pages_fetched_last_run")
    if isinstance(last_run, int):
        return last_run
    return None


def slack_channel_history_sync_mode(
    *,
    ctx_sync_mode: str,
    channel_id: str,
    ingest_channel_ids: set[str],
    existing_history: dict[str, Any] | None,
) -> str:
    """Keep admin-selected channels in backfill until history is fully paginated."""
    if ctx_sync_mode == "backfill":
        return "backfill"
    history = existing_history if isinstance(existing_history, dict) else {}
    if ingest_channel_ids and channel_id not in ingest_channel_ids:
        return "incremental"
    if history.get("backfill_exhausted") is True:
        return "incremental"
    if history.get("backfill_complete") is True:
        pages_done = slack_history_pages_done(history)
        if pages_done is None or pages_done <= 1:
            return "backfill"
        return "incremental"
    return "backfill"


def slack_history_time_bounds(
    *,
    sync_mode: str,
    existing_history: dict[str, Any] | None,
    history_cursor: str | None,
    backfill_oldest_ts: str,
) -> tuple[str | None, str | None]:
    """Return (oldest, latest) for conversations.history when cursor is absent."""
    history = existing_history if isinstance(existing_history, dict) else {}
    if sync_mode == "incremental":
        last_seen = history.get("last_message_ts")
        if isinstance(last_seen, str) and last_seen.strip():
            return last_seen.strip(), None
        return None, None
    if backfill_oldest_ts.strip():
        return backfill_oldest_ts.strip(), None
    if history_cursor:
        return None, None
    last_seen = history.get("last_message_ts")
    if isinstance(last_seen, str) and last_seen.strip():
        return None, last_seen.strip()
    return None, None


def pick_slack_channels_round_robin(
    channels: list[dict[str, Any]],
    *,
    ring_index: int,
    count: int,
) -> tuple[list[dict[str, Any]], int]:
    if count <= 0 or not channels:
        return [], 0
    ordered = sorted(
        [c for c in channels if isinstance(c.get("id"), str)],
        key=lambda c: str(c.get("id")),
    )
    if not ordered:
        return [], 0
    start = max(0, ring_index) % len(ordered)
    out: list[dict[str, Any]] = []
    idx = start
    for _ in range(min(count, len(ordered))):
        out.append(ordered[idx])
        idx = (idx + 1) % len(ordered)
    return out, idx

def run_slack_connector_sync(
    session: Session,
    settings: Settings,
    *,
    ctx: IngestionSyncContext,
    tenant_id: uuid.UUID,
    connection_id: uuid.UUID,
    run_id: uuid.UUID,
    source_trigger: str,
) -> int:
    scope_ck = ctx.checkpoint_scope_key()
    existing_ckpt = read_checkpoint_state(
        session,
        tenant_id=tenant_id,
        connection_id=connection_id,
        connector=CONNECTION_PROVIDER_SLACK,
        scope_key=scope_ck,
    )
    link = slack_repo.get_slack_connection_for_tenant(session, tenant_id)
    if link is None:
        return generic_scope_ping(
            session,
            ctx=ctx,
            tenant_id=tenant_id,
            connection_id=connection_id,
            connector=CONNECTION_PROVIDER_SLACK,
            run_id=run_id,
            source_trigger=source_trigger,
            label="no_slack_detail",
        )
    token = link.detail.bot_access_token
    from vector.domains.cortex.connectors.slack.errors import SlackWebApiError
    from vector.domains.cortex.connectors.slack.ingestion_api import (
        iter_conversations_list_pages,
        iter_conversations_history_pages,
        iter_conversations_replies_pages,
        iter_users_list_pages,
    )

    n_ins = 0
    user_pages = 0
    user_members = 0
    channel_pages = 0
    channel_rows = 0
    message_rows = 0
    reply_rows = 0
    reaction_rows = 0
    file_rows = 0
    thread_pages = 0
    thread_rows = 0
    threads_processed = 0
    budget_exhausted = False
    slack_api_base = "https://slack.com/api"
    if settings.vector_use_mock_connectors and settings.notion_api_base_url().endswith("/admin/dataset/full"):
        slack_api_base = f"{settings.vector_mock_connector_base_url.rstrip('/')}/slack/api"
    start_t = time.monotonic()

    streams_existing = checkpoint_streams_for_mode(existing_ckpt, ctx.sync_mode)
    slack_existing = (
        streams_existing.get("slack")
        if isinstance(streams_existing, dict) and isinstance(streams_existing.get("slack"), dict)
        else {}
    )
    channels_existing = (
        slack_existing.get("channels")
        if isinstance(slack_existing, dict) and isinstance(slack_existing.get("channels"), dict)
        else {}
    )
    ring_index_raw = slack_existing.get("channel_ring_index") if isinstance(slack_existing, dict) else 0
    try:
        ring_index = int(ring_index_raw)
    except (TypeError, ValueError):
        ring_index = 0

    channel_patch_map: dict[str, Any] = (
        dict(channels_existing) if isinstance(channels_existing, dict) else {}
    )
    try:
        for members in iter_users_list_pages(
            token,
            api_base=slack_api_base,
            max_pages=settings.cortex_slack_users_max_pages,
        ):
            user_pages += 1
            for m in members:
                uid = m.get("id")
                if not isinstance(uid, str) or not uid:
                    continue
                user_members += 1
                body = {
                    **core_envelope_fields(
                        connector=CONNECTION_PROVIDER_SLACK,
                        connection_id=connection_id,
                        source_object_type="slack.user",
                        source_object_id=uid,
                    ),
                    "member": m,
                }
                if append_raw(
                    session,
                    ctx=ctx,
                    tenant_id=tenant_id,
                    connection_id=connection_id,
                    connector=CONNECTION_PROVIDER_SLACK,
                    run_id=run_id,
                    source_trigger=source_trigger,
                    resource_type="slack.user",
                    external_id=uid,
                    api_endpoint=f"{slack_api_base}/users.list",
                    query_params={"source": "users.list"},
                    payload_body=body,
                    http_status=200,
                    idempotency_key=idem_key(ctx, run_id, f"slack:user:{uid}"),
                ):
                    n_ins += 1

        all_channels: list[dict[str, Any]] = []
        for chans in iter_conversations_list_pages(
            token,
            api_base=slack_api_base,
            types=settings.cortex_slack_conversation_types,
            max_pages=settings.cortex_slack_conversations_max_pages,
        ):
            channel_pages += 1
            all_channels.extend(chans)
            for c in chans:
                cid = c.get("id")
                if not isinstance(cid, str) or not cid:
                    continue
                channel_rows += 1
                body = {
                    **core_envelope_fields(
                        connector=CONNECTION_PROVIDER_SLACK,
                        connection_id=connection_id,
                        source_object_type="slack.conversation",
                        source_object_id=cid,
                    ),
                    "channel": c,
                }
                if append_raw(
                    session,
                    ctx=ctx,
                    tenant_id=tenant_id,
                    connection_id=connection_id,
                    connector=CONNECTION_PROVIDER_SLACK,
                    run_id=run_id,
                    source_trigger=source_trigger,
                    resource_type="slack.conversation",
                    external_id=cid,
                    api_endpoint=f"{slack_api_base}/conversations.list",
                    query_params={"source": "conversations.list"},
                    payload_body=body,
                    http_status=200,
                    idempotency_key=idem_key(ctx, run_id, f"slack:channel:{cid}"),
                ):
                    n_ins += 1

        ingest_channel_ids = set(get_saved_ingest_channel_ids(link.detail))
        if ingest_channel_ids:
            candidates = [
                c
                for c in all_channels
                if isinstance(c.get("id"), str)
                and str(c["id"]) in ingest_channel_ids
                and c.get("is_archived") is not True
            ]
        else:
            candidates = [
                c
                for c in all_channels
                if isinstance(c.get("id"), str)
                and c.get("is_member") is not False
                and c.get("is_archived") is not True
            ]
        if ingest_channel_ids:
            listed_ids = {
                str(c["id"]) for c in candidates if isinstance(c.get("id"), str) and str(c["id"]).strip()
            }
            for missing_id in sorted(ingest_channel_ids):
                if missing_id in listed_ids:
                    continue
                try:
                    from vector.domains.cortex.connectors.slack.ingestion_api import conversations_info

                    ch_info = conversations_info(token, channel=missing_id, api_base=slack_api_base)
                    if ch_info.get("is_archived") is not True:
                        candidates.append(ch_info)
                        listed_ids.add(missing_id)
                except SlackWebApiError:
                    candidates.append(
                        {
                            "id": missing_id,
                            "is_archived": False,
                            "is_private": False,
                            "is_member": True,
                        }
                    )
                    listed_ids.add(missing_id)

        selected_channels, next_ring_index = pick_slack_channels_round_robin(
            candidates,
            ring_index=ring_index,
            count=settings.cortex_slack_history_channels_per_sync,
        )
        for c in selected_channels:
            cid = str(c["id"])
            existing_channel = channel_patch_map.get(cid)
            if not isinstance(existing_channel, dict):
                existing_channel = (
                    channels_existing.get(cid) if isinstance(channels_existing, dict) else None
                )
            existing_history = (
                existing_channel.get("history")
                if isinstance(existing_channel, dict) and isinstance(existing_channel.get("history"), dict)
                else {}
            )
            sync_mode = slack_channel_history_sync_mode(
                ctx_sync_mode=ctx.checkpoint_sync_mode,
                channel_id=cid,
                ingest_channel_ids=ingest_channel_ids,
                existing_history=existing_history,
            )
            history_cursor = existing_history.get("next_cursor")
            if not isinstance(history_cursor, str) or not history_cursor.strip():
                history_cursor = None
            # Incremental must use oldest=last_message_ts on the first history page.
            # Slack ignores oldest/latest when ``cursor`` is set, so a leftover backfill
            # cursor would replay old pages and miss same-day messages.
            if sync_mode == "incremental":
                history_cursor = None
            oldest, latest = slack_history_time_bounds(
                sync_mode=sync_mode,
                existing_history=existing_history,
                history_cursor=history_cursor,
                backfill_oldest_ts=settings.cortex_slack_backfill_oldest_ts,
            )

            channel_message_rows = 0
            channel_reply_rows = 0
            channel_reaction_rows = 0
            channel_file_rows = 0
            channel_thread_pages = 0
            history_pages = 0
            latest_message_ts = (
                oldest
                if isinstance(oldest, str)
                else (
                    existing_history.get("last_message_ts")
                    if isinstance(existing_history.get("last_message_ts"), str)
                    else None
                )
            )
            next_history_cursor: str | None = history_cursor
            thread_roots: list[str] = []
            thread_seen: set[str] = set()

            for page in iter_conversations_history_pages(
                token,
                api_base=slack_api_base,
                channel=cid,
                limit=settings.cortex_slack_conversations_history_limit,
                max_pages=settings.cortex_slack_history_max_pages_per_channel,
                cursor=history_cursor,
                oldest=oldest,
                latest=latest,
            ):
                history_pages += 1
                page_cursor = page.get("next_cursor")
                next_history_cursor = page_cursor if isinstance(page_cursor, str) and page_cursor else None
                page_messages = page.get("messages")
                msgs = [m for m in page_messages if isinstance(m, dict)] if isinstance(page_messages, list) else []
                for msg in msgs:
                    ts = msg.get("ts")
                    if not isinstance(ts, str):
                        continue
                    ext = f"{cid}:{ts}"[:512]
                    if latest_message_ts is None or slack_ts_value(ts) > slack_ts_value(latest_message_ts):
                        latest_message_ts = ts
                    body = {
                        **core_envelope_fields(
                            connector=CONNECTION_PROVIDER_SLACK,
                            connection_id=connection_id,
                            source_object_type="slack.message",
                            source_object_id=ext,
                        ),
                        "channel_id": cid,
                        "message": msg,
                        "paging": {"next_cursor": next_history_cursor, "mode": sync_mode},
                    }
                    message_rows += 1
                    channel_message_rows += 1
                    if append_raw(
                        session,
                        ctx=ctx,
                        tenant_id=tenant_id,
                        connection_id=connection_id,
                        connector=CONNECTION_PROVIDER_SLACK,
                        run_id=run_id,
                        source_trigger=source_trigger,
                        resource_type="slack.message",
                        external_id=ext,
                        api_endpoint=f"{slack_api_base}/conversations.history",
                        query_params={"channel": cid, "mode": sync_mode},
                        payload_body=body,
                        http_status=200,
                        idempotency_key=idem_key(ctx, run_id, f"slack:msg:{cid}:{ts}"),
                    ):
                        n_ins += 1

                    rc = msg.get("reply_count")
                    thread_ts = msg.get("thread_ts")
                    if isinstance(rc, int) and rc > 0 and isinstance(thread_ts, str) and thread_ts == ts:
                        if thread_ts not in thread_seen:
                            thread_seen.add(thread_ts)
                            thread_roots.append(thread_ts)
                            thr_ext = f"{cid}:{thread_ts}"[:512]
                            if append_raw(
                                session,
                                ctx=ctx,
                                tenant_id=tenant_id,
                                connection_id=connection_id,
                                connector=CONNECTION_PROVIDER_SLACK,
                                run_id=run_id,
                                source_trigger=source_trigger,
                                resource_type="slack.thread",
                                external_id=thr_ext,
                                api_endpoint=f"{slack_api_base}/conversations.history",
                                query_params={"channel": cid, "thread_ts": thread_ts},
                                payload_body={
                                    **core_envelope_fields(
                                        connector=CONNECTION_PROVIDER_SLACK,
                                        connection_id=connection_id,
                                        source_object_type="slack.thread",
                                        source_object_id=thr_ext,
                                    ),
                                    "channel": cid,
                                    "thread_ts": thread_ts,
                                    "root_message_ts": ts,
                                },
                                http_status=200,
                                idempotency_key=idem_key(ctx, run_id, f"slack:thread:{thr_ext}"),
                            ):
                                n_ins += 1
                                thread_rows += 1

                    reactions = msg.get("reactions")
                    if isinstance(reactions, list):
                        for reaction in reactions:
                            if not isinstance(reaction, dict):
                                continue
                            name = reaction.get("name")
                            if not isinstance(name, str) or not name.strip():
                                continue
                            reaction_ext = f"{cid}:{ts}:{name.strip()}"[:512]
                            reaction_rows += 1
                            channel_reaction_rows += 1
                            if append_raw(
                                session,
                                ctx=ctx,
                                tenant_id=tenant_id,
                                connection_id=connection_id,
                                connector=CONNECTION_PROVIDER_SLACK,
                                run_id=run_id,
                                source_trigger=source_trigger,
                                resource_type="slack.reaction",
                                external_id=reaction_ext,
                                api_endpoint=f"{slack_api_base}/conversations.history",
                                query_params={"channel": cid, "message_ts": ts},
                                payload_body={
                                    **core_envelope_fields(
                                        connector=CONNECTION_PROVIDER_SLACK,
                                        connection_id=connection_id,
                                        source_object_type="slack.reaction",
                                        source_object_id=reaction_ext,
                                    ),
                                    "channel_id": cid,
                                    "message_ts": ts,
                                    "reaction": reaction,
                                },
                                http_status=200,
                                idempotency_key=idem_key(ctx, run_id, f"slack:reaction:{reaction_ext}"),
                            ):
                                n_ins += 1

                    files = msg.get("files")
                    msg_thread_ts = msg.get("thread_ts")
                    if isinstance(files, list):
                        for f in files:
                            if not isinstance(f, dict):
                                continue
                            fid = f.get("id")
                            if not isinstance(fid, str) or not fid.strip():
                                continue
                            file_ext = f"{cid}:{fid.strip()}"[:512]
                            file_rows += 1
                            channel_file_rows += 1
                            if append_raw(
                                session,
                                ctx=ctx,
                                tenant_id=tenant_id,
                                connection_id=connection_id,
                                connector=CONNECTION_PROVIDER_SLACK,
                                run_id=run_id,
                                source_trigger=source_trigger,
                                resource_type="slack.file",
                                external_id=file_ext,
                                api_endpoint=f"{slack_api_base}/conversations.history",
                                query_params={"channel": cid, "message_ts": ts},
                                payload_body={
                                    **core_envelope_fields(
                                        connector=CONNECTION_PROVIDER_SLACK,
                                        connection_id=connection_id,
                                        source_object_type="slack.file",
                                        source_object_id=file_ext,
                                    ),
                                    "channel_id": cid,
                                    "message_ts": ts,
                                    "thread_ts": msg_thread_ts
                                    if isinstance(msg_thread_ts, str) and msg_thread_ts.strip()
                                    else None,
                                    "file": f,
                                },
                                http_status=200,
                                idempotency_key=idem_key(ctx, run_id, f"slack:file:{file_ext}"),
                            ):
                                n_ins += 1

                if not next_history_cursor:
                    break
                if time.monotonic() - start_t >= settings.cortex_slack_channel_time_budget_seconds:
                    budget_exhausted = True
                    break

            history_state = (
                existing_history if isinstance(existing_history, dict) else {}
            )
            prev_cumulative = 0
            if isinstance(history_state.get("cumulative_history_pages"), int):
                prev_cumulative = int(history_state["cumulative_history_pages"])
            cumulative_history_pages = prev_cumulative + history_pages
            last_message_ts = history_state.get("last_message_ts")
            history_no_progress = (
                sync_mode == "backfill"
                and history_pages == 0
                and channel_message_rows == 0
                and isinstance(last_message_ts, str)
                and last_message_ts.strip()
            )
            backfill_exhausted = (
                history_state.get("backfill_exhausted") is True or history_no_progress
            )
            history_complete = bool(not next_history_cursor and not backfill_exhausted)
            channel_patch_map[cid] = {
                "cursor_owner": "slack.message",
                "history": {
                    "last_message_ts": latest_message_ts,
                    "next_cursor": next_history_cursor,
                    "backfill_complete": history_complete,
                    "backfill_exhausted": backfill_exhausted,
                    "cumulative_history_pages": cumulative_history_pages,
                    "history_pages_at_complete": (
                        cumulative_history_pages
                        if history_complete
                        else existing_history.get("history_pages_at_complete")
                    ),
                    "pages_fetched_last_run": history_pages,
                },
                "threads": (
                    existing_channel.get("threads")
                    if isinstance(existing_channel, dict) and isinstance(existing_channel.get("threads"), dict)
                    else {}
                ),
                "last_sync_mode": sync_mode,
                "message_rows_last_run": channel_message_rows,
                "reply_rows_last_run": channel_reply_rows,
                "reaction_rows_last_run": channel_reaction_rows,
                "file_rows_last_run": channel_file_rows,
                "thread_pages_last_run": channel_thread_pages,
            }

            existing_threads = (
                channel_patch_map[cid].get("threads")
                if isinstance(channel_patch_map.get(cid), dict)
                else {}
            )
            if not isinstance(existing_threads, dict):
                existing_threads = {}
            thread_patch: dict[str, Any] = dict(existing_threads)
            for thread_ts in thread_roots:
                if threads_processed >= settings.cortex_slack_threads_per_sync:
                    break
                threads_processed += 1
                existing_thread = (
                    existing_threads.get(thread_ts)
                    if isinstance(existing_threads, dict) and isinstance(existing_threads.get(thread_ts), dict)
                    else {}
                )
                replies_cursor = existing_thread.get("next_cursor")
                if not isinstance(replies_cursor, str) or not replies_cursor.strip():
                    replies_cursor = None
                replies_oldest: str | None = None
                if sync_mode == "incremental":
                    last_reply_ts = existing_thread.get("last_reply_ts")
                    if isinstance(last_reply_ts, str) and last_reply_ts.strip():
                        replies_oldest = last_reply_ts.strip()
                next_replies_cursor: str | None = replies_cursor
                latest_reply_ts = (
                    replies_oldest
                    if isinstance(replies_oldest, str)
                    else (
                        existing_thread.get("last_reply_ts")
                        if isinstance(existing_thread.get("last_reply_ts"), str)
                        else None
                    )
                )
                per_thread_pages = 0
                try:
                    for rep_page in iter_conversations_replies_pages(
                        token,
                        api_base=slack_api_base,
                        channel=cid,
                        thread_ts=thread_ts,
                        limit=settings.cortex_slack_conversations_history_limit,
                        max_pages=settings.cortex_slack_replies_max_pages_per_thread,
                        cursor=replies_cursor,
                        oldest=replies_oldest,
                    ):
                        per_thread_pages += 1
                        thread_pages += 1
                        channel_thread_pages += 1
                        page_cursor = rep_page.get("next_cursor")
                        next_replies_cursor = page_cursor if isinstance(page_cursor, str) and page_cursor else None
                        rep_msgs = rep_page.get("messages")
                        rows = [m for m in rep_msgs if isinstance(m, dict)] if isinstance(rep_msgs, list) else []
                        for reply in rows:
                            rts = reply.get("ts")
                            if not isinstance(rts, str) or rts == thread_ts:
                                continue
                            reply_ext = f"{cid}:{thread_ts}:{rts}"[:512]
                            if latest_reply_ts is None or slack_ts_value(rts) > slack_ts_value(latest_reply_ts):
                                latest_reply_ts = rts
                            reply_rows += 1
                            channel_reply_rows += 1
                            if append_raw(
                                session,
                                ctx=ctx,
                                tenant_id=tenant_id,
                                connection_id=connection_id,
                                connector=CONNECTION_PROVIDER_SLACK,
                                run_id=run_id,
                                source_trigger=source_trigger,
                                resource_type="slack.message_reply",
                                external_id=reply_ext,
                                api_endpoint=f"{slack_api_base}/conversations.replies",
                                query_params={"channel": cid, "thread_ts": thread_ts, "mode": sync_mode},
                                payload_body={
                                    **core_envelope_fields(
                                        connector=CONNECTION_PROVIDER_SLACK,
                                        connection_id=connection_id,
                                        source_object_type="slack.message_reply",
                                        source_object_id=reply_ext,
                                    ),
                                    "channel_id": cid,
                                    "thread_ts": thread_ts,
                                    "reply": reply,
                                    "paging": {"next_cursor": next_replies_cursor, "mode": sync_mode},
                                },
                                http_status=200,
                                idempotency_key=idem_key(ctx, run_id, f"slack:reply:{reply_ext}"),
                            ):
                                n_ins += 1
                        if not next_replies_cursor:
                            break
                        if time.monotonic() - start_t >= settings.cortex_slack_channel_time_budget_seconds:
                            budget_exhausted = True
                            break
                except SlackWebApiError as reply_exc:
                    _logger.warning(
                        "slack thread replies skipped",
                        extra={"channel_id": cid, "thread_ts": thread_ts, "error": str(reply_exc)},
                    )
                    thread_patch[thread_ts] = {
                        "cursor_owner": "slack.message_reply",
                        "last_sync_error": str(reply_exc),
                    }
                    continue

                thread_patch[thread_ts] = {
                    "cursor_owner": "slack.message_reply",
                    "last_reply_ts": latest_reply_ts,
                    "next_cursor": next_replies_cursor,
                    "backfill_complete": bool(not next_replies_cursor),
                    "pages_fetched_last_run": per_thread_pages,
                }
                if budget_exhausted:
                    break

            if isinstance(channel_patch_map.get(cid), dict):
                channel_patch_map[cid]["threads"] = thread_patch
                channel_patch_map[cid]["reply_rows_last_run"] = channel_reply_rows
                channel_patch_map[cid]["thread_pages_last_run"] = channel_thread_pages
            if budget_exhausted:
                break

    except SlackWebApiError as e:
        err_ins = int(
            append_raw(
                session,
                ctx=ctx,
                tenant_id=tenant_id,
                connection_id=connection_id,
                connector=CONNECTION_PROVIDER_SLACK,
                run_id=run_id,
                source_trigger=source_trigger,
                resource_type="slack.api_error",
                external_id="slack_web_api",
                api_endpoint=f"{slack_api_base}/ingestion_error",
                query_params={"error": True},
                payload_body={
                    **core_envelope_fields(
                        connector=CONNECTION_PROVIDER_SLACK,
                        connection_id=connection_id,
                        source_object_type="slack.api_error",
                        source_object_id="slack_web_api",
                    ),
                    "error": str(e),
                },
                http_status=502,
                idempotency_key=idem_key(ctx, run_id, "slack:api_error"),
            )
        )
        n_ins += err_ins

    chosen_types = [
        t.strip()
        for t in settings.cortex_slack_conversation_types.split(",")
        if isinstance(t, str) and t.strip()
    ]
    if not chosen_types:
        chosen_types = ["public_channel", "private_channel"]

    upsert_checkpoint(
        session,
        tenant_id=tenant_id,
        connection_id=connection_id,
        connector=CONNECTION_PROVIDER_SLACK,
        scope_key=scope_ck,
        patch={
            "last_incremental_at": utc_now().isoformat(),
            "slack_user_pages": user_pages,
            "slack_user_members_seen": user_members,
            "slack_conversation_pages": channel_pages,
            "slack_conversations_seen": channel_rows,
            "slack_messages_seen": message_rows,
            "slack_message_replies_seen": reply_rows,
            "slack_threads_seen": thread_rows,
            "slack_reactions_seen": reaction_rows,
            "slack_files_seen": file_rows,
            "streams": {
                "slack": {
                    "users": {
                        "cursor_owner": "slack.user",
                        "pages_fetched": user_pages,
                    },
                    "conversations": {
                        "cursor_owner": "slack.conversation",
                        "pages_fetched": channel_pages,
                    },
                    "messages": {
                        "cursor_owner": "slack.message",
                        "rows_seen": message_rows,
                    },
                    "message_replies": {
                        "cursor_owner": "slack.message_reply",
                        "rows_seen": reply_rows,
                        "thread_pages_seen": thread_pages,
                    },
                    "threads": {
                        "cursor_owner": "slack.thread",
                        "rows_seen": thread_rows,
                    },
                    "reactions": {
                        "cursor_owner": "slack.reaction",
                        "rows_seen": reaction_rows,
                    },
                    "files": {
                        "cursor_owner": "slack.file",
                        "rows_seen": file_rows,
                    },
                    "channels": channel_patch_map,
                    "channel_ring_index": next_ring_index if "next_ring_index" in locals() else ring_index,
                    "conversation_types": chosen_types,
                    "resume_required": budget_exhausted,
                    "time_budget_seconds": settings.cortex_slack_channel_time_budget_seconds,
                }
            },
        },
        sync_mode=ctx.checkpoint_sync_mode,
    )
    return n_ins


