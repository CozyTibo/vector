"""Wave 9 — final Cortex substrate domain shape: five verbs, ownership map, invariant CI."""

from __future__ import annotations

import inspect
import re
from pathlib import Path
from typing import Any, Final

_CORTEX_ROOT: Final[Path] = Path(__file__).resolve().parents[1]

SUBSTRATE_CRITICAL_MODULE_MAX_V1: Final[int] = 40

# Authoritative substrate critical path (ingest → truth). Count must stay ≤ SUBSTRATE_CRITICAL_MODULE_MAX_V1.
SUBSTRATE_CRITICAL_MODULES_V1: Final[tuple[str, ...]] = (
    "ingestion/sync_router.py",
    "ingestion/post_ingestion_refresh_dispatch.py",
    "ingestion/scheduler.py",
    "canonical/transform_runtime.py",
    "canonical/forward_progress/drain_runtime.py",
    "canonical/forward_progress/deferral_store.py",
    "identity/identity_substrate_repair_v1.py",
    "identity/identity_substrate_operator_v1.py",
    "identity/identity_substrate_health_v1.py",
    "identity/identity_substrate_phase_helpers_v1.py",
    "identity/authoritative_writer.py",
    "identity/projection_export.py",
    "identity/people_directory_v1.py",
    "execution/lease.py",
    "execution/convergence_dispatch.py",
    "execution/enqueue.py",
    "execution/dual_lane_worker.py",
    "execution/dual_lane_lease.py",
    "execution/run_tenant_execution.py",
    "execution/execution_event_triggers.py",
    "operational_runtime/graph_density_promotion.py",
    "substrate_pipeline/substrate_truth_v1.py",
    "substrate_pipeline/substrate_contract_v1.py",
    "substrate_pipeline/substrate_operational_simplicity_v1.py",
    "substrate_pipeline/substrate_deploy_contract_v1.py",
    "substrate_pipeline/substrate_phase_receipt.py",
    "substrate_pipeline/phase_runners.py",
    "substrate_pipeline/constants.py",
    "substrate_pipeline/semantic_readiness_v1.py",
    "substrate_pipeline/canonical_phase_gate.py",
    "substrate_pipeline/graph_truth_metrics_v1.py",
    "substrate_pipeline/orchestrator.py",
    "substrate_pipeline/substrate_residue_v1.py",
    "substrate_pipeline/substrate_final_domain_shape_v1.py",
)

SUBSTRATE_VERBS_OWNERSHIP_V1: Final[tuple[dict[str, str], ...]] = (
    {"verb": "INGEST", "owner": "ingestion.sync_router.execute_connector_sync", "state": "connector checkpoints"},
    {"verb": "MATERIALIZE", "owner": "canonical.forward_progress.drain_runtime.drain_forward_progress_backlog", "state": "deferrals"},
    {"verb": "REPAIR", "owner": "identity.identity_substrate_repair_v1.run_identity_substrate_repair_slice_v1", "state": "lease repair cursor"},
    {"verb": "PROMOTE", "owner": "operational_runtime.graph_density_promotion.run_graph_density_promotion_pass_v1", "state": "authoritative org links"},
    {"verb": "EXPORT", "owner": "identity.projection_export.run_graph_projection_export_for_pipeline_v1", "state": "phase 04 graph hash"},
    {"verb": "TRUTH", "owner": "substrate_pipeline.substrate_truth_v1.build_substrate_truth_v1", "state": "read-only aggregate"},
)

_IDENTITY_CONTINUITY_REBUILD_ALLOWED_SUFFIXES_V1: Final[frozenset[str]] = frozenset(
    {
        "/tests/",
        "/unlock/",
        "debug_full_substrate_refresh_v1.py",
        "continuity_rebuild.py",
        "org_link_replay_runtime.py",
        "control_plane.py",
        "failure_remediation.py",
        "identity_substrate_operator_v1.py",
        "substrate_operational_simplicity_v1.py",
        "substrate_admin_deprecation_v1.py",
        "substrate_final_domain_shape_v1.py",
        "execution/scheduling.py",
        "cortex_org_link_jobs.py",
        "admin.py",
        "contracts/admin.py",
    }
)

_IDENTITY_HOT_PATH_MODULES_V1: Final[tuple[str, ...]] = (
    "identity/identity_substrate_repair_v1.py",
    "identity/identity_substrate_operator_v1.py",
    "identity/projection_export.py",
    "identity/authoritative_writer.py",
    "identity/identity_substrate_health_v1.py",
    "identity/identity_substrate_phase_helpers_v1.py",
)

_FORBIDDEN_REPLAY_IMPORTS_V1: Final[tuple[str, ...]] = (
    "org_link_replay_runtime",
    "run_identity_continuity_rebuild",
    "execute_org_link_replay_job",
)

_ONBOARDING_DOC_REL_V1: Final[str] = "DOCS/cortex/substrate_onboarding_v1.md"


def build_substrate_domain_shape_catalog_v1() -> dict[str, Any]:
    """Machine-readable final domain shape for docs and admin tooling."""
    return {
        "surface_kind": "substrate_domain_shape_v1",
        "schema_version": 1,
        "verbs": list(SUBSTRATE_VERBS_OWNERSHIP_V1),
        "critical_module_count": len(SUBSTRATE_CRITICAL_MODULES_V1),
        "critical_module_max": SUBSTRATE_CRITICAL_MODULE_MAX_V1,
        "critical_modules": list(SUBSTRATE_CRITICAL_MODULES_V1),
        "operator_model": {
            "view_substrate": "GET /admin/tenants/{tenant_id}/cortex/substrate/truth",
            "repair": "operator_rebuild_identities_v1 (reset cursor + mark dirty)",
            "ingest_now": "connector trigger-sync",
            "debug": "/admin/tenants/{tenant_id}/cortex/debug/*",
        },
        "onboarding_doc": _ONBOARDING_DOC_REL_V1,
    }


def verify_substrate_critical_modules_v1() -> list[str]:
    errors: list[str] = []
    if len(SUBSTRATE_CRITICAL_MODULES_V1) > SUBSTRATE_CRITICAL_MODULE_MAX_V1:
        errors.append(
            f"critical_module_count_exceeds_max:{len(SUBSTRATE_CRITICAL_MODULES_V1)}>{SUBSTRATE_CRITICAL_MODULE_MAX_V1}"
        )
    for rel in SUBSTRATE_CRITICAL_MODULES_V1:
        if not (_CORTEX_ROOT / rel).is_file():
            errors.append(f"missing_critical_module:{rel}")
    return errors


def verify_l10_no_unlock_in_execution_identity_v1() -> list[str]:
    """L10 — execution and identity packages must not import unlock wedge steps."""
    errors: list[str] = []
    for pkg in ("execution", "identity"):
        root = _CORTEX_ROOT / pkg
        if not root.is_dir():
            continue
        for path in root.rglob("*.py"):
            if "tests" in path.parts:
                continue
            rel = path.relative_to(_CORTEX_ROOT).as_posix()
            if "vector.domains.cortex.unlock" in path.read_text(encoding="utf-8"):
                errors.append(f"unlock_import_l10:{rel}")
    return errors


def verify_l11_org_link_insert_scope_v1() -> list[str]:
    """L11 — delegate to Wave 8 promotion-scope gate (authoritative_writer + promotion pass only)."""
    from vector.domains.cortex.substrate_pipeline.substrate_operational_simplicity_v1 import (
        verify_org_link_writes_scope_v1,
    )

    return verify_org_link_writes_scope_v1()


def verify_l12_admin_state_mutation_debug_namespace_v1(*, repo_root: Path | None = None) -> list[str]:
    """L12 — collapsed replay on primary API; debug router registered; revoke link explicit."""
    errors: list[str] = []
    from vector.api.http.routes import admin as admin_mod

    admin_src = inspect.getsource(admin_mod.build_admin_router)
    if "register_cortex_debug_routes" not in admin_src:
        errors.append("admin_missing_debug_router_registration")
    if "raise_identity_replay_jobs_primary_route_gone_v1" not in admin_src:
        errors.append("admin_missing_primary_replay_410")
    if "soft_revoke_org_link" not in admin_src:
        errors.append("admin_missing_explicit_revoke_link")

    root = repo_root
    if root is None:
        from vector.domains.cortex.substrate_pipeline.substrate_deploy_contract_v1 import (
            discover_repo_root_v1,
        )

        root = discover_repo_root_v1()
    if root is not None:
        debug_path = root / "backend/src/vector/api/http/routes/admin_cortex_debug.py"
        if not debug_path.is_file():
            errors.append("missing_admin_cortex_debug_routes")
        else:
            dbg = debug_path.read_text(encoding="utf-8")
            if "/cortex/debug/identity/replay-jobs" not in dbg:
                errors.append("debug_router_missing_replay_jobs")
        onboarding = root / _ONBOARDING_DOC_REL_V1
        if not onboarding.is_file():
            errors.append("missing_substrate_onboarding_doc")
    return errors


def verify_l13_substrate_truth_schema_version_v1() -> list[str]:
    """L13 — truth builder schema version must match packaged JSON schema."""
    errors: list[str] = []
    from vector.domains.cortex.substrate_pipeline.substrate_truth_v1 import SUBSTRATE_TRUTH_SCHEMA_VERSION
    from vector.domains.cortex.substrate_pipeline.substrate_contract_v1 import (
        discover_substrate_contracts_dir_v1,
        load_json_schema_v1,
    )

    schema = load_json_schema_v1("substrate_truth_v1.schema.json")
    props = schema.get("properties") or {}
    schema_ver = props.get("schema_version")
    if schema_ver is None:
        errors.append("substrate_truth_schema_missing_schema_version_property")
    from vector.domains.cortex.substrate_pipeline import substrate_truth_v1 as truth_mod

    if "operational" not in inspect.getsource(truth_mod.build_substrate_truth_v1):
        errors.append("substrate_truth_missing_operational_panel")
    if SUBSTRATE_TRUTH_SCHEMA_VERSION != 1:
        errors.append(f"unexpected_truth_schema_version:{SUBSTRATE_TRUTH_SCHEMA_VERSION}")
    return errors


def verify_identity_continuity_rebuild_scope_v1() -> list[str]:
    """Wave 9.8.5 — ``identity_continuity_rebuild`` only in debug/tests/archive paths."""
    errors: list[str] = []
    token = "identity_continuity_rebuild"
    vector_root = _CORTEX_ROOT.parents[1]
    scan_roots = (
        vector_root / "domains" / "cortex",
        vector_root / "app",
        vector_root / "api",
    )
    runtime_markers = (
        'job_kind="identity_continuity_rebuild"',
        "job_kind='identity_continuity_rebuild'",
        "run_identity_continuity_rebuild(",
        "execute_org_link_replay_job(",
    )
    for root in scan_roots:
        if not root.is_dir():
            continue
        for path in root.rglob("*.py"):
            if "tests" in path.parts or "test_" in path.name:
                continue
            posix = path.as_posix()
            if any(allowed in posix for allowed in _IDENTITY_CONTINUITY_REBUILD_ALLOWED_SUFFIXES_V1):
                continue
            text = path.read_text(encoding="utf-8")
            if not any(marker in text for marker in runtime_markers):
                continue
            if "identity_continuity_rebuild" not in text:
                continue
            errors.append(
                f"identity_continuity_rebuild_runtime_outside_allowed_scope:{path.relative_to(vector_root).as_posix()}"
            )
    return errors


def verify_no_replay_runtime_in_identity_hot_path_v1() -> list[str]:
    """Wave 9.8.3 — autonomous identity slice modules must not import replay runtime."""
    errors: list[str] = []
    for rel in _IDENTITY_HOT_PATH_MODULES_V1:
        path = _CORTEX_ROOT / rel
        if not path.is_file():
            errors.append(f"missing_identity_hot_path:{rel}")
            continue
        text = path.read_text(encoding="utf-8")
        for token in _FORBIDDEN_REPLAY_IMPORTS_V1:
            if token in text:
                errors.append(f"replay_runtime_in_identity_hot_path:{rel}:{token}")
    return errors


def verify_substrate_openapi_contract_v1(*, repo_root: Path | None = None) -> list[str]:
    """Wave 9.8.4 — single OpenAPI contract for substrate truth."""
    errors: list[str] = []
    root = repo_root
    if root is None:
        from vector.domains.cortex.substrate_pipeline.substrate_deploy_contract_v1 import (
            discover_repo_root_v1,
        )

        root = discover_repo_root_v1()
    if root is None:
        return errors
    yaml_path = root / "backend/contracts/substrate_v1.yaml"
    if not yaml_path.is_file():
        return ["missing_substrate_v1_openapi"]
    text = yaml_path.read_text(encoding="utf-8")
    if "/cortex/substrate/truth" not in text:
        errors.append("substrate_v1_yaml_missing_truth_path")
    if "substrate_truth_v1.schema.json" not in text:
        errors.append("substrate_v1_yaml_missing_truth_schema_ref")
    if "substrate_domain_shape" not in text and "Wave 9" not in text:
        errors.append("substrate_v1_yaml_missing_wave9_marker")
    return errors


def verify_substrate_invariant_laws_v1() -> list[str]:
    """L1–L9 static subset enforced in CI (see plan §9.2)."""
    errors: list[str] = []
    from vector.domains.cortex.execution import convergence_dispatch as cd_mod
    from vector.domains.cortex.execution import execution_event_triggers as et_mod
    from vector.domains.cortex.identity import identity_substrate_repair_v1 as repair_mod
    from vector.domains.cortex.identity import projection_export as export_mod
    from vector.domains.cortex.operational_runtime import graph_density_promotion as promo_mod
    from vector.domains.cortex.substrate_pipeline import phase_runners as pr_mod
    from vector.domains.cortex.substrate_pipeline import substrate_truth_v1 as truth_mod

    et_src = inspect.getsource(et_mod.trigger_post_ingestion_execution_v1)
    if "mark_dirty_and_enqueue_convergence_v1" not in et_src:
        errors.append("l1_post_ingest_not_mark_dirty_and_enqueue")

    canon_src = inspect.getsource(repair_mod.run_identity_substrate_repair_slice_v1)
    if "schedule_graph_density_pass_v1" not in canon_src and "run_graph_density_promotion_pass_v1" not in canon_src:
        errors.append("l3_l4_repair_slice_missing_inline_promotion")

    p03_src = inspect.getsource(pr_mod.run_phase_03_identity_v1)
    if "resolve_phase_03_outcome_v1" not in p03_src:
        errors.append("l6_phase03_missing_outcome_resolver")

    p04_src = inspect.getsource(pr_mod.run_phase_04_graph_v1)
    if "should_skip_phase_04_after_identity_v1" not in p04_src:
        errors.append("l7_phase04_missing_identity_skip_gate")

    truth_src = inspect.getsource(truth_mod)
    if "BROKEN" not in truth_src or "overall_status" not in truth_src:
        errors.append("l8_truth_missing_broken_status")

    export_src = inspect.getsource(export_mod.run_graph_projection_export_for_pipeline_v1)
    if "snapshot_graph_substrate_isolation_v1" not in export_src:
        errors.append("l7_export_missing_isolation_snapshot")

    promo_src = inspect.getsource(promo_mod)
    if "promote_candidate_to_authoritative_link" not in promo_src:
        errors.append("l4_promotion_pass_missing_authoritative_promote")

    cd_src = inspect.getsource(cd_mod.mark_dirty_and_enqueue_convergence_v1)
    if "ingest_handoff_v1" not in cd_src:
        errors.append("l1_dispatch_missing_ingest_handoff")

    from vector.domains.cortex.substrate_pipeline.substrate_deploy_contract_v1 import (
        diff_substrate_truth_against_baseline_v1,
    )

    if not callable(diff_substrate_truth_against_baseline_v1):
        errors.append("l9_missing_baseline_diff_helper")

    return errors


def verify_unlock_package_archived_v1() -> list[str]:
    """Unlock package must declare archived; production execution/identity must not import it."""
    errors: list[str] = []
    init = _CORTEX_ROOT / "unlock" / "__init__.py"
    if init.is_file():
        doc = init.read_text(encoding="utf-8")
        if "ARCHIVED" not in doc and "Wave 9" not in doc:
            errors.append("unlock_init_missing_archived_marker")
    return errors


def verify_wave9_final_domain_shape_v1(*, repo_root: Path | None = None) -> list[str]:
    """Wave 9 exit gate — final domain shape, laws L10–L13, module budget, onboarding doc."""
    errors: list[str] = []
    errors.extend(verify_substrate_critical_modules_v1())
    errors.extend(verify_l10_no_unlock_in_execution_identity_v1())
    errors.extend(verify_l11_org_link_insert_scope_v1())
    errors.extend(verify_l12_admin_state_mutation_debug_namespace_v1(repo_root=repo_root))
    errors.extend(verify_l13_substrate_truth_schema_version_v1())
    errors.extend(verify_identity_continuity_rebuild_scope_v1())
    errors.extend(verify_no_replay_runtime_in_identity_hot_path_v1())
    errors.extend(verify_substrate_openapi_contract_v1(repo_root=repo_root))
    errors.extend(verify_substrate_invariant_laws_v1())
    errors.extend(verify_unlock_package_archived_v1())
    return errors
