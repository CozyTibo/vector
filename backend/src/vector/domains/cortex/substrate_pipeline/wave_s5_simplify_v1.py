"""S5.2 — simplify operator surface (archived proofs, lease-first, env catalog)."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Final

WAVE_S5_SIMPLIFY_SCHEMA_VERSION: Final[int] = 1
WAVE_S5_STEP_22: Final[str] = "wave_s5_simplify_operator_surface"

CANONICAL_OPERATOR_SCRIPTS_V1: Final[tuple[str, ...]] = (
    "continuity_audit_snapshot.py",
    "graph_truth_audit_snapshot.py",
)

ARCHIVED_PROOFS_DIR_V1: Final[str] = "backend/scripts/archive/continuity_proofs"

# Ten operator-facing env vars (runbook §S5.2).
OPERATOR_ENV_VARS_V1: Final[tuple[dict[str, str], ...]] = (
    {"key": "CORTEX_EXECUTION_DUAL_LANE", "purpose": "Require dual-lane worker (must be 1 in prod)"},
    {"key": "CORTEX_CONVERGENCE_SWEEPER_ENABLED", "purpose": "Enable convergence sweeper beat"},
    {"key": "CORTEX_SUBSTRATE_PIPELINE_PHASE_08_ENABLED", "purpose": "Enable phase 08 synthesis"},
    {"key": "CORTEX_RETRIEVAL_SEMANTIC_MIX_GATE_ENABLED", "purpose": "Block org_link-heavy retrieval publish"},
    {"key": "CORTEX_SYNTHESIS_RETRIEVAL_SEMANTIC_GATE_ENABLED", "purpose": "Block synthesis on weak retrieval mix"},
    {"key": "CORTEX_SYNTHESIS_REQUIRE_EXECUTION_REFS", "purpose": "Require execution refs before synthesis LLM"},
    {"key": "CORTEX_SYNTHESIS_PER_ISLAND_ENABLED", "purpose": "Inline per-island synthesis pipeline path"},
    {"key": "CORTEX_AA5_REQUIRE_JOBS_COMPLETED", "purpose": "AA5 strict jobs_completed + useful artifact"},
    {"key": "CORTEX_WAVE_S5_SEMANTIC_PRIMARY_OPERATOR_KPI", "purpose": "Semantic panel as primary admin KPI"},
    {"key": "CORTEX_SYNTHESIS_JOB_RECONCILE_ON_MATERIALIZE", "purpose": "Reconcile stale synthesis jobs pre phase 08"},
)


def count_archived_continuity_proofs_v1(*, repo_root: Path | None = None) -> int:
    from vector.domains.cortex.substrate_pipeline.substrate_deploy_contract_v1 import (
        default_repo_root_v1,
        resolve_backend_scripts_dir_v1,
        resolve_repo_relative_path_v1,
    )

    root = repo_root or default_repo_root_v1()
    archive = resolve_repo_relative_path_v1(root, ARCHIVED_PROOFS_DIR_V1)
    if not archive.is_dir():
        archive = resolve_backend_scripts_dir_v1(repo_root=root) / "archive" / "continuity_proofs"
    if not archive.is_dir():
        return 0
    return len(list(archive.glob("continuity_*_proof.py")))


def verify_s5_2_simplify_contract_v1(*, repo_root: Path | None = None) -> dict[str, Any]:
    from vector.domains.cortex.substrate_pipeline.substrate_deploy_contract_v1 import (
        default_repo_root_v1,
        resolve_backend_scripts_dir_v1,
        resolve_repo_relative_path_v1,
    )

    root = repo_root or default_repo_root_v1()
    scripts = resolve_backend_scripts_dir_v1(repo_root=root)
    errors: list[str] = []
    live_proofs = list(scripts.glob("continuity_*_proof.py"))
    if live_proofs:
        errors.append(f"continuity_proofs_still_in_scripts_root:{len(live_proofs)}")
    archived = count_archived_continuity_proofs_v1(repo_root=root)
    if archived < 30:
        errors.append(f"archived_proof_count_low:{archived}")
    for name in CANONICAL_OPERATOR_SCRIPTS_V1:
        if not (scripts / name).is_file():
            errors.append(f"missing_canonical_script:{name}")
    return {
        "schema_version": WAVE_S5_SIMPLIFY_SCHEMA_VERSION,
        "s5_2_ok": not errors,
        "errors": errors,
        "archived_proof_count": archived,
        "canonical_operator_scripts": list(CANONICAL_OPERATOR_SCRIPTS_V1),
        "operator_env_var_count": len(OPERATOR_ENV_VARS_V1),
    }


def snapshot_wave_s5_simplify_contract_v1(*, repo_root: Path | None = None) -> dict[str, Any]:
    return {
        "schema_version": WAVE_S5_SIMPLIFY_SCHEMA_VERSION,
        "step": WAVE_S5_STEP_22,
        "contract": verify_s5_2_simplify_contract_v1(repo_root=repo_root),
        "operator_env_vars": list(OPERATOR_ENV_VARS_V1),
        "lease_truth_policy": "convergence_lease_fsm_authoritative_pipeline_receipt_mirror",
        "graph_tab_label": "Graph + Traversal",
    }
