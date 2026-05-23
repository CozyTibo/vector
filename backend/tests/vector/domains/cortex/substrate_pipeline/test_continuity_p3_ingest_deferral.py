"""Phase 3.4 — P2-E ingest deferral monitoring proof evaluator."""

from __future__ import annotations

from datetime import UTC, datetime

from vector.domains.cortex.substrate_pipeline.continuity_p3_ingest_deferral import (
    evaluate_p3_4_ingest_deferral_proof_v1,
    verify_p2e_ingest_deferral_wiring_v1,
)


def test_static_wiring_ok() -> None:
    wiring = verify_p2e_ingest_deferral_wiring_v1()
    assert wiring["wiring_ok"] is True


def test_p3_4_pass_with_release_probe() -> None:
    wiring = verify_p2e_ingest_deferral_wiring_v1()
    snapshot = {
        "monitoring_enabled": True,
        "wiring": wiring,
        "ingest_caps": {"fix6_caps": {"x": {}}, "meets_fix6_recommended": True},
        "panel": {
            "surface_kind": "ingest_deferral_monitoring",
            "deferral_release": {
                "deferral_counts": {"deferred_total": 100},
                "deferral_pressure": [{"count": 10}],
            },
            "exhaust_registry": {
                "surface_kind": "exhaust_registry_honesty",
                "github": {"maturity_level": 4},
            },
        },
        "execution_inspect_ingest_deferral": {"surface_kind": "ingest_deferral_monitoring"},
    }
    release_drive = {
        "acquired": True,
        "release_probe": {
            "released_total": 2,
            "deferral_counts_after": {"deferred_total": 98},
        },
    }
    proof = evaluate_p3_4_ingest_deferral_proof_v1(
        closure_git_sha="a" * 40,
        prod_deploy={"verification": {"deploy_matches_closure_sha": True}},
        snapshot=snapshot,
        release_drive=release_drive,
        deploy_recorded_at=datetime(2026, 5, 22, 12, 0, 0, tzinfo=UTC),
    )
    assert proof["p3_4_pass"] is True
    assert proof["verification"]["cleared_for_phase_4"] is True
