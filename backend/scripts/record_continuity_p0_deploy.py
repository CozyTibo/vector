#!/usr/bin/env python3
"""Record Phase 0 deploy SHA + verify prod ECS images match (step 0.2; merge-safe baseline)."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "backend" / "src"))

from vector.domains.cortex.substrate_pipeline.continuity_p0_baseline import (
    P0_A_SCHEMA_COMMIT,
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


def main() -> int:
    expected_sha = _git_sha(os.environ.get("CONTINUITY_DEPLOY_GIT_SHA"))
    deploy = probe_prod_ecs_deploy_v1(expected_sha=expected_sha)
    deploy["notes"] = (
        "Step 0.2 complete when both ECS services run ECR tags equal deploy git SHA "
        "(includes bundled OCTS walk policy under traversal/schemas)."
    )
    deploy["p0_a_schema_packaging_commit"] = P0_A_SCHEMA_COMMIT

    date_suffix = datetime.now(UTC).strftime("%Y-%m-%d")
    out_path = continuity_p0_baseline_path_v1(repo_root=REPO_ROOT, date_suffix=date_suffix)
    baseline = load_continuity_p0_baseline_v1(out_path)
    baseline = merge_step_0_2_deploy_into_baseline_v1(baseline, deploy)
    save_continuity_p0_baseline_v1(out_path, baseline)

    print(json.dumps(baseline.get("step_0_2_deploy", deploy), indent=2))
    print(f"wrote {out_path} (merged)", file=sys.stderr)

    ver = deploy["verification"]
    if not ver["deploy_matches_closure_sha"]:
        print(
            f"FAIL: expected both images tagged {expected_sha}, "
            f"got api={deploy['api']['image_tag']} worker={deploy['worker']['image_tag']}",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
