"""Tests for Step 8 insight generation."""

from __future__ import annotations

import uuid
from importlib import import_module
from types import SimpleNamespace
from typing import Any

from vector.contracts.manager_insights_activity import (
    EvidenceBundle,
    EvidenceItem,
    GapBundle,
    GapItem,
    InterpretationBundleDebug,
    InterpretationItemDebug,
    KeyAchievementsBundleDebug,
    RawHighlightItem,
    RawHighlightsBundleDebug,
    SignalsV0Debug,
)

mod = import_module("vector.domains.manager_insights.generate_insights")


def _signals() -> SignalsV0Debug:
    return SignalsV0Debug(
        delivery_strength="moderate",
        urgent_pressure="high",
        expectation_coverage="partial",
        follow_through="weak",
        blocker_visibility="partial",
        repeated_discussion_present=True,
        execution_momentum="steady",
        documentation_linkage="partially_linked",
        focus="fragmented",
        collaboration_intensity="high",
        support_pattern="asks_for_help",
        feedback_reception="neutral",
        coordination_role="contributing",
        interaction_friction="present",
        explain={
            "delivery_strength": "done execution items=5",
            "urgent_pressure": "open urgent execution items=3",
            "expectation_coverage": "action coverage=2/4",
            "follow_through": "action_items linked to done execution=1/4",
            "blocker_visibility": "tracked blockers=1/2",
            "repeated_discussion_present": "true via discussed_not_linked_to_work gap",
            "execution_momentum": "recent done=2 vs prior=2",
            "documentation_linkage": "linked docs=1/3",
            "focus": "active execution projects=5",
            "collaboration_intensity": "discussion_items=7 participants=6",
            "support_pattern": "help markers gives=1 asks=4",
            "feedback_reception": "defaulted to neutral",
            "coordination_role": "lead_score=4",
            "interaction_friction": "friction markers=5",
        },
    )


def _bundles(run_id: uuid.UUID, tenant_id: uuid.UUID) -> dict[str, Any]:
    evidence = EvidenceBundle(
        run_id=run_id,
        tenant_id=tenant_id,
        window_days=30,
        action_items=[
            EvidenceItem(
                id="a1",
                kind="action_item",
                statement="Need help closing NEX-1",
                evidence="Need help closing NEX-1",
                source_work_item_id="calls:c1",
                source_connector="calls",
                source_type="call",
                source_ref={},
                linked_work_items=[],
            )
        ],
        blockers=[],
        decisions=[],
        discarded_without_evidence=0,
    )
    gaps = GapBundle(
        run_id=run_id,
        tenant_id=tenant_id,
        window_days=30,
        gaps=[
            GapItem(
                id="g1",
                type="expected_not_executed",
                description="action item has no linked issue",
                evidence_pointers={},
            )
        ],
    )
    highlights = RawHighlightsBundleDebug(
        run_id=run_id,
        tenant_id=tenant_id,
        window_days=30,
        items=[
            RawHighlightItem(
                id="rh1",
                text='Term "incident" appears in 3 distinct calls/Slack work items.',
                sources=["calls:c1"],
            )
        ],
    )
    achievements = KeyAchievementsBundleDebug(
        run_id=run_id,
        tenant_id=tenant_id,
        window_days=30,
        items=[],
    )
    interpretations = InterpretationBundleDebug(
        run_id=run_id,
        tenant_id=tenant_id,
        window_days=30,
        generated_via="llm",
        fallback_reason=None,
        model="gpt-5-mini",
        latency_ms=10,
        prompt_tokens=10,
        completion_tokens=10,
        total_tokens=20,
        items=[
            InterpretationItemDebug(
                id="interp_1",
                type="follow_through",
                description="Follow-through is weak.",
                based_on_signals=["follow_through"],
                evidence=["Need help closing NEX-1"],
                confidence="medium",
            )
        ],
    )
    return {
        "evidence": evidence,
        "gaps": gaps,
        "highlights": highlights,
        "achievements": achievements,
        "interpretations": interpretations,
    }


def test_generate_insights_fallback_without_openai_key() -> None:
    run_id = uuid.uuid4()
    tenant_id = uuid.uuid4()
    b = _bundles(run_id, tenant_id)
    out = mod.generate_insights(
        SimpleNamespace(openai_api_key="", openai_model="gpt-5-mini"),  # type: ignore[arg-type]
        signals=_signals(),
        interpretations=b["interpretations"],
        evidence=b["evidence"],
        gaps=b["gaps"],
        key_achievements=b["achievements"],
        raw_highlights=b["highlights"],
    )
    assert out.generated_via == "fallback"
    assert out.fallback_reason == "missing_api_key"
    assert out.items
    assert all(i.based_on_interpretations for i in out.items)


def test_generate_insights_llm_payload_is_schema_and_grounding_validated(monkeypatch: Any) -> None:
    run_id = uuid.uuid4()
    tenant_id = uuid.uuid4()
    b = _bundles(run_id, tenant_id)

    class _FakeCompletions:
        @staticmethod
        def create(**kwargs: Any) -> Any:
            del kwargs
            return SimpleNamespace(
                choices=[
                    SimpleNamespace(
                        message=SimpleNamespace(
                            content=(
                                '{"insights":['
                                '{"id":"ins_1","observation":"Follow-through is weak.",'
                                '"interpretation":"Execution handoffs are inconsistent.",'
                                '"implication":"Manager should enforce closure criteria.",'
                                '"evidence":["Need help closing NEX-1"],'
                                '"based_on_interpretations":["interp_1"],'
                                '"based_on_signals":["follow_through"],'
                                '"confidence":"high","priority":"high"},'
                                '{"id":"ins_bad","observation":"bad","interpretation":"bad","implication":"bad",'
                                '"evidence":["invented quote"],'
                                '"based_on_interpretations":["interp_1"],'
                                '"based_on_signals":["follow_through"],'
                                '"confidence":"high","priority":"high"}'
                                "]}"
                            )
                        )
                    )
                ],
                usage=SimpleNamespace(prompt_tokens=123, completion_tokens=55, total_tokens=178),
            )

    class _FakeChat:
        completions = _FakeCompletions()

    class _FakeClient:
        def __init__(self, api_key: str) -> None:
            self.api_key = api_key
            self.chat = _FakeChat()

    monkeypatch.setattr(mod, "OpenAI", _FakeClient)
    out = mod.generate_insights(
        SimpleNamespace(openai_api_key="sk-test", openai_model="gpt-5-mini"),  # type: ignore[arg-type]
        signals=_signals(),
        interpretations=b["interpretations"],
        evidence=b["evidence"],
        gaps=b["gaps"],
        key_achievements=b["achievements"],
        raw_highlights=b["highlights"],
    )
    assert out.generated_via == "llm"
    assert out.fallback_reason is None
    assert len(out.items) == 1
    assert out.items[0].id == "ins_1"
    assert out.model == "gpt-5-mini"
    assert out.total_tokens == 178
    assert out.llm_parsed_insight_rows == 2
    assert len(out.rejected_insights) == 1
    assert out.rejected_insights[0].index == 1
    assert "verifiable" in out.rejected_insights[0].reason
    assert out.rejected_insights[0].raw.get("id") == "ins_bad"
    assert out.llm_response_text is not None


def test_generate_insights_reports_invalid_llm_output_reason(monkeypatch: Any) -> None:
    run_id = uuid.uuid4()
    tenant_id = uuid.uuid4()
    b = _bundles(run_id, tenant_id)

    class _FakeCompletions:
        @staticmethod
        def create(**kwargs: Any) -> Any:
            del kwargs
            return SimpleNamespace(
                choices=[
                    SimpleNamespace(
                        message=SimpleNamespace(
                            content=(
                                '{"insights":[{"id":"x","observation":"bad","interpretation":"bad",'
                                '"implication":"bad","evidence":["Need help closing NEX-1"],'
                                '"based_on_interpretations":["missing_interp"],'
                                '"based_on_signals":["follow_through"],'
                                '"confidence":"high","priority":"high"}]}'
                            )
                        )
                    )
                ],
                usage=SimpleNamespace(prompt_tokens=10, completion_tokens=10, total_tokens=20),
            )

    class _FakeChat:
        completions = _FakeCompletions()

    class _FakeClient:
        def __init__(self, api_key: str) -> None:
            self.api_key = api_key
            self.chat = _FakeChat()

    monkeypatch.setattr(mod, "OpenAI", _FakeClient)
    out = mod.generate_insights(
        SimpleNamespace(openai_api_key="sk-test", openai_model="gpt-5-mini"),  # type: ignore[arg-type]
        signals=_signals(),
        interpretations=b["interpretations"],
        evidence=b["evidence"],
        gaps=b["gaps"],
        key_achievements=b["achievements"],
        raw_highlights=b["highlights"],
    )
    assert out.generated_via == "fallback"
    assert out.fallback_reason == "llm_output_invalid"
    assert out.llm_parsed_insight_rows == 1
    assert len(out.rejected_insights) == 1
    assert out.rejected_insights[0].index == 0
    assert out.rejected_insights[0].raw.get("id") == "x"
    assert out.llm_response_text is not None
