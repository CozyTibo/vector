#!/usr/bin/env python3
"""Phase A step A5 — ban ``--trace-only`` as production baseline sign-off."""

from __future__ import annotations

import argparse
import functools
import json
import os
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

os.environ.setdefault("VECTOR_SETTINGS_SKIP_DOTENV", "1")

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "backend" / "src"))

print = functools.partial(print, flush=True)  # noqa: A001

from vector.domains.cortex.substrate_pipeline.continuity_p0_baseline import (
    continuity_p0_baseline_path_v1,
    load_continuity_p0_baseline_v1,
    probe_prod_ecs_deploy_v1,
    save_continuity_p0_baseline_v1,
    snapshot_prod_ecs_deploy_v1,
)
from vector.domains.cortex.substrate_pipeline.continuity_p0_trace_only_policy import (
    PHASE_A_BASELINE_STEP_KEYS,
    evaluate_p0_a5_trace_only_ban_proof_v1,
    record_p0_step_baseline_v1,
    validate_baseline_prod_signoff_steps_v1,
    verify_a5_trace_only_ban_wiring_v1,
)


def _git_sha(expected: str | None) -> str:
    if expected:
        return expected.strip()
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO_ROOT, text=True).strip()


def main() -> int:
    parser = argparse.ArgumentParser(description="Phase A.5 trace-only prod sign-off ban proof")
    parser.add_argument("--closure-sha", default="")
    parser.add_argument("--baseline-date", default="2026-05-22")
    parser.add_argument(
        "--use-deployed-closure",
        action="store_true",
        help="Use prod API ECS tag as closure SHA",
    )
    args = parser.parse_args()

    closure_sha = _git_sha(args.closure_sha or os.environ.get("CONTINUITY_DEPLOY_GIT_SHA"))
    if args.use_deployed_closure:
        closure_sha = str(snapshot_prod_ecs_deploy_v1()["api"]["image_tag"])
        print(f"using deployed API tag as closure: {closure_sha[:12]}…", file=sys.stderr)

    deploy_started = datetime.now(UTC)
    prod_deploy = probe_prod_ecs_deploy_v1(expected_sha=closure_sha)
    wiring = verify_a5_trace_only_ban_wiring_v1(repo_root=REPO_ROOT)

    baseline_path = continuity_p0_baseline_path_v1(
        repo_root=REPO_ROOT,
        date_suffix=args.baseline_date,
    )
    baseline = load_continuity_p0_baseline_v1(baseline_path)
    signoff_audit = validate_baseline_prod_signoff_steps_v1(
        baseline,
        step_keys=PHASE_A_BASELINE_STEP_KEYS,
    )

    proof = evaluate_p0_a5_trace_only_ban_proof_v1(
        closure_git_sha=closure_sha,
        prod_deploy=prod_deploy,
        baseline=baseline,
        wiring=wiring,
        signoff_audit=signoff_audit,
        deploy_recorded_at=deploy_started,
    )
    proof["wiring"] = wiring
    proof["signoff_audit"] = signoff_audit
    print(json.dumps(proof, indent=2, default=str))

    step_record = {
        "validated_at": datetime.now(UTC).isoformat(),
        "closure_git_sha": closure_sha,
        "p0_a5_pass": proof["p0_a5_pass"],
        "checks": proof["checks"],
        "checks_advisory": proof.get("checks_advisory"),
        "wiring_ok": wiring.get("wiring_ok"),
        "scripts_checked": wiring.get("scripts_checked"),
        "phase_a_violations": signoff_audit.get("violations"),
    }
    record_p0_step_baseline_v1(
        baseline,
        "step_a5_trace_only_ban",
        step_record,
        trace_only=False,
    )
    save_continuity_p0_baseline_v1(baseline_path, baseline)
    print(f"baseline updated: {baseline_path}")

    return 0 if proof["p0_a5_pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
