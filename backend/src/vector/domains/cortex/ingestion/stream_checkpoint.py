"""Checkpoint stream helpers — introduced_at, admin summaries, operator stream reset."""

from __future__ import annotations

from copy import deepcopy
from datetime import UTC, datetime
from typing import Any

from vector.domains.cortex.ingestion.checkpoint_contract import (
    CHECKPOINT_SCHEMA_VERSION,
    merge_monotonic_connector_state,
)


def utc_now_iso() -> str:
    return datetime.now(tz=UTC).isoformat()


def ensure_stream_introduced_at(stream_patch: dict[str, Any], *, introduced_at: str | None = None) -> dict[str, Any]:
    """Set ``introduced_at`` once when a stream first ships."""
    out = deepcopy(stream_patch)
    if isinstance(out.get("introduced_at"), str) and out["introduced_at"].strip():
        return out
    out["introduced_at"] = (introduced_at or utc_now_iso()).strip()
    return out


def _stream_blob(state: dict[str, Any], connector: str, stream_key: str) -> dict[str, Any]:
    streams = state.get("streams")
    if not isinstance(streams, dict):
        return {}
    conn = streams.get(connector)
    if not isinstance(conn, dict):
        return {}
    blob = conn.get(stream_key)
    return blob if isinstance(blob, dict) else {}


def summarize_connector_streams(state: dict[str, Any], connector: str) -> list[dict[str, Any]]:
    """Flatten per-stream checkpoint blobs for admin read models."""
    streams = state.get("streams")
    if not isinstance(streams, dict):
        return []
    conn = streams.get(connector)
    if not isinstance(conn, dict):
        return []
    out: list[dict[str, Any]] = []
    for stream_key in sorted(conn.keys()):
        if stream_key in ("resume_required", "time_budget_seconds"):
            continue
        blob = conn.get(stream_key)
        if not isinstance(blob, dict):
            continue
        out.append(
            {
                "stream_key": stream_key,
                "cursor_owner": blob.get("cursor_owner"),
                "next_cursor": blob.get("next_cursor"),
                "backfill_complete": bool(blob.get("backfill_complete")),
                "introduced_at": blob.get("introduced_at"),
                "last_ok_at": blob.get("last_ok_at"),
                "pages_fetched_last_run": blob.get("pages_fetched_last_run"),
                "rows_seen_last_run": blob.get("rows_seen_last_run"),
            },
        )
    meta = state.get("meta")
    if isinstance(meta, dict):
        depth = meta.get("exhaust_depth")
        if isinstance(depth, str) and depth.strip():
            for row in out:
                row["connector_exhaust_depth"] = depth.strip()
    return out


def reset_stream_checkpoint(
    state: dict[str, Any],
    *,
    connector: str,
    stream_key: str,
) -> tuple[dict[str, Any], bool]:
    """Clear one stream blob under ``streams.{connector}``; preserve siblings and meta."""
    migrated = deepcopy(state)
    if migrated.get("checkpoint_schema_version") != CHECKPOINT_SCHEMA_VERSION:
        migrated["checkpoint_schema_version"] = CHECKPOINT_SCHEMA_VERSION
    streams = migrated.get("streams")
    if not isinstance(streams, dict):
        streams = {}
        migrated["streams"] = streams
    conn = streams.get(connector)
    if not isinstance(conn, dict) or stream_key not in conn:
        return migrated, False
    conn = deepcopy(conn)
    prior = conn.pop(stream_key)
    conn[f"{stream_key}__reset"] = {
        "reset_at": utc_now_iso(),
        "prior_keys": sorted(prior.keys()) if isinstance(prior, dict) else [],
    }
    streams[connector] = conn
    meta = migrated.get("meta")
    if not isinstance(meta, dict):
        meta = {}
        migrated["meta"] = meta
    meta["last_stream_reset_at"] = utc_now_iso()
    meta["last_stream_reset"] = {"connector": connector, "stream_key": stream_key}
    return migrated, True


def apply_stream_reset_to_db_state(
    existing_state: dict[str, Any],
    *,
    connector: str,
    stream_key: str,
) -> dict[str, Any]:
    """Apply stream reset by replacing ``streams.{connector}`` (deep merge cannot delete keys)."""
    streams = existing_state.get("streams")
    if not isinstance(streams, dict):
        return existing_state
    conn = streams.get(connector)
    if not isinstance(conn, dict) or stream_key not in conn:
        return existing_state
    reset_state, changed = reset_stream_checkpoint(existing_state, connector=connector, stream_key=stream_key)
    if not changed:
        return existing_state
    out = merge_monotonic_connector_state(existing_state, {"meta": reset_state.get("meta", {})})
    new_streams = reset_state.get("streams")
    if isinstance(new_streams, dict) and isinstance(new_streams.get(connector), dict):
        out["streams"] = deepcopy(streams)
        out["streams"][connector] = deepcopy(new_streams[connector])
    return out
