"""§6 Step 6 — manager insights coordination env flags on Settings."""

from __future__ import annotations

import os

import pytest

from vector.settings import Settings, get_settings


@pytest.fixture(autouse=True)
def _database_url_for_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://test:test@localhost:5432/vector_test")


def test_coordination_flags_default_false() -> None:
    old = {k: os.environ.pop(k, None) for k in _FLAG_ENVS}
    get_settings.cache_clear()
    try:
        os.environ["ENV"] = "development"
        s = Settings()
        assert s.vector_manager_insights_perception_llm is False
        assert s.vector_manager_insights_include_execution_graph is False
        assert s.vector_manager_insights_skip_narrative_steps is False
        assert s.vector_manager_insights_gaps_use_graph is False
        assert s.vector_manager_insights_hold_start_affected_wi_threshold == 2
        assert s.vector_manager_insights_llm_interpretation is False
    finally:
        get_settings.cache_clear()
        _restore_all(old)


def test_coordination_flags_env_true() -> None:
    old = {k: os.environ.pop(k, None) for k in _FLAG_ENVS}
    get_settings.cache_clear()
    try:
        os.environ["ENV"] = "development"
        for k in _FLAG_ENVS:
            os.environ[k] = "true"
        s = Settings()
        assert s.vector_manager_insights_perception_llm is True
        assert s.vector_manager_insights_include_execution_graph is True
        assert s.vector_manager_insights_skip_narrative_steps is True
        assert s.vector_manager_insights_gaps_use_graph is True
        assert s.vector_manager_insights_hold_start_affected_wi_threshold == 2
        assert s.vector_manager_insights_llm_interpretation is True
    finally:
        get_settings.cache_clear()
        _restore_all(old)


_FLAG_ENVS = (
    "VECTOR_MANAGER_INSIGHTS_PERCEPTION_LLM",
    "VECTOR_MANAGER_INSIGHTS_INCLUDE_EXECUTION_GRAPH",
    "VECTOR_MANAGER_INSIGHTS_SKIP_NARRATIVE_STEPS",
    "VECTOR_MANAGER_INSIGHTS_GAPS_USE_GRAPH",
    "VECTOR_MANAGER_INSIGHTS_LLM_INTERPRETATION",
)


def test_hold_start_threshold_env_override(monkeypatch: pytest.MonkeyPatch) -> None:
    old = {k: os.environ.pop(k, None) for k in (*_FLAG_ENVS, "VECTOR_MANAGER_INSIGHTS_HOLD_START_AFFECTED_WI_THRESHOLD")}
    get_settings.cache_clear()
    try:
        os.environ["ENV"] = "development"
        os.environ["VECTOR_MANAGER_INSIGHTS_HOLD_START_AFFECTED_WI_THRESHOLD"] = "7"
        s = Settings()
        assert s.vector_manager_insights_hold_start_affected_wi_threshold == 7
    finally:
        get_settings.cache_clear()
        _restore_all(old)


def _restore_all(snapshot: dict[str, str | None]) -> None:
    for key, value in snapshot.items():
        if value is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = value
