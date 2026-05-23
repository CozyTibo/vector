"""Phase C3 — audit snapshot proof evaluator."""

from __future__ import annotations

from pathlib import Path

from vector.domains.cortex.substrate_pipeline.continuity_audit_snapshot import (
    AUDIT_SNAPSHOT_SURFACE_KIND,
    PHASE_C3_AUDIT_SNAPSHOT_SCHEMA_VERSION,
)
from vector.domains.cortex.substrate_pipeline.continuity_p0_phase_c3_audit_snapshot import (
    evaluate_p0_c3_audit_snapshot_proof_v1,
    verify_c3_audit_snapshot_wiring_v1,
)


def _snapshot() -> dict:
    return {
        "surface_kind": AUDIT_SNAPSHOT_SURFACE_KIND,
        "phase_c3_schema_version": PHASE_C3_AUDIT_SNAPSHOT_SCHEMA_VERSION,
        "panel": {"surface_kind": "continuity_proof_panel", "summary": {"fail_count": 1}},
        "panel_text": "AA1\nAA7\nSUBSTRATE SQL",
        "substrate_sql": {
            "surface_kind": "continuity_substrate_sql_snapshot",
            "obligation_epoch_gap_ok": True,
            "lease": {"obligation_epoch_gap_ok": True},
        },
        "phase_snapshots": {
            "c1_phase08_empty_scope_truth": {},
            "c2_synthesis_scope_caps": {},
        },
        "deprecated_proof_scripts": ["a"] * 12,
        "canonical_entrypoint": "backend/scripts/continuity_audit_snapshot.py",
    }


def test_c3_wiring_ok() -> None:
    repo = Path(__file__).resolve().parents[6]
    wiring = verify_c3_audit_snapshot_wiring_v1(repo_root=repo)
    assert wiring["wiring_ok"] is True


def test_c3_proof_passes() -> None:
    proof = evaluate_p0_c3_audit_snapshot_proof_v1(
        closure_git_sha="abc",
        prod_deploy={"verification": {"deploy_matches_closure_sha": True}},
        snapshot=_snapshot(),
        snapshot_text="AA1 AA7 Substrate SQL",
        wiring={"wiring_ok": True},
    )
    assert proof["p0_c3_pass"] is True
