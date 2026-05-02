"""§6 Step 19 — SignalsV0Debug extension keys (contract defaults)."""

from __future__ import annotations

from vector.contracts.manager_insights_activity import SignalsV0Debug


def test_signals_v0_debug_step19_fields_default_low() -> None:
    s = SignalsV0Debug(
        delivery_strength="moderate",
        urgent_pressure="low",
        expectation_coverage="high",
        follow_through="strong",
        blocker_visibility="visible",
        repeated_discussion_present=False,
        execution_momentum="steady",
        documentation_linkage="linked",
        focus="focused",
        collaboration_intensity="moderate",
        support_pattern="balanced",
        feedback_reception="neutral",
        coordination_role="contributing",
        interaction_friction="absent",
        explain={},
    )
    assert s.scope_ambiguity == "low"
    assert s.discussion_churn == "low"
    assert s.contradiction_density == "low"


def test_signals_v0_debug_round_trip_json_includes_step19_keys() -> None:
    s = SignalsV0Debug(
        delivery_strength="moderate",
        urgent_pressure="low",
        expectation_coverage="high",
        follow_through="strong",
        blocker_visibility="visible",
        repeated_discussion_present=False,
        execution_momentum="steady",
        documentation_linkage="linked",
        focus="focused",
        collaboration_intensity="moderate",
        support_pattern="balanced",
        feedback_reception="neutral",
        coordination_role="contributing",
        interaction_friction="absent",
        scope_ambiguity="moderate",
        discussion_churn="high",
        contradiction_density="low",
        explain={"scope_ambiguity": "x", "discussion_churn": "y", "contradiction_density": "z"},
    )
    data = s.model_dump(mode="json")
    again = SignalsV0Debug.model_validate(data)
    assert again == s
