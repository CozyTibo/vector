"""Hostile completeness scenarios — omission visibility must not silently pass."""

from __future__ import annotations

from vector.domains.cortex.completeness._completeness_common import build_stage_envelope_v1
from vector.domains.cortex.completeness.completeness_degradation_projection import (
    build_degradation_propagation_chain_v1,
)


def test_chronology_degradation_propagation_visible() -> None:
    stages = [
        build_stage_envelope_v1(
            stage_id="canonical",
            label="Canonical",
            total_objects=100,
            processed_count=80,
            degraded_count=10,
            omission_classes={"parse_failure": 5},
            substrate_state="degraded",
            detail_route="/c",
        ),
        build_stage_envelope_v1(
            stage_id="tcre",
            label="TCRE",
            total_objects=80,
            processed_count=60,
            degraded_count=15,
            omission_classes={"degradation_propagated": 15},
            substrate_state="degraded",
            detail_route="/r",
        ),
    ]
    chain = build_degradation_propagation_chain_v1(stages)
    assert isinstance(chain, list)


def test_unresolved_identity_omission_class() -> None:
    stage = build_stage_envelope_v1(
        stage_id="identity",
        label="Identity",
        total_objects=50,
        processed_count=40,
        unresolved_count=10,
        omission_classes={"unresolved_actor": 10, "replay_conflicted_identity": 2},
        substrate_state="degraded",
        replay_posture="partial",
        detail_route="/id",
    )
    assert stage["omission_classes"]["unresolved_actor"] == 10
    assert stage["unresolved_percent"] == 20.0
