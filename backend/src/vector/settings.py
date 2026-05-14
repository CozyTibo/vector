"""Application configuration (environment-driven)."""

from __future__ import annotations

import os
import uuid
from pathlib import Path
from typing import Self

from pydantic import AliasChoices, Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def _dotenv_file_paths() -> tuple[Path, ...]:
    """Paths to load in order (later overrides earlier). Omit bogus paths.

    - **Monorepo host:** ``.../backend/src/vector/settings.py`` → repo root ``.env``, then cwd ``.env``.
    - **Docker image:** ``/app/src/vector/settings.py`` — ``parents[3]`` is ``/``; do **not** use it.
      Slack/GitHub/etc. must come from process env (``docker compose`` ``env_file`` / ``environment``).

    When ``VECTOR_SETTINGS_SKIP_DOTENV=1`` (set in ``tests/conftest.py`` before imports), skip files so
    ``monkeypatch`` / unconfigured connector tests are not overridden by a developer's repo ``.env``.
    """
    if os.environ.get("VECTOR_SETTINGS_SKIP_DOTENV") == "1":
        return ()
    here = Path(__file__).resolve()
    out: list[Path] = []
    try:
        if here.parents[2].name == "backend":
            root_env = here.parents[3] / ".env"
            if root_env.is_file():
                out.append(root_env)
    except IndexError:
        pass
    # Docker Compose mounts repo `.env` at `/app/.env`. Uvicorn `--reload` can run the worker with a
    # cwd other than `/app`, so `./.env` would miss the file while `DATABASE_URL` still works (set in
    # compose `environment:`). Always load the canonical mount when present.
    docker_app_env = Path("/app/.env")
    if docker_app_env.is_file():
        resolved_docker = docker_app_env.resolve()
        if not out or resolved_docker not in out:
            out.append(resolved_docker)
    cwd_env = Path(".env")
    if cwd_env.is_file():
        resolved = cwd_env.resolve()
        if resolved not in out:
            out.append(resolved)
    return tuple(out)


_DOTENV_FILES = _dotenv_file_paths()


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=_DOTENV_FILES if _DOTENV_FILES else None,
        env_file_encoding="utf-8",
        extra="ignore",
        # Docker / shells often export `FOO=` (empty). Without this, those override non-empty values
        # from `.env` files and connectors look "unconfigured" even when `/app/.env` is correct.
        env_ignore_empty=True,
    )

    database_url: str = Field(validation_alias="DATABASE_URL")
    redis_url: str = Field(default="", validation_alias="REDIS_URL")
    env: str = Field(default="development", validation_alias="ENV")
    secret_key: str = Field(
        default="dev-only-secret-key-min-32-chars-long!!",
        validation_alias="SECRET_KEY",
    )
    google_client_id: str = Field(default="", validation_alias="GOOGLE_CLIENT_ID")
    google_client_secret: str = Field(default="", validation_alias="GOOGLE_CLIENT_SECRET")
    google_redirect_uri: str = Field(
        default="http://localhost:8000/auth/google/callback",
        validation_alias="GOOGLE_REDIRECT_URI",
    )
    frontend_url: str = Field(
        default="http://localhost:5173",
        validation_alias="FRONTEND_URL",
    )
    session_cookie_name: str = Field(
        default="vector_session",
        validation_alias="SESSION_COOKIE_NAME",
    )
    session_ttl_seconds: int = Field(
        default=60 * 60 * 24 * 7,
        validation_alias="SESSION_TTL_SECONDS",
    )
    oauth_state_cookie_name: str = Field(
        default="vector_oauth",
        validation_alias="OAUTH_STATE_COOKIE_NAME",
    )
    github_app_id: str = Field(default="", validation_alias="GITHUB_APP_ID")
    github_app_private_key: str = Field(default="", validation_alias="GITHUB_APP_PRIVATE_KEY")
    github_app_private_key_path: str = Field(
        default="",
        validation_alias="GITHUB_APP_PRIVATE_KEY_PATH",
    )
    github_app_slug: str = Field(default="", validation_alias="GITHUB_APP_SLUG")
    github_client_id: str = Field(default="", validation_alias="GITHUB_CLIENT_ID")
    github_client_secret: str = Field(default="", validation_alias="GITHUB_CLIENT_SECRET")
    github_user_callback_url: str = Field(default="", validation_alias="GITHUB_USER_CALLBACK_URL")
    github_api_public_base_url: str = Field(
        default="http://127.0.0.1:8000",
        validation_alias="GITHUB_API_PUBLIC_BASE_URL",
    )
    linear_client_id: str = Field(default="", validation_alias="LINEAR_CLIENT_ID")
    linear_client_secret: str = Field(default="", validation_alias="LINEAR_CLIENT_SECRET")
    linear_redirect_uri: str = Field(default="", validation_alias="LINEAR_REDIRECT_URI")
    notion_client_id: str = Field(default="", validation_alias="NOTION_CLIENT_ID")
    notion_client_secret: str = Field(default="", validation_alias="NOTION_CLIENT_SECRET")
    notion_redirect_uri: str = Field(default="", validation_alias="NOTION_REDIRECT_URI")
    notion_version: str = Field(default="2022-06-28", validation_alias="NOTION_VERSION")
    calls_redirect_uri: str = Field(default="", validation_alias="CALLS_REDIRECT_URI")
    slack_client_id: str = Field(default="", validation_alias="SLACK_CLIENT_ID")
    slack_client_secret: str = Field(default="", validation_alias="SLACK_CLIENT_SECRET")
    slack_signing_secret: str = Field(
        default="",
        validation_alias="SLACK_SIGNING_SECRET",
        description="For verifying Slack Events API requests (optional until events are wired).",
    )
    slack_callback_url: str = Field(
        default="",
        validation_alias="SLACK_CALLBACK_URL",
        description="Full redirect URL registered in Slack app (e.g. https://xxx.ngrok-free.dev/slack/callback).",
    )
    slack_bot_scopes: str = Field(
        default=(
            "channels:read,channels:join,chat:write,im:history,im:write,users:read,usergroups:read"
        ),
        validation_alias="SLACK_BOT_SCOPES",
        description=(
            "Comma-separated bot scopes for oauth.v2.authorize (must match Slack app). "
            "channels:join for joining public channels in onboarding; im:history for message.im."
        ),
    )
    admin_password: str = Field(
        default="",
        validation_alias="ADMIN_PASSWORD",
        description="When set, enables /admin/* HTTP Basic (password only; username ignored).",
    )
    vector_use_mock_connectors: bool = Field(
        default=False,
        validation_alias="VECTOR_USE_MOCK_CONNECTORS",
        description="Local dev: use mock connectors (requires ENV=development).",
    )
    vector_mock_connector_base_url: str = Field(
        default="http://127.0.0.1:9183",
        validation_alias="VECTOR_MOCK_CONNECTOR_BASE_URL",
        description=(
            "Unified mock base: GitHub REST (poll sync) + Linear GraphQL only. "
            "GitHub user token and App JWT GET /app/installations/{id} always use api.github.com. "
            "Linear OAuth code exchange always uses https://api.linear.app/oauth/token."
        ),
    )
    vector_mock_seed: int = Field(
        default=42,
        validation_alias="VECTOR_MOCK_SEED",
        description="Deterministic seed for mock dataset generation.",
    )
    openai_api_key: str = Field(default="", validation_alias="OPENAI_API_KEY")
    openai_model: str = Field(
        default="gpt-5-mini",
        validation_alias="OPENAI_MODEL",
        description="Default Chat Completions model for non-onboarding features.",
    )
    openai_model_onboarding: str = Field(
        default="gpt-4o-mini",
        validation_alias="OPENAI_MODEL_ONBOARDING",
        description=(
            "Chat Completions model for product onboarding chat only (fast path). "
            "When empty, OPENAI_MODEL is used."
        ),
    )
    smtp_host: str = Field(
        default="",
        validation_alias="SMTP_HOST",
        description="SMTP host (Mailtrap dev or SES email-smtp.<region>.amazonaws.com).",
    )
    smtp_port: int = Field(default=587, validation_alias="SMTP_PORT")
    smtp_user: str = Field(default="", validation_alias="SMTP_USER")
    smtp_password: str = Field(
        default="",
        validation_alias=AliasChoices("SMTP_PASSWORD", "SMTP_PASS"),
    )
    smtp_use_tls: bool = Field(default=True, validation_alias="SMTP_USE_TLS")
    ses_configuration_set: str = Field(
        default="",
        validation_alias="SES_CONFIGURATION_SET",
        description=(
            "Optional SES configuration set name. When set, SMTP sender adds "
            "X-SES-CONFIGURATION-SET header for delivery/bounce event tracking."
        ),
    )
    email_from_address: str = Field(
        default="",
        validation_alias=AliasChoices("EMAIL_FROM_ADDRESS", "EMAIL_FROM"),
        description="RFC5322 From address (e.g. vector@angelcorp.ai).",
    )
    email_from_name: str = Field(default="Vector", validation_alias="EMAIL_FROM_NAME")
    waitlist_signup_email_enabled: bool = Field(
        default=True,
        validation_alias="VECTOR_WAITLIST_SIGNUP_EMAIL",
        description=(
            "Send the waitlist confirmation after email/password signup. "
            "Set false in pytest (or CI) to avoid real SMTP when integration tests register users."
        ),
    )
    onboarding_activation_email_enabled: bool = Field(
        default=True,
        validation_alias="VECTOR_ONBOARDING_ACTIVATION_EMAIL",
        description=(
            "Send onboarding activation when an admin enables workspace access (waitlist → onboarding). "
            "Set false in pytest (or CI) to avoid enqueueing SMTP when admin tests toggle access."
        ),
    )
    cortex_connector_migration_enabled: bool = Field(
        default=True,
        validation_alias="CORTEX_CONNECTOR_MIGRATION_ENABLED",
        description=(
            "Phase 01: master switch for Cortex-owned ingestion (default on). Set false only to "
            "disable Cortex routing globally (emergency / staged environments)."
        ),
    )
    cortex_connector_migration_calls: bool = Field(
        default=True,
        validation_alias="CORTEX_CONNECTOR_MIGRATION_CALLS",
        description="Cortex ingestion for calls (default on; requires master switch). Set false to opt out.",
    )
    cortex_connector_migration_github: bool = Field(
        default=True,
        validation_alias="CORTEX_CONNECTOR_MIGRATION_GITHUB",
        description="Cortex ingestion for GitHub (default on; requires master switch). Set false to opt out.",
    )
    cortex_connector_migration_linear: bool = Field(
        default=True,
        validation_alias="CORTEX_CONNECTOR_MIGRATION_LINEAR",
        description="Cortex ingestion for Linear (default on; requires master switch). Set false to opt out.",
    )
    cortex_connector_migration_notion: bool = Field(
        default=True,
        validation_alias="CORTEX_CONNECTOR_MIGRATION_NOTION",
        description="Cortex ingestion for Notion (default on; requires master switch). Set false to opt out.",
    )
    cortex_connector_migration_slack: bool = Field(
        default=True,
        validation_alias="CORTEX_CONNECTOR_MIGRATION_SLACK",
        description="Cortex ingestion for Slack (default on; requires master switch). Set false to opt out.",
    )
    cortex_connector_migration_calls_tenants: str = Field(
        default="",
        validation_alias="CORTEX_CONNECTOR_MIGRATION_CALLS_TENANTS",
        description="Optional comma-separated tenant UUID allowlist; empty = all tenants.",
    )
    cortex_connector_migration_github_tenants: str = Field(
        default="",
        validation_alias="CORTEX_CONNECTOR_MIGRATION_GITHUB_TENANTS",
        description="Optional comma-separated tenant UUID allowlist; empty = all tenants.",
    )
    cortex_connector_migration_linear_tenants: str = Field(
        default="",
        validation_alias="CORTEX_CONNECTOR_MIGRATION_LINEAR_TENANTS",
        description="Optional comma-separated tenant UUID allowlist; empty = all tenants.",
    )
    cortex_connector_migration_notion_tenants: str = Field(
        default="",
        validation_alias="CORTEX_CONNECTOR_MIGRATION_NOTION_TENANTS",
        description="Optional comma-separated tenant UUID allowlist; empty = all tenants.",
    )
    cortex_connector_migration_slack_tenants: str = Field(
        default="",
        validation_alias="CORTEX_CONNECTOR_MIGRATION_SLACK_TENANTS",
        description="Optional comma-separated tenant UUID allowlist; empty = all tenants.",
    )
    cortex_ingestion_scheduler_enabled: bool = Field(
        default=False,
        validation_alias="CORTEX_INGESTION_SCHEDULER_ENABLED",
        description=(
            "Phase 01 Step 2: Celery Beat dispatches scheduled sync ticks when true (requires worker "
            "listening on cortex_live queue + migration flags routing tenants). "
            "Default is false — set true in production when Beat + cortex_live workers are ready."
        ),
    )
    cortex_ingestion_scheduler_interval_seconds: int = Field(
        default=1800,
        ge=60,
        validation_alias="CORTEX_INGESTION_SCHEDULER_INTERVAL_SECONDS",
        description=(
            "Beat cadence for scheduler ticks (seconds). Restart celery-beat after changing; mirrors "
            "beat_schedule in celery_app when env is set at process start."
        ),
    )
    cortex_ingestion_min_gap_seconds: int = Field(
        default=120,
        ge=0,
        validation_alias="CORTEX_INGESTION_MIN_GAP_SECONDS",
        description=(
            "Minimum seconds between enqueueing the same tenant×connector scheduled sync "
            "(uses connector_sync_state.last_incremental_at)."
        ),
    )
    cortex_ingestion_verify_after_sync: bool = Field(
        default=True,
        validation_alias="CORTEX_INGESTION_VERIFY_AFTER_SYNC",
        description=(
            "Phase 01 Step 5: after a successful ingestion run, execute read-only invariant probes "
            "and attach the report to the task response (disable in hot paths if needed)."
        ),
    )
    cortex_raw_memory_enforcement_mode: str = Field(
        default="progressive",
        validation_alias="CORTEX_RAW_MEMORY_ENFORCEMENT_MODE",
        description=(
            "Phase 02 Step 11 enforcement posture: observe|progressive|strict. "
            "progressive blocks catastrophic trust failures only and annotates would-block decisions."
        ),
    )
    cortex_github_installation_repos_max_pages: int = Field(
        default=100,
        ge=1,
        le=500,
        validation_alias="CORTEX_GITHUB_INSTALLATION_REPOS_MAX_PAGES",
        description=(
            "Max pages of GET /installation/repositories per sync (100 repos/page max). "
            "Increase for large installs; each page is one API call."
        ),
    )
    cortex_slack_users_max_pages: int = Field(
        default=50,
        ge=1,
        le=500,
        validation_alias="CORTEX_SLACK_USERS_MAX_PAGES",
        description="Max users.list cursor pages per Slack ingestion sync (~200 users/page).",
    )
    cortex_slack_conversations_max_pages: int = Field(
        default=50,
        ge=1,
        le=500,
        validation_alias="CORTEX_SLACK_CONVERSATIONS_MAX_PAGES",
        description="Max conversations.list cursor pages per Slack ingestion sync.",
    )
    cortex_slack_conversation_types: str = Field(
        default="public_channel,private_channel",
        validation_alias="CORTEX_SLACK_CONVERSATION_TYPES",
        description=(
            "Comma-separated Slack conversation types for conversations.list. "
            "Default excludes im/mpim unless policy explicitly allows."
        ),
    )
    cortex_slack_history_channels_per_sync: int = Field(
        default=5,
        ge=0,
        le=50,
        validation_alias="CORTEX_SLACK_HISTORY_CHANNELS_PER_SYNC",
        description=(
            "After listing channels, fetch conversations.history for up to N channels per sync "
            "(0 disables message history in this pass)."
        ),
    )
    cortex_slack_conversations_history_limit: int = Field(
        default=200,
        ge=1,
        le=1000,
        validation_alias="CORTEX_SLACK_CONVERSATIONS_HISTORY_LIMIT",
        description="Slack conversations.history `limit` (most recent messages in the window).",
    )
    cortex_slack_history_max_pages_per_channel: int = Field(
        default=5,
        ge=1,
        le=200,
        validation_alias="CORTEX_SLACK_HISTORY_MAX_PAGES_PER_CHANNEL",
        description=(
            "Max conversations.history pages per channel per sync (supports resumable backfill "
            "with checkpointed next_cursor)."
        ),
    )
    cortex_slack_threads_per_sync: int = Field(
        default=100,
        ge=0,
        le=1000,
        validation_alias="CORTEX_SLACK_THREADS_PER_SYNC",
        description="Max thread roots to process via conversations.replies per sync.",
    )
    cortex_slack_replies_max_pages_per_thread: int = Field(
        default=3,
        ge=1,
        le=100,
        validation_alias="CORTEX_SLACK_REPLIES_MAX_PAGES_PER_THREAD",
        description="Max conversations.replies pages per thread root per sync.",
    )
    cortex_slack_channel_time_budget_seconds: int = Field(
        default=20,
        ge=1,
        le=600,
        validation_alias="CORTEX_SLACK_CHANNEL_TIME_BUDGET_SECONDS",
        description=(
            "Soft per-run time budget for Slack channel/deep history loop before checkpoint-and-resume."
        ),
    )
    cortex_slack_backfill_oldest_ts: str = Field(
        default="",
        validation_alias="CORTEX_SLACK_BACKFILL_OLDEST_TS",
        description=(
            "Optional Slack oldest timestamp floor for backfill mode (Unix ts string). "
            "Empty means workspace/API default window."
        ),
    )
    cortex_linear_issues_first: int = Field(
        default=50,
        ge=1,
        le=250,
        validation_alias="CORTEX_LINEAR_ISSUES_FIRST",
        description="How many Linear issues to fetch per sync (GraphQL `issues(first: n)`).",
    )
    cortex_linear_issues_max_pages_per_sync: int = Field(
        default=10,
        ge=1,
        le=500,
        validation_alias="CORTEX_LINEAR_ISSUES_MAX_PAGES_PER_SYNC",
        description="Max paginated `issues` pages per Linear sync before checkpoint resume.",
    )
    cortex_linear_stream_first: int = Field(
        default=100,
        ge=1,
        le=250,
        validation_alias="CORTEX_LINEAR_STREAM_FIRST",
        description="Default page size for non-issue Linear GraphQL streams.",
    )
    cortex_linear_comments_max_pages_per_sync: int = Field(
        default=5,
        ge=1,
        le=500,
        validation_alias="CORTEX_LINEAR_COMMENTS_MAX_PAGES_PER_SYNC",
        description="Max paginated `comments` pages per Linear sync.",
    )
    cortex_linear_projects_max_pages_per_sync: int = Field(
        default=3,
        ge=1,
        le=500,
        validation_alias="CORTEX_LINEAR_PROJECTS_MAX_PAGES_PER_SYNC",
        description="Max paginated `projects` pages per Linear sync.",
    )
    cortex_linear_cycles_max_pages_per_sync: int = Field(
        default=3,
        ge=1,
        le=500,
        validation_alias="CORTEX_LINEAR_CYCLES_MAX_PAGES_PER_SYNC",
        description="Max paginated `cycles` pages per Linear sync.",
    )
    cortex_linear_issue_relations_max_pages_per_sync: int = Field(
        default=5,
        ge=1,
        le=500,
        validation_alias="CORTEX_LINEAR_ISSUE_RELATIONS_MAX_PAGES_PER_SYNC",
        description="Max paginated `issueRelations` pages per Linear sync.",
    )
    cortex_linear_issue_labels_max_pages_per_sync: int = Field(
        default=3,
        ge=1,
        le=500,
        validation_alias="CORTEX_LINEAR_ISSUE_LABELS_MAX_PAGES_PER_SYNC",
        description="Max paginated `issueLabels` pages per Linear sync.",
    )
    cortex_linear_initiatives_max_pages_per_sync: int = Field(
        default=3,
        ge=1,
        le=500,
        validation_alias="CORTEX_LINEAR_INITIATIVES_MAX_PAGES_PER_SYNC",
        description="Max paginated `initiatives` pages per Linear sync.",
    )
    cortex_linear_project_updates_max_pages_per_sync: int = Field(
        default=3,
        ge=1,
        le=500,
        validation_alias="CORTEX_LINEAR_PROJECT_UPDATES_MAX_PAGES_PER_SYNC",
        description="Max paginated `projectUpdates` pages per Linear sync.",
    )
    cortex_linear_time_budget_seconds: int = Field(
        default=25,
        ge=1,
        le=600,
        validation_alias="CORTEX_LINEAR_TIME_BUDGET_SECONDS",
        description="Soft per-run Linear deep-ingestion budget before checkpoint-and-resume.",
    )
    cortex_notion_search_page_size: int = Field(
        default=50,
        ge=1,
        le=100,
        validation_alias="CORTEX_NOTION_SEARCH_PAGE_SIZE",
        description="Notion `/search` page size for organizational exhaust traversal.",
    )
    cortex_notion_search_max_pages_per_sync: int = Field(
        default=8,
        ge=1,
        le=200,
        validation_alias="CORTEX_NOTION_SEARCH_MAX_PAGES_PER_SYNC",
        description="Max Notion `/search` pages processed per sync before checkpoint resume.",
    )
    cortex_notion_databases_per_sync: int = Field(
        default=40,
        ge=1,
        le=500,
        validation_alias="CORTEX_NOTION_DATABASES_PER_SYNC",
        description="Max discovered Notion databases to process per sync.",
    )
    cortex_notion_database_query_page_size: int = Field(
        default=100,
        ge=1,
        le=100,
        validation_alias="CORTEX_NOTION_DATABASE_QUERY_PAGE_SIZE",
        description="Notion database query page size (`/databases/{id}/query`).",
    )
    cortex_notion_database_query_max_pages_per_database: int = Field(
        default=5,
        ge=1,
        le=200,
        validation_alias="CORTEX_NOTION_DATABASE_QUERY_MAX_PAGES_PER_DATABASE",
        description="Max pages for each Notion database query stream per sync.",
    )
    cortex_notion_blocks_page_size: int = Field(
        default=100,
        ge=1,
        le=100,
        validation_alias="CORTEX_NOTION_BLOCKS_PAGE_SIZE",
        description="Notion block children page size (`/blocks/{id}/children`).",
    )
    cortex_notion_blocks_max_pages_per_parent: int = Field(
        default=3,
        ge=1,
        le=200,
        validation_alias="CORTEX_NOTION_BLOCKS_MAX_PAGES_PER_PARENT",
        description="Max block-children pages fetched for a parent per sync.",
    )
    cortex_notion_blocks_parents_per_sync: int = Field(
        default=100,
        ge=1,
        le=2000,
        validation_alias="CORTEX_NOTION_BLOCKS_PARENTS_PER_SYNC",
        description="Max distinct page/block parents traversed for children per sync.",
    )
    cortex_notion_time_budget_seconds: int = Field(
        default=25,
        ge=1,
        le=600,
        validation_alias="CORTEX_NOTION_TIME_BUDGET_SECONDS",
        description="Soft per-run Notion deep-ingestion budget before checkpoint-and-resume.",
    )
    cortex_calls_events_page_size: int = Field(
        default=100,
        ge=1,
        le=250,
        validation_alias="CORTEX_CALLS_EVENTS_PAGE_SIZE",
        description="Calls meetings/events page size per API page.",
    )
    cortex_calls_events_max_pages_per_sync: int = Field(
        default=8,
        ge=1,
        le=500,
        validation_alias="CORTEX_CALLS_EVENTS_MAX_PAGES_PER_SYNC",
        description="Max Calls events pages processed per sync before checkpoint resume.",
    )
    cortex_calls_time_budget_seconds: int = Field(
        default=25,
        ge=1,
        le=600,
        validation_alias="CORTEX_CALLS_TIME_BUDGET_SECONDS",
        description="Soft per-run Calls deep-ingestion budget before checkpoint-and-resume.",
    )
    cortex_github_pr_fetch_max_repos: int = Field(
        default=8,
        ge=0,
        le=200,
        validation_alias="CORTEX_GITHUB_PR_FETCH_MAX_REPOS",
        description="After repo list sync, fetch open+closed PRs for up to this many repos (0 disables PR fetch).",
    )
    cortex_github_prs_per_repo: int = Field(
        default=30,
        ge=1,
        le=100,
        validation_alias="CORTEX_GITHUB_PRS_PER_REPO",
        description="Max pull requests per repo per sync (GitHub REST `/pulls` first page).",
    )
    cortex_github_prs_max_pages_per_repo: int = Field(
        default=5,
        ge=1,
        le=200,
        validation_alias="CORTEX_GITHUB_PRS_MAX_PAGES_PER_REPO",
        description="Max paginated `/pulls` pages per repo per sync.",
    )
    cortex_github_reviews_max_pages_per_pr: int = Field(
        default=2,
        ge=1,
        le=100,
        validation_alias="CORTEX_GITHUB_REVIEWS_MAX_PAGES_PER_PR",
        description="Max pages for `/pulls/{number}/reviews` per PR per sync.",
    )
    cortex_github_review_comments_max_pages_per_pr: int = Field(
        default=2,
        ge=1,
        le=100,
        validation_alias="CORTEX_GITHUB_REVIEW_COMMENTS_MAX_PAGES_PER_PR",
        description="Max pages for `/pulls/{number}/comments` per PR per sync.",
    )
    cortex_github_issue_comments_max_pages_per_pr: int = Field(
        default=2,
        ge=1,
        le=100,
        validation_alias="CORTEX_GITHUB_ISSUE_COMMENTS_MAX_PAGES_PER_PR",
        description="Max pages for `/issues/{number}/comments` per PR per sync.",
    )
    cortex_github_commits_max_pages_per_repo: int = Field(
        default=2,
        ge=1,
        le=100,
        validation_alias="CORTEX_GITHUB_COMMITS_MAX_PAGES_PER_REPO",
        description="Max pages for `/repos/{owner}/{repo}/commits` per repo per sync.",
    )
    cortex_github_check_runs_max_pages_per_pr: int = Field(
        default=2,
        ge=1,
        le=100,
        validation_alias="CORTEX_GITHUB_CHECK_RUNS_MAX_PAGES_PER_PR",
        description="Max pages for `/commits/{sha}/check-runs` per PR head sha per sync.",
    )
    cortex_github_workflow_runs_max_pages_per_repo: int = Field(
        default=2,
        ge=1,
        le=100,
        validation_alias="CORTEX_GITHUB_WORKFLOW_RUNS_MAX_PAGES_PER_REPO",
        description="Max pages for `/actions/runs` per repo per sync.",
    )
    cortex_github_deployments_max_pages_per_repo: int = Field(
        default=2,
        ge=1,
        le=100,
        validation_alias="CORTEX_GITHUB_DEPLOYMENTS_MAX_PAGES_PER_REPO",
        description="Max pages for `/deployments` per repo per sync.",
    )
    cortex_github_deployment_statuses_max_pages_per_deployment: int = Field(
        default=2,
        ge=1,
        le=100,
        validation_alias="CORTEX_GITHUB_DEPLOYMENT_STATUSES_MAX_PAGES_PER_DEPLOYMENT",
        description="Max pages for deployment statuses per deployment per sync.",
    )
    cortex_github_branches_max_pages_per_repo: int = Field(
        default=2,
        ge=1,
        le=100,
        validation_alias="CORTEX_GITHUB_BRANCHES_MAX_PAGES_PER_REPO",
        description="Max pages for `/branches` per repo per sync.",
    )
    cortex_github_tags_max_pages_per_repo: int = Field(
        default=2,
        ge=1,
        le=100,
        validation_alias="CORTEX_GITHUB_TAGS_MAX_PAGES_PER_REPO",
        description="Max pages for `/tags` per repo per sync.",
    )
    cortex_github_commit_comments_max_pages_per_repo: int = Field(
        default=2,
        ge=1,
        le=100,
        validation_alias="CORTEX_GITHUB_COMMIT_COMMENTS_MAX_PAGES_PER_REPO",
        description="Max pages for repo-wide `/comments` (commit comments) per repo per sync.",
    )
    cortex_github_releases_max_pages_per_repo: int = Field(
        default=2,
        ge=1,
        le=100,
        validation_alias="CORTEX_GITHUB_RELEASES_MAX_PAGES_PER_REPO",
        description="Max pages for `/releases` per repo per sync.",
    )
    cortex_github_issues_max_pages_per_repo: int = Field(
        default=2,
        ge=1,
        le=100,
        validation_alias="CORTEX_GITHUB_ISSUES_MAX_PAGES_PER_REPO",
        description="Max pages for `/issues` per repo per sync.",
    )
    cortex_github_timeline_max_pages_per_issue_or_pr: int = Field(
        default=10,
        ge=1,
        le=100,
        validation_alias="CORTEX_GITHUB_TIMELINE_MAX_PAGES_PER_ISSUE_OR_PR",
        description="Max pages for `/issues/{n}/timeline` per issue or pull request number per sync.",
    )
    cortex_github_repo_time_budget_seconds: int = Field(
        default=25,
        ge=1,
        le=600,
        validation_alias="CORTEX_GITHUB_REPO_TIME_BUDGET_SECONDS",
        description="Soft per-run GitHub deep-ingestion budget before checkpoint-and-resume.",
    )

    @field_validator("github_app_private_key", mode="before")
    @classmethod
    def expand_pem_newlines(cls, value: object) -> object:
        if isinstance(value, str) and "\\n" in value:
            return value.replace("\\n", "\n")
        return value

    @field_validator("github_client_secret", mode="before")
    @classmethod
    def strip_github_client_secret_quotes(cls, value: object) -> object:
        if isinstance(value, str) and len(value) >= 2 and value[0] == value[-1] == '"':
            return value[1:-1]
        return value

    @field_validator("linear_client_secret", mode="before")
    @classmethod
    def strip_linear_client_secret_quotes(cls, value: object) -> object:
        if isinstance(value, str) and len(value) >= 2 and value[0] == value[-1] == '"':
            return value[1:-1]
        return value

    @field_validator("slack_client_secret", mode="before")
    @classmethod
    def strip_slack_client_secret_quotes(cls, value: object) -> object:
        if isinstance(value, str) and len(value) >= 2 and value[0] == value[-1] == '"':
            return value[1:-1]
        return value

    @model_validator(mode="after")
    def load_github_private_key_from_path(self) -> Self:
        """When set, load PEM from `GITHUB_APP_PRIVATE_KEY_PATH` (replaces env PEM)."""
        raw_path = self.github_app_private_key_path.strip()
        if raw_path:
            pem = Path(raw_path).expanduser().read_text(encoding="utf-8")
            if pem.strip():
                object.__setattr__(self, "github_app_private_key", pem)
        return self

    @model_validator(mode="after")
    def enforce_mock_connectors_local_only(self) -> Self:
        """Mock connectors are allowed only in local development; forbidden in prod/CI-like envs."""
        env = self.env.strip().lower()
        if self.vector_use_mock_connectors and env != "development":
            msg = "VECTOR_USE_MOCK_CONNECTORS=true is only allowed when ENV=development"
            raise ValueError(msg)
        if env in ("staging", "production") and self.vector_use_mock_connectors:
            msg = "VECTOR_USE_MOCK_CONNECTORS must be false when ENV is staging or production"
            raise ValueError(msg)
        return self

    def github_rest_api_base_url(self) -> str:
        """Base for GitHub REST (poll sync, installation access token POST)."""
        if self.vector_use_mock_connectors:
            return self.vector_mock_connector_base_url.rstrip("/")
        return "https://api.github.com"

    def github_rest_api_app_install_base_url(self) -> str:
        """App JWT GET /app/installations/{id} during OAuth callback — always GitHub.

        Installation IDs from the real install flow exist only on api.github.com; the local REST
        mock cannot validate App JWTs or return that record. Poll sync still uses
        `github_rest_api_base_url()` (mock when enabled).
        """
        return "https://api.github.com"

    def linear_graphql_url(self) -> str:
        """GraphQL for Step 1 sync / bulk reads — mock base when `VECTOR_USE_MOCK_CONNECTORS`."""
        if self.vector_use_mock_connectors:
            return f"{self.vector_mock_connector_base_url.rstrip('/')}/linear/graphql"
        return "https://api.linear.app/graphql"

    def linear_graphql_oauth_profile_url(self) -> str:
        """Post-OAuth viewer/org lookup only — always Linear production.

        Uses the real access token from `api.linear.app/oauth/token`. Keeps OAuth working when
        the backend runs in Docker (mock GraphQL on 127.0.0.1 is unreachable from the container).
        """
        return "https://api.linear.app/graphql"

    def linear_oauth_token_url(self) -> str:
        """Always real Linear — OAuth codes are issued by linear.app, not the mock."""
        return "https://api.linear.app/oauth/token"

    def notion_oauth_authorize_url(self) -> str:
        return "https://api.notion.com/v1/oauth/authorize"

    def notion_oauth_token_url(self) -> str:
        return "https://api.notion.com/v1/oauth/token"

    def notion_api_base_url(self) -> str:
        if self.vector_use_mock_connectors:
            return f"{self.vector_mock_connector_base_url.rstrip('/')}/notion/v1"
        return "https://api.notion.com/v1"

    def calls_google_calendar_events_base_url(self) -> str:
        if self.vector_use_mock_connectors:
            return f"{self.vector_mock_connector_base_url.rstrip('/')}/google-calendar/v3"
        return "https://www.googleapis.com/calendar/v3"

    def cortex_migration_route_active(self, connector_id: str, tenant_id: uuid.UUID) -> bool:
        """True when migration flags route this connector×tenant onto the Cortex ingestion path."""
        if not self.cortex_connector_migration_enabled:
            return False
        flag_by_id = {
            "calls": self.cortex_connector_migration_calls,
            "github": self.cortex_connector_migration_github,
            "linear": self.cortex_connector_migration_linear,
            "notion": self.cortex_connector_migration_notion,
            "slack": self.cortex_connector_migration_slack,
        }
        if not flag_by_id.get(connector_id):
            return False
        allow = self._cortex_migration_tenant_allowlist(connector_id)
        if allow is None:
            return True
        return tenant_id in allow

    def _cortex_migration_tenant_allowlist(self, connector_id: str) -> frozenset[uuid.UUID] | None:
        raw_by_id = {
            "calls": self.cortex_connector_migration_calls_tenants,
            "github": self.cortex_connector_migration_github_tenants,
            "linear": self.cortex_connector_migration_linear_tenants,
            "notion": self.cortex_connector_migration_notion_tenants,
            "slack": self.cortex_connector_migration_slack_tenants,
        }
        raw = (raw_by_id.get(connector_id) or "").strip()
        if not raw:
            return None
        parsed: set[uuid.UUID] = set()
        for part in raw.split(","):
            p = part.strip()
            if not p:
                continue
            try:
                parsed.add(uuid.UUID(p))
            except ValueError:
                continue
        if not parsed:
            return None
        return frozenset(parsed)

    def calls_google_oauth_authorize_url(self) -> str:
        return "https://accounts.google.com/o/oauth2/v2/auth"

    def calls_google_oauth_token_url(self) -> str:
        return "https://oauth2.googleapis.com/token"

    @property
    def email_is_configured(self) -> bool:
        """True when SMTP + From are set (Mailtrap, SES SMTP, etc.)."""
        return bool(self.smtp_host.strip() and self.email_from_address.strip())


def get_settings() -> Settings:
    """Build from current environment. Not cached — a stale `@lru_cache` hid edits to `.env`
    until process restart; connector OAuth looked \"not configured\" after adding Slack keys."""
    return Settings()


def _noop_settings_cache_clear() -> None:
    """Tests call `get_settings.cache_clear()` between env changes; caching was removed."""


get_settings.cache_clear = _noop_settings_cache_clear  # type: ignore[attr-defined]
