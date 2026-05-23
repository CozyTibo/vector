#!/usr/bin/env python3
"""Phase A step A1 — synthesis job stale ``running`` reconcile prod proof."""

from __future__ import annotations

import argparse
import functools
import json
import os
import subprocess
import sys
import time
import uuid
from datetime import UTC, datetime
from pathlib import Path

os.environ.setdefault("VECTOR_SETTINGS_SKIP_DOTENV", "1")
os.environ.setdefault("VECTOR_USE_MOCK_CONNECTORS", "false")

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

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from vector.domains.cortex.substrate_pipeline.continuity_p0_baseline import (
    continuity_p0_baseline_path_v1,
    load_continuity_p0_baseline_v1,
    probe_prod_ecs_deploy_v1,
    save_continuity_p0_baseline_v1,
)
from vector.domains.cortex.substrate_pipeline.continuity_p0_synthesis_job_lifecycle import (
    DEFAULT_TENANT_ID,
    drive_synthesis_job_reconcile_v1,
    evaluate_p0_a1_synthesis_job_lifecycle_proof_v1,
    snapshot_synthesis_job_lifecycle_v1,
)

TENANT_DEFAULT = str(DEFAULT_TENANT_ID)


def _db_url() -> str:
    host = os.environ["DB_PROD_HOST"]
    port = os.environ.get("DB_PROD_PORT", "5432")
    user = os.environ["DB_PROD_USER"]
    password = os.environ["DB_PROD_PASSWORD"]
    dbname = os.environ.get("DB_PROD_DATABASE", "postgres")
    return f"postgresql+psycopg://{user}:{password}@{host}:{port}/{dbname}"


def _git_sha(expected: str | None) -> str:
    if expected:
        return expected.strip()
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO_ROOT, text=True).strip()


def main() -> int:
    parser = argparse.ArgumentParser(description="Phase A.1 synthesis job reconcile prod proof")
    parser.add_argument("--tenant", default=TENANT_DEFAULT)
    parser.add_argument("--closure-sha", default="")
    parser.add_argument("--baseline-date", default="2026-05-22")
    parser.add_argument("--wait-for-deploy", type=int, default=0)
    parser.add_argument(
        "--stale-seconds",
        type=int,
        default=0,
        help="0 = reconcile all running jobs (incident cleanup); >0 age threshold",
    )
    parser.add_argument("--dry-run", action="store_true", help="Snapshot only; do not mutate jobs")
    parser.add_argument("--snapshot-only", action="store_true", help="Alias for --dry-run")
    parser.add_argument("--trace-only", action="store_true", help="Skip deploy gate; static + snapshot")
    args = parser.parse_args()

    dry_run = args.dry_run or args.snapshot_only
    closure_sha = _git_sha(args.closure_sha or os.environ.get("CONTINUITY_DEPLOY_GIT_SHA"))
    tenant_id = uuid.UUID(args.tenant)
    deploy_started = datetime.now(UTC)

    prod_deploy: dict = {"verification": {"deploy_matches_closure_sha": args.trace_only}}
    if args.wait_for_deploy > 0 and not args.trace_only:
        deadline = time.monotonic() + args.wait_for_deploy
        while True:
            prod_deploy = probe_prod_ecs_deploy_v1(expected_sha=closure_sha)
            if prod_deploy["verification"]["deploy_matches_closure_sha"]:
                break
            if time.monotonic() >= deadline:
                break
            print(
                f"waiting for ECS {closure_sha[:12]}… "
                f"api={prod_deploy['api']['image_tag']} worker={prod_deploy['worker']['image_tag']}",
                file=sys.stderr,
            )
            time.sleep(30)
    elif not args.trace_only:
        prod_deploy = probe_prod_ecs_deploy_v1(expected_sha=closure_sha)

    engine = create_engine(_db_url())
    SessionLocal = sessionmaker(bind=engine)
    reconcile_drive: dict | None = None

    with SessionLocal() as session:
        snapshot = snapshot_synthesis_job_lifecycle_v1(session, tenant_id=tenant_id)
        if not dry_run:
            reconcile_drive = drive_synthesis_job_reconcile_v1(
                session,
                tenant_id=tenant_id,
                stale_after_seconds=args.stale_seconds,
                dry_run=False,
            )
            session.commit()
        else:
            reconcile_drive = drive_synthesis_job_reconcile_v1(
                session,
                tenant_id=tenant_id,
                stale_after_seconds=args.stale_seconds,
                dry_run=True,
            )

    proof = evaluate_p0_a1_synthesis_job_lifecycle_proof_v1(
        closure_git_sha=closure_sha,
        prod_deploy=prod_deploy,
        snapshot=snapshot,
        reconcile_drive=reconcile_drive,
        deploy_recorded_at=deploy_started,
        trace_only=args.trace_only,
    )
    print(json.dumps(proof, indent=2, default=str))

    baseline_path = continuity_p0_baseline_path_v1(
        repo_root=REPO_ROOT,
        date_suffix=args.baseline_date,
    )
    baseline = load_continuity_p0_baseline_v1(baseline_path)
    hist_after = dict((reconcile_drive or {}).get("histogram_after") or snapshot.get("histogram") or {})
    baseline["step_a1_synthesis_job_reconcile"] = {
        "validated_at": datetime.now(UTC).isoformat(),
        "closure_git_sha": closure_sha,
        "tenant_id": str(tenant_id),
        "p0_a1_pass": proof["p0_a1_pass"],
        "checks": proof["checks"],
        "checks_advisory": proof.get("checks_advisory"),
        "wiring_ok": (snapshot.get("wiring") or {}).get("wiring_ok"),
        "running_before": int(
            ((reconcile_drive or {}).get("histogram_before") or {}).get("running")
            or snapshot.get("running_count")
            or 0
        ),
        "running_after": int(hist_after.get("running", 0)),
        "reconciled_count": int((reconcile_drive or {}).get("reconciled_count") or 0),
        "stale_seconds": args.stale_seconds,
        "dry_run": dry_run,
        "trace_only": args.trace_only,
    }
    save_continuity_p0_baseline_v1(baseline_path, baseline)
    print(f"baseline updated: {baseline_path}")

    return 0 if proof["p0_a1_pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
