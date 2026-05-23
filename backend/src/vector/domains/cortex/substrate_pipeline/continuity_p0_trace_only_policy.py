"""Phase A step A5 — ban ``--trace-only`` as production baseline sign-off."""

from __future__ import annotations

import argparse
import os
from collections.abc import Mapping
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

P0_A5_STEP = "step_a5_trace_only_ban"
TRACE_ONLY_CI_ENV = "VECTOR_CONTINUITY_CI_ONLY_TRACE"
TRACE_ONLY_POLICY_SCHEMA_VERSION = 1

PHASE_A_BASELINE_STEP_KEYS: tuple[str, ...] = (
    "step_a1_synthesis_job_reconcile",
    "step_a2_ecs_deploy_align",
    "step_a3_tcre_queued_drain",
    "step_a4_aa_panel_strict",
    "step_a5_trace_only_ban",
    "step_a6_synthesis_terminal_transitions",
)

P3_BASELINE_STEP_KEYS: tuple[str, ...] = (
    "step_3_1_p2c_island_registry",
    "step_3_2_p2b_event_triggers",
    "step_3_3_p2d_per_island_synthesis",
    "step_3_4_p2e_ingest_deferral",
)

PROD_SIGNOFF_STEP_PREFIXES: tuple[str, ...] = ("step_a", "step_3_")


class TraceOnlyProdSignoffError(ValueError):
    """Raised when a prod baseline update is attempted with ``trace_only=True``."""


def ci_only_trace_mode_enabled_v1() -> bool:
    return os.environ.get(TRACE_ONLY_CI_ENV, "").strip() in ("1", "true", "yes", "on")


def add_trace_only_ci_argparse_v1(parser: argparse.ArgumentParser) -> None:
    """Register ``--trace-only`` (CI-only; never writes baseline)."""
    parser.add_argument(
        "--trace-only",
        action="store_true",
        help=(
            f"CI-only wiring probe (requires env {TRACE_ONLY_CI_ENV}=1). "
            "Skips ECS deploy gate and does NOT update the committed baseline."
        ),
    )


def resolve_trace_only_cli_v1(*, requested: bool) -> bool:
    """Validate CLI flag and return effective trace-only mode."""
    if not requested:
        return False
    if not ci_only_trace_mode_enabled_v1():
        raise TraceOnlyProdSignoffError(
            f"--trace-only requires CI-only mode: set {TRACE_ONLY_CI_ENV}=1. "
            "Production baseline sign-off must run without --trace-only "
            "(use --use-deployed-closure when local HEAD is not on ECS)."
        )
    return True


def prod_signoff_valid_v1(*, trace_only: bool) -> bool:
    return not trace_only


def merge_prod_signoff_checks_v1(
    checks: dict[str, Any],
    *,
    trace_only: bool,
) -> dict[str, Any]:
    out = dict(checks)
    out["prod_signoff_valid"] = prod_signoff_valid_v1(trace_only=trace_only)
    return out


def annotate_step_record_signoff_v1(
    step_record: dict[str, Any],
    *,
    trace_only: bool,
) -> dict[str, Any]:
    out = dict(step_record)
    out["trace_only"] = trace_only
    out["signoff_grade"] = "ci_probe" if trace_only else "prod"
    out["trace_only_policy_version"] = TRACE_ONLY_POLICY_SCHEMA_VERSION
    return out


def assert_prod_baseline_signoff_allowed_v1(*, trace_only: bool) -> None:
    if trace_only:
        raise TraceOnlyProdSignoffError(
            "Refusing baseline update: trace_only=True is CI-only and cannot sign off prod. "
            f"Re-run without --trace-only (deploy gate uses real ECS probe)."
        )


def record_p0_step_baseline_v1(
    baseline: dict[str, Any],
    step_key: str,
    step_record: dict[str, Any],
    *,
    trace_only: bool,
) -> dict[str, Any]:
    """Merge a step record; refuses prod sign-off when ``trace_only``."""
    assert_prod_baseline_signoff_allowed_v1(trace_only=trace_only)
    baseline[step_key] = annotate_step_record_signoff_v1(step_record, trace_only=trace_only)
    policy = dict(baseline.get("trace_only_policy") or {})
    policy.update(
        {
            "schema_version": TRACE_ONLY_POLICY_SCHEMA_VERSION,
            "ci_only_env": TRACE_ONLY_CI_ENV,
            "updated_at": datetime.now(UTC).isoformat(),
            "last_prod_signoff_step": step_key,
        }
    )
    baseline["trace_only_policy"] = policy
    return baseline


def save_p0_step_baseline_v1(
    path: Path,
    baseline: dict[str, Any],
    *,
    step_key: str,
    step_record: dict[str, Any],
    trace_only: bool,
    save_fn: Any,
) -> Path | None:
    """Persist baseline only for prod sign-off; CI trace mode skips the write."""
    if trace_only:
        return None
    from vector.domains.cortex.substrate_pipeline.continuity_p0_baseline import (
        save_continuity_p0_baseline_v1,
    )

    record_p0_step_baseline_v1(baseline, step_key, step_record, trace_only=False)
    return save_fn(path, baseline)


def validate_baseline_prod_signoff_steps_v1(
    baseline: Mapping[str, Any],
    *,
    step_keys: tuple[str, ...] | None = None,
) -> dict[str, Any]:
    """Ensure listed steps (default Phase A) have ``trace_only: false``."""
    keys = step_keys or PHASE_A_BASELINE_STEP_KEYS
    violations: list[dict[str, Any]] = []
    checked: list[str] = []
    for key in keys:
        block = baseline.get(key)
        if not isinstance(block, Mapping):
            continue
        checked.append(key)
        if bool(block.get("trace_only")):
            violations.append(
                {
                    "step_key": key,
                    "trace_only": block.get("trace_only"),
                    "signoff_grade": block.get("signoff_grade"),
                }
            )
    return {
        "checked_steps": checked,
        "violations": violations,
        "all_prod_signoff": not violations,
    }


def _proof_script_paths_v1(repo_root: Path) -> list[Path]:
    scripts = repo_root / "backend" / "scripts"
    patterns = (
        "continuity_p0_phase_a*_proof.py",
        "continuity_p0_phase_b*_proof.py",
        "continuity_p3_phase*_proof.py",
    )
    out: list[Path] = []
    for pat in patterns:
        out.extend(sorted(scripts.glob(pat)))
    return out


def verify_a5_trace_only_ban_wiring_v1(*, repo_root: Path | None = None) -> dict[str, Any]:
    """Static wiring: proof scripts use shared policy helpers."""
    root = repo_root or Path(__file__).resolve().parents[6]
    errors: list[str] = []
    required_import = "continuity_p0_trace_only_policy"
    required_calls = (
        "resolve_trace_only_cli_v1",
        "save_p0_step_baseline_v1",
    )
    for script in _proof_script_paths_v1(root):
        src = script.read_text(encoding="utf-8")
        if required_import not in src:
            errors.append(f"missing_policy_import:{script.name}")
            continue
        if script.name == "continuity_p0_phase_a5_trace_only_ban_proof.py":
            if "record_p0_step_baseline_v1" not in src:
                errors.append(f"missing_record_p0_step_baseline_v1:{script.name}")
            continue
        for call in required_calls:
            if call not in src:
                errors.append(f"missing_{call}:{script.name}")
        if "--trace-only" in src and "add_trace_only_ci_argparse_v1" not in src:
            errors.append(f"missing_ci_trace_argparse:{script.name}")
    return {"wiring_ok": not errors, "errors": errors, "scripts_checked": len(_proof_script_paths_v1(root))}


def evaluate_p0_a5_trace_only_ban_proof_v1(
    *,
    closure_git_sha: str,
    prod_deploy: dict[str, Any],
    baseline: dict[str, Any],
    wiring: dict[str, Any],
    signoff_audit: dict[str, Any],
    deploy_recorded_at: datetime | None = None,
) -> dict[str, Any]:
    deploy_ok = bool((prod_deploy.get("verification") or {}).get("deploy_matches_closure_sha"))
    policy = dict(baseline.get("trace_only_policy") or {})
    checks = {
        "ecs_deploy_matches_closure_sha": deploy_ok,
        "static_wiring_ok": bool(wiring.get("wiring_ok")),
        "trace_only_policy_present": bool(policy.get("schema_version")),
        "phase_a_steps_prod_signoff": bool(signoff_audit.get("all_prod_signoff")),
        "no_phase_a_trace_only_violations": not list(signoff_audit.get("violations") or []),
        "ci_env_documented": policy.get("ci_only_env") == TRACE_ONLY_CI_ENV,
    }
    checks_advisory = {
        "checked_steps": signoff_audit.get("checked_steps"),
        "violations": signoff_audit.get("violations"),
        "scripts_checked": wiring.get("scripts_checked"),
    }
    step_a5_pass = all(checks.values())
    return {
        "step": P0_A5_STEP,
        "closure_git_sha": closure_git_sha,
        "deploy_recorded_at": deploy_recorded_at.isoformat() if deploy_recorded_at else None,
        "prod_deploy": prod_deploy,
        "checks": checks,
        "checks_advisory": checks_advisory,
        "p0_a5_pass": step_a5_pass,
        "verification": {
            "step_a5_pass": step_a5_pass,
            "cleared_for_a6": step_a5_pass,
        },
    }
