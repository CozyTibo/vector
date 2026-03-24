"""Application configuration (environment-driven)."""

from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    database_url: str = Field(validation_alias="DATABASE_URL")
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


@lru_cache
def get_settings() -> Settings:
    return Settings()
