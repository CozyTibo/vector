#!/usr/bin/env python3
"""Post-deploy gate: verify prod ECS services run the expected image SHA.

Substrate truth baseline diff was removed with ingestion-only cortex; use
``--skip-baseline-diff`` (default) or omit DB secrets in CI.
"""

from __future__ import annotations

import argparse
import functools
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "backend" / "src"))

print = functools.partial(print, flush=True)  # noqa: A001

from vector.infrastructure.deploy.ecs_deploy_probe_v1 import probe_prod_ecs_deploy_v1  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Post-deploy ECS image tag gate")
    parser.add_argument("--expected-sha", required=True, help="Git SHA deployed to ECS")
    parser.add_argument(
        "--skip-baseline-diff",
        action="store_true",
        default=True,
        help="No-op (substrate baseline removed); kept for workflow compatibility",
    )
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    report: dict[str, object] = {
        "surface_kind": "ingestion_post_deploy_gate_v1",
        "expected_sha": args.expected_sha,
        "baseline_diff": {
            "skipped": True,
            "reason": "substrate_pipeline_removed",
        },
    }

    deploy = probe_prod_ecs_deploy_v1(expected_sha=args.expected_sha)
    report["ecs_probe"] = deploy
    ver = dict(deploy.get("verification") or {})
    if not ver.get("deploy_matches_closure_sha"):
        report["passed"] = False
        text = json.dumps(report, indent=2, default=str)
        if args.json:
            print(text)
        else:
            print("ECS probe FAILED — service image tags do not match deploy SHA", file=sys.stderr)
            print(text, file=sys.stderr)
        return 1

    report["passed"] = True
    text = json.dumps(report, indent=2, default=str)
    if args.json:
        print(text)
    else:
        print("post_deploy_gate: pass")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
