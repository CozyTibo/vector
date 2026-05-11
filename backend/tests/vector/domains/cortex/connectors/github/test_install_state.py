"""Install state token encoding."""

from __future__ import annotations

import os
import uuid
from collections.abc import Generator

import pytest

from vector.domains.cortex.connectors.github.errors import InvalidGitHubInstallStateError
from vector.domains.cortex.connectors.github.install_state import (
    create_install_state_token,
    parse_install_state_token,
)
from vector.settings import get_settings


@pytest.fixture(autouse=True)
def _minimal_env(monkeypatch: pytest.MonkeyPatch) -> Generator[None, None, None]:
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


def test_install_state_round_trip(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SECRET_KEY", "test-secret-key-at-least-32-characters-long!!")
    get_settings.cache_clear()
    settings = get_settings()
    tid = uuid.uuid4()
    uid = uuid.uuid4()
    raw = create_install_state_token(settings, tid, uid)
    parsed = parse_install_state_token(settings, raw)
    assert parsed.tenant_id == tid
    assert parsed.user_id == uid
    assert parsed.return_to is None


def test_install_state_return_to_round_trip(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SECRET_KEY", "test-secret-key-at-least-32-characters-long!!")
    get_settings.cache_clear()
    settings = get_settings()
    tid = uuid.uuid4()
    uid = uuid.uuid4()
    raw = create_install_state_token(
        settings,
        tid,
        uid,
        return_to="/app/onboarding",
    )
    parsed = parse_install_state_token(settings, raw)
    assert parsed.return_to == "/app/onboarding"


def test_install_state_tamper_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SECRET_KEY", "test-secret-key-at-least-32-characters-long!!")
    get_settings.cache_clear()
    settings = get_settings()
    tid = uuid.uuid4()
    uid = uuid.uuid4()
    raw = create_install_state_token(settings, tid, uid)
    bad = raw[:-3] + "xxx"
    with pytest.raises(InvalidGitHubInstallStateError):
        parse_install_state_token(settings, bad)


def test_install_state_wrong_secret_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SECRET_KEY", "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa")
    get_settings.cache_clear()
    settings_a = get_settings()
    tid = uuid.uuid4()
    uid = uuid.uuid4()
    token = create_install_state_token(settings_a, tid, uid)
    monkeypatch.setenv("SECRET_KEY", "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb")
    get_settings.cache_clear()
    settings_b = get_settings()
    with pytest.raises(InvalidGitHubInstallStateError):
        parse_install_state_token(settings_b, token)
