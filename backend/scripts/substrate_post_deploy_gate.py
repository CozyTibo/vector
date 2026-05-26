#!/usr/bin/env python3
"""Wave 5 — mandatory post-deploy gate: ECS probe + optional substrate truth baseline diff.

  python backend/scripts/substrate_post_deploy_gate.py --expected-sha $GITHUB_SHA
  python backend/scripts/substrate_post_deploy_gate.py --expected-sha $SHA --tenant <uuid> --baseline DOCS/audits/baselines/substrate_truth_fizzer_wave0_baseline.json
"""

from __future__ import annotations

import argparse
import functools
import json
import os
import sys
import uuid
from pathlib import Path

os.environ.setdefault("VECTOR_SETTINGS_SKIP_DOTENV", "1")

REPO_ROOT = Path(__file__).resolve().parents[2]
_env = REPO_ROOT / ".env"
if _env.exists():
    for line in _env.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))

for _k in ("GITHUB_APP_PRIVATE_KEY_PATH", "GITHUB_APP_PRIVATE_KEY"):
    os.environ.pop(_k, None)

sys.path.insert(0, str(REPO_ROOT / "backend" / "src"))

print = functools.partial(print, flush=True)  # noqa: A001

from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402

from vector.domains.cortex.substrate_pipeline.continuity_p0_baseline import (  # noqa: E402
    probe_prod_ecs_deploy_v1,
)
from vector.domains.cortex.substrate_pipeline.continuity_proof_panel import (  # noqa: E402
    DEFAULT_TENANT_ID,
)
from vector.domains.cortex.substrate_pipeline.substrate_deploy_contract_v1 import (  # noqa: E402
    DEFAULT_BASELINE_PATH,
    diff_substrate_truth_against_baseline_v1,
    load_substrate_truth_baseline_v1,
)
from vector.domains.cortex.substrate_pipeline.substrate_truth_v1 import (  # noqa: E402
    build_substrate_truth_v1,
)


def _db_url() -> str | None:
    if os.environ.get("DATABASE_URL", "").strip():
        return os.environ["DATABASE_URL"].strip()
    host = os.environ.get("DB_PROD_HOST", "").strip()
    if not host:
        return None
    port = os.environ.get("DB_PROD_PORT", "5432")
    user = os.environ["DB_PROD_USER"]
    password = os.environ["DB_PROD_PASSWORD"]
    dbname = os.environ.get("DB_PROD_DATABASE", "postgres")
    return f"postgresql+psycopg://{user}:{password}@{host}:{port}/{dbname}"


def main() -> int:
    parser = argparse.ArgumentParser(description="Substrate post-deploy gate (Wave 5)")
    parser.add_argument("--expected-sha", required=True, help="Git SHA deployed to ECS")
    parser.add_argument("--tenant", default=str(DEFAULT_TENANT_ID))
    parser.add_argument(
        "--baseline",
        default=DEFAULT_BASELINE_PATH,
        help="Committed baseline JSON for regression diff",
    )
    parser.add_argument("--skip-baseline-diff", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    report: dict[str, object] = {
        "surface_kind": "substrate_post_deploy_gate_v1",
        "expected_sha": args.expected_sha,
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
            print("ECS probe FAILED — API/worker tags do not match deploy SHA", file=sys.stderr)
            print(text, file=sys.stderr)
        return 1

    diff_out: dict[str, object] | None = None
    db_url = _db_url()
    if not args.skip_baseline_diff and db_url:
        tenant_id = uuid.UUID(args.tenant.strip())
        baseline_path = REPO_ROOT / args.baseline if not Path(args.baseline).is_absolute() else Path(args.baseline)
        baseline_doc = load_substrate_truth_baseline_v1(baseline_path, repo_root=REPO_ROOT)
        engine = create_engine(db_url)
        Session = sessionmaker(bind=engine)
        with Session() as session:
            current = build_substrate_truth_v1(session, tenant_id=tenant_id)
        diff_out = diff_substrate_truth_against_baseline_v1(current, baseline_doc)
        report["baseline_diff"] = diff_out
        report["current_substrate_truth"] = current
        if not diff_out.get("passed") and not diff_out.get("skipped"):
            report["passed"] = False
            text = json.dumps(report, indent=2, default=str)
            if args.json:
                print(text)
            else:
                print("Baseline diff FAILED", file=sys.stderr)
                print(text, file=sys.stderr)
            return 1
    elif not args.skip_baseline_diff:
        report["baseline_diff"] = {
            "skipped": True,
            "reason": "no_database_url_or_db_prod_host",
        }

    report["passed"] = True
    text = json.dumps(report, indent=2, default=str)
    if args.json:
        print(text)
    else:
        print("substrate_post_deploy_gate: pass")
        if diff_out and diff_out.get("skipped"):
            print(f"baseline diff skipped: {diff_out.get('reason')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
