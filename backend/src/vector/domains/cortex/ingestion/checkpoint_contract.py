"""Phase 01 Step 7 — schema-versioned checkpoint contract with deep merge + recovery hooks."""

from __future__ import annotations

import json
import logging
from copy import deepcopy
from datetime import UTC, datetime
from typing import Any

_logger = logging.getLogger("app")

CHECKPOINT_SCHEMA_VERSION = 2
CHECKPOINT_MODE_INCREMENTAL = "incremental"
CHECKPOINT_MODE_BACKFILL = "backfill"
_KNOWN_MODES = frozenset({CHECKPOINT_MODE_INCREMENTAL, CHECKPOINT_MODE_BACKFILL})

_MONOTONIC_NUMERIC_KEYS = frozenset(
    {
        "repos_fetched",
        "total_count_hint",
        "github_installation_repos_pages",
        "github_pull_requests_written",
        "github_reviews_written",
        "github_review_comments_written",
        "github_issue_comments_written",
        "github_commits_written",
        "github_check_runs_written",
        "github_workflow_runs_written",
        "github_deployments_written",
        "github_deployment_statuses_written",
        "github_branches_written",
        "github_tags_written",
        "linear_issues_fetched",
        "slack_user_pages",
        "slack_user_members_seen",
        "slack_conversation_pages",
        "slack_conversations_seen",
        "slack_messages_seen",
        "slack_message_replies_seen",
        "slack_reactions_seen",
        "slack_files_seen",
    }
)


def _utc_now_iso() -> str:
    return datetime.now(tz=UTC).isoformat()


def parse_checkpoint_iso_timestamp(value: object) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    raw = value.strip().replace("Z", "+00:00")
    try:
        dt = datetime.fromisoformat(raw)
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt


def _monotonic_scalar_merge(existing: Any, patch: Any) -> Any:
    if isinstance(existing, str) and isinstance(patch, str):
        old_dt = parse_checkpoint_iso_timestamp(existing)
        new_dt = parse_checkpoint_iso_timestamp(patch)
        if old_dt is not None and new_dt is not None:
            if new_dt < old_dt:
                return existing
            return patch
    try:
        old_n = int(existing)
        new_n = int(patch)
    except (TypeError, ValueError):
        return patch
    return max(old_n, new_n)


def _deep_merge(existing: dict[str, Any], patch: dict[str, Any]) -> dict[str, Any]:
    out = deepcopy(existing)
    for key, value in patch.items():
        if key == "last_incremental_at":
            out[key] = _monotonic_scalar_merge(out.get(key), value)
            continue
        if key in _MONOTONIC_NUMERIC_KEYS:
            out[key] = _monotonic_scalar_merge(out.get(key), value)
            continue
        old_val = out.get(key)
        if isinstance(old_val, dict) and isinstance(value, dict):
            out[key] = _deep_merge(old_val, value)
            continue
        out[key] = deepcopy(value)
    return out


def _legacy_flat_from_state(state: dict[str, Any]) -> dict[str, Any]:
    reserved = {"checkpoint_schema_version", "modes", "streams", "meta"}
    return {k: deepcopy(v) for k, v in state.items() if k not in reserved}


def _normalize_mode_name(mode: str) -> str:
    if mode == "backfill":
        return CHECKPOINT_MODE_BACKFILL
    # replay/recovery/targeted all write through incremental lane; replay stays isolated by scope_key.
    return CHECKPOINT_MODE_INCREMENTAL


def _ensure_v2_shape(state: dict[str, Any]) -> dict[str, Any]:
    out = deepcopy(state)
    if out.get("checkpoint_schema_version") != CHECKPOINT_SCHEMA_VERSION:
        out["checkpoint_schema_version"] = CHECKPOINT_SCHEMA_VERSION
    modes = out.get("modes")
    if not isinstance(modes, dict):
        modes = {}
    for m in _KNOWN_MODES:
        lane = modes.get(m)
        if not isinstance(lane, dict):
            lane = {}
        lane.setdefault("watermarks", {})
        lane.setdefault("streams", {})
        modes[m] = lane
    out["modes"] = modes
    streams = out.get("streams")
    if not isinstance(streams, dict):
        streams = {}
    out["streams"] = streams
    meta = out.get("meta")
    if not isinstance(meta, dict):
        meta = {}
    out["meta"] = meta
    return out


def migrate_checkpoint_state(existing: dict[str, Any] | None) -> tuple[dict[str, Any], bool]:
    """Return a v2 checkpoint state and whether migration happened.

    Corrupted/non-dict states fail closed into a fresh v2 state with recovery metadata.
    """
    if existing is None:
        return _ensure_v2_shape({}), False
    if not isinstance(existing, dict):
        repaired = _ensure_v2_shape({})
        repaired["meta"]["recovery"] = {
            "status": "reset_invalid_state",
            "reason": "state_not_dict",
            "at": _utc_now_iso(),
        }
        return repaired, True

    maybe_v = existing.get("checkpoint_schema_version")
    if maybe_v == CHECKPOINT_SCHEMA_VERSION:
        return _ensure_v2_shape(existing), False

    legacy_flat = _legacy_flat_from_state(existing)
    migrated = _ensure_v2_shape(
        {
            "checkpoint_schema_version": CHECKPOINT_SCHEMA_VERSION,
            "modes": {
                CHECKPOINT_MODE_INCREMENTAL: deepcopy(legacy_flat),
                CHECKPOINT_MODE_BACKFILL: {},
            },
            "streams": {},
            "meta": {
                "migrated_from_legacy": True,
                "migrated_at": _utc_now_iso(),
            },
        }
    )
    # Keep legacy top-level projection for backward compatibility while v2 readers migrate.
    migrated.update(legacy_flat)
    return migrated, True


def checkpoint_last_incremental_at(state: dict[str, Any]) -> str | None:
    """Read incremental watermark from v2 lane first, then legacy top-level fallback."""
    modes = state.get("modes")
    if isinstance(modes, dict):
        inc = modes.get(CHECKPOINT_MODE_INCREMENTAL)
        if isinstance(inc, dict):
            ts = inc.get("last_incremental_at")
            if isinstance(ts, str) and ts.strip():
                return ts.strip()
    raw = state.get("last_incremental_at")
    if isinstance(raw, str) and raw.strip():
        return raw.strip()
    return None


def merge_monotonic_connector_state(
    existing: dict[str, Any],
    patch: dict[str, Any],
    *,
    sync_mode: str = CHECKPOINT_MODE_INCREMENTAL,
) -> dict[str, Any]:
    """Merge patch into schema-versioned checkpoint state.

    Step 7 behavior:
    - migrate legacy flat state to v2 checkpoint schema;
    - deep-merge known nested maps;
    - keep incremental/backfill cursor lanes isolated by sync mode;
    - keep a legacy top-level projection for older readers.
    """
    current, migrated = migrate_checkpoint_state(existing)
    writer_mode = _normalize_mode_name(sync_mode)

    out = _deep_merge(current, patch)
    out = _ensure_v2_shape(out)
    lane_existing = out["modes"].get(writer_mode, {})
    lane_merged = _deep_merge(lane_existing, patch)
    out["modes"][writer_mode] = lane_merged

    # Backward-compatible projection for existing readers.
    legacy_projection = _legacy_flat_from_state(lane_merged)
    out.update(legacy_projection)
    out["last_incremental_at"] = checkpoint_last_incremental_at(out)

    out["meta"]["last_writer_mode"] = writer_mode
    out["meta"]["last_merged_at"] = _utc_now_iso()
    if migrated:
        out["meta"]["migration_observed_at"] = _utc_now_iso()

    # Side-table escape hatch signal (advisory only in Step 7).
    try:
        encoded_len = len(json.dumps(out, default=str, sort_keys=True).encode())
    except Exception:  # pragma: no cover - defensive
        encoded_len = 0
    if encoded_len > 100_000:
        out["meta"]["side_table_escape_hatch_recommended"] = True
        out["meta"]["side_table_escape_hatch_reason"] = "checkpoint_state_size_gt_100kb"
        _logger.warning("ingestion checkpoint: state exceeded 100KB; side-table escape hatch recommended")
    return out
