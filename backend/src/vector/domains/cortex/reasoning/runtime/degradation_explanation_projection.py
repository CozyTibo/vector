"""RUNTIME-02 — deterministic degradation explanation templates."""

from __future__ import annotations

from typing import Any, Final

from vector.domains.cortex.reasoning.chronology_degradation_propagation import CD_CHRON

TCRE_OPERATOR_DEGRADATION_EXPLANATION_SCHEMA_VERSION: Final[int] = 1


def explain_chronology_degradation_v1(
    *,
    materialization_id: str,
    chronology_legality_class: str,
    projection_rule_id: str,
    skew_detected: bool,
    late_arrival: bool,
) -> dict[str, Any] | None:
    if chronology_legality_class != "chronology_degraded":
        return None
    triggers: list[str] = []
    if skew_detected:
        triggers.append("skew_detected")
    if late_arrival:
        triggers.append("late_arrival")
    trigger_text = ", ".join(triggers) if triggers else "policy_row_match_without_skew_flags"
    return {
        "schema_version": TCRE_OPERATOR_DEGRADATION_EXPLANATION_SCHEMA_VERSION,
        "scope": "chronology",
        "source_artifact_id": materialization_id,
        "degradation_class": CD_CHRON,
        "triggering_rule_id": projection_rule_id,
        "triggering_signals": triggers,
        "replay_consequence": "chronology_legality_class=chronology_degraded",
        "legality_impact": "strict temporal order claims require degraded band review",
        "explanation_summary": (
            f"{CD_CHRON} triggered for materialization {materialization_id}: "
            f"{trigger_text}; projected via {projection_rule_id}."
        ),
    }


def explain_edge_legality_v1(
    *,
    tcre_causal_edge_id: str,
    causal_legality_class: str,
    derivation_rule_id: str,
) -> dict[str, Any] | None:
    if causal_legality_class == "causal_replay_equivalent":
        return None
    return {
        "schema_version": TCRE_OPERATOR_DEGRADATION_EXPLANATION_SCHEMA_VERSION,
        "scope": "causal_edge",
        "source_artifact_id": tcre_causal_edge_id,
        "degradation_class": None,
        "triggering_rule_id": derivation_rule_id,
        "triggering_signals": [causal_legality_class],
        "replay_consequence": f"edge causal_legality_class={causal_legality_class}",
        "legality_impact": "chain replay equivalence may be constrained",
        "explanation_summary": (
            f"Edge {tcre_causal_edge_id} carries causal_legality_class={causal_legality_class} "
            f"under derivation {derivation_rule_id}."
        ),
    }
