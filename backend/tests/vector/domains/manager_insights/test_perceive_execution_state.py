"""§6 Step 9 — perceive_execution_state (mocked LLM)."""

from __future__ import annotations

import json
import uuid
from typing import Any

import pytest

from vector.contracts.manager_insights_activity import WorkItem, WorkItemBundle
from vector.domains.manager_insights.perceive_execution_state import (
    build_perception_execution_state_demo_debug,
    perceive_execution_state,
)
from vector.settings import Settings


@pytest.fixture
def mi_settings(monkeypatch: pytest.MonkeyPatch) -> Settings:
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://test:test@localhost:5432/vector_test")
    return Settings()


def _single_item_bundle() -> WorkItemBundle:
    rid = uuid.UUID("11111111-1111-1111-1111-111111111111")
    tid = uuid.UUID("22222222-2222-2222-2222-222222222222")
    wi = WorkItem(
        id="wi-test-1",
        source="linear",
        type="issue",
        title="Auth rollout",
        summary="Blocked on security review today.",
    )
    return WorkItemBundle(run_id=rid, tenant_id=tid, window_days=30, items=[wi])


def test_perceive_execution_state_mock_parses_rows(mi_settings: Settings) -> None:
    bundle = _single_item_bundle()
    assistant = json.dumps(
        {
            "perception_rows": [
                {
                    "id": "r1",
                    "work_item_id": "wi-test-1",
                    "kind": "blocker",
                    "statement": "Security review blocks rollout.",
                    "quote": "Blocked on security review",
                }
            ]
        }
    )

    def stub_create(**_kwargs: Any) -> Any:
        class _U:
            prompt_tokens = 1
            completion_tokens = 2
            total_tokens = 3

        class _M:
            content = assistant

        class _C:
            message = _M()

        class _R:
            choices = [_C()]
            usage = _U()

        return _R()

    out = perceive_execution_state(mi_settings, bundle, completions_create=stub_create)
    assert out.skipped_reason is None
    assert out.parse_error is None
    assert out.response_level_error is None
    assert len(out.rows) == 1
    assert out.rows[0]["id"] == "r1"
    assert out.rows[0]["quote"] == "Blocked on security review"


def test_missing_api_key_without_inject_skips(mi_settings: Settings) -> None:
    mi_settings = mi_settings.model_copy(update={"openai_api_key": ""})
    out = perceive_execution_state(mi_settings, _single_item_bundle())
    assert out.skipped_reason == "missing_api_key"
    assert out.rows == []


def test_empty_work_items_skips(mi_settings: Settings) -> None:
    bundle = WorkItemBundle(
        run_id=uuid.UUID(int=1),
        tenant_id=uuid.UUID(int=2),
        window_days=30,
        items=[],
    )
    out = perceive_execution_state(mi_settings, bundle)
    assert out.skipped_reason == "no_work_items"


def test_invalid_json_sets_parse_error(mi_settings: Settings) -> None:
    def stub_create(**_kwargs: Any) -> Any:
        class _M:
            content = "not json at all"

        class _C:
            message = _M()

        class _R:
            choices = [_C()]
            usage = None

        return _R()

    out = perceive_execution_state(mi_settings, _single_item_bundle(), completions_create=stub_create)
    assert out.parse_error == "assistant_text_not_json_object"


def test_missing_perception_rows_key(mi_settings: Settings) -> None:
    def stub_create(**_kwargs: Any) -> Any:
        class _M:
            content = json.dumps({"other": []})

        class _C:
            message = _M()

        class _R:
            choices = [_C()]
            usage = None

        return _R()

    out = perceive_execution_state(mi_settings, _single_item_bundle(), completions_create=stub_create)
    assert out.response_level_error == "missing_perception_rows_key"


def test_demo_debug_two_rows() -> None:
    d = build_perception_execution_state_demo_debug()
    assert len(d.rows) == 2
    assert d.skipped_reason is None
    assert d.rows[0]["work_item_id"] == "coordination:perception-llm:wi-a"
