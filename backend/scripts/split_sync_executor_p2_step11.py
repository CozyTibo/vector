#!/usr/bin/env python3
"""One-off splitter: sync_executor.py → connectors/* + sync_shared + router (P2 step 11)."""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src/vector/domains/cortex/ingestion/sync_executor.py"
OUT = ROOT / "src/vector/domains/cortex/ingestion"
BACKUP = ROOT / "src/vector/domains/cortex/ingestion/sync_executor.py.bak"


def _lines(path: Path) -> list[str]:
    return path.read_text(encoding="utf-8").splitlines(keepends=True)


def _slice(lines: list[str], start: int, end: int) -> str:
    return "".join(lines[start - 1 : end])


_RENAMES = [
    ("def _utc_now", "def utc_now"),
    ("def _idem_key", "def idem_key"),
    ("def _tag_replay_payload", "def tag_replay_payload"),
    ("def _hash_payload", "def hash_payload"),
    ("def _append_raw", "def append_raw"),
    ("def _resolve_connection", "def resolve_connection"),
    ("def _upsert_checkpoint", "def upsert_checkpoint"),
    ("def _read_checkpoint_state", "def read_checkpoint_state"),
    ("def _checkpoint_streams_for_mode", "def checkpoint_streams_for_mode"),
    ("_utc_now()", "utc_now()"),
    ("_idem_key(", "idem_key("),
    ("_tag_replay_payload(", "tag_replay_payload("),
    ("_hash_payload(", "hash_payload("),
    ("_append_raw(", "append_raw("),
    ("_resolve_connection(", "resolve_connection("),
    ("_upsert_checkpoint(", "upsert_checkpoint("),
    ("_read_checkpoint_state(", "read_checkpoint_state("),
    ("_checkpoint_streams_for_mode(", "checkpoint_streams_for_mode("),
]


def _apply_renames(text: str) -> str:
    for old, new in _RENAMES:
        text = text.replace(old, new)
    return text


def main() -> None:
    if not BACKUP.exists():
        BACKUP.write_text(SRC.read_text(encoding="utf-8"), encoding="utf-8")
    lines = _lines(BACKUP)
    conn = OUT / "connectors"
    conn.mkdir(parents=True, exist_ok=True)

    shared_parts = [
        _slice(lines, 1, 451),
        _slice(lines, 502, 725),
        _slice(lines, 3155, 3190),
    ]
    shared_text = _apply_renames("".join(shared_parts))
    shared_text = shared_text.replace(
        '"""Phase 01 Step 1–3 — connector sync execution (run + raw persistence + checkpoint + replay)."""\n\n',
        '"""Shared ingestion sync helpers (checkpoint, raw persistence, connections)."""\n\n',
    )
    (OUT / "sync_shared.py").write_text(shared_text, encoding="utf-8")

    shared_imports = """
from vector.domains.cortex.ingestion.sync_shared import (
    append_raw,
    checkpoint_streams_for_mode,
    hash_payload,
    idem_key,
    read_checkpoint_state,
    tag_replay_payload,
    upsert_checkpoint,
    utc_now,
)
"""

    def write_connector(name: str, func_name: str, old_name: str, parts: list[str]) -> None:
        pkg = conn / name
        pkg.mkdir(exist_ok=True)
        body = _apply_renames("".join(parts))
        body = body.replace(f"def {old_name}(", f"def {func_name}(")
        body = re.sub(r"^def _([a-z_]+)\(", r"def \1(", body, flags=re.MULTILINE)
        body = body.replace("_pick_github_repos_round_robin", "pick_github_repos_round_robin")
        body = body.replace("_pick_slack_channels_round_robin", "pick_slack_channels_round_robin")
        body = body.replace("_slack_channel_history_sync_mode", "slack_channel_history_sync_mode")
        body = body.replace("_slack_history_pages_done", "slack_history_pages_done")
        body = body.replace("_slack_history_time_bounds", "slack_history_time_bounds")
        body = body.replace("_slack_ts_value", "slack_ts_value")
        body = body.replace("_calls_transcript_segment_sort_key", "calls_transcript_segment_sort_key")
        (pkg / "sync.py").write_text(body, encoding="utf-8")
        (pkg / "__init__.py").write_text(
            f'from vector.domains.cortex.ingestion.connectors.{name}.sync import {func_name}\n\n__all__ = ["{func_name}"]\n',
            encoding="utf-8",
        )

    write_connector(
        "github",
        "run_github_connector_sync",
        "_github_sync",
        [_slice(lines, 452, 501), _slice(lines, 746, 2541), _slice(lines, 3284, 3299)],
    )
    write_connector("linear", "run_linear_connector_sync", "_linear_sync", [_slice(lines, 2542, 3153)])
    write_connector(
        "slack",
        "run_slack_connector_sync",
        "_slack_sync",
        [_slice(lines, 3192, 3282), _slice(lines, 3302, 3998)],
    )
    write_connector("notion", "run_notion_connector_sync", "_notion_sync", [_slice(lines, 3999, 4650)])
    write_connector(
        "calls",
        "run_calls_connector_sync",
        "_calls_sync",
        [_slice(lines, 726, 743), _slice(lines, 4651, 5034)],
    )

    router_text = _apply_renames(_slice(lines, 5037, 5249))
    router_text = router_text.replace("_github_sync(", "run_github_connector_sync(")
    router_text = router_text.replace("_linear_sync(", "run_linear_connector_sync(")
    router_text = router_text.replace("_slack_sync(", "run_slack_connector_sync(")
    router_text = router_text.replace("_notion_sync(", "run_notion_connector_sync(")
    router_text = router_text.replace("_calls_sync(", "run_calls_connector_sync(")
    router_header = '''"""Thin connector sync router (P2 step 11)."""

from __future__ import annotations

import logging
import uuid
from typing import Any

from sqlalchemy.orm import Session

from vector.domains.cortex.connectors.provider_keys import (
    CONNECTION_PROVIDER_CALLS,
    CONNECTION_PROVIDER_GITHUB,
    CONNECTION_PROVIDER_LINEAR,
    CONNECTION_PROVIDER_NOTION,
    CONNECTION_PROVIDER_SLACK,
)
from vector.domains.cortex.ingestion.connectors.calls.sync import run_calls_connector_sync
from vector.domains.cortex.ingestion.connectors.github.sync import run_github_connector_sync
from vector.domains.cortex.ingestion.connectors.linear.sync import run_linear_connector_sync
from vector.domains.cortex.ingestion.connectors.notion.sync import run_notion_connector_sync
from vector.domains.cortex.ingestion.connectors.slack.sync import run_slack_connector_sync
from vector.domains.cortex.ingestion.sync_context import IngestionSyncContext
from vector.domains.cortex.ingestion.sync_shared import (
    RUN_COMPLETED,
    RUN_FAILED,
    RUN_RUNNING,
    resolve_connection,
    upsert_checkpoint,
    utc_now,
)
from vector.infrastructure.db.models.ingestion_run import IngestionRun
from vector.infrastructure.observability.ingestion_tasks import (
    PHASE_STEP1,
    PHASE_STEP3,
    PHASE_STEP5,
    log_ingestion_event,
)
from vector.settings import Settings

_logger = logging.getLogger("app")

'''
    (conn / "__init__.py").write_text(
        '"""Per-connector ingestion sync adapters (P2 step 11)."""\n',
        encoding="utf-8",
    )
    (OUT / "sync_router.py").write_text(router_header + router_text, encoding="utf-8")

    shim = '''"""Compatibility shim — prefer ``sync_router`` and ``connectors.*`` (P2 step 11)."""

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
    "_append_raw",
    "_slack_channel_history_sync_mode",
    "_slack_history_pages_done",
    "_slack_history_time_bounds",
]
'''
    SRC.write_text(shim, encoding="utf-8")
    print("split complete — backup at sync_executor.py.bak")


if __name__ == "__main__":
    main()
