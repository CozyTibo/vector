#!/usr/bin/env python3
"""Phase 1 step 1.2 — deploy P3′ to prod and prove autonomous walks (no step 9 wedge)."""

from __future__ import annotations

import argparse
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

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from vector.domains.cortex.substrate_pipeline.continuity_p0_baseline import (
    continuity_p0_baseline_path_v1,
    load_continuity_p0_baseline_v1,
    probe_prod_ecs_deploy_v1,
    save_continuity_p0_baseline_v1,
)
from vector.domains.cortex.substrate_pipeline.continuity_p1_p3_deploy import (
    evaluate_p1_2_p3_deploy_proof_v1,
    get_active_pipeline_run_id_v1,
    run_autonomous_walk_schedule_pass_v1,
    snapshot_walk_footprint_v1,
)

TENANT_DEFAULT = "c08ef32b-f89a-40f6-9566-e19b5329436f"


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
    parser = argparse.ArgumentParser(description="Phase 1.2 P3′ deploy + autonomous walk proof")
    parser.add_argument("--tenant", default=TENANT_DEFAULT)
    parser.add_argument("--closure-sha", default="")
    parser.add_argument("--baseline-date", default="2026-05-22")
    parser.add_argument(
        "--wait-for-deploy",
        type=int,
        default=600,
        metavar="SECONDS",
        help="Poll ECS until API+worker match closure SHA",
    )
    parser.add_argument(
        "--schedule-only",
        action="store_true",
        help="Skip deploy wait; only run schedule pass + proof",
    )
    args = parser.parse_args()

    closure_sha = _git_sha(args.closure_sha or os.environ.get("CONTINUITY_DEPLOY_GIT_SHA"))
    tenant_id = uuid.UUID(args.tenant)
    deploy_started = datetime.now(UTC)

    deadline = time.monotonic() + max(0, args.wait_for_deploy)
    prod_deploy: dict = {}
    while True:
        prod_deploy = probe_prod_ecs_deploy_v1(expected_sha=closure_sha)
        if prod_deploy["verification"]["deploy_matches_closure_sha"] or args.schedule_only:
            break
        if time.monotonic() >= deadline:
            break
        print(
            f"waiting for ECS {closure_sha[:12]}… "
            f"api={prod_deploy['api']['image_tag']} worker={prod_deploy['worker']['image_tag']}",
            file=sys.stderr,
        )
        time.sleep(30)

    engine = create_engine(_db_url())
    SessionLocal = sessionmaker(bind=engine)

    with SessionLocal() as session:
        walks_before = snapshot_walk_footprint_v1(session, tenant_id=tenant_id)
        pipeline_run_id = get_active_pipeline_run_id_v1(session, tenant_id=tenant_id)
        schedule_pass = run_autonomous_walk_schedule_pass_v1(
            session,
            tenant_id=tenant_id,
            pipeline_run_id=pipeline_run_id,
            force=False,
        )
        if not schedule_pass.get("scheduled") or int(schedule_pass.get("persisted_new") or 0) == 0:
            schedule_pass = run_autonomous_walk_schedule_pass_v1(
                session,
                tenant_id=tenant_id,
                pipeline_run_id=pipeline_run_id,
                force=True,
            )
        session.commit()
        walks_after = snapshot_walk_footprint_v1(session, tenant_id=tenant_id)

    proof = evaluate_p1_2_p3_deploy_proof_v1(
        closure_git_sha=closure_sha,
        prod_deploy=prod_deploy,
        schedule_pass=schedule_pass,
        walks_before=walks_before,
        walks_after=walks_after,
        deploy_recorded_at=deploy_started,
    )
    proof["recorded_at"] = datetime.now(UTC).isoformat()
    proof["tenant_id"] = args.tenant

    baseline_path = continuity_p0_baseline_path_v1(
        repo_root=REPO_ROOT,
        date_suffix=args.baseline_date,
    )
    baseline = load_continuity_p0_baseline_v1(baseline_path)
    baseline["step_1_2_p3_deploy"] = proof
    baseline["p1_2_closure_git_sha"] = closure_sha
    save_continuity_p0_baseline_v1(baseline_path, baseline)

    print(json.dumps(proof, indent=2, default=str))
    print(f"wrote {baseline_path}", file=sys.stderr)

    if not proof.get("p1_2_pass"):
        print("FAIL: step 1.2 not satisfied", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
