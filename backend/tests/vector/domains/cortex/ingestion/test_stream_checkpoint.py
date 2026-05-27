"""Stream checkpoint helpers — introduced_at, summaries, reset."""

from __future__ import annotations

from vector.domains.cortex.ingestion.stream_checkpoint import (
    apply_stream_reset_to_db_state,
    ensure_stream_introduced_at,
    reset_stream_checkpoint,
    summarize_connector_streams,
)


def test_ensure_stream_introduced_at_sets_once() -> None:
    blob = ensure_stream_introduced_at({}, introduced_at="2026-05-28T00:00:00+00:00")
    assert blob["introduced_at"] == "2026-05-28T00:00:00+00:00"
    again = ensure_stream_introduced_at(blob, introduced_at="2026-06-01T00:00:00+00:00")
    assert again["introduced_at"] == "2026-05-28T00:00:00+00:00"


def test_summarize_connector_streams() -> None:
    state = {
        "streams": {
            "linear": {
                "issues": {
                    "cursor_owner": "linear.issue",
                    "backfill_complete": True,
                    "introduced_at": "2026-05-01T00:00:00+00:00",
                },
            },
        },
        "meta": {"exhaust_depth": "deepening"},
    }
    rows = summarize_connector_streams(state, "linear")
    assert len(rows) == 1
    assert rows[0]["stream_key"] == "issues"
    assert rows[0]["backfill_complete"] is True
    assert rows[0]["connector_exhaust_depth"] == "deepening"


def test_reset_stream_checkpoint_clears_target_only() -> None:
    state = {
        "checkpoint_schema_version": 2,
        "streams": {
            "github": {
                "issues": {"next_cursor": "abc"},
                "installation_repositories": {"backfill_complete": True},
            },
        },
    }
    merged, changed = reset_stream_checkpoint(state, connector="github", stream_key="issues")
    assert changed is True
    gh = merged["streams"]["github"]
    assert "issues" not in gh
    assert "installation_repositories" in gh
    assert "issues__reset" in gh


def test_apply_stream_reset_merges_into_existing() -> None:
    state = {
        "checkpoint_schema_version": 2,
        "last_incremental_at": "2026-05-08T10:00:00+00:00",
        "streams": {"linear": {"issues": {"next_cursor": "x"}}},
    }
    merged = apply_stream_reset_to_db_state(state, connector="linear", stream_key="issues")
    assert merged["last_incremental_at"] == "2026-05-08T10:00:00+00:00"
    assert "issues" not in merged["streams"]["linear"]
