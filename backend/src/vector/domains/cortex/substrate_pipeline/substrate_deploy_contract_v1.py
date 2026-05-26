"""Wave 5 — substrate coherence CI gates, post-deploy diff, and soak checks (V6–V8)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Final

SUBSTRATE_DEPLOY_CONTRACT_SCHEMA_VERSION: Final[int] = 1
DEFAULT_BASELINE_PATH: Final[str] = "DOCS/audits/baselines/substrate_truth_fizzer_wave0_baseline.json"


def discover_repo_root_v1(start: Path | None = None) -> Path | None:
    """Walk up from ``start`` until GitHub workflow dir is found (full monorepo checkout)."""
    anchor = start or Path(__file__).resolve()
    for candidate in (anchor, *anchor.parents):
        if (candidate / ".github" / "workflows" / "ci.yml").is_file():
            return candidate
    return None

SOAK_CHECK_V6_PROMOTION_RULES_MIN_V1: Final[int] = 3
SOAK_CHECK_V8_ISOLATED_PCT_MAX_V1: Final[float] = 90.0


def verify_substrate_coherence_ci_gates_v1() -> list[str]:
    """Static gates for waves 1–6 + M9 + D3/D5 (run in CI before deploy)."""
    from vector.domains.cortex.execution.scheduling import (
        verify_d3_graph_promotion_on_convergence_worker_v1,
        verify_d5_legacy_coordinator_enqueue_paths_deleted_v1,
        verify_m9_dead_celery_modules_absent_v1,
        verify_wave2_operator_paths_v1,
        verify_wave3_dead_weight_v1,
        verify_wave4_graph_truth_v1,
        verify_wave6_residue_purge_v1,
        verify_wave7_contract_collapse_v1,
        verify_wave8_operational_simplicity_v1,
        verify_wave9_final_domain_shape_v1,
    )

    errors: list[str] = []
    errors.extend(verify_m9_dead_celery_modules_absent_v1())
    errors.extend(verify_d3_graph_promotion_on_convergence_worker_v1())
    errors.extend(verify_d5_legacy_coordinator_enqueue_paths_deleted_v1())
    errors.extend(verify_wave2_operator_paths_v1())
    errors.extend(verify_wave3_dead_weight_v1())
    errors.extend(verify_wave4_graph_truth_v1())
    errors.extend(verify_wave6_residue_purge_v1())
    errors.extend(verify_wave7_contract_collapse_v1())
    errors.extend(verify_wave8_operational_simplicity_v1())
    errors.extend(verify_wave9_final_domain_shape_v1())
    return errors


def verify_wave5_deploy_contract_wiring_v1(*, repo_root: Path | None = None) -> list[str]:
    """Repo wiring for CI substrate job + CD post-deploy gate scripts."""
    root = repo_root or discover_repo_root_v1()
    if root is None:
        return []
    errors: list[str] = []

    ci = root / ".github" / "workflows" / "ci.yml"
    if not ci.is_file():
        errors.append("missing_ci_workflow")
    else:
        ci_text = ci.read_text(encoding="utf-8")
        if "backend-substrate-coherence" not in ci_text:
            errors.append("ci_missing_backend_substrate_coherence_job")
        if "test_substrate_wave" not in ci_text and "substrate_ci_gates" not in ci_text:
            errors.append("ci_missing_substrate_test_or_gates")

    deploy = root / ".github" / "workflows" / "deploy.yml"
    if not deploy.is_file():
        errors.append("missing_deploy_workflow")
    else:
        dep_text = deploy.read_text(encoding="utf-8")
        if "substrate_post_deploy_gate" not in dep_text:
            errors.append("deploy_missing_substrate_post_deploy_gate_step")
        if "ECS_SUBSTRATE_WORKER_SERVICE" not in dep_text or "substrate_tag" not in dep_text:
            errors.append("deploy_missing_substrate_worker_sha_verify")

    for rel in (
        "backend/scripts/substrate_ci_gates.py",
        "backend/scripts/substrate_post_deploy_gate.py",
        "backend/scripts/substrate_soak_v6_v8_check.py",
    ):
        if not (root / rel).is_file():
            errors.append(f"missing_script:{rel}")

    baseline = root / DEFAULT_BASELINE_PATH
    if not baseline.is_file():
        errors.append("missing_substrate_truth_baseline_template")

    return errors


def _truth_graph_panel(truth: dict[str, Any]) -> dict[str, Any]:
    graph = truth.get("graph")
    return dict(graph) if isinstance(graph, dict) else {}


def _truth_identity_counts(truth: dict[str, Any]) -> dict[str, Any]:
    identity = truth.get("identity")
    if not isinstance(identity, dict):
        return {}
    counts = identity.get("counts")
    return dict(counts) if isinstance(counts, dict) else {}


def diff_substrate_truth_against_baseline_v1(
    current: dict[str, Any],
    baseline: dict[str, Any],
    *,
    isolated_pct_max_delta: float = 5.0,
) -> dict[str, Any]:
    """Post-deploy regression diff (plan §7.2)."""
    errors: list[str] = []
    hints = baseline.get("acceptance_hints") if isinstance(baseline.get("acceptance_hints"), dict) else {}
    base_truth = baseline.get("substrate_truth")
    if not isinstance(base_truth, dict):
        return {
            "passed": True,
            "skipped": True,
            "reason": "baseline_substrate_truth_not_populated",
            "errors": [],
        }

    cur_graph = _truth_graph_panel(current)
    base_graph = _truth_graph_panel(base_truth)
    cur_promo = int(cur_graph.get("promotion_rule_count") or 0)
    base_promo = int(base_graph.get("promotion_rule_count") or 0)
    min_promo = int(hints.get("promotion_rule_count_min") or SOAK_CHECK_V6_PROMOTION_RULES_MIN_V1)
    if cur_promo < base_promo:
        errors.append(f"promotion_rule_count_regressed:{base_promo}->{cur_promo}")
    if cur_promo < min_promo:
        errors.append(f"promotion_rule_count_below_min:{cur_promo}<{min_promo}")

    cur_iso = float(cur_graph.get("isolated_pct") if cur_graph.get("isolated_pct") is not None else 100.0)
    base_iso = float(base_graph.get("isolated_pct") if base_graph.get("isolated_pct") is not None else cur_iso)
    if cur_iso > base_iso + isolated_pct_max_delta:
        errors.append(f"isolated_pct_increased:{base_iso}->{cur_iso}")

    iso_max = float(hints.get("isolated_pct_max") or SOAK_CHECK_V8_ISOLATED_PCT_MAX_V1)
    if cur_iso > iso_max:
        errors.append(f"isolated_pct_above_max:{cur_iso}>{iso_max}")

    cur_counts = _truth_identity_counts(current)
    base_counts = _truth_identity_counts(base_truth)
    for key in ("anchors_without_human_actor", "anchors_without_entity"):
        if key in cur_counts or key in base_counts:
            cur_v = int(cur_counts.get(key) or cur_counts.get("anchors_without_human_actors") or 0)
            base_v = int(base_counts.get(key) or base_counts.get("anchors_without_human_actors") or 0)
            if cur_v > base_v:
                errors.append(f"{key}_increased:{base_v}->{cur_v}")

    status = str(current.get("overall_status") or "")
    if status == "BROKEN":
        errors.append("overall_status_broken")

    return {
        "passed": not errors,
        "skipped": False,
        "errors": errors,
        "deltas": {
            "promotion_rule_count": {"baseline": base_promo, "current": cur_promo},
            "isolated_pct": {"baseline": base_iso, "current": cur_iso},
        },
    }


def evaluate_soak_contract_v6_v8_v1(
    substrate_truth: dict[str, Any],
    *,
    isolation_waiver: bool = False,
    prior_graph_hash: str | None = None,
) -> dict[str, Any]:
    """24h Fizzer soak subset: V6 promotion diversity, V7 hash motion, V8 isolation."""
    graph = _truth_graph_panel(substrate_truth)
    promotion_rule_count = int(graph.get("promotion_rule_count") or 0)
    isolated_pct = float(graph.get("isolated_pct") if graph.get("isolated_pct") is not None else 100.0)
    unique_auth_pairs = int(graph.get("unique_auth_pairs") or 0)

    v6_pass = promotion_rule_count >= SOAK_CHECK_V6_PROMOTION_RULES_MIN_V1
    v8_pass = isolated_pct < SOAK_CHECK_V8_ISOLATED_PCT_MAX_V1 or isolation_waiver

    v7_pass = True
    v7_detail: dict[str, Any] = {}
    lease_hash = None
    motion = substrate_truth.get("motion")
    if isinstance(motion, dict):
        lease_hash = str(motion.get("last_graph_projection_hash") or "").strip() or None
    if prior_graph_hash and unique_auth_pairs > 0:
        v7_pass = bool(lease_hash) and lease_hash != prior_graph_hash.strip()
        v7_detail = {
            "prior_hash": prior_graph_hash[:16],
            "current_hash": (lease_hash or "")[:16],
            "hash_changed": v7_pass,
        }
    elif unique_auth_pairs == 0:
        v7_pass = False
        v7_detail = {"reason": "no_authoritative_pairs"}
    else:
        v7_detail = {"reason": "no_prior_hash_for_delta_check_skipped"}

    checks = [
        {
            "id": "V6",
            "name": "promotion_diversity",
            "passed": v6_pass,
            "detail": {"promotion_rule_count": promotion_rule_count, "min": SOAK_CHECK_V6_PROMOTION_RULES_MIN_V1},
        },
        {
            "id": "V7",
            "name": "graph_hash_tracks_auth",
            "passed": v7_pass,
            "detail": {**v7_detail, "unique_auth_pairs": unique_auth_pairs},
        },
        {
            "id": "V8",
            "name": "isolation",
            "passed": v8_pass,
            "detail": {
                "isolated_pct": isolated_pct,
                "max": SOAK_CHECK_V8_ISOLATED_PCT_MAX_V1,
                "waiver": isolation_waiver,
            },
        },
    ]
    passed = all(c["passed"] for c in checks)
    return {
        "schema_version": SUBSTRATE_DEPLOY_CONTRACT_SCHEMA_VERSION,
        "surface_kind": "substrate_soak_v6_v8_v1",
        "passed": passed,
        "checks": checks,
        "isolation_waiver": isolation_waiver,
    }


def load_substrate_truth_baseline_v1(
    path: Path | str | None = None,
    *,
    repo_root: Path | None = None,
) -> dict[str, Any]:
    root = repo_root or discover_repo_root_v1() or Path(__file__).resolve().parents[6]
    p = Path(path) if path else root / DEFAULT_BASELINE_PATH
    return json.loads(p.read_text(encoding="utf-8"))


def run_substrate_ci_gate_report_v1(*, repo_root: Path | None = None) -> dict[str, Any]:
    coherence_errors = verify_substrate_coherence_ci_gates_v1()
    root = repo_root or discover_repo_root_v1()
    wiring_errors = verify_wave5_deploy_contract_wiring_v1(repo_root=root) if root else []
    wiring_skipped = root is None
    all_errors = [*coherence_errors, *wiring_errors]
    return {
        "schema_version": SUBSTRATE_DEPLOY_CONTRACT_SCHEMA_VERSION,
        "surface_kind": "substrate_ci_gate_report_v1",
        "passed": not all_errors,
        "coherence_errors": coherence_errors,
        "wiring_errors": wiring_errors,
        "wiring_checks_skipped": wiring_skipped,
    }
