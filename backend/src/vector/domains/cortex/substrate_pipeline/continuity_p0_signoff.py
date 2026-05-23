"""Phase 0 step 0.6 — P0 sign-off gate (CONT-INV-01/02/08 + P0-D + baseline consolidation)."""

from __future__ import annotations

import uuid
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from vector.domains.cortex.substrate_pipeline.constants import PIPELINE_STATUS_FAILED
from vector.domains.cortex.substrate_pipeline.continuity_p0_baseline import (
    evaluate_phase0_prerequisites_v1,
    probe_prod_ecs_deploy_v1,
)
from vector.domains.cortex.substrate_pipeline.continuity_p0_phase05_proof import (
    evaluate_p0_b_phase05_proof_v1,
)

P0_SIGNOFF_STEP = "0.6_p0_signoff"
CONT_INV_08 = "CONT-INV-08"

P0_D_CI_PATHS = (
    ".github/workflows/ci.yml",
    ".github/workflows/deploy.yml",
    "backend/Dockerfile",
    "backend/worker.Dockerfile",
    "backend/tests/vector/domains/cortex/traversal/test_walk_policy_packaging.py",
    "backend/src/vector/domains/cortex/traversal/schemas/octs-walk-policy-v1.schema.json",
)


def verify_p0_d_ci_gates_v1(*, repo_root: Path) -> dict[str, Any]:
    """Static repo checks for P0-D (walk policy packaging in CI + images)."""
    checks: dict[str, bool] = {}
    workflow_text = ""
    for rel in (".github/workflows/ci.yml", ".github/workflows/deploy.yml"):
        path = repo_root / rel
        if path.is_file():
            workflow_text += path.read_text(encoding="utf-8")
    checks["deploy_workflow_walk_policy_test"] = "test_walk_policy_packaging" in workflow_text
    checks["bundled_schema_present"] = (
        repo_root / "backend/src/vector/domains/cortex/traversal/schemas/octs-walk-policy-v1.schema.json"
    ).is_file()
    for rel in ("backend/Dockerfile", "backend/worker.Dockerfile"):
        path = repo_root / rel
        text = path.read_text(encoding="utf-8") if path.is_file() else ""
        key = rel.replace("/", "_").replace(".", "_") + "_packaging_gate"
        checks[key] = "validate_walk_policy_for_request_v1" in text or "walk_policy_packaging" in text
    checks["packaging_unit_test_present"] = (
        repo_root / "backend/tests/vector/domains/cortex/traversal/test_walk_policy_packaging.py"
    ).is_file()
    p0_d_pass = all(checks.values())
    return {
        "gate": "P0-D",
        "checks": checks,
        "p0_d_pass": p0_d_pass,
    }


def evaluate_p0_signoff_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    baseline: dict[str, Any],
    repo_root: Path,
    pipeline_run_id: uuid.UUID | None = None,
) -> dict[str, Any]:
    """Evaluate Phase 0 P0 sign-off (step 0.6) from prod DB + committed baseline + repo gates."""
    closure_sha = (baseline.get("phase0_closure_git_sha") or baseline.get("git_sha_full") or "").strip()
    p0_b = evaluate_p0_b_phase05_proof_v1(
        session,
        tenant_id=tenant_id,
        pipeline_run_id=pipeline_run_id,
    )
    p0_d = verify_p0_d_ci_gates_v1(repo_root=repo_root)

    run_status = p0_b.get("pipeline_run_status")
    cont_inv_08_pass = run_status is not None and run_status != PIPELINE_STATUS_FAILED

    baseline_prereq = evaluate_phase0_prerequisites_v1(baseline)
    step_05 = (baseline.get("step_0_5_phase0_closure") or {}).get("verification") or {}
    baseline_closure_ok = bool(baseline.get("phase0_complete")) and bool(step_05.get("step_05_pass"))
    baseline_steps_ok = (
        baseline_closure_ok
        and baseline_prereq.get("step_02_artifact_present")
        and baseline_prereq.get("step_04_pass")
        and (baseline_prereq.get("step_03_pass") or cont_inv_08_pass)
    )

    ecs_match = False
    prod_deploy: dict[str, Any] = {}
    if closure_sha:
        prod_deploy = probe_prod_ecs_deploy_v1(expected_sha=closure_sha)
        ecs_match = bool(
            (prod_deploy.get("verification") or {}).get("deploy_matches_closure_sha")
        )

    cont_inv_checks = {
        "CONT-INV-01_phase_05_completed": bool(
            (p0_b.get("checks") or {}).get("phase_05_status_completed")
        ),
        "CONT-INV-02_schema_and_lease_clear": bool(
            (p0_b.get("checks") or {}).get("no_schema_path_error")
        )
        and bool((p0_b.get("checks") or {}).get("lease_last_error_null")),
        "CONT-INV-08_active_run_not_failed": cont_inv_08_pass,
    }

    signoff_checks = {
        **cont_inv_checks,
        "P0-D_ci_packaging_gates": bool(p0_d.get("p0_d_pass")),
        "baseline_steps_0_1_through_0_5": baseline_steps_ok,
        "ecs_matches_closure_sha": ecs_match,
    }
    step_06_pass = all(signoff_checks.values())

    return {
        "step": P0_SIGNOFF_STEP,
        "tenant_id": str(tenant_id),
        "closure_git_sha": closure_sha or None,
        "pipeline_run_id": p0_b.get("pipeline_run_id"),
        "cont_inv_08": CONT_INV_08,
        "p0_b_proof": p0_b,
        "p0_d_ci": p0_d,
        "prod_deploy": prod_deploy,
        "baseline_prerequisites": baseline_prereq,
        "baseline_phase0_complete": baseline_closure_ok,
        "checks": signoff_checks,
        "p0_signoff_pass": step_06_pass,
        "verification": {
            "step_06_pass": step_06_pass,
            "phase_0_signed_off": step_06_pass,
            "cleared_for_phase_1": step_06_pass,
        },
    }


def apply_step_0_6_to_baseline_v1(
    baseline: dict[str, Any],
    signoff: dict[str, Any],
) -> dict[str, Any]:
    baseline["step_0_6_p0_signoff"] = signoff
    baseline["phase_0_signed_off"] = signoff["verification"]["phase_0_signed_off"]
    return baseline
