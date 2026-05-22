#!/usr/bin/env python3
"""Phase 0 step 0.5 — record closure deploy SHA in baseline (merge-safe, ECS verified)."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "backend" / "src"))

from vector.domains.cortex.substrate_pipeline.continuity_p0_baseline import (
    apply_step_0_5_to_baseline_v1,
    build_step_0_5_phase0_closure_v1,
    continuity_p0_baseline_path_v1,
    load_continuity_p0_baseline_v1,
    merge_step_0_2_deploy_into_baseline_v1,
    probe_prod_ecs_deploy_v1,
    save_continuity_p0_baseline_v1,
)


def _git_sha(expected: str | None) -> str:
    if expected:
        return expected.strip()
    out = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO_ROOT, text=True)
    return out.strip()


def _phase0_commits(closure_sha: str) -> dict[str, str]:
    commits: dict[str, str] = {"p0_4_phase05_proof": closure_sha}
    for key, path in (
        ("p0_a_schema_packaging", "789b25fbcc360488975b9fabb0ae90960fca54c1"),
        ("p0_2_deploy", None),
        ("p0_3_recovery", None),
    ):
        if path:
            commits[key] = path
    try:
        for label, rev in (
            ("p0_2_deploy", "0146cd05149c03a8b6e9572e1bc6739f24584b2e"),
            ("p0_3_recovery", "3cd8561539656d6c1196144755bb457b8b415103"),
        ):
            if label not in commits or commits[label] is None:
                commits[label] = rev
    except OSError:
        pass
    return commits


def main() -> int:
    parser = argparse.ArgumentParser(description="Phase 0 step 0.5 baseline closure")
    parser.add_argument(
        "--closure-sha",
        default="",
        help="Git SHA for Phase 0 closure (default: HEAD or CONTINUITY_DEPLOY_GIT_SHA)",
    )
    parser.add_argument(
        "--baseline-date",
        default="2026-05-22",
        help="Baseline file date suffix continuity_p0_<date>.json",
    )
    parser.add_argument(
        "--wait-for-deploy",
        type=int,
        default=0,
        metavar="SECONDS",
        help="Poll ECS until both services match closure SHA (0 = single probe)",
    )
    parser.add_argument(
        "--skip-deploy-check",
        action="store_true",
        help="Record closure artifact without requiring ECS match (not for sign-off)",
    )
    args = parser.parse_args()

    closure_sha = _git_sha(args.closure_sha or os.environ.get("CONTINUITY_DEPLOY_GIT_SHA"))
    baseline_path = continuity_p0_baseline_path_v1(
        repo_root=REPO_ROOT,
        date_suffix=args.baseline_date,
    )
    baseline = load_continuity_p0_baseline_v1(baseline_path)

    deadline = time.monotonic() + max(0, args.wait_for_deploy)
    prod_deploy: dict = {}
    while True:
        prod_deploy = probe_prod_ecs_deploy_v1(expected_sha=closure_sha)
        if prod_deploy["verification"]["deploy_matches_closure_sha"]:
            break
        if args.skip_deploy_check or time.monotonic() >= deadline:
            break
        print(
            f"waiting for ECS closure tag {closure_sha[:12]}… "
            f"(api={prod_deploy['api']['image_tag']} worker={prod_deploy['worker']['image_tag']})",
            file=sys.stderr,
        )
        time.sleep(30)

    baseline = merge_step_0_2_deploy_into_baseline_v1(baseline, prod_deploy)
    closure = build_step_0_5_phase0_closure_v1(
        closure_git_sha=closure_sha,
        prod_deploy=prod_deploy,
        baseline=baseline,
        phase0_commits=_phase0_commits(closure_sha),
    )
    baseline = apply_step_0_5_to_baseline_v1(baseline, closure)
    save_continuity_p0_baseline_v1(baseline_path, baseline)

    print(json.dumps(closure, indent=2))
    print(f"wrote {baseline_path}", file=sys.stderr)

    if not args.skip_deploy_check and not closure["verification"]["step_05_pass"]:
        print("FAIL: step 0.5 not satisfied (prerequisites or ECS deploy mismatch)", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
