#!/usr/bin/env python3
"""Phase A step A3 — drain stale queued TCRE jobs and resume phase 07."""

from __future__ import annotations

import argparse
import functools
import json
import os
import subprocess
import sys
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
from vector.domains.cortex.substrate_pipeline.continuity_p0_tcre_job_drain import (
    DEFAULT_TENANT_ID,
    drive_tcre_queued_drain_v1,
    evaluate_p0_a3_tcre_job_drain_proof_v1,
    snapshot_tcre_job_drain_v1,
)
from vector.domains.cortex.substrate_pipeline.continuity_p0_trace_only_policy import (
    TraceOnlyProdSignoffError,
    add_trace_only_ci_argparse_v1,
    resolve_trace_only_cli_v1,
    save_p0_step_baseline_v1,
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
    parser = argparse.ArgumentParser(description="Phase A.3 TCRE queued drain prod proof")
    parser.add_argument("--tenant", default=TENANT_DEFAULT)
    parser.add_argument("--closure-sha", default="")
    parser.add_argument("--baseline-date", default="2026-05-22")
    parser.add_argument(
        "--stale-seconds",
        type=int,
        default=None,
        help="Queued age threshold (default settings: 3600)",
    )
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--snapshot-only", action="store_true")
    add_trace_only_ci_argparse_v1(parser)
    parser.add_argument(
        "--use-deployed-closure",
        action="store_true",
        help="Use prod API ECS tag as closure SHA (same as A.2)",
    )
    parser.add_argument(
        "--lease-only",
        action="store_true",
        help="Resume lease at phase 07 without Celery enqueue (for local prod proof)",
    )
    args = parser.parse_args()

    try:
        trace_only = resolve_trace_only_cli_v1(requested=args.trace_only)
    except TraceOnlyProdSignoffError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    dry_run = args.dry_run or args.snapshot_only
    closure_sha = _git_sha(args.closure_sha or os.environ.get("CONTINUITY_DEPLOY_GIT_SHA"))
    if args.use_deployed_closure:
        from vector.domains.cortex.substrate_pipeline.continuity_p0_baseline import (
            snapshot_prod_ecs_deploy_v1,
        )

        closure_sha = str(snapshot_prod_ecs_deploy_v1()["api"]["image_tag"])
        print(f"using deployed API tag as closure: {closure_sha[:12]}…", file=sys.stderr)

    tenant_id = uuid.UUID(args.tenant)
    deploy_started = datetime.now(UTC)
    prod_deploy = probe_prod_ecs_deploy_v1(expected_sha=closure_sha)

    engine = create_engine(_db_url())
    SessionLocal = sessionmaker(bind=engine)
    drain_drive: dict | None = None

    with SessionLocal() as session:
        snapshot = snapshot_tcre_job_drain_v1(session, tenant_id=tenant_id)
        if not dry_run:
            drain_drive = drive_tcre_queued_drain_v1(
                session,
                tenant_id=tenant_id,
                stale_after_seconds=args.stale_seconds,
                dry_run=False,
                enqueue_convergence=not args.lease_only,
            )
            session.commit()
        else:
            drain_drive = drive_tcre_queued_drain_v1(
                session,
                tenant_id=tenant_id,
                stale_after_seconds=args.stale_seconds,
                dry_run=True,
            )

    proof = evaluate_p0_a3_tcre_job_drain_proof_v1(
        closure_git_sha=closure_sha,
        prod_deploy=prod_deploy,
        snapshot=snapshot,
        drain_drive=drain_drive,
        deploy_recorded_at=deploy_started,
        trace_only=trace_only,
    )
    print(json.dumps(proof, indent=2, default=str))

    baseline_path = continuity_p0_baseline_path_v1(
        repo_root=REPO_ROOT,
        date_suffix=args.baseline_date,
    )
    baseline = load_continuity_p0_baseline_v1(baseline_path)
    hist_after = dict((drain_drive or {}).get("histogram_after") or snapshot.get("histogram") or {})
    step_record = {
        "validated_at": datetime.now(UTC).isoformat(),
        "closure_git_sha": closure_sha,
        "tenant_id": str(tenant_id),
        "p0_a3_pass": proof["p0_a3_pass"],
        "checks": proof["checks"],
        "checks_advisory": proof.get("checks_advisory"),
        "wiring_ok": (snapshot.get("wiring") or {}).get("wiring_ok"),
        "stale_queued_before": int((drain_drive or {}).get("stale_queued_before") or 0),
        "stale_queued_after": int((drain_drive or {}).get("stale_queued_after") or 0),
        "jobs_drained": int((drain_drive or {}).get("jobs_drained") or 0),
        "queued_after": int(hist_after.get("queued", 0)),
        "dry_run": dry_run,
        "lease_only": args.lease_only,
        "use_deployed_closure": args.use_deployed_closure,
    }
    saved = save_p0_step_baseline_v1(
        baseline_path,
        baseline,
        step_key="step_a3_tcre_queued_drain",
        step_record=step_record,
        trace_only=trace_only,
        save_fn=save_continuity_p0_baseline_v1,
    )
    if saved is None:
        print("baseline write skipped (CI --trace-only)", file=sys.stderr)
    else:
        print(f"baseline updated: {saved}")

    return 0 if proof["p0_a3_pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
