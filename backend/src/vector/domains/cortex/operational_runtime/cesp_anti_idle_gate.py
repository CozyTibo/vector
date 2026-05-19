"""Phase 08.5 Step 02 — static gate **G-P085-ANTI-IDLE-01**."""

from __future__ import annotations

from typing import Any, Final

from vector.domains.cortex.operational_runtime.fake_green_prohibition import (
    GP085_ANTI_IDLE01_GATE_ID_V1,
    OPERATIONAL_IDLE_STARVATION_V1,
    assert_never_fake_green_healthy_v1,
    classify_synthesis_idle_v1,
    must_degrade_for_anti_idle_law_v1,
    CespAntiIdleLawError,
)

def verify_gp085_anti_idle01_static() -> dict[str, Any]:
    """**G-P085-ANTI-IDLE-01** — fake-green prohibition static law checks."""
    failures: list[str] = []

    try:
        assert_never_fake_green_healthy_v1(
            stage_id="retrieval",
            total_objects=10,
            processed_count=0,
            substrate_state="healthy",
        )
    except CespAntiIdleLawError:
        pass
    else:
        failures.append("expected_fake_green_rejection")

    try:
        assert_never_fake_green_healthy_v1(
            stage_id="retrieval",
            total_objects=0,
            processed_count=0,
            substrate_state="healthy",
        )
    except CespAntiIdleLawError as exc:
        failures.append(f"zero_total_should_pass:{exc.code}")

    if not must_degrade_for_anti_idle_law_v1(
        substrate_state="healthy",
        operational_idle_class=OPERATIONAL_IDLE_STARVATION_V1,
    ):
        failures.append("starvation_must_force_degrade")

    if classify_synthesis_idle_v1(
        eligible_scopes=0,
        synthesized_scopes=0,
        upstream_starvation=True,
    ) != "starved":
        failures.append("synthesis_upstream_starvation_must_be_starved")

    if classify_synthesis_idle_v1(
        eligible_scopes=5,
        synthesized_scopes=0,
        upstream_starvation=False,
    ) != "starved":
        failures.append("synthesis_eligible_unprocessed_must_be_starved")

    # graph/tcre projection law spot checks
    from vector.domains.cortex.completeness.graph_completeness_projection import (
        _derive_graph_substrate_state_v1,
    )
    from vector.domains.cortex.completeness.tcre_completeness_projection import (
        _derive_tcre_substrate_state_v1,
    )

    if (
        _derive_graph_substrate_state_v1(
            entity_count=10,
            linked_entities=0,
            orphan_count=10,
            link_count=0,
            candidate_count=0,
        )
        != "degraded"
    ):
        failures.append("graph_all_orphans_must_degrade")
    if _derive_tcre_substrate_state_v1(
        mat_total=5,
        reconstructed=0,
        reconstruction_never_run=True,
        failed_jobs=0,
        degraded_chron=0,
        pending=5,
    ) != "degraded":
        failures.append("tcre_never_run_must_degrade")

    passed = not failures
    return {
        "id": GP085_ANTI_IDLE01_GATE_ID_V1,
        "passed": passed,
        "gate_id": GP085_ANTI_IDLE01_GATE_ID_V1,
        "failure_codes": failures,
    }
