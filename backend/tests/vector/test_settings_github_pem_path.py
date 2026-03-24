"""Settings: load GitHub PEM from file path."""

from __future__ import annotations

import os
from collections.abc import Generator
from pathlib import Path

import pytest

from vector.settings import get_settings


@pytest.fixture(autouse=True)
def _db_url(monkeypatch: pytest.MonkeyPatch) -> Generator[None, None, None]:
    monkeypatch.setenv(
        "DATABASE_URL",
        os.environ.get(
            "DATABASE_URL",
            "postgresql+psycopg://vector:vector@127.0.0.1:5432/vector",
        ),
    )
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def test_github_private_key_path_overrides_env(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    pem = "-----BEGIN TEST KEY-----\nabc\n-----END TEST KEY-----\n"
    p = tmp_path / "gh.pem"
    p.write_text(pem, encoding="utf-8")
    monkeypatch.setenv("GITHUB_APP_PRIVATE_KEY", "WRONG")
    monkeypatch.setenv("GITHUB_APP_PRIVATE_KEY_PATH", str(p))
    get_settings.cache_clear()
    settings = get_settings()
    assert "BEGIN TEST KEY" in settings.github_app_private_key
    assert "WRONG" not in settings.github_app_private_key
