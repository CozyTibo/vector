"""Phase D4 — permanent orphan omission doctrine proof."""

from __future__ import annotations

from pathlib import Path

from vector.domains.cortex.canonical.permanent_orphan_omission_doctrine import (
    FIZZER_REFERENCE_PERMANENT_ORPHAN_COUNT_V1,
    OMISSION_POSTURE_ACCEPTED_BOUNDED_DEBT_V1,
    PHASE_D4_OMISSION_SCHEMA_VERSION,
    evaluate_permanent_orphan_omission_posture_v1,
)
from vector.domains.cortex.substrate_pipeline.continuity_p0_phase_d4_permanent_orphan_omission import (
    evaluate_p0_d4_permanent_orphan_omission_proof_v1,
    verify_d4_permanent_orphan_omission_wiring_v1,
)

from vector.domains.cortex.substrate_pipeline.substrate_deploy_contract_v1 import (
    default_repo_root_v1,
)

REPO_ROOT = default_repo_root_v1()


def test_d4_wiring_ok() -> None:
    wiring = verify_d4_permanent_orphan_omission_wiring_v1(repo_root=REPO_ROOT)
    assert wiring["wiring_ok"] is True
    assert wiring["fizzer_reference_permanent_orphan"] == FIZZER_REFERENCE_PERMANENT_ORPHAN_COUNT_V1


def test_d4_doctrine_posture_with_permanent_orphans() -> None:
    posture = evaluate_permanent_orphan_omission_posture_v1(
        deferral_counts={"deferred_permanent_orphan": 466, "deferred_total": 500, "deferred_retry_ready": 10}
    )
    assert posture["posture"] == OMISSION_POSTURE_ACCEPTED_BOUNDED_DEBT_V1
    assert posture["chase_zero_deferrals_forbidden"] is True
    assert posture["is_bounded_omission_not_failure"] is True


def test_d4_proof_passes() -> None:
    operator_block = {
        "surface_kind": "deferral_omission_posture",
        "schema_version": PHASE_D4_OMISSION_SCHEMA_VERSION,
        "posture": OMISSION_POSTURE_ACCEPTED_BOUNDED_DEBT_V1,
        "permanent_orphan_count": 466,
        "deferral_total": 500,
        "chase_zero_deferrals_forbidden": True,
        "is_bounded_omission_not_failure": True,
    }
    snapshot = {
        "wiring": {
            "wiring_ok": True,
            "runbook_path": "DOCS/cortex/operational-runtime/canonical_permanent_orphan_omission_runbook.md",
            "fizzer_reference_permanent_orphan": FIZZER_REFERENCE_PERMANENT_ORPHAN_COUNT_V1,
            "phase_d4_schema_version": PHASE_D4_OMISSION_SCHEMA_VERSION,
        },
        "snapshot": {"deferral_omission": dict(operator_block)},
        "operator_block": operator_block,
        "overview_deferral_omission": operator_block,
    }
    proof = evaluate_p0_d4_permanent_orphan_omission_proof_v1(
        closure_git_sha="abc",
        prod_deploy={"verification": {"deploy_matches_closure_sha": True}},
        snapshot=snapshot,
    )
    assert proof["p0_d4_pass"] is True
    assert proof["verification"]["cleared_for_phase_d5"] is True
