"""Organizational exhaust coverage — static registry mirrored from docs.

Keep **in lockstep** with ``DOCS/cortex/connectors/connector-exhaust-matrix.md``.
Admin UI and ``GET …/cortex/ingestion/exhaust-coverage`` read from here so
operators never confuse substrate maturity with exhaust depth.
"""

from __future__ import annotations

import uuid
from typing import Any, Literal

Coverage = Literal["none", "partial", "full"]
Historical = Literal["none", "partial", "full", "n/a"]
Replay = Literal["no", "partial", "yes"]
Canon = Literal["none", "partial", "full"]
RowStatus = Literal["missing", "in_progress", "active"]
ConnectorId = Literal["calls", "github", "linear", "notion", "slack"]


def _row(
    resource_type: str,
    *,
    coverage: Coverage,
    historical: Historical,
    replay: Replay,
    canonicalization: Canon,
    status: RowStatus,
    notes: str | None = None,
) -> dict[str, Any]:
    d: dict[str, Any] = {
        "resource_type": resource_type,
        "coverage": coverage,
        "historical": historical,
        "replay": replay,
        "canonicalization": canonicalization,
        "status": status,
    }
    if notes:
        d["notes"] = notes
    return d


def _level_title(level: int) -> str:
    titles = {
        0: "Level 0 — Connectivity only",
        1: "Level 1 — Ping / shallow fetch",
        2: "Level 2 — Incremental sync operational",
        3: "Level 3 — Historical backfill operational",
        4: "Level 4 — Replay-safe deep ingestion",
        5: "Level 5 — Canonicalization-compatible completeness",
        6: "Level 6 — Operationally trusted organizational exhaust",
    }
    return titles.get(level, f"Level {level}")


def _missing_types(resources: list[dict[str, Any]]) -> list[str]:
    out: list[str] = []
    for r in resources:
        if r.get("status") != "missing":
            continue
        rt = str(r["resource_type"])
        if rt.endswith(".scope_ping") or rt in ("viewer_ping",):
            continue
        out.append(rt)
    return out


def _connector_bundle(
    connector: ConnectorId,
    *,
    maturity_level: int,
    historical_backfill_summary: str,
    replay_compatibility_summary: str,
    canonicalization_summary: str,
    resources: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "connector": connector,
        "maturity_level": maturity_level,
        "maturity_level_title": _level_title(maturity_level),
        "historical_backfill_summary": historical_backfill_summary,
        "replay_compatibility_summary": replay_compatibility_summary,
        "canonicalization_summary": canonicalization_summary,
        "missing_resource_types": _missing_types(resources),
        "resources": resources,
    }


def _slack() -> dict[str, Any]:
    resources = [
        _row(
            "slack.user",
            coverage="partial",
            historical="partial",
            replay="partial",
            canonicalization="none",
            status="in_progress",
            notes="users.list with cursor pagination; one raw row per member.",
        ),
        _row(
            "slack.conversation",
            coverage="partial",
            historical="partial",
            replay="partial",
            canonicalization="none",
            status="in_progress",
            notes="conversations.list (public+private, non-archived); not yet DMs / MPIMs.",
        ),
        _row(
            "slack.message",
            coverage="full",
            historical="partial",
            replay="partial",
            canonicalization="none",
            status="in_progress",
            notes="conversations.history paginated with per-channel checkpoint cursors + ring resume; incremental/backfill lanes use Step 7 checkpoint schema.",
        ),
        _row(
            "slack.message_reply",
            coverage="partial",
            historical="partial",
            replay="partial",
            canonicalization="none",
            status="in_progress",
            notes="conversations.replies ingested for discovered thread roots with per-thread cursor continuity.",
        ),
        _row(
            "slack.thread",
            coverage="partial",
            historical="partial",
            replay="partial",
            canonicalization="none",
            status="in_progress",
            notes="First-class thread container emitted for each history message with reply_count>0 (channel+thread_ts identity).",
        ),
        _row(
            "slack.reaction",
            coverage="partial",
            historical="partial",
            replay="partial",
            canonicalization="none",
            status="in_progress",
            notes="Message-embedded reactions ingested from conversations.history pages.",
        ),
        _row("edits", coverage="none", historical="none", replay="no", canonicalization="none", status="missing"),
        _row("pins", coverage="none", historical="none", replay="no", canonicalization="none", status="missing"),
        _row(
            "slack.file",
            coverage="partial",
            historical="partial",
            replay="partial",
            canonicalization="none",
            status="in_progress",
            notes="Message-embedded file metadata ingested from conversations.history pages.",
        ),
        _row("bookmarks", coverage="none", historical="none", replay="no", canonicalization="none", status="missing"),
        _row("canvases", coverage="none", historical="none", replay="no", canonicalization="none", status="missing"),
        _row(
            "slack.scope_ping",
            coverage="partial",
            historical="n/a",
            replay="partial",
            canonicalization="none",
            status="in_progress",
            notes="Used only when Slack connection detail is missing (no bot token).",
        ),
    ]
    return _connector_bundle(
        "slack",
        maturity_level=2,
        historical_backfill_summary="Per-channel history + thread cursors with checkpointed resume; channel ring and time budget drive progressive deepening.",
        replay_compatibility_summary="Per-resource idempotency keys; replay lane uses replay-scoped keys.",
        canonicalization_summary="Partial — user/channel/message/reply/reaction/file payloads present; deeper edit/pin/bookmark streams pending.",
        resources=resources,
    )


def _github() -> dict[str, Any]:
    resources = [
        _row(
            "github.installation_repositories",
            coverage="partial",
            historical="partial",
            replay="partial",
            canonicalization="none",
            status="in_progress",
            notes="Paginated GET /installation/repositories up to CORTEX_GITHUB_INSTALLATION_REPOS_MAX_PAGES per sync.",
        ),
        _row(
            "github.repository",
            coverage="partial",
            historical="partial",
            replay="partial",
            canonicalization="none",
            status="in_progress",
            notes="One raw row per repo returned across paginated installation scan.",
        ),
        _row(
            "github.pull_request",
            coverage="full",
            historical="partial",
            replay="partial",
            canonicalization="none",
            status="in_progress",
            notes="Paginated /repos/{owner}/{repo}/pulls with per-repo checkpoint pages; bounded by per-run page budgets.",
        ),
        _row(
            "github.issue",
            coverage="partial",
            historical="partial",
            replay="partial",
            canonicalization="none",
            status="in_progress",
            notes="Non-PR rows from REST /repos/{owner}/{repo}/issues (pull_request field absent).",
        ),
        _row(
            "github.issue_timeline_event",
            coverage="partial",
            historical="partial",
            replay="partial",
            canonicalization="none",
            status="in_progress",
            notes="Paginated GET /repos/{owner}/{repo}/issues/{n}/timeline for standalone issues (per issue row).",
        ),
        _row(
            "github.pull_request_timeline_event",
            coverage="partial",
            historical="partial",
            replay="partial",
            canonicalization="none",
            status="in_progress",
            notes="Same timeline endpoint scoped per pull request number after each PR row is ingested.",
        ),
        _row(
            "github.pull_request_review",
            coverage="partial",
            historical="partial",
            replay="partial",
            canonicalization="none",
            status="in_progress",
            notes="Paginated /pulls/{n}/reviews for ingested PRs.",
        ),
        _row(
            "github.pull_request_review_comment",
            coverage="partial",
            historical="partial",
            replay="partial",
            canonicalization="none",
            status="in_progress",
            notes="Paginated /pulls/{n}/comments for ingested PRs.",
        ),
        _row(
            "github.issue_comment",
            coverage="partial",
            historical="partial",
            replay="partial",
            canonicalization="none",
            status="in_progress",
            notes="Paginated /issues/{n}/comments for ingested PRs.",
        ),
        _row(
            "github.commit",
            coverage="partial",
            historical="partial",
            replay="partial",
            canonicalization="none",
            status="in_progress",
            notes="Paginated /repos/{owner}/{repo}/commits with per-repo cursor continuity.",
        ),
        _row(
            "commits",
            coverage="partial",
            historical="partial",
            replay="partial",
            canonicalization="none",
            status="in_progress",
            notes="Compatibility alias for github.commit in existing admin snapshots/tests.",
        ),
        _row(
            "github.check_run",
            coverage="partial",
            historical="partial",
            replay="partial",
            canonicalization="none",
            status="in_progress",
            notes="Paginated check-runs for PR head SHAs.",
        ),
        _row(
            "github.workflow_run",
            coverage="partial",
            historical="partial",
            replay="partial",
            canonicalization="none",
            status="in_progress",
            notes="Paginated /actions/runs with per-repo cursor continuity.",
        ),
        _row(
            "github.deployment",
            coverage="partial",
            historical="partial",
            replay="partial",
            canonicalization="none",
            status="in_progress",
            notes="Paginated /deployments with per-repo cursor continuity.",
        ),
        _row(
            "github.deployment_status",
            coverage="partial",
            historical="partial",
            replay="partial",
            canonicalization="none",
            status="in_progress",
            notes="Paginated statuses for ingested deployments.",
        ),
        _row(
            "github.branch",
            coverage="partial",
            historical="partial",
            replay="partial",
            canonicalization="none",
            status="in_progress",
            notes="Paginated /branches with per-repo cursor continuity.",
        ),
        _row(
            "github.tag",
            coverage="partial",
            historical="partial",
            replay="partial",
            canonicalization="none",
            status="in_progress",
            notes="Paginated /tags with per-repo cursor continuity.",
        ),
        _row(
            "github.check_suite",
            coverage="partial",
            historical="partial",
            replay="partial",
            canonicalization="none",
            status="in_progress",
            notes="Deduped check-suite rows derived from check-run payloads (one row per suite id per repo sync).",
        ),
        _row(
            "github.release",
            coverage="partial",
            historical="partial",
            replay="partial",
            canonicalization="none",
            status="in_progress",
            notes="Paginated /releases with repository full_name injected when missing.",
        ),
        _row(
            "github.commit_comment",
            coverage="partial",
            historical="partial",
            replay="partial",
            canonicalization="none",
            status="in_progress",
            notes="Paginated repo-wide /comments (commit comments), distinct from PR review comments.",
        ),
        _row(
            "github.review_thread",
            coverage="partial",
            historical="partial",
            replay="partial",
            canonicalization="none",
            status="in_progress",
            notes="Deterministic thread roots from PR review comment in_reply_to_id closure per PR fetch.",
        ),
        _row(
            "timeline",
            coverage="none",
            historical="none",
            replay="no",
            canonicalization="none",
            status="missing",
            notes="PR timeline/event stream still pending dedicated implementation pass.",
        ),
    ]
    return _connector_bundle(
        "github",
        maturity_level=3,
        historical_backfill_summary="Repo-scoped PR/review/comment/commit/check/suite/workflow/deployment/branch/tag/release/commit-comment streams progress with checkpointed page continuity.",
        replay_compatibility_summary="Repository rows replay with standard idempotency keys.",
        canonicalization_summary="Partial — delivery/review artifacts now present; deeper timeline/event nuance remains for later phases.",
        resources=resources,
    )


def _linear() -> dict[str, Any]:
    resources = [
        _row(
            "linear.issue",
            coverage="full",
            historical="partial",
            replay="partial",
            canonicalization="none",
            status="in_progress",
            notes="Paginated GraphQL issues connection with `pageInfo` checkpoints and incremental `updatedAt` watermark filtering.",
        ),
        _row(
            "linear.comment",
            coverage="partial",
            historical="partial",
            replay="partial",
            canonicalization="none",
            status="in_progress",
            notes="Paginated GraphQL comments connection with checkpoint cursor continuity.",
        ),
        _row(
            "linear.comment_thread",
            coverage="partial",
            historical="partial",
            replay="partial",
            canonicalization="none",
            status="in_progress",
            notes="Emitted for root comments (no parent id) alongside linear.comment rows.",
        ),
        _row(
            "linear.project_update",
            coverage="partial",
            historical="partial",
            replay="partial",
            canonicalization="none",
            status="in_progress",
            notes="Paginated GraphQL projectUpdates connection when exposed by workspace schema.",
        ),
        _row(
            "linear.project",
            coverage="partial",
            historical="partial",
            replay="partial",
            canonicalization="none",
            status="in_progress",
            notes="Paginated GraphQL projects connection for delivery planning context.",
        ),
        _row(
            "linear.cycle",
            coverage="partial",
            historical="partial",
            replay="partial",
            canonicalization="none",
            status="in_progress",
            notes="Paginated GraphQL cycles connection.",
        ),
        _row(
            "linear.issue_relation",
            coverage="partial",
            historical="partial",
            replay="partial",
            canonicalization="none",
            status="in_progress",
            notes="Paginated GraphQL issueRelations stream.",
        ),
        _row(
            "linear.issue_label",
            coverage="partial",
            historical="partial",
            replay="partial",
            canonicalization="none",
            status="in_progress",
            notes="Paginated GraphQL issueLabels stream.",
        ),
        _row(
            "linear.initiative",
            coverage="partial",
            historical="partial",
            replay="partial",
            canonicalization="none",
            status="in_progress",
            notes="Paginated GraphQL initiatives stream.",
        ),
        _row(
            "linear.issue_attachment",
            coverage="partial",
            historical="partial",
            replay="partial",
            canonicalization="none",
            status="in_progress",
            notes="Issue-embedded attachment rows extracted when present in issue payloads.",
        ),
        _row(
            "linear.activity_history",
            coverage="partial",
            historical="partial",
            replay="partial",
            canonicalization="none",
            status="in_progress",
            notes="Issue activity/history rows extracted from issue payloads when available.",
        ),
        _row(
            "linear.viewer_ping",
            coverage="partial",
            historical="n/a",
            replay="partial",
            canonicalization="none",
            status="active",
            notes="Connectivity snapshot retained alongside deep streams.",
        ),
    ]
    return _connector_bundle(
        "linear",
        maturity_level=3,
        historical_backfill_summary="Issues/comments/projects/cycles/relations/labels/initiatives paginate with checkpoint cursor continuity.",
        replay_compatibility_summary="Linear streams use replay-scoped idempotency keys; checkpoint scope isolation applies to live vs replay.",
        canonicalization_summary="Partial — deep planning streams now ingested; canonical graph assembly remains later-phase work.",
        resources=resources,
    )


def _notion() -> dict[str, Any]:
    resources = [
        _row(
            "notion.search_result",
            coverage="partial",
            historical="partial",
            replay="partial",
            canonicalization="none",
            status="in_progress",
            notes="Paginated `/search` traversal with checkpointed `next_cursor` and incremental watermark.",
        ),
        _row(
            "notion.page",
            coverage="partial",
            historical="partial",
            replay="partial",
            canonicalization="none",
            status="in_progress",
            notes="Pages discovered via search and database row scans.",
        ),
        _row(
            "notion.database",
            coverage="partial",
            historical="partial",
            replay="partial",
            canonicalization="none",
            status="in_progress",
            notes="Database metadata capture via `/databases/{id}` for discovered databases.",
        ),
        _row(
            "notion.database_row",
            coverage="partial",
            historical="partial",
            replay="partial",
            canonicalization="none",
            status="in_progress",
            notes="Paginated `/databases/{id}/query` rows with per-database cursors.",
        ),
        _row(
            "notion.block",
            coverage="partial",
            historical="partial",
            replay="partial",
            canonicalization="none",
            status="in_progress",
            notes="Paginated `/blocks/{id}/children` traversal with per-parent checkpoint continuity.",
        ),
        _row(
            "notion.scope_ping",
            coverage="partial",
            historical="n/a",
            replay="partial",
            canonicalization="none",
            status="in_progress",
            notes="Workspace connectivity row emitted alongside deep streams.",
        ),
    ]
    return _connector_bundle(
        "notion",
        maturity_level=3,
        historical_backfill_summary="Search/database-row/block streams run with checkpointed cursors and resume budgets.",
        replay_compatibility_summary="Replay lane uses replay-scoped idempotency keys with checkpoint scope isolation.",
        canonicalization_summary="Partial — organizational artifacts now ingested; canonical graphing remains later-phase.",
        resources=resources,
    )


def _calls() -> dict[str, Any]:
    resources = [
        _row(
            "calls.meeting",
            coverage="partial",
            historical="partial",
            replay="partial",
            canonicalization="none",
            status="in_progress",
            notes="Paginated meeting/event ingestion (mock dataset + Google Calendar events API fallback).",
        ),
        _row(
            "calls.participant",
            coverage="partial",
            historical="partial",
            replay="partial",
            canonicalization="none",
            status="in_progress",
            notes="Per-meeting attendees ingested as participant rows when available.",
        ),
        _row(
            "calls.transcript",
            coverage="partial",
            historical="partial",
            replay="partial",
            canonicalization="none",
            status="in_progress",
            notes="Transcript blobs persisted with transcript_id + segment_count; segments sorted deterministically before segment row emission.",
        ),
        _row(
            "calls.transcript_segment",
            coverage="partial",
            historical="partial",
            replay="partial",
            canonicalization="none",
            status="in_progress",
            notes="Segment rows use contiguous ordinals after deterministic sort; payload carries transcript_id for linkage.",
        ),
        _row(
            "calls.recording",
            coverage="partial",
            historical="partial",
            replay="partial",
            canonicalization="none",
            status="in_progress",
            notes="Recording metadata rows ingested when provider payload includes recording details.",
        ),
        _row(
            "calls.scope_ping",
            coverage="partial",
            historical="n/a",
            replay="partial",
            canonicalization="none",
            status="in_progress",
            notes="Connectivity row retained alongside meeting/transcript streams.",
        ),
    ]
    return _connector_bundle(
        "calls",
        maturity_level=3,
        historical_backfill_summary="Meeting/event stream paginates with checkpointed cursor + watermark continuation.",
        replay_compatibility_summary="Calls streams use replay-scoped idempotency keys with checkpoint scope isolation.",
        canonicalization_summary="Partial — meeting/transcript/participant primitives present; provider breadth remains future work.",
        resources=resources,
    )


def build_admin_exhaust_coverage_payload(*, tenant_id: uuid.UUID) -> dict[str, Any]:
    """Payload for :class:`AdminCortexIngestionExhaustCoverageResponse`."""
    connectors: list[dict[str, Any]] = [_calls(), _github(), _linear(), _notion(), _slack()]
    connectors.sort(key=lambda c: c["connector"])
    return {
        "tenant_id": tenant_id,
        "connector_exhaust_matrix_doc": "DOCS/cortex/connectors/connector-exhaust-matrix.md",
        "ingestion_depth_model_doc": "DOCS/cortex/connectors/ingestion-depth-model.md",
        "organizational_exhaust_definition_doc": "DOCS/cortex/connectors/organizational-exhaust-definition.md",
        "real_ingestion_definition_doc": "DOCS/cortex/01-ingestion/real-ingestion-definition.md",
        "connector_expansion_roadmap_doc": "DOCS/cortex/implementation/connector-expansion-roadmap.md",
        "connectors": connectors,
    }
