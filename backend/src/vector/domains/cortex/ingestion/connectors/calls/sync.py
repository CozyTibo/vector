"""Phase 01 — calls connector sync."""

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

def calls_transcript_segment_sort_key(seg: dict[str, Any]) -> tuple[Any, ...]:
    for k in ("segment_index", "ord", "index", "idx"):
        v = seg.get(k)
        if isinstance(v, int):
            return (0, v, "")
        if isinstance(v, str) and v.strip().lstrip("-").isdigit():
            return (0, int(v.strip()), "")
    for k in ("start_ms", "offset_ms", "offset", "startOffset", "start_time_ms", "start"):
        v = seg.get(k)
        if isinstance(v, (int, float)):
            return (1, float(v), k)
        if isinstance(v, str) and v.strip():
            try:
                return (1, float(v.strip()), k)
            except ValueError:
                pass
    txt = seg.get("text") if isinstance(seg.get("text"), str) else seg.get("body")
    return (2, str(txt or ""), "")
def run_calls_connector_sync(
    session: Session,
    settings: Settings,
    *,
    ctx: IngestionSyncContext,
    tenant_id: uuid.UUID,
    connection_id: uuid.UUID,
    run_id: uuid.UUID,
    source_trigger: str,
) -> int:
    class _CallsSyncApiError(RuntimeError):
        pass

    def _calls_get_json(url: str, headers: dict[str, str], params: dict[str, Any] | None = None) -> dict[str, Any]:
        try:
            resp = httpx.get(url, headers=headers, params=params, timeout=60.0)
        except httpx.HTTPError as e:
            raise _CallsSyncApiError(f"calls request failed: {e}") from e
        if resp.status_code >= 400:
            raise _CallsSyncApiError(f"calls http {resp.status_code}: {(resp.text or '')[:300]}")
        try:
            payload = resp.json()
        except ValueError:
            raise _CallsSyncApiError("calls endpoint returned non-json")
        if not isinstance(payload, dict):
            raise _CallsSyncApiError("calls endpoint returned invalid json shape")
        return payload

    def _event_updated_at(event: dict[str, Any]) -> str | None:
        for key in ("updated", "updated_at", "last_modified", "start"):
            val = event.get(key)
            if isinstance(val, str) and val.strip():
                return val
        return None

    def _iso_max(current: str | None, candidate: str | None) -> str | None:
        if not isinstance(candidate, str) or not candidate.strip():
            return current
        if current is None or candidate > current:
            return candidate
        return current

    def _state_map(root: dict[str, Any], key: str) -> dict[str, Any]:
        val = root.get(key)
        return val if isinstance(val, dict) else {}

    def _append_calls_row(
        *,
        resource_type: str,
        external_id: str,
        api_endpoint: str,
        query_params: dict[str, Any],
        source_object_type: str,
        payload_key: str,
        payload_value: dict[str, Any],
    ) -> bool:
        return append_raw(
            session,
            ctx=ctx,
            tenant_id=tenant_id,
            connection_id=connection_id,
            connector=CONNECTION_PROVIDER_CALLS,
            run_id=run_id,
            source_trigger=source_trigger,
            resource_type=resource_type,
            external_id=external_id[:512],
            api_endpoint=api_endpoint[:512],
            query_params=query_params,
            payload_body={
                **core_envelope_fields(
                    connector=CONNECTION_PROVIDER_CALLS,
                    connection_id=connection_id,
                    source_object_type=source_object_type,
                    source_object_id=external_id[:512],
                ),
                payload_key: payload_value,
            },
            http_status=200,
            idempotency_key=idem_key(ctx, run_id, f"calls:{resource_type}:{external_id}"),
        )

    def _ingest_event(event: dict[str, Any], *, endpoint: str, query_params: dict[str, Any]) -> tuple[int, int, int, int, int]:
        inserted = 0
        participants_written = 0
        transcripts_written = 0
        transcript_segments_written = 0
        recordings_written = 0

        event_id = event.get("id")
        if not isinstance(event_id, str) or not event_id:
            return (0, 0, 0, 0, 0)

        if _append_calls_row(
            resource_type="calls.meeting",
            external_id=event_id,
            api_endpoint=endpoint,
            query_params=query_params,
            source_object_type="calls.meeting",
            payload_key="meeting",
            payload_value=event,
        ):
            inserted += 1

        attendees = event.get("attendees")
        if isinstance(attendees, list):
            for idx, attendee in enumerate(attendees):
                if not isinstance(attendee, dict):
                    continue
                raw_email = attendee.get("email")
                email = raw_email.strip().lower() if isinstance(raw_email, str) and raw_email.strip() else f"idx-{idx}"
                participant_external_id = f"{event_id}:{email}"[:512]
                participant_payload = {"meeting_id": event_id, "participant": attendee}
                if _append_calls_row(
                    resource_type="calls.participant",
                    external_id=participant_external_id,
                    api_endpoint=endpoint,
                    query_params=query_params,
                    source_object_type="calls.participant",
                    payload_key="participant_record",
                    payload_value=participant_payload,
                ):
                    inserted += 1
                    participants_written += 1

        transcript = event.get("transcript")
        if not isinstance(transcript, dict):
            ext_props = event.get("extendedProperties")
            private_props = ext_props.get("private") if isinstance(ext_props, dict) else None
            raw = private_props.get("vector_transcript_json") if isinstance(private_props, dict) else None
            if isinstance(raw, str) and raw.strip():
                try:
                    parsed = json.loads(raw)
                    if isinstance(parsed, dict):
                        transcript = parsed
                except ValueError:
                    transcript = None
        if isinstance(transcript, dict):
            transcript_external_id = f"{event_id}:transcript"
            tid = transcript_external_id
            segments = transcript.get("segments")
            seg_list = [s for s in segments if isinstance(s, dict)] if isinstance(segments, list) else []
            seg_sorted = sorted(seg_list, key=calls_transcript_segment_sort_key)
            transcript_enriched = {**transcript, "segments": seg_sorted}
            transcript_payload = {
                "meeting_id": event_id,
                "transcript_id": tid,
                "segment_count": len(seg_sorted),
                "transcript": transcript_enriched,
            }
            if _append_calls_row(
                resource_type="calls.transcript",
                external_id=transcript_external_id,
                api_endpoint=endpoint,
                query_params=query_params,
                source_object_type="calls.transcript",
                payload_key="transcript_record",
                payload_value=transcript_payload,
            ):
                inserted += 1
                transcripts_written += 1
            if seg_sorted:
                for s_idx, seg in enumerate(seg_sorted):
                    seg_external_id = f"{event_id}:seg:{s_idx}"
                    seg_payload = {
                        "meeting_id": event_id,
                        "transcript_id": tid,
                        "segment_index": s_idx,
                        "segment": seg,
                    }
                    if _append_calls_row(
                        resource_type="calls.transcript_segment",
                        external_id=seg_external_id,
                        api_endpoint=endpoint,
                        query_params=query_params,
                        source_object_type="calls.transcript_segment",
                        payload_key="segment_record",
                        payload_value=seg_payload,
                    ):
                        inserted += 1
                        transcript_segments_written += 1

        recording = event.get("recording")
        if not isinstance(recording, dict):
            ext_props = event.get("extendedProperties")
            private_props = ext_props.get("private") if isinstance(ext_props, dict) else None
            raw = private_props.get("vector_recording_json") if isinstance(private_props, dict) else None
            if isinstance(raw, str) and raw.strip():
                try:
                    parsed = json.loads(raw)
                    if isinstance(parsed, dict):
                        recording = parsed
                except ValueError:
                    recording = None
        if isinstance(recording, dict):
            rec_id = recording.get("recording_id")
            rec_suffix = rec_id if isinstance(rec_id, str) and rec_id.strip() else "recording"
            recording_external_id = f"{event_id}:{rec_suffix}"[:512]
            recording_payload = {"meeting_id": event_id, "recording": recording}
            if _append_calls_row(
                resource_type="calls.recording",
                external_id=recording_external_id,
                api_endpoint=endpoint,
                query_params=query_params,
                source_object_type="calls.recording",
                payload_key="recording_record",
                payload_value=recording_payload,
            ):
                inserted += 1
                recordings_written += 1

        return (
            inserted,
            participants_written,
            transcripts_written,
            transcript_segments_written,
            recordings_written,
        )

    scope_ck = ctx.checkpoint_scope_key()
    existing_ckpt = read_checkpoint_state(
        session,
        tenant_id=tenant_id,
        connection_id=connection_id,
        connector=CONNECTION_PROVIDER_CALLS,
        scope_key=scope_ck,
    )
    link = calls_repo.get_calls_connection_for_tenant(session, tenant_id)
    if link is None:
        return generic_scope_ping(
            session,
            ctx=ctx,
            tenant_id=tenant_id,
            connection_id=connection_id,
            connector=CONNECTION_PROVIDER_CALLS,
            run_id=run_id,
            source_trigger=source_trigger,
            label="no_calls_detail",
        )
    token = link.detail.access_token
    n_ins = 0
    meetings_written = 0
    participants_written = 0
    transcripts_written = 0
    transcript_segments_written = 0
    recordings_written = 0
    pages_fetched = 0
    budget_exhausted = False
    start_t = time.monotonic()

    streams_existing = checkpoint_streams_for_mode(existing_ckpt, ctx.sync_mode)
    calls_existing = (
        streams_existing.get("calls")
        if isinstance(streams_existing, dict) and isinstance(streams_existing.get("calls"), dict)
        else {}
    )
    events_existing = _state_map(calls_existing, "events")
    next_cursor_raw = events_existing.get("next_cursor")
    next_cursor = next_cursor_raw if isinstance(next_cursor_raw, str) and next_cursor_raw.strip() else None
    watermark_raw = events_existing.get("updated_watermark")
    updated_watermark = watermark_raw if isinstance(watermark_raw, str) and watermark_raw.strip() else None
    max_seen_updated = updated_watermark

    headers = {} if settings.vector_use_mock_connectors else {"Authorization": f"Bearer {token}"}
    calendar_base = settings.calls_google_calendar_events_base_url().rstrip("/")
    calendar_id = "primary"
    page_token = next_cursor
    for _ in range(settings.cortex_calls_events_max_pages_per_sync):
        params: dict[str, Any] = {
            "singleEvents": "true",
            "maxResults": settings.cortex_calls_events_page_size,
            "orderBy": "updated",
        }
        if isinstance(page_token, str) and page_token:
            params["pageToken"] = page_token
        if ctx.checkpoint_sync_mode == "incremental" and isinstance(updated_watermark, str) and updated_watermark:
            params["updatedMin"] = updated_watermark

        endpoint = f"{calendar_base}/calendars/{calendar_id}/events"
        data = _calls_get_json(endpoint, headers=headers, params=params)
        page_items = [ev for ev in data.get("items", []) if isinstance(ev, dict)]
        pages_fetched += 1
        for event in page_items:
            event_updated = _event_updated_at(event)
            max_seen_updated = _iso_max(max_seen_updated, event_updated)
            inserted, p_cnt, t_cnt, s_cnt, r_cnt = _ingest_event(
                event,
                endpoint=endpoint,
                query_params={"pageToken": page_token or "", "updatedMin": params.get("updatedMin", "")},
            )
            if inserted > 0:
                meetings_written += 1
            n_ins += inserted
            participants_written += p_cnt
            transcripts_written += t_cnt
            transcript_segments_written += s_cnt
            recordings_written += r_cnt
        raw_next = data.get("nextPageToken")
        page_token = raw_next if isinstance(raw_next, str) and raw_next else None
        next_cursor = page_token
        if page_token is None:
            break
        if time.monotonic() - start_t >= settings.cortex_calls_time_budget_seconds:
            budget_exhausted = True
            break

    provider_label = link.detail.provider_email or link.detail.provider_user_id or "calls_connected"
    if append_raw(
        session,
        ctx=ctx,
        tenant_id=tenant_id,
        connection_id=connection_id,
        connector=CONNECTION_PROVIDER_CALLS,
        run_id=run_id,
        source_trigger=source_trigger,
        resource_type="calls.scope_ping",
        external_id=str(link.connection.id),
        api_endpoint="internal://calls/scope_ping",
        query_params={},
        payload_body={
            **core_envelope_fields(
                connector=CONNECTION_PROVIDER_CALLS,
                connection_id=connection_id,
                source_object_type="calls.scope_ping",
                source_object_id=str(link.connection.id),
            ),
            "provider_user_id": link.detail.provider_user_id,
            "provider_email": link.detail.provider_email,
            "connectivity": {"label": provider_label},
        },
        http_status=200,
        idempotency_key=idem_key(ctx, run_id, f"calls:scope_ping:{link.connection.id}"),
    ):
        n_ins += 1

    upsert_checkpoint(
        session,
        tenant_id=tenant_id,
        connection_id=connection_id,
        connector=CONNECTION_PROVIDER_CALLS,
        scope_key=scope_ck,
        patch={
            "last_incremental_at": utc_now().isoformat(),
            "calls_meetings_written": meetings_written,
            "calls_participants_written": participants_written,
            "calls_transcripts_written": transcripts_written,
            "calls_transcript_segments_written": transcript_segments_written,
            "calls_recordings_written": recordings_written,
            "streams": {
                "calls": {
                    "events": {
                        "cursor_owner": "calls.meeting",
                        "next_cursor": next_cursor,
                        "pages_fetched_last_run": pages_fetched,
                        "rows_seen_last_run": meetings_written,
                        "updated_watermark": max_seen_updated,
                    },
                    "participants": {
                        "cursor_owner": "calls.participant",
                        "rows_seen_last_run": participants_written,
                    },
                    "transcripts": {
                        "cursor_owner": "calls.transcript",
                        "rows_seen_last_run": transcripts_written,
                    },
                    "transcript_segments": {
                        "cursor_owner": "calls.transcript_segment",
                        "rows_seen_last_run": transcript_segments_written,
                    },
                    "recordings": {
                        "cursor_owner": "calls.recording",
                        "rows_seen_last_run": recordings_written,
                    },
                    "scope_ping": {
                        "cursor_owner": "calls.scope_ping",
                        "provider_email": link.detail.provider_email,
                    },
                    "resume_required": budget_exhausted,
                    "time_budget_seconds": settings.cortex_calls_time_budget_seconds,
                }
            },
        },
        sync_mode=ctx.checkpoint_sync_mode,
    )
    return n_ins
