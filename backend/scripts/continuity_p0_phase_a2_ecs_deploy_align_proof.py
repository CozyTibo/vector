#!/usr/bin/env python3
"""Phase A step A2 — align prod ECS API + worker to the same closure git SHA."""

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
)
from vector.domains.cortex.substrate_pipeline.continuity_p0_baseline import snapshot_prod_ecs_deploy_v1
from vector.domains.cortex.substrate_pipeline.continuity_p0_ecs_deploy_align import (
    drive_prod_ecs_deploy_align_v1,
    evaluate_p0_a2_ecs_deploy_align_proof_v1,
    realign_ecs_worker_to_api_image_tag_v1,
    verify_a2_ecs_deploy_align_wiring_v1,
    wait_for_prod_ecs_deploy_v1,
)


def _git_sha(expected: str | None) -> str:
    if expected:
        return expected.strip()
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO_ROOT, text=True).strip()


def main() -> int:
    parser = argparse.ArgumentParser(description="Phase A.2 ECS API+worker deploy alignment proof")
    parser.add_argument("--closure-sha", default="")
    parser.add_argument("--baseline-date", default="2026-05-22")
    parser.add_argument(
        "--wait-for-deploy",
        type=int,
        default=900,
        metavar="SECONDS",
        help="Poll ECS until API+worker match closure SHA",
    )
    parser.add_argument(
        "--deploy",
        action="store_true",
        help="Run prod_deploy_backend_worker.sh before waiting (build+push+ECS update)",
    )
    parser.add_argument(
        "--probe-only",
        action="store_true",
        help="Single ECS probe; no wait loop",
    )
    parser.add_argument(
        "--trace-only",
        action="store_true",
        help="Skip deploy gate failures (CI/static only)",
    )
    parser.add_argument(
        "--use-deployed-closure",
        action="store_true",
        help="Use prod API image tag as closure SHA (honest sign-off for current ECS state)",
    )
    parser.add_argument(
        "--realign-worker",
        action="store_true",
        help="ECS-only: update worker task to API image tag before probe/wait",
    )
    args = parser.parse_args()

    closure_sha = _git_sha(args.closure_sha or os.environ.get("CONTINUITY_DEPLOY_GIT_SHA"))
    if args.use_deployed_closure:
        snap = snapshot_prod_ecs_deploy_v1()
        closure_sha = str(snap["api"]["image_tag"])
        print(f"using deployed API tag as closure: {closure_sha[:12]}…", file=sys.stderr)
    deploy_started = datetime.now(UTC)
    wiring = verify_a2_ecs_deploy_align_wiring_v1(repo_root=REPO_ROOT)

    realign_drive: dict | None = None
    if args.realign_worker:
        print("realigning worker to API image tag (ECS-only)…", file=sys.stderr)
        realign_drive = realign_ecs_worker_to_api_image_tag_v1()
        print(json.dumps(realign_drive, indent=2, default=str), file=sys.stderr)

    deploy_drive: dict | None = None
    if args.deploy:
        print(f"deploying closure SHA {closure_sha[:12]}…", file=sys.stderr)
        deploy_drive = drive_prod_ecs_deploy_align_v1(repo_root=REPO_ROOT, closure_sha=closure_sha)
        if not deploy_drive.get("acquired"):
            print(json.dumps(deploy_drive, indent=2), file=sys.stderr)
            if not args.trace_only:
                return 1

    if args.probe_only:
        prod_deploy = probe_prod_ecs_deploy_v1(expected_sha=closure_sha)
    else:
        prod_deploy = wait_for_prod_ecs_deploy_v1(
            expected_sha=closure_sha,
            timeout_seconds=args.wait_for_deploy,
        )
        if prod_deploy.get("wait_outcome") == "timeout" and not args.trace_only:
            print(
                f"timeout: api={prod_deploy['api']['image_tag']} "
                f"worker={prod_deploy['worker']['image_tag']} "
                f"expected={closure_sha[:12]}",
                file=sys.stderr,
            )

    proof = evaluate_p0_a2_ecs_deploy_align_proof_v1(
        closure_git_sha=closure_sha,
        prod_deploy=prod_deploy,
        wiring=wiring,
        deploy_drive=deploy_drive,
        deploy_recorded_at=deploy_started,
        trace_only=args.trace_only,
    )
    print(json.dumps(proof, indent=2, default=str))

    baseline_path = continuity_p0_baseline_path_v1(
        repo_root=REPO_ROOT,
        date_suffix=args.baseline_date,
    )
    baseline = load_continuity_p0_baseline_v1(baseline_path)
    ver = dict(prod_deploy.get("verification") or {})
    baseline["step_a2_ecs_deploy_align"] = {
        "validated_at": datetime.now(UTC).isoformat(),
        "closure_git_sha": closure_sha,
        "p0_a2_pass": proof["p0_a2_pass"],
        "checks": proof["checks"],
        "checks_advisory": proof.get("checks_advisory"),
        "wiring_ok": wiring.get("wiring_ok"),
        "api_image_tag": (prod_deploy.get("api") or {}).get("image_tag"),
        "worker_image_tag": (prod_deploy.get("worker") or {}).get("image_tag"),
        "deploy_matches_closure_sha": ver.get("deploy_matches_closure_sha"),
        "both_services_on_same_tag": ver.get("both_services_on_same_tag"),
        "wait_outcome": prod_deploy.get("wait_outcome"),
        "deploy_ran": bool(args.deploy),
        "realign_ran": bool(args.realign_worker),
        "use_deployed_closure": bool(args.use_deployed_closure),
        "trace_only": args.trace_only,
        "realign_drive": realign_drive,
    }
    save_continuity_p0_baseline_v1(baseline_path, baseline)
    print(f"baseline updated: {baseline_path}")

    return 0 if proof["p0_a2_pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
