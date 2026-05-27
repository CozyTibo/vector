"""Phase 01 — github connector sync."""

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
    list_org_members_page,
    list_org_teams_page,
    list_team_members_page,
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

from vector.domains.cortex.ingestion.stream_checkpoint import (
    derive_exhaust_depth,
    ensure_stream_introduced_at,
    stream_backfill_complete,
)
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

def ensure_github_workflow_run_repository_metadata(
    run: Mapping[str, Any],
    *,
    installation_repository: Mapping[str, Any],
    repository_full_name: str,
) -> dict[str, Any]:
    """Merge durable repository identity onto a workflow run dict before raw persistence.

    GitHub's ``GET /repos/{owner}/{repo}/actions/runs`` list payload sometimes omits the nested
    ``repository`` object (or returns it without ``id`` / ``full_name``). The sync loop already
    holds the authoritative installation repository record for ``repository_full_name`` — merge
    that truth so canonical materialization has stable ``repository_provider_id`` inputs without
    inventing identifiers: values come from the installation ``repositories`` payload or the
    known ``owner/repo`` pair for this fetch.
    """
    wr = dict(run)
    api_repo = wr.get("repository")
    merged: dict[str, Any] = dict(api_repo) if isinstance(api_repo, dict) else {}
    inst = dict(installation_repository) if isinstance(installation_repository, dict) else {}
    fn = repository_full_name.strip()

    fn_ok = isinstance(merged.get("full_name"), str) and "/" in merged["full_name"].strip()
    if not fn_ok and "/" in fn:
        merged["full_name"] = fn

    rid = merged.get("id")
    has_numeric_id = isinstance(rid, int) or (isinstance(rid, str) and rid.strip().isdigit())
    if not has_numeric_id:
        inst_id = inst.get("id")
        if isinstance(inst_id, int):
            merged["id"] = inst_id
        elif isinstance(inst_id, str) and inst_id.strip().isdigit():
            merged["id"] = int(inst_id.strip())

    if not isinstance(merged.get("name"), str) or not merged["name"].strip():
        if "/" in fn:
            merged["name"] = fn.split("/", 1)[1].strip()
        elif fn:
            merged["name"] = fn

    own = merged.get("owner")
    if not isinstance(own, dict) or not isinstance(own.get("login"), str) or not str(own.get("login", "")).strip():
        inst_owner = inst.get("owner")
        if isinstance(inst_owner, dict) and isinstance(inst_owner.get("login"), str):
            merged["owner"] = dict(inst_owner)
        elif "/" in fn:
            merged["owner"] = {"login": fn.split("/", 1)[0].strip()}

    wr["repository"] = merged
    return wr


def _sync_github_people_plane(
    session: Session,
    settings: Settings,
    *,
    ctx: IngestionSyncContext,
    tenant_id: uuid.UUID,
    connection_id: uuid.UUID,
    run_id: uuid.UUID,
    source_trigger: str,
    token: str,
    org_login: str,
    github_existing: dict[str, Any],
) -> tuple[int, dict[str, Any]]:
    """Org members, teams, and team memberships (people plane)."""
    n_ins = 0
    people_patch: dict[str, Any] = {}
    gh_base = settings.github_rest_api_base_url().rstrip("/")
    max_pages = min(settings.cortex_github_installation_repos_max_pages, 10)

    def _stream(name: str) -> dict[str, Any]:
        s = github_existing.get(name) if isinstance(github_existing, dict) else None
        return s if isinstance(s, dict) else {}

    # Org members -> github.user
    users_state = _stream("users")
    user_page_start = max(1, int(users_state.get("last_page") or 0) + 1) if users_state.get("last_page") else 1
    user_rows = 0
    users_complete = False
    last_user_page = user_page_start - 1
    for page in range(user_page_start, user_page_start + max_pages):
        last_user_page = page
        try:
            members = list_org_members_page(settings, token, org_login, page=page)
        except GitHubApiError:
            break
        if not members:
            users_complete = True
            break
        for m in members:
            login = m.get("login")
            if not isinstance(login, str) or not login:
                continue
            uid = str(m.get("id") or login)[:512]
            if append_raw(
                session,
                ctx=ctx,
                tenant_id=tenant_id,
                connection_id=connection_id,
                connector=CONNECTION_PROVIDER_GITHUB,
                run_id=run_id,
                source_trigger=source_trigger,
                resource_type="github.user",
                external_id=uid,
                api_endpoint=f"{gh_base}/orgs/{org_login}/members",
                query_params={"page": page},
                payload_body={
                    **core_envelope_fields(
                        connector=CONNECTION_PROVIDER_GITHUB,
                        connection_id=connection_id,
                        source_object_type="github.user",
                        source_object_id=uid,
                    ),
                    "person": {"provider_user_id": uid, "handle": login},
                    "member": m,
                },
                http_status=200,
                idempotency_key=idem_key(ctx, run_id, f"github:user:{login}"),
            ):
                n_ins += 1
                user_rows += 1
        if len(members) < 100:
            users_complete = True
            break
    people_patch["users"] = ensure_stream_introduced_at(
        {
            "cursor_owner": "github.user",
            "last_page": last_user_page if user_rows else users_state.get("last_page"),
            "rows_seen_last_run": user_rows,
            "backfill_complete": stream_backfill_complete(pagination_exhausted=users_complete),
            "last_ok_at": utc_now().isoformat(),
        },
    )

    # Teams + memberships
    teams_state = _stream("teams")
    team_page_start = max(1, int(teams_state.get("last_page") or 0) + 1) if teams_state.get("last_page") else 1
    team_rows = 0
    membership_rows = 0
    teams_complete = False
    last_team_page = team_page_start - 1
    for page in range(team_page_start, team_page_start + max_pages):
        last_team_page = page
        try:
            teams = list_org_teams_page(settings, token, org_login, page=page)
        except GitHubApiError:
            break
        if not teams:
            teams_complete = True
            break
        for team in teams:
            slug = team.get("slug")
            tid = str(team.get("id") or slug or "")[:512]
            if not tid:
                continue
            if append_raw(
                session,
                ctx=ctx,
                tenant_id=tenant_id,
                connection_id=connection_id,
                connector=CONNECTION_PROVIDER_GITHUB,
                run_id=run_id,
                source_trigger=source_trigger,
                resource_type="github.team",
                external_id=tid,
                api_endpoint=f"{gh_base}/orgs/{org_login}/teams",
                query_params={"page": page},
                payload_body={
                    **core_envelope_fields(
                        connector=CONNECTION_PROVIDER_GITHUB,
                        connection_id=connection_id,
                        source_object_type="github.team",
                        source_object_id=tid,
                    ),
                    "team": team,
                },
                http_status=200,
                idempotency_key=idem_key(ctx, run_id, f"github:team:{tid}"),
            ):
                n_ins += 1
                team_rows += 1
            if isinstance(slug, str) and slug.strip():
                try:
                    tmembers = list_team_members_page(
                        settings,
                        token,
                        org_login,
                        slug.strip(),
                        page=1,
                    )
                except GitHubApiError:
                    continue
                for tm in tmembers:
                    login = tm.get("login")
                    mem_ext = f"{slug}:{login}"[:512] if isinstance(login, str) else f"{slug}:{tm.get('id')}"[:512]
                    if append_raw(
                        session,
                        ctx=ctx,
                        tenant_id=tenant_id,
                        connection_id=connection_id,
                        connector=CONNECTION_PROVIDER_GITHUB,
                        run_id=run_id,
                        source_trigger=source_trigger,
                        resource_type="github.team_membership",
                        external_id=mem_ext,
                        api_endpoint=f"{gh_base}/orgs/{org_login}/teams/{slug}/members",
                        query_params={"team": slug},
                        payload_body={
                            **core_envelope_fields(
                                connector=CONNECTION_PROVIDER_GITHUB,
                                connection_id=connection_id,
                                source_object_type="github.team_membership",
                                source_object_id=mem_ext,
                            ),
                            "team": {"id": tid, "slug": slug},
                            "member": tm,
                        },
                        http_status=200,
                        idempotency_key=idem_key(ctx, run_id, f"github:team_member:{mem_ext}"),
                    ):
                        n_ins += 1
                        membership_rows += 1
        if len(teams) < 100:
            teams_complete = True
            break
    people_patch["teams"] = ensure_stream_introduced_at(
        {
            "cursor_owner": "github.team",
            "last_page": last_team_page if team_rows else teams_state.get("last_page"),
            "rows_seen_last_run": team_rows,
            "membership_rows_seen_last_run": membership_rows,
            "backfill_complete": stream_backfill_complete(pagination_exhausted=teams_complete),
            "last_ok_at": utc_now().isoformat(),
        },
    )
    return n_ins, people_patch


def run_github_connector_sync(
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
        connector=CONNECTION_PROVIDER_GITHUB,
        scope_key=scope_ck,
    )
    link = gh_repo.get_github_connection_for_tenant(session, tenant_id)
    if link is None:
        ins = int(
            append_raw(
                session,
                ctx=ctx,
                tenant_id=tenant_id,
                connection_id=connection_id,
                connector=CONNECTION_PROVIDER_GITHUB,
                run_id=run_id,
                source_trigger=source_trigger,
                resource_type="github.sync",
                external_id="missing-github-detail",
                api_endpoint="internal://github/no-detail",
                query_params={},
                payload_body={
                    **core_envelope_fields(
                        connector=CONNECTION_PROVIDER_GITHUB,
                        connection_id=connection_id,
                        source_object_type="github.connection",
                        source_object_id="github_connection_detail_missing",
                    ),
                    "ingestion_error": {"code": "github_connection_detail_missing"},
                },
                http_status=503,
                idempotency_key=idem_key(ctx, run_id, "github:no-detail"),
            )
        )
        upsert_checkpoint(
            session,
            tenant_id=tenant_id,
            connection_id=connection_id,
            connector=CONNECTION_PROVIDER_GITHUB,
            scope_key=scope_ck,
            patch={
                "last_incremental_at": utc_now().isoformat(),
                "repos_fetched": 0,
                "streams": {
                    "github": {
                        "installation_repositories": {
                            "cursor_owner": "github.installation_repositories",
                            "last_status": "missing_connection_detail",
                        }
                    }
                },
            },
            sync_mode=ctx.checkpoint_sync_mode,
        )
        return ins
    try:
        token = create_github_installation_access_token(settings, link.installation_id)
    except GitHubApiError as e:
        ins = int(
            append_raw(
                session,
                ctx=ctx,
                tenant_id=tenant_id,
                connection_id=connection_id,
                connector=CONNECTION_PROVIDER_GITHUB,
                run_id=run_id,
                source_trigger=source_trigger,
                resource_type="github.installation_repositories",
                external_id="fetch_error",
                api_endpoint=f"{settings.github_rest_api_base_url().rstrip('/')}/installation/repositories",
                query_params={"error": True},
                payload_body={
                    **core_envelope_fields(
                        connector=CONNECTION_PROVIDER_GITHUB,
                        connection_id=connection_id,
                        source_object_type="github.installation_repositories",
                        source_object_id="fetch_error",
                    ),
                    "ingestion_error": {"code": "github_api_error", "message": str(e)},
                },
                http_status=502,
                idempotency_key=idem_key(ctx, run_id, "github:fetch_error"),
            )
        )
        upsert_checkpoint(
            session,
            tenant_id=tenant_id,
            connection_id=connection_id,
            connector=CONNECTION_PROVIDER_GITHUB,
            scope_key=scope_ck,
            patch={
                "last_incremental_at": utc_now().isoformat(),
                "repos_fetched": 0,
                "streams": {
                    "github": {
                        "installation_repositories": {
                            "cursor_owner": "github.installation_repositories",
                            "last_status": "token_fetch_error",
                        }
                    }
                },
            },
            sync_mode=ctx.checkpoint_sync_mode,
        )
        return ins

    n_ins = 0
    streams_existing = checkpoint_streams_for_mode(existing_ckpt, ctx.sync_mode)
    github_existing_pre = (
        streams_existing.get("github")
        if isinstance(streams_existing, dict) and isinstance(streams_existing.get("github"), dict)
        else {}
    )
    people_patch: dict[str, Any] = {}
    if (link.detail.account_type or "").strip().lower() == "organization":
        people_n, people_patch = _sync_github_people_plane(
            session,
            settings,
            ctx=ctx,
            tenant_id=tenant_id,
            connection_id=connection_id,
            run_id=run_id,
            source_trigger=source_trigger,
            token=token,
            org_login=link.detail.account_login,
            github_existing=github_existing_pre,
        )
        n_ins += people_n

    collected: list[tuple[str, str, dict[str, Any]]] = []
    total_hint: int | None = None
    pages_fetched = 0
    install_complete = False
    per_page = 100
    max_pages = settings.cortex_github_installation_repos_max_pages
    page = 1
    try:
        while page <= max_pages:
            repos, page_total = list_installation_repositories_page(
                settings,
                token,
                page=page,
                per_page=per_page,
            )
            if total_hint is None and page_total is not None:
                total_hint = page_total
            if not repos:
                break
            for repo in repos:
                rid = repo.get("id")
                rid_s = str(rid) if rid is not None else ""
                fn = repo.get("full_name") or rid_s
                body = {
                    **core_envelope_fields(
                        connector=CONNECTION_PROVIDER_GITHUB,
                        connection_id=connection_id,
                        source_object_type="github.repository",
                        source_object_id=rid_s or fn[:512],
                    ),
                    "payload_hash_basis": "github_rest_repo_record_v1",
                    "repository": repo,
                }
                base = f"github:repo:{rid_s}" if rid_s else f"github:repo:{fn[:200]}"
                if append_raw(
                    session,
                    ctx=ctx,
                    tenant_id=tenant_id,
                    connection_id=connection_id,
                    connector=CONNECTION_PROVIDER_GITHUB,
                    run_id=run_id,
                    source_trigger=source_trigger,
                    resource_type="github.repository",
                    external_id=rid_s or fn[:512],
                    api_endpoint=f"{settings.github_rest_api_base_url().rstrip('/')}/installation/repositories",
                    query_params={"page": page, "per_page": per_page},
                    payload_body=body,
                    http_status=200,
                    idempotency_key=idem_key(ctx, run_id, base),
                ):
                    n_ins += 1
                if isinstance(fn, str) and "/" in fn.strip():
                    collected.append((rid_s, fn.strip(), repo))
            pages_fetched += 1
            if len(repos) < per_page:
                install_complete = True
                break
            page += 1
    except GitHubApiError as e:
        ins = int(
            append_raw(
                session,
                ctx=ctx,
                tenant_id=tenant_id,
                connection_id=connection_id,
                connector=CONNECTION_PROVIDER_GITHUB,
                run_id=run_id,
                source_trigger=source_trigger,
                resource_type="github.installation_repositories",
                external_id=f"page_{page}_error",
                api_endpoint=f"{settings.github_rest_api_base_url().rstrip('/')}/installation/repositories",
                query_params={"page": page, "error": True},
                payload_body={
                    **core_envelope_fields(
                        connector=CONNECTION_PROVIDER_GITHUB,
                        connection_id=connection_id,
                        source_object_type="github.installation_repositories",
                        source_object_id=f"page_{page}_error",
                    ),
                    "ingestion_error": {"code": "github_api_error", "message": str(e)},
                },
                http_status=502,
                idempotency_key=idem_key(ctx, run_id, f"github:page_error:{page}"),
            )
        )
        upsert_checkpoint(
            session,
            tenant_id=tenant_id,
            connection_id=connection_id,
            connector=CONNECTION_PROVIDER_GITHUB,
            scope_key=scope_ck,
            patch={
                "last_incremental_at": utc_now().isoformat(),
                "repos_fetched": n_ins,
                "github_installation_repos_pages": pages_fetched,
                "total_count_hint": total_hint,
                "streams": {
                    "github": {
                        **people_patch,
                        "installation_repositories": ensure_stream_introduced_at(
                            {
                                "cursor_owner": "github.installation_repositories",
                                "last_page": pages_fetched,
                                "backfill_complete": stream_backfill_complete(pagination_exhausted=install_complete),
                            },
                        ),
                    }
                },
            },
            sync_mode=ctx.checkpoint_sync_mode,
        )
        return ins

    streams_existing = checkpoint_streams_for_mode(existing_ckpt, ctx.sync_mode)
    github_existing = (
        streams_existing.get("github")
        if isinstance(streams_existing, dict) and isinstance(streams_existing.get("github"), dict)
        else {}
    )
    repos_existing = (
        github_existing.get("repos")
        if isinstance(github_existing, dict) and isinstance(github_existing.get("repos"), dict)
        else {}
    )
    repo_ring_raw = github_existing.get("repo_ring_index") if isinstance(github_existing, dict) else 0
    try:
        repo_ring_index = int(repo_ring_raw)
    except (TypeError, ValueError):
        repo_ring_index = 0

    def _repo_deep_incomplete(fn: str) -> bool:
        sub = repos_existing.get(fn) if isinstance(repos_existing, dict) else None
        if not isinstance(sub, dict):
            return True
        pr = sub.get("pull_requests")
        if isinstance(pr, dict) and pr.get("backfill_complete"):
            return False
        return True

    collected.sort(key=lambda item: (not _repo_deep_incomplete(item[1]), item[1]))

    selected_repos, next_repo_ring_index = pick_github_repos_round_robin(
        collected,
        ring_index=repo_ring_index,
        count=settings.cortex_github_pr_fetch_max_repos,
    )
    gh_base = settings.github_rest_api_base_url().rstrip("/")
    pr_per_repo = settings.cortex_github_prs_per_repo
    pr_rows = 0
    review_rows = 0
    review_comment_rows = 0
    issue_comment_rows = 0
    commit_rows = 0
    check_run_rows = 0
    workflow_rows = 0
    deployment_rows = 0
    deployment_status_rows = 0
    branch_rows = 0
    tag_rows = 0
    check_suite_rows = 0
    release_rows = 0
    issue_rows = 0
    commit_comment_rows = 0
    review_thread_rows = 0
    issue_timeline_rows = 0
    pr_timeline_rows = 0
    budget_exhausted = False
    start_t = time.monotonic()
    repo_patch_map: dict[str, Any] = {}

    for _rid_s, fn, _repo in selected_repos:
        parts = fn.split("/", 1)
        if len(parts) != 2:
            continue
        owner, repo_name = parts[0], parts[1]
        existing_repo = repos_existing.get(fn) if isinstance(repos_existing, dict) else None
        if not isinstance(existing_repo, dict):
            existing_repo = {}

        repo_pr_rows = 0
        repo_review_rows = 0
        repo_review_comment_rows = 0
        repo_issue_comment_rows = 0
        repo_commit_rows = 0
        repo_check_rows = 0
        repo_workflow_rows = 0
        repo_deploy_rows = 0
        repo_deploy_status_rows = 0
        repo_branch_rows = 0
        repo_tag_rows = 0
        repo_check_suite_rows = 0
        repo_release_rows = 0
        repo_issue_rows = 0
        repo_commit_comment_rows = 0
        repo_review_thread_rows = 0
        repo_issue_timeline_rows = 0
        repo_pr_timeline_rows = 0
        emitted_check_suite_ids: set[int] = set()

        pull_state = existing_repo.get("pull_requests") if isinstance(existing_repo.get("pull_requests"), dict) else {}
        pulls_next_page_raw = pull_state.get("next_page", 1)
        try:
            pulls_next_page = max(1, int(pulls_next_page_raw))
        except (TypeError, ValueError):
            pulls_next_page = 1
        current_pulls_page = pulls_next_page
        pull_heads: list[tuple[int, str]] = []
        pulls_complete = False
        pull_pages_fetched = 0
        try:
            for _ in range(settings.cortex_github_prs_max_pages_per_repo):
                pulls = list_repo_pulls_page(
                    settings,
                    token,
                    owner=owner,
                    repo=repo_name,
                    page=current_pulls_page,
                    per_page=pr_per_repo,
                    state="all",
                )
                pull_pages_fetched += 1
                for pr in pulls:
                    num = pr.get("number")
                    if not isinstance(num, int):
                        continue
                    pr_ext = f"{fn}#{num}"[:512]
                    pr_body = {
                        **core_envelope_fields(
                            connector=CONNECTION_PROVIDER_GITHUB,
                            connection_id=connection_id,
                            source_object_type="github.pull_request",
                            source_object_id=pr_ext,
                        ),
                        "pull_request": pr,
                        "paging": {"page": current_pulls_page, "mode": ctx.sync_mode},
                    }
                    if append_raw(
                        session,
                        ctx=ctx,
                        tenant_id=tenant_id,
                        connection_id=connection_id,
                        connector=CONNECTION_PROVIDER_GITHUB,
                        run_id=run_id,
                        source_trigger=source_trigger,
                        resource_type="github.pull_request",
                        external_id=pr_ext,
                        api_endpoint=f"{gh_base}/repos/{owner}/{repo_name}/pulls",
                        query_params={"state": "all", "per_page": pr_per_repo, "page": current_pulls_page},
                        payload_body=pr_body,
                        http_status=200,
                        idempotency_key=idem_key(ctx, run_id, f"github:pr:{pr_ext}"),
                    ):
                        n_ins += 1
                        pr_rows += 1
                        repo_pr_rows += 1
                    head = pr.get("head")
                    if isinstance(head, dict):
                        sha = head.get("sha")
                        if isinstance(sha, str) and sha:
                            pull_heads.append((num, sha))

                    # PR reviews
                    try:
                        for review_page in range(1, settings.cortex_github_reviews_max_pages_per_pr + 1):
                            reviews = list_pull_reviews_page(
                                settings,
                                token,
                                owner=owner,
                                repo=repo_name,
                                pull_number=num,
                                page=review_page,
                            )
                            for review in reviews:
                                rid = review.get("id")
                                if rid is None:
                                    continue
                                ext = f"{pr_ext}:review:{rid}"[:512]
                                if append_raw(
                                    session,
                                    ctx=ctx,
                                    tenant_id=tenant_id,
                                    connection_id=connection_id,
                                    connector=CONNECTION_PROVIDER_GITHUB,
                                    run_id=run_id,
                                    source_trigger=source_trigger,
                                    resource_type="github.pull_request_review",
                                    external_id=ext,
                                    api_endpoint=f"{gh_base}/repos/{owner}/{repo_name}/pulls/{num}/reviews",
                                    query_params={"page": review_page},
                                    payload_body={
                                        **core_envelope_fields(
                                            connector=CONNECTION_PROVIDER_GITHUB,
                                            connection_id=connection_id,
                                            source_object_type="github.pull_request_review",
                                            source_object_id=ext,
                                        ),
                                        "pull_request_number": num,
                                        "github_pull_request_id": pr.get("id"),
                                        "review": review,
                                    },
                                    http_status=200,
                                    idempotency_key=idem_key(ctx, run_id, f"github:pr_review:{ext}"),
                                ):
                                    n_ins += 1
                                    review_rows += 1
                                    repo_review_rows += 1
                            if len(reviews) < 100:
                                break
                    except GitHubApiError:
                        pass

                    # PR review comments (+ deterministic review thread roots)
                    try:
                        all_review_comments: list[dict[str, Any]] = []
                        for rc_page in range(1, settings.cortex_github_review_comments_max_pages_per_pr + 1):
                            review_comments = list_pull_review_comments_page(
                                settings,
                                token,
                                owner=owner,
                                repo=repo_name,
                                pull_number=num,
                                page=rc_page,
                            )
                            all_review_comments.extend([x for x in review_comments if isinstance(x, dict)])
                            if len(review_comments) < 100:
                                break

                        by_id: dict[int, dict[str, Any]] = {}
                        for rc in all_review_comments:
                            raw_id = rc.get("id")
                            nid: int | None
                            if isinstance(raw_id, int):
                                nid = raw_id
                            elif isinstance(raw_id, str) and raw_id.strip().isdigit():
                                nid = int(raw_id.strip())
                            else:
                                nid = None
                            if nid is not None:
                                by_id[nid] = rc

                        def _review_comment_root_id(comment_id: int) -> int:
                            seen: set[int] = set()
                            cur: int | None = comment_id
                            while cur is not None:
                                if cur in seen:
                                    return cur
                                seen.add(cur)
                                c = by_id.get(cur)
                                if c is None:
                                    return cur
                                parent_raw = c.get("in_reply_to_id")
                                if parent_raw is None:
                                    return cur
                                if isinstance(parent_raw, int):
                                    cur = parent_raw
                                elif isinstance(parent_raw, str) and parent_raw.strip().isdigit():
                                    cur = int(parent_raw.strip())
                                else:
                                    return cur
                            return comment_id

                        thread_roots = {
                            _review_comment_root_id(nid)
                            for nid in by_id
                        }
                        for root_id in sorted(thread_roots):
                            rt_ext = f"{pr_ext}:review_thread:{root_id}"[:512]
                            if append_raw(
                                session,
                                ctx=ctx,
                                tenant_id=tenant_id,
                                connection_id=connection_id,
                                connector=CONNECTION_PROVIDER_GITHUB,
                                run_id=run_id,
                                source_trigger=source_trigger,
                                resource_type="github.review_thread",
                                external_id=rt_ext,
                                api_endpoint=f"{gh_base}/repos/{owner}/{repo_name}/pulls/{num}/comments",
                                query_params={"thread_roots": len(thread_roots)},
                                payload_body={
                                    **core_envelope_fields(
                                        connector=CONNECTION_PROVIDER_GITHUB,
                                        connection_id=connection_id,
                                        source_object_type="github.review_thread",
                                        source_object_id=rt_ext,
                                    ),
                                    "pull_request_number": num,
                                    "thread_id": root_id,
                                },
                                http_status=200,
                                idempotency_key=idem_key(ctx, run_id, f"github:review_thread:{rt_ext}"),
                            ):
                                n_ins += 1
                                review_thread_rows += 1
                                repo_review_thread_rows += 1

                        for rc in all_review_comments:
                            cid = rc.get("id")
                            if cid is None:
                                continue
                            ext = f"{pr_ext}:review_comment:{cid}"[:512]
                            if append_raw(
                                session,
                                ctx=ctx,
                                tenant_id=tenant_id,
                                connection_id=connection_id,
                                connector=CONNECTION_PROVIDER_GITHUB,
                                run_id=run_id,
                                source_trigger=source_trigger,
                                resource_type="github.pull_request_review_comment",
                                external_id=ext,
                                api_endpoint=f"{gh_base}/repos/{owner}/{repo_name}/pulls/{num}/comments",
                                query_params={},
                                payload_body={
                                    **core_envelope_fields(
                                        connector=CONNECTION_PROVIDER_GITHUB,
                                        connection_id=connection_id,
                                        source_object_type="github.pull_request_review_comment",
                                        source_object_id=ext,
                                    ),
                                    "pull_request_number": num,
                                    "comment": rc,
                                },
                                http_status=200,
                                idempotency_key=idem_key(ctx, run_id, f"github:pr_review_comment:{ext}"),
                            ):
                                n_ins += 1
                                review_comment_rows += 1
                                repo_review_comment_rows += 1
                    except GitHubApiError:
                        pass

                    # PR issue comments
                    try:
                        for ic_page in range(1, settings.cortex_github_issue_comments_max_pages_per_pr + 1):
                            issue_comments = list_pull_issue_comments_page(
                                settings,
                                token,
                                owner=owner,
                                repo=repo_name,
                                pull_number=num,
                                page=ic_page,
                            )
                            for ic in issue_comments:
                                cid = ic.get("id")
                                if cid is None:
                                    continue
                                ext = f"{pr_ext}:issue_comment:{cid}"[:512]
                                if append_raw(
                                    session,
                                    ctx=ctx,
                                    tenant_id=tenant_id,
                                    connection_id=connection_id,
                                    connector=CONNECTION_PROVIDER_GITHUB,
                                    run_id=run_id,
                                    source_trigger=source_trigger,
                                    resource_type="github.issue_comment",
                                    external_id=ext,
                                    api_endpoint=f"{gh_base}/repos/{owner}/{repo_name}/issues/{num}/comments",
                                    query_params={"page": ic_page},
                                    payload_body={
                                        **core_envelope_fields(
                                            connector=CONNECTION_PROVIDER_GITHUB,
                                            connection_id=connection_id,
                                            source_object_type="github.issue_comment",
                                            source_object_id=ext,
                                        ),
                                        "pull_request_number": num,
                                        "comment": ic,
                                    },
                                    http_status=200,
                                    idempotency_key=idem_key(ctx, run_id, f"github:issue_comment:{ext}"),
                                ):
                                    n_ins += 1
                                    issue_comment_rows += 1
                                    repo_issue_comment_rows += 1
                            if len(issue_comments) < 100:
                                break
                    except GitHubApiError:
                        pass

                    # PR timeline (REST `/issues/{n}/timeline` — issue number equals PR number)
                    pr_gid = pr.get("id")
                    if isinstance(pr_gid, int) and isinstance(num, int):
                        try:
                            for tl_page in range(1, settings.cortex_github_timeline_max_pages_per_issue_or_pr + 1):
                                if time.monotonic() - start_t >= settings.cortex_github_repo_time_budget_seconds:
                                    budget_exhausted = True
                                    break
                                timeline = list_repo_issue_timeline_page(
                                    settings,
                                    token,
                                    owner=owner,
                                    repo=repo_name,
                                    issue_number=num,
                                    page=tl_page,
                                )
                                for te in timeline:
                                    if not isinstance(te, dict):
                                        continue
                                    te_id = te.get("id")
                                    if te_id is None:
                                        continue
                                    tl_ext = f"{pr_ext}:timeline_event:{te_id}"[:512]
                                    ts = te.get("created_at")
                                    ts_str = ts if isinstance(ts, str) else None
                                    if append_raw(
                                        session,
                                        ctx=ctx,
                                        tenant_id=tenant_id,
                                        connection_id=connection_id,
                                        connector=CONNECTION_PROVIDER_GITHUB,
                                        run_id=run_id,
                                        source_trigger=source_trigger,
                                        resource_type="github.pull_request_timeline_event",
                                        external_id=tl_ext,
                                        api_endpoint=f"{gh_base}/repos/{owner}/{repo_name}/issues/{num}/timeline",
                                        query_params={"page": tl_page},
                                        payload_body={
                                            **core_envelope_fields(
                                                connector=CONNECTION_PROVIDER_GITHUB,
                                                connection_id=connection_id,
                                                source_object_type="github.pull_request_timeline_event",
                                                source_object_id=tl_ext,
                                            ),
                                            "id": te_id,
                                            "repository_full_name": fn,
                                            "pull_request_external_ref": pr_ext,
                                            "pull_request_number": num,
                                            "github_pull_request_id": pr_gid,
                                            "timeline_event": te,
                                            "provider_event_timestamp": ts_str,
                                        },
                                        http_status=200,
                                        idempotency_key=idem_key(ctx, run_id, f"github:pr_timeline:{tl_ext}"),
                                    ):
                                        n_ins += 1
                                        pr_timeline_rows += 1
                                        repo_pr_timeline_rows += 1
                                if len(timeline) < 100:
                                    break
                        except GitHubApiError:
                            pass

                if len(pulls) < pr_per_repo:
                    pulls_complete = True
                    current_pulls_page = 1
                    break
                current_pulls_page += 1
                if time.monotonic() - start_t >= settings.cortex_github_repo_time_budget_seconds:
                    budget_exhausted = True
                    break
        except GitHubApiError:
            pass

        # Commits
        commit_state = existing_repo.get("commits") if isinstance(existing_repo.get("commits"), dict) else {}
        commit_page_raw = commit_state.get("next_page", 1)
        try:
            commit_page = max(1, int(commit_page_raw))
        except (TypeError, ValueError):
            commit_page = 1
        commits_complete = False
        commit_pages_fetched = 0
        try:
            for _ in range(settings.cortex_github_commits_max_pages_per_repo):
                commits = list_repo_commits_page(
                    settings,
                    token,
                    owner=owner,
                    repo=repo_name,
                    page=commit_page,
                )
                commit_pages_fetched += 1
                for commit in commits:
                    sha = commit.get("sha")
                    if not isinstance(sha, str) or not sha:
                        continue
                    ext = f"{fn}:{sha}"[:512]
                    if append_raw(
                        session,
                        ctx=ctx,
                        tenant_id=tenant_id,
                        connection_id=connection_id,
                        connector=CONNECTION_PROVIDER_GITHUB,
                        run_id=run_id,
                        source_trigger=source_trigger,
                        resource_type="github.commit",
                        external_id=ext,
                        api_endpoint=f"{gh_base}/repos/{owner}/{repo_name}/commits",
                        query_params={"page": commit_page},
                        payload_body={
                            **core_envelope_fields(
                                connector=CONNECTION_PROVIDER_GITHUB,
                                connection_id=connection_id,
                                source_object_type="github.commit",
                                source_object_id=ext,
                            ),
                            "commit": commit,
                        },
                        http_status=200,
                        idempotency_key=idem_key(ctx, run_id, f"github:commit:{ext}"),
                    ):
                        n_ins += 1
                        commit_rows += 1
                        repo_commit_rows += 1
                if len(commits) < 100:
                    commits_complete = True
                    commit_page = 1
                    break
                commit_page += 1
                if time.monotonic() - start_t >= settings.cortex_github_repo_time_budget_seconds:
                    budget_exhausted = True
                    break
        except GitHubApiError:
            pass

        # Check runs for PR heads
        for pr_num, sha in pull_heads:
            try:
                for check_page in range(1, settings.cortex_github_check_runs_max_pages_per_pr + 1):
                    check_runs, _ = list_repo_check_runs_page(
                        settings,
                        token,
                        owner=owner,
                        repo=repo_name,
                        ref=sha,
                        page=check_page,
                    )
                    for cr in check_runs:
                        cid = cr.get("id")
                        if cid is None:
                            continue
                        ext = f"{fn}:{sha}:check:{cid}"[:512]
                        if append_raw(
                            session,
                            ctx=ctx,
                            tenant_id=tenant_id,
                            connection_id=connection_id,
                            connector=CONNECTION_PROVIDER_GITHUB,
                            run_id=run_id,
                            source_trigger=source_trigger,
                            resource_type="github.check_run",
                            external_id=ext,
                            api_endpoint=f"{gh_base}/repos/{owner}/{repo_name}/commits/{sha}/check-runs",
                            query_params={"page": check_page, "pull_number": pr_num},
                            payload_body={
                                **core_envelope_fields(
                                    connector=CONNECTION_PROVIDER_GITHUB,
                                    connection_id=connection_id,
                                    source_object_type="github.check_run",
                                    source_object_id=ext,
                                ),
                                "pull_request_number": pr_num,
                                "head_sha": sha,
                                "check_run": cr,
                            },
                            http_status=200,
                            idempotency_key=idem_key(ctx, run_id, f"github:check_run:{ext}"),
                        ):
                            n_ins += 1
                            check_run_rows += 1
                            repo_check_rows += 1
                        suite_obj = cr.get("check_suite") if isinstance(cr.get("check_suite"), dict) else {}
                        suite_raw = suite_obj.get("id")
                        suite_id: int | None
                        if isinstance(suite_raw, int):
                            suite_id = suite_raw
                        elif isinstance(suite_raw, str) and suite_raw.strip().isdigit():
                            suite_id = int(suite_raw.strip())
                        else:
                            suite_id = None
                        if suite_id is not None and suite_id not in emitted_check_suite_ids:
                            emitted_check_suite_ids.add(suite_id)
                            suite_payload = dict(suite_obj)
                            if not isinstance(suite_payload.get("repository"), dict):
                                suite_payload["repository"] = {"full_name": fn}
                            suite_ext = f"{fn}:check_suite:{suite_id}"[:512]
                            if append_raw(
                                session,
                                ctx=ctx,
                                tenant_id=tenant_id,
                                connection_id=connection_id,
                                connector=CONNECTION_PROVIDER_GITHUB,
                                run_id=run_id,
                                source_trigger=source_trigger,
                                resource_type="github.check_suite",
                                external_id=suite_ext,
                                api_endpoint=f"{gh_base}/repos/{owner}/{repo_name}/commits/{sha}/check-runs",
                                query_params={"suite": suite_id},
                                payload_body={
                                    **core_envelope_fields(
                                        connector=CONNECTION_PROVIDER_GITHUB,
                                        connection_id=connection_id,
                                        source_object_type="github.check_suite",
                                        source_object_id=suite_ext,
                                    ),
                                    "check_suite": suite_payload,
                                },
                                http_status=200,
                                idempotency_key=idem_key(ctx, run_id, f"github:check_suite:{suite_ext}"),
                            ):
                                n_ins += 1
                                check_suite_rows += 1
                                repo_check_suite_rows += 1
                    if len(check_runs) < 100:
                        break
            except GitHubApiError:
                continue

        # Workflows
        workflow_state = (
            existing_repo.get("workflow_runs")
            if isinstance(existing_repo.get("workflow_runs"), dict)
            else {}
        )
        workflow_page_raw = workflow_state.get("next_page", 1)
        try:
            workflow_page = max(1, int(workflow_page_raw))
        except (TypeError, ValueError):
            workflow_page = 1
        workflow_complete = False
        workflow_pages_fetched = 0
        try:
            for _ in range(settings.cortex_github_workflow_runs_max_pages_per_repo):
                runs, _ = list_repo_workflow_runs_page(
                    settings,
                    token,
                    owner=owner,
                    repo=repo_name,
                    page=workflow_page,
                )
                workflow_pages_fetched += 1
                for run in runs:
                    rid = run.get("id")
                    if rid is None:
                        continue
                    ext = f"{fn}:workflow_run:{rid}"[:512]
                    run_for_raw = ensure_github_workflow_run_repository_metadata(
                        run,
                        installation_repository=_repo,
                        repository_full_name=fn,
                    )
                    if append_raw(
                        session,
                        ctx=ctx,
                        tenant_id=tenant_id,
                        connection_id=connection_id,
                        connector=CONNECTION_PROVIDER_GITHUB,
                        run_id=run_id,
                        source_trigger=source_trigger,
                        resource_type="github.workflow_run",
                        external_id=ext,
                        api_endpoint=f"{gh_base}/repos/{owner}/{repo_name}/actions/runs",
                        query_params={"page": workflow_page},
                        payload_body={
                            **core_envelope_fields(
                                connector=CONNECTION_PROVIDER_GITHUB,
                                connection_id=connection_id,
                                source_object_type="github.workflow_run",
                                source_object_id=ext,
                            ),
                            "workflow_run": run_for_raw,
                        },
                        http_status=200,
                        idempotency_key=idem_key(ctx, run_id, f"github:workflow_run:{ext}"),
                    ):
                        n_ins += 1
                        workflow_rows += 1
                        repo_workflow_rows += 1
                if len(runs) < 100:
                    workflow_complete = True
                    workflow_page = 1
                    break
                workflow_page += 1
                if time.monotonic() - start_t >= settings.cortex_github_repo_time_budget_seconds:
                    budget_exhausted = True
                    break
        except GitHubApiError:
            pass

        # Deployments + statuses
        deployment_state = (
            existing_repo.get("deployments")
            if isinstance(existing_repo.get("deployments"), dict)
            else {}
        )
        deployment_page_raw = deployment_state.get("next_page", 1)
        try:
            deployment_page = max(1, int(deployment_page_raw))
        except (TypeError, ValueError):
            deployment_page = 1
        deployment_complete = False
        deployment_pages_fetched = 0
        try:
            for _ in range(settings.cortex_github_deployments_max_pages_per_repo):
                deployments = list_repo_deployments_page(
                    settings,
                    token,
                    owner=owner,
                    repo=repo_name,
                    page=deployment_page,
                )
                deployment_pages_fetched += 1
                for dep in deployments:
                    did = dep.get("id")
                    if not isinstance(did, int):
                        continue
                    dep_ext = f"{fn}:deployment:{did}"[:512]
                    if append_raw(
                        session,
                        ctx=ctx,
                        tenant_id=tenant_id,
                        connection_id=connection_id,
                        connector=CONNECTION_PROVIDER_GITHUB,
                        run_id=run_id,
                        source_trigger=source_trigger,
                        resource_type="github.deployment",
                        external_id=dep_ext,
                        api_endpoint=f"{gh_base}/repos/{owner}/{repo_name}/deployments",
                        query_params={"page": deployment_page},
                        payload_body={
                            **core_envelope_fields(
                                connector=CONNECTION_PROVIDER_GITHUB,
                                connection_id=connection_id,
                                source_object_type="github.deployment",
                                source_object_id=dep_ext,
                            ),
                            "deployment": dep,
                        },
                        http_status=200,
                        idempotency_key=idem_key(ctx, run_id, f"github:deployment:{dep_ext}"),
                    ):
                        n_ins += 1
                        deployment_rows += 1
                        repo_deploy_rows += 1
                    try:
                        for dstat_page in range(
                            1, settings.cortex_github_deployment_statuses_max_pages_per_deployment + 1
                        ):
                            statuses = list_deployment_statuses_page(
                                settings,
                                token,
                                owner=owner,
                                repo=repo_name,
                                deployment_id=did,
                                page=dstat_page,
                            )
                            for st in statuses:
                                sid = st.get("id")
                                if sid is None:
                                    continue
                                ext = f"{dep_ext}:status:{sid}"[:512]
                                if append_raw(
                                    session,
                                    ctx=ctx,
                                    tenant_id=tenant_id,
                                    connection_id=connection_id,
                                    connector=CONNECTION_PROVIDER_GITHUB,
                                    run_id=run_id,
                                    source_trigger=source_trigger,
                                    resource_type="github.deployment_status",
                                    external_id=ext,
                                    api_endpoint=f"{gh_base}/repos/{owner}/{repo_name}/deployments/{did}/statuses",
                                    query_params={"page": dstat_page},
                                    payload_body={
                                        **core_envelope_fields(
                                            connector=CONNECTION_PROVIDER_GITHUB,
                                            connection_id=connection_id,
                                            source_object_type="github.deployment_status",
                                            source_object_id=ext,
                                        ),
                                        "deployment_id": did,
                                        "status": st,
                                    },
                                    http_status=200,
                                    idempotency_key=idem_key(ctx, run_id, f"github:deployment_status:{ext}"),
                                ):
                                    n_ins += 1
                                    deployment_status_rows += 1
                                    repo_deploy_status_rows += 1
                            if len(statuses) < 100:
                                break
                    except GitHubApiError:
                        pass
                if len(deployments) < 100:
                    deployment_complete = True
                    deployment_page = 1
                    break
                deployment_page += 1
                if time.monotonic() - start_t >= settings.cortex_github_repo_time_budget_seconds:
                    budget_exhausted = True
                    break
        except GitHubApiError:
            pass

        # Branches
        branch_state = existing_repo.get("branches") if isinstance(existing_repo.get("branches"), dict) else {}
        branch_page_raw = branch_state.get("next_page", 1)
        try:
            branch_page = max(1, int(branch_page_raw))
        except (TypeError, ValueError):
            branch_page = 1
        branch_complete = False
        branch_pages_fetched = 0
        try:
            for _ in range(settings.cortex_github_branches_max_pages_per_repo):
                branches = list_repo_branches_page(
                    settings,
                    token,
                    owner=owner,
                    repo=repo_name,
                    page=branch_page,
                )
                branch_pages_fetched += 1
                for br in branches:
                    nm = br.get("name")
                    if not isinstance(nm, str) or not nm:
                        continue
                    ext = f"{fn}:branch:{nm}"[:512]
                    if append_raw(
                        session,
                        ctx=ctx,
                        tenant_id=tenant_id,
                        connection_id=connection_id,
                        connector=CONNECTION_PROVIDER_GITHUB,
                        run_id=run_id,
                        source_trigger=source_trigger,
                        resource_type="github.branch",
                        external_id=ext,
                        api_endpoint=f"{gh_base}/repos/{owner}/{repo_name}/branches",
                        query_params={"page": branch_page},
                        payload_body={
                            **core_envelope_fields(
                                connector=CONNECTION_PROVIDER_GITHUB,
                                connection_id=connection_id,
                                source_object_type="github.branch",
                                source_object_id=ext,
                            ),
                            "branch": br,
                        },
                        http_status=200,
                        idempotency_key=idem_key(ctx, run_id, f"github:branch:{ext}"),
                    ):
                        n_ins += 1
                        branch_rows += 1
                        repo_branch_rows += 1
                if len(branches) < 100:
                    branch_complete = True
                    branch_page = 1
                    break
                branch_page += 1
                if time.monotonic() - start_t >= settings.cortex_github_repo_time_budget_seconds:
                    budget_exhausted = True
                    break
        except GitHubApiError:
            pass

        # Tags
        tag_state = existing_repo.get("tags") if isinstance(existing_repo.get("tags"), dict) else {}
        tag_page_raw = tag_state.get("next_page", 1)
        try:
            tag_page = max(1, int(tag_page_raw))
        except (TypeError, ValueError):
            tag_page = 1
        tag_complete = False
        tag_pages_fetched = 0
        try:
            for _ in range(settings.cortex_github_tags_max_pages_per_repo):
                tags = list_repo_tags_page(
                    settings,
                    token,
                    owner=owner,
                    repo=repo_name,
                    page=tag_page,
                )
                tag_pages_fetched += 1
                for tag in tags:
                    nm = tag.get("name")
                    if not isinstance(nm, str) or not nm:
                        continue
                    ext = f"{fn}:tag:{nm}"[:512]
                    if append_raw(
                        session,
                        ctx=ctx,
                        tenant_id=tenant_id,
                        connection_id=connection_id,
                        connector=CONNECTION_PROVIDER_GITHUB,
                        run_id=run_id,
                        source_trigger=source_trigger,
                        resource_type="github.tag",
                        external_id=ext,
                        api_endpoint=f"{gh_base}/repos/{owner}/{repo_name}/tags",
                        query_params={"page": tag_page},
                        payload_body={
                            **core_envelope_fields(
                                connector=CONNECTION_PROVIDER_GITHUB,
                                connection_id=connection_id,
                                source_object_type="github.tag",
                                source_object_id=ext,
                            ),
                            "tag": tag,
                        },
                        http_status=200,
                        idempotency_key=idem_key(ctx, run_id, f"github:tag:{ext}"),
                    ):
                        n_ins += 1
                        tag_rows += 1
                        repo_tag_rows += 1
                if len(tags) < 100:
                    tag_complete = True
                    tag_page = 1
                    break
                tag_page += 1
                if time.monotonic() - start_t >= settings.cortex_github_repo_time_budget_seconds:
                    budget_exhausted = True
                    break
        except GitHubApiError:
            pass

        # Repo-wide commit comments (distinct from PR review comments)
        cc_state = (
            existing_repo.get("commit_comments")
            if isinstance(existing_repo.get("commit_comments"), dict)
            else {}
        )
        cc_page_raw = cc_state.get("next_page", 1)
        try:
            cc_page = max(1, int(cc_page_raw))
        except (TypeError, ValueError):
            cc_page = 1
        cc_complete = False
        cc_pages_fetched = 0
        try:
            for _ in range(settings.cortex_github_commit_comments_max_pages_per_repo):
                cc_items = list_repo_commit_comments_page(
                    settings,
                    token,
                    owner=owner,
                    repo=repo_name,
                    page=cc_page,
                )
                cc_pages_fetched += 1
                for cc in cc_items:
                    cid = cc.get("id")
                    if cid is None:
                        continue
                    sha = cc.get("commit_id")
                    if not isinstance(sha, str) or not sha:
                        continue
                    ext = f"{fn}:commit_comment:{cid}"[:512]
                    if append_raw(
                        session,
                        ctx=ctx,
                        tenant_id=tenant_id,
                        connection_id=connection_id,
                        connector=CONNECTION_PROVIDER_GITHUB,
                        run_id=run_id,
                        source_trigger=source_trigger,
                        resource_type="github.commit_comment",
                        external_id=ext,
                        api_endpoint=f"{gh_base}/repos/{owner}/{repo_name}/comments",
                        query_params={"page": cc_page},
                        payload_body={
                            **core_envelope_fields(
                                connector=CONNECTION_PROVIDER_GITHUB,
                                connection_id=connection_id,
                                source_object_type="github.commit_comment",
                                source_object_id=ext,
                            ),
                            "commit_sha": sha,
                            "comment": cc,
                        },
                        http_status=200,
                        idempotency_key=idem_key(ctx, run_id, f"github:commit_comment:{ext}"),
                    ):
                        n_ins += 1
                        commit_comment_rows += 1
                        repo_commit_comment_rows += 1
                if len(cc_items) < 100:
                    cc_complete = True
                    cc_page = 1
                    break
                cc_page += 1
                if time.monotonic() - start_t >= settings.cortex_github_repo_time_budget_seconds:
                    budget_exhausted = True
                    break
        except GitHubApiError:
            pass

        # GitHub issues (REST `/issues`; skips pull requests surfaced in that listing)
        iss_state = existing_repo.get("issues") if isinstance(existing_repo.get("issues"), dict) else {}
        iss_page_raw = iss_state.get("next_page", 1)
        try:
            iss_page = max(1, int(iss_page_raw))
        except (TypeError, ValueError):
            iss_page = 1
        iss_complete = False
        iss_pages_fetched = 0
        try:
            for _ in range(settings.cortex_github_issues_max_pages_per_repo):
                iss_items = list_repo_issues_page(
                    settings,
                    token,
                    owner=owner,
                    repo=repo_name,
                    page=iss_page,
                )
                iss_pages_fetched += 1
                for issue_row in iss_items:
                    if not isinstance(issue_row, dict):
                        continue
                    if isinstance(issue_row.get("pull_request"), dict):
                        continue
                    iid = issue_row.get("id")
                    if iid is None:
                        continue
                    ext = f"{fn}:issue:{iid}"[:512]
                    issue_body = dict(issue_row)
                    if not isinstance(issue_body.get("repository"), dict):
                        issue_body["repository"] = {"full_name": fn}
                    if append_raw(
                        session,
                        ctx=ctx,
                        tenant_id=tenant_id,
                        connection_id=connection_id,
                        connector=CONNECTION_PROVIDER_GITHUB,
                        run_id=run_id,
                        source_trigger=source_trigger,
                        resource_type="github.issue",
                        external_id=ext,
                        api_endpoint=f"{gh_base}/repos/{owner}/{repo_name}/issues",
                        query_params={"page": iss_page, "state": "all"},
                        payload_body={
                            **core_envelope_fields(
                                connector=CONNECTION_PROVIDER_GITHUB,
                                connection_id=connection_id,
                                source_object_type="github.issue",
                                source_object_id=ext,
                            ),
                            "issue": issue_body,
                        },
                        http_status=200,
                        idempotency_key=idem_key(ctx, run_id, f"github:issue:{ext}"),
                    ):
                        n_ins += 1
                        issue_rows += 1
                        repo_issue_rows += 1
                    inum = issue_row.get("number")
                    if isinstance(inum, int) and isinstance(iid, int):
                        try:
                            for tl_page in range(1, settings.cortex_github_timeline_max_pages_per_issue_or_pr + 1):
                                if time.monotonic() - start_t >= settings.cortex_github_repo_time_budget_seconds:
                                    budget_exhausted = True
                                    break
                                timeline = list_repo_issue_timeline_page(
                                    settings,
                                    token,
                                    owner=owner,
                                    repo=repo_name,
                                    issue_number=inum,
                                    page=tl_page,
                                )
                                for te in timeline:
                                    if not isinstance(te, dict):
                                        continue
                                    te_id = te.get("id")
                                    if te_id is None:
                                        continue
                                    tl_ext = f"{fn}:issue:{iid}:timeline_event:{te_id}"[:512]
                                    ts = te.get("created_at")
                                    ts_str = ts if isinstance(ts, str) else None
                                    if append_raw(
                                        session,
                                        ctx=ctx,
                                        tenant_id=tenant_id,
                                        connection_id=connection_id,
                                        connector=CONNECTION_PROVIDER_GITHUB,
                                        run_id=run_id,
                                        source_trigger=source_trigger,
                                        resource_type="github.issue_timeline_event",
                                        external_id=tl_ext,
                                        api_endpoint=f"{gh_base}/repos/{owner}/{repo_name}/issues/{inum}/timeline",
                                        query_params={"page": tl_page},
                                        payload_body={
                                            **core_envelope_fields(
                                                connector=CONNECTION_PROVIDER_GITHUB,
                                                connection_id=connection_id,
                                                source_object_type="github.issue_timeline_event",
                                                source_object_id=tl_ext,
                                            ),
                                            "id": te_id,
                                            "repository_full_name": fn,
                                            "issue_number": inum,
                                            "github_issue_id": iid,
                                            "timeline_event": te,
                                            "provider_event_timestamp": ts_str,
                                        },
                                        http_status=200,
                                        idempotency_key=idem_key(ctx, run_id, f"github:issue_timeline:{tl_ext}"),
                                    ):
                                        n_ins += 1
                                        issue_timeline_rows += 1
                                        repo_issue_timeline_rows += 1
                                if len(timeline) < 100:
                                    break
                        except GitHubApiError:
                            pass
                if len(iss_items) < 100:
                    iss_complete = True
                    iss_page = 1
                    break
                iss_page += 1
                if time.monotonic() - start_t >= settings.cortex_github_repo_time_budget_seconds:
                    budget_exhausted = True
                    break
        except GitHubApiError:
            pass

        # Releases (mapped to deployment semantics in canonical transform)
        rel_state = existing_repo.get("releases") if isinstance(existing_repo.get("releases"), dict) else {}
        rel_page_raw = rel_state.get("next_page", 1)
        try:
            rel_page = max(1, int(rel_page_raw))
        except (TypeError, ValueError):
            rel_page = 1
        rel_complete = False
        rel_pages_fetched = 0
        try:
            for _ in range(settings.cortex_github_releases_max_pages_per_repo):
                rel_items = list_repo_releases_page(
                    settings,
                    token,
                    owner=owner,
                    repo=repo_name,
                    page=rel_page,
                )
                rel_pages_fetched += 1
                for rel in rel_items:
                    rid = rel.get("id")
                    if rid is None:
                        continue
                    ext = f"{fn}:release:{rid}"[:512]
                    rel_body = dict(rel)
                    if not isinstance(rel_body.get("repository"), dict):
                        rel_body["repository"] = {"full_name": fn}
                    if append_raw(
                        session,
                        ctx=ctx,
                        tenant_id=tenant_id,
                        connection_id=connection_id,
                        connector=CONNECTION_PROVIDER_GITHUB,
                        run_id=run_id,
                        source_trigger=source_trigger,
                        resource_type="github.release",
                        external_id=ext,
                        api_endpoint=f"{gh_base}/repos/{owner}/{repo_name}/releases",
                        query_params={"page": rel_page},
                        payload_body={
                            **core_envelope_fields(
                                connector=CONNECTION_PROVIDER_GITHUB,
                                connection_id=connection_id,
                                source_object_type="github.release",
                                source_object_id=ext,
                            ),
                            "release": rel_body,
                        },
                        http_status=200,
                        idempotency_key=idem_key(ctx, run_id, f"github:release:{ext}"),
                    ):
                        n_ins += 1
                        release_rows += 1
                        repo_release_rows += 1
                if len(rel_items) < 100:
                    rel_complete = True
                    rel_page = 1
                    break
                rel_page += 1
                if time.monotonic() - start_t >= settings.cortex_github_repo_time_budget_seconds:
                    budget_exhausted = True
                    break
        except GitHubApiError:
            pass

        repo_patch_map[fn] = {
            "cursor_owner": "github.repository",
            "pull_requests": {
                "cursor_owner": "github.pull_request",
                "next_page": current_pulls_page,
                "backfill_complete": stream_backfill_complete(pagination_exhausted=pulls_complete),
                "pages_fetched_last_run": pull_pages_fetched,
                "rows_seen_last_run": repo_pr_rows,
            },
            "reviews": {
                "cursor_owner": "github.pull_request_review",
                "rows_seen_last_run": repo_review_rows,
            },
            "review_comments": {
                "cursor_owner": "github.pull_request_review_comment",
                "rows_seen_last_run": repo_review_comment_rows,
            },
            "issue_comments": {
                "cursor_owner": "github.issue_comment",
                "rows_seen_last_run": repo_issue_comment_rows,
            },
            "commits": {
                "cursor_owner": "github.commit",
                "next_page": commit_page,
                "backfill_complete": stream_backfill_complete(pagination_exhausted=commits_complete),
                "pages_fetched_last_run": commit_pages_fetched,
                "rows_seen_last_run": repo_commit_rows,
            },
            "check_runs": {
                "cursor_owner": "github.check_run",
                "rows_seen_last_run": repo_check_rows,
            },
            "workflow_runs": {
                "cursor_owner": "github.workflow_run",
                "next_page": workflow_page,
                "backfill_complete": stream_backfill_complete(pagination_exhausted=workflow_complete),
                "pages_fetched_last_run": workflow_pages_fetched,
                "rows_seen_last_run": repo_workflow_rows,
            },
            "deployments": {
                "cursor_owner": "github.deployment",
                "next_page": deployment_page,
                "backfill_complete": stream_backfill_complete(pagination_exhausted=deployment_complete),
                "pages_fetched_last_run": deployment_pages_fetched,
                "rows_seen_last_run": repo_deploy_rows,
                "status_rows_seen_last_run": repo_deploy_status_rows,
            },
            "branches": {
                "cursor_owner": "github.branch",
                "next_page": branch_page,
                "backfill_complete": stream_backfill_complete(pagination_exhausted=branch_complete),
                "pages_fetched_last_run": branch_pages_fetched,
                "rows_seen_last_run": repo_branch_rows,
            },
            "tags": {
                "cursor_owner": "github.tag",
                "next_page": tag_page,
                "backfill_complete": stream_backfill_complete(pagination_exhausted=tag_complete),
                "pages_fetched_last_run": tag_pages_fetched,
                "rows_seen_last_run": repo_tag_rows,
            },
            "check_suites": {
                "cursor_owner": "github.check_suite",
                "rows_seen_last_run": repo_check_suite_rows,
            },
            "commit_comments": {
                "cursor_owner": "github.commit_comment",
                "next_page": cc_page,
                "backfill_complete": stream_backfill_complete(pagination_exhausted=cc_complete),
                "pages_fetched_last_run": cc_pages_fetched,
                "rows_seen_last_run": repo_commit_comment_rows,
            },
            "releases": {
                "cursor_owner": "github.release",
                "next_page": rel_page,
                "backfill_complete": stream_backfill_complete(pagination_exhausted=rel_complete),
                "pages_fetched_last_run": rel_pages_fetched,
                "rows_seen_last_run": repo_release_rows,
            },
            "issues": {
                "cursor_owner": "github.issue",
                "next_page": iss_page,
                "backfill_complete": stream_backfill_complete(pagination_exhausted=iss_complete),
                "pages_fetched_last_run": iss_pages_fetched,
                "rows_seen_last_run": repo_issue_rows,
            },
            "review_threads": {
                "cursor_owner": "github.review_thread",
                "rows_seen_last_run": repo_review_thread_rows,
            },
            "issue_timeline_events": {
                "cursor_owner": "github.issue_timeline_event",
                "rows_seen_last_run": repo_issue_timeline_rows,
            },
            "pull_request_timeline_events": {
                "cursor_owner": "github.pull_request_timeline_event",
                "rows_seen_last_run": repo_pr_timeline_rows,
            },
            "last_sync_mode": ctx.sync_mode,
        }
        if budget_exhausted:
            break

    upsert_checkpoint(
        session,
        tenant_id=tenant_id,
        connection_id=connection_id,
        connector=CONNECTION_PROVIDER_GITHUB,
        scope_key=scope_ck,
        patch={
            "last_incremental_at": utc_now().isoformat(),
            "repos_fetched": n_ins,
            "github_installation_repos_pages": pages_fetched,
            "github_pull_requests_written": pr_rows,
            "github_reviews_written": review_rows,
            "github_review_comments_written": review_comment_rows,
            "github_issue_comments_written": issue_comment_rows,
            "github_commits_written": commit_rows,
            "github_check_runs_written": check_run_rows,
            "github_workflow_runs_written": workflow_rows,
            "github_deployments_written": deployment_rows,
            "github_deployment_statuses_written": deployment_status_rows,
            "github_branches_written": branch_rows,
            "github_tags_written": tag_rows,
            "github_check_suites_written": check_suite_rows,
            "github_commit_comments_written": commit_comment_rows,
            "github_releases_written": release_rows,
            "github_issues_written": issue_rows,
            "github_review_threads_written": review_thread_rows,
            "github_issue_timeline_events_written": issue_timeline_rows,
            "github_pull_request_timeline_events_written": pr_timeline_rows,
            "total_count_hint": total_hint,
            "streams": {
                "github": {
                    **people_patch,
                    "installation_repositories": ensure_stream_introduced_at(
                        {
                            "cursor_owner": "github.installation_repositories",
                            "last_page": pages_fetched,
                            "backfill_complete": stream_backfill_complete(pagination_exhausted=install_complete),
                        },
                    ),
                    "pull_requests": {
                        "cursor_owner": "github.pull_request",
                        "repos_processed": len(selected_repos),
                        "rows_written": pr_rows,
                    },
                    "pull_request_reviews": {"cursor_owner": "github.pull_request_review", "rows_written": review_rows},
                    "pull_request_review_comments": {
                        "cursor_owner": "github.pull_request_review_comment",
                        "rows_written": review_comment_rows,
                    },
                    "issue_comments": {"cursor_owner": "github.issue_comment", "rows_written": issue_comment_rows},
                    "commits": {"cursor_owner": "github.commit", "rows_written": commit_rows},
                    "check_runs": {"cursor_owner": "github.check_run", "rows_written": check_run_rows},
                    "workflow_runs": {"cursor_owner": "github.workflow_run", "rows_written": workflow_rows},
                    "deployments": {"cursor_owner": "github.deployment", "rows_written": deployment_rows},
                    "deployment_statuses": {
                        "cursor_owner": "github.deployment_status",
                        "rows_written": deployment_status_rows,
                    },
                    "branches": {"cursor_owner": "github.branch", "rows_written": branch_rows},
                    "tags": {"cursor_owner": "github.tag", "rows_written": tag_rows},
                    "check_suites": {"cursor_owner": "github.check_suite", "rows_written": check_suite_rows},
                    "commit_comments": {"cursor_owner": "github.commit_comment", "rows_written": commit_comment_rows},
                    "releases": {"cursor_owner": "github.release", "rows_written": release_rows},
                    "issues": {"cursor_owner": "github.issue", "rows_written": issue_rows},
                    "review_threads": {"cursor_owner": "github.review_thread", "rows_written": review_thread_rows},
                    "issue_timeline_events": {
                        "cursor_owner": "github.issue_timeline_event",
                        "rows_written": issue_timeline_rows,
                    },
                    "pull_request_timeline_events": {
                        "cursor_owner": "github.pull_request_timeline_event",
                        "rows_written": pr_timeline_rows,
                    },
                    "repos": repo_patch_map,
                    "repo_ring_index": next_repo_ring_index,
                    "resume_required": budget_exhausted,
                    "time_budget_seconds": settings.cortex_github_repo_time_budget_seconds,
                }
            },
            "meta": {
                "exhaust_depth": derive_exhaust_depth(
                    {
                        "users": people_patch.get("users", {}),
                        "installation_repositories": {
                            "cursor_owner": "github.repository",
                            "backfill_complete": stream_backfill_complete(
                                pagination_exhausted=install_complete,
                            ),
                        },
                    },
                ),
            },
        },
        sync_mode=ctx.checkpoint_sync_mode,
    )
    return n_ins

def pick_github_repos_round_robin(
    repos: list[tuple[str, str, dict[str, Any]]],
    *,
    ring_index: int,
    count: int,
) -> tuple[list[tuple[str, str, dict[str, Any]]], int]:
    if count <= 0 or not repos:
        return [], 0
    ordered = sorted(repos, key=lambda item: item[1])
    start = max(0, ring_index) % len(ordered)
    out: list[tuple[str, str, dict[str, Any]]] = []
    idx = start
    for _ in range(min(count, len(ordered))):
        out.append(ordered[idx])
        idx = (idx + 1) % len(ordered)
    return out, idx

