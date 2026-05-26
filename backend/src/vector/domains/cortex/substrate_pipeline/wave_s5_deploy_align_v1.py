"""S5.6 — deploy alignment contract (ECS = repo HEAD via probe_prod_ecs_deploy_v1)."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Final

WAVE_S5_DEPLOY_ALIGN_SCHEMA_VERSION: Final[int] = 1
WAVE_S5_STEP_26: Final[str] = "wave_s5_ecs_deploy_align"

PROBE_SYMBOL: Final[str] = "probe_prod_ecs_deploy_v1"


def verify_s5_6_deploy_align_wiring_v1(*, repo_root: Path | None = None) -> dict[str, Any]:
    from vector.domains.cortex.substrate_pipeline.substrate_deploy_contract_v1 import (
        default_repo_root_v1,
        resolve_repo_relative_path_v1,
    )

    root = repo_root or default_repo_root_v1()
    errors: list[str] = []
    workflow = root / ".github" / "workflows" / "deploy.yml"
    if not workflow.is_file():
        errors.append("missing_deploy_workflow")
    else:
        wf = workflow.read_text(encoding="utf-8")
        if "Verify prod image tags match deploy SHA" not in wf:
            errors.append("deploy_workflow_missing_sha_verify_step")
        elif "ECS_WORKER_SERVICE" not in wf or 'test "$worker_tag" = "$IMAGE_TAG"' not in wf:
            errors.append("deploy_workflow_missing_worker_sha_verify")
        if "VECTOR_GIT_SHA" not in wf:
            errors.append("deploy_workflow_missing_vector_git_sha_env")
    baseline = resolve_repo_relative_path_v1(
        root,
        "backend/src/vector/domains/cortex/substrate_pipeline/continuity_p0_baseline.py",
    )
    if not baseline.is_file() or PROBE_SYMBOL not in baseline.read_text(encoding="utf-8"):
        errors.append("missing_probe_prod_ecs_deploy_v1_implementation")
    return {
        "schema_version": WAVE_S5_DEPLOY_ALIGN_SCHEMA_VERSION,
        "s5_6_ok": not errors,
        "errors": errors,
        "probe_symbol": PROBE_SYMBOL,
        "policy": "prod_api_and_worker_ecs_tags_match_github_sha",
    }


def snapshot_wave_s5_deploy_align_contract_v1(*, repo_root: Path | None = None) -> dict[str, Any]:
    return {
        "schema_version": WAVE_S5_DEPLOY_ALIGN_SCHEMA_VERSION,
        "step": WAVE_S5_STEP_26,
        "contract": verify_s5_6_deploy_align_wiring_v1(repo_root=repo_root),
    }
