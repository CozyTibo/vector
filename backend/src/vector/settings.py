"""Application configuration (environment-driven)."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Self

from pydantic import Field, field_validator, model_validator
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
    post_connect_enqueue_ingestion: bool = Field(
        default=True,
        validation_alias="VECTOR_POST_CONNECT_INGESTION",
        description="Enqueue full sync after GitHub/Linear OAuth (disable for manual-only sync).",
    )
    ingestion_sweep_interval_seconds: int = Field(
        default=900,
        validation_alias="VECTOR_INGESTION_SWEEP_INTERVAL_SECONDS",
        description="Beat interval (seconds) for canonical lag sweep; 0 disables.",
    )
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
        default="channels:read,chat:write,users:read",
        validation_alias="SLACK_BOT_SCOPES",
        description="Comma-separated bot scopes for oauth.v2.authorize (must match Slack app).",
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
    openai_model: str = Field(default="gpt-4o-mini", validation_alias="OPENAI_MODEL")
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


def get_settings() -> Settings:
    """Build from current environment. Not cached — a stale `@lru_cache` hid edits to `.env`
    until process restart; connector OAuth looked \"not configured\" after adding Slack keys."""
    return Settings()


def _noop_settings_cache_clear() -> None:
    """Tests call `get_settings.cache_clear()` between env changes; caching was removed."""


get_settings.cache_clear = _noop_settings_cache_clear  # type: ignore[attr-defined]
