"""Compatibility shim — prefer ``sync_router`` and ``connectors.*`` (P2 step 11)."""

from __future__ import annotations

import httpx

from vector.domains.cortex.ingestion.connectors.github.sync import (
    ensure_github_workflow_run_repository_metadata,
)
from vector.domains.cortex.ingestion.connectors.slack.sync import (
    slack_channel_history_sync_mode,
    slack_history_pages_done,
    slack_history_time_bounds,
)
from vector.domains.cortex.ingestion.sync_router import execute_connector_sync
from vector.domains.cortex.ingestion.sync_shared import append_raw

_slack_channel_history_sync_mode = slack_channel_history_sync_mode
_slack_history_pages_done = slack_history_pages_done
_slack_history_time_bounds = slack_history_time_bounds
_append_raw = append_raw

__all__ = [
    "execute_connector_sync",
    "ensure_github_workflow_run_repository_metadata",
    "append_raw",
    "httpx",
    "_append_raw",
    "_slack_channel_history_sync_mode",
    "_slack_history_pages_done",
    "_slack_history_time_bounds",
]
