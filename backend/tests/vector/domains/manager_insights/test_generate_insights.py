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
    WorkItem,
    WorkItemBundle,
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
    work_items = WorkItemBundle(
        run_id=run_id,
        tenant_id=tenant_id,
        window_days=30,
        items=[
            WorkItem(
                id="calls:c1",
                source="calls",
                type="call",
                title="Call about NEX-1",
                summary="Need help closing NEX-1",
                status="active",
                project="NEX",
                owner=None,
                participants=[],
                source_ref={},
            )
        ],
    )
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
                evidence_pointers={
                    "action_item_ids": ["a1"],
                    "source_work_item_ids": ["calls:c1"],
                },
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
                description="g1 — calls:c1 — Follow-through is weak for tracked execution.",
                based_on_signals=["follow_through"],
                evidence=["Need help closing NEX-1"],
                confidence="medium",
                based_on_gaps=["g1"],
                based_on_blockers=[],
                based_on_highlights=[],
            )
        ],
    )
    return {
        "work_items": work_items,
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
        work_items=b["work_items"],
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
                                '{"id":"ins_1","observation":"g1 — calls:c1 and NEX: Follow-through is weak.",'
                                '"interpretation":"Execution handoffs are inconsistent.",'
                                '"implication":"Manager should enforce closure criteria.",'
                                '"evidence":["Need help closing NEX-1"],'
                                '"evidence_ids":["a1"],'
                                '"based_on_interpretations":["interp_1"],'
                                '"based_on_signals":["follow_through"],'
                                '"primary_work_item_ids":["calls:c1"],'
                                '"supporting_work_item_ids":[],'
                                '"primary_entities":[{"name":"NEX","kind":"project"}],'
                                '"based_on_gaps":["g1"],"based_on_blockers":[],"based_on_highlights":[],'
                                '"confidence":"high","priority":"high"},'
                                '{"id":"ins_bad","observation":"g1 — calls:c1 and NEX: bad","interpretation":"bad",'
                                '"implication":"bad",'
                                '"evidence":["invented quote"],'
                                '"evidence_ids":["a1"],'
                                '"based_on_interpretations":["interp_1"],'
                                '"based_on_signals":["follow_through"],'
                                '"primary_work_item_ids":["calls:c1"],'
                                '"supporting_work_item_ids":[],'
                                '"primary_entities":[{"name":"NEX","kind":"project"}],'
                                '"based_on_gaps":["g1"],"based_on_blockers":[],"based_on_highlights":[],'
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
        work_items=b["work_items"],
    )
    assert out.generated_via == "llm"
    assert out.fallback_reason is None
    assert len(out.items) == 1
    assert out.items[0].id == "ins_1"
    assert out.items[0].evidence_ids == ["a1"]
    assert out.items[0].primary_work_item_ids == ["calls:c1"]
    assert out.items[0].primary_entities[0].name == "NEX"
    assert out.items[0].based_on_gaps == ["g1"]
    assert out.model == "gpt-5-mini"
    assert out.total_tokens == 178
    assert out.llm_parsed_insight_rows == 2
    assert len(out.rejected_insights) == 1
    assert out.rejected_insights[0].index == 1
    assert "cited evidence_ids" in out.rejected_insights[0].reason
    assert out.rejected_insights[0].raw.get("id") == "ins_bad"
    assert out.llm_response_text is not None


def test_resolve_bundle_work_item_id_maps_linear_ticket_to_canonical_id() -> None:
    w = WorkItem(
        id="linear:issue:550e8400-e29b-41d4-a716-446655440000",
        source="linear",
        type="issue",
        title="NEX-5 — Integration dashboard",
        summary=None,
        status="open",
        project="NEX",
        owner=None,
        participants=[],
        source_ref={"identifier": "NEX-5"},
    )
    assert (
        mod._resolve_bundle_work_item_id("linear:issue:NEX-5", [w])
        == "linear:issue:550e8400-e29b-41d4-a716-446655440000"
    )
    assert mod._resolve_bundle_work_item_id("linear:issue:NEX-404", [w]) is None


def test_insight_evidence_gap_boilerplate_triggers_replace_with_row_quotes(monkeypatch: Any) -> None:
    """LLM gap-summary phrases → substitute Step-3 evidence quotes when validating."""
    run_id = uuid.uuid4()
    tenant_id = uuid.uuid4()
    b = _bundles(run_id, tenant_id)
    b["evidence"] = EvidenceBundle(
        run_id=run_id,
        tenant_id=tenant_id,
        window_days=30,
        action_items=[],
        blockers=[
            EvidenceItem(
                id="blocker:z",
                kind="blocker",
                statement="War room: blocked on approval",
                evidence="War room: blocked on approval",
                source_work_item_id="calls:c1",
                source_connector="calls",
                source_type="call",
                source_ref={},
                linked_work_items=[],
            )
        ],
        decisions=[],
        discarded_without_evidence=0,
    )

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
                                '{"id":"ins_boiler","observation":"g1 — calls:c1 — NEX: blocker linkage.",'
                                '"interpretation":"x","implication":"y",'
                                '"evidence":["Blocker is mentioned but not linked to a tracked issue/PR."],'
                                '"evidence_ids":["blocker:z"],'
                                '"based_on_interpretations":["interp_1"],'
                                '"based_on_signals":["blocker_visibility"],'
                                '"primary_work_item_ids":["calls:c1"],'
                                '"supporting_work_item_ids":[],'
                                '"primary_entities":[{"name":"NEX","kind":"project"}],'
                                '"based_on_gaps":["g1"],"based_on_blockers":["blocker:z"],"based_on_highlights":[],'
                                '"confidence":"high","priority":"high"}'
                                "]}"
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
        work_items=b["work_items"],
    )
    assert out.generated_via == "llm"
    assert len(out.items) == 1
    assert out.items[0].evidence == ["War room: blocked on approval"]


def test_insight_accepts_gap_ids_in_interpretation_not_observation(monkeypatch: Any) -> None:
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
                                '{"id":"ins_split","observation":"blocker:3738cc61aa15 — calls:c1 — NEX-1 narrative.",'
                                '"interpretation":"Anchored to gap g1 and calls:c1.",'
                                '"implication":"Do something.",'
                                '"evidence":["Need help closing NEX-1"],'
                                '"evidence_ids":["a1"],'
                                '"based_on_interpretations":["interp_1"],'
                                '"based_on_signals":["follow_through"],'
                                '"primary_work_item_ids":["calls:c1"],'
                                '"supporting_work_item_ids":[],'
                                '"primary_entities":[{"name":"NEX","kind":"project"}],'
                                '"based_on_gaps":["g1"],"based_on_blockers":[],"based_on_highlights":[],'
                                '"confidence":"high","priority":"high"}'
                                "]}"
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
        work_items=b["work_items"],
    )
    assert out.generated_via == "llm"
    assert len(out.items) == 1
    assert out.items[0].id == "ins_split"


def test_insight_adds_supporting_work_item_from_cited_evidence_source(monkeypatch: Any) -> None:
    run_id = uuid.uuid4()
    tenant_id = uuid.uuid4()
    b = _bundles(run_id, tenant_id)
    slack_wi = WorkItem(
        id="slack:message:#incident-review:2025-10-11T14:00:00Z",
        source="slack",
        type="message_thread",
        title="incident thread",
        summary="review notes",
        status=None,
        project=None,
        owner=None,
        participants=[],
        source_ref={},
    )
    b["work_items"].items.append(slack_wi)
    b["evidence"] = EvidenceBundle(
        run_id=run_id,
        tenant_id=tenant_id,
        window_days=30,
        action_items=[
            EvidenceItem(
                id="action:x",
                kind="action_item",
                statement="Follow up from incident review",
                evidence="Follow up from incident review",
                source_work_item_id=slack_wi.id,
                source_connector="slack",
                source_type="message_thread",
                source_ref={},
                linked_work_items=["calls:c1"],
            )
        ],
        blockers=[],
        decisions=[],
        discarded_without_evidence=0,
    )

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
                                '{"id":"ins_sup","observation":"g1 — calls:c1 — NEX-1 gap narrative.",'
                                '"interpretation":"Uses action:x evidence.",'
                                '"implication":"Add supporting slack.",'
                                '"evidence":["Follow up from incident review"],'
                                '"evidence_ids":["action:x"],'
                                '"based_on_interpretations":["interp_1"],'
                                '"based_on_signals":["follow_through"],'
                                '"primary_work_item_ids":["calls:c1"],'
                                '"supporting_work_item_ids":[],'
                                '"primary_entities":[{"name":"NEX","kind":"project"}],'
                                '"based_on_gaps":["g1"],"based_on_blockers":[],"based_on_highlights":[],'
                                '"confidence":"high","priority":"high"}'
                                "]}"
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
        work_items=b["work_items"],
    )
    assert out.generated_via == "llm"
    assert len(out.items) == 1
    assert slack_wi.id in out.items[0].supporting_work_item_ids


def test_generate_insights_maps_evidence_id_strings_to_row_quotes(monkeypatch: Any) -> None:
    """LLM sometimes puts evidence_ids into evidence[]; we normalize to quotable text."""
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
                                '{"id":"ins_ids","observation":"g1 — calls:c1 and NEX: Follow-through.",'
                                '"interpretation":"Handoffs are weak.",'
                                '"implication":"Enforce closure.",'
                                '"evidence":["a1"],'
                                '"evidence_ids":["a1"],'
                                '"based_on_interpretations":["interp_1"],'
                                '"based_on_signals":["follow_through"],'
                                '"primary_work_item_ids":["calls:c1"],'
                                '"supporting_work_item_ids":[],'
                                '"primary_entities":[{"name":"NEX","kind":"project"}],'
                                '"based_on_gaps":["g1"],"based_on_blockers":[],"based_on_highlights":[],'
                                '"confidence":"high","priority":"high"}'
                                "]}"
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
        work_items=b["work_items"],
    )
    assert out.generated_via == "llm"
    assert len(out.items) == 1
    assert out.items[0].evidence == ["Need help closing NEX-1"]


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
                                '{"insights":[{"id":"x","observation":"g1 — calls:c1 and NEX: bad",'
                                '"interpretation":"bad","implication":"bad",'
                                '"evidence":["Need help closing NEX-1"],'
                                '"evidence_ids":["a1"],'
                                '"based_on_interpretations":["missing_interp"],'
                                '"based_on_signals":["follow_through"],'
                                '"primary_work_item_ids":["calls:c1"],'
                                '"supporting_work_item_ids":[],'
                                '"primary_entities":[{"name":"NEX","kind":"project"}],'
                                '"based_on_gaps":["g1"],"based_on_blockers":[],"based_on_highlights":[],'
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
        work_items=b["work_items"],
    )
    assert out.generated_via == "fallback"
    assert out.fallback_reason == "llm_output_invalid"
    assert out.llm_parsed_insight_rows == 1
    assert len(out.rejected_insights) == 1
    assert out.rejected_insights[0].index == 0
    assert out.rejected_insights[0].raw.get("id") == "x"
    assert out.llm_response_text is not None
