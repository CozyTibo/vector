"""Defaults for OPENAI_MODEL vs OPENAI_MODEL_ONBOARDING."""

from __future__ import annotations

import pytest

from vector.settings import Settings, get_settings


@pytest.fixture(autouse=True)
def _database_url(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://test:test@localhost:5432/vector_test")


def test_default_global_model_is_gpt5_mini_and_onboarding_is_4o_mini(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("OPENAI_MODEL", raising=False)
    monkeypatch.delenv("OPENAI_MODEL_ONBOARDING", raising=False)
    get_settings.cache_clear()
    s = Settings()
    assert s.openai_model == "gpt-5-mini"
    assert s.openai_model_onboarding == "gpt-4o-mini"
