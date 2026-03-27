"""Application configuration (environment-driven)."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Self

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
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
    admin_password: str = Field(
        default="",
        validation_alias="ADMIN_PASSWORD",
        description="When set, enables /admin/* HTTP Basic (password only; username ignored).",
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

    @model_validator(mode="after")
    def load_github_private_key_from_path(self) -> Self:
        """When set, load PEM from `GITHUB_APP_PRIVATE_KEY_PATH` (replaces env PEM)."""
        raw_path = self.github_app_private_key_path.strip()
        if raw_path:
            pem = Path(raw_path).expanduser().read_text(encoding="utf-8")
            if pem.strip():
                object.__setattr__(self, "github_app_private_key", pem)
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
