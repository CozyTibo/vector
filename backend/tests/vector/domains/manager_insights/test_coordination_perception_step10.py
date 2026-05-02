"""§6 Step 10 — coordination perception before linking (flag-gated)."""

from __future__ import annotations

import uuid

from vector.contracts.manager_insights_activity import (
    PerceptionExecutionStateLlmDebug,
    WorkItem,
    WorkItemBundle,
)
from vector.domains.manager_insights.coordination_perception import run_coordination_perception_for_fetch_debug
from vector.settings import Settings


def _settings(*, perception_llm: bool, api_key: str = "sk-test") -> Settings:
    return Settings.model_construct(
        database_url="postgresql://coordination-step10-test",
        openai_api_key=api_key,
        openai_model="gpt-4o-mini",
        env="development",
        secret_key="dev-only-secret-key-min-32-chars-long!!",
        vector_manager_insights_perception_llm=perception_llm,
        vector_manager_insights_include_execution_graph=False,
        vector_manager_insights_skip_narrative_steps=False,
        vector_manager_insights_gaps_use_graph=False,
    )


def _bundle_one_item() -> WorkItemBundle:
    rid = uuid.UUID("11111111-1111-1111-1111-111111111111")
    tid = uuid.UUID("22222222-2222-2222-2222-222222222222")
    wi = WorkItem(
        id="wi-step10",
        source="linear",
        type="issue",
        title="Rollout",
        summary="We are blocked on QA signoff before release.",
    )
    return WorkItemBundle(run_id=rid, tenant_id=tid, window_days=30, items=[wi])


def test_flag_off_no_perception_no_rejected() -> None:
    p, r, accepted_models = run_coordination_perception_for_fetch_debug(
        _settings(perception_llm=False), _bundle_one_item()
    )
    assert p is None
    assert r == []
    assert accepted_models == []


def test_flag_on_stub_llm_populates_accepted() -> None:
    bundle = _bundle_one_item()

    def stub_perceive(_s: Settings, _w: WorkItemBundle) -> PerceptionExecutionStateLlmDebug:
        return PerceptionExecutionStateLlmDebug(
            rows=[
                {
                    "id": "r1",
                    "work_item_id": "wi-step10",
                    "kind": "blocker",
                    "statement": "QA blocks release.",
                    "quote": "blocked on QA signoff",
                }
            ],
            raw_assistant_text='{"perception_rows":[...]}',
            latency_ms=1,
            prompt_tokens=1,
            completion_tokens=2,
            total_tokens=3,
        )

    p, r, accepted_models = run_coordination_perception_for_fetch_debug(
        _settings(perception_llm=True),
        bundle,
        perceive_fn=stub_perceive,
    )
    assert p is not None
    assert p["enabled"] is True
    assert p["accepted_count"] == 1
    assert len(p["accepted"]) == 1
    assert p["accepted"][0]["quote"] == "blocked on QA signoff"
    assert p["rejected_count"] == 0
    assert r == []
    assert len(accepted_models) == 1
    assert accepted_models[0].quote == "blocked on QA signoff"


def test_flag_on_bad_schema_accumulates_rejected() -> None:
    bundle = _bundle_one_item()

    def stub_perceive(_s: Settings, _w: WorkItemBundle) -> PerceptionExecutionStateLlmDebug:
        return PerceptionExecutionStateLlmDebug(
            rows=[
                {"id": "bad"},
                {
                    "id": "ok",
                    "work_item_id": "wi-step10",
                    "kind": "risk",
                    "statement": "Schedule risk.",
                    "quote": "before release",
                },
            ],
        )

    p, r, accepted_models = run_coordination_perception_for_fetch_debug(
        _settings(perception_llm=True),
        bundle,
        perceive_fn=stub_perceive,
    )
    assert p is not None
    assert p["accepted_count"] == 1
    assert p["rejected_count"] == 1
    assert len(r) == 1
    assert r[0].reason == "schema_invalid"
    assert len(accepted_models) == 1
