"""S5.3 — KEEP list contract (surfaces that must remain after cleanup)."""

from __future__ import annotations

import importlib
from pathlib import Path
from typing import Any, Final

WAVE_S5_KEEP_SCHEMA_VERSION: Final[int] = 1
WAVE_S5_STEP_23: Final[str] = "wave_s5_keep_surfaces"

KEEP_SURFACES_V1: Final[tuple[dict[str, str], ...]] = (
    {
        "key": "dual_lane_worker_lease_fsm",
        "kind": "orchestration",
        "module": "vector.domains.cortex.execution.dual_lane_worker",
        "why": "Sole orchestration owner — dual-lane worker + lease FSM",
    },
    {
        "key": "continuity_audit_snapshot",
        "kind": "operator_script",
        "path": "backend/scripts/continuity_audit_snapshot.py",
        "why": "Runtime continuity truth (AA panel + phase receipts)",
    },
    {
        "key": "graph_truth_audit_snapshot",
        "kind": "operator_script",
        "path": "backend/scripts/graph_truth_audit_snapshot.py",
        "why": "Semantic / graph / retrieval / synthesis truth",
    },
    {
        "key": "retrieval_semantic_mix_gate",
        "kind": "gate",
        "module": "vector.domains.cortex.retrieval.retrieval_semantic_mix_v1",
        "why": "Honest blocker — org_link-heavy retrieval publish",
    },
    {
        "key": "synthesis_fail_loud_gates",
        "kind": "gate",
        "module": "vector.domains.cortex.synthesis.synthesis_fail_loud_contract_v1",
        "why": "Honest blocker — empty scope / weak retrieval / missing execution refs",
    },
    {
        "key": "identity_continuity_inspector",
        "kind": "admin_inspector",
        "route": "identity/continuity-inspector",
        "route_module": "admin.py",
        "why": "Debug surface — cross-system identity promotions",
    },
    {
        "key": "operator_graph_snapshot",
        "kind": "admin_inspector",
        "route": "operator/snapshots/graph",
        "why": "Debug surface — materialized graph snapshot (R6 operator inspect)",
    },
)


def _module_importable(module: str) -> bool:
    try:
        importlib.import_module(module)
        return True
    except Exception:  # noqa: BLE001
        return False


def verify_s5_3_keep_contract_v1(*, repo_root: Path | None = None) -> dict[str, Any]:
    from vector.domains.cortex.substrate_pipeline.substrate_deploy_contract_v1 import (
        discover_repo_root_v1,
        resolve_repo_relative_path_v1,
    )

    root = repo_root or discover_repo_root_v1() or Path(__file__).resolve().parents[6]
    errors: list[str] = []
    checked: list[dict[str, Any]] = []

    for item in KEEP_SURFACES_V1:
        key = item["key"]
        ok = True
        detail: dict[str, Any] = {"key": key, "kind": item["kind"]}
        if "module" in item:
            mod = item["module"]
            ok = _module_importable(mod)
            detail["module"] = mod
            if not ok:
                errors.append(f"missing_module:{key}")
        elif "path" in item:
            path = resolve_repo_relative_path_v1(root, item["path"])
            ok = path.is_file()
            detail["path"] = item["path"]
            if not ok:
                errors.append(f"missing_script:{key}")
        elif "route" in item:
            route_module = item.get("route_module", "admin_cortex_pipeline.py")
            route_rel = (
                "backend/src/vector/api/http/routes/"
                + (
                    "admin_cortex_operator.py"
                    if item["route"].startswith("operator/")
                    else route_module
                )
            )
            route_file = resolve_repo_relative_path_v1(root, route_rel)
            needle = item["route"].split("/")[-1]
            ok = route_file.is_file() and needle in route_file.read_text(encoding="utf-8")
            detail["route"] = item["route"]
            if not ok:
                errors.append(f"missing_admin_route:{key}")
        detail["present"] = ok
        detail["why"] = item["why"]
        checked.append(detail)

    # Dual-lane must remain wired into run_tenant execution.
    rte = resolve_repo_relative_path_v1(
        root,
        "backend/src/vector/domains/cortex/execution/run_tenant_execution.py",
    )
    if rte.is_file():
        rte_src = rte.read_text(encoding="utf-8")
        if "run_dual_lane_convergence_v1" not in rte_src:
            errors.append("run_tenant_missing_dual_lane_entry")
        if "ExecutionSerialFallbackRemovedError" not in rte_src:
            errors.append("run_tenant_missing_serial_fallback_removed_guard")
    else:
        errors.append("missing_run_tenant_execution")

    return {
        "schema_version": WAVE_S5_KEEP_SCHEMA_VERSION,
        "s5_3_ok": not errors,
        "errors": errors,
        "keep_surfaces": checked,
        "keep_surface_count": len(KEEP_SURFACES_V1),
    }


def snapshot_wave_s5_keep_contract_v1(*, repo_root: Path | None = None) -> dict[str, Any]:
    return {
        "schema_version": WAVE_S5_KEEP_SCHEMA_VERSION,
        "step": WAVE_S5_STEP_23,
        "contract": verify_s5_3_keep_contract_v1(repo_root=repo_root),
        "surfaces": list(KEEP_SURFACES_V1),
    }
